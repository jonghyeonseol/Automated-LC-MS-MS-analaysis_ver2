"""
API Routes Initialization - Flask Blueprints
"""

from .analysis import analysis_bp
from .visualization import visualization_bp
from .settings import settings_bp
from .web import web_bp

__all__ = ["analysis_bp", "visualization_bp", "settings_bp", "web_bp"]
