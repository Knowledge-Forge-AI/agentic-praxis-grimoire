{
  description = "Agentic Praxis Grimoire (APGR): skills, portable Go CLI and dispatcher runtime";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";

  outputs = { self, nixpkgs }:
    let
      distribution = builtins.fromJSON (builtins.readFile ./nix/distribution.json);
      forAllSystems = nixpkgs.lib.genAttrs (builtins.attrNames distribution.systems);
      src = import ./nix/source.nix { inherit (nixpkgs) lib; root = ./.; inherit distribution; };
      app = system: command: {
        type = "app";
        program = "${self.packages.${system}.default}/bin/${command}";
        meta.description = "APGR ${command} from the installed runtime";
      };
    in
    {
      packages = forAllSystems (system:
        let
          package = nixpkgs.legacyPackages.${system}.callPackage ./nix/package.nix {
            inherit src distribution;
            goTarget = distribution.systems.${system};
          };
        in
        {
          default = package;
          agentic-praxis-grimoire = package;
          apgr = package;
        });

      apps = forAllSystems (system: {
        default = app system "apgr";
        apgr = app system "apgr";
        agent-phase-dispatch = app system "agent-phase-dispatch";
        apgr-dispatcher-bundle = app system "apgr-dispatcher-bundle";
      });

      checks = forAllSystems (system: import ./nix/checks.nix {
        pkgs = nixpkgs.legacyPackages.${system};
        package = self.packages.${system}.default;
        goTarget = distribution.systems.${system};
        inherit src system;
      });
    };
}
