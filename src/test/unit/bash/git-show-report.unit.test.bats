#!/usr/bin/env bats
# apg-test-source-target: bin/git-show-report

bats_require_minimum_version 1.5.0

setup() {
  repo_dir="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../../../.." && pwd)"
  command_file="$repo_dir/bin/git-show-report"
  report_root="$BATS_TEST_TMPDIR/reports"
  boundary="--------------------------------------------------------------------------------"
  envelope="================================================================================"
}

init_report_repo() {
  local work_repo="$1"

  mkdir -p "$work_repo"
  git -C "$work_repo" init -q -b main
  git -C "$work_repo" config user.email "codex@example.invalid"
  git -C "$work_repo" config user.name "Codex Test"
  printf '%s\n' "hello from git-show-report" > "$work_repo/file.txt"
  git -C "$work_repo" add file.txt
  GIT_AUTHOR_DATE="2030-01-02T03:04:05Z" GIT_COMMITTER_DATE="2030-01-02T03:04:05Z" \
    git -C "$work_repo" commit -q -m "initial report commit" -m "Complete message body."
  git -C "$work_repo" rev-parse HEAD
}

run_report() {
  local work_repo="$1"
  shift
  run env GIT_SHOW_REPORT_ROOT="$report_root" bash -c \
    'cd "$1" && shift && exec "$@"' _ "$work_repo" "$command_file" "$@"
}

mode_of() {
  if stat -f '%Lp' "$1" >/dev/null 2>&1; then
    stat -f '%Lp' "$1"
  else
    stat -c '%a' "$1"
  fi
}

field_value() {
  local key="$1"
  local file="$2"
  sed -n "s/^${key}: //p" "$file" | tail -n 1
}

extract_payload() {
  local section="$1"
  local file="$2"
  local output="$3"
  awk -v begin="BEGIN $section" -v end="END $section" -v line="$boundary" '
    !in_payload {
      if (previous == line && $0 == begin) {
        getline
        if ($0 == line) { in_payload = 1; previous = ""; next }
      }
      previous = $0
      next
    }
    pending && $0 == line { print line; next }
    in_payload && $0 == line { pending = 1; next }
    pending && $0 == end { exit }
    pending { print line; pending = 0 }
    in_payload { print }
  ' "$file" > "$output"
}

@test "git-show-report writes one complete version-2 root record with canonical identity and hashes" {
  work_repo="$BATS_TEST_TMPDIR/example-repo"
  commit_hash="$(init_report_repo "$work_repo")"
  abbreviated="$(printf '%s' "$commit_hash" | cut -c1-10 | tr '[:lower:]' '[:upper:]')"
  report_file="$report_root/example-repo/ORCH22.report.txt"

  run_report "$work_repo" ORCH22 "$abbreviated" docs/status/ORCH22.md passed full-gate

  [ "$status" -eq 0 ]
  [ "$(sed -n '1p' "$report_file")" = "$envelope" ]
  [ "$(sed -n '2p' "$report_file")" = "BEGIN AGENT-REPORT-RECORD" ]
  [ "$(field_value ENVELOPE-FORMAT "$report_file")" = "agent-report-record" ]
  [ "$(field_value ENVELOPE-VERSION "$report_file")" = "1" ]
  [ "$(field_value RECORD-TYPE "$report_file")" = "git-show-report" ]
  [ "$(field_value RECORD-FORMAT-VERSION "$report_file")" = "2" ]
  [ "$(field_value FORMAT-VERSION "$report_file")" = "2" ]
  [ "$(field_value REPORT-ID "$report_file")" = "GIT-SHOW-REPORT-$commit_hash" ]
  [ "$(field_value COMMIT-INPUT "$report_file")" = "$abbreviated" ]
  [ "$(field_value COMMIT "$report_file")" = "$commit_hash" ]
  [ "$(field_value ROOT-COMMIT "$report_file")" = "true" ]
  [ "$(field_value MERGE-COMMIT "$report_file")" = "false" ]
  [ "$(field_value PARENT-COUNT "$report_file")" = "0" ]
  [ "$(field_value PARENTS "$report_file")" = "NONE" ]
  [ "$(field_value PATCH-MODE "$report_file")" = "root" ]
  [ "$(field_value RELATED-OPERATIONAL-REPORT "$report_file")" = "NONE" ]
  [[ "$(field_value PAYLOAD-SHA256 "$report_file")" =~ ^[0-9a-f]{64}$ ]]
  [[ "$(field_value PAYLOAD-SIZE-BYTES "$report_file")" =~ ^[0-9]+$ ]]
  [ "$(grep -c '^BEGIN READING GUIDE$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN REPORT IDENTITY$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN COMMIT SUMMARY$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN CHANGED FILES$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN NUMSTAT$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN COMMIT MESSAGE$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN PATCH$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN INTEGRITY SUMMARY$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN AGENT-REPORT-RECORD$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^END AGENT-REPORT-RECORD$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN GIT-SHOW-REPORT$' "$report_file")" -eq 0 ]
  [ "$(field_value RECORD-COMPLETE "$report_file")" = "true" ]
  [ "$(tail -c 1 "$report_file" | od -An -t u1 | tr -d ' ')" = "10" ]
  [ "$(mode_of "$report_root/example-repo")" = "700" ]
  [ "$(mode_of "$report_file")" = "600" ]
  [[ "$output" == *"appended $commit_hash"* ]]

  for section in "CHANGED FILES" NUMSTAT "COMMIT MESSAGE" PATCH; do
    payload="$BATS_TEST_TMPDIR/${section// /-}.payload"
    extract_payload "$section" "$report_file" "$payload"
    key="${section// /-}-SHA256"
    [ "$(shasum -a 256 "$payload" | awk '{print $1}')" = "$(field_value "$key" "$report_file")" ]
  done
}

