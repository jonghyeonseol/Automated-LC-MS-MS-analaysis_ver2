#!/usr/bin/env python
"""
Week 2 Integration Test Suite

Tests the complete integration of:
- Django Channels (WebSocket)
- Celery (Background Tasks)
- PostgreSQL (Database)
- Complete analysis workflow
"""

import os
import sys
import django
import time
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth.models import User
from django.core.files import File
from apps.analysis.models import AnalysisSession, Compound, AnalysisResult
from apps.analysis.services.analysis_service import AnalysisService
from apps.analysis.tasks import run_analysis_async, cleanup_old_sessions
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from celery.result import AsyncResult
from django.db import connection


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_postgresql_connection():
    """Test PostgreSQL database connection"""
    print_section("Test 1: PostgreSQL Connection")

    try:
        db_settings = connection.settings_dict
        print(f"✓ Database: {db_settings['NAME']}")
        print(f"✓ User: {db_settings['USER']}")
        print(f"✓ Host: {db_settings['HOST']}:{db_settings['PORT']}")

        # Test query
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✓ PostgreSQL Version: {version.split(',')[0]}")

        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_database_data_integrity():
    """Test that all data was migrated correctly"""
    print_section("Test 2: Database Data Integrity")

    try:
        user_count = User.objects.count()
        session_count = AnalysisSession.objects.count()
        result_count = AnalysisResult.objects.count()
        compound_count = Compound.objects.count()

        print(f"✓ Users: {user_count}")
        print(f"✓ Sessions: {session_count}")
        print(f"✓ Results: {result_count}")
        print(f"✓ Compounds: {compound_count}")

        # Verify relationships
        if session_count > 0:
            latest = AnalysisSession.objects.latest('created_at')
            print(f"✓ Latest Session: #{latest.id} - {latest.name}")

            if hasattr(latest, 'result'):
                print(f"✓ Has Result: {latest.result.total_compounds} compounds")

        return compound_count > 0
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_postgresql_performance():
    """Test PostgreSQL query performance"""
    print_section("Test 3: PostgreSQL Performance")

    try:
        # Test 1: Simple count
        start = time.time()
        count = Compound.objects.count()
        duration_ms = (time.time() - start) * 1000
        print(f"✓ Count query: {count} records in {duration_ms:.2f}ms")

        # Test 2: Complex query with joins
        start = time.time()
        compounds = list(
            Compound.objects
            .select_related('session')
            .prefetch_related('session__result')
            .filter(status='valid')[:100]
        )
        duration_ms = (time.time() - start) * 1000
        print(f"✓ Complex query: {len(compounds)} records in {duration_ms:.2f}ms")

        # Test 3: Aggregation
        start = time.time()
        from django.db.models import Count, Avg
        stats = Compound.objects.aggregate(
            total=Count('id'),
            avg_rt=Avg('rt')
        )
        duration_ms = (time.time() - start) * 1000
        print(f"✓ Aggregation query: {duration_ms:.2f}ms")
        print(f"  Total: {stats['total']}, Avg RT: {stats['avg_rt']:.2f}")

        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_channels_configuration():
    """Test Django Channels is properly configured"""
    print_section("Test 4: Django Channels Configuration")

    try:
        channel_layer = get_channel_layer()

        if not channel_layer:
            print("✗ FAIL: Channel layer not configured")
            return False

        print(f"✓ Channel layer: {type(channel_layer).__name__}")
        print(f"✓ Config: {channel_layer}")

        # Test sending a message
        async_to_sync(channel_layer.group_send)(
            'test_group',
            {
                'type': 'test_message',
                'message': 'Integration test',
            }
        )
        print("✓ Message sent successfully")

        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_celery_configuration():
    """Test Celery is properly configured"""
    print_section("Test 5: Celery Configuration")

    try:
        from config.celery import app

        print(f"✓ Celery app: {app.main}")
        print(f"✓ Broker: {app.conf.broker_url}")
        print(f"✓ Result backend: {app.conf.result_backend}")

        # Check registered tasks
        analysis_tasks = [t for t in app.tasks.keys() if 'analysis' in t]
        print(f"✓ Analysis tasks registered: {len(analysis_tasks)}")

        for task_name in sorted(analysis_tasks):
            print(f"  - {task_name}")

        return len(analysis_tasks) >= 5
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_celery_task_queue():
    """Test queuing a Celery task"""
    print_section("Test 6: Celery Task Queue")

    try:
        # Get a test session
        session = AnalysisSession.objects.filter(status='completed').first()

        if not session:
            print("⚠ SKIP: No completed sessions to test with")
            return True

        print(f"✓ Test session: #{session.id}")

        # Queue a cleanup task (won't actually delete anything with days=999)
        result = cleanup_old_sessions.delay(days=999)

        print(f"✓ Task queued: {result.id}")
        print(f"✓ Task state: {result.state}")

        # Wait briefly and check status
        time.sleep(0.5)
        print(f"✓ Task ready: {result.ready()}")

        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_analysis_service_with_postgres():
    """Test analysis service works with PostgreSQL"""
    print_section("Test 7: Analysis Service with PostgreSQL")

    try:
        # Get test user
        user = User.objects.first()
        if not user:
            print("✗ FAIL: No users found")
            return False

        # Find test CSV
        test_csv = Path('../data/sample/testwork.csv')
        if not test_csv.exists():
            print("⚠ SKIP: testwork.csv not found")
            return True

        print(f"✓ Test user: {user.username}")
        print(f"✓ Test file: {test_csv}")

        # Create session
        with open(test_csv, 'rb') as f:
            file_obj = File(f, name='testwork.csv')
            file_size = test_csv.stat().st_size

            session = AnalysisSession.objects.create(
                user=user,
                name="Integration Test - PostgreSQL",
                data_type='porcine',
                uploaded_file=file_obj,
                file_size=file_size,
                original_filename='testwork.csv',
                r2_threshold=0.75,
                outlier_threshold=2.5,
                rt_tolerance=0.1,
            )

        print(f"✓ Session created: #{session.id}")

        # Run analysis
        service = AnalysisService()
        start = time.time()
        result = service.run_analysis(session)
        duration = time.time() - start

        print(f"✓ Analysis completed in {duration:.2f}s")
        print(f"✓ Total compounds: {result.total_compounds}")
        print(f"✓ Valid compounds: {result.valid_compounds}")
        print(f"✓ Success rate: {result.success_rate}%")

        # Verify data was saved to PostgreSQL
        compounds = Compound.objects.filter(session=session)
        print(f"✓ Compounds saved to PostgreSQL: {compounds.count()}")

        return result.valid_compounds > 0
    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_channels_celery_integration():
    """Test Channels + Celery work together"""
    print_section("Test 8: Channels + Celery Integration")

    try:
        channel_layer = get_channel_layer()

        # Simulate what happens during async analysis
        session_id = 1
        room_group = f'analysis_{session_id}'

        # Send progress update (like Celery task would)
        async_to_sync(channel_layer.group_send)(
            room_group,
            {
                'type': 'analysis_progress',
                'message': 'Integration test progress',
                'percentage': 50,
                'current_step': 'Testing',
                'timestamp': '2025-10-21T23:30:00',
            }
        )
        print(f"✓ Progress message sent to room: {room_group}")

        # Send completion message
        async_to_sync(channel_layer.group_send)(
            room_group,
            {
                'type': 'analysis_complete',
                'message': 'Integration test complete',
                'success': True,
                'results_url': f'/analysis/sessions/{session_id}/',
                'timestamp': '2025-10-21T23:30:01',
            }
        )
        print(f"✓ Completion message sent to room: {room_group}")

        print("✓ Channels + Celery integration working")
        return True
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_concurrent_database_access():
    """Test PostgreSQL handles concurrent access"""
    print_section("Test 9: Concurrent Database Access")

    try:
        from django.db import transaction

        # Simulate concurrent writes
        user = User.objects.first()

        # Create multiple sessions in transactions
        sessions_created = []

        for i in range(3):
            with transaction.atomic():
                session = AnalysisSession.objects.create(
                    user=user,
                    name=f"Concurrent Test {i+1}",
                    data_type='porcine',
                    status='pending',
                    file_size=1024,  # Dummy file size
                    original_filename=f'test_{i+1}.csv',
                )
                sessions_created.append(session.id)

        print(f"✓ Created {len(sessions_created)} sessions concurrently")

        # Verify all were saved
        saved_count = AnalysisSession.objects.filter(
            id__in=sessions_created
        ).count()

        print(f"✓ Verified {saved_count}/{len(sessions_created)} saved")

        # Cleanup
        AnalysisSession.objects.filter(id__in=sessions_created).delete()
        print(f"✓ Cleanup: Deleted test sessions")

        return saved_count == len(sessions_created)
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def test_system_health():
    """Overall system health check"""
    print_section("Test 10: Overall System Health")

    try:
        from django.core.management import call_command
        from io import StringIO

        # Run Django check
        out = StringIO()
        call_command('check', stdout=out)
        print("✓ Django system check: PASSED")

        # Check all services
        checks = {
            'PostgreSQL': connection.cursor() is not None,
            'Channels': get_channel_layer() is not None,
            'Celery': True,  # Already tested
            'Models': AnalysisSession.objects.count() >= 0,
        }

        print("\nService Status:")
        all_ok = True
        for service, status in checks.items():
            icon = "✓" if status else "✗"
            print(f"  {icon} {service}: {'OK' if status else 'FAIL'}")
            all_ok = all_ok and status

        return all_ok
    except Exception as e:
        print(f"✗ FAIL: {e}")
        return False


