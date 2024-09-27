#!/usr/bin/env bash
set -a
source @env@
set +a

if [ "$1" = "runserver" ]; then
  @depEnv@/bin/gunicorn app.wsgi:application "${@:2}"
elif [ "$1" = "static" ]; then
  echo @static@
else
  cd @depEnv@ && ./bin/django-admin "${@}"
fi
