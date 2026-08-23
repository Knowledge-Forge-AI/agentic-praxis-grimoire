package hotspot

import (
	"bytes"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"strings"
)

type goOwnerMetrics struct {
	statements int64
	complexity int64
	nesting    int64
	parameters int64
}

func analyzeGo(path string, content []byte, row *FileRow) ([]OwnerRow, []RegionRow, []Warning) {
	row.Generated = generatedGo(content)
	set := token.NewFileSet()
	parsed, err := parser.ParseFile(set, path, content, parser.AllErrors|parser.ParseComments)
	if err != nil || parsed == nil {
		row.ParseFailure = "go-syntax-error"
		unavailableSemanticMetrics(row, "go-parse-failed")
		return nil, nil, []Warning{{Code: "parse-failure", Path: path, Detail: "Go syntax could not be parsed exactly"}}
	}
	var owners []OwnerRow
	var regions []RegionRow
	ast.Inspect(parsed, func(node ast.Node) bool {
		switch value := node.(type) {
		case *ast.FuncDecl:
			position := set.Position(value.Pos())
			end := set.Position(value.End())
			name := value.Name.Name
			kind := "function"
			if value.Recv != nil && len(value.Recv.List) > 0 {
				kind = "method"
				name = receiverName(value.Recv.List[0].Type) + "." + name
			}
			metrics := inspectGoOwner(value.Body, value.Type)
			owner := goOwnerRow(path, kind, name, position.Line, position.Column, end.Line, metrics, row.Generated)
			owners = append(owners, owner)
			if value.Recv == nil && value.Name.Name == "init" {
				regions = append(regions, RegionRow{
					ID: stableID("region:init", path, position.Line, position.Column), Path: path, Language: LanguageGo,
					Kind: "init-region", DisplayName: "init", StartLine: position.Line, EndLine: end.Line, Confidence: ConfidenceHigh,
					Metrics: []Metric{metric(MetricProceduralSize, AvailabilityExact, metrics.statements, "statements", "go-package-regions:E"), lineSpanMetric(position.Line, end.Line)},
				})
			}
		case *ast.FuncLit:
			position := set.Position(value.Pos())
			end := set.Position(value.End())
			name := fmt.Sprintf("func literal at %d:%d", position.Line, position.Column)
			metrics := inspectGoOwner(value.Body, value.Type)
			owners = append(owners, goOwnerRow(path, "function-literal", name, position.Line, position.Column, end.Line, metrics, row.Generated))
		}
		return true
	})
	for _, declaration := range parsed.Decls {
		general, ok := declaration.(*ast.GenDecl)
		if !ok || general.Tok != token.VAR {
			continue
		}
		for _, spec := range general.Specs {
			value, ok := spec.(*ast.ValueSpec)
			if !ok || len(value.Values) == 0 {
				continue
			}
			position := set.Position(value.Pos())
			end := set.Position(value.End())
			regions = append(regions, RegionRow{
				ID: stableID("region:package-initializer", path, position.Line, position.Column), Path: path, Language: LanguageGo,
				Kind: "package-initializer", DisplayName: strings.Join(identifierNames(value.Names), ", "), StartLine: position.Line, EndLine: end.Line, Confidence: ConfidenceHigh,
				Metrics: []Metric{metric(MetricProceduralSize, AvailabilityExact, int64(len(value.Values)), "initializers", "go-package-regions:E"), lineSpanMetric(position.Line, end.Line)},
			})
		}
	}
	totalStatements := int64(0)
	maxComplexity := int64(0)
	maxNesting := int64(0)
	for _, owner := range owners {
		totalStatements += availableMetricValue(owner.Metrics, MetricStatements)
		if value := availableMetricValue(owner.Metrics, MetricCyclomatic); value > maxComplexity {
			maxComplexity = value
		}
		if value := availableMetricValue(owner.Metrics, MetricNesting); value > maxNesting {
			maxNesting = value
		}
	}
	row.Metrics = append(row.Metrics,
		metric(MetricStatements, AvailabilityExact, totalStatements, "statements", "go-statements:E"),
		metric(MetricSymbols, AvailabilityExact, int64(len(owners)), "owners", ""),
		metric(MetricCyclomatic, AvailabilityExact, maxComplexity, "complexity", "go-cyclomatic:E"),
		metric(MetricNesting, AvailabilityExact, maxNesting, "levels", "go-control-nesting:E"),
	)
	row.PrimarySize = PrimarySize{Value: totalStatements, Unit: "statements"}
	return owners, regions, nil
}

