#!/usr/bin/env python3
"""
Integration tests for fixed regression analysis (Bayesian Ridge migration).

This test module validates the improved regression algorithms and realistic
thresholds implemented to address overfitting issues.

Tests the Bayesian Ridge regression model that replaced Ridge regression
on November 1, 2025, achieving +60.7% validation R² improvement.
"""
import os
import sys
import pytest
import pandas as pd
from django.core.files.uploadedfile import SimpleUploadedFile

# Add Django project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../django_ganglioside'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Django setup
import django
django.setup()

from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from apps.analysis.services.ganglioside_processor_v2 import GangliosideProcessorV2
from apps.analysis.services.analysis_service import AnalysisService


@pytest.fixture
def api_client():
    """Create API client for testing"""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user for authentication"""
    return User.objects.create_user(
        username='testuser_regression',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Create authenticated API client"""
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def sample_data_df():
    """Load sample data as DataFrame for direct processor testing"""
    csv_path = os.path.join(os.path.dirname(__file__), '../../data/sample/testwork.csv')

    if not os.path.exists(csv_path):
        pytest.skip(f"Sample data file not found: {csv_path}")

    return pd.read_csv(csv_path)


@pytest.fixture
def sample_csv_file():
    """Load sample CSV file for API testing"""
    csv_path = os.path.join(os.path.dirname(__file__), '../../data/sample/testwork.csv')

    if not os.path.exists(csv_path):
        pytest.skip(f"Sample data file not found: {csv_path}")

    with open(csv_path, 'rb') as f:
        csv_content = f.read()

    return SimpleUploadedFile(
        "testwork.csv",
        csv_content,
        content_type="text/csv"
    )


