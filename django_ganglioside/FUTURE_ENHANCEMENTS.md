# Future Enhancements - Django Ganglioside Platform

**Status**: Week 2 Complete (Core Features Functional)
**Date**: 2025-10-21

This document outlines planned enhancements that require additional infrastructure (Redis, WebSockets, etc.) and are deferred to future development cycles.

---

## Phase 3: Real-time Progress with Django Channels

**Status**: 📋 Planned (Not Implemented)
**Reason**: Requires Redis setup and additional complexity
**Current Solution**: Page auto-refresh every 5 seconds for processing sessions

### Implementation Plan

#### 3.1 Install Dependencies
```bash
pip install channels[daphne] channels-redis
```

#### 3.2 Configure Django Channels

**`config/asgi.py`**:
```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import apps.analysis.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.analysis.routing.websocket_urlpatterns
        )
    ),
})
```

**`config/settings/base.py`** (add to INSTALLED_APPS):
```python
INSTALLED_APPS = [
    'daphne',  # Before django.contrib.staticfiles
    ...
]

ASGI_APPLICATION = 'config.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}
```

#### 3.3 Create WebSocket Consumer

**`apps/analysis/consumers.py`**:
```python
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class AnalysisProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'analysis_{self.session_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def analysis_progress(self, event):
        await self.send(text_data=json.dumps({
            'type': 'progress',
            'message': event['message'],
            'percentage': event['percentage'],
            'current_step': event['current_step']
        }))

    async def analysis_complete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'complete',
            'message': event['message'],
            'redirect_url': event['redirect_url']
        }))
```

**`apps/analysis/routing.py`**:
```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/analysis/(?P<session_id>\d+)/$', consumers.AnalysisProgressConsumer.as_asgi()),
]
```

#### 3.4 Send Progress from Service

**Update `apps/analysis/services/analysis_service.py`**:
```python
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class AnalysisService:
    def _send_progress(self, session_id, message, percentage, step):
        """Send progress update via WebSocket"""
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'analysis_{session_id}',
            {
                'type': 'analysis_progress',
                'message': message,
                'percentage': percentage,
                'current_step': step
            }
        )

    def run_analysis(self, session):
        # ... existing code ...

        # Send progress updates
        self._send_progress(session.id, "Preprocessing data...", 10, "preprocessing")
        # ... preprocessing ...

        self._send_progress(session.id, "Running Rule 1 regression...", 25, "rule1")
        # ... rule 1 ...

        self._send_progress(session.id, "Running Rules 2-3...", 50, "rule2_3")
        # ... rules 2-3 ...

        self._send_progress(session.id, "Running Rule 4...", 70, "rule4")
        # ... rule 4 ...

        self._send_progress(session.id, "Running Rule 5...", 85, "rule5")
        # ... rule 5 ...

        self._send_progress(session.id, "Saving results...", 95, "saving")
        # ... save ...

        # Send completion
        async_to_sync(channel_layer.group_send)(
            f'analysis_{session.id}',
            {
                'type': 'analysis_complete',
                'message': 'Analysis completed!',
                'redirect_url': f'/analysis/sessions/{session.id}/results/'
            }
        )
```

#### 3.5 Frontend WebSocket Client

**In `templates/analysis/session_detail.html`**:
```html
<script>
{% if session.status == 'processing' %}
const sessionId = {{ session.id }};
const wsUrl = `ws://${window.location.host}/ws/analysis/${sessionId}/`;
const socket = new WebSocket(wsUrl);

socket.onmessage = function(e) {
    const data = JSON.parse(e.data);

    if (data.type === 'progress') {
        document.getElementById('progressBar').style.width = data.percentage + '%';
        document.getElementById('progressMessage').textContent = data.message;
    } else if (data.type === 'complete') {
        window.location.href = data.redirect_url;
    }
};

socket.onclose = function(e) {
    console.error('WebSocket closed unexpectedly');
};
{% endif %}
</script>
```

#### 3.6 Run with Daphne

```bash
# Instead of runserver, use:
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

## Phase 4: Background Tasks with Celery

**Status**: 📋 Planned (Not Implemented)
**Reason**: Requires Redis and worker processes
**Current Solution**: Synchronous analysis in view (works fine for development)

### Implementation Plan

#### 4.1 Install Dependencies
```bash
pip install celery redis django-celery-beat django-celery-results
```

#### 4.2 Configure Celery

**`config/celery.py`** (already exists, uncomment):
```python
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('ganglioside')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

**`config/__init__.py`** (uncomment):
```python
from .celery import app as celery_app
__all__ = ('celery_app',)
```

**`config/settings/base.py`** (uncomment in INSTALLED_APPS):
```python
THIRD_PARTY_APPS = [
    ...
    'django_celery_beat',
    'django_celery_results',
]

