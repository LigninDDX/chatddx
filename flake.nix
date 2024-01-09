{
  description = "deploy chatddx";

  inputs = {
    my-nixos.url = "github:ahbk/my-nixos";
    nixpkgs.follows = "my-nixos/nixpkgs";
    nixpkgs-stable.follows = "my-nixos/nixpkgs-stable";

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
    inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) mkPoetryApplication;
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
        chatddx_site = chatddx-site;
        chatddx_env = chatddx-env;
      };

      chatddx-env = mkEnv {
        secret_key = "secret-key-test-env";
        user = "test";
        db = "test";
        log_level = "info";
        env = "test";
        host = "*";
        allowed_origins = "*";
        static_root = "/tmp/chatddx/static/";
        db_root = "/tmp/chatddx/db/";
        DJANGO_SETTINGS_MODULE = "mysite.settings";
      };

      chatddx-site = let
        app = mkPoetryApplication {
          projectDir = self;
        };
      in app.dependencyEnv;

    };

    nixosModules.default = { config, lib, ... }:
    let
      cfg = config.chatddx;
      inherit (lib) mkOption types mkIf;
      inherit (self.packages.${system}) chatddx-bin chatddx-site;

      chatddx-prod-env = mkEnv {
        secret_key_file = cfg.secret_key_file;
        user = cfg.user;
        db = cfg.user;
        env = "prod";
        log_level = "error";
        host = cfg.hostname;
        static_root = "${cfg.www_root}/static/";
        db_root = "${cfg.db_root}/";
        DJANGO_SETTINGS_MODULE = "mysite.settings";
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

        user = mkOption {
          type = types.str;
        };

        www_root = mkOption {
          type = types.str;
        };

        hostname = mkOption {
          type = types.str;
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
          virtualHosts.${cfg.hostname} = {
            forceSSL = true;
            enableACME = true;

            locations = {
              "/" = {
                recommendedProxySettings = true;
                proxyPass = "http://localhost:8000";
              };
              "/static" = {
                root = cfg.www_root;
              };
            };
          };
        };
        security.acme = {
          acceptTerms = true;
          defaults.email = "alxhbk@proton.me";
        };
        networking.firewall.allowedTCPPorts = [ 80 443 ];

        users = rec {
          users.${cfg.user} = {
            isSystemUser = true;
            group = cfg.user;
            uid = 994;
          };
          groups.${cfg.user}.gid = users.${cfg.user}.uid;

        };

        systemd.services.chatddx-setup = {
          description = "setup chatddx";
          serviceConfig = {
            Type = "oneshot";
            ExecStartPre = [
              "+-${pkgs.coreutils}/bin/mkdir -p ${cfg.www_root}"
              "+${pkgs.coreutils}/bin/chown ${cfg.user}:${cfg.user} ${cfg.www_root}"
            ];
            ExecStart = "${chatddx-site}/bin/setup";
            User = cfg.user;
            Group = cfg.user;
            EnvironmentFile="${chatddx-prod-env}";
          };
          wantedBy = [ "multi-user.target" ];
          before = [ "chatddx-site.service" ];
        };

        systemd.services.chatddx-site = {
          description = "manage chatddx-site";
          serviceConfig = {
            ExecStart = "${chatddx-site}/bin/gunicorn mysite.asgi:application";
            User = cfg.user;
            Group = cfg.user;
            EnvironmentFile="${chatddx-prod-env}";
          };
          wantedBy = [ "multi-user.target" ];
        };
      };
    };
  };
}
