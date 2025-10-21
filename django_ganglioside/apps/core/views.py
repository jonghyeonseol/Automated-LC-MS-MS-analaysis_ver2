"""
Core views - Health check
"""
from django.http import JsonResponse
from django.db import connection
from django.utils import timezone
import redis
from django.conf import settings


def health_check(request):
    """
    Health check endpoint for monitoring
    Tests database and Redis connectivity
    """
    health = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'ganglioside-analysis-django',
        'version': '2.0.0',
        'checks': {}
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'

    # Check Redis
    try:
        r = redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        health['checks']['redis'] = 'ok'
    except Exception as e:
        health['checks']['redis'] = f'error: {str(e)}'
        health['status'] = 'degraded'  # Redis is optional

    return JsonResponse(health)
