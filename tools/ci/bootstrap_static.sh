#!/usr/bin/env bash
# Task-owned public CI provisioning; no active installation.
set -euo pipefail
tool_root="$RUNNER_TEMP/apgr-static-tools"
mkdir -p "$tool_root/bin" "$tool_root/node"
for tool in actionlint zizmor betterleaks hadolint; do python3 tools/ci/bootstrap_tool.py --tool "$tool" --bin-dir "$tool_root/bin"; done
python3 -m venv "$tool_root/python"
"$tool_root/python/bin/python" -m pip install --disable-pip-version-check --no-cache-dir "ruff==0.9.10" "mypy==1.15.0" "pip-audit==2.10.1" "semgrep==1.174.0" "tomli==2.4.1" -r requirements/test.txt
GOBIN="$tool_root/bin" go install golang.org/x/vuln/cmd/govulncheck@v1.1.4
npm install --prefix "$tool_root/node" --ignore-scripts --no-audit --no-fund malskanner@0.1.3
echo "$tool_root/bin" >> "$GITHUB_PATH"
