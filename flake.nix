{
  description = "deploy chatddx";

  inputs = {
    nixpkgs.url = "github:ahbk/nixpkgs/nixos-unstable";
    nixpkgs-stable.url = "github:ahbk/nixpkgs/nixos-23.11";

    poetry2nix = {
      url = "github:ahbk/poetry2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, poetry2nix, ... }: 
  with nixpkgs.lib;
  let
    system = "x86_64-linux";
    pkgs = nixpkgs.legacyPackages.${system};
    inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication defaultPoetryOverrides;
    mkEnv = env: pkgs.writeText "env" (
      concatStringsSep "\n" (mapAttrsToList (k: v: "${k}=${v}") env)
      );
  in {
    packages.${system} = rec {

      default = chatddx-bin;

      chatddx-bin = pkgs.substituteAll {
        src = "${self}/bin/chatddx";
        dir = "bin";
        isExecutable = true;
        chatddx_static = chatddx-static;
        chatddx_site = chatddx-site;
        chatddx_env = chatddx-env;
      };

      chatddx-env = mkEnv {
        secret_key_file = "/tmp/chatddx/secret_key";
        user = "test";
        db = "test";
        log_level = "info";
        env = "test";
        host = "*";
        allowed_origins = "*";
        db_root = "/tmp/chatddx/db/";
        DJANGO_SETTINGS_MODULE = "chatddx.settings";
      };

      chatddx-static = pkgs.stdenv.mkDerivation {
        pname = "chatddx-static";
        version = "0.1.0";
        src = self;
        buildPhase = ''
          echo "key" > ./secret_key

          export static_root=$out/static
          export DJANGO_SETTINGS_MODULE=chatddx.settings
          export secret_key_file=./secret_key

          ${chatddx-site}/bin/django-admin collectstatic --no-input
        '';
      };

      chatddx-site = let
        app = mkPoetryApplication {
          projectDir = self;
          overrides = defaultPoetryOverrides.extend
          (self: super: {
            dj-user-login-history = super.dj-user-login-history.overridePythonAttrs
            (
              old: {
                buildInputs = (old.buildInputs or [ ]) ++ [ super.setuptools ];
              }
              );
            });
        };
      in app.dependencyEnv;

    };

    nixosModules.default = { config, lib, ... }:
    let
      cfg = config.chatddx;
      inherit (lib) mkOption types mkIf;
      inherit (self.packages.${system}) chatddx-bin chatddx-site chatddx-static;

      chatddx-prod-env = mkEnv {
        secret_key_file = cfg.secret_key_file;
        user = cfg.host;
        db = cfg.host;
        env = "prod";
        log_level = "error";
        host = cfg.host;
        db_root = "/var/db/${cfg.host}/";
        DJANGO_SETTINGS_MODULE = "chatddx.settings";
      }; 

      chatddx-prod-bin = chatddx-bin.overrideAttrs{
        chatddx_env = chatddx-prod-env;
      };

    in {

      options.chatddx = {
        enable = mkOption {
          type = types.bool;
          default = false;
        };

        host = mkOption {
          type = types.str;
        };

        port = mkOption {
          type = types.str;
        };

        uid = mkOption {
          type = types.int;
        };

        secret_key_file = mkOption {
          type = types.path;
        };
      };

      config = mkIf cfg.enable {
        environment = {
          systemPackages = [ chatddx-prod-bin ];
        };

        services.nginx = {
          enable = true;
          virtualHosts.${cfg.host} = {
            forceSSL = true;
            enableACME = true;

            locations = {
              "/" = {
                recommendedProxySettings = true;
                proxyPass = "http://localhost:8001";
              };
              "/static" = {
                root = chatddx-static;
              };
            };
          };
        };

        users = rec {
          users.${cfg.host} = {
            isSystemUser = true;
            group = cfg.host;
            uid = cfg.uid;
          };
          groups.${cfg.host}.gid = users.${cfg.host}.uid;

        };

        systemd.services.chatddx-setup = {
          description = "setup ${cfg.host}";
          serviceConfig = {
            Type = "oneshot";
            ExecStartPre = [
              "+-${pkgs.coreutils}/bin/mkdir -p /var/db/${cfg.host}"
              "+${pkgs.coreutils}/bin/chown ${cfg.host}:${cfg.host} /var/db/${cfg.host}"
            ];
            ExecStart = "${chatddx-site}/bin/setup";
            User = cfg.host;
            Group = cfg.host;
            EnvironmentFile="${chatddx-prod-env}";
          };
          wantedBy = [ "multi-user.target" ];
          before = [ "chatddx-site.service" ];
        };

        systemd.services.chatddx-site = {
          description = "manage ${cfg.host}";
          serviceConfig = {
            ExecStart = "${chatddx-site}/bin/gunicorn chatddx.wsgi:application --bind 0.0.0.0:${cfg.port}";
            User = cfg.host;
            Group = cfg.host;
            EnvironmentFile="${chatddx-prod-env}";
          };
          wantedBy = [ "multi-user.target" ];
        };
      };
    };
  };
}
