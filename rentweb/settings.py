"""
Django settings for rentweb project.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-insecure-vseaajxf!_0wfe^7qj-3fg9f5^!n&879qt=q-40k4v9v)xzrh6"

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "dashboard.apps.DashboardConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "dashboard.middleware.BotGateMiddleware",
]

# Public pages require a solved CAPTCHA session (set BOT_GATE_ENABLED=0 to disable)
BOT_GATE_ENABLED = os.environ.get("BOT_GATE_ENABLED", "1").lower() not in (
    "0",
    "false",
    "no",
    "off",
)
BOT_GATE_TTL_SECONDS = 60 * 60 * 24
BOT_GATE_MAX_ATTEMPTS = 8
BOT_GATE_LOCKOUT_SECONDS = 300
BOT_GATE_MIN_SOLVE_SECONDS = 1.5

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rentweb-bot-gate",
    }
}

ROOT_URLCONF = "rentweb.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "rentweb.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Rent listings DB (same schema as init_db.py / main.py)
RENT_DB_PATH = BASE_DIR / "real_estate.db"
RENT_SCHEMA_PATH = BASE_DIR / "schema.sql"

# Weekly scrape at local midnight Monday (Asia/Yerevan)
SCRAPE_CRON_DAY_OF_WEEK = "mon"  # mon..sun
SCRAPE_CRON_HOUR = 0
SCRAPE_CRON_MINUTE = 0
ENABLE_SCRAPE_SCHEDULER = True

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

TIME_ZONE = "Asia/Yerevan"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
