"""
Fixed Analysis API Routes - Enhanced data analysis endpoints with improved regression
"""

import io
import traceback
from datetime import datetime
from typing import Any, Dict

import pandas as pd
import numpy as np
from flask import Blueprint, jsonify, request, g, Response


# Blueprint creation
analysis_bp = Blueprint('analysis', __name__)


def convert_to_serializable(obj: Any) -> Any:
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
    elif hasattr(obj, 'isoformat'):  # datetime objects
        return obj.isoformat()
    return obj


@analysis_bp.route("/analyze", methods=["POST"])
def analyze_data_enhanced():
    """
    Enhanced data analysis with fixed regression algorithms
    """
    try:
        print("🚀 Enhanced analysis request received")

        # Validate request
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        # Get analysis parameters
        data_type = request.form.get('data_type', 'Porcine')
        outlier_threshold = float(request.form.get('outlier_threshold', 2.5))  # Lowered default
        r2_threshold = float(request.form.get('r2_threshold', 0.75))  # Lowered default
        rt_tolerance = float(request.form.get('rt_tolerance', 0.1))

        print(f"📊 Analysis parameters: outlier={outlier_threshold}, r2={r2_threshold}, rt={rt_tolerance}")

        # Read and validate CSV file
        try:
            df = pd.read_csv(file)
            print(f"📄 CSV loaded: {len(df)} compounds")
        except Exception as e:
            return jsonify({"error": f"Failed to read CSV file: {str(e)}"}), 400

        # Validate required columns
        required_columns = ['Name', 'RT', 'Log P']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({
                "error": f"Missing required columns: {missing_columns}",
                "available_columns": list(df.columns),
                "required_columns": required_columns
            }), 400

        # Update analysis service settings
        try:
            g.analysis_service.update_settings(
                outlier_threshold=outlier_threshold,
                r2_threshold=r2_threshold,
                rt_tolerance=rt_tolerance
            )
        except Exception as e:
            print(f"⚠️ Settings update warning: {e}")

        # Perform enhanced analysis
        print("🔬 Starting enhanced analysis...")
        analysis_results = g.analysis_service.analyze_data(
            df=df,
            data_type=data_type,
            include_advanced_regression=True
        )

        # Extract key statistics for response
        primary_stats = analysis_results.get("primary_analysis", {}).get("statistics", {})
        quality_assessment = analysis_results.get("quality_assessment", {})

        # Prepare response with enhanced information
        response_data = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "results": {
                "statistics": {
                    "total_compounds": primary_stats.get("total_compounds", 0),
                    "valid_compounds": primary_stats.get("valid_compounds", 0),
                    "outliers": primary_stats.get("outliers", 0),
                    "success_rate": primary_stats.get("success_rate", 0.0),
                    "rule_breakdown": primary_stats.get("rule_breakdown", {}),
                },
                "quality_assessment": {
                    "overall_grade": quality_assessment.get("overall_grade", "Unknown"),
                    "confidence_level": quality_assessment.get("confidence_level", "Unknown"),
                    "regression_quality": quality_assessment.get("regression_analysis_quality", "Not performed"),
                    "recommendations": quality_assessment.get("recommendations", [])
                },
                "analysis_details": {
                    "data_type": data_type,
                    "settings_used": analysis_results.get("analysis_metadata", {}).get("settings_used", {}),
                    "enhanced_features": analysis_results.get("analysis_metadata", {}).get("includes_advanced_regression", False),
                    "processing_timestamp": analysis_results.get("analysis_metadata", {}).get("analysis_timestamp")
                },
                "compounds": {
                    "valid": analysis_results.get("primary_analysis", {}).get("rule1_results", {}).get("valid_compounds", []),
                    "outliers": analysis_results.get("primary_analysis", {}).get("rule1_results", {}).get("outliers", []),
                    "regression_models": analysis_results.get("primary_analysis", {}).get("rule1_results", {}).get("regression_results", {})
                }
            },
            "enhanced_analysis": {
                "available": analysis_results.get("enhanced_regression") is not None,
                "regression_summary": analysis_results.get("enhanced_regression", {}).get("data_summary", {}) if analysis_results.get("enhanced_regression") else None
            }
        }

        # Convert to serializable format
        response_data = convert_to_serializable(response_data)

        print(f"✅ Enhanced analysis completed: {primary_stats.get('success_rate', 0):.1f}% success rate")

        return jsonify(response_data), 200

    except Exception as e:
        print(f"❌ Enhanced analysis error: {str(e)}")
        print("Traceback:", traceback.format_exc())

        return jsonify({
            "error": "Analysis failed",
            "details": str(e),
            "timestamp": datetime.now().isoformat(),
            "status": "error"
        }), 500


