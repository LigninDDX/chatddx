{
  description = "build chatddx";

  inputs = {
    nixpkgs.url = "github:kompismoln/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";

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
      flake-utils,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        inherit (nixpkgs) lib;

        name = "chatddx";
        version = toString (self.shortRev or self.dirtyShortRev or self.lastModified or "unknown");
        apiRoot = ./backend;
        webRoot = ./client;
        python = pkgs.python312;

        pkgs = nixpkgs.legacyPackages.${system};

        workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = apiRoot; };
        overlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel";
        };

        pyprojectOverrides = _final: _prev: { };

        pythonSet =
          (pkgs.callPackage pyproject-nix.build.packages {
            inherit python;
          }).overrideScope
            (
              lib.composeManyExtensions [
                pyproject-build-systems.overlays.default
                overlay
                pyprojectOverrides
              ]
            );

        svelte-env = {
          PUBLIC_API = "http://localhost:8000";
          PUBLIC_API_SSR = "http://localhost:8000";
          ORIGIN = "http://localhost:3000";
        };

        svelte-app = pkgs.buildNpmPackage {
          pname = "${name}-web";
          inherit version;
          src = webRoot;
          env = svelte-env;
          npmDeps = pkgs.importNpmLock { npmRoot = webRoot; };
          npmConfigHook = pkgs.importNpmLock.npmConfigHook;

          buildPhase = ''
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

        django-app = pythonSet.mkVirtualEnv "${name}-django-app" workspace.deps.default;

        mkDjangoManage =
          {
            runtimeEnv ? { },
            ...
          }:
          pkgs.writeShellApplication {
            name = "${name}-django-manage";
            text = builtins.readFile (apiRoot + /src/chatddx_backend/bin/manage);
            runtimeEnv = django-env // runtimeEnv;
          };

        django-manage = mkDjangoManage { };

        django-static = pkgs.stdenv.mkDerivation {
          pname = "${name}-django-static";
          inherit version;
          src = apiRoot;
          buildPhase = ''
            export STATIC_ROOT=$out
            export DJANGO_SETTINGS_MODULE=chatddx_backend.settings
            ${django-app}/bin/django-admin collectstatic --no-input
          '';
        };

        django-env = {
          DEBUG = "true";
          DJANGO_SETTINGS_MODULE = "chatddx_backend.settings";
          HOST = "localhost";
          SCHEME = "http";
          SECRET_KEY_FILE = "./secret_key";
          STATE_DIR = "./";
          DJANGO_APP = django-app;
          DJANGO_STATIC = django-static;
        };
      in
      {
        packages = {
          inherit
            django-app
            django-static
            django-manage
            svelte-app
            ;
        };

        lib = {
          inherit mkDjangoManage;
        };

        devShells = {
          default = pkgs.mkShell {
            inherit name;
            packages = [
              django-manage
              pkgs.uv
            ];
            env = django-env // svelte-env;
            shellHook = ''
              echo "flake: ${version}"
              echo "nixpkgs: ${nixpkgs.shortRev}"
            '';
          };
        };
      }
    );
}
