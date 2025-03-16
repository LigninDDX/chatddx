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
      backendRoot = ./backend;
      clientRoot = ./client;
      siteRoot = ./site;
      python = pkgs.python312;

      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = backendRoot; };
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
    rec {
      checks.${system} = pythonSet.chatddx-backend.passthru.tests;

      djangoPkgs.${system} = {
        bin = packages.${system}.django_bin;
        static = packages.${system}.django_static;
        app = packages.${system}.django_app;
        env = packages.${system}.django_env;
      };

      packages.${system} = rec {
        default = pkgs.buildEnv {
          inherit name;
          paths = [
            svelte
            django_bin
            site
          ];
        };

        site = pkgs.buildNpmPackage {
          pname = "${name}-site";
          inherit version;
          src = siteRoot;

          npmDeps = pkgs.importNpmLock { npmRoot = siteRoot; };
          npmConfigHook = pkgs.importNpmLock.npmConfigHook;

          buildPhase = ''
            npm run build
          '';

          installPhase = ''
            cp -r ./build $out
          '';
        };
        svelte = pkgs.buildNpmPackage {
          pname = "${name}-web";
          inherit version;
          src = clientRoot;
          env = mkEnv {
            PUBLIC_API = "http://localhost:8000";
            PUBLIC_API_SSR = "http://localhost:8000";
            ORIGIN = "http://localhost:3000";
          };

          npmDeps = pkgs.importNpmLock { npmRoot = clientRoot; };
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
          src = backendRoot + /src/chatddx_backend/bin/manage;
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
          src = backendRoot;
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
          default = pkgs.mkShell {
            inherit name;
            pakages = [
              self.packages.${system}.default
            ];
            inputsFrom = [
              uv2nix-env
              node-env
            ];
            shellHook = ''
              echo "flake: ${version}"
              echo "nixpkgs: ${nixpkgs.shortRev}"
              ${uv2nix-env.shellHook}
              ${node-env.shellHook}
            '';
          };
          node-env = pkgs.mkShell {
            inherit name;
            packages = [
              pkgs.nodejs
            ];
            shellHook = '''';
          };
          uv2nix-env = pkgs.mkShell {
            inherit name;
            packages = [
              venv
              pkgs.uv
            ];
            env = {
              UV_NO_SYNC = "1";
              UV_PYTHON = "${venv}/bin/python";
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              export REPO_ROOT=$(git rev-parse --show-toplevel)
              unset PYTHONPATH
              set -a
              source ./backend/.env
              set +a
            '';
          };
        };
    };
}
