# src/chatddx/django/settings_main.py
import os
from pathlib import Path

DEBUG = False

ALLOWED_HOSTS = [os.environ["HOST"], "localhost"]

SCHEME = os.environ["SCHEME"]

STATE_DIR = Path(os.environ["STATE_DIR"])

CSRF_TRUSTED_ORIGINS = [f"{SCHEME}://{os.environ['HOST']}"]
CORS_ALLOWED_ORIGINS = [f"{SCHEME}://{os.environ['HOST']}"]

with open(os.environ["SECRET_KEY_FILE"]) as f:
    SECRET_KEY = f.read()

SALT_KEY = SECRET_KEY

CORS_ALLOW_CREDENTIALS = True

SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
