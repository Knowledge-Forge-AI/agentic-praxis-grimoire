package cli

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestMain(main *testing.M) {
	if os.Getenv("APG_ENV_CLI_HELPER") == "17" {
		os.Exit(17)
	}
	if os.Getenv("APG_ENV_CLI_HELPER") == "1" {
		if len(os.Args) != 4 || os.Args[1] != "apg-env-child" || os.Args[2] != "$(echo must-not-run)" || os.Args[3] != "argument with spaces" {
			os.Exit(91)
		}
		if os.Getenv("APG_ENV_CLI_VALUE") != "child-value" {
			os.Exit(92)
		}
		fmt.Fprint(os.Stdout, "child-ok\n")
		os.Exit(0)
	}
	os.Exit(main.Run())
}

func TestEnvProfileCheckSnapshotAndValuesSafeShow(t *testing.T) {
	profile, storage := writeEnvironmentCLIProfile(t)
	t.Setenv("APG_ENV_CLI_HELPER", "0")
	t.Setenv("APG_ENV_CLI_VALUE", "secret-value-must-not-appear")
	if exit, _, _ := runTest(t, context.Background(), "env", "show", "--profile-id", "cli-test", "--storage-root", storage); exit != 2 {
		t.Fatalf("profile-id-only show exit = %d", exit)
	}
	if exit, _, _ := runTest(t, context.Background(), "env", "profile-check", "--profile", profile, "--context", "not-allowed"); exit != 2 {
		t.Fatalf("profile-check context exit = %d", exit)
	}

	if exit, _, _ := runTest(t, context.Background(), "env", "profile-check", "--profile", profile, "--mode", "overlay"); exit != 2 {
		t.Fatalf("profile-check misplaced mode exit = %d", exit)
	}
	if exit, _, _ := runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage, "--context", "test", "--mode", "overlay"); exit != 2 {
		t.Fatalf("snapshot misplaced mode exit = %d", exit)
	}
	if exit, _, _ := runTest(t, context.Background(), "env", "show", "--profile", profile, "--storage-root", storage, "--mode", "overlay"); exit != 2 {
		t.Fatalf("show misplaced mode exit = %d", exit)
	}

	exit, stdout, stderr := runTest(t, context.Background(), "env", "profile-check", "--profile", profile, "--json")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, `"profile_id":"cli-test"`) {
		t.Fatalf("profile-check = %d %q %q", exit, stdout, stderr)
	}
	if strings.Contains(stdout, "secret-value-must-not-appear") {
		t.Fatal("profile-check exposed an environment value")
	}
	if exit, _, _ := runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage); exit != 2 {
		t.Fatalf("missing snapshot context exit = %d", exit)
	}
	if exit, _, _ := runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage, "--context", "one", "--context", "two"); exit != 2 {
		t.Fatalf("duplicate snapshot context exit = %d", exit)
	}

	exit, stdout, stderr = runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage, "--context", "focused-test", "--json")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, `"disposition":"stored"`) {
		t.Fatalf("snapshot = %d %q %q", exit, stdout, stderr)
	}
	if strings.Contains(stdout, "secret-value-must-not-appear") {
		t.Fatal("snapshot exposed an environment value")
	}

	exit, stdout, stderr = runTest(t, context.Background(), "env", "show", "--profile", profile, "--storage-root", storage, "--json")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "APG_ENV_CLI_VALUE") {
		t.Fatalf("safe show = %d %q %q", exit, stdout, stderr)
	}
	if strings.Contains(stdout, "secret-value-must-not-appear") {
		t.Fatal("default show exposed an environment value")
	}

	exit, stdout, stderr = runTest(t, context.Background(), "env", "show", "--profile", profile, "--storage-root", storage, "--with-values", "--json")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, "secret-value-must-not-appear") {
		t.Fatalf("deliberate value show = %d %q %q", exit, stdout, stderr)
	}
}

