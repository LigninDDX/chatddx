#!/usr/bin/env bash
set -a
source @env@
set +a

if [ "$1" = "runserver" ]; then
  @app@/bin/gunicorn app.wsgi:application "${@:2}"
elif [ "$1" = "static" ]; then
  echo @static@
else
  cd @app@ && ./bin/django-admin "${@}"
fi
