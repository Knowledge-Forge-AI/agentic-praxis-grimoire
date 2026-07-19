#!/usr/bin/env bash

# Public constants and state variables are consumed by scripts sourcing this file.
# shellcheck disable=SC2034

readonly agent_report_envelope_line="================================================================================"
readonly agent_report_section_line="--------------------------------------------------------------------------------"
readonly agent_report_max_source_bytes=$((8 * 1024 * 1024))

agent_report_fail() {
  local status="$1"
  shift
  printf '%s: %s\n' "${agent_report_command_name:-agent-report}" "$*" >&2
  exit "$status"
}

agent_report_header_value() {
  if [ -z "$1" ]; then
    printf 'NULL'
  else
    printf '%s' "$1"
  fi
}

agent_report_contains_control() {
  [[ "$1" =~ [[:cntrl:]] ]]
}

agent_report_validate_ticket() {
  local ticket_id="$1"

  [[ "$ticket_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || return 1
  [ "$ticket_id" != "." ] && [ "$ticket_id" != ".." ] || return 1
  [ "${#ticket_id}" -le 128 ]
}

agent_report_file_mode() {
  if stat -f '%Lp' "$1" >/dev/null 2>&1; then
    stat -f '%Lp' "$1"
  else
    stat -c '%a' "$1"
  fi
}

agent_report_file_owner() {
  if stat -f '%u' "$1" >/dev/null 2>&1; then
    stat -f '%u' "$1"
  else
    stat -c '%u' "$1"
  fi
}

agent_report_file_links() {
  if stat -f '%l' "$1" >/dev/null 2>&1; then
    stat -f '%l' "$1"
  else
    stat -c '%h' "$1"
  fi
}

agent_report_file_size() {
  wc -c < "$1" | tr -d '[:space:]'
}

agent_report_last_byte_decimal() {
  tail -c 1 "$1" | od -An -t u1 | tr -d '[:space:]'
}

agent_report_ensure_payload_ending() {
  if [ -s "$1" ] && [ "$(agent_report_last_byte_decimal "$1")" != "10" ]; then
    printf '\n' >> "$1"
  fi
}

agent_report_sha256_file() {
  shasum -a 256 "$1" | awk '{print $1}'
}

agent_report_emit_section() {
  local name="$1"
  local payload="$2"

  printf '%s\nBEGIN %s\n%s\n' "$agent_report_section_line" "$name" "$agent_report_section_line"
  cat "$payload"
  printf '%s\nEND %s\n%s\n' "$agent_report_section_line" "$name" "$agent_report_section_line"
}

agent_report_validate_private_directory() {
  [ ! -L "$1" ] && [ -d "$1" ] || return 1
  [ "$(agent_report_file_owner "$1")" = "$(id -u)" ] || return 1
  [ "$(agent_report_file_mode "$1")" = "700" ]
}

agent_report_validate_existing_report() {
  [ ! -L "$1" ] && [ -f "$1" ] || return 1
  [ "$(agent_report_file_owner "$1")" = "$(id -u)" ] || return 1
  [ "$(agent_report_file_mode "$1")" = "600" ]
}

agent_report_injected_failure() {
  local step="$1"

  if [ "${agent_REPORT_TESTING:-${GIT_SHOW_REPORT_TESTING:-}}" = "1" ] \
    && [ "${agent_REPORT_TEST_FAIL_STEP:-${GIT_SHOW_REPORT_TEST_FAIL_STEP:-}}" = "$step" ]; then
    agent_report_fail 1 "injected failure at $step"
  fi
}

agent_report_release_lock() {
  if [ "${agent_report_lock_acquired:-false}" != "true" ]; then
    return
  fi
  if [ -f "$agent_report_lock_dir/owner" ] \
    && [ "$(cat "$agent_report_lock_dir/owner")" = "$agent_report_lock_token" ]; then
    rm -f "$agent_report_lock_dir/owner"
    rmdir "$agent_report_lock_dir" 2>/dev/null || true
  fi
  agent_report_lock_acquired=false
}

agent_report_cleanup() {
  local status=$?

  agent_report_release_lock
  if [ -n "${agent_report_temporary_root:-}" ] && [ -d "$agent_report_temporary_root" ]; then
    rm -rf "$agent_report_temporary_root"
  fi
  if [ -n "${agent_report_replacement:-}" ] && [ -f "$agent_report_replacement" ]; then
    rm -f "$agent_report_replacement"
  fi
  exit "$status"
}

agent_report_begin() {
  agent_report_command_name="$1"
  agent_report_temporary_root="$(mktemp -d "${TMPDIR:-/tmp}/${1}.XXXXXX")" \
    || agent_report_fail 1 "create private temporary directory failed"
  chmod 700 "$agent_report_temporary_root"
  agent_report_lock_acquired=false
  agent_report_replacement=""
  trap agent_report_cleanup EXIT HUP INT TERM
}

agent_report_prepare_destination() {
  local git_root="$1"
  local requested_ticket="$2"

  ticket_id="$requested_ticket"

  agent_report_project="$(basename "$git_root")"
  agent_report_contains_control "$agent_report_project" \
    && agent_report_fail 1 "repository name contains a control character"
  agent_report_root="${GIT_SHOW_REPORT_ROOT:-$HOME/Documents/agent}"
  agent_report_dir="$agent_report_root/$agent_report_project"
  agent_report_file="$agent_report_dir/$ticket_id.report.txt"
  agent_report_lock_dir="$agent_report_file.lock"
  agent_report_lock_token="$$-${RANDOM:-0}-${ticket_id}"

  if [ ! -e "$agent_report_root" ]; then
    mkdir -p "$agent_report_root"
  fi
  [ ! -L "$agent_report_dir" ] || agent_report_fail 1 "report directory is unsafe"
  if [ ! -e "$agent_report_dir" ]; then
    if mkdir "$agent_report_dir" 2>/dev/null; then
      chmod 700 "$agent_report_dir"
    fi
  fi
  agent_report_validate_private_directory "$agent_report_dir" \
    || agent_report_fail 1 "report directory is unsafe"
}

agent_report_build_record() {
  local record_type="$1"
  local format_version="$2"
  local record_id="$3"
  local project="$4"
  local phase="$5"
  local payload_file="$6"
  local record_file="$7"
  local payload_sha payload_size

  payload_sha="$(agent_report_sha256_file "$payload_file")"
  payload_size="$(agent_report_file_size "$payload_file")"
  {
    printf '%s\n' "$agent_report_envelope_line"
    printf 'BEGIN AGENT-REPORT-RECORD\n'
    printf 'ENVELOPE-FORMAT: agent-report-record\n'
    printf 'ENVELOPE-VERSION: 1\n'
    printf 'RECORD-TYPE: %s\n' "$record_type"
    printf 'RECORD-FORMAT-VERSION: %s\n' "$format_version"
    printf 'RECORD-ID: %s\n' "$record_id"
    printf 'PROJECT: %s\n' "$project"
    printf 'PHASE: %s\n' "$phase"
    printf 'PAYLOAD-SHA256: %s\n' "$payload_sha"
    printf 'PAYLOAD-SIZE-BYTES: %s\n' "$payload_size"
    printf '%s\n' "$agent_report_envelope_line"
    cat "$payload_file"
    printf '%s\n' "$agent_report_envelope_line"
    printf 'END AGENT-REPORT-RECORD\n'
    printf 'ENVELOPE-FORMAT: agent-report-record\n'
    printf 'ENVELOPE-VERSION: 1\n'
    printf 'RECORD-TYPE: %s\n' "$record_type"
    printf 'RECORD-FORMAT-VERSION: %s\n' "$format_version"
    printf 'RECORD-ID: %s\n' "$record_id"
    printf 'PROJECT: %s\n' "$project"
    printf 'PHASE: %s\n' "$phase"
    printf 'RECORD-COMPLETE: true\n'
    printf '%s\n' "$agent_report_envelope_line"
  } > "$record_file"
  chmod 600 "$record_file"
}

agent_report_validate_record() {
  local record_file="$1"
  local payload_file="$2"

  [ "$(agent_report_file_mode "$record_file")" = "600" ] || return 1
  [ "$(sed -n '1p' "$record_file")" = "$agent_report_envelope_line" ] || return 1
  [ "$(sed -n '2p' "$record_file")" = "BEGIN AGENT-REPORT-RECORD" ] || return 1
  [ "$(tail -n 11 "$record_file" | sed -n '2p')" = "END AGENT-REPORT-RECORD" ] || return 1
  [ "$(tail -n 11 "$record_file" | sed -n '10p')" = "RECORD-COMPLETE: true" ] || return 1
  [ "$(tail -n 1 "$record_file")" = "$agent_report_envelope_line" ] || return 1
  [ "$(sed -n '5p' "$record_file")" = "$(tail -n 11 "$record_file" | sed -n '5p')" ] || return 1
  [ "$(sed -n '6p' "$record_file")" = "$(tail -n 11 "$record_file" | sed -n '6p')" ] || return 1
  [ "$(sed -n '7p' "$record_file")" = "$(tail -n 11 "$record_file" | sed -n '7p')" ] || return 1
  [ "$(sed -n '8p' "$record_file")" = "$(tail -n 11 "$record_file" | sed -n '8p')" ] || return 1
  [ "$(sed -n '9p' "$record_file")" = "$(tail -n 11 "$record_file" | sed -n '9p')" ] || return 1
  [ "$(sed -n 's/^PAYLOAD-SHA256: //p' "$record_file" | head -n 1)" \
    = "$(agent_report_sha256_file "$payload_file")" ] || return 1
  [ "$(sed -n 's/^PAYLOAD-SIZE-BYTES: //p' "$record_file" | head -n 1)" \
    = "$(agent_report_file_size "$payload_file")" ] || return 1
}

agent_report_append_record() {
  local record_file="$1"
  local payload_file="$2"

  agent_report_validate_record "$record_file" "$payload_file" \
    || agent_report_fail 1 "report record envelope is invalid"
  for _ in $(seq 1 200); do
    if mkdir "$agent_report_lock_dir" 2>/dev/null; then
      agent_report_lock_acquired=true
      break
    fi
    [ -d "$agent_report_lock_dir" ] && [ ! -L "$agent_report_lock_dir" ] \
      || agent_report_fail 1 "report append lock is unsafe"
    sleep 0.01
  done
  [ "$agent_report_lock_acquired" = "true" ] || agent_report_fail 1 "report append is already active"
  chmod 700 "$agent_report_lock_dir"
  printf '%s\n' "$agent_report_lock_token" > "$agent_report_lock_dir/owner"
  chmod 600 "$agent_report_lock_dir/owner"

  if [ -e "$agent_report_file" ] || [ -L "$agent_report_file" ]; then
    agent_report_validate_existing_report "$agent_report_file" \
      || agent_report_fail 1 "existing report file is unsafe"
  fi

  agent_report_replacement="$(mktemp "$agent_report_dir/.${ticket_id}.report.XXXXXX")"
  chmod 600 "$agent_report_replacement"
  if [ -e "$agent_report_file" ]; then
    cat "$agent_report_file" >> "$agent_report_replacement"
    if [ -s "$agent_report_file" ] \
      && [ "$(agent_report_last_byte_decimal "$agent_report_file")" != "10" ]; then
      printf '\n' >> "$agent_report_replacement"
    fi
  fi
  cat "$record_file" >> "$agent_report_replacement"
  chmod 600 "$agent_report_replacement"
  agent_report_injected_failure before-destination-replacement
  sync
  mv -f "$agent_report_replacement" "$agent_report_file"
  agent_report_replacement=""
  chmod 600 "$agent_report_file"
  agent_report_release_lock
}