@test "git-show-report preserves operational metadata and renders empty values as NULL" {
  work_repo="$BATS_TEST_TMPDIR/example-repo"
  commit_hash="$(init_report_repo "$work_repo")"
  report_file="$report_root/example-repo/PHASE-1.report.txt"

  run_report "$work_repo" PHASE-1 "$commit_hash" "" "" ""

  [ "$status" -eq 0 ]
  [ "$(field_value PHASE "$report_file")" = "PHASE-1" ]
  [ "$(field_value STATUS-DOC "$report_file")" = "NULL" ]
  [ "$(field_value RESULT "$report_file")" = "NULL" ]
  [ "$(field_value FINAL-GATE "$report_file")" = "NULL" ]
  grep -Fqx "initial report commit" "$report_file"
  grep -Fqx "Complete message body." "$report_file"
}

@test "git-show-report keeps the five-argument usage and rejects unsafe inputs" {
  work_repo="$BATS_TEST_TMPDIR/example-repo"
  commit_hash="$(init_report_repo "$work_repo")"

  run "$command_file" --help
  [ "$status" -eq 0 ]
  [[ "$output" == Usage:* ]]
  run "$command_file" -h
  [ "$status" -eq 0 ]

  for args in \
    "" \
    "ORCH22 $commit_hash status passed" \
    "ORCH22 $commit_hash status passed gate extra"; do
    run bash -c 'exec "$1" ${2}' _ "$command_file" "$args"
    [ "$status" -eq 2 ]
  done

  for ticket in "." ".." "../ORCH22" 'bad\name' " leading" "trailing " $'bad\ttab' $'bad\nline'; do
    run_report "$work_repo" "$ticket" "$commit_hash" status passed gate
    [ "$status" -eq 2 ]
  done
  [ ! -e "$report_root" ]

  run_report "$work_repo" ORCH22 "$commit_hash" $'bad\nstatus' passed gate
  [ "$status" -eq 2 ]
  run_report "$work_repo" ORCH22 not-a-hash status passed gate
  [ "$status" -eq 2 ]
}

@test "git-show-report uses explicit single-parent and first-parent merge patches" {
  work_repo="$BATS_TEST_TMPDIR/merge-repo"
  root_hash="$(init_report_repo "$work_repo")"
  printf '%s\n' "main change" >> "$work_repo/file.txt"
  git -C "$work_repo" commit -qam "main change"
  normal_hash="$(git -C "$work_repo" rev-parse HEAD)"
  git -C "$work_repo" switch -q -c feature "$root_hash"
  printf '%s\n' "feature" > "$work_repo/feature.txt"
  git -C "$work_repo" add feature.txt
  git -C "$work_repo" commit -qm "feature change"
  git -C "$work_repo" switch -q main
  git -C "$work_repo" merge -q --no-ff feature -m "merge feature"
  merge_hash="$(git -C "$work_repo" rev-parse HEAD)"

  run_report "$work_repo" NORMAL "$normal_hash" status passed gate
  [ "$status" -eq 0 ]
  normal_report="$report_root/merge-repo/NORMAL.report.txt"
  [ "$(field_value PATCH-MODE "$normal_report")" = "single-parent" ]
  [ "$(field_value PARENT-COUNT "$normal_report")" = "1" ]

  run_report "$work_repo" MERGE "$merge_hash" status passed gate
  [ "$status" -eq 0 ]
  merge_report="$report_root/merge-repo/MERGE.report.txt"
  [ "$(field_value PATCH-MODE "$merge_report")" = "first-parent-merge" ]
  [ "$(field_value MERGE-COMMIT "$merge_report")" = "true" ]
  [ "$(field_value PARENT-COUNT "$merge_report")" = "2" ]
  grep -Fqx $'A\tfeature.txt' "$merge_report"
  grep -Fq 'diff --git a/feature.txt b/feature.txt' "$merge_report"
}

