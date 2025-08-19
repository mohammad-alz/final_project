from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- IMPORTANT: SECRET KEYS AND API CONFIG ---
# In a real production environment, load these from environment variables!
SECRET_KEY = 'django-insecure-your-secret-key-goes-here' # Replace with a real secret key
FINANCIAL_API_KEY = 'YOUR_FINANCIAL_DATA_API_KEY'
FINANCIAL_API_URL = 'https://api.example.com/v1/price' # The URL from your price provider
PAYMENT_WEBHOOK_SECRET = 'YOUR_PAYMENT_GATEWAY_WEBHOOK_SECRET_KEY'


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['45.138.135.212', '127.0.0.1', 'localhost']


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 3rd Party Apps
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    # Local Apps
    'api',
    'corsheaders'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
]

ROOT_URLCONF = 'digital_gold.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'digital_gold.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'digital_gold',
        'USER': 'admin',
        'PASSWORD': 'p&^Edr(P9jhVpiji7t%%hg',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Custom User Model
AUTH_USER_MODEL = 'api.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'


MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        # Use JWT for authentication instead of the old TokenAuthentication
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}


# Email Configuration
# For development, log emails to the console.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'

BRS_API_KEY = "FreerPdX0sePXY2fABdMB9d2neHsjjsY"

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

CORS_ALLOW_ALL_ORIGINS = True