{
  description = "build chatddx";

  inputs = {
    nixpkgs.url = "github:ahbk/nixpkgs/nixos-unstable";

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
      inherit (nixpkgs.lib) concatStringsSep mapAttrsToList composeManyExtensions;

      name = "chatddx";
      version = toString (self.shortRev or self.dirtyShortRev or self.lastModified or "unknown");
      apiRoot = ./backend;
      webRoot = ./client;
      python = pkgs.python312;

      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = apiRoot; };
      overlay = workspace.mkPyprojectOverlay {
        sourcePreference = "wheel";
      };

      mkEnv = env: pkgs.writeText "env" (concatStringsSep "\n" (mapAttrsToList (k: v: "${k}=${v}") env));

      derivations = {
        mypy =
          final:
          let
            venv = final.mkVirtualEnv "chatddx-backend-typing-env" {
              chatddx-backend = [ "typing" ];
            };
          in
          pkgs.stdenv.mkDerivation {
            name = "${final.chatddx-backend.name}-mypy";
            inherit (final.chatddx-backend) src;
            nativeBuildInputs = [
              venv
            ];
            dontConfigure = true;
            dontInstall = true;
            buildPhase = ''
              mkdir $out
              mypy --strict . --junit-xml $out/junit.xml
            '';
          };

        pytest =
          final:
          let
            venv = final.mkVirtualEnv "chatddx-backend-pytest-env" {
              chatddx-backend = [ "test" ];
            };
          in
          pkgs.stdenv.mkDerivation {
            name = "${final.chatddx-backend.name}-pytest";
            inherit (final.chatddx-backend) src;
            nativeBuildInputs = [
              venv
            ];

            dontConfigure = true;

            buildPhase = ''
              runHook preBuild
              pytest --cov tests --cov-report html tests
              runHook postBuild
            '';

            installPhase = ''
              runHook preInstall
              mv htmlcov $out
              runHook postInstall
            '';
          };
      };

      pyprojectOverrides = final: prev: {
        chatddx-backend = prev.chatddx-backend.overrideAttrs (old: {
          passthru = old.passthru // {
            tests =
              (old.tests or { }) // { mypy = derivations.mypy final; } // { pytest = derivations.pytest final; };
          };
        });
      };

      pythonSet =
        (pkgs.callPackage pyproject-nix.build.packages {
          inherit python;
        }).overrideScope
          (composeManyExtensions [
            pyproject-build-systems.overlays.default
            overlay
            pyprojectOverrides
          ]);
    in
    {
      checks.${system} = pythonSet.chatddx-backend.passthru.tests;

      packages.${system} = rec {
        default = pkgs.buildEnv {
          inherit name;
          paths = [
            svelte_app
            django_bin
          ];
        };

        svelte_app = pkgs.buildNpmPackage {
          pname = "${name}-web";
          inherit version;
          src = webRoot;
          env = mkEnv {
            PUBLIC_API = "http://localhost:8000";
            PUBLIC_API_SSR = "http://localhost:8000";
            ORIGIN = "http://localhost:3000";
          };

          npmDeps = pkgs.importNpmLock { npmRoot = webRoot; };
          npmConfigHook = pkgs.importNpmLock.npmConfigHook;

          buildPhase = ''
            set -a
            source $env
            set +a
            npm run build

            mkdir bin

            cat <<EOF > bin/run
            #!/usr/bin/env bash
            ${pkgs.nodejs}/bin/node $out/build
            EOF

            chmod +x bin/run
          '';

          installPhase = ''
            cp -r . $out
          '';
        };

        django_app = pythonSet.mkVirtualEnv "chatddx-api-env" workspace.deps.default;

        django_bin = pkgs.substituteAll {
          src = apiRoot + /src/chatddx_backend/bin/manage;
          dir = "bin";
          isExecutable = true;
          inherit django_env django_static django_app;
        };

        django_env = mkEnv {
          DEBUG = "true";
          DJANGO_SETTINGS_MODULE = "chatddx_backend.settings";
          HOST = "localhost";
          SCHEME = "http";
          SECRET_KEY_FILE = "./secret_key";
          STATE_DIR = "./";
        };

        django_static = pkgs.stdenv.mkDerivation {
          pname = "${name}-static";
          inherit version;
          src = apiRoot;
          buildPhase = ''
            export STATIC_ROOT=$out
            export DJANGO_SETTINGS_MODULE=chatddx_backend.settings
            ${django_app}/bin/django-admin collectstatic --no-input
          '';
        };
      };

      devShells.${system} =
        let
          editableOverlay = workspace.mkEditablePyprojectOverlay {
            root = "$REPO_ROOT/backend";
          };
          editablePythonSet = pythonSet.overrideScope (composeManyExtensions [
            editableOverlay
            (final: prev: {
              chatddx-backend = prev.chatddx-backend.overrideAttrs (old: {
                src = pkgs.lib.fileset.toSource {
                  root = old.src;
                  fileset = pkgs.lib.fileset.unions [
                    (old.src + "/pyproject.toml")
                    (old.src + "/README.md")
                    (old.src + "/src/chatddx_backend/__init__.py")
                  ];
                };
                nativeBuildInputs =
                  old.nativeBuildInputs
                  ++ final.resolveBuildSystem {
                    editables = [ ];
                  };
              });
            })
          ]);
          venv = editablePythonSet.mkVirtualEnv "chatddx-backend-dev-env" {
            chatddx-backend = [ "dev" ];
          };
        in
        rec {
          default = uv2nix;
          uv2nix = pkgs.mkShell {
            inherit name;
            packages = [
              venv
              pkgs.uv
              pkgs.nodejs
            ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = "${venv}/bin/python";
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              export REPO_ROOT=$(git rev-parse --show-toplevel)
              unset PYTHONPATH
              echo "flake: ${version}"
              echo "nixpkgs: ${nixpkgs.shortRev}"
              set -a
              source ./backend/.env
              set +a
            '';
          };
          old = pkgs.mkShell {
            inherit name;
            packages = [
              pkgs.uv
            ];
            shellHook = ''
              echo "flake: ${version}"
              echo "nixpkgs: ${nixpkgs.shortRev}"
              set -a
              source ./backend/.env
              set +a
            '';
          };
        };
    };
}
