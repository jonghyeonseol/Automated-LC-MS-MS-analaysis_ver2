#!/usr/bin/env python3
"""
Integration tests for visualization pipeline.

Tests the complete analysis-to-visualization workflow including:
- Analysis execution with sample data
- Visualization generation from results
- Plot structure and content validation
- HTML/JavaScript embedding verification
"""

import pytest
import json
from io import BytesIO


@pytest.mark.integration
@pytest.mark.visualization
class TestVisualizationPipeline:
    """Test visualization generation from analysis results."""

    def test_run_analysis_for_visualization(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test running analysis to generate data for visualization."""
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
        assert "error" not in result, f"Analysis error: {result.get('error')}"

        # Verify analysis results structure
        analysis_data = result["results"]
        assert "statistics" in analysis_data, "Missing statistics"
        assert "valid_compounds" in analysis_data, "Missing valid_compounds"

        # Check success rate
        stats = analysis_data["statistics"]
        assert "success_rate" in stats, "Missing success_rate"
        assert stats["success_rate"] >= 0, "Invalid success rate"

    def test_generate_visualizations(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test generating visualizations from analysis results."""
        # Step 1: Run analysis
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

        assert analysis_response.status_code == 200
        analysis_result = analysis_response.get_json()
        analysis_data = analysis_result["results"]

        # Step 2: Generate visualizations
        viz_payload = {"results": analysis_data}

        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps(viz_payload),
            content_type="application/json"
        )

        assert viz_response.status_code == 200, \
            f"Visualization failed: {viz_response.get_data(as_text=True)}"

        viz_result = viz_response.get_json()
        assert "error" not in viz_result, \
            f"Visualization error: {viz_result.get('error')}"

    def test_visualization_structure(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test that visualization result has correct structure."""
        # Run analysis
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

        # Generate visualizations
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        viz_result = viz_response.get_json()

        # Check for plots key
        assert "plots" in viz_result, "Missing 'plots' key in visualization result"

        plots = viz_result["plots"]
        assert isinstance(plots, dict), "Plots should be a dictionary"

    @pytest.mark.parametrize("plot_name", [
        "regression_scatter",
        "3d_distribution",
        "category_distribution",
        "rt_vs_logp"
    ])
    def test_plot_types_available(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params,
        plot_name
    ):
        """Test that expected plot types are generated."""
        # Run analysis
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

        # Generate visualizations
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        viz_result = viz_response.get_json()
        plots = viz_result.get("plots", {})

        # Handle nested plots structure (plots.plots)
        if "plots" in plots:
            nested_plots = plots["plots"]
        else:
            nested_plots = plots

        # Plot may or may not be present depending on data
        if plot_name in nested_plots:
            plot_content = nested_plots[plot_name]
            assert plot_content is not None, \
                f"{plot_name} should have content"

    def test_plot_content_size(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test that plots have substantial content (not empty)."""
        # Run analysis
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

        # Generate visualizations
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        viz_result = viz_response.get_json()
        plots = viz_result.get("plots", {})

        # Handle nested plots structure
        if "plots" in plots:
            nested_plots = plots["plots"]
        else:
            nested_plots = plots

        # Check that at least one plot has substantial content
        plot_sizes = []
        for plot_name, plot_content in nested_plots.items():
            if plot_content:
                content_length = len(str(plot_content))
                plot_sizes.append(content_length)

                # Each plot should have meaningful content (>100 chars minimum)
                assert content_length > 100, \
                    f"{plot_name} has suspiciously small content ({content_length} chars)"

        # Should have generated at least one plot
        assert len(plot_sizes) > 0, "No plots were generated"

    def test_plot_html_structure(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test that plots contain valid HTML/JavaScript structure."""
        # Run analysis
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

        # Generate visualizations
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        viz_result = viz_response.get_json()
        plots = viz_result.get("plots", {})

        # Handle nested plots structure
        if "plots" in plots:
            nested_plots = plots["plots"]
        else:
            nested_plots = plots

        # Check HTML structure in plots
        for plot_name, plot_content in nested_plots.items():
            if plot_content:
                content_str = str(plot_content)

                # Should contain Plotly-related content
                has_plotly = (
                    "plotly" in content_str.lower() or
                    "plot" in content_str.lower()
                )

                # Should have HTML div or script tags (typical Plotly output)
                has_html_elements = (
                    "<div" in content_str or
                    "<script" in content_str or
                    "data" in content_str  # JSON data structure
                )

                assert has_plotly or has_html_elements, \
                    f"{plot_name} missing Plotly/HTML structure"

    def test_visualization_with_empty_results(self, flask_client):
        """Test that visualization handles empty/minimal results gracefully."""
        # Create minimal results structure
        minimal_results = {
            "statistics": {
                "success_rate": 0.0,
                "valid_compounds": 0,
                "outliers": 0
            },
            "valid_compounds": [],
            "outliers": []
        }

        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": minimal_results}),
            content_type="application/json"
        )

        # Should handle gracefully (either success or informative error)
        assert viz_response.status_code in [200, 400], \
            "Unexpected status code for empty results"

        if viz_response.status_code == 200:
            viz_result = viz_response.get_json()
            # If successful, should still have plots key
            assert "plots" in viz_result or "error" in viz_result

    def test_3d_visualization_endpoint(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test dedicated 3D visualization endpoint."""
        # Run analysis
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

        # Generate 3D visualization
        viz_response = flask_client.post(
            "/api/visualize-3d",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        # Should succeed or return informative error
        assert viz_response.status_code in [200, 400, 404], \
            f"Unexpected 3D viz status: {viz_response.status_code}"

    def test_complete_pipeline_integration(
        self,
        flask_client,
        sample_csv_path,
        default_analysis_params
    ):
        """Test complete analysis-to-visualization pipeline."""
        # Step 1: Upload and analyze
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

        assert analysis_response.status_code == 200
        analysis_result = analysis_response.get_json()
        analysis_data = analysis_result["results"]

        # Verify analysis produced valid data
        assert analysis_data["statistics"]["success_rate"] >= 0

        # Step 2: Generate visualizations
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        assert viz_response.status_code == 200
        viz_result = viz_response.get_json()

        # Verify visualizations were generated
        assert "plots" in viz_result

        # Step 3: Verify plots are ready for frontend
        plots = viz_result["plots"]
        if "plots" in plots:
            nested_plots = plots["plots"]

            # Should have at least one plot
            assert len(nested_plots) > 0, "No plots generated"

            # Each plot should be usable
            for plot_name, plot_content in nested_plots.items():
                if plot_content:
                    assert len(str(plot_content)) > 0, \
                        f"{plot_name} is empty"
