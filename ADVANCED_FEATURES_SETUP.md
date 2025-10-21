# Advanced Features Setup Guide

**Date**: 2025-10-21
**Version**: Django 2.0.0
**Features**: Django Channels (WebSocket) + Celery (Background Tasks)

---

## Table of Contents

1. [Overview](#overview)
2. [Redis Installation](#redis-installation)
3. [Django Channels Setup (Real-time Progress)](#django-channels-setup)
4. [Celery Setup (Background Tasks)](#celery-setup)
5. [Integration Testing](#integration-testing)
6. [Production Configuration](#production-configuration)
7. [Monitoring & Debugging](#monitoring--debugging)

---

## Overview

### What These Features Add

**Django Channels** (WebSocket):
- Real-time progress updates during analysis
- Live log streaming
- Instant notification when analysis completes
- No page refresh needed

**Celery** (Background Tasks):
- Asynchronous analysis execution
- Multiple concurrent analyses
- Scheduled cleanup jobs
- Email notifications
- Task monitoring

### Prerequisites

- Redis server (required for both features)
- Working Django application
- Production or staging environment

### Architecture After Implementation

```
User Browser
    ↓ WebSocket
Django Channels (ASGI)
    ↓ Channel Layer (Redis)
Django Views/Celery Tasks
    ↓ Task Queue (Redis)
Celery Workers
    ↓
Database (PostgreSQL)
```

---

## Redis Installation

### Development (Local)

**macOS**:
```bash
# Install via Homebrew
brew install redis

# Start Redis
brew services start redis

# Or run manually
redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

**Linux (Ubuntu)**:
```bash
# Install Redis
sudo apt update
sudo apt install -y redis-server

# Start service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test connection
redis-cli ping
```

### Production

**Configure Redis for Production** (`/etc/redis/redis.conf`):

```conf
# Bind to localhost only (security)
bind 127.0.0.1

# Set password
requirepass your_redis_password_here

# Enable persistence
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Max memory
maxmemory 256mb
maxmemory-policy allkeys-lru
```

**Restart Redis**:
```bash
sudo systemctl restart redis-server
```

---

## Django Channels Setup

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install Channels and Redis support
pip install channels[daphne]==4.0.0
pip install channels-redis==4.1.0

# Update requirements
pip freeze > requirements/production.txt
```

### 2. Configure Settings

**File**: `config/settings/base.py`

```python
# Add to INSTALLED_APPS (before django.contrib.staticfiles)
INSTALLED_APPS = [
    'daphne',  # Must be first for ASGI
    'django.contrib.admin',
    # ... rest of apps ...
    'apps.analysis',
    'apps.visualization',
]

# ASGI application
ASGI_APPLICATION = 'config.asgi.application'

# Channel layers configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.getenv('REDIS_URL', 'redis://localhost:6379/0')],
        },
    },
}
```

### 3. Update ASGI Configuration

**File**: `config/asgi.py`

```python
"""
ASGI config for ganglioside project.
Enables WebSocket support via Django Channels.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Initialize Django ASGI application early
django_asgi_app = get_asgi_application()

# Import routing after Django is initialized
from apps.analysis import routing as analysis_routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                analysis_routing.websocket_urlpatterns
            )
        )
    ),
})
```

### 4. Create WebSocket Consumer

**File**: `apps/analysis/consumers.py`

```python
"""
WebSocket consumers for real-time analysis progress
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AnalysisProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for analysis progress updates
    """

    async def connect(self):
        """Accept WebSocket connection"""
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'analysis_{self.session_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Send initial connection message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected to analysis {self.session_id}'
        }))

    async def disconnect(self, close_code):
        """Disconnect from WebSocket"""
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Receive message from WebSocket"""
        # Not used for progress updates (server pushes only)
        pass

    # Message handlers (called from channel layer)

    async def analysis_progress(self, event):
        """Send progress update to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'progress',
            'message': event['message'],
            'percentage': event['percentage'],
            'current_step': event['current_step'],
            'timestamp': event.get('timestamp', ''),
        }))

    async def analysis_complete(self, event):
        """Send completion message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'complete',
            'message': event['message'],
            'redirect_url': event['redirect_url'],
            'success': event.get('success', True),
        }))

    async def analysis_error(self, event):
        """Send error message to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': event['message'],
            'error': event.get('error', ''),
        }))
```

### 5. Create WebSocket Routing

**File**: `apps/analysis/routing.py`

```python
"""
WebSocket URL routing for analysis app
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/analysis/(?P<session_id>\d+)/$',
        consumers.AnalysisProgressConsumer.as_asgi()
    ),
]
```

### 6. Update Analysis Service to Send Progress

**File**: `apps/analysis/services/analysis_service.py`

Add progress notification methods:

```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.utils import timezone


class AnalysisService:
    # ... existing code ...

    def _send_progress(self, session_id: int, message: str, percentage: int, step: str):
        """
        Send real-time progress update via WebSocket

        Args:
            session_id: Analysis session ID
            message: Progress message
            percentage: Completion percentage (0-100)
            step: Current step identifier
        """
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'analysis_{session_id}',
                {
                    'type': 'analysis_progress',
                    'message': message,
                    'percentage': percentage,
                    'current_step': step,
                    'timestamp': timezone.now().isoformat(),
                }
            )

    def _send_complete(self, session_id: int, success: bool, redirect_url: str):
        """Send completion notification"""
        channel_layer = get_channel_layer()
        if channel_layer:
            message = 'Analysis completed successfully!' if success else 'Analysis failed'
            async_to_sync(channel_layer.group_send)(
                f'analysis_{session_id}',
                {
                    'type': 'analysis_complete',
                    'message': message,
                    'redirect_url': redirect_url,
                    'success': success,
                }
            )

    def _send_error(self, session_id: int, error_message: str):
        """Send error notification"""
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'analysis_{session_id}',
                {
                    'type': 'analysis_error',
                    'message': 'Analysis encountered an error',
                    'error': error_message,
                }
            )

    def run_analysis(self, session: AnalysisSession) -> AnalysisResult:
        """
        Main entry point with progress updates
        """
        session_id = session.id

        try:
            # Send progress updates at each step
            self._send_progress(session_id, "Loading data...", 5, "loading")

            df = self._load_csv_from_session(session)

            self._send_progress(session_id, "Preprocessing data...", 10, "preprocessing")

            self.processor.update_settings(
                r2_threshold=session.r2_threshold,
                outlier_threshold=session.outlier_threshold,
                rt_tolerance=session.rt_tolerance
            )

            self._send_progress(session_id, "Running Rule 1: Regression analysis...", 20, "rule1")

            # Run analysis
            results = self.processor.process_data(df, data_type=session.data_type)

            self._send_progress(session_id, "Saving results to database...", 90, "saving")

            # Persist results
            with transaction.atomic():
                analysis_result = self._save_results(session, results, df)

            self._send_progress(session_id, "Analysis complete!", 100, "complete")

            # Send completion notification
            self._send_complete(
                session_id,
                success=True,
                redirect_url=f'/sessions/{session_id}/results/'
            )

            return analysis_result

        except Exception as e:
            self._send_error(session_id, str(e))
            raise
```

### 7. Update Frontend Template

**File**: `templates/analysis/session_detail.html`

Add WebSocket client code:

```html
{% if session.status == 'processing' %}
<div class="mb-4">
    <div class="progress" style="height: 30px;">
        <div id="progressBar" class="progress-bar progress-bar-striped progress-bar-animated"
             role="progressbar" style="width: 0%;">
            <span id="progressText">0%</span>
        </div>
    </div>
    <p class="mt-2 text-center" id="progressMessage">Initializing...</p>
</div>

<script>
// WebSocket connection
const sessionId = {{ session.id }};
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/analysis/${sessionId}/`;
const socket = new WebSocket(wsUrl);

socket.onopen = function(e) {
    console.log('WebSocket connected');
};

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);
    console.log('WebSocket message:', data);

    if (data.type === 'progress') {
        // Update progress bar
        const percentage = data.percentage;
        document.getElementById('progressBar').style.width = percentage + '%';
        document.getElementById('progressText').textContent = percentage + '%';
        document.getElementById('progressMessage').textContent = data.message;

    } else if (data.type === 'complete') {
        // Redirect to results
        setTimeout(() => {
            window.location.href = data.redirect_url;
        }, 1000);

    } else if (data.type === 'error') {
        // Show error
        document.getElementById('progressMessage').innerHTML =
            `<span class="text-danger">Error: ${data.error}</span>`;
    }
};

socket.onclose = function(e) {
    console.log('WebSocket disconnected');
    if (e.code !== 1000) {
        // Abnormal closure - fall back to page refresh
        setTimeout(() => location.reload(), 5000);
    }
};

socket.onerror = function(error) {
    console.error('WebSocket error:', error);
};
</script>
{% endif %}
```

### 8. Test Channels Setup

```bash
# Test Redis connection
python manage.py shell
>>> from channels.layers import get_channel_layer
>>> channel_layer = get_channel_layer()
>>> from asgiref.sync import async_to_sync
>>> async_to_sync(channel_layer.send)('test_channel', {'type': 'test.message'})
# Should complete without errors

# Run with Daphne (ASGI server)
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

## Celery Setup

### 1. Install Dependencies

```bash
pip install celery[redis]==5.3.4
pip install django-celery-beat==2.5.0
pip install django-celery-results==2.5.1
pip install flower==2.0.1  # Monitoring tool
```

### 2. Configure Celery

**File**: `config/celery.py` (uncomment existing code)

```python
"""
Celery configuration for ganglioside project
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('ganglioside')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Periodic tasks schedule
app.conf.beat_schedule = {
    'cleanup-old-sessions': {
        'task': 'apps.analysis.tasks.cleanup_old_sessions',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}


@app.task(bind=True)
def debug_task(self):
    """Debug task for testing"""
    print(f'Request: {self.request!r}')
```

**File**: `config/__init__.py` (uncomment)

```python
from .celery import app as celery_app

__all__ = ('celery_app',)
```

### 3. Update Settings

**File**: `config/settings/base.py`

```python
# Add to INSTALLED_APPS
THIRD_PARTY_APPS = [
    # ... existing apps ...
    'django_celery_beat',      # Periodic tasks
    'django_celery_results',   # Task results
]

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = 'django-db'  # Store results in Django database
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes
```

### 4. Create Celery Tasks

**File**: `apps/analysis/tasks.py`

```python
"""
Celery tasks for background processing
"""
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import AnalysisSession
from .services.analysis_service import AnalysisService


@shared_task(bind=True, name='apps.analysis.tasks.run_analysis_async')
def run_analysis_async(self, session_id: int):
    """
    Run analysis in background

    Args:
        session_id: ID of AnalysisSession to process

    Returns:
        dict: Task result with success status
    """
    try:
        session = AnalysisSession.objects.get(id=session_id)

        # Update status
        session.status = 'processing'
        session.started_at = timezone.now()
        session.celery_task_id = self.request.id  # Store task ID
        session.save()

        # Run analysis
        service = AnalysisService()
        result = service.run_analysis(session)

        # Update status
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()

        return {
            'success': True,
            'session_id': session_id,
            'result_id': result.id,
        }

    except AnalysisSession.DoesNotExist:
        return {'success': False, 'error': 'Session not found'}

    except Exception as e:
        # Update session status
        try:
            session.status = 'failed'
            session.error_message = str(e)
            session.completed_at = timezone.now()
            session.save()
        except:
            pass

        # Re-raise exception
        raise


@shared_task(name='apps.analysis.tasks.cleanup_old_sessions')
def cleanup_old_sessions(days=30):
    """
    Periodic task to clean up old completed sessions

    Args:
        days: Delete sessions older than this many days
    """
    cutoff_date = timezone.now() - timedelta(days=days)

    old_sessions = AnalysisSession.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed']
    )

    count = old_sessions.count()
    old_sessions.delete()

    return f'Deleted {count} old sessions'


@shared_task(name='apps.analysis.tasks.send_analysis_notification')
def send_analysis_notification(session_id: int, user_email: str):
    """
    Send email notification when analysis completes

    Args:
        session_id: ID of completed analysis
        user_email: User email address
    """
    from django.core.mail import send_mail
    from django.conf import settings

    session = AnalysisSession.objects.get(id=session_id)

    subject = f'Analysis Complete: {session.name}'
    message = f'''
    Your ganglioside analysis has completed.

    Session: {session.name}
    Status: {session.get_status_display()}
    Results: http://yourdomain.com/sessions/{session_id}/results/

    - Ganglioside Analysis Platform
    '''

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )

    return f'Email sent to {user_email}'
```

### 5. Update ViewSet to Use Celery

**File**: `apps/analysis/views.py`

Modify the `analyze` action:

```python
from .tasks import run_analysis_async

@action(detail=True, methods=['post'])
def analyze(self, request, pk=None):
    """Trigger background analysis using Celery"""
    session = self.get_object()

    if session.status in ['processing', 'completed']:
        return Response(
            {'error': f'Analysis is already {session.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Queue analysis task
    task = run_analysis_async.delay(session.id)

    # Store task ID
    session.celery_task_id = task.id
    session.status = 'pending'
    session.save()

    return Response({
        'message': 'Analysis queued successfully',
        'task_id': task.id,
        'session_id': session.id,
        'status': 'pending'
    }, status=status.HTTP_202_ACCEPTED)
```

### 6. Run Celery Workers

**Development**:

```bash
# Terminal 1: Django/Daphne server
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Terminal 2: Celery worker
celery -A config worker -l info

# Terminal 3: Celery beat (periodic tasks)
celery -A config beat -l info

# Terminal 4: Flower (monitoring UI)
celery -A config flower
# Access at: http://localhost:5555
```

**Production** (Systemd services):

**File**: `/etc/systemd/system/celery-worker.service`

```ini
[Unit]
Description=Celery Worker
After=network.target redis-server.service postgresql.service

[Service]
Type=forking
User=ganglioside
Group=ganglioside
WorkingDirectory=/home/ganglioside/django_ganglioside
EnvironmentFile=/home/ganglioside/.env.production
ExecStart=/home/ganglioside/django_ganglioside/venv/bin/celery -A config worker \
    --loglevel=info \
    --logfile=/home/ganglioside/logs/celery_worker.log \
    --pidfile=/var/run/celery/worker.pid

[Install]
WantedBy=multi-user.target
```

**File**: `/etc/systemd/system/celery-beat.service`

```ini
[Unit]
Description=Celery Beat
After=network.target redis-server.service

[Service]
Type=simple
User=ganglioside
Group=ganglioside
WorkingDirectory=/home/ganglioside/django_ganglioside
EnvironmentFile=/home/ganglioside/.env.production
ExecStart=/home/ganglioside/django_ganglioside/venv/bin/celery -A config beat \
    --loglevel=info \
    --logfile=/home/ganglioside/logs/celery_beat.log \
    --pidfile=/var/run/celery/beat.pid

[Install]
WantedBy=multi-user.target
```

Enable services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable celery-worker celery-beat
sudo systemctl start celery-worker celery-beat
```

---

## Integration Testing

### Test Channels

```python
# In Django shell
python manage.py shell

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

channel_layer = get_channel_layer()

# Send test message
async_to_sync(channel_layer.group_send)(
    'analysis_1',
    {
        'type': 'analysis_progress',
        'message': 'Test progress',
        'percentage': 50,
        'current_step': 'test',
    }
)
```

### Test Celery

```python
# Queue a task
from apps.analysis.tasks import run_analysis_async
task = run_analysis_async.delay(session_id=1)

# Check task status
from celery.result import AsyncResult
result = AsyncResult(task.id)
print(result.state)  # PENDING, STARTED, SUCCESS, FAILURE
print(result.info)   # Task result or exception
```

---

## Production Configuration

### Nginx for WebSocket

Add to Nginx config:

```nginx
# WebSocket support
location /ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_redirect off;
    proxy_read_timeout 86400;
}
```

---

## Monitoring & Debugging

### Flower (Celery Monitoring)

Access: http://localhost:5555

Features:
- Real-time task monitoring
- Worker status
- Task history
- Resource usage

### Redis Monitoring

```bash
# Monitor Redis commands
redis-cli monitor

# Check memory usage
redis-cli info memory

# List all keys
redis-cli keys '*'
```

---

**Last Updated**: 2025-10-21
**Status**: Advanced Features Implementation Guide Complete
