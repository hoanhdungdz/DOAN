import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def flag(name, default=False):
    return os.getenv(name, str(default)).lower() == "true"


def csv(name, default):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = flag("DJANGO_DEBUG", True)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY.startswith("CHANGE_ME"):
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY in be/.env (do not commit secrets).")
ALLOWED_HOSTS = csv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
MODULES = [
    "accounts",
    "products",
    "stores",
    "inventory",
    "customers",
    "orders",
    "payments",
    "suppliers",
    "reports",
    "ai_consultation",
]
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "common",
    *["apps." + x for x in MODULES],
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "common.portal_sessions.PortalCookieMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "common.middleware.RequestContextMiddleware",
]
ROOT_URLCONF = "config.urls"
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
    }
]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("DB_NAME", "tech_retail"),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
            "isolation_level": "read committed",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {"CHARSET": "utf8mb4"},
    }
}
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation." + x}
    for x in [
        "UserAttributeSimilarityValidator",
        "MinimumLengthValidator",
        "CommonPasswordValidator",
        "NumericPasswordValidator",
    ]
]
PASSWORD_RESET_TIMEOUT = 3600
LANGUAGE_CODE = "vi"
TIME_ZONE = os.getenv("BUSINESS_TIME_ZONE", "Asia/Ho_Chi_Minh")
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "sessionid")
CSRF_COOKIE_NAME = os.getenv("CSRF_COOKIE_NAME", "csrftoken")
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = APP_ENV == "production"
CSRF_COOKIE_SECURE = APP_ENV == "production"
SECURE_SSL_REDIRECT = APP_ENV == "production"
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = csv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:5174")
CSRF_TRUSTED_ORIGINS = csv("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://localhost:5174")
CUSTOMER_FRONTEND_URL = os.getenv("CUSTOMER_FRONTEND_URL", "http://localhost:5173")
ADMIN_FRONTEND_URL = os.getenv("ADMIN_FRONTEND_URL", "http://localhost:5174")
EMAIL_DELIVERY_MODE = os.getenv("EMAIL_DELIVERY_MODE", "console")
EMAIL_BACKEND = (
    "django.core.mail.backends.console.EmailBackend"
    if EMAIL_DELIVERY_MODE == "console"
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = flag("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "development@localhost")
EMAIL_TIMEOUT = 10
ORDER_PENDING_TTL_MINUTES = int(os.getenv("ORDER_PENDING_TTL_MINUTES", "30"))
GOOGLE_LOGIN_ENABLED = flag("GOOGLE_LOGIN_ENABLED")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "")
GOOGLE_REDIRECT_URIS = csv("GOOGLE_REDIRECT_URIS", GOOGLE_REDIRECT_URI) or (
    [GOOGLE_REDIRECT_URI] if GOOGLE_REDIRECT_URI else []
)
if GOOGLE_LOGIN_ENABLED and not (
    GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URIS
):
    raise ImproperlyConfigured("Google login requires a client ID, secret and registered callback.")
FACEBOOK_LOGIN_ENABLED = flag("FACEBOOK_LOGIN_ENABLED")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI", "")
FACEBOOK_GRAPH_VERSION = os.getenv("FACEBOOK_GRAPH_VERSION", "v25.0")
if FACEBOOK_LOGIN_ENABLED and not (
    FACEBOOK_APP_ID and FACEBOOK_APP_SECRET and FACEBOOK_REDIRECT_URI
):
    raise ImproperlyConfigured("Facebook login requires an app ID, secret and registered callback.")
GEMINI_ENABLED = flag("GEMINI_ENABLED")
VNPAY_SANDBOX_ENABLED = flag("VNPAY_SANDBOX_ENABLED")
VNPAY_TMN_CODE = os.getenv("VNPAY_TMN_CODE", "").strip()
VNPAY_HASH_SECRET = os.getenv("VNPAY_HASH_SECRET", "")
VNPAY_RETURN_URL = os.getenv("VNPAY_RETURN_URL", "")
if VNPAY_SANDBOX_ENABLED and (
    APP_ENV == "production" or not (VNPAY_TMN_CODE and VNPAY_HASH_SECRET and VNPAY_RETURN_URL)
):
    raise ImproperlyConfigured(
        "VNPay sandbox requires merchant credentials/return URL and a non-production environment."
    )
if GEMINI_ENABLED:
    raise ImproperlyConfigured("Gemini integration is DEFERRED. Keep this flag false.")
if APP_ENV == "production" and (
    DEBUG or EMAIL_DELIVERY_MODE != "smtp" or not EMAIL_HOST or not DEFAULT_FROM_EMAIL
):
    raise ImproperlyConfigured("Production requires debug=false and configured SMTP.")
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["common.authentication.CsrfSessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "common.errors.exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "300/min",
        "auth": "10/min",
        "payment": "10/min",
        "feedback": "10/min",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "COERCE_DECIMAL_TO_STRING": True,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Tech Retail API",
    "VERSION": "1.0.0",
    "COMPONENT_SPLIT_REQUEST": True,
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "common.schema.errors_hook",
    ],
}
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"oauth_query": {"()": "common.logging.RedactOAuthQuery"}},
    "formatters": {
        "dev_server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        }
    },
    "handlers": {
        "dev_server": {
            "class": "logging.StreamHandler",
            "formatter": "dev_server",
            "filters": ["oauth_query"],
        }
    },
    "loggers": {"django.server": {"handlers": ["dev_server"], "level": "INFO", "propagate": False}},
}