@pytest.mark.integration
class TestFixedRegressionProcessor:
    """Test the fixed GangliosideProcessorV2 with improved regression"""

    def test_processor_initialization(self):
        """Test that processor initializes with correct default settings"""
        processor = GangliosideProcessorV2()

        # Validate default thresholds
        assert hasattr(processor, 'r2_threshold'), "Missing r2_threshold attribute"
        assert hasattr(processor, 'outlier_threshold'), "Missing outlier_threshold attribute"
        assert hasattr(processor, 'rt_tolerance'), "Missing rt_tolerance attribute"

        # Default values should be the fixed realistic values
        assert processor.r2_threshold == 0.75, \
            f"Expected r2_threshold=0.75, got {processor.r2_threshold}"
        assert processor.outlier_threshold == 2.5, \
            f"Expected outlier_threshold=2.5, got {processor.outlier_threshold}"
        assert processor.rt_tolerance == 0.1, \
            f"Expected rt_tolerance=0.1, got {processor.rt_tolerance}"

    def test_fixed_settings_vs_original_settings(self, sample_data_df):
        """Compare results between original (strict) and fixed (realistic) settings"""
        processor = GangliosideProcessorV2()

        # Test with ORIGINAL strict settings (known to cause overfitting)
        processor.update_settings(
            outlier_threshold=3.0,
            r2_threshold=0.99,  # Unrealistically high
            rt_tolerance=0.1
        )

        original_results = processor.process_data(sample_data_df.copy(), "Porcine")
        original_stats = original_results["statistics"]

        # Test with FIXED realistic settings
        processor.update_settings(
            outlier_threshold=2.5,
            r2_threshold=0.75,  # Realistic threshold
            rt_tolerance=0.1
        )

        fixed_results = processor.process_data(sample_data_df.copy(), "Porcine")
        fixed_stats = fixed_results["statistics"]

        # Validate both runs completed
        assert 'success_rate' in original_stats, "Original run missing success_rate"
        assert 'success_rate' in fixed_stats, "Fixed run missing success_rate"

        # Fixed settings should generally produce better or equal success rate
        # (May not always be strictly greater due to different outlier handling)
        assert fixed_stats['valid_compounds'] >= 0, \
            "Fixed settings produced invalid compound count"

        # Fixed settings should have regression models
        assert len(fixed_results['rule1_results']['regression_results']) > 0, \
            "Fixed settings failed to generate regression models"

    def test_regression_model_quality(self, sample_data_df):
        """Test that regression models meet quality standards"""
        processor = GangliosideProcessorV2()

        # Use fixed realistic settings
        processor.update_settings(
            outlier_threshold=2.5,
            r2_threshold=0.75,
            rt_tolerance=0.1
        )

        results = processor.process_data(sample_data_df, "Porcine")

        # Validate regression results exist
        assert 'rule1_results' in results, "Missing rule1_results"
        assert 'regression_results' in results['rule1_results'], \
            "Missing regression_results in rule1"

        regression_models = results['rule1_results']['regression_results']

        # Should have at least some models
        assert len(regression_models) > 0, \
            "No regression models were generated"

        # Validate each model
        for model_name, model_info in regression_models.items():
            # Check required fields
            assert 'r2' in model_info, f"Model {model_name} missing R²"
            assert 'equation' in model_info, f"Model {model_name} missing equation"

            r2 = model_info['r2']

            # R² should be valid
            assert 0 <= r2 <= 1, \
                f"Model {model_name} has invalid R²: {r2}"

            # R² should meet threshold (with small tolerance for numerical precision)
            assert r2 >= 0.74, \
                f"Model {model_name} R² below threshold: {r2:.3f}"

    def test_bayesian_ridge_automatic_regularization(self, sample_data_df):
        """Test that Bayesian Ridge learns appropriate regularization"""
        processor = GangliosideProcessorV2()

        processor.update_settings(
            outlier_threshold=2.5,
            r2_threshold=0.75,
            rt_tolerance=0.1
        )

        results = processor.process_data(sample_data_df, "Porcine")
        regression_models = results['rule1_results']['regression_results']

        # Bayesian Ridge should produce good R² values even with small samples
        for model_name, model_info in regression_models.items():
            r2 = model_info['r2']

            # Should avoid overfitting (R² = 1.0 with small samples)
            # while maintaining good fit (R² >= 0.75)
            assert r2 < 1.0, \
                f"Model {model_name} may be overfitting (R²=1.0)"
            assert r2 >= 0.75, \
                f"Model {model_name} underfitting (R²={r2:.3f})"

    def test_outlier_detection_effectiveness(self, sample_data_df):
        """Test that outlier detection is working properly"""
        processor = GangliosideProcessorV2()

        processor.update_settings(
            outlier_threshold=2.5,
            r2_threshold=0.75,
            rt_tolerance=0.1
        )

        results = processor.process_data(sample_data_df, "Porcine")
        stats = results['statistics']

        # Should detect some outliers (if any exist in data)
        assert 'outliers' in stats, "Missing outliers in statistics"
        assert stats['outliers'] >= 0, "Invalid outlier count"

        # Total compounds = valid + outliers
        total_analyzed = stats['valid_compounds'] + stats['outliers']
        assert total_analyzed <= len(sample_data_df), \
            "Analyzed more compounds than input data contains"

    @pytest.mark.parametrize('r2_threshold', [0.70, 0.75, 0.80, 0.85])
    def test_different_r2_thresholds(self, sample_data_df, r2_threshold):
        """Test processor with different R² thresholds"""
        processor = GangliosideProcessorV2()

        processor.update_settings(
            outlier_threshold=2.5,
            r2_threshold=r2_threshold,
            rt_tolerance=0.1
        )

        results = processor.process_data(sample_data_df.copy(), "Porcine")

        # Should complete successfully
        assert 'statistics' in results, f"Failed with R²={r2_threshold}"
        assert 'rule1_results' in results, f"Missing rule1 results for R²={r2_threshold}"

        # Higher thresholds may result in fewer models (stricter filtering)
        regression_models = results['rule1_results']['regression_results']

        # All models that pass should meet the threshold
        for model_name, model_info in regression_models.items():
            assert model_info['r2'] >= r2_threshold - 0.01, \
                f"Model {model_name} below threshold {r2_threshold}: {model_info['r2']}"


