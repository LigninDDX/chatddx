{
  description = "build chatddx";

  inputs = {
    nixpkgs.url = "github:ahbk/nixpkgs/nixos-unstable";

    poetry2nix = {
      url = "github:nix-community/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      poetry2nix,
    }:
    let
      inherit (nixpkgs.lib) concatStringsSep mapAttrsToList;
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;

      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      name = "chatddx";
      version = toString (self.shortRev or self.dirtyShortRev or self.lastModified or "unknown");

      mkEnv = env: pkgs.writeText "env" (concatStringsSep "\n" (mapAttrsToList (k: v: "${k}=${v}") env));
    in
    {
      packages.${system} = rec {
        default = pkgs.buildEnv {
          inherit name;
          paths = [
            svelte.app
            django.bin
          ];
        };

        svelte.app = pkgs.buildNpmPackage {
          pname = "${name}-web";
          inherit version;
          src = ./client;
          env = mkEnv {
            PUBLIC_API = "http://localhost:8000";
            PUBLIC_API_SSR = "http://localhost:8000";
            ORIGIN = "http://localhost:3000";
          };

          npmDeps = pkgs.importNpmLock { npmRoot = ./client; };
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
          app = mkPoetryApplication {
            projectDir = ./backend;
            groups = [ ];
            checkGroups = [ ];
            overrides = defaultPoetryOverrides.extend (
              final: prev: {
                dj-user-login-history = prev.dj-user-login-history.overridePythonAttrs (old: {
                  buildInputs = (old.buildInputs or [ ]) ++ [ prev.setuptools ];
                });
              }
            );
          };

          bin = pkgs.substituteAll {
            src = ./backend/bin/manage;
            dir = "bin";
            isExecutable = true;
            depEnv = app.dependencyEnv;
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
            src = ./backend;
            buildPhase = ''
              export STATIC_ROOT=$out
              export DJANGO_SETTINGS_MODULE=app.settings
              ${app.dependencyEnv}/bin/django-admin collectstatic --no-input
            '';
          };
        };
      };

      devShells.${system} = with self.packages.${system}; {
        default = pkgs.mkShell {
          inherit name;
          packages = [
            default
            django.app.dependencyEnv
          ];
          shellHook = ''
            echo "flake: ${version}"
            echo "nixpkgs: ${nixpkgs.shortRev}"
            set -a
            source ${django.env}
            set +a
          '';
        };
      };
    };
}