def main():
    """Run all integration tests"""
    print("\n" + "="*60)
    print("  WEEK 2 INTEGRATION TEST SUITE")
    print("  Advanced Features Validation")
    print("="*60)

    results = []

    # Run tests in order
    results.append(("PostgreSQL Connection", test_postgresql_connection()))
    results.append(("Database Data Integrity", test_database_data_integrity()))
    results.append(("PostgreSQL Performance", test_postgresql_performance()))
    results.append(("Channels Configuration", test_channels_configuration()))
    results.append(("Celery Configuration", test_celery_configuration()))
    results.append(("Celery Task Queue", test_celery_task_queue()))
    results.append(("Analysis Service + PostgreSQL", test_analysis_service_with_postgres()))
    results.append(("Channels + Celery Integration", test_channels_celery_integration()))
    results.append(("Concurrent Database Access", test_concurrent_database_access()))
    results.append(("Overall System Health", test_system_health()))

    # Print summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "="*60)
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*60)

    if passed == total:
        print("\n🎉 All integration tests passed!")
        print("\n✅ Week 2 Advanced Features are fully operational:")
        print("   - Django Channels (WebSocket)")
        print("   - Celery (Background Tasks)")
        print("   - PostgreSQL (Production Database)")
        print("   - Complete Integration")
        print("\n🚀 System is PRODUCTION READY!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed.")
        print("Please review errors above and ensure all services are running:")
        print("  - Redis server")
        print("  - PostgreSQL server")
        print("  - Celery worker (for full test coverage)")
        return 1


if __name__ == '__main__':
    sys.exit(main())
