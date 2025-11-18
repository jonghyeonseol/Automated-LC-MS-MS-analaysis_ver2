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

# SECURITY FIX: Only allow specific origins, even in development
# Use CORS_ALLOWED_ORIGINS in .env to add development domains if needed
# CORS_ALLOW_ALL_ORIGINS = True  # DANGEROUS - disabled for security
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8000',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:8000',
]

# Disable require HTTPS in development
SECURE_SSL_REDIRECT = False

# DRF - SECURITY FIX: Keep authentication required even in development
# To disable auth for specific views, use permission_classes = [AllowAny] on the view
# REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = [
#     'rest_framework.permissions.AllowAny',  # DANGEROUS - disabled
# ]
# Default is IsAuthenticated (inherited from base.py)

# Celery - Use synchronous execution in development for easier debugging
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_ALWAYS_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = True
