package acquisition

import (
	"bufio"
	"encoding/json"
	"errors"
	"io"
	"strings"
)

const ProtocolVersion = "2025-11-25"

type rpcRequest struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id,omitempty"`
	Method  string          `json:"method"`
	Params  json.RawMessage `json:"params,omitempty"`
}
type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func rpcFailure(code int, message string) *rpcError { return &rpcError{code, message} }
func textResult(value any) map[string]any {
	raw, _ := json.Marshal(value)
	return map[string]any{"content": []any{map[string]any{"type": "text", "text": string(raw)}}}
}
func params(data json.RawMessage, target any) error {
	if len(data) == 0 {
		data = json.RawMessage(`{}`)
	}
	if len(data) == 0 || data[0] != '{' {
		return errors.New("invalid params")
	}
	// MCP reserves metadata on request/notification parameters. Validate it
	// before removing it from the method-specific closed shape.
	var fields map[string]json.RawMessage
	if err := StrictJSON(data, &fields); err != nil {
		return err
	}
	if meta, ok := fields["_meta"]; ok {
		var value map[string]json.RawMessage
		if len(meta) == 0 || meta[0] != '{' || StrictJSON(meta, &value) != nil {
			return errors.New("invalid metadata")
		}
		delete(fields, "_meta")
	}
	clean, err := json.Marshal(fields)
	if err != nil {
		return err
	}
	return StrictJSON(clean, target)
}
func toolSchema(key string) map[string]any {
	properties := map[string]any{}
	required := []string{}
	if key != "" {
		properties[key] = map[string]any{"type": "string", "maxLength": 256}
		required = append(required, key)
	}
	return map[string]any{"type": "object", "properties": properties, "required": required, "additionalProperties": false}
}
func Tools() []any {
	return []any{
		map[string]any{"name": "skill_search", "description": "Search permitted skill metadata in the captured catalog.", "inputSchema": toolSchema("query")},
		map[string]any{"name": "skill_acquire", "description": "Acquire an exact qualified skill and declared support in run-owned storage.", "inputSchema": toolSchema("id")},
		map[string]any{"name": "context_explain", "description": "Explain this retained run, binding and attempt; observation remains unknown.", "inputSchema": toolSchema("")},
	}
}

