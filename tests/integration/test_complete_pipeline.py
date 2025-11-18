#!/usr/bin/env python3
"""
Complete end-to-end integration tests for the analysis and visualization pipeline.

This test module validates the complete workflow from file upload through analysis
to visualization generation using the Django REST API.
"""
import os
import sys
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status

# Add Django project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../django_ganglioside'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Django setup
import django
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User


@pytest.fixture
def api_client():
    """Create API client for testing"""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user for authentication"""
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
    """Load actual testwork.csv file for realistic testing"""
    csv_path = os.path.join(os.path.dirname(__file__), '../../data/sample/testwork.csv')

    if not os.path.exists(csv_path):
        # Fallback to minimal test data
        csv_content = b"""Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),9.572,1000000,1.53,T
GM1(36:1;O2),10.452,500000,4.00,F
GM3(36:1;O2),10.606,2000000,7.74,F
GD3(36:1;O2),10.126,800000,5.27,T
GT1(36:1;O2),8.701,1200000,-0.94,T
"""
    else:
        with open(csv_path, 'rb') as f:
            csv_content = f.read()

    return SimpleUploadedFile(
        "testwork.csv",
        csv_content,
        content_type="text/csv"
    )


@pytest.mark.integration
class TestCompletePipeline:
    """Integration tests for complete analysis and visualization pipeline"""

    def test_health_check(self, api_client):
        """Test that server health endpoint responds correctly"""
        response = api_client.get('/api/health/')

        assert response.status_code == status.HTTP_200_OK, \
            f"Health check failed with status {response.status_code}"
        assert 'status' in response.data, "Health check response missing 'status' field"
        assert response.data['status'] == 'healthy', \
            f"Server not healthy: {response.data.get('status')}"

    def test_analysis_requires_authentication(self, api_client, sample_csv_file):
        """Test that analysis endpoint requires authentication"""
        response = api_client.post(
            '/api/analysis/analyze/',
            {
                'file': sample_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN], \
            "Analysis should require authentication"

    def test_complete_analysis_workflow(self, authenticated_client, sample_csv_file):
        """Test complete analysis workflow from upload to results"""
        # Step 1: Upload and analyze data
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': sample_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK, \
            f"Analysis failed with status {response.status_code}: {response.data}"

        # Step 2: Validate analysis results structure
        assert 'results' in response.data, "Analysis response missing 'results' field"
        results = response.data['results']

        # Step 3: Validate statistics
        assert 'statistics' in results, "Results missing 'statistics' field"
        stats = results['statistics']

        assert 'success_rate' in stats, "Statistics missing 'success_rate'"
        assert 'valid_compounds' in stats, "Statistics missing 'valid_compounds'"
        assert 'outliers' in stats, "Statistics missing 'outliers'"

        # Validate success rate is reasonable
        assert 0 <= stats['success_rate'] <= 100, \
            f"Invalid success rate: {stats['success_rate']}"
        assert stats['valid_compounds'] >= 0, \
            f"Invalid valid_compounds count: {stats['valid_compounds']}"

        return results

    def test_regression_analysis_results(self, authenticated_client, sample_csv_file):
        """Test that regression analysis produces valid models"""
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': sample_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']

        # Validate regression analysis exists
        assert 'regression_analysis' in results, "Results missing 'regression_analysis'"
        regression_data = results['regression_analysis']

        # Validate at least some regression models were created
        assert len(regression_data) > 0, "No regression models were generated"

        # Validate each model has required fields
        for model_name, model_info in regression_data.items():
            assert 'r2' in model_info, f"Model {model_name} missing R² value"
            assert 'equation' in model_info, f"Model {model_name} missing equation"

            # Validate R² is within valid range
            r2_value = model_info['r2']
            assert 0 <= r2_value <= 1, \
                f"Model {model_name} has invalid R² value: {r2_value}"

    def test_visualization_generation(self, authenticated_client, sample_csv_file):
        """Test visualization generation from analysis results"""
        # Step 1: Run analysis first
        analysis_response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': sample_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert analysis_response.status_code == status.HTTP_200_OK
        analysis_results = analysis_response.data['results']

        # Step 2: Request visualization
        viz_response = authenticated_client.post(
            '/api/visualization/generate/',
            {'results': analysis_results},
            format='json'
        )

        assert viz_response.status_code == status.HTTP_200_OK, \
            f"Visualization failed with status {viz_response.status_code}"

        # Step 3: Validate visualization structure
        assert 'plots' in viz_response.data, "Visualization response missing 'plots'"
        plots = viz_response.data['plots']

        # Step 4: Check for critical plot types
        critical_plots = ['regression_scatter', '3d_distribution', 'dashboard']

        # Handle both nested and direct plot structures
        plot_data = plots.get('plots', plots) if isinstance(plots, dict) else {}

        found_plots = []
        for plot_name in critical_plots:
            if plot_name in plot_data and plot_data[plot_name]:
                plot_content = str(plot_data[plot_name])

                # Validate plot has content
                assert len(plot_content) > 1000, \
                    f"Plot {plot_name} seems too small ({len(plot_content)} chars)"

                # Validate plot contains Plotly markers
                assert 'plotly' in plot_content.lower() or 'plot_ly' in plot_content.lower(), \
                    f"Plot {plot_name} doesn't appear to be a Plotly chart"

                found_plots.append(plot_name)

        # Validate at least one critical plot was generated
        assert len(found_plots) > 0, \
            f"No critical plots were generated. Available plots: {list(plot_data.keys())}"

    @pytest.mark.parametrize('outlier_threshold,r2_threshold,rt_tolerance', [
        (2.0, 0.70, 0.1),
        (2.5, 0.75, 0.1),
        (3.0, 0.80, 0.15),
    ])
    def test_analysis_with_different_thresholds(
        self, authenticated_client, sample_csv_file,
        outlier_threshold, r2_threshold, rt_tolerance
    ):
        """Test analysis with various threshold configurations"""
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': sample_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': outlier_threshold,
                'r2_threshold': r2_threshold,
                'rt_tolerance': rt_tolerance
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK, \
            f"Analysis failed with thresholds: outlier={outlier_threshold}, " \
            f"r2={r2_threshold}, rt={rt_tolerance}"

        # Validate results structure exists
        assert 'results' in response.data
        assert 'statistics' in response.data['results']

    def test_invalid_csv_format(self, authenticated_client):
        """Test that invalid CSV format is rejected"""
        invalid_csv = SimpleUploadedFile(
            "invalid.csv",
            b"Invalid,CSV,Format\n1,2,3",
            content_type="text/csv"
        )

        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': invalid_csv,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        # Should fail validation
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ], "Invalid CSV should be rejected"

    def test_missing_required_columns(self, authenticated_client):
        """Test that CSV missing required columns is rejected"""
        incomplete_csv = SimpleUploadedFile(
            "incomplete.csv",
            b"Name,RT\nGM1,10.5",
            content_type="text/csv"
        )

        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': incomplete_csv,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        # Should fail validation
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ], "CSV with missing columns should be rejected"
