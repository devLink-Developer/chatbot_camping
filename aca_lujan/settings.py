import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

allowed_hosts = os.getenv("ALLOWED_HOSTS", "*")
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts.split(",") if h.strip()] or ["*"]

csrf_trusted = os.getenv("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_trusted.split(",") if o.strip()]

secure_proxy_ssl = os.getenv("SECURE_PROXY_SSL_HEADER", "")
if secure_proxy_ssl:
    parts = [p.strip() for p in secure_proxy_ssl.split(",") if p.strip()]
    if len(parts) == 2:
        SECURE_PROXY_SSL_HEADER = (parts[0], parts[1])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_apscheduler",
    "rest_framework",
    "corsheaders",
    "app",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aca_lujan.urls"

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

WSGI_APPLICATION = "aca_lujan.wsgi.application"
ASGI_APPLICATION = "aca_lujan.asgi.application"


def parse_database_url(db_url: str) -> dict:
    parsed = urlparse(db_url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://chatbot:password@postgres:5432/aca_lujan_bot"
)
DATABASES = {"default": parse_database_url(DATABASE_URL)}

LANGUAGE_CODE = "es-ar"
TIME_ZONE = os.getenv("TIME_ZONE", "America/Argentina/Buenos_Aires")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
CORS_ALLOW_ALL_ORIGINS = True

# API / WhatsApp settings
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_API_BASE = os.getenv("WHATSAPP_API_BASE", "https://graph.facebook.com")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v18.0")

SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "900"))
INACTIVE_TIMEOUT_SECONDS = int(os.getenv("INACTIVE_TIMEOUT_SECONDS", "1800"))

API_TITLE = os.getenv("API_TITLE", "Aca Lujan Chatbot")
API_VERSION = os.getenv("API_VERSION", "1.0.0")

APPEND_SLASH = False

# Jobs / Scheduler (LiteCore-style)
ASYNC_BACKEND = os.getenv("ASYNC_BACKEND", "thread")
ASYNC_JOB_SYNC_TIMEOUT_SECONDS = int(os.getenv("ASYNC_JOB_SYNC_TIMEOUT_SECONDS", "0"))
GENERIC_JOB_STALE_MINUTES = int(os.getenv("GENERIC_JOB_STALE_MINUTES", "15"))
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "True").lower() == "true"

# Queue worker / human-like timing
QUEUE_WORKER_ENABLED = os.getenv("QUEUE_WORKER_ENABLED", "True").lower() == "true"
QUEUE_POLL_INTERVAL_SECONDS = float(os.getenv("QUEUE_POLL_INTERVAL_SECONDS", "1"))
QUEUE_BATCH_SIZE = int(os.getenv("QUEUE_BATCH_SIZE", "10"))
QUEUE_PROCESS_INLINE = os.getenv("QUEUE_PROCESS_INLINE", "False").lower() == "true"

RESPONSE_MIN_DELAY_MS = int(os.getenv("RESPONSE_MIN_DELAY_MS", "800"))
RESPONSE_MAX_DELAY_MS = int(os.getenv("RESPONSE_MAX_DELAY_MS", "2000"))
RESPONSE_CHARS_PER_SEC = float(os.getenv("RESPONSE_CHARS_PER_SEC", "18"))
RESPONSE_JITTER_MS = int(os.getenv("RESPONSE_JITTER_MS", "250"))

WHATSAPP_ENABLE_TYPING_INDICATOR = os.getenv("WHATSAPP_ENABLE_TYPING_INDICATOR", "False")
WHATSAPP_TYPING_INDICATOR_TYPE = os.getenv("WHATSAPP_TYPING_INDICATOR_TYPE", "text")
WHATSAPP_INTERACTIVE_ENABLED = os.getenv("WHATSAPP_INTERACTIVE_ENABLED", "False").lower() == "true"

# Drop stale outbound messages to avoid late replies
OUTBOUND_MAX_AGE_SECONDS = int(os.getenv("OUTBOUND_MAX_AGE_SECONDS", "900"))
OUTBOUND_DROP_IF_NEWER_INBOUND = os.getenv("OUTBOUND_DROP_IF_NEWER_INBOUND", "True").lower() == "true"
