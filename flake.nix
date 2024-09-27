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
      ...
    }:
    let
      inherit (nixpkgs.lib) concatStringsSep mapAttrsToList;
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;

      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      hostname = "chatddx.com";

      mkEnv = env: pkgs.writeText "env" (concatStringsSep "\n" (mapAttrsToList (k: v: "${k}=${v}") env));
    in
    {
      packages.${system} = rec {
        default = pkgs.buildEnv {
          name = hostname;
          paths = [
            svelte.app
            django.bin
          ];
        };

        svelte.app = pkgs.buildNpmPackage {
          pname = "${hostname}-svelte";
          version = "0.1.0";
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
          bin = pkgs.substituteAll {
            src = ./backend/bin/chatddx.com;
            dir = "bin";
            isExecutable = true;
            depEnv = app.dependencyEnv;
            inherit env static app;
          };

          env = mkEnv {
            DEBUG = "false";
            DJANGO_SETTINGS_MODULE = "app.settings";
            HOST = hostname;
            SECRET_KEY_FILE = ./backend/secret_key;
            STATE_DIR = "/var/lib/${hostname}";
          };

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

          static = pkgs.stdenv.mkDerivation {
            pname = "${hostname}-static";
            version = app.version;
            src = ./backend;
            buildPhase = ''
              export STATIC_ROOT=$out
              export DJANGO_SETTINGS_MODULE=app.settings
              ${app.dependencyEnv}/bin/django-admin collectstatic --no-input
            '';
          };
        };
      };

      devShells.${system} = {
        default = pkgs.mkShell {
          name = "chatddx.com";
          packages = with self.packages.${system}; [
            default
            django.app.dependencyEnv
          ];
          shellHook = '''';
        };
      };

    };
}
