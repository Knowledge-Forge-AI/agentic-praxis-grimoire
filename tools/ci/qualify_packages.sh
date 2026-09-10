#!/usr/bin/env bash
# Task-owned public CI provisioning; no active installation.
set -euo pipefail
pkg_root="$RUNNER_TEMP/apgr-packages"
mkdir -p "$pkg_root/npm-a" "$pkg_root/npm-work-a" "$pkg_root/npm-b" "$pkg_root/npm-work-b"
python3 bin/apg-build-python-release-bundle build --source "$GITHUB_WORKSPACE" --output "$pkg_root/python" --work-root "$pkg_root/python-work" --python "$(command -v python3)"
python3 libexec/apg_npm_distribution.py build --source "$GITHUB_WORKSPACE" --artifact-root "$pkg_root/python-work/build-a/binaries" --output "$pkg_root/npm-a" --work-root "$pkg_root/npm-work-a"
python3 libexec/apg_npm_distribution.py build --source "$GITHUB_WORKSPACE" --artifact-root "$pkg_root/python-work/build-b/binaries" --output "$pkg_root/npm-b" --work-root "$pkg_root/npm-work-b"
diff -ru "$pkg_root/npm-a" "$pkg_root/npm-b"
python3 libexec/apg_distribution_candidate.py build --source-root "$GITHUB_WORKSPACE" --go-artifacts "$pkg_root/python-work/build-a/binaries" --python-artifacts "$pkg_root/python" --npm-artifacts "$pkg_root/npm-a" --output "$pkg_root/manifest"
python3 libexec/apg_distribution_candidate.py check --source-root "$GITHUB_WORKSPACE" --go-artifacts "$pkg_root/python-work/build-a/binaries" --python-artifacts "$pkg_root/python" --npm-artifacts "$pkg_root/npm-a" --manifest "$pkg_root/manifest/apg-distribution-manifest.json"
mkdir -p "$RUNNER_TEMP/deliverables"
cp -R "$pkg_root/python-work/build-a/binaries" "$RUNNER_TEMP/deliverables/go"
mkdir -p "$RUNNER_TEMP/deliverables/python"
cp "$pkg_root/python"/*.whl "$pkg_root/python"/*.tar.gz "$RUNNER_TEMP/deliverables/python/"
cp -R "$pkg_root/npm-a" "$RUNNER_TEMP/deliverables/npm"
cp "$pkg_root/manifest/apg-distribution-manifest.json" "$pkg_root/manifest/SHA256SUMS" "$RUNNER_TEMP/deliverables/"
(cd "$RUNNER_TEMP/deliverables" && sha256sum --check SHA256SUMS)
python3 bin/apg-public-release manifest --source "$GITHUB_WORKSPACE" --version 0.11.0 --format json > "$RUNNER_TEMP/public-projection-manifest.json"
python3 -m venv "$pkg_root/python-install"
"$pkg_root/python-install/bin/python" -m pip install --no-index --no-deps "$pkg_root/python/agentic_praxis_grimoire-0.11.0-py3-none-manylinux_2_17_x86_64.whl"
"$pkg_root/python-install/bin/apgr" --version
"$pkg_root/python-install/bin/apgr" report verify "$GITHUB_WORKSPACE/report/testdata/persisted/diff.report.txt"
mkdir -p "$pkg_root/npm-install"
printf '%s\n' '{"name":"apgr-ci-install","private":true}' > "$pkg_root/npm-install/package.json"
npm install --prefix "$pkg_root/npm-install" --ignore-scripts --offline --no-audit --no-fund --package-lock=false "$pkg_root/npm-a/knowledge-forge-ai-apgr-0.11.0.tgz" "$pkg_root/npm-a/knowledge-forge-ai-apgr-linux-x64-0.11.0.tgz"
"$pkg_root/npm-install/node_modules/.bin/apgr" --version
"$pkg_root/npm-install/node_modules/.bin/apgr" report verify "$GITHUB_WORKSPACE/report/testdata/persisted/diff.report.txt"
test -z "$(git status --porcelain --untracked-files=all)"
