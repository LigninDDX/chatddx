# src/chatddx/django/settings_main.py
import os
from pathlib import Path

DEBUG = False

ALLOWED_HOSTS = [os.environ["HOST"], "localhost"]

SCHEME = os.environ["SCHEME"]

STATE_DIR = Path(os.environ["STATE_DIR"])

CSRF_TRUSTED_ORIGINS = [f"{SCHEME}://{os.environ['HOST']}"]

with open(os.environ["SECRET_KEY_FILE"]) as f:
    SECRET_KEY = f.read()

SALT_KEY = SECRET_KEY
