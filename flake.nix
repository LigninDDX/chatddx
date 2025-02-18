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

      pyprojectOverrides = _final: _prev: {
        # Implement build fixups here.
        # Note that uv2nix is _not_ using Nixpkgs buildPythonPackage.
        # It's using https://pyproject-nix.github.io/pyproject.nix/build.html
      };

      pythonSet =
        # Use base package set from pyproject.nix builders
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
      packages.${system} = rec {
        default = pkgs.buildEnv {
          inherit name;
          paths = [
            svelte.app
            django.app
          ];
        };

        svelte.app = pkgs.buildNpmPackage {
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

        django = rec {
          app = pythonSet.mkVirtualEnv "chatddx-api-env" workspace.deps.default;

          bin = pkgs.substituteAll {
            src = apiRoot + /bin/manage;
            dir = "bin";
            isExecutable = true;
            depEnv = app;
            inherit env static app;
          };

          env = mkEnv {
            DEBUG = "true";
            DJANGO_SETTINGS_MODULE = "app.settings";
            HOST = "localhost";
            SCHEME = "http";
            SECRET_KEY_FILE = "./secret_key";
            STATE_DIR = "./";
          };

          static = pkgs.stdenv.mkDerivation {
            pname = "${name}-static";
            inherit version;
            src = apiRoot;
            buildPhase = ''
              export STATIC_ROOT=$out
              export DJANGO_SETTINGS_MODULE=app.settings
              ${app}/bin/django-admin collectstatic --no-input
            '';
          };
        };
      };

      devShells.${system} = with self.packages.${system}; {
        default = pkgs.mkShell {
          inherit name;
          packages = [
            default
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
