# src/chatddx/django/settings/dev.py
import os
from pathlib import Path

DEBUG = True
STATE_DIR = Path(os.environ["STATE_DIR"])
SECRET_KEY = "django-insecure-@dl&bssqzr%xaviwu73kb!bng!(sgx#^u0+q7!$_&=kw+*4$#z"
SALT_KEY = SECRET_KEY
ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = ["http://localhost:8080"]
CORS_ALLOWED_ORIGINS = ["http://localhost:8080"]
CORS_ALLOW_CREDENTIALS = True

SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = False
