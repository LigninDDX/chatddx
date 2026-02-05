{
  description = "build chatddx";
  inputs = {
    nixpkgs.url = "github:kompismoln/nixpkgs/nixos-unstable"; # org-wide version pin
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
    }:
    let
      name = "chatddx";
      inherit (nixpkgs) lib;
      pyprojectToml = fromTOML (builtins.readFile ./backend/pyproject.toml);
      djangoApp = builtins.replaceStrings [ "-" ] [ "_" ] pyprojectToml.project.name;
      version = toString (self.shortRev or self.dirtyShortRev or self.lastModified or "unknown");
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./backend; };
      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };
      editableOverlay = workspace.mkEditablePyprojectOverlay {
        root = "$BACKEND_ROOT";
      };
      pythonSets = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python312;
        in
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
          (
            lib.composeManyExtensions [
              pyproject-build-systems.overlays.wheel
              overlay
            ]
          )
      );
    in
    {
      inherit workspace pythonSets;

      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        rec {
          svelte-app = pkgs.stdenv.mkDerivation {
            pname = "${name}-client";
            inherit version;
            src = ./client;

            nativeBuildInputs = with pkgs; [
              nodejs
              pnpm
              pnpmConfigHook
              makeWrapper
            ];

            pnpmDeps = pkgs.fetchPnpmDeps {
              pname = name;
              src = ./client;
              fetcherVersion = 2;
              hash = "sha256-gQPPm/ymE1nuXQdFqRtQIgR7ON3EFV0c7De+F34dRKc=";
            };

            buildPhase = ''
              runHook preBuild
              pnpm build
              runHook postBuild
            '';

            installPhase = ''
              mkdir -p $out/{lib,bin}
              cp -r build $out/lib/
              makeWrapper ${pkgs.nodejs}/bin/node $out/bin/run \
                --add-flags "$out/lib/build/index.js" \
                --set NODE_ENV production
            '';
          };

          # workspace.deps.default excludes dev/test dependency-groups
          django-app = pythonSets.${system}.mkVirtualEnv "${name}-django-${version}" workspace.deps.default;

          django-manage = pkgs.writeShellApplication {
            name = "${name}-django-manage-${version}";
            # manage is also a stand-alone script
            text = builtins.readFile ./backend/src/${djangoApp}/bin/manage;
          };

          django-static = pkgs.stdenv.mkDerivation {
            pname = "${name}-django-static";
            inherit version;
            src = ./backend;
            buildPhase = ''
              export STATIC_ROOT=$out
              export DJANGO_SETTINGS_MODULE=${djangoApp}.settings
              ${django-app}/bin/django-admin collectstatic --no-input
            '';
            installPhase = ":";
          };
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonSet = pythonSets.${system}.overrideScope editableOverlay;
          # workspace.deps.all includes dev/test dependency-groups
          venv = pythonSet.mkVirtualEnv "${name}-venv" workspace.deps.all;
        in
        {
          default = pkgs.mkShell {
            inherit name;
            packages = [
              (pkgs.writeScriptBin "npm" ''echo "use pnpm"'')
              (pkgs.writeScriptBin "npx" ''echo "use pnpm dlx"'')
              venv
              pkgs.pnpm
              pkgs.uv
              pkgs.nodejs
            ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = pythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              unset PYTHONPATH
              export BACKEND_ROOT=$(git rev-parse --show-toplevel)/backend
              set -a
              [ -f backend/.env ] && source backend/.env
              [ -f client/.env ] && source client/.env
              set +a
              echo "flake: ${version}"
              echo "nixpkgs: ${nixpkgs.shortRev}"
            '';
          };
        }
      );
    };
}
