"""
Web Routes - Template serving and static pages
"""

import traceback

from flask import Blueprint, render_template

# Blueprint creation
web_bp = Blueprint('web', __name__)


@web_bp.route("/")
def index():
    """Main page - Working analyzer"""
    try:
        with open("working_analyzer.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Working analyzer file not found.", 404
    except Exception as e:
        print(f"Error serving working analyzer: {str(e)}")
        return f"Error loading working analyzer: {str(e)}", 500


@web_bp.route("/interactive")
def interactive_analyzer():
    """Interactive analyzer page"""
    try:
        return render_template("interactive_analyzer.html")
    except Exception as e:
        print(f"Template error for interactive: {str(e)}")
        return f"Template rendering error: {str(e)}", 500


@web_bp.route("/legacy")
def simple_analyzer():
    """Simple analyzer page (legacy)"""
    try:
        return render_template("analyzer.html")
    except Exception as e:
        print(f"Template error for legacy: {str(e)}")
        return f"Template rendering error: {str(e)}", 500


@web_bp.route("/integrated")
def integrated_view():
    """Integrated visualization page - combined 2D and 3D displays"""
    try:
        with open("integrated_visualization_english.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Integrated visualization file not found.", 404
    except Exception as e:
        print(f"Error serving integrated view: {str(e)}")
        return f"Error loading integrated view: {str(e)}", 500


@web_bp.route("/diagnostic")
def diagnostic_test():
    """Diagnostic test page for JavaScript debugging"""
    try:
        with open("diagnostic_test.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Diagnostic test file not found.", 404
    except Exception as e:
        print(f"Error serving diagnostic test: {str(e)}")
        return f"Error loading diagnostic test: {str(e)}", 500


@web_bp.route("/simple")
def simple_analyzer_working():
    """Simple working analyzer page"""
    try:
        with open("simple_analyzer.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Simple analyzer file not found.", 404
    except Exception as e:
        print(f"Error serving simple analyzer: {str(e)}")
        return f"Error loading simple analyzer: {str(e)}", 500


@web_bp.route("/working")
def working_analyzer():
    """Working analyzer with integrated features"""
    try:
        with open("working_analyzer.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Working analyzer file not found.", 404
    except Exception as e:
        print(f"Error serving working analyzer: {str(e)}")
        return f"Error loading working analyzer: {str(e)}", 500
