"""Source-owned promotion fixture registry and structural validators."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import textwrap
from typing import Mapping


class PromotionOracleError(ValueError):
    """Raised when a source-owned promotion oracle cannot qualify."""


@dataclass(frozen=True)
class FixtureSpec:
    """One independent good/bad fixture pair."""

    case_id: str
    kind: str
    fixture_kind: str
    command: tuple[str, ...] | None
    good_files: Mapping[str, str]
    bad_files: Mapping[str, str]
    hidden_facts: tuple[str, ...]
    check_name: str
    runtime_requirements: tuple[str, ...] = ()
    attestation_report: str | None = None

    @property
    def implementation_paths(self) -> tuple[str, ...]:
        """Only these declared subject APIs may be substituted for test grading.

        Everything else, including absent configuration/support, belongs to the
        candidate. File extensions never confer implementation ownership.
        """
        return {
            "go-test-profile/positive/lifecycle": ("parse.go",),
            "go-test-profile/positive/false-pass": ("harness.go",),
            "go-test-profile/positive/parallel-isolation": ("isolation.go",),
            "pytest-test-profile/positive/collection": ("values.py",),
            "pytest-test-profile/positive/fixture-lifecycle": ("output_support.py",),
            "pytest-test-profile/positive/worker-isolation": ("isolation.py",),
        }.get(self.case_id, ())

    @property
    def skill_id(self) -> str:
        return self.case_id.split("/", 1)[0]

    @property
    def oracle_id(self) -> str:
        return f"{self.case_id}::source-oracle-v2"

    @property
    def hidden_oracle_files(self) -> Mapping[str, str]:
        """Return source-owned tests that are overlaid on later model output.

        These bytes are never taken from a model subject.  They are copied to
        an oracle-owned temporary evaluation directory under reserved names.
        Structural Markdown and non-trigger checks are represented by the
        source contract itself and therefore have an empty file overlay.
        """
        if self.fixture_kind != "command":
            return {}
        if self.case_id == "pytest-test-profile/positive/fixture-lifecycle":
            from .lifecycle_hidden import HIDDEN_TEST
            return {"test_output.py": HIDDEN_TEST}
        if self.command and self.command[0] == "go":
            names = lambda name: name.endswith("_test.go")
        elif self.command and self.command[0] == "python3":
            names = lambda name: (name.startswith("test_") or name.endswith("_test.py")
                                  or name.startswith("check_"))
        else:
            names = lambda name: False
        return {name: content for name, content in self.good_files.items() if names(name)}

    @property
    def hidden_oracle_sha256(self) -> str:
        payload = {
            "oracle_id": self.oracle_id,
            "fixture_kind": self.fixture_kind,
            "check_name": self.check_name,
            "files": dict(sorted(self.hidden_oracle_files.items())),
            "implementation_paths": list(self.implementation_paths),
            "facts": list(self.hidden_facts),
        }
        return hashlib.sha256((json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()


def _dedent(value: str) -> str:
    return textwrap.dedent(value).lstrip("\n")


def _go(case_id: str, files: Mapping[str, str], bad_files: Mapping[str, str], *facts: str) -> FixtureSpec:
    return FixtureSpec(case_id, "positive", "command", ("go", "test", "-count=1", "./..."),
                       dict(files), dict(bad_files), tuple(facts), "command_exit_and_assertions", ("go",))


def _go_race(case_id: str, files: Mapping[str, str], bad_files: Mapping[str, str], *facts: str) -> FixtureSpec:
    return FixtureSpec(case_id, "positive", "command", ("go", "test", "-race", "-count=1", "./..."),
                       dict(files), dict(bad_files), tuple(facts), "command_exit_and_assertions", ("go", "cc"))


def _pytest(case_id: str, files: Mapping[str, str], bad_files: Mapping[str, str], *facts: str) -> FixtureSpec:
    return FixtureSpec(case_id, "positive", "command", ("python3", "-m", "pytest", "-q"),
                       dict(files), dict(bad_files), tuple(facts), "command_exit_and_assertions",
                       ("python3", "pytest-module"))


def _unittest(case_id: str, files: Mapping[str, str], bad_files: Mapping[str, str], *facts: str) -> FixtureSpec:
    return FixtureSpec(case_id, "positive", "command", ("python3", "-m", "unittest", "discover", "-q"),
                       dict(files), dict(bad_files), tuple(facts), "command_exit_and_assertions",
                       ("python3", "sqlite3-module"))


def _static(case_id: str, kind: str, files: Mapping[str, str], bad_files: Mapping[str, str],
            check_name: str, *facts: str) -> FixtureSpec:
    return FixtureSpec(case_id, kind, "source_fact", None, dict(files), dict(bad_files), tuple(facts), check_name)


GO_MOD = "module example.invalid/apg-promotion\n\ngo 1.25\n"


_ORACLES: dict[str, FixtureSpec] = {
    "go-language-profile/positive/cancellation": _go(
        "go-language-profile/positive/cancellation",
        {
            "go.mod": GO_MOD,
            "fetch.go": _dedent('''
                package fetch

                import (
                    "context"
                    "fmt"
                    "io"
                    "net/http"
                )

                func Fetch(ctx context.Context, url string) ([]byte, error) {
                    request, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
                    if err != nil { return nil, err }
                    response, err := http.DefaultClient.Do(request)
                    if err != nil { return nil, err }
                    defer response.Body.Close()
                    if response.StatusCode >= http.StatusBadRequest {
                        return nil, fmt.Errorf("fetch %s: %s", url, response.Status)
                    }
                    return io.ReadAll(response.Body)
                }
            '''),
            "fetch_test.go": _dedent('''
                package fetch

                import (
                    "context"
                    "errors"
                    "net/http"
                    "net/http/httptest"
                    "testing"
                    "time"
                )

                func TestFetchCancellationAndSuccess(t *testing.T) {
                    server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
                        _, _ = w.Write([]byte("ok"))
                    }))
                    defer server.Close()
                    value, err := Fetch(context.Background(), server.URL)
                    if err != nil || string(value) != "ok" { t.Fatalf("success = %q, %v", value, err) }
                    ctx, cancel := context.WithCancel(context.Background())
                    cancel()
                    if _, err := Fetch(ctx, server.URL); !errors.Is(err, context.Canceled) {
                        t.Fatalf("cancellation error = %v", err)
                    }
                    expired, finish := context.WithDeadline(context.Background(), time.Now().Add(-time.Second)); defer finish()
                    if _, err := Fetch(expired, server.URL); !errors.Is(err, context.DeadlineExceeded) { t.Fatalf("deadline error = %v", err) }
                    entered := make(chan struct{}); release := make(chan struct{})
                    blocked := httptest.NewServer(http.HandlerFunc(func(_ http.ResponseWriter, request *http.Request) {
                        close(entered); select { case <-request.Context().Done(): case <-release: }
                    }))
                    defer blocked.Close(); defer close(release)
                    ctx, cancel = context.WithCancel(context.Background()); defer cancel()
                    done := make(chan error, 1)
                    go func(){ _, failure := Fetch(ctx, blocked.URL); done <- failure }()
                    select { case <-entered: case <-time.After(5*time.Second): t.Fatal("request never entered") }
                    cancel()
                    select { case failure := <-done: if !errors.Is(failure, context.Canceled) { t.Fatal(failure) }
                    case <-time.After(5*time.Second): t.Fatal("outstanding request ignored cancellation") }
                }
            '''),
        },
        {
            "go.mod": GO_MOD,
            "fetch.go": _dedent('''
                package fetch
                import "context"
                func Fetch(context.Context, string) ([]byte, error) { return []byte("ok"), nil }
            '''),
        },
        "cancellation_error_propagation", "context_ownership", "successful_bytes",
    ),
    "go-language-profile/positive/concurrency": _go_race(
        "go-language-profile/positive/concurrency",
        {
            "go.mod": GO_MOD,
            "map.go": _dedent('''
                package parallel

                import (
                    "context"
                    "fmt"
                    "sync"
                )

                func Map(ctx context.Context, values []int, workers int,
                    fn func(context.Context, int) (int, error)) ([]int, error) {
                    if workers < 1 { return nil, fmt.Errorf("workers must be positive") }
                    if err := ctx.Err(); err != nil { return nil, err }
                    result := make([]int, len(values))
                    jobs := make(chan int)
                    var group sync.WaitGroup
                    var once sync.Once
                    var first error
                    for worker := 0; worker < workers; worker++ {
                        group.Add(1)
                        go func() {
                            defer group.Done()
                            for index := range jobs {
                                value, err := fn(ctx, values[index])
                                if err != nil { once.Do(func() { first = err }); continue }
                                result[index] = value
                            }
                        }()
                    }
                    for index := range values {
                        select { case <-ctx.Done(): close(jobs); group.Wait(); return nil, ctx.Err()
                        case jobs <- index: }
                    }
                    close(jobs); group.Wait()
                    if first != nil { return nil, first }
                    return result, nil
                }
            '''),
            "map_test.go": _dedent('''
                package parallel
                import ("context"; "errors"; "sync/atomic"; "testing"; "time")
                func TestMapPreservesOrderAndCancellation(t *testing.T) {
                    entered := make(chan struct{}, 4); release := make(chan struct{})
                    done := make(chan struct{}); var values []int; var err error
                    var active, maximum int32
                    go func() {
                        values, err = Map(context.Background(), []int{1,2,3,4}, 2,
                            func(_ context.Context, value int) (int, error) {
                                current := atomic.AddInt32(&active, 1)
                                for { observed := atomic.LoadInt32(&maximum); if current <= observed || atomic.CompareAndSwapInt32(&maximum, observed, current) { break } }
                                entered <- struct{}{}; <-release
                                atomic.AddInt32(&active, -1); return value * 2, nil
                            })
                        close(done)
                    }()
                    timer := time.NewTimer(5*time.Second); defer timer.Stop()
                    for i := 0; i < 2; i++ {
                        select { case <-entered: case <-timer.C: close(release); <-done; t.Fatal("two workers never entered") }
                    }
                    close(release); <-done
                    if err != nil || len(values) != 4 { t.Fatal(values, err) }
                    for i, want := range []int{2,4,6,8} { if values[i] != want { t.Fatal(values) } }
                    if maximum != 2 { t.Fatalf("maximum concurrent workers = %d", maximum) }
                    ctx, cancel := context.WithCancel(context.Background()); cancel()
                    _, err = Map(ctx, []int{1}, 1, func(context.Context, int) (int, error) { return 1, nil })
                    if !errors.Is(err, context.Canceled) { t.Fatalf("cancel error = %v", err) }
                    ctx, cancel = context.WithCancel(context.Background())
                    started := make(chan struct{}); stopped := make(chan error, 1)
                    go func() { _, failure := Map(ctx, []int{1,2,3}, 1, func(ctx context.Context, _ int)(int,error) {
                        select { case <-started: default: close(started) }; <-ctx.Done(); return 0, ctx.Err()
                    }); stopped <- failure }()
                    <-started; cancel()
                    select { case failure := <-stopped: if !errors.Is(failure, context.Canceled) { t.Fatal(failure) }
                    case <-time.After(5*time.Second): t.Fatal("cancellation did not finish") }
                    expected := errors.New("callback failed")
                    _, err = Map(context.Background(), []int{1}, 1, func(context.Context,int)(int,error){ return 0, expected })
                    if !errors.Is(err, expected) { t.Fatal(err) }
                }
            '''),
        },
        {
            "go.mod": GO_MOD,
            "map.go": _dedent('''
                package parallel
                import "context"
                func Map(_ context.Context, values []int, _ int,
                    fn func(context.Context, int) (int, error)) ([]int, error) {
                    result := make([]int, 0, len(values))
                    for _, value := range values { output, err := fn(context.Background(), value); if err != nil { return nil, err }; result = append(result, output) }
                    return result, nil
                }
            '''),
        },
        "ordered_results", "bounded_workers", "cancellation_propagation",
    ),
    "go-language-profile/positive/api-resources": _go(
        "go-language-profile/positive/api-resources",
        {
            "go.mod": GO_MOD,
            "copy.go": _dedent('''
                package copyfile
                import ("io"; "os")
                func CopyFile(src, dst string) error {
                    input, err := os.Open(src); if err != nil { return err }; defer input.Close()
                    output, err := os.Create(dst); if err != nil { return err }
                    if _, err = io.Copy(output, input); err != nil { output.Close(); return err }
                    return output.Close()
                }
            '''),
            "copy_test.go": _dedent('''
                package copyfile
                import ("os"; "path/filepath"; "testing")
                func TestCopyFileAndDestinationFailure(t *testing.T) {
                    root := t.TempDir(); source := filepath.Join(root, "source"); destination := filepath.Join(root, "out")
                    if err := os.WriteFile(source, []byte("payload"), 0600); err != nil { t.Fatal(err) }
                    if err := CopyFile(source, destination); err != nil { t.Fatal(err) }
                    bytes, err := os.ReadFile(destination); if err != nil || string(bytes) != "payload" { t.Fatal(string(bytes), err) }
                    if err := os.WriteFile(destination, []byte("longer previous contents"), 0600); err != nil { t.Fatal(err) }
                    copyErr := CopyFile(source, destination)
                    bytes, err = os.ReadFile(destination); if err != nil { t.Fatal(err) }
                    if copyErr == nil && string(bytes) != "payload" { t.Fatal("silent corruption", string(bytes)) }
                    if copyErr != nil && string(bytes) != "longer previous contents" { t.Fatal("refusal changed destination") }
                    if err := os.WriteFile(destination, []byte("preserve on missing source"), 0600); err != nil { t.Fatal(err) }
                    if err := CopyFile(filepath.Join(root, "missing"), destination); err == nil { t.Fatal("missing source accepted") }
                    bytes, err = os.ReadFile(destination); if err != nil || string(bytes) != "preserve on missing source" { t.Fatal("missing source changed destination", err) }
                }
            '''),
        },
        {
            "go.mod": GO_MOD,
            "copy.go": _dedent('''
                package copyfile
                func CopyFile(_, _ string) error { return nil }
            '''),
        },
        "resource_close", "destination_behavior", "error_propagation",
    ),
    "go-test-profile/positive/lifecycle": _go(
        "go-test-profile/positive/lifecycle",
        {
            "go.mod": GO_MOD,
            "parse.go": _dedent('''
                package parsing
                import "strconv"
                func Parse(value string) (int, error) { return strconv.Atoi(value) }
            '''),
            "parse_test.go": _dedent('''
                package parsing
                import "testing"
                func TestParseValidAndMalformed(t *testing.T) {
                    value, err := Parse("12"); if err != nil || value != 12 { t.Fatal(value, err) }
                    if _, err := Parse("bad"); err == nil { t.Fatal("malformed input accepted") }
                }
            '''),
        },
        {
            "go.mod": GO_MOD,
            "parse.go": _dedent('''
                package parsing
                import "strconv"
                func Parse(value string) (int, error) { parsed, _ := strconv.Atoi(value); return parsed, nil }
            '''),
        },
        "malformed_input_error", "valid_result", "test_failure_visibility",
    ),
    "go-test-profile/positive/false-pass": _go(
        "go-test-profile/positive/false-pass",
        {
            "go.mod": GO_MOD,
            "harness.go": _dedent('''
                package harness
                func Check(value int) bool { return value >= 0 }
            '''),
            "harness_test.go": _dedent('''
                package harness
                import "testing"
                func TestCheckReportsFailure(t *testing.T) {
                    if !Check(4) { t.Fatal("valid check failed") }
                    if Check(-1) { t.Fatal("invalid check passed") }
                }
            '''),
        },
        {
            "go.mod": GO_MOD,
            "harness.go": _dedent('''
                package harness
                func Check(_ int) bool { return true }
            '''),
        },
        "negative_result", "assertion_failure", "normal_result",
    ),
    "go-test-profile/positive/parallel-isolation": _go_race(
        "go-test-profile/positive/parallel-isolation",
        {
            "go.mod": GO_MOD,
            "isolation.go": _dedent('''
                package files
                import ("os"; "path/filepath")
                func WriteCheck(root, name, value string) error { return os.WriteFile(filepath.Join(root, name), []byte(value), 0600) }
            '''),
            "files.go": _dedent('''
                package files
                // The visible subject supplies this API; this source-owned
                // implementation is retained solely for authored-test grading.
            '''),
            "files_test.go": _dedent('''
                package files
                import ("os"; "path/filepath"; "testing")
                func TestA(t *testing.T) { t.Parallel(); root := t.TempDir(); if err := WriteCheck(root, "a", "one"); err != nil { t.Fatal(err) }; data, err := os.ReadFile(filepath.Join(root, "a")); if err != nil || string(data) != "one" { t.Fatal(string(data), err) } }
                func TestB(t *testing.T) { t.Parallel(); root := t.TempDir(); if err := WriteCheck(root, "b", "two"); err != nil { t.Fatal(err) }; data, err := os.ReadFile(filepath.Join(root, "b")); if err != nil || string(data) != "two" { t.Fatal(string(data), err) } }
            '''),
        },
        {
            "go.mod": GO_MOD,
            "isolation.go": _dedent('''
                package files
                import "os"
                func WriteCheck(_, _ , value string) error { return os.WriteFile("counter", []byte(value), 0600) }
            '''),
            "files.go": _dedent('''
                package files
                // The visible subject supplies this API; this source-owned
                // implementation is retained solely for authored-test grading.
            '''),
        },
        "per_test_destination", "parallel_safe_writes", "race_clean",
    ),
    "pytest-test-profile/positive/collection": _pytest(
        "pytest-test-profile/positive/collection",
        {
            "pytest.ini": "[pytest]\npython_files = check_*.py\n",
            "values.py": "def normalize(values):\n    return [value.strip().lower() for value in values]\n",
            "check_values.py": "from values import normalize\n\ndef test_value_normalizes_mixed_input():\n    assert normalize([' Alpha ', 'BETA']) == ['alpha', 'beta']\n\ndef test_empty_input_is_stable():\n    assert normalize([]) == []\n",
        },
        {
            "pytest.ini": "[pytest]\npython_files = check_*.py\n",
            "values.py": "def normalize(values):\n    return list(values)\n",
        },
        "collection_contract", "broken_check_is_visible", "strict_config",
    ),
    "pytest-test-profile/positive/fixture-lifecycle": _pytest(
        "pytest-test-profile/positive/fixture-lifecycle",
        {
            "conftest.py": "from output_support import output, root\n",
            "output_support.py": _dedent('''
                import pytest

                @pytest.fixture(scope="session")
                def root(tmp_path_factory):
                    return tmp_path_factory.mktemp("outputs")

                @pytest.fixture
                def output(root):
                    path = root / "output.txt"
                    yield path
                    if path.exists():
                        path.unlink()
            '''),
            "test_output.py": _dedent('''
                def test_write(output):
                    output.write_text("first")
                    assert output.read_text() == "first"

                def test_is_clean(output):
                    assert not output.exists()
                    output.write_text("second")

                import pytest
                @pytest.mark.xfail(strict=True, reason="exercise teardown after failure")
                def test_failing_writer(output):
                    output.write_text("failed")
                    assert False

                def test_after_failure(output):
                    assert not output.exists()
            '''),
        },
        {
            "conftest.py": "from output_support import output, root\n",
            "output_support.py": _dedent('''
                import pytest
                @pytest.fixture(scope="session")
                def root(tmp_path_factory):
                    return tmp_path_factory.mktemp("outputs")
                @pytest.fixture(scope="session")
                def output(tmp_path_factory):
                    return tmp_path_factory.mktemp("outputs") / "output.txt"
            '''),
        },
        "function_cleanup", "failure_safe_teardown", "independent_results",
    ),
    "pytest-test-profile/positive/worker-isolation": _pytest(
        "pytest-test-profile/positive/worker-isolation",
        {
            "pytest.ini": "[pytest]\naddopts = -q\n",
            "isolation.py": _dedent('''
                from pathlib import Path

                def write_value(root, name, value):
                    path = Path(root) / name
                    path.write_text(value)
                    return path.read_text()
            '''),
            "test_counter.py": _dedent('''
                from concurrent.futures import ThreadPoolExecutor
                from isolation import write_value

                def test_one(tmp_path):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        futures = [pool.submit(write_value, tmp_path, name, name) for name in ("one", "two")]
                        assert [future.result() for future in futures] == ["one", "two"]

                def test_two(tmp_path):
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        assert pool.submit(write_value, tmp_path, "two", "two").result() == "two"
            '''),
        },
        {
            "pytest.ini": "[pytest]\naddopts = -q\n",
            "isolation.py": _dedent('''
                from pathlib import Path

                def write_value(root, name, value):
                    Path("counter").write_text(value)
                    return (Path(root) / name).read_text()
            '''),
        },
        "worker_local_namespace", "concurrent_isolation", "no_unbound_xdist",
    ),
    "sqlite-database-profile/positive/transactions": _unittest(
        "sqlite-database-profile/positive/transactions",
        {
            "transfer.py": _dedent('''
                import sqlite3

                def transfer(connection, source, target, amount):
                    if amount < 0 or source == target:
                        raise ValueError("invalid transfer")
                    with connection:
                        row = connection.execute("SELECT balance FROM accounts WHERE id = ?", (source,)).fetchone()
                        target_row = connection.execute("SELECT balance FROM accounts WHERE id = ?", (target,)).fetchone()
                        if row is None or target_row is None or row[0] < amount:
                            raise ValueError("insufficient funds")
                        connection.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, source))
                        connection.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, target))
            '''),
            "test_transfer.py": _dedent('''
                import sqlite3
                import unittest
                from transfer import transfer

                class TransferTests(unittest.TestCase):
                    def setUp(self):
                        self.db = sqlite3.connect(":memory:")
                        self.db.execute("CREATE TABLE accounts(id INTEGER PRIMARY KEY, balance INTEGER NOT NULL CHECK(balance >= 0))")
                        self.db.executemany("INSERT INTO accounts VALUES (?, ?)", [(1, 100), (2, 0)])
                        self.db.commit()

                    def test_success_and_rollback(self):
                        outcome = transfer(self.db, 1, 2, 40)
                        self.assertTrue(outcome is None or outcome is True, "success must not report refusal")
                        self.assertEqual(self.db.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall(), [(1, 60), (2, 40)])
                        for args in ((1, 2, 1000), (1, 99, 10), (99, 2, 10), (1, 2, -1), (1, 1, 10)):
                            before = self.db.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall()
                            try:
                                outcome = transfer(self.db, *args)
                            except Exception:
                                outcome = False
                            self.assertIs(outcome, False, "invalid request must raise or return False")
                            self.assertEqual(self.db.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall(), before)
                        with self.assertRaises(sqlite3.IntegrityError):
                            self.db.execute("UPDATE accounts SET balance=-1 WHERE id=1")
                        self.db.rollback()
                        transfer(self.db, 2, 1, 10)
                        self.assertEqual(self.db.execute("SELECT id, balance FROM accounts ORDER BY id").fetchall(), [(1, 70), (2, 30)])
            '''),
        },
        {
            "transfer.py": _dedent('''
                def transfer(connection, source, target, amount):
                    if amount > 100:
                        connection.execute("UPDATE accounts SET balance = balance - 40 WHERE id = ?", (source,))
                        return
                    connection.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, source))
                    connection.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, target))
            '''),
        },
        "atomic_transfer", "state_unchanged_on_failure", "constraint_preservation",
    ),
    "sqlite-database-profile/positive/writer-wal": _unittest(
        "sqlite-database-profile/positive/writer-wal",
        {
            "exercise.py": _dedent('''
                import sqlite3

                def open_database(path):
                    return sqlite3.connect(path, timeout=0.2)
            '''),
            "test_store.py": _dedent('''
                import sqlite3
                import tempfile
                import unittest
                from exercise import open_database
                import time

                class StoreTests(unittest.TestCase):
                    def test_local_path_and_bounded_contention(self):
                        with tempfile.TemporaryDirectory() as directory:
                            path = directory + "/events.db"
                            first = open_database(path)
                            self.assertEqual(first.execute("PRAGMA database_list").fetchone()[2], path)
                            first.execute("CREATE TABLE events(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
                            first.execute("INSERT INTO events(value) VALUES ('baseline')")
                            first.commit()
                            second = open_database(path)
                            self.assertEqual(second.execute("PRAGMA database_list").fetchone()[2], path)
                            self.assertEqual(second.execute("SELECT value FROM events").fetchall(), [("baseline",)])
                            first.execute("BEGIN IMMEDIATE")
                            first.execute("INSERT INTO events(value) VALUES ('held')")
                            started = time.monotonic()
                            try:
                                second.execute("INSERT INTO events(value) VALUES ('contended')")
                                second.commit()
                                outcome = "committed"
                            except sqlite3.OperationalError as error:
                                self.assertIn(error.sqlite_errorcode & 255, (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED))
                                outcome = "unavailable"
                            self.assertLess(time.monotonic() - started, 6.0)
                            self.assertEqual(outcome, "unavailable")
                            first.rollback()
                            second.rollback()
                            second.execute("INSERT INTO events(value) VALUES ('after')")
                            second.commit()
                            second.close()
                            first.close()
                            reopened = sqlite3.connect(path)
                            self.assertEqual(reopened.execute("SELECT value FROM events ORDER BY id").fetchall(), [("baseline",), ("after",)])
                            reopened.close()
            '''),
        },
        {
            "exercise.py": _dedent('''
                import sqlite3
                def open_database(path):
                    return sqlite3.connect(":memory:")
            '''),
        },
        "observable_contention_policy", "local_database_path", "disposable_database",
    ),
    "sqlite-database-profile/positive/rebuild-integrity": _unittest(
        "sqlite-database-profile/positive/rebuild-integrity",
        {
            "migrate.py": _dedent('''
                def migrate(connection):
                    with connection:
                        connection.execute("CREATE INDEX IF NOT EXISTS children_parent_idx ON children(parent_id)")
                        connection.execute("PRAGMA foreign_key_check")
            '''),
            "test_migrate.py": _dedent('''
                import sqlite3
                import unittest
                from migrate import migrate

                class MigrationTests(unittest.TestCase):
                    def test_existing_rows_and_foreign_keys_survive(self):
                        db = sqlite3.connect(":memory:")
                        db.execute("PRAGMA foreign_keys=ON")
                        db.execute("CREATE TABLE parents(id INTEGER PRIMARY KEY)")
                        db.execute("CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id))")
                        db.execute("INSERT INTO parents VALUES (1)")
                        db.execute("INSERT INTO children VALUES (1, 1)")
                        db.commit()
                        migrate(db)
                        self.assertEqual(db.execute("SELECT count(*) FROM parents").fetchone()[0], 1)
                        self.assertEqual(db.execute("SELECT count(*) FROM children").fetchone()[0], 1)
                        self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                        self.assertEqual(db.execute("PRAGMA index_info(children_parent_idx)").fetchall(), [(0, 1, "parent_id")])
                        self.assertEqual(db.execute("SELECT * FROM children").fetchall(), [(1, 1)])
                        self.assertEqual(db.execute("SELECT * FROM parents").fetchall(), [(1,)])
                        self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone(), (1,))
                        db.commit()
                        with self.assertRaises(sqlite3.IntegrityError):
                            db.execute("INSERT INTO children VALUES (2, 99)")
                        db.rollback()
                        db.execute("INSERT INTO children VALUES (2, 1)")
                        db.commit()
                        migrate(db)
                        self.assertEqual(db.execute("SELECT * FROM children ORDER BY id").fetchall(), [(1, 1), (2, 1)])


                    def test_denied_change_is_recoverable(self):
                        db = sqlite3.connect(":memory:")
                        db.execute("PRAGMA foreign_keys=ON")
                        db.executescript("CREATE TABLE parents(id INTEGER PRIMARY KEY); CREATE TABLE children(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id)); INSERT INTO parents VALUES(1); INSERT INTO children VALUES(1,1);")
                        db.commit()
                        db.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_CREATE_INDEX else sqlite3.SQLITE_OK)
                        try:
                            outcome = migrate(db)
                        except Exception:
                            outcome = False
                        self.assertIs(outcome, False, "denied migration must report failure")
                        db.rollback()
                        db.set_authorizer(None)
                        self.assertEqual(db.execute("SELECT * FROM parents").fetchall(), [(1,)])
                        self.assertEqual(db.execute("SELECT * FROM children").fetchall(), [(1, 1)])
                        self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                        migrate(db)
                        self.assertEqual(db.execute("PRAGMA index_info(children_parent_idx)").fetchall(), [(0, 1, "parent_id")])
                        self.assertEqual(db.execute("SELECT * FROM parents").fetchall(), [(1,)])
                        self.assertEqual(db.execute("SELECT * FROM children").fetchall(), [(1, 1)])
                        self.assertEqual(db.execute("PRAGMA foreign_keys").fetchone(), (1,))
                        self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            '''),
        },
        {
            "migrate.py": _dedent('''
                def migrate(connection):
                    connection.execute("DROP TABLE parents")
            '''),
        },
        "foreign_key_integrity", "existing_rows", "recoverable_change",
    ),
    "markdown-language-profile/positive/nested-blocks": _static(
        "markdown-language-profile/positive/nested-blocks", "positive",
        {"README.md": _dedent('''
            1. Prepare
               - first item
               - second item

               ```sh
               echo ready
               ```

            2. Finish
        ''')},
        {"README.md": "1. Prepare\n- first item\n- second item\n```sh\necho ready\n```\n2. Finish\n"},
        "markdown_nested_structure", "ordered_list_nesting", "fenced_code_scope",
    ),
    "markdown-language-profile/positive/links": _static(
        "markdown-language-profile/positive/links", "positive",
        {"README.md": "# Guide\n\n[Setup](setup.md#installation)\n[Next](next.md)\n",
         "setup.md": "# Setup\n\n## Installation\n\nRun the documented command.\n",
         "next.md": "# Next\n"},
        {"README.md": "# Guide\n\n[Setup](setup.md#installation)\n[Next](missing.md)\n",
         "setup.md": "# Setup\n\n## Install\n"},
        "markdown_links", "local_destination_exists", "fragment_heading_exists",
    ),
    "markdown-language-profile/positive/code-literals": _static(
        "markdown-language-profile/positive/code-literals", "positive",
        {"README.md": "# Examples\n\n````markdown\n```python\nprint(\"literal\")\n```\n````\n"},
        {"README.md": "# Examples\n\n```markdown\n```python\nprint(\"literal\")\n```\n```\n"},
        "markdown_code_literals", "outer_fence_contains_inner", "literal_source_preserved",
    ),
    'go-language-profile/non-trigger/go-test-only': _static(
        'go-language-profile/non-trigger/go-test-only', "non-trigger",
        {'x_test.go': 'package example\nimport "testing"\nfunc TestExample(t *testing.T) {}\n'},
        {'x_test.go': 'package example\nimport "testing"\nfunc TestOne(t *testing.T) {}\n'},
        'neighbor_go_test_only', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'go-language-profile/non-trigger/non-go': _static(
        'go-language-profile/non-trigger/non-go', "non-trigger",
        {'x.py': '"""Example."""\n'},
        {'x.py': '"""Exampel."""\n'},
        'neighbor_non_go', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'go-test-profile/non-trigger/production-go': _static(
        'go-test-profile/non-trigger/production-go', "non-trigger",
        {'x.go': 'package example\nfunc Name() string { return "sample" }\n'},
        {'x.go': 'package example\nfunc Name() string { return "example" }\n'},
        'neighbor_production_go', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'go-test-profile/non-trigger/foreign-tests': _static(
        'go-test-profile/non-trigger/foreign-tests', "non-trigger",
        {'test_x.py': 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self): self.assertEqual(2 + 2, 4)\n'},
        {'test_x.py': 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self): self.assertEqual(2 + 2, 5)\n'},
        'neighbor_foreign_runner', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'pytest-test-profile/non-trigger/bats': _static(
        'pytest-test-profile/non-trigger/bats', "non-trigger",
        {'x.bats': '@test "false" {\n  run false\n  [ "$status" -eq 1 ]\n}\n'},
        {'x.bats': '@test "false" {\n  run false\n  [ "$status" -eq 0 ]\n}\n'},
        'neighbor_bats', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'pytest-test-profile/non-trigger/unittest': _static(
        'pytest-test-profile/non-trigger/unittest', "non-trigger",
        {'test_x.py': 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self): self.assertEqual(2 + 2, 4)\n'},
        {'test_x.py': 'import unittest\nclass T(unittest.TestCase):\n    def test_x(self): self.assertEqual(2 + 2, 5)\n'},
        'neighbor_unittest', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'markdown-language-profile/non-trigger/mdx': _static(
        'markdown-language-profile/non-trigger/mdx', "non-trigger",
        {'x.mdx': 'export const Count = 3\n\n<Widget value={Count} />\n'},
        {'x.mdx': 'export const Count = 2\n\n<Widget value={Count} />\n'},
        'neighbor_mdx', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'markdown-language-profile/non-trigger/frontmatter': _static(
        'markdown-language-profile/non-trigger/frontmatter', "non-trigger",
        {'x.md': '---\ntitle: Example\ntags: [one, two, three]\n---\n\n# Example\n', 'json.md': '---\n{"title": "Example", "tags": ["one", "two", "three"]}\n---\n\n# JSON Example\n'},
        {'x.md': '---\ntitle: Example\ntags: [one, two]\n---\n\n# Example\n', 'json.md': '---\n{"title": "Example", "tags": ["one", "two"]}\n---\n\n# JSON Example\n'},
        'neighbor_frontmatter', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'sqlite-database-profile/non-trigger/postgresql': _static(
        'sqlite-database-profile/non-trigger/postgresql', "non-trigger",
        {'query.sql': 'SELECT pg_advisory_xact_lock(43);\n'},
        {'query.sql': 'SELECT pg_advisory_xact_lock(42);\n'},
        'neighbor_postgresql', "requested_neighbor_edit_with_preserved_surroundings",
    ),
    'sqlite-database-profile/non-trigger/generic-sql': _static(
        'sqlite-database-profile/non-trigger/generic-sql', "non-trigger",
        {'query.sql': 'SELECT name FROM people WHERE active = 0;\n'},
        {'query.sql': 'SELECT name FROM people WHERE active = 1;\n'},
        'neighbor_generic_sql', "requested_neighbor_edit_with_preserved_surroundings",
    ),

}


def _markdown_nested(files: Mapping[str, str]) -> bool:
    """Validate the frozen list meaning with flexible markers and spacing."""
    lines = files.get("README.md", "").strip("\n").splitlines()
    if not lines:
        return False
    first = re.fullmatch(r"( {0,3})1[.)] +Prepare\s*", lines[0])
    if first is None:
        return False
    content_column = lines[0].index("Prepare")
    index = 1

    def skip_blanks(position):
        while position < len(lines) and not lines[position].strip():
            position += 1
        return position

    for wording in ("first item", "second item"):
        index = skip_blanks(index)
        if index >= len(lines):
            return False
        bullet = re.fullmatch(r"( *)[-*+] +(.+?)\s*", lines[index])
        if (bullet is None or bullet[2] != wording
                or not content_column <= len(bullet[1]) <= content_column + 3):
            return False
        index += 1
    index = skip_blanks(index)
    if index >= len(lines):
        return False
    opening = re.fullmatch(r"( *)(`{3,}|~{3,})([^`]*)", lines[index])
    if opening is None or not content_column <= len(opening[1]) <= content_column + 3:
        return False
    fence = opening[2]
    index += 1
    body = []
    while index < len(lines):
        closing = re.fullmatch(r"( *)(`{3,}|~{3,})\s*", lines[index])
        if (closing and closing[2][0] == fence[0] and len(closing[2]) >= len(fence)
                and content_column <= len(closing[1]) <= content_column + 3):
            break
        if lines[index].strip() and len(lines[index]) - len(lines[index].lstrip()) < content_column:
            return False
        body.append(lines[index].strip())
        index += 1
    if index >= len(lines) or "\n".join(body).strip() != "echo ready":
        return False
    index = skip_blanks(index + 1)
    return (index == len(lines) - 1
            and bool(re.fullmatch(r" {0,3}[12][.)] +Finish\s*", lines[index])))


def _markdown_links(files: Mapping[str, str]) -> bool:
    text = files["README.md"]
    for target in re.findall(r"\[[^]]+\]\(([^)]+)\)", text):
        path, _, fragment = target.partition("#")
        if path and path not in files:
            return False
        if fragment:
            if not path or path not in files:
                return False
            headings = set()
            for line in files[path].splitlines():
                heading = re.fullmatch(r" {0,3}#{1,6}[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*", line)
                if heading:
                    text = re.sub(r"[^\w -]", "", heading[1].strip().lower())
                    headings.add(text.replace(" ", "-"))
            if fragment.lower() not in headings:
                return False
    return True


def _markdown_code_literals(files: Mapping[str, str]) -> bool:
    """Keep the visible literal bytes within any valid enclosing fence."""
    lines = files.get("README.md", "").splitlines()
    for index, line in enumerate(lines):
        opening = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", line)
        if opening is None:
            continue
        fence, info = opening.groups()
        if fence[0] == "`" and "`" in info:
            continue
        for end in range(index + 1, len(lines)):
            closing = re.fullmatch(r" {0,3}(`{3,}|~{3,}) *", lines[end])
            if closing and closing[1][0] == fence[0] and len(closing[1]) >= len(fence):
                body = "\n".join(lines[index + 1:end])
                return ("\n".join(lines[:index]).strip() == "# Examples"
                        and body == '```python\nprint("literal")\n```'
                        and not "\n".join(lines[end + 1:]).strip())
    return False


def _nontrigger(files: Mapping[str, str], case_id: str) -> bool:
    """Grade the visible, deliberately bounded edit, not domain membership.

    Prompts require one concrete replacement and preservation of all other
    content. Only line endings and trailing whitespace are immaterial. This
    correctness observation never proves semantic non-use of target guidance.
    """
    def normalized(text):
        return "\n".join(line.rstrip(" \t") for line in text.replace("\r\n", "\n").split("\n")).rstrip("\n")

    expected = _ORACLES[case_id].good_files
    return (set(files) == set(expected)
            and all(normalized(files[name]) == normalized(text)
                    for name, text in expected.items()))


def _source_check(spec: FixtureSpec, files: Mapping[str, str]) -> bool:
    if spec.check_name == "markdown_nested_structure":
        return _markdown_nested(files)
    if spec.check_name == "markdown_links":
        return _markdown_links(files)
    if spec.check_name == "markdown_code_literals":
        return _markdown_code_literals(files)
    if spec.kind == "non-trigger":
        return _nontrigger(files, spec.case_id)
    raise PromotionOracleError(f"unknown source fixture check {spec.check_name}")


ORACLES = _ORACLES
source_check = _source_check
