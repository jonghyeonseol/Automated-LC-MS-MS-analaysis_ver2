"""
Visualization API Routes - Chart and plot generation endpoints
"""

import traceback
from datetime import datetime

import pandas as pd
import numpy as np
from flask import Blueprint, jsonify, request

# Global service instances
visualization_service = None

# Blueprint creation
visualization_bp = Blueprint('visualization', __name__, url_prefix='/api')


def init_visualization_service(vis_service):
    """Initialize visualization service instance"""
    global visualization_service
    visualization_service = vis_service


def convert_to_serializable(obj):
    """Convert NumPy/pandas objects to JSON serializable format"""
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    return obj


@visualization_bp.route("/visualize", methods=["POST"])
def create_visualizations():
    """Create all visualizations from analysis results"""
    try:
        data = request.get_json()
        if not data or "results" not in data:
            return jsonify({"error": "Analysis results data is required."}), 400

        results = data["results"]

        # Generate all visualizations
        plots = visualization_service.create_all_plots(results)

        return jsonify({
            "message": "Visualizations created successfully",
            "plots": plots,
            "creation_time": datetime.now().isoformat()
        })

    except Exception as e:
        error_msg = f"Visualization creation error: {str(e)}"
        print(f"Visualization error: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500


@visualization_bp.route("/visualize-3d", methods=["POST"])
def create_3d_visualization():
    """Dedicated endpoint for 3D distribution visualization"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request data is required."}), 400

        # Check for file data
        if "file_data" in data:
            # Process CSV data directly
            df = pd.DataFrame(data["file_data"])
        elif "results" in data:
            # Use existing analysis results
            results = data["results"]
            df = None
        else:
            return jsonify({"error": "Either file_data or results must be provided."}), 400

        # Get settings
        settings = data.get("settings", {})
        outlier_threshold = float(settings.get("outlier_threshold", 3.0))
        r2_threshold = float(settings.get("r2_threshold", 0.99))
        rt_tolerance = float(settings.get("rt_tolerance", 0.1))

        # If we have raw file data, we need to process it first
        if df is not None:
            # This would need access to the processor, which we should inject
            # For now, return error for this case
            return jsonify({
                "error": "Direct file processing not implemented in visualization endpoint"
            }), 501

        # Generate 3D visualization from results
        plot_3d = visualization_service._create_3d_distribution_plot(results)

        return jsonify({
            "message": "3D visualization created successfully",
            "plot_3d": plot_3d,
            "settings": {
                "outlier_threshold": outlier_threshold,
                "r2_threshold": r2_threshold,
                "rt_tolerance": rt_tolerance,
            },
            "creation_time": datetime.now().isoformat()
        })

    except Exception as e:
        error_msg = f"3D visualization error: {str(e)}"
        print(f"3D Visualization error: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500