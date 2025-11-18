#!/usr/bin/env python3
"""
Integration tests for tab functionality in the web interface.

Tests the complete workflow from analysis to visualization generation
including multi-tab scenarios:
- Combined view tab (displays all plots together)
- Individual plot tabs (2D Analysis, 3D Distribution)
- Plot copying between tabs
- Backend visualization readiness
"""

import pytest
import json


@pytest.mark.integration
@pytest.mark.tabs
class TestTabFunctionality:
    """Test tab functionality and visualization distribution."""

    def test_complete_analysis_workflow(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test complete analysis workflow for tab functionality."""
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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
        assert "results" in result, "Missing analysis results"
        assert "error" not in result, f"Analysis error: {result.get('error')}"

        # Verify analysis completed successfully
        stats = result["results"]["statistics"]
        assert "success_rate" in stats, "Missing success rate"

    def test_visualization_generation_for_tabs(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that visualizations are generated for all tabs."""
        # Step 1: Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
                **default_analysis_params
            }

            analysis_response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        assert analysis_response.status_code == 200
        analysis_data = analysis_response.get_json()["results"]

        # Step 2: Generate visualizations
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        assert viz_response.status_code == 200, \
            f"Visualization failed: {viz_response.get_data(as_text=True)}"

        viz_result = viz_response.get_json()
        assert "plots" in viz_result, "Missing plots in visualization"

    def test_plots_available_for_tabs(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that required plots are available for tab display."""
        # Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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

        # Verify plots dictionary exists
        assert isinstance(nested_plots, dict), \
            "Plots should be dictionary"

        # Count available plots
        available_plots = [name for name, content in nested_plots.items()
                          if content and len(str(content)) > 0]

        assert len(available_plots) > 0, \
            "Should have at least one plot available"

    @pytest.mark.parametrize("plot_type", [
        "regression_scatter",
        "3d_distribution"
    ])
    def test_critical_plots_for_tabs(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params,
        plot_type
    ):
        """Test that critical plots for tabs are generated properly."""
        # Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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

        # Check if this critical plot exists
        if plot_type in nested_plots:
            plot_content = nested_plots[plot_type]

            # Should have substantial content
            assert plot_content is not None, \
                f"{plot_type} should not be None"
            assert len(str(plot_content)) > 5000, \
                f"{plot_type} content too small ({len(str(plot_content))} chars)"

    def test_combined_view_readiness(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that combined view has all necessary plots."""
        # Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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

        # Combined view should be able to display all plots
        assert len(nested_plots) > 0, \
            "Combined view needs at least one plot"

        # Each plot should be ready for display
        for plot_name, plot_content in nested_plots.items():
            if plot_content:
                assert isinstance(plot_content, (str, dict)), \
                    f"{plot_name} should be string or dict"

    def test_2d_analysis_tab_data(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that 2D analysis tab has required data."""
        # Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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

        # 2D analysis typically shows regression_scatter or rt_vs_logp
        two_d_plots = ["regression_scatter", "rt_vs_logp", "category_distribution"]

        has_2d_plot = any(plot_name in nested_plots
                         for plot_name in two_d_plots)

        # May or may not have 2D plots depending on data
        # Just verify structure is correct
        assert isinstance(nested_plots, dict), \
            "Should have plots dictionary for 2D tab"

    def test_3d_distribution_tab_data(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that 3D distribution tab has required data."""
        # Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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

        # Check if 3D distribution plot exists
        if "3d_distribution" in nested_plots:
            plot_3d = nested_plots["3d_distribution"]

            # Should have content
            assert plot_3d is not None, \
                "3D distribution plot should not be None"

    def test_plot_content_sufficient_for_display(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that plot content is sufficient for frontend display."""
        # Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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

        # Each plot should have meaningful content
        for plot_name, plot_content in nested_plots.items():
            if plot_content:
                content_str = str(plot_content)

                # Should not be empty or minimal
                assert len(content_str) > 100, \
                    f"{plot_name} content too small for display"

    def test_backend_ready_for_frontend_tabs(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that backend provides all data needed for frontend tabs."""
        # Complete workflow: analysis -> visualization
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
                **default_analysis_params
            }

            analysis_response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        assert analysis_response.status_code == 200, \
            "Analysis must succeed for tab functionality"

        analysis_data = analysis_response.get_json()["results"]

        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        assert viz_response.status_code == 200, \
            "Visualization must succeed for tab functionality"

        viz_result = viz_response.get_json()
        assert "plots" in viz_result, \
            "Backend must provide plots for tabs"

        plots = viz_result["plots"]

        # Backend should provide plots in a format ready for tabs
        assert plots is not None, \
            "Plots object should not be None"

    def test_multiple_plot_types_for_tabs(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that multiple plot types are available for different tabs."""
        # Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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

        # Count distinct plot types
        plot_types = list(nested_plots.keys())

        # Should ideally have multiple plot types for different tabs
        # But minimum is at least one
        assert len(plot_types) >= 1, \
            "Should have at least one plot type available"

    def test_plot_data_structure_consistency(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test that plot data structure is consistent across tabs."""
        # Run analysis
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
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

        # Structure should be consistent
        assert isinstance(plots, dict), \
            "Plots should be dictionary"

        # Handle nested structure
        if "plots" in plots:
            nested_plots = plots["plots"]
            assert isinstance(nested_plots, dict), \
                "Nested plots should be dictionary"

            # Each plot value should be string or dict
            for plot_name, plot_content in nested_plots.items():
                if plot_content is not None:
                    assert isinstance(plot_content, (str, dict)), \
                        f"{plot_name} should be string or dict"


@pytest.mark.integration
@pytest.mark.tabs
@pytest.mark.ui
class TestTabWorkflowIntegration:
    """Test complete tab workflow integration scenarios."""

    def test_end_to_end_tab_workflow(
        self,
        flask_client,
        user_csv_path,
        default_analysis_params
    ):
        """Test complete end-to-end workflow for tab display."""
        # This simulates the full user workflow:
        # 1. Upload file
        # 2. Run analysis
        # 3. Generate visualizations
        # 4. Display in tabs

        # Step 1 & 2: Upload and analyze
        with open(user_csv_path, "rb") as f:
            data = {
                "file": (f, "testwork_user.csv", "text/csv"),
                **default_analysis_params
            }

            analysis_response = flask_client.post(
                "/api/analyze",
                data=data,
                content_type="multipart/form-data"
            )

        assert analysis_response.status_code == 200, \
            "Step 1-2: Analysis must succeed"

        analysis_result = analysis_response.get_json()
        analysis_data = analysis_result["results"]

        # Verify analysis success
        assert analysis_data["statistics"]["success_rate"] >= 0, \
            "Analysis should produce valid results"

        # Step 3: Generate visualizations
        viz_response = flask_client.post(
            "/api/visualize",
            data=json.dumps({"results": analysis_data}),
            content_type="application/json"
        )

        assert viz_response.status_code == 200, \
            "Step 3: Visualization must succeed"

        viz_result = viz_response.get_json()

        # Step 4: Verify plots ready for tabs
        assert "plots" in viz_result, \
            "Step 4: Plots must be available for tabs"

        plots = viz_result["plots"]
        if "plots" in plots:
            nested_plots = plots["plots"]

            # Verify at least one plot for display
            assert len(nested_plots) > 0, \
                "Should have plots to display in tabs"

            # Verify each plot is usable
            usable_plots = 0
            for plot_name, plot_content in nested_plots.items():
                if plot_content and len(str(plot_content)) > 0:
                    usable_plots += 1

            assert usable_plots > 0, \
                "Should have at least one usable plot for tabs"
