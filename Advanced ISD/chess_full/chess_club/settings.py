"""
Django settings for chess_club project.
"""

import os
from pathlib import Path

from decouple import Csv, config
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

_SECRET_DEFAULT = 'django-insecure-dev-only-change-me'
SECRET_KEY = config('SECRET_KEY', default=_SECRET_DEFAULT)
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='127.0.0.1,localhost', cast=Csv())

if not DEBUG:
    if not SECRET_KEY or SECRET_KEY == _SECRET_DEFAULT or SECRET_KEY.startswith('django-insecure'):
        raise ImproperlyConfigured(
            'Set a strong SECRET_KEY in the environment when DEBUG is False.'
        )
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    # TLS / reverse-proxy (set USE_X_FORWARDED_PROTO when behind nginx, Traefik, or a load balancer)
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
    if SECURE_HSTS_SECONDS > 0:
        SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
        SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)
    USE_X_FORWARDED_HOST = config('USE_X_FORWARDED_HOST', default=False, cast=bool)
    if config('USE_X_FORWARDED_PROTO', default=False, cast=bool):
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

_csrf_origins = config('CSRF_TRUSTED_ORIGINS', default='')
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.microsoft',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'crispy_forms',
    'crispy_bootstrap5',
    'rest_framework',
    'drf_spectacular',
    'club',
    'ai_pipeline',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# --- django-allauth (OAuth sign-in; Lichess linking stays on the dashboard) ---
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https' if not DEBUG else 'http'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_ON_GET = False
ACCOUNT_UNIQUE_EMAIL = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_ADAPTER = 'club.adapters.ClubSocialAccountAdapter'

_SOCIAL_PROVIDERS: dict = {}

_google_id = config('GOOGLE_OAUTH_CLIENT_ID', default='').strip()
_google_secret = config('GOOGLE_OAUTH_CLIENT_SECRET', default='').strip()
if _google_id and _google_secret:
    _SOCIAL_PROVIDERS['google'] = {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'APP': {'client_id': _google_id, 'secret': _google_secret, 'key': ''},
    }

_github_id = config('GITHUB_OAUTH_CLIENT_ID', default='').strip()
_github_secret = config('GITHUB_OAUTH_CLIENT_SECRET', default='').strip()
if _github_id and _github_secret:
    _SOCIAL_PROVIDERS['github'] = {
        'SCOPE': ['user:email'],
        'APP': {'client_id': _github_id, 'secret': _github_secret, 'key': ''},
    }

_ms_id = config('MICROSOFT_OAUTH_CLIENT_ID', default='').strip()
_ms_secret = config('MICROSOFT_OAUTH_CLIENT_SECRET', default='').strip()
if _ms_id and _ms_secret:
    _ms_tenant = config('MICROSOFT_OAUTH_TENANT', default='common').strip() or 'common'
    _SOCIAL_PROVIDERS['microsoft'] = {
        'TENANT': _ms_tenant,
        'APP': {'client_id': _ms_id, 'secret': _ms_secret, 'key': ''},
    }

SOCIALACCOUNT_PROVIDERS = _SOCIAL_PROVIDERS

# Public site URL for OAuth callback hints in templates (no trailing slash). Use behind reverse proxies when
# request.is_secure() is wrong, e.g. PUBLIC_BASE_URL=https://chesmate1.duckdns.org
PUBLIC_BASE_URL = config('PUBLIC_BASE_URL', default='').strip().rstrip('/')

ROOT_URLCONF = 'chess_club.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'club.context_processors.user_theme',
                'club.context_processors.admin_log_nav',
                'club.context_processors.oauth_public_base',
            ],
        },
    },
]

WSGI_APPLICATION = 'chess_club.wsgi.application'

USE_POSTGRES = config('USE_POSTGRES', default=False, cast=bool)
if USE_POSTGRES:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('POSTGRES_DB', default='chess_club'),
            'USER': config('POSTGRES_USER', default='postgres'),
            'PASSWORD': config('POSTGRES_PASSWORD', default=''),
            'HOST': config('POSTGRES_HOST', default='localhost'),
            'PORT': config('POSTGRES_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend',
)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='webmaster@localhost')

LICHESS_API_BASE_URL = os.getenv('LICHESS_API_BASE_URL', 'https://lichess.org/api')
LICHESS_API_TOKEN = os.getenv('LICHESS_API_TOKEN', '')
if os.name == 'nt':
    _default_stockfish_path = str(
        BASE_DIR.parent / 'ai_pipeline' / 'bin' / 'stockfish_extracted' / 'stockfish' / 'stockfish-windows-x86-64-avx2.exe'
    )
elif os.path.exists('/usr/games/stockfish'):
    _default_stockfish_path = '/usr/games/stockfish'
else:
    _default_stockfish_path = '/opt/homebrew/bin/stockfish'

STOCKFISH_PATH = os.getenv('STOCKFISH_PATH', _default_stockfish_path)
STOCKFISH_DEPTH = int(os.getenv('STOCKFISH_DEPTH', '12'))
STOCKFISH_THREADS = int(os.getenv('STOCKFISH_THREADS', '1'))
STOCKFISH_HASH_MB = int(os.getenv('STOCKFISH_HASH_MB', '128'))

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'club:login'
LOGIN_REDIRECT_URL = 'club:dashboard'
LOGOUT_REDIRECT_URL = 'club:home'

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Eschen Chess Club API',
    'DESCRIPTION': 'Interactive API surface for pipeline functions and diagnostics.',
    'VERSION': '1.0.0',
}

# --- Application logging (errors & diagnostics; see logs/application.log) ---
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(parents=True, exist_ok=True)
APP_LOG_LEVEL = config('APP_LOG_LEVEL', default='INFO')
APP_LOG_MAX_BYTES = config('APP_LOG_MAX_BYTES', default=10 * 1024 * 1024, cast=int)
APP_LOG_BACKUP_COUNT = config('APP_LOG_BACKUP_COUNT', default=5, cast=int)
APP_LOG_FILE = config('APP_LOG_FILE', default=str(LOGS_DIR / 'application.log'))
APP_LOG_ADMIN_SUPERUSER_ONLY = config('APP_LOG_ADMIN_SUPERUSER_ONLY', default=True, cast=bool)
APP_LOG_ADMIN_MAX_LINES = config('APP_LOG_ADMIN_MAX_LINES', default=5000, cast=int)
APP_LOG_ADMIN_TAIL_BYTES = config('APP_LOG_ADMIN_TAIL_BYTES', default=512 * 1024, cast=int)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': APP_LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': APP_LOG_FILE,
            'maxBytes': APP_LOG_MAX_BYTES,
            'backupCount': APP_LOG_BACKUP_COUNT,
            'formatter': 'verbose',
        },
        'console': {
            'level': APP_LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': APP_LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': APP_LOG_LEVEL,
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'club': {
            'handlers': ['console', 'file'],
            'level': APP_LOG_LEVEL,
            'propagate': False,
        },
        'ai_pipeline': {
            'handlers': ['console', 'file'],
            'level': APP_LOG_LEVEL,
            'propagate': False,
        },
    },
}
