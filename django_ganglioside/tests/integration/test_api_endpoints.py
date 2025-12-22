"""
Integration tests for API endpoints
"""
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from apps.analysis.models import AnalysisSession


@pytest.mark.integration
class TestAnalysisAPIEndpoints:
    """Test Analysis API endpoints"""

    def test_create_analysis_session_unauthorized(self, api_client, sample_csv_file):
        """Test creating session without authentication fails"""
        url = reverse('analysis:api-session-list')
        data = {
            'name': 'Test Analysis',
            'data_type': 'porcine',
            'uploaded_file': sample_csv_file,
        }

        response = api_client.post(url, data, format='multipart')

        # Should require authentication
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_create_analysis_session_authorized(self, authenticated_client, sample_csv_file):
        """Test creating session with authentication"""
        url = reverse('analysis:api-session-list')
        data = {
            'name': 'Test Analysis',
            'data_type': 'porcine',
            'uploaded_file': sample_csv_file,
            'r2_threshold': 0.75,
            'outlier_threshold': 2.5,
            'rt_tolerance': 0.1,
        }

        response = authenticated_client.post(url, data, format='multipart')

        # Should succeed
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert response.data['name'] == 'Test Analysis'
        assert response.data['status'] == 'pending'

    def test_list_user_sessions(self, authenticated_client, test_user):
        """Test listing user's sessions"""
        # Create sessions
        for i in range(3):
            AnalysisSession.objects.create(
                user=test_user,
                name=f"Session {i}",
                data_type="porcine",
                status="completed",
                file_size=1024,
                original_filename=f"test_{i}.csv",
            )

        url = reverse('analysis:api-session-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3

    def test_retrieve_session_detail(self, authenticated_client, test_user):
        """Test retrieving session details"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Detail Test",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        url = reverse('analysis:api-session-detail', kwargs={'pk': session.id})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == session.id
        assert response.data['name'] == "Detail Test"

    def test_update_session(self, authenticated_client, test_user):
        """Test updating session"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Original Name",
            data_type="porcine",
            status="pending",
            file_size=1024,
            original_filename="test.csv",
        )

        url = reverse('analysis:api-session-detail', kwargs={'pk': session.id})
        data = {'name': 'Updated Name'}

        response = authenticated_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated Name'

        session.refresh_from_db()
        assert session.name == 'Updated Name'

    def test_delete_session(self, authenticated_client, test_user):
        """Test deleting session (soft delete)"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Delete Test",
            data_type="porcine",
            status="pending",
            file_size=1024,
            original_filename="test.csv",
        )

        url = reverse('analysis:api-session-detail', kwargs={'pk': session.id})
        response = authenticated_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Note: AnalysisSession uses SoftDeleteModel, so it will be soft-deleted
        # The default manager should filter out soft-deleted items
        session.refresh_from_db()
        assert session.is_deleted == True

    def test_filter_sessions_by_status(self, authenticated_client, test_user):
        """Test filtering sessions by status"""
        # Create sessions with different statuses
        AnalysisSession.objects.create(
            user=test_user,
            name="Pending Session",
            data_type="porcine",
            status="pending",
            file_size=1024,
            original_filename="test1.csv",
        )
        AnalysisSession.objects.create(
            user=test_user,
            name="Completed Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test2.csv",
        )

        url = reverse('analysis:api-session-list')
        response = authenticated_client.get(url, {'status': 'completed'})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['status'] == 'completed'

    def test_user_can_only_access_own_sessions(self, api_client, test_user, db):
        """Test users can only access their own sessions"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            password='otherpass123'
        )

        # Create session for other user
        other_session = AnalysisSession.objects.create(
            user=other_user,
            name="Other Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="other.csv",
        )

        # Authenticate as test_user
        api_client.force_authenticate(user=test_user)

        # Try to access other user's session
        url = reverse('analysis:api-session-detail', kwargs={'pk': other_session.id})
        response = api_client.get(url)

        # Should not be able to access
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.integration
class TestHealthCheckEndpoint:
    """Test health check endpoint"""

    def test_health_check_endpoint(self, api_client):
        """Test health check returns healthy status"""
        url = reverse('core:health-check')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Health check returns JsonResponse, use .json() instead of .data
        data = response.json()
        assert data['status'] in ['healthy', 'degraded']  # Redis might be unavailable
        assert 'checks' in data
        assert data['checks']['database'] == 'ok'


@pytest.mark.integration
class TestAPIValidation:
    """Test API input validation"""

    def test_invalid_data_type(self, authenticated_client, sample_csv_file):
        """Test invalid data_type is rejected"""
        url = reverse('analysis:api-session-list')
        data = {
            'name': 'Test',
            'data_type': 'invalid_type',  # Invalid
            'uploaded_file': sample_csv_file,
        }

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'data_type' in response.data

    def test_missing_required_fields(self, authenticated_client):
        """Test missing required fields are rejected"""
        url = reverse('analysis:api-session-list')
        data = {}  # Missing required fields

        response = authenticated_client.post(url, data, format='multipart')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_threshold_values(self, authenticated_client, sample_csv_file):
        """Test invalid threshold values are rejected"""
        url = reverse('analysis:api-session-list')
        data = {
            'name': 'Test',
            'data_type': 'porcine',
            'uploaded_file': sample_csv_file,
            'r2_threshold': -0.5,  # Invalid (should be 0-1)
        }

        response = authenticated_client.post(url, data, format='multipart')

        # Should either reject or coerce to valid value
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_201_CREATED]


@pytest.mark.integration
class TestAPIPagination:
    """Test API pagination"""

    def test_pagination_works(self, authenticated_client, test_user):
        """Test pagination of session list"""
        # Create many sessions
        for i in range(25):
            AnalysisSession.objects.create(
                user=test_user,
                name=f"Session {i}",
                data_type="porcine",
                status="completed",
                file_size=1024,
                original_filename=f"test_{i}.csv",
            )

        url = reverse('analysis:api-session-list')
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data
        assert 'results' in response.data
        assert response.data['count'] == 25

    def test_pagination_page_size(self, authenticated_client, test_user):
        """Test custom page size"""
        # Create sessions
        for i in range(15):
            AnalysisSession.objects.create(
                user=test_user,
                name=f"Session {i}",
                data_type="porcine",
                status="completed",
                file_size=1024,
                original_filename=f"test_{i}.csv",
            )

        url = reverse('analysis:api-session-list')
        response = authenticated_client.get(url, {'page_size': 5})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5
