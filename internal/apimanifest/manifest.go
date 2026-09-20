package apimanifest

import (
	"bytes"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"slices"
	"strings"
)

// Manifest represents the complete machine-readable API manifest of exported v0.12 Go surfaces.
type Manifest struct {
	Schema      string           `json:"schema"`
	GeneratedAt string           `json:"generated_at"`
	Version     string           `json:"version"`
	Maturity    string           `json:"maturity"`
	Packages    []PackageSurface `json:"packages"`
}

// PackageSurface captures all exported symbols of a package.
type PackageSurface struct {
	Path      string           `json:"path"`
	Doc       string           `json:"doc"`
	Constants []ConstantSymbol `json:"constants,omitempty"`
	Types     []TypeSymbol     `json:"types,omitempty"`
	Functions []FunctionSymbol `json:"functions,omitempty"`
}

type ConstantSymbol struct {
	Name  string `json:"name"`
	Value string `json:"value,omitempty"`
}

type TypeSymbol struct {
	Name    string           `json:"name"`
	Doc     string           `json:"doc,omitempty"`
	Kind    string           `json:"kind"`
	Def     string           `json:"def"`
	Methods []FunctionSymbol `json:"methods,omitempty"`
}

type FunctionSymbol struct {
	Name      string `json:"name"`
	Doc       string `json:"doc,omitempty"`
	Signature string `json:"signature"`
}

func nodeToString(fset *token.FileSet, node any) string {
	var buf bytes.Buffer
	if err := format.Node(&buf, fset, node); err != nil {
		return fmt.Sprintf("%v", node)
	}
	return buf.String()
}

// Generate extracts the exported API manifest from the specified repository root.
func Generate(root string) (*Manifest, error) {
	pkgPaths := []string{"phase", "routing", "evidence", "candidate", "provider"}
	slices.Sort(pkgPaths)

	fset := token.NewFileSet()
	var packages []PackageSurface

	for _, relPkg := range pkgPaths {
		pkgDir := filepath.Join(root, relPkg)
		pkgs, err := parser.ParseDir(fset, pkgDir, func(fi os.FileInfo) bool {
			return !strings.HasSuffix(fi.Name(), "_test.go")
		}, parser.ParseComments)
		if err != nil {
			return nil, fmt.Errorf("parsing %s: %w", relPkg, err)
		}

		for pkgName, astPkg := range pkgs {
			surface := PackageSurface{
				Path: "github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/" + relPkg,
			}

			var constants []ConstantSymbol
			typeMap := make(map[string]*TypeSymbol)
			var typeNames []string
			var functions []FunctionSymbol

			for filename, file := range astPkg.Files {
				if strings.HasSuffix(filename, "doc.go") && file.Doc != nil {
					surface.Doc = strings.TrimSpace(file.Doc.Text())
				}

				for _, decl := range file.Decls {
					switch d := decl.(type) {
					case *ast.GenDecl:
						switch d.Tok {
						case token.CONST:
							for _, spec := range d.Specs {
								vspec := spec.(*ast.ValueSpec)
								for i, name := range vspec.Names {
									if ast.IsExported(name.Name) {
										val := ""
										if i < len(vspec.Values) {
											val = nodeToString(fset, vspec.Values[i])
										}
										constants = append(constants, ConstantSymbol{
											Name:  name.Name,
											Value: val,
										})
									}
								}
							}
						case token.TYPE:
							for _, spec := range d.Specs {
								tspec := spec.(*ast.TypeSpec)
								if ast.IsExported(tspec.Name.Name) {
									kind := "type"
									switch tspec.Type.(type) {
									case *ast.StructType:
										kind = "struct"
									case *ast.InterfaceType:
										kind = "interface"
									}
									doc := ""
									if d.Doc != nil {
										doc = strings.TrimSpace(d.Doc.Text())
									}
									ts := &TypeSymbol{
										Name: tspec.Name.Name,
										Doc:  doc,
										Kind: kind,
										Def:  nodeToString(fset, tspec.Type),
									}
									typeMap[tspec.Name.Name] = ts
									typeNames = append(typeNames, tspec.Name.Name)
								}
							}
						}
					case *ast.FuncDecl:
						if !ast.IsExported(d.Name.Name) {
							continue
						}
						doc := ""
						if d.Doc != nil {
							doc = strings.TrimSpace(d.Doc.Text())
						}

						sig := nodeToString(fset, d.Type)
						fn := FunctionSymbol{
							Name:      d.Name.Name,
							Doc:       doc,
							Signature: sig,
						}

						// Check if method
						if d.Recv != nil && len(d.Recv.List) > 0 {
							recvType := nodeToString(fset, d.Recv.List[0].Type)
							recvType = strings.TrimPrefix(recvType, "*")
							if ts, ok := typeMap[recvType]; ok {
								ts.Methods = append(ts.Methods, fn)
								continue
							}
						}
						functions = append(functions, fn)
					}
				}
			}

			// Sort constants
			slices.SortFunc(constants, func(a, b ConstantSymbol) int {
				return strings.Compare(a.Name, b.Name)
			})
			surface.Constants = constants

			// Sort types
			slices.Sort(typeNames)
			for _, name := range typeNames {
				ts := typeMap[name]
				slices.SortFunc(ts.Methods, func(a, b FunctionSymbol) int {
					return strings.Compare(a.Name, b.Name)
				})
				surface.Types = append(surface.Types, *ts)
			}

			// Sort functions
			slices.SortFunc(functions, func(a, b FunctionSymbol) int {
				return strings.Compare(a.Name, b.Name)
			})
			surface.Functions = functions

			_ = pkgName
			packages = append(packages, surface)
		}
	}

	slices.SortFunc(packages, func(a, b PackageSurface) int {
		return strings.Compare(a.Path, b.Path)
	})

	return &Manifest{
		Schema:      "apgr-go-api-manifest-v1",
		GeneratedAt: "2026-09-17T00:00:00Z",
		Version:     "v0.12.0-provisional",
		Maturity:    "experimental",
		Packages:    packages,
	}, nil
}
