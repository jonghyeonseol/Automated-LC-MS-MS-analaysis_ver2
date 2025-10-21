"""
Celery configuration for background task processing
"""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('ganglioside_analysis')

# Load configuration from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
# This will look for tasks.py in each app listed in INSTALLED_APPS
app.autodiscover_tasks()

# Also manually import tasks to ensure they're registered
try:
    from apps.analysis import tasks  # noqa: F401
except ImportError:
    pass


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery setup"""
    print(f'Request: {self.request!r}')
