// Package acquisition owns the bounded local late-acquisition channel shared by
// CLI and MCP. It has no network, subprocess, configuration, or execution owner.
package acquisition

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"net/url"
	"os"
	"path"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"sync"
	"syscall"
	"unicode/utf8"

	"github.com/Knowledge-Forge-AI/agentic-praxis-grimoire/skills"
)

const MaxMessageBytes = 1 << 20
const MaxEvents = 4096
const MaxResultBytes = 768 << 10
const MaxBindingEvents = 256
const MaxStoreBytes = 24 << 20
const MaxStoreEntries = 4096

var identity = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:/-]{0,511}$`)
var qualified = regexp.MustCompile(`^(apgr|project|user):[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`)

type Config struct {
	Preparation bool                `json:"preparation,omitempty"`
	RunDir      string              `json:"run_dir"`
	RunID       string              `json:"run_id"`
	BindingID   string              `json:"binding_id"`
	AttemptID   string              `json:"attempt_id"`
	Consumer    skills.ConsumerKind `json:"consumer"`
	Catalog     skills.CatalogInput `json:"catalog"`
	ProjectRoot string              `json:"project_root,omitempty"`
	APGRHome    string              `json:"apgr_home,omitempty"`
	AllowedIDs  []string            `json:"allowed_ids"`
	// ContextPlan is a captured immutable F invocation record, never a path to
	// discover or re-plan. Absence is explicitly reported by Explain.
	ContextPlan json.RawMessage `json:"context_plan,omitempty"`
}

type Event struct {
	Schema           string `json:"schema"`
	EventID          string `json:"event_id"`
	AcquisitionID    string `json:"acquisition_id,omitempty"`
	RunID            string `json:"run_id"`
	BindingID        string `json:"binding_id"`
	AttemptID        string `json:"attempt_id"`
	Sequence         uint64 `json:"sequence"`
	Kind             string `json:"kind"`
	Channel          string `json:"channel"`
	Requested        string `json:"requested,omitempty"`
	Selected         string `json:"selected,omitempty"`
	ContentIdentity  string `json:"content_identity,omitempty"`
	MaterializedPath string `json:"materialized_path,omitempty"`
	IsRepeatDelivery bool   `json:"is_repeat_delivery"`
	ControlledBytes  int    `json:"controlled_bytes"`
	PayloadSHA256    string `json:"payload_sha256,omitempty"`
	Phase            string `json:"phase,omitempty"`
	Provenance       string `json:"provenance,omitempty"`
	ObservationKind  string `json:"observation_kind,omitempty"`
	IndexState       string `json:"index_state"`
	ProviderObserved any    `json:"provider_observed"`
	ModelObserved    any    `json:"model_observed"`
	Tokens           any    `json:"tokens"`
	Diagnostic       string `json:"diagnostic,omitempty"`
}
type Result struct {
	EventID          string                  `json:"event_id"`
	Selection        skills.CatalogSelection `json:"selection"`
	MaterializedPath string                  `json:"materialized_path"`
	IsRepeatDelivery bool                    `json:"is_repeat_delivery"`
}
type SearchRow struct {
	ID              string `json:"id"`
	SelectedID      string `json:"selected_id"`
	Description     string `json:"description"`
	Bytes           int64  `json:"bytes"`
	ContentIdentity string `json:"content_identity"`
}
type Engine struct {
	mu          sync.Mutex
	config      Config
	catalog     skills.Catalog
	root        *os.Root
	nonce       string
	sequence    uint64
	diagnostics []string
}

func Open(c Config) (*Engine, error) {
	if !identity.MatchString(c.RunID) || !identity.MatchString(c.BindingID) || !identity.MatchString(c.AttemptID) {
		return nil, errors.New("ACQUIRE_INVALID_SCOPE")
	}
	switch c.Consumer {
	case skills.ConsumerClaude, skills.ConsumerCodex, skills.ConsumerGo, skills.ConsumerChatGPT:
	default:
		return nil, errors.New("ACQUIRE_INVALID_CONSUMER")
	}
	if !filepath.IsAbs(c.RunDir) || filepath.Clean(c.RunDir) != c.RunDir {
		return nil, errors.New("ACQUIRE_INVALID_STORE")
	}
	// Caller owns the selected run root; never create an arbitrary supplied root.
	info, err := os.Lstat(c.RunDir)
	if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return nil, errors.New("ACQUIRE_INVALID_STORE")
	}
	if len(c.ContextPlan) > MaxResultBytes {
		return nil, errors.New("ACQUIRE_PLAN_TOO_LARGE")
	}
	if len(c.ContextPlan) > 0 {
		var plan map[string]any
		if StrictJSON(c.ContextPlan, &plan) != nil || plan["schema"] != "apg.invocation-context/v1" || plan["run_id"] != c.RunID || plan["binding_id"] != c.BindingID || plan["attempt_id"] != c.AttemptID {
			return nil, errors.New("ACQUIRE_PLAN_SCOPE_MISMATCH")
		}
	}
	// Own input bytes, including override relationships, for the entire channel.
	raw, err := json.Marshal(c)
	if err != nil {
		return nil, err
	}
	var owned Config
	if err = json.Unmarshal(raw, &owned); err != nil {
		return nil, err
	}
	c = owned
	catalog, err := skills.BuildCatalog(c.Catalog)
	if err != nil {
		return nil, errors.New("ACQUIRE_INVALID_CATALOG")
	}
	if len(c.AllowedIDs) > 128 {
		return nil, errors.New("ACQUIRE_ALLOWLIST_LIMIT")
	}
	for _, id := range c.AllowedIDs {
		if !qualified.MatchString(id) {
			return nil, errors.New("ACQUIRE_INVALID_ALLOWLIST")
		}
	}
	root, err := os.OpenRoot(c.RunDir)
	if err != nil {
		return nil, errors.New("ACQUIRE_INVALID_STORE")
	}
	e := &Engine{config: c, catalog: catalog, root: root}
	var nonce [16]byte
	if _, err = rand.Read(nonce[:]); err != nil {
		root.Close()
		return nil, err
	}
	e.nonce = hex.EncodeToString(nonce[:])
	if err = e.directory("acquisitions/skills"); err != nil {
		root.Close()
		return nil, err
	}
	return e, nil
}
func (e *Engine) Close() error { return e.root.Close() }

// directory pins each direct directory while descending; symlinks are refused.
func (e *Engine) directory(name string) error {
	r, err := e.root.OpenRoot(".")
	if err != nil {
		return err
	}
	defer func() { r.Close() }()
	for _, part := range strings.Split(name, "/") {
		if part == "" || part == "." || part == ".." {
			return errors.New("ACQUIRE_UNSAFE_PATH")
		}
		if err = r.Mkdir(part, 0700); err != nil && !os.IsExist(err) {
			return errors.New("ACQUIRE_STORE_WRITE_FAILED")
		}
		info, err := r.Lstat(part)
		if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
			return errors.New("ACQUIRE_UNSAFE_PATH")
		}
		next, err := r.OpenRoot(part)
		if err != nil {
			return errors.New("ACQUIRE_UNSAFE_PATH")
		}
		r.Close()
		r = next
	}
	return nil
}
func (e *Engine) write(name string, data []byte) error {
	// os.Root confines even a raced ancestor replacement; O_EXCL refuses final
	// symlinks and hardlinks. Files are never overwritten on delivery or resume.
	f, err := e.root.OpenFile(name, os.O_WRONLY|os.O_CREATE|os.O_EXCL|syscall.O_NOFOLLOW, 0600)
	if err != nil {
		return errors.New("ACQUIRE_STORE_WRITE_FAILED")
	}
	_, err = f.Write(data)
	if err == nil {
		err = f.Sync()
	}
	closeErr := f.Close()
	if err == nil {
		err = closeErr
	}
	return err
}
func (e *Engine) events() ([]Event, error) {
	e.diagnostics = nil
	dir, err := e.root.Open("acquisitions")
	if err != nil {
		return nil, err
	}
	entries, err := dir.ReadDir(MaxEvents + 3)
	dir.Close()
	if err != nil && err != io.EOF {
		return nil, err
	}
	if len(entries) > MaxEvents+2 {
		return nil, errors.New("ACQUIRE_EVENT_LIMIT")
	}
	result := []Event{}
	for _, entry := range entries {
		if !strings.HasPrefix(entry.Name(), "event-") || !strings.HasSuffix(entry.Name(), ".jsonl") {
			continue
		}
		data, err := ReadFile(e.root, "acquisitions/"+entry.Name(), 8192)
		var event Event
		if err != nil || StrictJSON(data, &event) != nil || event.Schema != "apg.acquisition-event/v1" || entry.Name() != "event-"+event.EventID+".jsonl" || event.RunID != e.config.RunID || !identity.MatchString(event.BindingID) || !identity.MatchString(event.AttemptID) {
			e.diagnostics = append(e.diagnostics, "ACQUIRE_INVALID_EVENT:"+entry.Name())
			continue
		}
		result = append(result, event)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].EventID < result[j].EventID })
	return result, nil
}
func (e *Engine) emit(event Event) (Event, error) {
	events, err := e.events()
	if err != nil {
		return event, err
	}
	if len(events) >= MaxEvents {
		return event, errors.New("ACQUIRE_EVENT_LIMIT")
	}
	scoped := 0
	for _, prior := range events {
		if prior.BindingID == e.config.BindingID {
			scoped++
		}
	}
	if scoped >= MaxBindingEvents {
		return event, errors.New("ACQUIRE_BINDING_EVENT_LIMIT")
	}
	e.sequence++
	seed, _ := json.Marshal([]any{"apg.acquisition-event/v1", e.config.RunID, e.config.BindingID, e.config.AttemptID, e.nonce, e.sequence})
	sum := sha256.Sum256(seed)
	event.Schema = "apg.acquisition-event/v1"
	event.EventID = hex.EncodeToString(sum[:])
	event.Sequence = e.sequence
	event.RunID = e.config.RunID
	event.BindingID = e.config.BindingID
	event.AttemptID = e.config.AttemptID
	event.IndexState = "not_observed"
	raw, _ := json.Marshal(event)
	raw = append(raw, '\n')
	// Stage under an unadvertised name, then publish without replacement. A
	// killed writer never exposes partial JSON as a canonical event.
	temporary := "acquisitions/.pending-" + event.EventID
	defer e.root.Remove(temporary)
	if err := e.write(temporary, raw); err != nil {
		return event, err
	}
	if err := e.root.Link(temporary, "acquisitions/event-"+event.EventID+".jsonl"); err != nil {
		return event, err
	}
	dir, err := e.root.Open("acquisitions")
	if err != nil {
		return event, err
	}
	defer dir.Close()
	return event, dir.Sync()
}
func (e *Engine) Search(query, channel string) ([]SearchRow, error) {
	e.mu.Lock()
	defer e.mu.Unlock()
	unlock, err := e.lock()
	if err != nil {
		return nil, err
	}
	defer unlock()
	if len(query) > 256 {
		return nil, errors.New("ACQUIRE_QUERY_TOO_LARGE")
	}
	rows := []SearchRow{}
	for _, d := range e.catalog.Skills {
		if !e.allowed(d.QualifiedID) {
			continue
		}
		if strings.Contains(strings.ToLower(d.QualifiedID+" "+d.Description), strings.ToLower(query)) {
			// Apply the same selected identity and consumer boundary as acquisition.
			selected, err := skills.ResolveCatalog(e.config.Catalog, d.QualifiedID, e.config.Consumer)
			if err != nil {
				continue
			}
			description := d.Description
			for _, target := range e.catalog.Skills {
				if target.QualifiedID == selected.SelectedIdentity {
					description = target.Description
					break
				}
			}
			rows = append(rows, SearchRow{d.QualifiedID, selected.SelectedIdentity, description, int64(len(selected.Snapshot.Body)), selected.ContentIdentity})
			if len(rows) == 100 {
				break
			}
		}
	}
	kind := "search_succeeded"
	if len(rows) == 0 {
		kind = "search_miss"
	}
	_, err = e.emit(Event{Kind: kind, Channel: channel})
	return rows, err
}
func (e *Engine) Acquire(id, channel string) (Result, error) {
	e.mu.Lock()
	defer e.mu.Unlock()
	unlock, err := e.lock()
	if err != nil {
		return Result{}, err
	}
	defer unlock()
	if channel != "cli" && channel != "mcp" && channel != "recovery_read" && channel != "preparation" {
		return Result{}, errors.New("ACQUIRE_INVALID_CHANNEL")
	}
	requested := ""
	if qualified.MatchString(id) {
		requested = id
	}
	kind := "requested"
	if channel == "preparation" {
		kind = "recovery_candidate"
	}
	request, err := e.emit(Event{Kind: kind, Channel: channel, Requested: requested})
	if err != nil {
		return Result{}, err
	}
	fail := func(code string) (Result, error) {
		_, writeErr := e.emit(Event{Kind: "rejected", AcquisitionID: request.EventID, Channel: channel, Diagnostic: code})
		if writeErr != nil {
			return Result{}, writeErr
		}
		return Result{}, errors.New(code)
	}
	if !qualified.MatchString(id) {
		return fail("ACQUIRE_QUALIFIED_ID_REQUIRED")
	}
	if !e.allowed(id) {
		return fail("ACQUIRE_ID_NOT_AUTHORIZED")
	}
	selected, err := skills.ResolveCatalog(e.config.Catalog, id, e.config.Consumer)
	if err != nil {
		return fail("ACQUIRE_SELECTION_UNAVAILABLE")
	}
	raw, err := json.Marshal(selected)
	if err != nil || len(raw) > MaxResultBytes {
		return fail("ACQUIRE_RESULT_TOO_LARGE")
	}
	events, err := e.events()
	if err != nil {
		return Result{}, err
	}
	repeat := false
	delivered := map[string]bool{}
	for _, event := range events {
		if event.Kind == "channel_delivered" {
			delivered[event.AcquisitionID] = true
		}
	}
	for _, event := range events {
		if event.Kind == "available" && delivered[event.EventID] && event.RunID == e.config.RunID && event.BindingID == e.config.BindingID && event.AttemptID == e.config.AttemptID && event.Selected == selected.SelectedIdentity {
			repeat = true
		}
	}
	snapshotID := sha256.Sum256(raw)
	location := "acquisitions/skills/" + hex.EncodeToString(snapshotID[:]) + "/" + selected.SelectedIdentity
	files := map[string][]byte{"SKILL.md": selected.Snapshot.Body}
	for name, data := range selected.Snapshot.Support {
		if name == "SKILL.md" || !fsPath(name) {
			return fail("ACQUIRE_UNSAFE_SUPPORT")
		}
		files[name] = data
	}
	names := make([]string, 0, len(files))
	for name := range files {
		names = append(names, name)
	}
	sort.Strings(names)
	additionalBytes, additionalEntries := 0, 0
	_, existsErr := e.root.Lstat(location)
	if os.IsNotExist(existsErr) {
		additionalEntries = 2
	}
	for _, name := range names {
		if _, err := e.root.Lstat(location + "/" + name); os.IsNotExist(err) {
			additionalBytes += len(files[name])
			additionalEntries += 1 + strings.Count(name, "/")
		}
	}
	if err = e.storeBudget(additionalBytes, additionalEntries); err != nil {
		return fail(err.Error())
	}
	if err = e.directory(location); err != nil {
		return fail("ACQUIRE_MATERIALIZATION_FAILED")
	}
	for _, name := range names {
		if parent := path.Dir(name); parent != "." {
			if err = e.directory(location + "/" + parent); err != nil {
				return fail("ACQUIRE_MATERIALIZATION_FAILED")
			}
		}
		if existing, readErr := ReadFile(e.root, location+"/"+name, MaxResultBytes); readErr == nil {
			if string(existing) != string(files[name]) {
				return fail("ACQUIRE_SNAPSHOT_CHANGED")
			}
			continue
		}
		if err = e.write(location+"/"+name, files[name]); err != nil {
			return fail("ACQUIRE_MATERIALIZATION_FAILED")
		}
	}
	if _, err = e.emit(Event{Kind: "materialized", AcquisitionID: request.EventID, Channel: channel, Requested: id, Selected: selected.SelectedIdentity, ContentIdentity: selected.ContentIdentity, MaterializedPath: location}); err != nil {
		return Result{}, err
	}
	event, err := e.emit(Event{Kind: "available", AcquisitionID: request.EventID, Channel: channel, Requested: id, Selected: selected.SelectedIdentity, ContentIdentity: selected.ContentIdentity, MaterializedPath: location, IsRepeatDelivery: repeat})
	return Result{event.EventID, selected, location, repeat}, err
}
func fsPath(name string) bool {
	return fs.ValidPath(name) && name != "." && !strings.Contains(name, "\\")
}

// Count retained and interrupted materialization before adding a new snapshot.
// This includes directories and never follows symlinks.
func (e *Engine) storeBudget(extraBytes, extraEntries int) error {
	bytes, entries := extraBytes, extraEntries
	return fs.WalkDir(e.root.FS(), "acquisitions/skills", func(_ string, d fs.DirEntry, err error) error {
		if err != nil {
			return errors.New("ACQUIRE_STORE_UNSAFE")
		}
		entries++
		info, err := d.Info()
		if err != nil || (!info.IsDir() && !info.Mode().IsRegular()) {
			return errors.New("ACQUIRE_STORE_UNSAFE")
		}
		if !info.IsDir() {
			bytes += int(info.Size())
		}
		if bytes > MaxStoreBytes || entries > MaxStoreEntries {
			return errors.New("ACQUIRE_STORE_LIMIT")
		}
		return nil
	})
}
func (e *Engine) allowed(id string) bool {
	if e.config.AllowedIDs == nil {
		return true
	}
	for _, allowed := range e.config.AllowedIDs {
		if allowed == id {
			return true
		}
	}
	return false
}

// Delivered is called only after the channel writer reports success. It appends
// a new observation, never upgrades an earlier record or claims model use.
func (e *Engine) Delivered(id, channel string, n int, payload ...[]byte) error {
	return e.deliveredPayload(Event{Kind: "channel_delivered", AcquisitionID: id, Channel: channel, ControlledBytes: n}, payload)
}

// ResponseDelivered records a successful non-acquisition response. A frame with
// an acquisition delivery uses Delivered instead; overlapping views never add.
// This boundary is server-to-client, including an APGR preflight client. A
// caller must distinguish preflight traffic from a provider evaluation session.
func (e *Engine) ResponseDelivered(channel, operation string, n int, payload ...[]byte) error {
	return e.responseDeliveredAt(channel, operation, "late", n, payload...)
}

func (e *Engine) responseDeliveredAt(channel, operation, phase string, n int, payload ...[]byte) error {
	if e.config.Preparation {
		return e.deliveredPayload(Event{Kind: "preparation_response", Channel: "preparation", Diagnostic: operation, ControlledBytes: n}, payload)
	}
	return e.deliveredPayload(Event{Kind: "response_delivered", Channel: channel, Diagnostic: operation, Phase: phase, ControlledBytes: n}, payload)
}

// Legacy count-only callers remain readable but cannot establish H coverage.
// The channel passes the actual completely written frame, including framing.
func (e *Engine) deliveredPayload(event Event, payload [][]byte) error {
	if len(payload) > 1 || (len(payload) == 1 && len(payload[0]) != event.ControlledBytes) {
		return errors.New("ACQUIRE_INVALID_MEASUREMENT")
	}
	if len(payload) == 1 {
		if !utf8.Valid(payload[0]) {
			return errors.New("ACQUIRE_INVALID_MEASUREMENT")
		}
		event.PayloadSHA256 = fmt.Sprintf("%x", sha256.Sum256(payload[0]))
		if event.Phase == "" {
			event.Phase = "late"
		}
		event.Provenance = "apgr-" + event.Channel + "-response-frame"
		event.ObservationKind = "complete_channel_write"
	}
	return e.delivered(event)
}

func (e *Engine) delivered(event Event) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	unlock, err := e.lock()
	if err != nil {
		return err
	}
	defer unlock()
	if event.ControlledBytes < 0 || event.ControlledBytes > MaxMessageBytes {
		return errors.New("ACQUIRE_INVALID_MEASUREMENT")
	}
	if event.Channel != "cli" && event.Channel != "mcp" && event.Channel != "recovery_read" && !(event.Channel == "preparation" && event.Kind == "preparation_response") {
		return errors.New("ACQUIRE_INVALID_CHANNEL")
	}
	_, err = e.emit(event)
	return err
}
func (e *Engine) lock() (func(), error) {
	f, err := e.root.OpenFile("acquisitions/.lock", os.O_CREATE|os.O_RDWR|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0600)
	if err != nil {
		return nil, errors.New("ACQUIRE_STORE_BUSY_OR_UNSAFE")
	}
	info, err := f.Stat()
	if err != nil || !info.Mode().IsRegular() {
		f.Close()
		return nil, errors.New("ACQUIRE_STORE_BUSY_OR_UNSAFE")
	}
	if err = syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		f.Close()
		return nil, errors.New("ACQUIRE_STORE_BUSY_OR_UNSAFE")
	}
	return func() { syscall.Flock(int(f.Fd()), syscall.LOCK_UN); f.Close() }, nil
}
func (e *Engine) Explain() (map[string]any, error) {
	e.mu.Lock()
	defer e.mu.Unlock()
	unlock, err := e.lock()
	if err != nil {
		return nil, err
	}
	defer unlock()
	events, err := e.events()
	if err != nil {
		return nil, err
	}
	scoped := []Event{}
	for _, event := range events {
		if event.RunID == e.config.RunID && event.BindingID == e.config.BindingID && event.AttemptID == e.config.AttemptID {
			scoped = append(scoped, event)
		}
	}
	value := map[string]any{"run_id": e.config.RunID, "binding_id": e.config.BindingID, "attempt_id": e.config.AttemptID, "context_plan": e.config.ContextPlan, "events": scoped, "diagnostics": e.diagnostics, "model_observed": nil, "tokens": nil}
	raw, _ := json.Marshal(value)
	if len(raw) > MaxResultBytes {
		return nil, errors.New("ACQUIRE_EXPLANATION_TOO_LARGE")
	}
	return value, nil
}
func (e *Engine) ContextURI() string {
	return "apgr://context/" + url.PathEscape(e.config.RunID) + "/" + url.PathEscape(e.config.BindingID)
}

// ReadFile rejects nonregular final entries and observes a bounded stable read.
func ReadFile(root *os.Root, name string, limit int) ([]byte, error) {
	before, err := root.Lstat(name)
	if err != nil || !before.Mode().IsRegular() || before.Size() > int64(limit) {
		return nil, errors.New("ACQUIRE_UNSAFE_INPUT")
	}
	f, err := root.OpenFile(name, os.O_RDONLY|syscall.O_NOFOLLOW|syscall.O_NONBLOCK, 0)
	if err != nil {
		return nil, errors.New("ACQUIRE_UNSAFE_INPUT")
	}
	defer f.Close()
	opened, err := f.Stat()
	if err != nil || !os.SameFile(before, opened) {
		return nil, errors.New("ACQUIRE_INPUT_CHANGED")
	}
	data, err := io.ReadAll(io.LimitReader(f, int64(limit)+1))
	if err != nil || len(data) > limit {
		return nil, errors.New("ACQUIRE_INPUT_TOO_LARGE")
	}
	after, err := f.Stat()
	entry, endErr := root.Lstat(name)
	if err != nil || endErr != nil || !os.SameFile(opened, entry) || opened.Size() != after.Size() || !opened.ModTime().Equal(after.ModTime()) || int64(len(data)) != after.Size() {
		return nil, errors.New("ACQUIRE_INPUT_CHANGED")
	}
	return data, nil
}