# Already configured:
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

#### 4.3 Create Celery Tasks

**`apps/analysis/tasks.py`**:
```python
from celery import shared_task
from django.utils import timezone
from .models import AnalysisSession
from .services.analysis_service import AnalysisService

@shared_task(bind=True)
def run_analysis_task(self, session_id):
    """
    Background task to run analysis
    """
    try:
        session = AnalysisSession.objects.get(id=session_id)

        # Update status
        session.status = 'processing'
        session.started_at = timezone.now()
        session.save()

        # Run analysis
        service = AnalysisService()
        result = service.run_analysis(session)

        # Update status
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()

        return {'success': True, 'session_id': session_id}

    except Exception as e:
        session.status = 'failed'
        session.error_message = str(e)
        session.completed_at = timezone.now()
        session.save()

        raise

@shared_task
def cleanup_old_sessions():
    """
    Periodic task to clean up old sessions
    """
    from datetime import timedelta
    from django.utils import timezone

    cutoff_date = timezone.now() - timedelta(days=30)
    old_sessions = AnalysisSession.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed']
    )

    count = old_sessions.count()
    old_sessions.delete()

    return f'Deleted {count} old sessions'
```

#### 4.4 Update ViewSet to Use Celery

**`apps/analysis/views.py`** (modify analyze action):
```python
@action(detail=True, methods=['post'])
def analyze(self, request, pk=None):
    session = self.get_object()

    if session.status in ['processing', 'completed']:
        return Response({'error': f'Analysis is already {session.status}'}, status=400)

    # Queue analysis task
    from .tasks import run_analysis_task
    task = run_analysis_task.delay(session.id)

    # Store task ID
    session.celery_task_id = task.id
    session.status = 'processing'
    session.save()

    return Response({
        'message': 'Analysis queued',
        'task_id': task.id,
        'session_id': session.id
    }, status=202)
```

#### 4.5 Start Celery Worker

```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A config worker -l info

# Terminal 3: Celery beat (for periodic tasks)
celery -A config beat -l info
```

#### 4.6 Configure Periodic Tasks

**In Django admin** → Periodic tasks → Add:
- Task: `apps.analysis.tasks.cleanup_old_sessions`
- Schedule: Cron `0 2 * * *` (daily at 2 AM)

---

## Phase 3-4 Summary

### What We Built Instead

Since Phases 3-4 require Redis infrastructure:
- **Auto-refresh**: Session detail page refreshes every 5 seconds during processing
- **Synchronous execution**: Analysis runs directly in the view (fine for development/small datasets)
- **Simple progress**: Status field updates (pending → processing → completed/failed)

### When to Implement

Implement Channels + Celery when:
1. **Redis is available** on the deployment server
2. **Analyses take >30 seconds** (currently ~5-10s for typical datasets)
3. **Multiple concurrent users** need to run analyses
4. **Real-time feedback** is critical for user experience

### Effort Estimate

- **Phase 3 (Channels)**: 2-3 hours (Redis setup + WebSocket implementation)
- **Phase 4 (Celery)**: 2-3 hours (Worker setup + task migration)
- **Total**: 4-6 hours additional work

---

## Alternative: Lightweight Progress Without Redis

If you want progress updates without Redis, consider:

### Option 1: Database Polling

**Add to `AnalysisSession` model**:
```python
class AnalysisSession(models.Model):
    # ... existing fields ...
    progress_percentage = models.IntegerField(default=0)
    progress_message = models.CharField(max_length=255, blank=True)
    current_step = models.CharField(max_length=50, blank=True)
```

**Update service to write progress**:
```python
def run_analysis(self, session):
    session.progress_percentage = 10
    session.progress_message = "Preprocessing data..."
    session.save()
    # ... continue ...
```

**Frontend polls every 2 seconds**:
```javascript
setInterval(function() {
    fetch(`/api/sessions/${sessionId}/status/`)
        .then(r => r.json())
        .then(data => {
            $('#progressBar').css('width', data.progress_percentage + '%');
            $('#progressMessage').text(data.progress_message);
        });
}, 2000);
```

### Option 2: Server-Sent Events (SSE)

Simpler than WebSockets, no Redis needed:

```python
# View
from django.http import StreamingHttpResponse

def analysis_stream(request, session_id):
    def event_stream():
        session = AnalysisSession.objects.get(id=session_id)
        while session.status == 'processing':
            session.refresh_from_db()
            yield f"data: {json.dumps({'percentage': session.progress_percentage})}\n\n"
            time.sleep(1)

    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
```

---

**Last Updated**: 2025-10-21
**Status**: Documentation complete, implementation deferred
