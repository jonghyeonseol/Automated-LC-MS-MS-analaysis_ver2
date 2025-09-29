"""
Settings API Routes - Configuration management endpoints
"""

import traceback
from datetime import datetime

from flask import Blueprint, jsonify, request

# Global service instances
processor = None

# Blueprint creation
settings_bp = Blueprint('settings', __name__, url_prefix='/api')


def init_processor_service(ganglioside_processor):
    """Initialize processor service instance"""
    global processor
    processor = ganglioside_processor


@settings_bp.route("/settings", methods=["GET", "POST"])
def manage_settings():
    """Settings management - get or update analysis parameters"""
    try:
        if request.method == "GET":
            # Return current settings
            current_settings = processor.get_settings()
            return jsonify({
                "message": "Current settings retrieved",
                "settings": current_settings,
                "timestamp": datetime.now().isoformat()
            })

        elif request.method == "POST":
            # Update settings
            data = request.get_json()
            if not data:
                return jsonify({"error": "Settings data is required."}), 400

            # Extract settings with validation
            outlier_threshold = data.get("outlier_threshold")
            r2_threshold = data.get("r2_threshold")
            rt_tolerance = data.get("rt_tolerance")

            # Validate numeric values
            try:
                if outlier_threshold is not None:
                    outlier_threshold = float(outlier_threshold)
                    if outlier_threshold <= 0:
                        return jsonify({"error": "Outlier threshold must be positive"}), 400

                if r2_threshold is not None:
                    r2_threshold = float(r2_threshold)
                    if not (0 <= r2_threshold <= 1):
                        return jsonify({"error": "R² threshold must be between 0 and 1"}), 400

                if rt_tolerance is not None:
                    rt_tolerance = float(rt_tolerance)
                    if rt_tolerance < 0:
                        return jsonify({"error": "RT tolerance must be non-negative"}), 400

            except ValueError:
                return jsonify({"error": "Settings must be valid numbers"}), 400

            # Update processor settings
            processor.update_settings(
                outlier_threshold=outlier_threshold,
                r2_threshold=r2_threshold,
                rt_tolerance=rt_tolerance
            )

            # Return updated settings
            updated_settings = processor.get_settings()
            return jsonify({
                "message": "Settings updated successfully",
                "settings": updated_settings,
                "timestamp": datetime.now().isoformat()
            })

    except Exception as e:
        error_msg = f"Settings management error: {str(e)}"
        print(f"Settings error: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": error_msg}), 500


@settings_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for service status"""
    try:
        # Check if processor is available and working
        if processor is None:
            return jsonify({
                "status": "unhealthy",
                "error": "Processor service not initialized"
            }), 503

        # Get current settings as a basic health check
        settings = processor.get_settings()

        return jsonify({
            "status": "healthy",
            "message": "All services operational",
            "processor_status": "active",
            "current_settings": settings,
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.2"
        })

    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        print(f"Health check error: {error_msg}")
        return jsonify({
            "status": "unhealthy",
            "error": error_msg,
            "timestamp": datetime.now().isoformat()
        }), 500