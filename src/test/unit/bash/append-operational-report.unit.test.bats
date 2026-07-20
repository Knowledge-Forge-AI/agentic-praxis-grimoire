#!/usr/bin/env bats
# apg-test-source-target: bin/append-operational-report
# apg-test-source-target: libexec/agent-report/common.sh

bats_require_minimum_version 1.5.0

setup() {
  repo_dir="$(cd "$(dirname "${BATS_TEST_FILENAME}")/../../../.." && pwd)"
  command_file="$repo_dir/bin/append-operational-report"
  git_command_file="$repo_dir/bin/git-show-report"
  report_root="$BATS_TEST_TMPDIR/reports"
  boundary="--------------------------------------------------------------------------------"
  envelope="================================================================================"
  work_repo="$BATS_TEST_TMPDIR/work-repo"
  mkdir -p "$work_repo"
  git -C "$work_repo" init -q -b main
  git -C "$work_repo" config user.email "codex@example.invalid"
  git -C "$work_repo" config user.name "Codex Test"
  printf 'tracked\n' > "$work_repo/tracked.txt"
  git -C "$work_repo" add tracked.txt
  git -C "$work_repo" commit -qm "initial"
  commit_hash="$(git -C "$work_repo" rev-parse HEAD)"
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

sha256_file_for_test() {
  shasum -a 256 "$1" | awk '{print $1}'
}

write_source() {
  local path="$1"
  local content="$2"

  printf '%s' "$content" > "$path"
  chmod 600 "$path"
}

run_operational() {
  run env GIT_SHOW_REPORT_ROOT="$report_root" bash -c \
    'cd "$1" && shift && exec "$@"' _ "$work_repo" "$command_file" "$@"
}

@test "append-operational-report writes a deterministic exact common-envelope record" {
  source_file="$BATS_TEST_TMPDIR/phase-operational-report.txt"
  source_content=$'REPORT\nreport_schema: operational-report-v1\nphase: PHASE-1\noutcome: passed\nproject: work-repo'
  write_source "$source_file" "$source_content"
  source_hash="$(sha256_file_for_test "$source_file")"
  git_report_id="GIT-SHOW-REPORT-$commit_hash"

  run_operational PHASE-1 "$source_file" passed full-gate \
    --related-commit "${commit_hash:0:10}" --related-git-report-id "$git_report_id"

  [ "$status" -eq 0 ]
  report_file="$report_root/work-repo/PHASE-1.report.txt"
  [ "$(sed -n '1p' "$report_file")" = "$envelope" ]
  [ "$(sed -n '2p' "$report_file")" = "BEGIN AGENT-REPORT-RECORD" ]
  [ "$(field_value ENVELOPE-FORMAT "$report_file")" = "agent-report-record" ]
  [ "$(field_value ENVELOPE-VERSION "$report_file")" = "1" ]
  [ "$(field_value RECORD-TYPE "$report_file")" = "operational-report" ]
  [ "$(field_value RECORD-FORMAT-VERSION "$report_file")" = "1" ]
  [ "$(field_value RECORD-ID "$report_file")" = "OPERATIONAL-REPORT-$source_hash" ]
  [ "$(field_value PROJECT "$report_file")" = "work-repo" ]
  [ "$(field_value PHASE "$report_file")" = "PHASE-1" ]
  [ "$(field_value SOURCE-FILE-BASENAME "$report_file")" = "phase-operational-report.txt" ]
  [ "$(field_value SOURCE-PAYLOAD-SHA256 "$report_file")" = "$source_hash" ]
  [ "$(field_value SOURCE-PAYLOAD-SIZE-BYTES "$report_file")" = "$(wc -c < "$source_file" | tr -d ' ')" ]
  [ "$(field_value RELATED-COMMIT "$report_file")" = "$commit_hash" ]
  [ "$(field_value RELATED-GIT-REPORT-ID "$report_file")" = "$git_report_id" ]
  [ "$(field_value BODY-SCHEMA-DETECTED "$report_file")" = "operational-report-v1" ]
  [ "$(field_value SOURCE-DECLARED-PHASE "$report_file")" = "PHASE-1" ]
  [ "$(field_value SOURCE-DECLARED-OUTCOME "$report_file")" = "passed" ]
  [ "$(field_value SOURCE-PRIMARY-COMMIT "$report_file")" = "UNKNOWN" ]
  [ "$(grep -c '^BEGIN AGENT-REPORT-RECORD$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^END AGENT-REPORT-RECORD$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^BEGIN OPERATIONAL REPORT BODY$' "$report_file")" -eq 1 ]
  [ "$(grep -c '^END OPERATIONAL REPORT BODY$' "$report_file")" -eq 1 ]
  [ "$(field_value END-OF-OPERATIONAL-BODY-REACHED "$report_file")" = "true" ]
  [ "$(field_value RECORD-COMPLETE "$report_file")" = "true" ]
  [[ "$(field_value PAYLOAD-SHA256 "$report_file")" =~ ^[0-9a-f]{64}$ ]]
  [[ "$(field_value PAYLOAD-SIZE-BYTES "$report_file")" =~ ^[0-9]+$ ]]
  [ "$(mode_of "$report_root/work-repo")" = "700" ]
  [ "$(mode_of "$report_file")" = "600" ]
  cmp -s <(printf '%s' "$source_content") "$source_file"
  [[ "$output" == *"OPERATIONAL-REPORT-$source_hash"* ]]
}

@test "append-operational-report preserves source and framed-body digest scopes" {
  source_file="$BATS_TEST_TMPDIR/no-terminal-newline.txt"
  write_source "$source_file" "exact bytes without newline"
  source_before="$BATS_TEST_TMPDIR/source-before"
  cp "$source_file" "$source_before"
  framed="$BATS_TEST_TMPDIR/framed"
  { cat "$source_file"; printf '\n'; } > "$framed"

  run_operational DIGEST "$source_file" passed gate

  [ "$status" -eq 0 ]
  report_file="$report_root/work-repo/DIGEST.report.txt"
  [ "$(field_value SOURCE-PAYLOAD-SHA256 "$report_file")" = "$(sha256_file_for_test "$source_file")" ]
  [ "$(field_value FRAMED-BODY-SHA256 "$report_file")" = "$(sha256_file_for_test "$framed")" ]
  [ "$(field_value FRAMED-BODY-SIZE-BYTES "$report_file")" = "$(wc -c < "$framed" | tr -d ' ')" ]
  cmp -s "$source_file" "$source_before"
}

@test "append-operational-report validates usage and related identities" {
  source_file="$BATS_TEST_TMPDIR/source.txt"
  write_source "$source_file" "evidence"
  matching="GIT-SHOW-REPORT-$commit_hash"
  other="GIT-SHOW-REPORT-$(printf '%040d' 0)"

  run "$command_file" --help
  [ "$status" -eq 0 ]
  for args in \
    "" \
    "PHASE $source_file passed" \
    "PHASE $source_file passed gate extra" \
    "PHASE $source_file passed gate --unknown value" \
    "PHASE $source_file passed gate --related-commit $commit_hash --related-commit $commit_hash" \
    "PHASE $source_file passed gate --related-git-report-id $matching --related-git-report-id $matching"; do
    run bash -c 'cd "$1" && exec "$2" ${3}' _ "$work_repo" "$command_file" "$args"
    [ "$status" -eq 2 ]
  done
  run_operational ../BAD "$source_file" passed gate
  [ "$status" -eq 2 ]
  run_operational PHASE relative.txt passed gate
  [ "$status" -eq 2 ]
  run_operational PHASE "$source_file" $'bad\nresult' gate
  [ "$status" -eq 2 ]
  run_operational PHASE "$source_file" passed gate --related-commit not-a-commit
  [ "$status" -eq 2 ]
  run_operational PHASE "$source_file" passed gate --related-commit "$commit_hash" --related-git-report-id "$other"
  [ "$status" -eq 2 ]
}

@test "append-operational-report detects legacy and free-form reports without rewriting" {
  legacy="$BATS_TEST_TMPDIR/legacy.txt"
  freeform="$BATS_TEST_TMPDIR/free-form.md"
  write_source "$legacy" $'phase: ORCH22\noutcome: passed\nsource commit: abc'
  write_source "$freeform" $'# Notes\n\nThis is free-form evidence.'

  run_operational LEGACY "$legacy" passed gate
  [ "$status" -eq 0 ]
  [ "$(field_value BODY-SCHEMA-DETECTED "$report_root/work-repo/LEGACY.report.txt")" = "legacy-key-value" ]
  run_operational FREEFORM "$freeform" passed gate
  [ "$status" -eq 0 ]
  [ "$(field_value BODY-SCHEMA-DETECTED "$report_root/work-repo/FREEFORM.report.txt")" = "free-form" ]
}

@test "append-operational-report rejects empty oversized and unsafe source evidence" {
  empty="$BATS_TEST_TMPDIR/empty.txt"
  : > "$empty"
  chmod 600 "$empty"
  run_operational EMPTY "$empty" passed gate
  [ "$status" -eq 1 ]

  permissive="$BATS_TEST_TMPDIR/permissive.txt"
  write_source "$permissive" "unsafe"
  chmod 640 "$permissive"
  run_operational UNSAFE "$permissive" passed gate
  [ "$status" -eq 1 ]

  target="$BATS_TEST_TMPDIR/target.txt"
  write_source "$target" "target"
  symlink="$BATS_TEST_TMPDIR/symlink.txt"
  ln -s "$target" "$symlink"
  run_operational SYMLINK "$symlink" passed gate
  [ "$status" -eq 1 ]

  hardlink="$BATS_TEST_TMPDIR/hardlink.txt"
  ln "$target" "$hardlink"
  run_operational HARDLINK "$hardlink" passed gate
  [ "$status" -eq 1 ]

  boundary_file="$BATS_TEST_TMPDIR/eight-mib.txt"
  dd if=/dev/zero of="$boundary_file" bs=1048576 count=8 2>/dev/null
  chmod 600 "$boundary_file"
  run_operational LIMIT "$boundary_file" passed gate
  [ "$status" -eq 0 ]
  printf 'x' >> "$boundary_file"
  run_operational TOO-LARGE "$boundary_file" passed gate
  [ "$status" -eq 1 ]
  [ ! -e "$report_root/work-repo/TOO-LARGE.report.txt" ]
}

@test "git and operational commands serialize complete same-ticket records" {
  source_file="$BATS_TEST_TMPDIR/ops.txt"
  write_source "$source_file" $'REPORT\nreport_schema: operational-report-v1\nphase: MIXED'
  output_git="$BATS_TEST_TMPDIR/git.out"
  output_ops="$BATS_TEST_TMPDIR/ops.out"

  (
    cd "$work_repo"
    GIT_SHOW_REPORT_ROOT="$report_root" "$git_command_file" MIXED "$commit_hash" status passed gate > "$output_git" 2>&1
  ) &
  git_pid=$!
  (
    cd "$work_repo"
    GIT_SHOW_REPORT_ROOT="$report_root" "$command_file" MIXED "$source_file" passed gate > "$output_ops" 2>&1
  ) &
  ops_pid=$!
  wait "$git_pid"
  git_status=$?
  wait "$ops_pid"
  ops_status=$?

  [ "$git_status" -eq 0 ]
  [ "$ops_status" -eq 0 ]
  report_file="$report_root/work-repo/MIXED.report.txt"
  [ "$(grep -c '^BEGIN AGENT-REPORT-RECORD$' "$report_file")" -eq 2 ]
  [ "$(grep -c '^END AGENT-REPORT-RECORD$' "$report_file")" -eq 2 ]
  [ "$(grep -c '^RECORD-TYPE: git-show-report$' "$report_file")" -eq 2 ]
  [ "$(grep -c '^RECORD-TYPE: operational-report$' "$report_file")" -eq 2 ]
  [ "$(grep -c '^RECORD-COMPLETE: true$' "$report_file")" -eq 2 ]
  [ ! -e "$report_file.lock" ]
}

@test "operational marker-like text remains payload and duplicate records remain distinct" {
  source_file="$BATS_TEST_TMPDIR/markers.txt"
  write_source "$source_file" $'BEGIN AGENT-REPORT-RECORD\nEND AGENT-REPORT-RECORD\nBEGIN OPERATIONAL REPORT BODY\nEND OPERATIONAL REPORT BODY'

  run_operational MARKERS "$source_file" passed gate
  [ "$status" -eq 0 ]
  run_operational MARKERS "$source_file" passed gate
  [ "$status" -eq 0 ]

  report_file="$report_root/work-repo/MARKERS.report.txt"
  [ "$(grep -c '^BEGIN AGENT-REPORT-RECORD$' "$report_file")" -eq 4 ]
  [ "$(grep -c '^END AGENT-REPORT-RECORD$' "$report_file")" -eq 4 ]
  [ "$(grep -c '^RECORD-COMPLETE: true$' "$report_file")" -eq 2 ]
  [ "$(grep '^RECORD-ID: OPERATIONAL-REPORT-' "$report_file" | sort -u | wc -l | tr -d ' ')" -eq 1 ]
  [ "$(tail -c 1 "$report_file" | od -An -t u1 | tr -d ' ')" = "10" ]
}

@test "operational failure injection preserves destination and cleans private state" {
  source_file="$BATS_TEST_TMPDIR/failure.txt"
  write_source "$source_file" "failure evidence"
  report_dir="$report_root/work-repo"
  report_file="$report_dir/FAILURE.report.txt"
  mkdir -p "$report_dir"
  chmod 700 "$report_dir"
  printf 'legacy evidence\n' > "$report_file"
  chmod 600 "$report_file"
  cp "$report_file" "$BATS_TEST_TMPDIR/before"

  for step in source-read body-framing hashing record-assembly before-destination-replacement; do
    run env GIT_SHOW_REPORT_ROOT="$report_root" GIT_SHOW_REPORT_TESTING=1 GIT_SHOW_REPORT_TEST_FAIL_STEP="$step" \
      bash -c 'cd "$1" && exec "$2" FAILURE "$3" passed gate' _ "$work_repo" "$command_file" "$source_file"
    [ "$status" -eq 1 ]
    cmp -s "$BATS_TEST_TMPDIR/before" "$report_file"
    [ ! -e "$report_file.lock" ]
    [ -z "$(find "$report_dir" -maxdepth 1 -name '.FAILURE.report.*' -print)" ]
  done
}

@test "omnibus concatenation preserves typed complete records across projects" {
  source_file="$BATS_TEST_TMPDIR/omnibus-ops.txt"
  marker_file="$BATS_TEST_TMPDIR/omnibus-markers.txt"
  write_source "$source_file" $'REPORT\nreport_schema: operational-report-v1\nphase: OMNIBUS'
  write_source "$marker_file" $'BEGIN AGENT-REPORT-RECORD\nEND AGENT-REPORT-RECORD'

  env GIT_SHOW_REPORT_ROOT="$report_root" bash -c \
    'cd "$1" && exec "$2" OMNI-GIT "$3" status passed gate' \
    _ "$work_repo" "$git_command_file" "$commit_hash" >/dev/null 2>&1
  run_operational OMNI-OPS "$source_file" passed gate
  [ "$status" -eq 0 ]
  run_operational OMNI-MARKERS "$marker_file" passed gate
  [ "$status" -eq 0 ]

  other_repo="$BATS_TEST_TMPDIR/other-project"
  git -C "$BATS_TEST_TMPDIR" init -q -b main "$(basename "$other_repo")"
  git -C "$other_repo" config user.email "codex@example.invalid"
  git -C "$other_repo" config user.name "Codex Test"
  printf 'other\n' > "$other_repo/file.txt"
  git -C "$other_repo" add file.txt
  git -C "$other_repo" commit -qm "other"
  run env GIT_SHOW_REPORT_ROOT="$report_root" bash -c \
    'cd "$1" && exec "$2" OTHER "$3" passed gate' _ "$other_repo" "$command_file" "$source_file"
  [ "$status" -eq 0 ]

  omnibus="$BATS_TEST_TMPDIR/omnibus.txt"
  cat \
    "$report_root/work-repo/OMNI-GIT.report.txt" \
    "$report_root/work-repo/OMNI-OPS.report.txt" \
    "$report_root/work-repo/OMNI-GIT.report.txt" \
    "$report_root/work-repo/OMNI-MARKERS.report.txt" \
    "$report_root/work-repo/OMNI-OPS.report.txt" \
    "$report_root/other-project/OTHER.report.txt" > "$omnibus"

  begin_count="$(awk -v edge="$envelope" '
    previous == edge && $0 == "BEGIN AGENT-REPORT-RECORD" { count++ }
    { previous = $0 }
    END { print count + 0 }
  ' "$omnibus")"
  end_count="$(awk -v edge="$envelope" '
    previous == edge && $0 == "END AGENT-REPORT-RECORD" { count++ }
    { previous = $0 }
    END { print count + 0 }
  ' "$omnibus")"
  [ "$begin_count" -eq 6 ]
  [ "$end_count" -eq 6 ]
  [ "$(grep -c '^RECORD-COMPLETE: true$' "$omnibus")" -eq 6 ]
  [ "$(grep -c '^RECORD-TYPE: git-show-report$' "$omnibus")" -eq 4 ]
  [ "$(grep -c '^RECORD-TYPE: operational-report$' "$omnibus")" -eq 8 ]
  [ "$(grep '^RECORD-ID: OPERATIONAL-REPORT-' "$omnibus" | sort | uniq -d | wc -l | tr -d ' ')" -ge 1 ]
  [ "$(tail -c 1 "$omnibus" | od -An -t u1 | tr -d ' ')" = "10" ]

  truncated="$BATS_TEST_TMPDIR/truncated.txt"
  size="$(wc -c < "$omnibus" | tr -d ' ')"
  dd if="$omnibus" of="$truncated" bs=1 count="$((size - 20))" 2>/dev/null
  [ "$(tail -n 1 "$truncated")" != "$envelope" ]
}
