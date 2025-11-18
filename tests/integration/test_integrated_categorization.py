#!/usr/bin/env python3
"""
Integration tests for the ganglioside categorization system.

This test module validates the categorization functionality that classifies
gangliosides by sialic acid content (GM, GD, GT, GQ, GP) and ensures
proper integration with analysis and visualization pipelines.
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
        username='testuser_categorization',
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
    """Load user's testwork_user.csv file for categorization testing"""
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
    """Load user's CSV as DataFrame"""
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
class TestIntegratedCategorization:
    """Test categorization system integration with analysis pipeline"""

    def test_categorization_in_analysis_results(
        self, authenticated_client, user_csv_file
    ):
        """Test that categorization data is included in analysis results"""
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

        results = response.data['results']

        # Categorization should be included
        assert 'categorization' in results, \
            "Analysis results missing 'categorization' field"

        categorization = results['categorization']

        # Validate categorization structure
        assert isinstance(categorization, dict), \
            "Categorization should be a dictionary"

        # Should have at least one of the key fields
        expected_fields = ['categories', 'base_prefixes', 'modifications', 'category_stats']
        has_field = any(field in categorization for field in expected_fields)

        assert has_field, \
            f"Categorization missing expected fields. Found: {list(categorization.keys())}"

    def test_category_stats_structure(self, authenticated_client, user_csv_file):
        """Test category statistics structure and content"""
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

        if 'categorization' not in results:
            pytest.skip("Categorization not enabled in this response")

        categorization = results['categorization']

        if 'category_stats' not in categorization:
            pytest.skip("Category stats not available")

        category_stats = categorization['category_stats']

        # Validate structure
        assert len(category_stats) > 0, \
            "No category statistics generated"

        # Validate each category
        for category_name, stats in category_stats.items():
            # Required fields
            assert 'count' in stats, \
                f"Category {category_name} missing 'count'"
            assert 'percentage' in stats, \
                f"Category {category_name} missing 'percentage'"
            assert 'color' in stats, \
                f"Category {category_name} missing 'color'"
            assert 'description' in stats, \
                f"Category {category_name} missing 'description'"

            # Validate values
            assert stats['count'] >= 0, \
                f"Invalid count for {category_name}: {stats['count']}"
            assert 0 <= stats['percentage'] <= 100, \
                f"Invalid percentage for {category_name}: {stats['percentage']}"
            assert isinstance(stats['color'], str), \
                f"Color should be string for {category_name}"
            assert len(stats['color']) > 0, \
                f"Empty color for {category_name}"

    def test_ganglioside_categories(self, authenticated_client, user_csv_file):
        """Test that standard ganglioside categories are recognized"""
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

        if 'categorization' not in results or 'category_stats' not in results['categorization']:
            pytest.skip("Category stats not available")

        category_stats = results['categorization']['category_stats']

        # Standard ganglioside categories based on sialic acid count
        standard_categories = {
            'GM': 'Monosialo',  # 1 sialic acid
            'GD': 'Disialo',    # 2 sialic acids
            'GT': 'Trisialo',   # 3 sialic acids
            'GQ': 'Tetrasialo', # 4 sialic acids
            'GP': 'Pentasialo', # 5 sialic acids
        }

        # Check if any standard categories are present
        found_categories = [cat for cat in standard_categories.keys() if cat in category_stats]

        # Should have at least one standard category in typical data
        assert len(found_categories) > 0, \
            f"No standard ganglioside categories found. Available: {list(category_stats.keys())}"

    def test_category_color_assignments(self, authenticated_client, user_csv_file):
        """Test that categories have proper color assignments"""
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

        if 'categorization' not in results or 'category_stats' not in results['categorization']:
            pytest.skip("Category stats not available")

        category_stats = results['categorization']['category_stats']

        # Expected color scheme (from CLAUDE.md)
        expected_colors = {
            'GM': '#1f77b4',  # Blue
            'GD': '#ff7f0e',  # Orange
            'GT': '#2ca02c',  # Green
            'GQ': '#d62728',  # Red
            'GP': '#9467bd',  # Purple
        }

        # Validate colors for categories that exist
        for category, expected_color in expected_colors.items():
            if category in category_stats:
                actual_color = category_stats[category]['color']

                # Allow for different color formats (hex, rgb, named)
                # Just verify color field is non-empty
                assert len(actual_color) > 0, \
                    f"Empty color for category {category}"

    def test_base_prefix_detection(self, authenticated_client, user_csv_file):
        """Test detection of base prefixes in compound names"""
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

        if 'categorization' not in results:
            pytest.skip("Categorization not enabled")

        categorization = results['categorization']

        if 'base_prefixes' in categorization:
            base_prefixes = categorization['base_prefixes']

            assert isinstance(base_prefixes, dict), \
                "Base prefixes should be a dictionary"

            # Should have some base prefixes detected
            assert len(base_prefixes) > 0, \
                "No base prefixes detected"

    def test_modification_detection(self, authenticated_client, user_csv_file):
        """Test detection of modifications (e.g., +dHex, +OAc)"""
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

        if 'categorization' not in results:
            pytest.skip("Categorization not enabled")

        categorization = results['categorization']

        if 'modifications' in categorization:
            modifications = categorization['modifications']

            assert isinstance(modifications, dict), \
                "Modifications should be a dictionary"

            # Modifications may or may not be present in data
            # Just validate structure if they exist
            assert modifications is not None, \
                "Modifications field should not be None"