// Serve implements a synchronous, bounded newline-delimited stdio lifecycle.
// It sends no requests: the client owns connection deadlines and EOF shutdown.
func (e *Engine) Serve(in io.Reader, out, diagnostics io.Writer) error {
	reader := bufio.NewReaderSize(in, MaxMessageBytes+1)
	state := 0
	seen := map[string]bool{}
	initialDiscovery := true
	discoverySeen := map[string]bool{}
	for count := 0; count < MaxEvents; count++ {
		line, err := reader.ReadSlice('\n')
		if err == io.EOF && len(line) == 0 {
			return nil
		}
		if len(line) > MaxMessageBytes || err == bufio.ErrBufferFull {
			return errors.New("MCP_MESSAGE_TOO_LARGE")
		}
		if err != nil {
			return errors.New("MCP_INCOMPLETE_FRAME")
		}
		var req rpcRequest
		var result any
		var failure *rpcError
		var delivery string
		var id any
		if !json.Valid(line) {
			failure = rpcFailure(-32700, "Parse error")
		} else if StrictJSON(line, &req) != nil || req.JSONRPC != "2.0" || req.Method == "" {
			failure = rpcFailure(-32600, "Invalid Request")
		} else {
			if len(req.ID) > 0 {
				if StrictJSON(req.ID, &id) != nil {
					failure = rpcFailure(-32600, "Invalid Request")
				} else {
					switch v := id.(type) {
					case string:
						if len(v) > 128 {
							failure = rpcFailure(-32600, "Invalid Request")
						}
					case json.Number:
						if _, err := v.Int64(); err != nil {
							failure = rpcFailure(-32600, "Invalid Request")
						}
					default:
						failure = rpcFailure(-32600, "Invalid Request")
					}
				}
				if failure != nil {
					id = nil
				}
			}
			if failure == nil && len(req.ID) == 0 {
				// Notifications never receive responses. Unknown notifications carry no
				// execution authority. Initialization must follow the initialize response.
				if req.Method == "notifications/initialized" && state == 1 {
					var empty struct{}
					if params(req.Params, &empty) == nil {
						state = 2
					} else {
						io.WriteString(diagnostics, "MCP_INVALID_INITIALIZED_PARAMS\n")
					}
				}
				continue
			}
			if failure == nil {
				canonicalID, _ := json.Marshal(id)
				key := string(canonicalID)
				if seen[key] {
					failure = rpcFailure(-32600, "Request ID already used")
				} else {
					seen[key] = true
				}
			}
			if failure == nil {
				switch req.Method {
				case "initialize":
					var p struct {
						ProtocolVersion string                     `json:"protocolVersion"`
						Capabilities    map[string]json.RawMessage `json:"capabilities"`
						ClientInfo      map[string]json.RawMessage `json:"clientInfo"`
						Meta            map[string]json.RawMessage `json:"_meta,omitempty"`
					}
					if state != 0 {
						failure = rpcFailure(-32600, "Already initialized")
					} else if params(req.Params, &p) != nil || p.ProtocolVersion == "" || p.Capabilities == nil || p.ClientInfo == nil || !nonemptyString(p.ClientInfo["name"]) || !nonemptyString(p.ClientInfo["version"]) {
						failure = rpcFailure(-32602, "Invalid initialization parameters")
					} else {
						// A different requested revision negotiates our one supported revision;
						// a client unable to speak it disconnects before initialized.
						result = map[string]any{"protocolVersion": ProtocolVersion, "capabilities": map[string]any{"tools": map[string]any{}, "resources": map[string]any{}}, "serverInfo": map[string]any{"name": "apgr", "version": "1"}}
						state = 1
					}
				case "ping":
					var empty struct{}
					if params(req.Params, &empty) != nil {
						failure = rpcFailure(-32602, "Invalid params")
					} else {
						result = map[string]any{}
					}
				default:
					if e.config.Preparation {
						failure = rpcFailure(-32600, "Preparation session cannot serve agent requests")
					} else if state != 2 {
						failure = rpcFailure(-32001, "Server not initialized")
					} else {
						result, delivery, failure = e.dispatch(req.Method, req.Params)
					}
				}
			}
		}
		response := map[string]any{"jsonrpc": "2.0", "id": id}
		if failure != nil {
			response["error"] = failure
		} else {
			response["result"] = result
		}
		raw, marshalErr := json.Marshal(response)
		if marshalErr != nil {
			return marshalErr
		}
		if len(raw)+1 > MaxMessageBytes {
			delivery = ""
			failure = rpcFailure(-32000, "MCP_RESULT_TOO_LARGE")
			raw, _ = json.Marshal(map[string]any{"jsonrpc": "2.0", "id": id, "error": rpcFailure(-32000, "MCP_RESULT_TOO_LARGE")})
		}
		raw = append(raw, '\n')
		n, writeErr := out.Write(raw)
		if writeErr != nil {
			return writeErr
		}
		if n != len(raw) {
			return io.ErrShortWrite
		}
		var observationErr error
		phase := "late"
		if req.Method == "tools/call" || req.Method == "resources/read" {
			initialDiscovery = false
		}
		if initialDiscovery && !discoverySeen[req.Method] && (req.Method == "initialize" || req.Method == "tools/list" || req.Method == "resources/list" || req.Method == "resources/templates/list") {
			phase = "initial"
			discoverySeen[req.Method] = true
		}
		if delivery != "" {
			observationErr = e.Delivered(delivery, "mcp", n, raw)
		} else if failure == nil {
			toolError := false
			if r, ok := result.(map[string]any); ok {
				toolError, _ = r["isError"].(bool)
			}
			if !toolError {
				observationErr = e.responseDeliveredAt("mcp", req.Method, phase, n, raw)
			}
		}
		if observationErr != nil {
			io.WriteString(diagnostics, "MCP_DELIVERY_OBSERVATION_WRITE_FAILED\n")
			return observationErr
		}
	}
	return errors.New("MCP_SESSION_MESSAGE_LIMIT")
}

