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
      inherit (nixpkgs) lib;
      name = "chatddx";
      version = toString (self.shortRev or self.dirtyShortRev or self.lastModified or "unknown");
      apiRoot = ./backend;
      webRoot = ./client;
      forAllSystems = lib.genAttrs lib.systems.flakeExposed;
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = apiRoot; };
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
      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          src = webRoot;
        in
        rec {
          svelte-app = pkgs.stdenv.mkDerivation {
            pname = "${name}-client";
            inherit src version;

            nativeBuildInputs = with pkgs; [
              nodejs
              pnpm
              pnpmConfigHook
              makeWrapper
            ];

            pnpmDeps = pkgs.fetchPnpmDeps {
              pname = name;
              inherit src version;
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
          django-app = pythonSets.${system}.mkVirtualEnv "${name}-django-app" workspace.deps.default;

          django-manage = pkgs.writeShellApplication {
            name = "${name}-django-manage";
            # manage is also a stand-alone script
            text = builtins.readFile (apiRoot + /src/chatddx_backend/bin/manage);
          };

          django-static = pkgs.stdenv.mkDerivation {
            pname = "${name}-django-static";
            inherit version;
            src = apiRoot;
            buildPhase = ''
              export STATIC_ROOT=$out
              export DJANGO_SETTINGS_MODULE=${name}_backend.settings
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
