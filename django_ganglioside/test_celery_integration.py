#!/usr/bin/env python
"""
Test Celery Integration

This script tests the Celery background task system:
1. Celery app configuration
2. Task discovery
3. Redis broker connection
4. Task execution
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from celery import current_app
from django.conf import settings


def test_celery_configuration():
    """Test Celery app is configured correctly"""
    print("\n=== Testing Celery Configuration ===")

    app = current_app

    print(f"✓ Celery app name: {app.main}")
    print(f"✓ Broker URL: {app.conf.broker_url}")
    print(f"✓ Result backend: {app.conf.result_backend}")
    print(f"✓ Task serializer: {app.conf.task_serializer}")
    print(f"✓ Result serializer: {app.conf.result_serializer}")
    print(f"✓ Timezone: {app.conf.timezone}")

    return True


def test_broker_connection():
    """Test connection to Redis broker"""
    print("\n=== Testing Broker Connection ===")

    try:
        from celery import Celery
        app = Celery(broker=settings.CELERY_BROKER_URL)

        # Test connection by pinging broker
        conn = app.connection()
        conn.ensure_connection(max_retries=3)
        print(f"✓ Successfully connected to broker: {settings.CELERY_BROKER_URL}")
        return True

    except Exception as e:
        print(f"✗ FAIL: Could not connect to broker: {e}")
        return False


def test_task_discovery():
    """Test that tasks are discovered"""
    print("\n=== Testing Task Discovery ===")

    app = current_app
    registered_tasks = list(app.tasks.keys())

    print(f"✓ Total registered tasks: {len(registered_tasks)}")

    # Filter custom tasks (not built-in Celery tasks)
    custom_tasks = [t for t in registered_tasks if t.startswith('analysis.')]

    print(f"✓ Custom analysis tasks: {len(custom_tasks)}")

    expected_tasks = [
        'analysis.run_analysis_async',
        'analysis.cleanup_old_sessions',
        'analysis.send_analysis_notification',
        'analysis.export_results_async',
        'analysis.batch_analysis',
    ]

    for task_name in expected_tasks:
        if task_name in registered_tasks:
            print(f"  ✓ {task_name}")
        else:
            print(f"  ✗ {task_name} - NOT FOUND")

    found_count = sum(1 for t in expected_tasks if t in registered_tasks)
    return found_count == len(expected_tasks)


def test_debug_task():
    """Test built-in debug task"""
    print("\n=== Testing Debug Task ===")

    try:
        from config.celery import debug_task

        # Queue the task
        result = debug_task.delay()

        print(f"✓ Debug task queued: {result.id}")
        print(f"✓ Task state: {result.state}")

        return True

    except Exception as e:
        print(f"✗ FAIL: Could not queue debug task: {e}")
        return False


def test_task_signature():
    """Test task signatures"""
    print("\n=== Testing Task Signatures ===")

    try:
        from apps.analysis.tasks import run_analysis_async, cleanup_old_sessions

        # Create task signatures (don't execute)
        sig1 = run_analysis_async.s(1)
        sig2 = cleanup_old_sessions.s(30)

        print(f"✓ run_analysis_async signature: {sig1}")
        print(f"✓ cleanup_old_sessions signature: {sig2}")

        return True

    except Exception as e:
        print(f"✗ FAIL: Could not create task signatures: {e}")
        return False


def test_celery_beat_models():
    """Test django-celery-beat models"""
    print("\n=== Testing Django-Celery-Beat Models ===")

    try:
        from django_celery_beat.models import PeriodicTask, IntervalSchedule

        # Check if models are accessible
        periodic_count = PeriodicTask.objects.count()
        interval_count = IntervalSchedule.objects.count()

        print(f"✓ PeriodicTask model accessible ({periodic_count} tasks)")
        print(f"✓ IntervalSchedule model accessible ({interval_count} schedules)")

        return True

    except Exception as e:
        print(f"✗ FAIL: Could not access beat models: {e}")
        return False


def test_celery_results_models():
    """Test django-celery-results models"""
    print("\n=== Testing Django-Celery-Results Models ===")

    try:
        from django_celery_results.models import TaskResult

        # Check if model is accessible
        result_count = TaskResult.objects.count()

        print(f"✓ TaskResult model accessible ({result_count} results)")

        return True

    except Exception as e:
        print(f"✗ FAIL: Could not access results models: {e}")
        return False


def create_sample_periodic_task():
    """Create a sample periodic task for cleanup"""
    print("\n=== Creating Sample Periodic Task ===")

    try:
        from django_celery_beat.models import PeriodicTask, IntervalSchedule

        # Create schedule: every 24 hours
        schedule, created = IntervalSchedule.objects.get_or_create(
            every=24,
            period=IntervalSchedule.HOURS,
        )

        # Create periodic task
        task, created = PeriodicTask.objects.get_or_create(
            name='Cleanup old analysis sessions',
            defaults={
                'task': 'analysis.cleanup_old_sessions',
                'interval': schedule,
                'args': '[30]',  # Keep sessions for 30 days
                'enabled': False,  # Disabled by default
            }
        )

        if created:
            print(f"✓ Created periodic task: {task.name}")
        else:
            print(f"✓ Periodic task already exists: {task.name}")

        print(f"  - Schedule: Every {schedule.every} {schedule.period}")
        print(f"  - Task: {task.task}")
        print(f"  - Args: {task.args}")
        print(f"  - Enabled: {task.enabled}")

        return True

    except Exception as e:
        print(f"✗ FAIL: Could not create periodic task: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Celery Integration Test")
    print("="*60)

    results = []

    # Run tests
    results.append(("Celery Configuration", test_celery_configuration()))
    results.append(("Broker Connection", test_broker_connection()))
    results.append(("Task Discovery", test_task_discovery()))
    results.append(("Debug Task", test_debug_task()))
    results.append(("Task Signatures", test_task_signature()))
    results.append(("Celery Beat Models", test_celery_beat_models()))
    results.append(("Celery Results Models", test_celery_results_models()))
    results.append(("Sample Periodic Task", create_sample_periodic_task()))

    # Print summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed")
    print("="*60)

    if passed == total:
        print("\n🎉 All tests passed! Celery is ready.")
        print("\nNext steps:")
        print("1. Start Celery worker:")
        print("   celery -A config worker -l info")
        print("\n2. Start Celery beat (for periodic tasks):")
        print("   celery -A config beat -l info")
        print("\n3. Start Flower (monitoring dashboard):")
        print("   celery -A config flower")
        print("\n4. Queue a test analysis task and monitor in Flower")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