@test "git-show-report appends complete records and preserves a legacy prefix" {
  work_repo="$BATS_TEST_TMPDIR/example-repo"
  first="$(init_report_repo "$work_repo")"
  printf '%s\n' "second" >> "$work_repo/file.txt"
  git -C "$work_repo" commit -qam "second commit"
  second="$(git -C "$work_repo" rev-parse HEAD)"
  printf '%s\n' "third" >> "$work_repo/file.txt"
  git -C "$work_repo" commit -qam "third commit"
  third="$(git -C "$work_repo" rev-parse HEAD)"
  report_dir="$report_root/example-repo"
  report_file="$report_dir/APPEND.report.txt"
  mkdir -p "$report_dir"
  chmod 700 "$report_dir"
  printf 'PHASE: LEGACY-V1' > "$report_file"
  chmod 600 "$report_file"

  run_report "$work_repo" APPEND "$first" status passed gate
  [ "$status" -eq 0 ]
  run_report "$work_repo" APPEND "$second" status passed gate
  [ "$status" -eq 0 ]
  run_report "$work_repo" APPEND "$third" status passed gate
  [ "$status" -eq 0 ]

  [ "$(head -c 16 "$report_file")" = "PHASE: LEGACY-V1" ]
  [ "$(grep -c '^BEGIN AGENT-REPORT-RECORD$' "$report_file")" -eq 3 ]
  [ "$(grep -c '^END AGENT-REPORT-RECORD$' "$report_file")" -eq 3 ]
  first_line="$(grep -n "^REPORT-ID: GIT-SHOW-REPORT-$first$" "$report_file" | head -1 | cut -d: -f1)"
  second_line="$(grep -n "^REPORT-ID: GIT-SHOW-REPORT-$second$" "$report_file" | head -1 | cut -d: -f1)"
  third_line="$(grep -n "^REPORT-ID: GIT-SHOW-REPORT-$third$" "$report_file" | head -1 | cut -d: -f1)"
  [ "$first_line" -lt "$second_line" ]
  [ "$second_line" -lt "$third_line" ]
  [ "$(grep -n '^BEGIN AGENT-REPORT-RECORD$' "$report_file" | head -1 | cut -d: -f1)" -gt 1 ]
  [ "$(tail -c 1 "$report_file" | od -An -t u1 | tr -d ' ')" = "10" ]
}

@test "git-show-report rejects unsafe existing destinations" {
  work_repo="$BATS_TEST_TMPDIR/example-repo"
  commit_hash="$(init_report_repo "$work_repo")"
  report_dir="$report_root/example-repo"
  mkdir -p "$report_dir"
  chmod 700 "$report_dir"
  target="$report_dir/UNSAFE.report.txt"
  printf '%s\n' unsafe > "$target"
  chmod 660 "$target"

  run_report "$work_repo" UNSAFE "$commit_hash" status passed gate
  [ "$status" -eq 1 ]
  [ "$(cat "$target")" = "unsafe" ]

  chmod 400 "$target"
  run_report "$work_repo" UNSAFE "$commit_hash" status passed gate
  [ "$status" -eq 1 ]
  [ "$(cat "$target")" = "unsafe" ]

  rm -f "$target"
  ln -s "$BATS_TEST_TMPDIR/missing" "$target"
  run_report "$work_repo" UNSAFE "$commit_hash" status passed gate
  [ "$status" -eq 1 ]
}

