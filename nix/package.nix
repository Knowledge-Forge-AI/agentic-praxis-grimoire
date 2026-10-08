# APGR installed runtime: the portable Go `apgr`, the Python front door and
# the existing dispatcher runtime, wrapped from one immutable store tree.
# The Go binary is built by the repository's own deterministic builder so
# version, corpus and build-flag identity are not re-expressed here.
{ lib, stdenv, go_1_25, python313, bash, git, makeWrapper
, src, distribution, goTarget }:
let
  version = lib.fileContents (src + "/src/agentic_praxis_grimoire/VERSION");
  runtimePath = [ python313 bash ];
in
assert builtins.match "[0-9A-Za-z.+-]+" version != null;
stdenv.mkDerivation {
  pname = distribution.package;
  inherit version src;

  nativeBuildInputs = [ go_1_25 python313 makeWrapper ];
  # patchShebangs resolves `env python3` and `env bash` against these.
  buildInputs = runtimePath;

  PYTHONDONTWRITEBYTECODE = "1";
  dontConfigure = true;
  # The binary must stay byte-identical to its manifest.
  dontStrip = true;
  dontPatchELF = true;

  buildPhase = ''
    runHook preBuild
    export HOME="$TMPDIR/home" GOCACHE="$TMPDIR/go-cache" GOPATH="$TMPDIR/go" GOPROXY=off
    python3 -B bin/apg-build-go-cli --target ${goTarget} \
      --output "$TMPDIR/go-out/apgr" --manifest "$TMPDIR/go-out/apgr.binary-manifest.json"
    runHook postBuild
  '';

  # Git is a PATH suffix fallback: an operator-selected Git wrapper must win
  # for the operator repositories the dispatcher works on.
  installPhase = ''
    runHook preInstall
    runtime="$out/share/agentic-praxis-grimoire/runtime"
    for entry in ${lib.escapeShellArgs distribution.runtime}; do
      mkdir -p "$runtime/$(dirname "$entry")"
      cp -R "$entry" "$runtime/$entry"
    done
    install -Dm0555 "$TMPDIR/go-out/apgr" "$runtime/src/agentic_praxis_grimoire/bin/apgr"
    install -Dm0444 "$TMPDIR/go-out/apgr.binary-manifest.json" \
      "$runtime/src/agentic_praxis_grimoire/bin/apgr.binary-manifest.json"
    for command in ${lib.escapeShellArgs distribution.commands}; do
      makeWrapper "$runtime/bin/$command" "$out/bin/$command" \
        --prefix PATH : "$runtime/bin:${lib.makeBinPath runtimePath}" \
        --suffix PATH : "${lib.makeBinPath [ git ]}" \
        --unset PYTHONPATH --unset PYTHONHOME --set PYTHONDONTWRITEBYTECODE 1
    done
    runHook postInstall
  '';

  # The marker digests the final tree, so it is written after patchShebangs.
  postFixup = ''
    python3 -B "$out/share/agentic-praxis-grimoire/runtime/libexec/apg_nix_distribution.py" \
      write-marker --runtime "$out/share/agentic-praxis-grimoire/runtime"
  '';

  meta = {
    description = "Agentic Praxis Grimoire skills, portable Go CLI and dispatcher runtime";
    homepage = "https://github.com/Knowledge-Forge-AI/agentic-praxis-grimoire";
    license = lib.licenses.agpl3Plus;
    mainProgram = "apgr";
    platforms = builtins.attrNames distribution.systems;
  };
}
