"""
Development settings
"""
from .base import *

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# Development-specific apps (commented out until packages installed)
# INSTALLED_APPS += [
#     'debug_toolbar',
#     'django_extensions',
# ]
#
# MIDDLEWARE += [
#     'debug_toolbar.middleware.DebugToolbarMiddleware',
# ]

# Debug toolbar configuration
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Email backend for development (prints to console)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Simplified password hashing for development (faster)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Allow all CORS origins in development
CORS_ALLOW_ALL_ORIGINS = True

# Disable require HTTPS in development
SECURE_SSL_REDIRECT = False

# DRF - Allow unauthenticated access in development for testing
REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
    'rest_framework.permissions.AllowAny',
]

# Celery - Use synchronous execution in development for easier debugging
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_ALWAYS_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = True