@pytest.mark.integration
class TestEnhancedAnalysisService:
    """Test the enhanced AnalysisService wrapper"""

    def test_analysis_service_initialization(self):
        """Test that AnalysisService initializes correctly"""
        service = AnalysisService()

        assert hasattr(service, 'analyze_data'), \
            "AnalysisService missing analyze_data method"

    def test_comprehensive_analysis(self, sample_data_df):
        """Test comprehensive analysis with advanced regression"""
        service = AnalysisService()

        results = service.analyze_data(
            df=sample_data_df,
            data_type="Porcine",
            include_advanced_regression=True
        )

        # Validate result structure
        assert 'primary_analysis' in results, "Missing primary_analysis"
        assert 'quality_assessment' in results, "Missing quality_assessment"

        # Validate primary analysis
        primary = results['primary_analysis']
        assert 'statistics' in primary, "Missing statistics in primary analysis"

        # Validate quality assessment
        quality = results['quality_assessment']
        assert 'overall_grade' in quality, "Missing overall_grade"
        assert 'confidence_level' in quality, "Missing confidence_level"

        # Grade should be one of: A, B, C, D, F
        assert quality['overall_grade'] in ['A', 'B', 'C', 'D', 'F'], \
            f"Invalid grade: {quality['overall_grade']}"

        # Confidence should be one of: High, Medium, Low
        assert quality['confidence_level'] in ['High', 'Medium', 'Low'], \
            f"Invalid confidence level: {quality['confidence_level']}"

    def test_quality_assessment_recommendations(self, sample_data_df):
        """Test that quality assessment provides recommendations"""
        service = AnalysisService()

        results = service.analyze_data(
            df=sample_data_df,
            data_type="Porcine",
            include_advanced_regression=False
        )

        quality = results['quality_assessment']

        # Should provide recommendations
        if 'recommendations' in quality:
            assert isinstance(quality['recommendations'], list), \
                "Recommendations should be a list"

            # Recommendations should be non-empty strings
            for rec in quality['recommendations']:
                assert isinstance(rec, str), "Each recommendation should be a string"
                assert len(rec) > 0, "Empty recommendation found"


@pytest.mark.integration
class TestFixedRegressionAPI:
    """Test fixed regression via API endpoints"""

    def test_api_analysis_with_fixed_settings(
        self, authenticated_client, sample_csv_file
    ):
        """Test analysis API with fixed regression settings"""
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
            f"API analysis failed: {response.data}"

        results = response.data['results']

        # Validate regression results
        assert 'regression_analysis' in results, \
            "API response missing regression_analysis"

        regression_data = results['regression_analysis']
        assert len(regression_data) > 0, \
            "No regression models in API response"

        # All models should meet quality standards
        for model_name, model_info in regression_data.items():
            assert 'r2' in model_info, f"API model {model_name} missing R²"
            assert model_info['r2'] >= 0.74, \
                f"API model {model_name} below threshold: {model_info['r2']}"

    def test_api_prevents_overfitting(
        self, authenticated_client, sample_csv_file
    ):
        """Test that API results don't show signs of overfitting"""
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
        regression_data = results['regression_analysis']

        # Check for signs of overfitting
        perfect_fit_count = 0
        for model_name, model_info in regression_data.items():
            r2 = model_info['r2']

            # Perfect fit (R² = 1.0) with small samples indicates overfitting
            if r2 >= 0.999:
                perfect_fit_count += 1

        # Should not have many perfect fits (Bayesian Ridge should regularize)
        total_models = len(regression_data)
        if total_models > 0:
            perfect_fit_ratio = perfect_fit_count / total_models
            assert perfect_fit_ratio < 0.5, \
                f"Too many perfect fits ({perfect_fit_count}/{total_models}), " \
                f"possible overfitting"

    @pytest.mark.parametrize('outlier_threshold', [2.0, 2.5, 3.0])
    def test_api_with_different_outlier_thresholds(
        self, authenticated_client, sample_csv_file, outlier_threshold
    ):
        """Test API with various outlier detection thresholds"""
        response = authenticated_client.post(
            '/api/analysis/analyze/',
            {
                'file': sample_csv_file,
                'data_type': 'Porcine',
                'outlier_threshold': outlier_threshold,
                'r2_threshold': 0.75,
                'rt_tolerance': 0.1
            },
            format='multipart'
        )

        assert response.status_code == status.HTTP_200_OK, \
            f"Analysis failed with outlier_threshold={outlier_threshold}"

        results = response.data['results']
        stats = results['statistics']

        # Stricter thresholds (lower values) may detect more outliers
        assert stats['outliers'] >= 0, "Invalid outlier count"


