import os
from pathlib import Path

DEBUG = True
STATE_DIR = Path(os.environ["STATE_DIR"])
SECRET_KEY = "django-insecure-@dl&bssqzr%xaviwu73kb!bng!(sgx#^u0+q7!$_&=kw+*4$#z"
CSRF_TRUSTED_ORIGINS = ["http://localhost:5173"]
SALT_KEY = SECRET_KEY
ALLOWED_HOSTS = ["*"]
