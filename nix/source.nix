# Closed source boundary. Only the declared runtime and Go build owners from
# nix/distribution.json enter the store; tests, fixtures, private material and
# operator settings never do, even when the flake is evaluated from a path.
{ lib, root, distribution }:
let
  fs = lib.fileset;
  declared = paths: fs.unions (map (path: root + "/${path}") paths);
  developmentOnly = fs.fileFilter
    (file: lib.hasSuffix "_test.go" file.name
      || lib.hasSuffix ".pyc" file.name
      || builtins.elem file.name distribution.excluded_names)
    root;
in
fs.toSource {
  inherit root;
  fileset = fs.difference
    (declared ([ "nix/distribution.json" ] ++ distribution.runtime ++ distribution.go_sources))
    (fs.union (declared distribution.go_excluded) developmentOnly);
}