func TestEnvResolveIsolatedAndOverlayPrecedence(t *testing.T) {
	profile, storage := writeEnvironmentCLIProfile(t)
	t.Setenv("APG_ENV_CLI_HELPER", "0")
	t.Setenv("APG_ENV_CLI_VALUE", "snapshot-value")
	if exit, _, stderr := runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage, "--context", "resolve-test"); exit != 0 {
		t.Fatalf("snapshot exit = %d (%s)", exit, stderr)
	}
	t.Setenv("APG_ENV_CLI_BASE", "base-only")

	exit, stdout, stderr := runTest(t, context.Background(), "env", "resolve", "--profile", profile, "--storage-root", storage, "--override", "APG_ENV_CLI_VALUE=override-value", "--with-values", "--json")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, `"mode":"isolated"`) || !strings.Contains(stdout, "override-value") {
		t.Fatalf("isolated = %d %q %q", exit, stdout, stderr)
	}
	if strings.Contains(stdout, "base-only") {
		t.Fatal("isolated resolution included the inherited base")
	}

	exit, stdout, stderr = runTest(t, context.Background(), "env", "resolve", "--profile", profile, "--storage-root", storage, "--mode", "overlay", "--with-values", "--json")
	if exit != 0 || stderr != "" || !strings.Contains(stdout, `"mode":"overlay"`) || !strings.Contains(stdout, "snapshot-value") {
		t.Fatalf("overlay = %d %q %q", exit, stdout, stderr)
	}
	if !strings.Contains(stdout, "base-only") {
		t.Fatal("overlay resolution did not retain a consumer-owned base value")
	}

	exit, _, stderr = runTest(t, context.Background(), "env", "resolve", "--profile", profile, "--storage-root", storage, "--override", "NOT_IN_PROFILE=value")
	if exit == 0 || !strings.Contains(stderr, "override NOT_IN_PROFILE is not in profile") {
		t.Fatalf("out-of-profile override error = %d %q", exit, stderr)
	}
}

func TestEnvRunUsesExactArgvAndNoShell(t *testing.T) {
	profile, storage := writeEnvironmentCLIProfile(t)
	t.Setenv("APG_ENV_CLI_VALUE", "snapshot-value")
	t.Setenv("APG_ENV_CLI_HELPER", "0")
	if exit, _, stderr := runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage, "--context", "run-test"); exit != 0 {
		t.Fatalf("snapshot exit = %d (%s)", exit, stderr)
	}
	exit, stdout, stderr := runTest(t, context.Background(), "env", "run", "--profile", profile, "--storage-root", storage, "--override", "APG_ENV_CLI_HELPER=1", "--override", "APG_ENV_CLI_VALUE=child-value", "--", os.Args[0], "apg-env-child", "$(echo must-not-run)", "argument with spaces")
	if exit != 0 || stderr != "" || stdout != "child-ok\n" {
		t.Fatalf("run = %d %q %q", exit, stdout, stderr)
	}
}

func TestEnvRunResolvesOnlyThroughResolvedPath(t *testing.T) {
	profile, storage := writeEnvironmentCLIProfile(t)
	commandDirectory := t.TempDir()
	commandName := "apg-env-cli-nonambient"
	if err := os.Symlink(os.Args[0], filepath.Join(commandDirectory, commandName)); err != nil {
		t.Fatal(err)
	}
	t.Setenv("PATH", commandDirectory)
	t.Setenv("APG_ENV_CLI_VALUE", "snapshot-value")
	t.Setenv("APG_ENV_CLI_HELPER", "0")
	if exit, _, stderr := runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage, "--context", "resolved-path-test"); exit != 0 {
		t.Fatalf("snapshot exit = %d (%s)", exit, stderr)
	}
	t.Setenv("PATH", "/ambient-path-must-not-participate")
	exit, stdout, stderr := runTest(t, context.Background(), "env", "run", "--profile", profile, "--storage-root", storage, "--override", "APG_ENV_CLI_HELPER=1", "--override", "APG_ENV_CLI_VALUE=child-value", "--", commandName, "apg-env-child", "$(echo must-not-run)", "argument with spaces")
	if exit != 0 || stderr != "" || stdout != "child-ok\n" {
		t.Fatalf("resolved-path run = %d %q %q", exit, stdout, stderr)
	}
}