@test "git-show-report reports renames and escapes line-oriented paths" {
  work_repo="$BATS_TEST_TMPDIR/path-repo"
  init_report_repo "$work_repo" >/dev/null
  git -C "$work_repo" mv file.txt renamed.txt
  unusual=$'line\nname.txt'
  printf '%s\n' unusual > "$work_repo/$unusual"
  git -C "$work_repo" add -A
  git -C "$work_repo" commit -qm "rename and unusual path"
  commit_hash="$(git -C "$work_repo" rev-parse HEAD)"

  run_report "$work_repo" PATHS "$commit_hash" status passed gate

  [ "$status" -eq 0 ]
  report_file="$report_root/path-repo/PATHS.report.txt"
  [ "$(field_value FILES-RENAMED "$report_file")" = "1" ]
  grep -Eq '^R[0-9]+[[:space:]]+file.txt[[:space:]]+renamed.txt$' "$report_file"
  grep -Fq '"line\nname.txt"' "$report_file"
}

@test "git-show-report uses bounded textual binary summaries and empty payload hashes" {
  work_repo="$BATS_TEST_TMPDIR/binary-repo"
  init_report_repo "$work_repo" >/dev/null
  printf '\000\001\002\003' > "$work_repo/blob.bin"
  git -C "$work_repo" add blob.bin
  git -C "$work_repo" commit -qm "add binary"
  binary_hash="$(git -C "$work_repo" rev-parse HEAD)"

  run_report "$work_repo" BINARY "$binary_hash" status passed gate
  [ "$status" -eq 0 ]
  binary_report="$report_root/binary-repo/BINARY.report.txt"
  [ "$(field_value BINARY-FILES "$binary_report")" = "1" ]
  [ "$(field_value INSERTIONS "$binary_report")" = "UNKNOWN" ]
  grep -Fq 'Binary files /dev/null and b/blob.bin differ' "$binary_report"
  ! grep -Fq 'GIT binary patch' "$binary_report"

  git -C "$work_repo" commit -q --allow-empty -m "empty commit"
  empty_hash="$(git -C "$work_repo" rev-parse HEAD)"
  run_report "$work_repo" EMPTY "$empty_hash" status passed gate
  [ "$status" -eq 0 ]
  empty_report="$report_root/binary-repo/EMPTY.report.txt"
  [ "$(field_value FILES-CHANGED "$empty_report")" = "0" ]
  [ "$(field_value PATCH-SHA256 "$empty_report")" = "$(printf '' | shasum -a 256 | awk '{print $1}')" ]
  [ "$(field_value CHANGED-FILES-SHA256 "$empty_report")" = "$(printf '' | shasum -a 256 | awk '{print $1}')" ]

  git -C "$work_repo" commit -q --allow-empty --allow-empty-message -m ""
  empty_message_hash="$(git -C "$work_repo" rev-parse HEAD)"
  run_report "$work_repo" EMPTY-MESSAGE "$empty_message_hash" status passed gate
  [ "$status" -eq 0 ]
  empty_message_report="$report_root/binary-repo/EMPTY-MESSAGE.report.txt"
  empty_message_payload="$BATS_TEST_TMPDIR/empty-message.payload"
  extract_payload "COMMIT MESSAGE" "$empty_message_report" "$empty_message_payload"
  [ ! -s "$empty_message_payload" ]
  [ "$(field_value COMMIT-MESSAGE-SHA256 "$empty_message_report")" = "$(printf '' | shasum -a 256 | awk '{print $1}')" ]
}

@test "git-show-report treats marker-like commit and patch text as untrusted payload" {
  work_repo="$BATS_TEST_TMPDIR/marker-repo"
  init_report_repo "$work_repo" >/dev/null
  cat > "$work_repo/markers.txt" <<'MARKERS'
BEGIN AGENT-REPORT-RECORD
END AGENT-REPORT-RECORD
BEGIN PATCH
END PATCH
-------------------------------------------------------------------------------
MARKERS
  git -C "$work_repo" add markers.txt
  git -C "$work_repo" commit -q -m "BEGIN AGENT-REPORT-RECORD" -m $'END AGENT-REPORT-RECORD\nBEGIN PATCH\nEND PATCH\n-------------------------------------------------------------------------------'
  commit_hash="$(git -C "$work_repo" rev-parse HEAD)"

  run_report "$work_repo" MARKERS "$commit_hash" status passed gate

  [ "$status" -eq 0 ]
  report_file="$report_root/marker-repo/MARKERS.report.txt"
  [ "$(field_value RECORD-COMPLETE "$report_file")" = "true" ]
  [ "$(grep -c '^BEGIN AGENT-REPORT-RECORD$' "$report_file")" -eq 2 ]
  [ "$(grep -c '^END AGENT-REPORT-RECORD$' "$report_file")" -eq 2 ]
  for section in "COMMIT MESSAGE" PATCH; do
    payload="$BATS_TEST_TMPDIR/marker-${section// /-}.payload"
    extract_payload "$section" "$report_file" "$payload"
    key="${section// /-}-SHA256"
    [ "$(sha256_file_for_test "$payload")" = "$(field_value "$key" "$report_file")" ]
  done
}

