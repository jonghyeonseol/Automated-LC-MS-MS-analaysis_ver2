#!/usr/bin/env python
"""
Test Django Channels Integration

This script tests the complete WebSocket flow:
1. Channel layer configuration
2. Consumer routing
3. Progress message sending
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime


def test_channel_layer():
    """Test channel layer is configured correctly"""
    print("\n=== Testing Channel Layer ===")
    channel_layer = get_channel_layer()

    if not channel_layer:
        print("✗ FAIL: Channel layer not configured")
        return False

    print(f"✓ Channel layer type: {type(channel_layer).__name__}")
    print(f"✓ Channel layer: {channel_layer}")
    return True


def test_send_progress_message(session_id=1):
    """Test sending a progress message"""
    print(f"\n=== Testing Progress Message (Session {session_id}) ===")

    channel_layer = get_channel_layer()
    if not channel_layer:
        print("✗ FAIL: No channel layer")
        return False

    room_group_name = f'analysis_{session_id}'

    try:
        # Send progress update
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'analysis_progress',
                'message': 'Test progress message',
                'percentage': 50,
                'current_step': 'Testing',
                'timestamp': datetime.now().isoformat(),
            }
        )
        print(f"✓ Sent progress message to room: {room_group_name}")
        return True

    except Exception as e:
        print(f"✗ FAIL: Error sending message: {e}")
        return False


def test_send_complete_message(session_id=1):
    """Test sending a completion message"""
    print(f"\n=== Testing Completion Message (Session {session_id}) ===")

    channel_layer = get_channel_layer()
    if not channel_layer:
        print("✗ FAIL: No channel layer")
        return False

    room_group_name = f'analysis_{session_id}'

    try:
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'analysis_complete',
                'message': 'Test analysis complete!',
                'success': True,
                'results_url': f'/analysis/sessions/{session_id}/',
                'timestamp': datetime.now().isoformat(),
            }
        )
        print(f"✓ Sent completion message to room: {room_group_name}")
        return True

    except Exception as e:
        print(f"✗ FAIL: Error sending message: {e}")
        return False


def test_import_consumer():
    """Test that consumer imports correctly"""
    print("\n=== Testing Consumer Import ===")

    try:
        from apps.analysis.consumers import AnalysisProgressConsumer
        print(f"✓ Consumer imported: {AnalysisProgressConsumer}")
        return True
    except Exception as e:
        print(f"✗ FAIL: Could not import consumer: {e}")
        return False


def test_import_routing():
    """Test that routing imports correctly"""
    print("\n=== Testing Routing Import ===")

    try:
        from apps.analysis.routing import websocket_urlpatterns
        print(f"✓ Routing imported: {len(websocket_urlpatterns)} URL pattern(s)")
        for pattern in websocket_urlpatterns:
            print(f"  - {pattern.pattern}")
        return True
    except Exception as e:
        print(f"✗ FAIL: Could not import routing: {e}")
        return False


def test_asgi_application():
    """Test that ASGI application loads"""
    print("\n=== Testing ASGI Application ===")

    try:
        from config.asgi import application
        print(f"✓ ASGI application loaded: {type(application).__name__}")
        return True
    except Exception as e:
        print(f"✗ FAIL: Could not load ASGI application: {e}")
        return False


def main():
    """Run all tests"""
    print("="*60)
    print("Django Channels Integration Test")
    print("="*60)

    results = []

    # Run tests
    results.append(("Channel Layer Configuration", test_channel_layer()))
    results.append(("Consumer Import", test_import_consumer()))
    results.append(("Routing Import", test_import_routing()))
    results.append(("ASGI Application", test_asgi_application()))
    results.append(("Send Progress Message", test_send_progress_message()))
    results.append(("Send Complete Message", test_send_complete_message()))

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
        print("\n🎉 All tests passed! Django Channels is ready.")
        print("\nNext steps:")
        print("1. Start Daphne server: daphne -b 0.0.0.0 -p 8000 config.asgi:application")
        print("2. Run an analysis and watch real-time progress updates")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