@analysis_bp.route("/upload", methods=["POST"])
def upload_csv_enhanced():
    """Enhanced CSV upload with better validation"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '' or not file.filename.endswith('.csv'):
            return jsonify({"error": "Invalid file. Please upload a CSV file."}), 400

        # Read and validate CSV
        try:
            df = pd.read_csv(file)
        except Exception as e:
            return jsonify({"error": f"Failed to read CSV file: {str(e)}"}), 400

        # Enhanced validation
        validation_result = _validate_csv_structure(df)
        if not validation_result["valid"]:
            return jsonify({
                "error": "CSV validation failed",
                "details": validation_result["errors"],
                "suggestions": validation_result["suggestions"]
            }), 400

        # Return file info and preview
        response_data = {
            "status": "success",
            "file_info": {
                "filename": file.filename,
                "rows": len(df),
                "columns": list(df.columns),
                "size_kb": len(file.read()) // 1024
            },
            "preview": {
                "first_5_rows": df.head().to_dict('records'),
                "data_types": df.dtypes.astype(str).to_dict(),
                "missing_values": df.isnull().sum().to_dict()
            },
            "validation": validation_result,
            "timestamp": datetime.now().isoformat()
        }

        file.seek(0)  # Reset file pointer

        return jsonify(convert_to_serializable(response_data)), 200

    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return jsonify({
            "error": "Upload failed",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


def _validate_csv_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """Enhanced CSV structure validation"""
    errors = []
    suggestions = []
    warnings = []

    # Required columns check
    required_columns = ['Name', 'RT', 'Log P']
    missing_required = [col for col in required_columns if col not in df.columns]

    if missing_required:
        errors.append(f"Missing required columns: {missing_required}")
        suggestions.append("Ensure your CSV has columns: Name, RT, Log P")

    # Optional columns check
    optional_columns = ['Volume', 'Anchor']
    missing_optional = [col for col in optional_columns if col not in df.columns]

    if missing_optional:
        warnings.append(f"Optional columns missing: {missing_optional}")
        if 'Anchor' in missing_optional:
            suggestions.append("Consider adding 'Anchor' column (T/F) for better regression analysis")

    # Data validation
    if not errors:  # Only check data if structure is valid
        if df.empty:
            errors.append("CSV file is empty")
        else:
            # Check for missing values in critical columns
            for col in ['Name', 'RT', 'Log P']:
                if col in df.columns:
                    missing_count = df[col].isnull().sum()
                    if missing_count > 0:
                        warnings.append(f"Column '{col}' has {missing_count} missing values")

            # Check data types
            if 'RT' in df.columns:
                try:
                    pd.to_numeric(df['RT'], errors='raise')
                except (ValueError, TypeError):
                    errors.append("RT column contains non-numeric values")

            if 'Log P' in df.columns:
                try:
                    pd.to_numeric(df['Log P'], errors='raise')
                except (ValueError, TypeError):
                    errors.append("Log P column contains non-numeric values")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "column_analysis": {
            "required_present": [col for col in required_columns if col in df.columns],
            "optional_present": [col for col in optional_columns if col in df.columns],
            "extra_columns": [col for col in df.columns if col not in required_columns + optional_columns]
        }
    }


@analysis_bp.route("/settings", methods=["GET", "POST"])
def analysis_settings():
    """Get or update analysis settings"""
    try:
        if request.method == "GET":
            # Return current settings
            current_settings = g.analysis_service.get_current_settings()
            return jsonify({
                "status": "success",
                "settings": current_settings,
                "timestamp": datetime.now().isoformat()
            }), 200

        elif request.method == "POST":
            # Update settings
            data = request.get_json()

            outlier_threshold = data.get('outlier_threshold')
            r2_threshold = data.get('r2_threshold')
            rt_tolerance = data.get('rt_tolerance')

            updated_settings = g.analysis_service.update_settings(
                outlier_threshold=outlier_threshold,
                r2_threshold=r2_threshold,
                rt_tolerance=rt_tolerance
            )

            return jsonify({
                "status": "success",
                "message": "Settings updated successfully",
                "settings": updated_settings,
                "timestamp": datetime.now().isoformat()
            }), 200

    except Exception as e:
        print(f"❌ Settings error: {str(e)}")
        return jsonify({
            "error": "Settings operation failed",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@analysis_bp.route("/export/<format>", methods=["GET"])
def export_results(format: str):
    """Export analysis results in different formats"""
    try:
        # This would typically use stored results from a session or database
        # For now, return a placeholder
        if format not in ['csv', 'xlsx', 'json']:
            return jsonify({"error": "Unsupported format. Use: csv, xlsx, json"}), 400

        return jsonify({
            "message": f"Export in {format} format - Feature coming soon",
            "available_formats": ["csv", "xlsx", "json"],
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Export failed",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500