func TestEnvProfileAndValueFailuresDoNotLeak(t *testing.T) {
	profile, storage := writeEnvironmentCLIProfile(t)
	t.Setenv("APG_ENV_CLI_HELPER", "0")
	secret := "secret-value-with-control-\x01-fragment"
	t.Setenv("APG_ENV_CLI_VALUE", secret)
	exit, stdout, stderr := runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage, "--context", "failure-test")
	if exit == 0 || strings.Contains(stdout, secret) || strings.Contains(stderr, secret) {
		t.Fatalf("snapshot failure leaked input: %d %q %q", exit, stdout, stderr)
	}

	link := filepath.Join(filepath.Dir(profile), "profile-link.json")
	if err := os.Symlink(profile, link); err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "env", "profile-check", "--profile", link)
	if exit == 0 || stdout != "" || stderr == "" {
		t.Fatalf("symlink profile = %d %q %q", exit, stdout, stderr)
	}
}

func TestEnvProfileRejectsHardLinksAndWrongModes(t *testing.T) {
	profile, _ := writeEnvironmentCLIProfile(t)
	hardlink := filepath.Join(filepath.Dir(profile), "profile-hardlink.json")
	if err := os.Link(profile, hardlink); err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr := runTest(t, context.Background(), "env", "profile-check", "--profile", hardlink)
	if exit == 0 || stdout != "" || stderr == "" {
		t.Fatalf("hard-linked profile = %d %q %q", exit, stdout, stderr)
	}

	if err := os.Chmod(profile, 0o640); err != nil {
		t.Fatal(err)
	}
	exit, stdout, stderr = runTest(t, context.Background(), "env", "profile-check", "--profile", profile)
	if exit == 0 || stdout != "" || stderr == "" {
		t.Fatalf("wrong-mode profile = %d %q %q", exit, stdout, stderr)
	}
}

func TestEnvRunPropagatesChildExitWithoutEnvironmentOutput(t *testing.T) {
	profile, storage := writeEnvironmentCLIProfile(t)
	t.Setenv("APG_ENV_CLI_HELPER", "0")
	t.Setenv("APG_ENV_CLI_VALUE", "snapshot-value")
	if exit, _, stderr := runTest(t, context.Background(), "env", "snapshot", "--profile", profile, "--storage-root", storage, "--context", "exit-test"); exit != 0 {
		t.Fatalf("snapshot exit = %d (%s)", exit, stderr)
	}
	secret := "child-secret-must-not-appear"
	exit, stdout, stderr := runTest(t, context.Background(), "env", "run", "--profile", profile, "--storage-root", storage, "--override", "APG_ENV_CLI_HELPER=17", "--override", "APG_ENV_CLI_VALUE="+secret, "--", os.Args[0], "apg-env-child-exit-17")
	if exit != 17 || stdout != "" || stderr != "" || strings.Contains(stdout+stderr, secret) {
		t.Fatalf("child exit = %d %q %q", exit, stdout, stderr)
	}
}

func writeEnvironmentCLIProfile(t *testing.T) (string, string) {
	t.Helper()
	root, err := filepath.EvalSymlinks(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	profile := filepath.Join(root, "profile.json")
	content := `{"schema_version":"apg.environment-profile/v1","profile_id":"cli-test","entries":[{"name":"APG_ENV_CLI_HELPER","validator":"token","max_bytes":32,"required":true,"description":"test helper selector"},{"name":"APG_ENV_CLI_VALUE","validator":"raw_safe","max_bytes":128,"required":true,"description":"test value"},{"name":"APG_ENV_CLI_OPTIONAL","validator":"raw_safe","max_bytes":128,"required":false,"description":"optional test value"},{"name":"PATH","validator":"path_list","max_bytes":8192,"required":true,"description":"explicit command search path"}]}`
	if err := os.WriteFile(profile, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := os.Chmod(profile, 0o600); err != nil {
		t.Fatal(err)
	}
	return profile, filepath.Join(root, "storage")
}
