# Checks exercise the exact built store output, never the source checkout.
{ pkgs, package, src, system, goTarget }:
let
  python = "${pkgs.python313}/bin/python3 -B";
  toolchain = pkgs.lib.importJSON ./go-toolchain.json;
  verify = candidate: pkgs.runCommand "apgr-installed-runtime-check" { } ''
    ${python} ${src}/libexec/apg_nix_distribution.py verify-installed \
      --package ${candidate} --source ${src} --system ${system}
    touch "$out"
  '';
  # Remove one required dispatcher resource; the verifier must refuse it.
  missingRoute = package.overrideAttrs (_: {
    postInstall = ''rm "$out/share/agentic-praxis-grimoire/runtime/common/dispatcher/routes.toml"'';
  });
in
{
  compiler-identity = pkgs.runCommand "apgr-compiler-identity" { } ''
    export HOME="$TMPDIR" GOTOOLCHAIN=local
    test "$(${package.goCompiler}/bin/go env GOVERSION)" = "go${toolchain.version}"
    binary=${package}/share/agentic-praxis-grimoire/runtime/src/agentic_praxis_grimoire/bin/apgr
    test "$(${package.goCompiler}/bin/go version "$binary")" = "$binary: go${toolchain.version}"
    ${package.goCompiler}/bin/go env GOVERSION GOROOT GOTOOLCHAIN > "$out"
    ${package.goCompiler}/bin/go version -m "$binary" >> "$out"
  '';

  installed-runtime = verify package;

  installed-smoke = pkgs.runCommand "apgr-installed-smoke" {
    nativeBuildInputs = [ pkgs.coreutils pkgs.git ];
  } ''
    export HOME="$TMPDIR/check-home"
    mkdir -p "$HOME"
    cd "$(mktemp -d)"
    ${python} ${src}/libexec/apg_nix_smoke.py --package ${package} --target ${goTarget} > "$out"
  '';

  negative-control = pkgs.runCommand "apgr-negative-control" {
    failed = pkgs.testers.testBuildFailure (verify missingRoute);
  } ''
    grep -F "missing runtime file: common/dispatcher/routes.toml" "$failed/testBuildFailure.log"
    touch "$out"
  '';
}
