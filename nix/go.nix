# Compiler-only source override; the locked package supplies its bootstrap.
{ lib, go_1_26, fetchurl }:
let
  toolchain = lib.importJSON ./go-toolchain.json;
in
assert lib.versions.majorMinor toolchain.version == lib.versions.majorMinor go_1_26.version;
go_1_26.overrideAttrs (_: {
  inherit (toolchain) version;
  src = fetchurl { inherit (toolchain.source) url sha256; };
})
