"""
Django settings for JobFit AI - Intelligent Resume-Based Job Matching and
Skill Recommendation Platform (config project).

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# SECURITY
# ---------------------------------------------------------------------------
# SECURITY WARNING: keep the secret key used in production secret!
# For an academic/dev project this hardcoded key is fine. For production,
# move this into an environment variable (e.g. via python-dotenv).
SECRET_KEY = 'django-insecure-CHANGE-THIS-KEY-BEFORE-DEPLOYMENT-8f92kd83jd'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []  # e.g. ['127.0.0.1', 'localhost'] — empty list is fine while DEBUG=True


# ---------------------------------------------------------------------------
# APPLICATION DEFINITION
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'widget_tweaks',   # lets templates add Bootstrap CSS classes to form fields

    # Local apps
    'matching_app',
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
        # Project-level templates directory (in addition to each app's own
        # templates/ folder, which Django finds automatically via APP_DIRS).
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'matching_app.context_processors.unread_messages_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ---------------------------------------------------------------------------
# DATABASE
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
# ---------------------------------------------------------------------------
# SQLite as agreed in the project plan — free, file-based, zero-config.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# ---------------------------------------------------------------------------
# PASSWORD VALIDATION
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# INTERNATIONALIZATION
# https://docs.djangoproject.com/en/5.0/topics/i18n/
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


# ---------------------------------------------------------------------------
# STATIC FILES (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'

# Additional locations Django looks for static files during development,
# on top of each app's own static/ folder (found automatically because
# 'django.contrib.staticfiles' is installed).
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Where `collectstatic` gathers everything for production deployment.
STATIC_ROOT = BASE_DIR / 'staticfiles'


# ---------------------------------------------------------------------------
# MEDIA FILES (user-uploaded resumes, etc.)
# https://docs.djangoproject.com/en/5.0/topics/files/
# ---------------------------------------------------------------------------
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ---------------------------------------------------------------------------
# DEFAULT PRIMARY KEY FIELD TYPE
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ---------------------------------------------------------------------------
# LOGIN / REDIRECT (kept at Django defaults; no extra auth features added)
# ---------------------------------------------------------------------------
LOGIN_REDIRECT_URL = '/'


# ---------------------------------------------------------------------------
# MESSAGE TAGS
# https://docs.djangoproject.com/en/5.0/ref/contrib/messages/
# ---------------------------------------------------------------------------
# Django's built-in messages framework uses the tag "error" by default,
# but Bootstrap's CSS class for red alert boxes is "danger". This mapping
# makes {% if messages %} blocks in our templates render with the correct
# Bootstrap alert color automatically.
from django.contrib.messages import constants as messages_constants

MESSAGE_TAGS = {
    messages_constants.ERROR: 'danger',
}


# ---------------------------------------------------------------------------
# PROJECT-SPECIFIC SETTINGS (used by matching_app/forms.py and services/)
# ---------------------------------------------------------------------------
# Maximum resume upload size, in megabytes. Enforced in forms.py so users
# get a friendly error message instead of a server crash on huge files.
MAX_RESUME_UPLOAD_SIZE_MB = 5

# File extensions accepted for resume uploads. Enforced in forms.py.
ALLOWED_RESUME_EXTENSIONS = ['pdf', 'docx']

# Name of the pretrained spaCy model used for Named Entity Recognition
# (organizations, dates, etc.) when extracting resume/JD information.
SPACY_MODEL_NAME = 'en_core_web_sm'

# Name of the pretrained Sentence-Transformers model used to generate
# semantic embeddings for resume <-> job description matching.
SENTENCE_TRANSFORMER_MODEL_NAME = 'all-MiniLM-L6-v2'
