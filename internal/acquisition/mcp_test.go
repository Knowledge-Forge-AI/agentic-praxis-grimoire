package acquisition

import (
	"bytes"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

func server(t *testing.T) *Engine {
	t.Helper()
	e, err := Open(Config{RunDir: t.TempDir(), RunID: "run", BindingID: "review", AttemptID: "attempt", Consumer: skills.ConsumerClaude, Catalog: skills.CatalogInput{SchemaVersion: skills.CatalogSchemaV1}})
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { e.Close() })
	return e
}
func initialize(version string) string {
	return fmt.Sprintf(`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":%q,"capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`+"\n"+`{"jsonrpc":"2.0","method":"notifications/initialized"}`+"\n", version)
}
func TestLifecycleToolsResourcesAndDelivery(t *testing.T) {
	e := server(t)
	var out, diag bytes.Buffer
	input := initialize(ProtocolVersion) + `{"jsonrpc":"2.0","id":2,"method":"tools/list"}` + "\n" + `{"jsonrpc":"2.0","id":3,"method":"resources/templates/list"}` + "\n" + `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"skill_acquire","arguments":{"id":"apgr:go-test-profile"}}}` + "\n" + `{"jsonrpc":"2.0","id":5,"method":"resources/read","params":{"uri":"apgr://context/run/review"}}` + "\n"
	if err := e.Serve(strings.NewReader(input), &out, &diag); err != nil {
		t.Fatal(err)
	}
	lines := bytes.Split(bytes.TrimSpace(out.Bytes()), []byte("\n"))
	if len(lines) != 5 {
		t.Fatal(out.String())
	}
	var result struct {
		Result struct {
			Content []struct {
				Text string `json:"text"`
			} `json:"content"`
		} `json:"result"`
	}
	if err := json.Unmarshal(lines[3], &result); err != nil {
		t.Fatal(err)
	}
	selected, _ := skills.ResolveCatalog(e.config.Catalog, "apgr:go-test-profile", skills.ConsumerClaude)
	if result.Result.Content[0].Text != string(selected.Snapshot.Body) {
		t.Fatal("MCP body differs")
	}
	facts, err := e.Explain()
	if err != nil {
		t.Fatal(err)
	}
	events := facts["events"].([]Event)
	delivered := 0
	for _, event := range events {
		if event.ModelObserved != nil {
			t.Fatal("model claim")
		}
		if event.Kind == "channel_delivered" {
			delivered++
			if event.ControlledBytes != len(lines[3])+1 {
				t.Fatal("wire measurement differs")
			}
			var observed map[string]any
			raw, _ := json.Marshal(event)
			json.Unmarshal(raw, &observed)
			if observed["payload_sha256"] != fmt.Sprintf("%x", sha256.Sum256(append(lines[3], '\n'))) || observed["phase"] != "late" {
				t.Fatal("missing exact payload identity or phase", observed)
			}
		}
	}
	if delivered != 1 {
		t.Fatal(events)
	}
}
func TestProtocolErrors(t *testing.T) {
	for name, input := range map[string]string{
		"parse": "{\n", "duplicate": `{"jsonrpc":"2.0","id":2,"id":3,"method":"ping"}` + "\n", "batch": "[]\n", "null-id": `{"jsonrpc":"2.0","id":null,"method":"ping"}` + "\n", "early": `{"jsonrpc":"2.0","id":1,"method":"tools/list"}` + "\n", "unsupported": initialize(ProtocolVersion) + `{"jsonrpc":"2.0","id":2,"method":"shutdown"}` + "\n", "argument-duplicate": initialize(ProtocolVersion) + `{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"skill_acquire","arguments":{"id":"apgr:go-test-profile","id":"user:secret"}}}` + "\n",
	} {
		t.Run(name, func(t *testing.T) {
			e := server(t)
			var out bytes.Buffer
			if err := e.Serve(strings.NewReader(input), &out, &bytes.Buffer{}); err != nil {
				t.Fatal(err)
			}
			if !strings.Contains(out.String(), `"error"`) {
				t.Fatal(out.String())
			}
		})
	}
}