sha256_file_for_test() {
  shasum -a 256 "$1" | awk '{print $1}'
}

@test "git-show-report record generation is deterministic" {
  work_repo="$BATS_TEST_TMPDIR/deterministic-repo"
  commit_hash="$(init_report_repo "$work_repo")"
  report_file="$report_root/deterministic-repo/DETERMINISTIC.report.txt"

  run_report "$work_repo" DETERMINISTIC "$commit_hash" status passed gate
  [ "$status" -eq 0 ]
  cp "$report_file" "$BATS_TEST_TMPDIR/first-record"
  rm "$report_file"
  run_report "$work_repo" DETERMINISTIC "$commit_hash" status passed gate
  [ "$status" -eq 0 ]

  cmp -s "$BATS_TEST_TMPDIR/first-record" "$report_file"
}

@test "git-show-report injected generation and replacement failures preserve the destination" {
  work_repo="$BATS_TEST_TMPDIR/failure-repo"
  commit_hash="$(init_report_repo "$work_repo")"
  report_dir="$report_root/failure-repo"
  report_file="$report_dir/FAILURE.report.txt"
  mkdir -p "$report_dir"
  chmod 700 "$report_dir"
  printf '%s\n' "existing evidence" > "$report_file"
  chmod 600 "$report_file"
  cp "$report_file" "$BATS_TEST_TMPDIR/before"

  for step in metadata changed-files numstat commit-message patch record-assembly before-destination-replacement; do
    run env GIT_SHOW_REPORT_ROOT="$report_root" GIT_SHOW_REPORT_TESTING=1 GIT_SHOW_REPORT_TEST_FAIL_STEP="$step" \
      bash -c 'cd "$1" && exec "$2" FAILURE "$3" status passed gate' _ "$work_repo" "$command_file" "$commit_hash"
    [ "$status" -eq 1 ]
    cmp -s "$BATS_TEST_TMPDIR/before" "$report_file"
    [ ! -e "$report_file.lock" ]
    [ -z "$(find "$report_dir" -maxdepth 1 -name '.FAILURE.report.*' -print)" ]
  done
}

@test "git-show-report serializes concurrent same-ticket appends" {
  work_repo="$BATS_TEST_TMPDIR/concurrent-repo"
  first="$(init_report_repo "$work_repo")"
  printf '%s\n' second >> "$work_repo/file.txt"
  git -C "$work_repo" commit -qam "second"
  second="$(git -C "$work_repo" rev-parse HEAD)"
  output_one="$BATS_TEST_TMPDIR/one.out"
  output_two="$BATS_TEST_TMPDIR/two.out"

  (
    cd "$work_repo"
    GIT_SHOW_REPORT_ROOT="$report_root" "$command_file" CONCURRENT "$first" status passed gate > "$output_one" 2>&1
  ) &
  pid_one=$!
  (
    cd "$work_repo"
    GIT_SHOW_REPORT_ROOT="$report_root" "$command_file" CONCURRENT "$second" status passed gate > "$output_two" 2>&1
  ) &
  pid_two=$!
  wait "$pid_one"
  status_one=$?
  wait "$pid_two"
  status_two=$?

  [ "$status_one" -eq 0 ]
  [ "$status_two" -eq 0 ]
  report_file="$report_root/concurrent-repo/CONCURRENT.report.txt"
  [ "$(grep -c '^BEGIN AGENT-REPORT-RECORD$' "$report_file")" -eq 2 ]
  [ "$(grep -c '^END AGENT-REPORT-RECORD$' "$report_file")" -eq 2 ]
  [ "$(grep -c '^RECORD-COMPLETE: true$' "$report_file")" -eq 2 ]
  [ ! -e "$report_file.lock" ]
}

@test "git-show-report rejects noncommit objects and overlong ticket ids" {
  work_repo="$BATS_TEST_TMPDIR/object-repo"
  commit_hash="$(init_report_repo "$work_repo")"
  blob_hash="$(printf blob | git -C "$work_repo" hash-object --stdin -w)"
  long_ticket="A$(printf '%0128d' 0)"

  run_report "$work_repo" OBJECT "$blob_hash" status passed gate
  [ "$status" -eq 1 ]
  run_report "$work_repo" "$long_ticket" "$commit_hash" status passed gate
  [ "$status" -eq 2 ]
}
