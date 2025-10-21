"""
Pytest configuration and fixtures for Ganglioside Analysis Platform
"""
import os
import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient


# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')


@pytest.fixture
def api_client():
    """Create API client for testing"""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Create authenticated API client"""
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def sample_csv_file():
    """Create a sample CSV file for testing"""
    csv_content = b"""Name,RT,Volume,Log P,Anchor
GM1(36:1;O2),10.452,500000,4.00,F
GM3(36:1;O2),10.606,2000000,7.74,F
GD1(36:1;O2),9.572,1000000,1.53,T
GD3(36:1;O2),10.126,800000,5.27,T
GT1(36:1;O2),8.701,1200000,-0.94,T
"""
    return SimpleUploadedFile(
        "test_data.csv",
        csv_content,
        content_type="text/csv"
    )


@pytest.fixture
def sample_analysis_data():
    """Sample analysis data for testing"""
    return {
        'name': 'Test Analysis',
        'data_type': 'porcine',
        'r2_threshold': 0.75,
        'outlier_threshold': 2.5,
        'rt_tolerance': 0.1,
    }


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Automatically enable database access for all tests"""
    pass


@pytest.fixture
def celery_eager_mode(settings):
    """Run Celery tasks synchronously for testing"""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
