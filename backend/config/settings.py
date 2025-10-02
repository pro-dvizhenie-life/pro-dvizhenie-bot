"""Базовые настройки Django для бэкенда проекта «Движение»."""

import os
import sys
from datetime import timedelta
from pathlib import Path

from django.core.management.utils import get_random_secret_key

from .constants import (
    DOCUMENTS_DEFAULT_ALLOWED_CONTENT_TYPES,
    DOCUMENTS_DEFAULT_ALLOWED_EXTENSIONS,
    DOCUMENTS_DEFAULT_MAX_COUNT_PER_APPLICATION,
    DOCUMENTS_DEFAULT_MAX_FILE_SIZE,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent
APPS_DIR = BASE_DIR / 'apps'
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))


# def load_env(env_path: Path) -> None:
#     """Заполняет os.environ парами ключ/значение из файла .env."""
#     if not env_path.exists():
#         return
#
#     for line in env_path.read_text(encoding='utf-8').splitlines():
#         line = line.strip()
#         if not line or line.startswith('#') or '=' not in line:
#             continue
#         key, value = line.split('=', 1)
#         key = key.strip()
#         value = value.strip().strip('"').strip("'")
#         os.environ.setdefault(key, value)
#
#
# load_env(PROJECT_ROOT / '.env')

def load_env(env_path: Path) -> None:
    """Заполняет os.environ парами ключ/значение из файла .env."""
    # Пробуем несколько возможных расположений .env
    possible_paths = [
        env_path,  # оригинальный путь (backend/.env)
        PROJECT_ROOT / '.env',  # корень проекта (pro-dvizhenie-bot/.env)
        BASE_DIR / '.env',  # папка backend
    ]

    found_path = None
    for path in possible_paths:
        if path.exists():
            found_path = path
            print(f"📁 Загружаем .env из: {found_path}")
            break

    if not found_path:
        print("⚠️  .env файл не найден")
        return

    for line in found_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


# Загружаем .env из корня проекта
load_env(PROJECT_ROOT.parent / '.env')  # Теперь ищем в /pro-dvizhenie-bot/.env

def str_to_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {'1', 'true', 'yes', 'on'}


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = (
    os.environ.get('DJANGO_SECRET_KEY')
    or os.environ.get('SECRET_KEY')
    or get_random_secret_key()
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = str_to_bool(os.environ.get('DJANGO_DEBUG'), default=True)

ALLOWED_HOSTS: list[str] = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'rest_framework_simplejwt',
    'users.apps.UsersConfig',
    'applications.apps.ApplicationsConfig',
    'documents.apps.DocumentsConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

AUTH_USER_MODEL = 'users.User'

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Pro Dvizhenie API',
    'DESCRIPTION': (
        'OpenAPI схема и интерактивная документация для backend части '
        'проекта «Движение».'
    ),
    'VERSION': '1.0.0',
    'SERVE_PERMISSIONS': ['rest_framework.permissions.AllowAny'],
    'SERVE_INCLUDE_SCHEMA': False,
}


def _int_from_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


DOCUMENTS_STORAGE = {
    'BACKEND': os.environ.get('DOCUMENTS_STORAGE_BACKEND', 'documents.storages.S3DocumentStorage'),
    'OPTIONS': {
        'bucket': os.environ.get('DOCUMENTS_STORAGE_BUCKET', ''),
        'endpoint_url': os.environ.get('DOCUMENTS_STORAGE_ENDPOINT'),
        'region_name': os.environ.get('DOCUMENTS_STORAGE_REGION'),
        'access_key': os.environ.get('DOCUMENTS_STORAGE_ACCESS_KEY'),
        'secret_key': os.environ.get('DOCUMENTS_STORAGE_SECRET_KEY'),
        'session_token': os.environ.get('DOCUMENTS_STORAGE_SESSION_TOKEN'),
        'upload_expiration': _int_from_env('DOCUMENTS_UPLOAD_EXPIRATION', 900),
        'download_expiration': _int_from_env('DOCUMENTS_DOWNLOAD_EXPIRATION', 900),
        'signature_version': os.environ.get('DOCUMENTS_STORAGE_SIGNATURE_VERSION'),
        'addressing_style': os.environ.get('DOCUMENTS_STORAGE_ADDRESSING_STYLE'),
    },
}

DOCUMENTS_MAX_FILE_SIZE = _int_from_env(
    'DOCUMENTS_MAX_FILE_SIZE', DOCUMENTS_DEFAULT_MAX_FILE_SIZE
)

_document_types_env = os.environ.get('DOCUMENTS_ALLOWED_CONTENT_TYPES')
if _document_types_env:
    DOCUMENTS_ALLOWED_CONTENT_TYPES = [
        item.strip() for item in _document_types_env.split(',') if item.strip()
    ]
else:
    DOCUMENTS_ALLOWED_CONTENT_TYPES = list(DOCUMENTS_DEFAULT_ALLOWED_CONTENT_TYPES)

_document_extensions_env = os.environ.get('DOCUMENTS_ALLOWED_FILE_EXTENSIONS')
if _document_extensions_env:
    DOCUMENTS_ALLOWED_FILE_EXTENSIONS = [
        item.strip().lower()
        for item in _document_extensions_env.split(',')
        if item.strip()
    ]
else:
    DOCUMENTS_ALLOWED_FILE_EXTENSIONS = list(DOCUMENTS_DEFAULT_ALLOWED_EXTENSIONS)

DOCUMENTS_MAX_DOCUMENTS_PER_APPLICATION = _int_from_env(
    'DOCUMENTS_MAX_DOCUMENTS_PER_APPLICATION',
    DOCUMENTS_DEFAULT_MAX_COUNT_PER_APPLICATION,
)


PROJECT_NAME = os.environ.get('PROJECT_NAME', 'Про Движение')
DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    'no-reply@pro-dvizhenie.local',
)
MAGIC_LINK_TOKEN_TTL_MINUTES = _int_from_env('MAGIC_LINK_TOKEN_TTL_MINUTES', 60 * 24)
MAGIC_LINK_EMAIL_SUBJECT = os.environ.get(
    'MAGIC_LINK_EMAIL_SUBJECT',
    'Продолжите заполнение заявки',
)
FRONTEND_APPLICATION_RESUME_URL = os.environ.get(
    'FRONTEND_APPLICATION_RESUME_URL',
    'http://localhost:3000/application/resume',
)
