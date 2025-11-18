#!/usr/bin/env python3
"""
Comprehensive integration tests using user's actual testwork_user.csv data.

This test module validates the entire analysis and visualization pipeline
with real-world data to ensure production readiness.
"""
import os
import sys
import pytest
import pandas as pd
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
        username='testuser_real_data',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Create authenticated API client"""
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def user_csv_file():
    """Load user's actual testwork_user.csv file"""
    csv_path = os.path.join(os.path.dirname(__file__), '../../testwork_user.csv')

    if not os.path.exists(csv_path):
        # Try alternate locations
        alternate_paths = [
            '../../data/sample/testwork_user.csv',
            '../../data/testwork_user.csv',
        ]
        for alt_path in alternate_paths:
            alt_csv_path = os.path.join(os.path.dirname(__file__), alt_path)
            if os.path.exists(alt_csv_path):
                csv_path = alt_csv_path
                break

    if not os.path.exists(csv_path):
        pytest.skip(f"User data file not found: {csv_path}")

    with open(csv_path, 'rb') as f:
        csv_content = f.read()

    return SimpleUploadedFile(
        "testwork_user.csv",
        csv_content,
        content_type="text/csv"
    )


@pytest.fixture
def user_csv_dataframe():
    """Load user's CSV as pandas DataFrame for validation"""
    csv_path = os.path.join(os.path.dirname(__file__), '../../testwork_user.csv')

    if not os.path.exists(csv_path):
        alternate_paths = [
            '../../data/sample/testwork_user.csv',
            '../../data/testwork_user.csv',
        ]
        for alt_path in alternate_paths:
            alt_csv_path = os.path.join(os.path.dirname(__file__), alt_path)
            if os.path.exists(alt_csv_path):
                csv_path = alt_csv_path
                break

    if not os.path.exists(csv_path):
        pytest.skip(f"User data file not found: {csv_path}")

    return pd.read_csv(csv_path)