func nonemptyString(raw json.RawMessage) bool {
	var value string
	return json.Unmarshal(raw, &value) == nil && value != ""
}
func (e *Engine) dispatch(method string, data json.RawMessage) (any, string, *rpcError) {
	invalid := func() (any, string, *rpcError) { return nil, "", rpcFailure(-32602, "Invalid params") }
	switch method {
	case "tools/list", "resources/list", "resources/templates/list":
		var listing struct {
			Cursor *string `json:"cursor,omitempty"`
		}
		if params(data, &listing) != nil || listing.Cursor != nil {
			return invalid()
		}
		switch method {
		case "tools/list":
			return map[string]any{"tools": Tools()}, "", nil
		case "resources/list":
			return map[string]any{"resources": []any{}}, "", nil
		default:
			return map[string]any{"resourceTemplates": []any{
				map[string]any{"uriTemplate": "apgr://skills/{namespace}:{id}", "name": "skill", "mimeType": "application/json"},
				map[string]any{"uriTemplate": "apgr://context/{run_id}/{binding_id}", "name": "context", "mimeType": "application/json"},
			}}, "", nil
		}
	case "tools/call":
		var p struct {
			Name      string                     `json:"name"`
			Arguments json.RawMessage            `json:"arguments"`
			Meta      map[string]json.RawMessage `json:"_meta,omitempty"`
		}
		if params(data, &p) != nil {
			return invalid()
		}
		switch p.Name {
		case "skill_search":
			var arg struct {
				Query *string `json:"query"`
			}
			if params(p.Arguments, &arg) != nil || arg.Query == nil {
				return invalid()
			}
			rows, err := e.Search(*arg.Query, "mcp")
			if err != nil {
				return toolFailure(err)
			}
			return textResult(rows), "", nil
		case "skill_acquire":
			var arg struct {
				ID string `json:"id"`
			}
			if params(p.Arguments, &arg) != nil || arg.ID == "" {
				return invalid()
			}
			acquired, err := e.Acquire(arg.ID, "mcp")
			if err != nil {
				return toolFailure(err)
			}
			// The first content block is the complete body, directly usable as text.
			// Exact binary support and identity are in a single JSON envelope block.
			result := map[string]any{"content": []any{map[string]any{"type": "text", "text": string(acquired.Selection.Snapshot.Body)}, map[string]any{"type": "text", "text": supportEnvelope(acquired)}}}
			return result, acquired.EventID, nil
		case "context_explain":
			var empty struct{}
			if params(p.Arguments, &empty) != nil {
				return invalid()
			}
			explanation, err := e.Explain()
			if err != nil {
				return toolFailure(err)
			}
			return textResult(explanation), "", nil
		default:
			return nil, "", rpcFailure(-32602, "Unknown tool")
		}
	case "resources/read":
		var p struct {
			URI string `json:"uri"`
		}
		if params(data, &p) != nil {
			return invalid()
		}
		var result any
		delivery := ""
		if p.URI == e.ContextURI() {
			v, err := e.Explain()
			if err != nil {
				return nil, "", rpcFailure(-32000, err.Error())
			}
			result = v
		} else if strings.HasPrefix(p.URI, "apgr://skills/") {
			a, err := e.Acquire(strings.TrimPrefix(p.URI, "apgr://skills/"), "mcp")
			if err != nil {
				return nil, "", rpcFailure(-32002, err.Error())
			}
			result = a
			delivery = a.EventID
		} else {
			return nil, "", rpcFailure(-32002, "Resource not found")
		}
		raw, _ := json.Marshal(result)
		return map[string]any{"contents": []any{map[string]any{"uri": p.URI, "mimeType": "application/json", "text": string(raw)}}}, delivery, nil
	default:
		return nil, "", rpcFailure(-32601, "Method not found")
	}
}
func supportEnvelope(a Result) string {
	raw, _ := json.Marshal(map[string]any{"event_id": a.EventID, "requested_identity": a.Selection.RequestedIdentity, "selected_identity": a.Selection.SelectedIdentity, "source_sha256": a.Selection.SourceSHA256, "content_identity": a.Selection.ContentIdentity, "support": a.Selection.Snapshot.Support, "materialized_path": a.MaterializedPath, "is_repeat_delivery": a.IsRepeatDelivery})
	return string(raw)
}
func toolFailure(err error) (any, string, *rpcError) {
	r := textResult(map[string]any{"diagnostic": err.Error()})
	r["isError"] = true
	return r, "", nil
}
