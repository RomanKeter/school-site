"""Настройки проекта «Учебный сайт» (MVP, этап 1).

Все секреты и параметры окружения — через переменные окружения (.env на сервере).
Если POSTGRES_DB не задана — используется SQLite (удобно для локальной разработки).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.content",
    "apps.srs",
    "apps.learning",
    "apps.missions",
    "apps.rewards",
    "apps.parents",
    "apps.ai",
    "apps.homework",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.ContentSecurityPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.accounts.context.child_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if os.environ.get("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ.get("POSTGRES_USER", "school"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
]
LOGIN_URL = "/parent/login/"

LANGUAGE_CODE = "ru"
TIME_ZONE = "Europe/Minsk"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_AGE = 14 * 24 * 3600  # родитель: 14 дней; ребёнку ставим 8 часов в момент входа
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 3600

# Параметры интервального повторения (раздел 6, SR-7). Дублируются в модели SrsConfig.
SRS = {
    "initial_ef": 2.5,
    "min_ef": 1.3,
    "max_ef": 2.8,
    "i_max": 60,
    "steps": [1, 3, 7],
    "fuzz_pct": 0.10,
    "daily_limit_default": 15,
}

# Защита от подбора картинного пароля (FR-AUTH-4)
CHILD_LOGIN_MAX_FAILS = 5
CHILD_LOGIN_LOCK_SECONDS = 5 * 60
TRUSTED_DEVICE_DAYS = 180
CHILD_SESSION_SECONDS = 8 * 3600

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# ИИ-помощник Мася и «Научи Масю» (этап 2, раздел 9.5 ТЗ, D-100…D-108). Ключи — только из окружения.
# AI_PROVIDER: gemini | openrouter | fake; пусто — gemini при наличии GEMINI_API_KEY, иначе офлайн-подсказки.
AI = {
    "PROVIDER": os.environ.get("AI_PROVIDER", ""),
    "MODEL": os.environ.get("AI_MODEL", "gemini-3.5-flash-lite"),
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
    "GEMINI_BASE_URL": os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
    "OPENROUTER_API_KEY": os.environ.get("OPENROUTER_API_KEY", ""),
    "OPENROUTER_BASE_URL": os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    "OPENROUTER_MODEL": os.environ.get("OPENROUTER_MODEL", ""),
    "HTTPS_PROXY": os.environ.get("AI_HTTPS_PROXY", ""),
    "REASONING_EFFORT": os.environ.get("AI_REASONING_EFFORT", ""),
    "TIMEOUT": float(os.environ.get("AI_TIMEOUT", "15")),
    "MIN_INTERVAL_SECONDS": int(os.environ.get("AI_MIN_INTERVAL_SECONDS", "10")),
    "MONTHLY_BUDGET_USD": float(os.environ.get("AI_MONTHLY_BUDGET_USD", "3")),
    "PRICE_IN_PER_M": float(os.environ.get("AI_PRICE_IN_PER_M", "0.30")),
    "PRICE_OUT_PER_M": float(os.environ.get("AI_PRICE_OUT_PER_M", "2.50")),
}
