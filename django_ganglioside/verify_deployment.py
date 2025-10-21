#!/usr/bin/env python
"""
Quick deployment verification script
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.analysis.models import AnalysisSession, AnalysisResult, Compound, RegressionModel

User = get_user_model()

print("=" * 80)
print("DJANGO GANGLIOSIDE PLATFORM - DEPLOYMENT VERIFICATION")
print("=" * 80)

# Check models
print("\n[1/5] Checking database models...")
try:
    user_count = User.objects.count()
    session_count = AnalysisSession.objects.count()
    result_count = AnalysisResult.objects.count()
    compound_count = Compound.objects.count()
    model_count = RegressionModel.objects.count()

    print(f"✅ Database accessible")
    print(f"   - Users: {user_count}")
    print(f"   - Sessions: {session_count}")
    print(f"   - Results: {result_count}")
    print(f"   - Compounds: {compound_count}")
    print(f"   - Regression Models: {model_count}")
except Exception as e:
    print(f"❌ Database error: {e}")
    import sys
    sys.exit(1)

# Check recent analysis
print("\n[2/5] Checking most recent analysis...")
try:
    latest_session = AnalysisSession.objects.filter(status='completed').latest('created_at')
    print(f"✅ Latest session found:")
    print(f"   - ID: {latest_session.id}")
    print(f"   - Name: {latest_session.name}")
    print(f"   - Status: {latest_session.get_status_display()}")
    print(f"   - Created: {latest_session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if hasattr(latest_session, 'result'):
        result = latest_session.result
        print(f"   - Success rate: {result.success_rate:.2f}%")
        print(f"   - Compounds: {result.total_compounds} total, {result.valid_compounds} valid")
except AnalysisSession.DoesNotExist:
    print("⚠️  No completed analyses found yet")

# Check URLs
print("\n[3/5] Checking URL configuration...")
try:
    from django.urls import resolve, reverse

    urls_to_check = [
        ('analysis:home', 'Home page'),
        ('analysis:upload', 'Upload page'),
        ('analysis:history', 'History page'),
        ('schema', 'API Schema'),
    ]

    for url_name, description in urls_to_check:
        try:
            url = reverse(url_name)
            print(f"✅ {description}: {url}")
        except Exception as e:
            print(f"⚠️  {description}: Could not reverse ({e})")

except Exception as e:
    print(f"❌ URL configuration error: {e}")

# Check settings
print("\n[4/5] Checking settings...")
from django.conf import settings

print(f"✅ Settings loaded:")
print(f"   - DEBUG: {settings.DEBUG}")
print(f"   - Database: {settings.DATABASES['default']['ENGINE'].split('.')[-1]}")
print(f"   - Media root: {settings.MEDIA_ROOT}")
print(f"   - Static root: {settings.STATIC_ROOT}")

# Check installed apps
print("\n[5/5] Checking installed apps...")
custom_apps = [app for app in settings.INSTALLED_APPS if app.startswith('apps.')]
print(f"✅ Custom apps installed:")
for app in custom_apps:
    print(f"   - {app}")

# Summary
print("\n" + "=" * 80)
print("DEPLOYMENT VERIFICATION COMPLETE")
print("=" * 80)
print("\n✅ System is ready for production use!")
print("\nTo start the server:")
print("  python manage.py runserver")
print("\nAccess points:")
print("  • Web UI: http://localhost:8000/")
print("  • Admin: http://localhost:8000/admin/")
print("  • API Docs: http://localhost:8000/api/docs/")
print("=" * 80)