func TestDiscoveryPhaseAndRepeatIdentity(t *testing.T) {
	e := server(t)
	input := initialize(ProtocolVersion) +
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}` + "\n" +
		`{"jsonrpc":"2.0","id":3,"method":"tools/list"}` + "\n" +
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"skill_acquire","arguments":{"id":"apgr:go-test-profile"}}}` + "\n" +
		`{"jsonrpc":"2.0","id":5,"method":"tools/list"}` + "\n"
	var out bytes.Buffer
	if err := e.Serve(strings.NewReader(input), &out, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	facts, err := e.Explain()
	if err != nil {
		t.Fatal(err)
	}
	initial, late := 0, 0
	identities := map[string]bool{}
	for _, event := range facts["events"].([]Event) {
		if event.Kind != "response_delivered" && event.Kind != "channel_delivered" {
			continue
		}
		if identities[event.EventID] || len(event.PayloadSHA256) != 64 {
			t.Fatal("transmission identity missing or repeated")
		}
		identities[event.EventID] = true
		if event.Phase == "initial" {
			initial++
		} else if event.Phase == "late" {
			late++
		}
	}
	if initial != 2 || late != 3 {
		t.Fatalf("initial=%d late=%d", initial, late)
	}
}
func TestVersionNegotiationBoundsAndEOF(t *testing.T) {
	e := server(t)
	var out bytes.Buffer
	if err := e.Serve(strings.NewReader(initialize("other")), &out, &bytes.Buffer{}); err != nil || !strings.Contains(out.String(), ProtocolVersion) {
		t.Fatal(err, out.String())
	}
	for _, input := range []string{strings.Repeat("x", MaxMessageBytes+1), `{"jsonrpc":"2.0"}`} {
		if err := e.Serve(strings.NewReader(input), &bytes.Buffer{}, &bytes.Buffer{}); err == nil {
			t.Fatal("accepted unbounded or incomplete frame")
		}
	}
	if err := e.Serve(strings.NewReader(""), &bytes.Buffer{}, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
}

func TestReservedMetadataLifecycle(t *testing.T) {
	e := server(t)
	input := strings.Replace(initialize(ProtocolVersion), `"method":"notifications/initialized"}`, `"method":"notifications/initialized","params":{"_meta":{"trace":"fixture"}}}`, 1)
	for i, method := range []string{"ping", "tools/list", "resources/list", "resources/templates/list"} {
		input += fmt.Sprintf(`{"jsonrpc":"2.0","id":%d,"method":%q,"params":{"_meta":{}}}`+"\n", i+2, method)
	}
	input += `{"jsonrpc":"2.0","id":6,"method":"resources/read","params":{"uri":"apgr://context/run/review","_meta":{}}}` + "\n"
	var out bytes.Buffer
	if err := e.Serve(strings.NewReader(input), &out, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(out.String(), `"error"`) {
		t.Fatal(out.String())
	}
}

// H0 accounts every successful response frame once, including definitions and
// metadata. These wire facts do not establish model observation.
func TestAllSuccessfulResponseBytes(t *testing.T) {
	e := server(t)
	input := initialize(ProtocolVersion)
	input += `{"jsonrpc":"2.0","id":2,"method":"tools/list"}` + "\n"
	input += `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"skill_search","arguments":{"query":"go-test"}}}` + "\n"
	input += `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"context_explain","arguments":{}}}` + "\n"
	input += `{"jsonrpc":"2.0","id":5,"method":"resources/read","params":{"uri":"apgr://context/run/review"}}` + "\n"
	input += `{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"skill_acquire","arguments":{"id":"apgr:go-test-profile"}}}` + "\n"
	input += `{"jsonrpc":"2.0","id":7,"method":"resources/read","params":{"uri":"apgr://skills/apgr:go-test-profile"}}` + "\n"
	input += `{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"skill_search","arguments":{"query":"go-test"}}}` + "\n"
	var out bytes.Buffer
	if err := e.Serve(strings.NewReader(input), &out, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	facts, err := e.Explain()
	if err != nil {
		t.Fatal(err)
	}
	total, count := 0, 0
	for _, event := range facts["events"].([]Event) {
		if event.Kind == "channel_delivered" || event.Kind == "response_delivered" {
			total += event.ControlledBytes
			count++
		}
	}
	if total != out.Len() || count != 8 {
		t.Fatalf("accounted %d bytes/%d frames, delivered %d bytes/8 frames", total, count, out.Len())
	}
}

type hShortWriter struct{}

func (hShortWriter) Write(p []byte) (int, error) { return len(p) - 1, nil }
func TestUnsuccessfulWritesAreNotDelivered(t *testing.T) {
	e := server(t)
	if err := e.Serve(strings.NewReader(initialize(ProtocolVersion)), hShortWriter{}, &bytes.Buffer{}); err == nil {
		t.Fatal("short write accepted")
	}
	facts, _ := e.Explain()
	for _, event := range facts["events"].([]Event) {
		if event.Kind == "response_delivered" || event.Kind == "channel_delivered" {
			t.Fatal("partial write claimed success")
		}
	}
}
