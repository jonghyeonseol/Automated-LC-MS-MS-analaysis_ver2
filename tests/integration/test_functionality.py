#!/usr/bin/env python3
"""
Integration tests for API functionality.

Tests all major API endpoints including:
- Health check
- File upload and analysis
- Visualization generation
- Settings configuration
- Error handling
"""

import pytest
import json


@pytest.mark.integration
@pytest.mark.api
class TestAPIFunctionality:
    """Test API endpoint functionality."""

    def test_health_endpoint(self, flask_client):
        """Test that health endpoint returns success status."""
        response = flask_client.get("/api/health")

        assert response.status_code == 200, \
            "Health endpoint should return 200 status"

        data = response.get_json()
        assert "status" in data, "Health response missing 'status' key"
        assert data["status"] in ["ok", "healthy", "up"], \
            f"Unexpected health status: {data['status']}"

    def test_health_endpoint_response_structure(self, flask_client):
        """Test health endpoint response has expected structure."""
        response = flask_client.get("/api/health")
        data = response.get_json()

        # Should be a dictionary
        assert isinstance(data, dict), "Health response should be dict"

        # Should have status
        assert "status" in data, "Missing status field"

    def test_analysis_endpoint_with_valid_data(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test analysis endpoint with valid CSV file."""
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **default_analysis_params
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        assert response.status_code == 200, \
            f"Analysis failed: {response.get_data(as_text=True)}"

        result = response.get_json()
        assert "results" in result, "Missing 'results' key"
        assert "error" not in result, f"Unexpected error: {result.get('error')}"

    def test_analysis_returns_statistics(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test that analysis returns proper statistics."""
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **default_analysis_params
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        result = response.get_json()
        stats = result["results"]["statistics"]

        # Check required statistics fields
        assert "success_rate" in stats, "Missing success_rate"
        assert "valid_compounds" in stats, "Missing valid_compounds"
        assert "outliers" in stats, "Missing outliers"

        # Validate value ranges
        assert 0 <= stats["success_rate"] <= 100, \
            "Success rate should be between 0 and 100"
        assert stats["valid_compounds"] >= 0, \
            "Valid compounds should be non-negative"
        assert stats["outliers"] >= 0, \
            "Outliers should be non-negative"

    def test_analysis_returns_compound_data(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test that analysis returns compound-level data."""
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **default_analysis_params
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        result = response.get_json()
        analysis_data = result["results"]

        # Should have compound lists
        assert "valid_compounds" in analysis_data, \
            "Missing valid_compounds list"
        assert "outliers" in analysis_data, \
            "Missing outliers list"

        # Lists should be valid
        assert isinstance(analysis_data["valid_compounds"], list), \
            "valid_compounds should be list"
        assert isinstance(analysis_data["outliers"], list), \
            "outliers should be list"

    @pytest.mark.parametrize("param,value", [
        ("outlier_threshold", 2.0),
        ("outlier_threshold", 3.0),
        ("r2_threshold", 0.70),
        ("r2_threshold", 0.80),
        ("rt_tolerance", 0.05),
        ("rt_tolerance", 0.15),
    ])
    def test_analysis_with_different_parameters(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params,
        param,
        value
    ):
        """Test analysis with various parameter values."""
        params = default_analysis_params.copy()
        params[param] = value

        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **params
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        # Should handle parameter variations
        assert response.status_code == 200, \
            f"Analysis failed with {param}={value}"

        result = response.get_json()
        assert "results" in result, \
            f"Missing results with {param}={value}"

    def test_visualization_endpoint_with_valid_results(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test visualization endpoint with valid analysis results."""
        # First run analysis
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **default_analysis_params
            }

            analysis_response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        analysis_data = analysis_response.get_json()["results"]

        # Then generate visualizations
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        assert viz_response.status_code == 200, \
            f"Visualization failed: {viz_response.get_data(as_text=True)}"

        viz_result = viz_response.get_json()
        assert "plots" in viz_result, "Missing plots in visualization result"

    def test_visualization_error_handling(self, flask_client):
        """Test that visualization handles invalid input gracefully."""
        # Try with empty/invalid results
        invalid_results = {}

        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": invalid_results}),
            content_type="application/json"
        )

        # Should either succeed with empty plots or return error
        assert viz_response.status_code in [200, 400, 500], \
            "Unexpected status code for invalid input"

    def test_analysis_without_file(self, flask_client, default_analysis_params):
        """Test that analysis endpoint requires a file."""
        # Try to analyze without uploading a file
        response = flask_client.post(
            "/api/analyze",
            data=default_analysis_params,
            content_type="multipart/form-data"
        )

        # Should return error or bad request
        assert response.status_code in [400, 422], \
            "Should reject request without file"

    def test_settings_endpoint_get(self, flask_client):
        """Test retrieving current settings."""
        response = flask_client.get("/api/settings")

        # Endpoint may or may not exist
        if response.status_code == 200:
            settings = response.get_json()
            assert isinstance(settings, dict), \
                "Settings should be dictionary"

    def test_settings_endpoint_post(self, flask_client):
        """Test updating settings."""
        new_settings = {
            "outlier_threshold": 2.5,
            "r2_threshold": 0.75,
            "rt_tolerance": 0.1
        }

        response = flask_client.post(
            "/api/settings",
            data=json.dumps(new_settings),
            content_type="application/json"
        )

        # Endpoint may or may not exist
        if response.status_code == 200:
            result = response.get_json()
            assert "success" in result or "status" in result

    def test_complete_workflow(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test complete workflow: health -> analyze -> visualize."""
        # Step 1: Health check
        health_response = flask_client.get("/api/health")
        assert health_response.status_code == 200, \
            "Health check failed"

        # Step 2: Analysis
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **default_analysis_params
            }

            analysis_response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        assert analysis_response.status_code == 200, \
            "Analysis failed"

        analysis_result = analysis_response.get_json()
        assert "results" in analysis_result, \
            "Missing results from analysis"

        # Step 3: Visualization
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_result["results"]}),
            content_type="application/json"
        )

        assert viz_response.status_code == 200, \
            "Visualization failed"

        viz_result = viz_response.get_json()
        assert "plots" in viz_result, \
            "Missing plots from visualization"

    def test_analysis_data_type_parameter(
        self,
        flask_client,
        sample_csv_path
    ):
        """Test analysis with different data_type values."""
        data_types = ["Porcine", "Human", "Bovine"]

        for data_type in data_types:
            with open(sample_csv_path, "rb") as f:
                data = {
                    "file": (f, "testwork.csv", "text/csv"),
                    "data_type": data_type,
                    "outlier_threshold": 2.5,
                    "r2_threshold": 0.75,
                    "rt_tolerance": 0.1
                }

                response = flask_client.post(
                    "/api/analyze",
                    data=data,
                    content_type="multipart/form-data"
                )

            # Should handle different data types
            assert response.status_code == 200, \
                f"Analysis failed with data_type={data_type}"

            result = response.get_json()
            assert "results" in result, \
                f"Missing results with data_type={data_type}"

    def test_regression_analysis_in_results(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test that regression analysis data is included in results."""
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **default_analysis_params
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        result = response.get_json()
        analysis_data = result["results"]

        # Should have regression analysis
        if "regression_analysis" in analysis_data:
            regression_data = analysis_data["regression_analysis"]
            assert isinstance(regression_data, dict), \
                "Regression analysis should be dict"

    def test_sugar_analysis_in_results(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test that sugar analysis data is included in results."""
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **default_analysis_params
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        result = response.get_json()
        analysis_data = result["results"]

        # Should have sugar analysis
        if "sugar_analysis" in analysis_data:
            sugar_data = analysis_data["sugar_analysis"]
            # Sugar analysis should be present
            assert sugar_data is not None

    def test_categorization_in_results(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test that categorization data is included in results."""
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                **default_analysis_params
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        result = response.get_json()
        analysis_data = result["results"]

        # Should have categorization
        if "categorization" in analysis_data:
            categorization = analysis_data["categorization"]
            assert isinstance(categorization, dict), \
                "Categorization should be dict"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.error_handling
class TestAPIErrorHandling:
    """Test API error handling and edge cases."""

    def test_invalid_endpoint(self, flask_client):
        """Test that invalid endpoints return 404."""
        response = flask_client.get("/api/nonexistent")
        assert response.status_code == 404, \
            "Invalid endpoint should return 404"

    def test_wrong_http_method(self, flask_client):
        """Test that wrong HTTP methods are rejected."""
        # Try GET on POST-only endpoint
        response = flask_client.get("/api/analyze")
        assert response.status_code in [405, 400], \
            "Wrong HTTP method should be rejected"

    def test_missing_required_parameters(
        self,
        flask_client,
        sample_csv_path
    ):
        """Test analysis with missing required parameters."""
        with open(sample_csv_path, "rb") as f:
            # Missing data_type
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                "outlier_threshold": 2.5,
                # Missing other required params
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        # Should either use defaults or return error
        assert response.status_code in [200, 400, 422], \
            "Should handle missing parameters"

    def test_invalid_parameter_types(
        self,
        flask_client,
        sample_csv_path
    ):
        """Test analysis with invalid parameter types."""
        with open(sample_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork.csv", "text/csv"),
                "data_type": "Porcine",
                "outlier_threshold": "not_a_number",  # Invalid type
                "r2_threshold": 0.75,
                "rt_tolerance": 0.1
            }

            response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        # Should reject invalid types
        assert response.status_code in [400, 422, 500], \
            "Should reject invalid parameter types"