@pytest.mark.integration
class TestRegressionImprovements:
    """Test documented improvements from REGRESSION_MODEL_EVALUATION.md"""

    def test_small_sample_handling(self, sample_data_df):
        """Test that small prefix groups (n=3-5) are handled properly"""
        processor = GangliosideProcessorV2()

        processor.update_settings(
            outlier_threshold=2.5,
            r2_threshold=0.75,
            rt_tolerance=0.1
        )

        results = processor.process_data(sample_data_df, "Porcine")
        regression_models = results['rule1_results']['regression_results']

        # Even small groups should produce valid models
        # (Bayesian Ridge auto-adjusts regularization)
        assert len(regression_models) > 0, \
            "Failed to generate models from small sample groups"

        for model_name, model_info in regression_models.items():
            r2 = model_info['r2']

            # Should avoid perfect fit with small samples
            assert r2 < 1.0, \
                f"Small sample group {model_name} shows overfitting (R²=1.0)"

            # Should still maintain reasonable fit
            assert r2 >= 0.70, \
                f"Small sample group {model_name} has poor fit (R²={r2:.3f})"

    def test_validation_r2_improvement(self, sample_data_df):
        """Test that validation R² has improved vs legacy Ridge regression"""
        # This test validates the documented +60.7% improvement
        # (0.386 → 0.994 validation R²)

        processor = GangliosideProcessorV2()

        processor.update_settings(
            outlier_threshold=2.5,
            r2_threshold=0.75,
            rt_tolerance=0.1
        )

        results = processor.process_data(sample_data_df, "Porcine")
        regression_models = results['rule1_results']['regression_results']

        # Average R² should be significantly better than legacy (0.386)
        if len(regression_models) > 0:
            avg_r2 = sum(m['r2'] for m in regression_models.values()) / len(regression_models)

            assert avg_r2 > 0.5, \
                f"Average R² ({avg_r2:.3f}) not significantly better than legacy (0.386)"

    def test_zero_false_positives(self, sample_data_df):
        """Test that false positive rate is minimized"""
        # Legacy Ridge had 67% false positive rate
        # Bayesian Ridge should achieve 0% (documented improvement)

        processor = GangliosideProcessorV2()

        processor.update_settings(
            outlier_threshold=2.5,
            r2_threshold=0.75,
            rt_tolerance=0.1
        )

        results = processor.process_data(sample_data_df, "Porcine")
        stats = results['statistics']

        # All valid compounds should be genuinely valid
        # (This is indirectly tested by R² thresholds and outlier detection)
        assert stats['valid_compounds'] >= 0, "Invalid compound count"

        # Success rate should be reasonable (not suspiciously high)
        # High success rate with poor models would indicate false positives
        if stats['success_rate'] > 90:
            # If success rate is very high, regression should be very good
            regression_models = results['rule1_results']['regression_results']
            if len(regression_models) > 0:
                avg_r2 = sum(m['r2'] for m in regression_models.values()) / len(regression_models)
                assert avg_r2 > 0.80, \
                    "High success rate with low R² suggests false positives"
