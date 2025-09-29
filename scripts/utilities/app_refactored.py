"""
Ganglioside Analyzer - Refactored Flask Main Application
LC-MS/MS data automated analysis web service with modular architecture
"""

from flask import Flask
from flask_cors import CORS

# Service imports
try:
    from backend.services.data_processor import \
        GangliosideDataProcessor as GangliosideProcessor
    from backend.services.regression_analyzer import RegressionAnalyzer
    from backend.services.visualization_service import VisualizationService
    print("✅ Real analysis modules loaded successfully")
except ImportError as e:
    print(f"⚠️ Analysis module load failed: {e}")
    print("Using dummy modules...")
    from backend.services.dummy import \
        DummyGangliosideDataProcessor as GangliosideProcessor
    from backend.services.dummy import \
        DummyVisualizationService as VisualizationService

    # Dummy RegressionAnalyzer class
    class RegressionAnalyzer:
        def __init__(self):
            print("🔬 Dummy Regression Analyzer initialized")

        def analyze(self, data):
            return {"message": "Dummy regression analysis result"}


# Blueprint imports
from backend.api.routes.analysis import analysis_bp, init_services
from backend.api.routes.visualization import visualization_bp, init_visualization_service
from backend.api.routes.settings import settings_bp, init_processor_service
from backend.api.routes.web import web_bp


def create_app():
    """Flask application factory"""

    # Flask app initialization
    app = Flask(
        __name__,
        template_folder="backend/templates",
        static_folder="backend/static"
    )
    CORS(app)  # CORS settings

    # Configuration
    app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
    app.config['SECRET_KEY'] = 'ganglioside-analyzer-v2.0.2'
    app.config['DEBUG'] = True

    # Initialize services
    print("🔧 Initializing analysis services...")
    processor = GangliosideProcessor()
    regression_analyzer = RegressionAnalyzer()
    visualization_service = VisualizationService()

    # Inject services into route modules
    init_services(processor, regression_analyzer, visualization_service)
    init_visualization_service(visualization_service)
    init_processor_service(processor)

    print("✅ Services initialized successfully")

    # Register blueprints
    print("📋 Registering blueprints...")
    app.register_blueprint(web_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(visualization_bp)
    app.register_blueprint(settings_bp)
    print("✅ All blueprints registered")

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Endpoint not found", "status": 404}, 404

    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error", "status": 500}, 500

    @app.errorhandler(413)
    def too_large(error):
        return {"error": "File too large (max 100MB)", "status": 413}, 413

    print("🧬 Ganglioside Analyzer Flask server initialization complete")
    return app


def main():
    """Main execution function"""
    app = create_app()

    print("🚀 Starting Ganglioside Analyzer Flask server")
    print("🌐 Available at http://localhost:5001")

    try:
        app.run(
            host="0.0.0.0",  # Listen on all interfaces
            port=5001,       # Use port 5001 (5000 conflicts with AirPlay on macOS)
            debug=True,      # Enable debug mode
            threaded=True    # Handle multiple requests
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")


if __name__ == "__main__":
    main()