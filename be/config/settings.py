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
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "common.middleware.RequestContextMiddleware",
]
ROOT_URLCONF = "config.urls"
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
SMS_DELIVERY_MODE = os.getenv("SMS_DELIVERY_MODE", "development")
DEV_INBOX = Path(
    os.getenv(
        "DEV_INBOX",
        str(Path(os.getenv("LOCALAPPDATA", str(BASE_DIR))) / "TechRetailRuntime" / "dev-inbox"),
    )
)
ORDER_PENDING_TTL_MINUTES = int(os.getenv("ORDER_PENDING_TTL_MINUTES", "30"))
OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
OTP_RESEND_COOLDOWN_SECONDS = int(os.getenv("OTP_RESEND_COOLDOWN_SECONDS", "60"))
GOOGLE_LOGIN_ENABLED = flag("GOOGLE_LOGIN_ENABLED")
FACEBOOK_LOGIN_ENABLED = flag("FACEBOOK_LOGIN_ENABLED")
GEMINI_ENABLED = flag("GEMINI_ENABLED")
if any([GOOGLE_LOGIN_ENABLED, FACEBOOK_LOGIN_ENABLED, GEMINI_ENABLED]):
    raise ImproperlyConfigured(
        "Provider integration is DEFERRED. Keep provider flags false until implemented and verified."
    )
if APP_ENV == "production" and (
    DEBUG
    or EMAIL_DELIVERY_MODE != "smtp"
    or SMS_DELIVERY_MODE == "development"
    or not EMAIL_HOST
    or not DEFAULT_FROM_EMAIL
):
    raise ImproperlyConfigured(
        "Production requires debug=false, SMTP and a configured SMS delivery adapter."
    )
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
        "lookup": "10/min",
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
