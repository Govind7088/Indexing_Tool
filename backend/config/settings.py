"""
Django settings for config project.

Secrets (SECRET_KEY, DB password) kabhi code mein nahi likhte.
Sab kuch backend/.env se aata hai (.env Git mein nahi jaati).
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# .env file ke variables load karo
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    """'1' ya 'true' (kisi bhi case mein) ho tabhi True, warna False."""
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true')


# --- Security settings (sab .env se) ---------------------------------

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '')
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('change-me'):
    raise ImproperlyConfigured(
        'DJANGO_SECRET_KEY .env mein set karo (kam se kam 50 characters, '
        'placeholder nahi).'
    )

# Default False: galti se production mein DEBUG on na ho jaye
DEBUG = env_bool('DJANGO_DEBUG', False)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',')
    if host.strip()
]


# --- Application definition ------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'indexing',
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
        'DIRS': [],
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


# --- Database (MySQL) ------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
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
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Email (development mein console par print hoga) -----------------
# Pehle yahan galti se MAILERS likha tha, Django ka sahi setting EMAIL_BACKEND hai.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# --- Django REST Framework -------------------------------------------

REST_FRAMEWORK = {
    # Sirf JSON response (browsable HTML API band)
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    # Is app mein user login nahi hai, isliye session/basic auth ki zaroorat nahi
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    # Ek IP se 1 minute mein max 20 URL submit
    'DEFAULT_THROTTLE_RATES': {
        'submit': '20/min',
    },
}