"""
Django 5.0.1
"""

from os import environ, getenv
from pathlib import Path

from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = Path(getenv("STATE_DIR", BASE_DIR))

DEBUG = getenv("DEBUG", "True").lower() in ["true", "1", "yes"]
SCHEME = getenv("SCHEME", "http")

if DEBUG:
    ALLOWED_HOSTS = ["*"]
    CSRF_TRUSTED_ORIGINS = [f"http://localhost:5173"]
    SECRET_KEY = "django-insecure-@dl&bssqzr%xaviwu73kb!bng!(sgx#^u0+q7!$_&=kw+*4$#z"
else:
    ALLOWED_HOSTS = [environ["HOST"], "localhost"]
    CSRF_TRUSTED_ORIGINS = [f"{SCHEME}://{environ['HOST']}"]
    with open(environ["SECRET_KEY_FILE"]) as f:
        SECRET_KEY = f.read()

INSTALLED_APPS = [
    "chatddx_backend.api.apps.ApiConfig",
    "chatddx_backend.cms.apps.CmsConfig",
    "modeltranslation",
    "login_history",
    "django_celery_results",
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "chatddx_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "chatddx_backend.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": getenv("DB_NAME"),
        "USER": getenv("DB_USER"),
        "HOST": getenv("DB_HOST"),
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "unix:///run/redis-alex/redis.sock?db=0",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": getenv("LOG_LEVEL"),
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
LANGUAGES = [
    ("en", _("English")),
    ("sv", _("Swedish")),
]

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = getenv("STATIC_ROOT")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CELERY_BROKER_URL = getenv("CELERY_BROKER_URL")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = False
CELERY_RESULT_BACKEND = "django-db"

UNFOLD = {
    "THEME": "dark",
}
