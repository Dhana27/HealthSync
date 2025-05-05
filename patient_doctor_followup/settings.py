# patient_doctor_followup/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv
import sys

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
# OpenAI API Key (if used in your project)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Debug Mode
DEBUG = os.getenv("DEBUG", "False") == "True"
#DEBUG = "TRUE"
ALLOWED_HOSTS = []

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/doctor-dashboard/'  # Default redirect for doctors
LOGOUT_REDIRECT_URL = '/'  # Redirect to home page after logout
STATIC_URL = '/static/'

# Celery settings
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")  # Redis broker
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Twilio Credentials (Store these in environment variables)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

FITBIT_CLIENT_ID = '***'
FITBIT_CLIENT_SECRET = '***'
FITBIT_REDIRECT_URI = 'http://localhost:8000/fitbit/callback/'  
FITBIT_SCOPE = ['heartrate', 'profile']

#DAILY_API_KEY = '***'

HMS_TEMPLATE_ID = "***"
HMS_MANAGEMENT_TOKEN = "***"
HMS_ACCESS_KEY = "***"
HMS_SECRET = "***="

HMS_ROOM_CODES = {
    "doctor": "mfm-merv-nny",
    "patient": "ywp-bmrv-jlw"
}
HMS_SUBDOMAIN = "healthsync-videoconf-1025"

INSTALLED_APPS = [
    'django.contrib.admin',  # Use default admin app
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'notifications',
    'recovery',
]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'patient_doctor_followup.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'core' / 'templates'],  # We point to our templates folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.views.global_data',  # NEW: Passing global data
                'core.views.base_context_processor', 
            ],
        },
    },
]

WSGI_APPLICATION = 'patient_doctor_followup.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

STATICFILES_DIRS = [
    BASE_DIR / 'core' / 'static',  # Match the templates structure
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Singapore'  # Change this to your correct timezone
USE_TZ = True  # If you want timezone support
USE_I18N = True
USE_L10N = True

STATIC_URL = '/static/'
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
}

# Custom authentication backend
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

"""LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
}

"""
