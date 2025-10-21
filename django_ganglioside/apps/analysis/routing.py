"""
WebSocket URL Routing for Analysis App

Defines WebSocket URL patterns for real-time communication.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/analysis/(?P<session_id>\d+)/$', consumers.AnalysisProgressConsumer.as_asgi()),
]