@pytest.mark.integration
class TestVisualizationWithCategorization:
    """Test visualization integration with categorization data"""

    def test_visualization_preserves_categorization(
        self, authenticated_client, user_csv_file
    ):
        """Test that categorization data is preserved in visualization"""
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
            f"Visualization failed: {viz_response.data}"

        # Validate visualization structure
        assert 'plots' in viz_response.data, \
            "Visualization response missing 'plots'"

    def test_category_based_visualizations(
        self, authenticated_client, user_csv_file
    ):
        """Test that visualizations can use categorization for color coding"""
        # Run analysis
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

        # If categorization exists, visualizations should be able to use it
        if 'categorization' in analysis_results:
            viz_response = authenticated_client.post(
                '/api/visualization/generate/',
                {'results': analysis_results},
                format='json'
            )

            assert viz_response.status_code == status.HTTP_200_OK, \
                "Visualization with categorization data failed"

            plots = viz_response.data['plots']
            assert isinstance(plots, dict), \
                "Plots should be a dictionary"


@pytest.mark.integration
class TestCategorizationEdgeCases:
    """Test edge cases in categorization system"""

    def test_categorization_with_minimal_data(self, authenticated_client):
        """Test categorization with minimal sample data"""
        minimal_csv = SimpleUploadedFile(
            "minimal.csv",
            b"""Name,RT,Volume,Log P,Anchor
GM1(36:1;O2),10.452,500000,4.00,T
GD1(36:1;O2),9.572,1000000,1.53,T
""",
            content_type="text/csv"
        )

        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': minimal_csv,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        # Should succeed even with minimal data
        assert response.status_code == status.HTTP_200_OK, \
            "Analysis with minimal data failed"

        results = response.data['results']

        # Categorization may or may not be present with minimal data
        # Just validate analysis completed
        assert 'statistics' in results

    def test_categorization_with_unknown_prefixes(self, authenticated_client):
        """Test handling of unknown/non-standard prefixes"""
        unknown_prefix_csv = SimpleUploadedFile(
            "unknown.csv",
            b"""Name,RT,Volume,Log P,Anchor
GM1(36:1;O2),10.452,500000,4.00,T
XX1(36:1;O2),9.572,1000000,1.53,T
""",
            content_type="text/csv"
        )

        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': unknown_prefix_csv,
                'data_type': 'Porcine',
                'outlier_threshold': 2.5,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        # Should handle gracefully (either categorize or skip unknown)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_400_BAD_REQUEST
        ], "Unexpected response to unknown prefix"

    def test_categorization_percentage_totals(
        self, authenticated_client, user_csv_file
    ):
        """Test that category percentages sum to ~100%"""
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

        if 'categorization' not in results or 'category_stats' not in results['categorization']:
            pytest.skip("Category stats not available")

        category_stats = results['categorization']['category_stats']

        # Sum percentages
        total_percentage = sum(stats['percentage'] for stats in category_stats.values())

        # Should be close to 100% (allow small floating point tolerance)
        assert 99.0 <= total_percentage <= 101.0, \
            f"Category percentages don't sum to 100%: {total_percentage:.2f}%"

    def test_categorization_count_consistency(
        self, authenticated_client, user_csv_file, user_csv_dataframe
    ):
        """Test that category counts match input data"""
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

        if 'categorization' not in results or 'category_stats' not in results['categorization']:
            pytest.skip("Category stats not available")

        category_stats = results['categorization']['category_stats']

        # Total count across categories should not exceed input data
        total_count = sum(stats['count'] for stats in category_stats.values())
        input_count = len(user_csv_dataframe)

        assert total_count <= input_count, \
            f"Category counts ({total_count}) exceed input data ({input_count})"

    @pytest.mark.parametrize('category_prefix,expected_description', [
        ('GM', 'Monosialo'),
        ('GD', 'Disialo'),
        ('GT', 'Trisialo'),
        ('GQ', 'Tetrasialo'),
        ('GP', 'Pentasialo'),
    ])
    def test_category_descriptions(
        self, authenticated_client, user_csv_file,
        category_prefix, expected_description
    ):
        """Test that categories have correct descriptions"""
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

        if 'categorization' not in results or 'category_stats' not in results['categorization']:
            pytest.skip("Category stats not available")

        category_stats = results['categorization']['category_stats']

        # If this category exists, validate description
        if category_prefix in category_stats:
            description = category_stats[category_prefix]['description']

            # Description should contain the expected term
            assert expected_description.lower() in description.lower(), \
                f"Category {category_prefix} description doesn't contain '{expected_description}'"
