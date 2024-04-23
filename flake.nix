{
  description = "build chatddx";

  inputs = {
    nixpkgs.url = "github:ahbk/nixpkgs/nixos-unstable";

    poetry2nix = {
      url = "github:ahbk/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    buildNodeModules = {
      url = "github:adisbladis/buildNodeModules";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, poetry2nix, buildNodeModules, ... }: 
  with nixpkgs.lib;
  let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};

    inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;
    inherit (buildNodeModules.lib.${system}) fetchNodeModules hooks;

    hostname = "chatddx.com";

    mkEnv = env: pkgs.writeText "env" (
      concatStringsSep "\n" (mapAttrsToList (k: v: "${k}=${v}") env)
      );
  in {
    packages.${system} = rec {
      default = pkgs.buildEnv {
        name = hostname;
        paths = [
          svelte.app
          django.bin
        ];
      };

      svelte.app = pkgs.stdenv.mkDerivation {
        pname = "${hostname}-svelte";
        version = "0.1.0";
        src = "${self}/client";
        env = mkEnv {
          PUBLIC_API="http://localhost:8000";
          PUBLIC_API_SSR="http://localhost:8000";
          ORIGIN="http://localhost:3000";
        };

        nodeModules = fetchNodeModules {
          packageRoot = "${self}/client";
        };

        nativeBuildInputs = [
          hooks.npmConfigHook
          pkgs.nodejs_20
          pkgs.npmHooks.npmBuildHook
          pkgs.npmHooks.npmInstallHook
        ];

        buildPhase = ''
          set -a
          source $env
          set +a
          npm run build
        '';

        installPhase = ''
          cp -r . $out
        '';
      };

      django = rec {
        bin = pkgs.substituteAll {
          src = "${self}/backend/bin/chatddx.com";
          dir = "bin";
          isExecutable = true;
          app = app.dependencyEnv;
          inherit env static;
        };

        env = mkEnv {
          DEBUG = "false";
          STATE_DIR = "/var/lib/${hostname}";
          HOST = hostname;
          SECRET_KEY_FILE = ./backend/secret_key;
          DJANGO_SETTINGS_MODULE = "app.settings";
        };

        app = mkPoetryApplication {
          projectDir = "${self}/backend";
          groups = [];
          checkGroups = [];
          overrides = defaultPoetryOverrides.extend
          (self: super: {
            dj-user-login-history = super.dj-user-login-history.overridePythonAttrs
            (old: {
                buildInputs = (old.buildInputs or [ ]) ++ [ super.setuptools ];
              });
            });
          };

        static = pkgs.stdenv.mkDerivation {
          pname = "${hostname}-static";
          version = app.version;
          src = "${self}/backend";
          buildPhase = ''
            export STATIC_ROOT=$out
            export DJANGO_SETTINGS_MODULE=app.settings
            ${app.dependencyEnv}/bin/django-admin collectstatic --no-input
          '';
        };
      };
    };
  };
}