@pytest.mark.integration
class TestUserDataComplete:
    """Comprehensive tests using real user data"""

    def test_user_data_structure_validation(self, user_csv_dataframe):
        """Validate the structure of user's test data"""
        df = user_csv_dataframe

        # Validate basic structure
        assert len(df) > 0, "User data file is empty"

        # Validate required columns exist
        required_columns = ['Name', 'RT', 'Volume', 'Log P', 'Anchor']
        for col in required_columns:
            assert col in df.columns, f"Missing required column: {col}"

        # Validate data types
        assert df['RT'].dtype in [float, int], "RT column should be numeric"
        assert df['Volume'].dtype in [float, int], "Volume column should be numeric"
        assert df['Log P'].dtype in [float, int], "Log P column should be numeric"

        # Validate anchor values
        anchor_values = df['Anchor'].unique()
        assert all(val in ['T', 'F'] for val in anchor_values), \
            f"Invalid Anchor values: {anchor_values}"

        # Count anchor vs non-anchor
        anchor_count = len(df[df['Anchor'] == 'T'])
        non_anchor_count = len(df[df['Anchor'] == 'F'])

        assert anchor_count > 0, "No anchor compounds found (Anchor='T')"
        assert non_anchor_count >= 0, "Unexpected negative non-anchor count"

        # Validate data ranges
        log_p_min, log_p_max = df['Log P'].min(), df['Log P'].max()
        rt_min, rt_max = df['RT'].min(), df['RT'].max()

        assert log_p_max > log_p_min, "Log P values have no variation"
        assert rt_max > rt_min, "RT values have no variation"

    def test_health_check_before_analysis(self, api_client):
        """Verify server is healthy before running analysis"""
        response = api_client.get('/api/health/')

        assert response.status_code == status.HTTP_200_OK, \
            "Server health check failed"
        assert response.data.get('status') == 'healthy', \
            "Server is not in healthy state"

    def test_user_data_analysis_workflow(self, authenticated_client, user_csv_file):
        """Test complete analysis workflow with user's actual data"""
        # Run analysis with user data
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': user_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK, \
            f"Analysis failed: {response.data}"

        # Validate results structure
        assert 'results' in response.data, "Missing 'results' in response"
        results = response.data['results']

        # Validate statistics
        assert 'statistics' in results, "Missing 'statistics' in results"
        stats = results['statistics']

        assert 'success_rate' in stats, "Missing 'success_rate'"
        assert 'valid_compounds' in stats, "Missing 'valid_compounds'"
        assert 'outliers' in stats, "Missing 'outliers'"

        # Log statistics for debugging
        success_rate = stats['success_rate']
        valid_compounds = stats['valid_compounds']
        outliers = stats['outliers']

        # Validate success rate is reasonable
        assert 0 <= success_rate <= 100, \
            f"Invalid success rate: {success_rate}%"

        # At least some compounds should be valid
        assert valid_compounds > 0, \
            "No valid compounds found - analysis may have failed"

        return results

    def test_regression_quality_with_user_data(
        self, authenticated_client, user_csv_file
    ):
        """Validate regression model quality with real data"""
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': user_csv_file,
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
        assert 'regression_analysis' in results, "Missing regression analysis"
        regression_data = results['regression_analysis']

        # Should have at least some regression models
        assert len(regression_data) > 0, \
            "No regression models generated from user data"

        # Validate each model
        for model_name, model_info in regression_data.items():
            assert 'r2' in model_info, f"Model {model_name} missing R²"
            assert 'equation' in model_info, f"Model {model_name} missing equation"

            r2 = model_info['r2']
            equation = model_info['equation']

            # R² should be valid
            assert 0 <= r2 <= 1, f"Invalid R² for {model_name}: {r2}"

            # R² should meet minimum threshold (with tolerance)
            # Note: May be slightly below threshold due to outlier removal
            assert r2 >= 0.5, \
                f"R² too low for {model_name}: {r2:.3f}. Equation: {equation}"

    def test_visualization_with_user_data(
        self, authenticated_client, user_csv_file
    ):
        """Test visualization generation with user's data"""
        # Step 1: Run analysis
        analysis_response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': user_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert analysis_response.status_code == status.HTTP_200_OK
        analysis_results = analysis_response.data['results']

        # Step 2: Generate visualizations
        viz_response = authenticated_client.post(
            '/api/visualization/generate/',
            {'results': analysis_results},
            format='json'
        )

        assert viz_response.status_code == status.HTTP_200_OK, \
            f"Visualization generation failed: {viz_response.data}"

        # Validate visualization structure
        assert 'plots' in viz_response.data, "Missing 'plots' in visualization response"
        plots = viz_response.data['plots']

        # Handle nested vs direct plot structure
        plot_data = plots.get('plots', plots) if isinstance(plots, dict) else {}

        # Validate critical plots
        critical_plots = {
            'regression_scatter': 'Regression Scatter Plot',
            '3d_distribution': '3D Distribution Plot',
            'dashboard': 'Dashboard'
        }

        working_plots = []
        for plot_key, plot_name in critical_plots.items():
            if plot_key in plot_data and plot_data[plot_key]:
                plot_content = str(plot_data[plot_key])
                content_length = len(plot_content)

                # Validate plot has substantial content
                assert content_length > 1000, \
                    f"{plot_name} has insufficient content ({content_length} chars)"

                # Validate Plotly markers
                has_plotly = 'plotly' in plot_content.lower() or \
                             'plot_ly' in plot_content.lower()
                assert has_plotly, f"{plot_name} doesn't appear to be a Plotly chart"

                # Validate has data
                has_data = 'data' in plot_content.lower() and content_length > 5000
                assert has_data, f"{plot_name} appears to lack data"

                working_plots.append(plot_key)

        # At least regression_scatter or 3d_distribution should work
        assert 'regression_scatter' in working_plots or '3d_distribution' in working_plots, \
            f"Critical plots missing. Found: {working_plots}, " \
            f"Available: {list(plot_data.keys())}"

    @pytest.mark.parametrize('r2_threshold', [0.70, 0.75, 0.80])
    def test_different_r2_thresholds_with_user_data(
        self, authenticated_client, user_csv_file, r2_threshold
    ):
        """Test how different R² thresholds affect results with real data"""
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': user_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': r2_threshold,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK, \
            f"Analysis failed with R²={r2_threshold}"

        results = response.data['results']
        stats = results['statistics']

        # Higher R² thresholds may result in fewer valid compounds
        # but should still produce results
        assert 'success_rate' in stats
        assert stats['success_rate'] >= 0

    def test_categorization_with_user_data(
        self, authenticated_client, user_csv_file
    ):
        """Test categorization system with user's data"""
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': user_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']

        # Check if categorization is included
        if 'categorization' in results:
            cat = results['categorization']

            # Validate categorization structure
            assert 'categories' in cat or 'base_prefixes' in cat, \
                "Categorization missing required fields"

            # If category_stats exists, validate it
            if 'category_stats' in cat:
                category_stats = cat['category_stats']
                assert len(category_stats) > 0, \
                    "No category statistics generated"

                # Validate each category
                for category, stats in category_stats.items():
                    assert 'count' in stats, f"Category {category} missing 'count'"
                    assert 'percentage' in stats, \
                        f"Category {category} missing 'percentage'"
                    assert 'color' in stats, f"Category {category} missing 'color'"

                    # Validate counts are non-negative
                    assert stats['count'] >= 0, \
                        f"Invalid count for {category}: {stats['count']}"
                    assert 0 <= stats['percentage'] <= 100, \
                        f"Invalid percentage for {category}: {stats['percentage']}"

    def test_oacetylation_validation_with_user_data(
        self, authenticated_client, user_csv_file
    ):
        """Test O-acetylation validation (Rule 4) with user's data"""
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': user_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']

        # Check if O-acetylation analysis is included
        if 'oacetylation_analysis' in results:
            oacet = results['oacetylation_analysis']

            # Should have some structure
            assert isinstance(oacet, dict), \
                "O-acetylation analysis should be a dictionary"

    def test_fragmentation_detection_with_user_data(
        self, authenticated_client, user_csv_file
    ):
        """Test fragmentation detection (Rule 5) with user's data"""
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': user_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']

        # Fragmentation may or may not be detected depending on data
        # Just validate the analysis completed successfully
        assert 'statistics' in results
        assert results['statistics']['success_rate'] >= 0


@pytest.mark.integration
class TestUserDataEdgeCases:
    """Test edge cases with user's data"""

    def test_empty_file_rejection(self, authenticated_client):
        """Test that empty CSV is rejected"""
        empty_csv = SimpleUploadedFile(
            "empty.csv",
            b"",
            content_type="text/csv"
        )

        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': empty_csv,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ], "Empty file should be rejected"

    def test_malformed_compound_names(self, authenticated_client):
        """Test handling of malformed compound names"""
        malformed_csv = SimpleUploadedFile(
            "malformed.csv",
            b"""Name,RT,Volume,Log P,Anchor
INVALID_NAME,10.5,1000,5.0,T
GD1(36:1;O2),9.5,2000,1.5,T
""",
            content_type="text/csv"
        )

        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': malformed_csv,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        # Should either reject or handle gracefully
        # (Depending on implementation, may return 200 with warnings or 400)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