func generatedGo(content []byte) bool {
	prefix := content
	if len(prefix) > 2048 {
		prefix = prefix[:2048]
	}
	for _, line := range bytes.Split(prefix, []byte{'\n'}) {
		text := strings.TrimSuffix(string(line), "\r")
		if strings.HasPrefix(text, "// Code generated ") && strings.HasSuffix(text, " DO NOT EDIT.") {
			return true
		}
	}
	return false
}

func receiverName(expression ast.Expr) string {
	switch value := expression.(type) {
	case *ast.Ident:
		return value.Name
	case *ast.StarExpr:
		return "(*" + receiverName(value.X) + ")"
	case *ast.IndexExpr:
		return receiverName(value.X)
	case *ast.IndexListExpr:
		return receiverName(value.X)
	default:
		return "receiver"
	}
}

func identifierNames(values []*ast.Ident) []string {
	result := make([]string, 0, len(values))
	for _, value := range values {
		result = append(result, value.Name)
	}
	return result
}

func goOwnerRow(path, kind, name string, line, column, end int, values goOwnerMetrics, generated bool) OwnerRow {
	return OwnerRow{
		ID: stableID("owner:"+kind, path, line, column), Path: path, Language: LanguageGo, Kind: kind, DisplayName: name,
		StartLine: line, EndLine: end, Confidence: ConfidenceHigh, Generated: generated,
		Metrics: []Metric{
			metric(MetricStatements, AvailabilityExact, values.statements, "statements", "go-owner-statements:E"),
			metric(MetricCyclomatic, AvailabilityExact, values.complexity, "complexity", "go-owner-cyclomatic:E"),
			metric(MetricNesting, AvailabilityExact, values.nesting, "levels", "go-owner-nesting:E"),
			metric(MetricParameters, AvailabilityExact, values.parameters, "parameters", ""),
			lineSpanMetric(line, end),
		},
	}
}

func inspectGoOwner(body *ast.BlockStmt, functionType *ast.FuncType) goOwnerMetrics {
	result := goOwnerMetrics{complexity: 1, parameters: countParameters(functionType)}
	if body == nil {
		return result
	}
	visitor := &goMetricVisitor{result: &result}
	ast.Walk(visitor, body)
	return result
}

type goMetricVisitor struct {
	result       *goOwnerMetrics
	controlDepth int64
	stack        []bool
}

func (visitor *goMetricVisitor) Visit(node ast.Node) ast.Visitor {
	if node == nil {
		if len(visitor.stack) > 0 {
			last := visitor.stack[len(visitor.stack)-1]
			visitor.stack = visitor.stack[:len(visitor.stack)-1]
			if last {
				visitor.controlDepth--
			}
		}
		return visitor
	}
	if _, ok := node.(*ast.FuncLit); ok {
		return nil
	}
	if statement, ok := node.(ast.Stmt); ok {
		if _, block := statement.(*ast.BlockStmt); !block {
			visitor.result.statements++
		}
	}
	increment, control := goNodeEffects(node)
	visitor.result.complexity += increment
	if control {
		visitor.controlDepth++
		if visitor.controlDepth > visitor.result.nesting {
			visitor.result.nesting = visitor.controlDepth
		}
	}
	visitor.stack = append(visitor.stack, control)
	return visitor
}

func goNodeEffects(node ast.Node) (int64, bool) {
	switch value := node.(type) {
	case *ast.IfStmt, *ast.ForStmt, *ast.RangeStmt:
		return 1, true
	case *ast.SwitchStmt, *ast.TypeSwitchStmt, *ast.SelectStmt:
		return 0, true
	case *ast.CaseClause:
		if len(value.List) > 0 {
			return 1, false
		}
	case *ast.CommClause:
		if value.Comm != nil {
			return 1, false
		}
	case *ast.BinaryExpr:
		if value.Op == token.LAND || value.Op == token.LOR {
			return 1, false
		}
	}
	return 0, false
}

func countParameters(functionType *ast.FuncType) int64 {
	if functionType == nil || functionType.Params == nil {
		return 0
	}
	result := int64(0)
	for _, field := range functionType.Params.List {
		if len(field.Names) == 0 {
			result++
		} else {
			result += int64(len(field.Names))
		}
	}
	return result
}

func availableMetricValue(metrics []Metric, name string) int64 {
	for _, value := range metrics {
		if value.Name == name && value.Value != nil {
			return *value.Value
		}
	}
	return 0
}
