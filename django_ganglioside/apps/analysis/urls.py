"""
URL configuration for analysis app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AnalysisSessionViewSet, CompoundViewSet, RegressionModelViewSet
from . import views_web

app_name = 'analysis'

# DRF Router for API endpoints
router = DefaultRouter()
router.register(r'api/sessions', AnalysisSessionViewSet, basename='api-session')
router.register(r'api/compounds', CompoundViewSet, basename='api-compound')
router.register(r'api/regression-models', RegressionModelViewSet, basename='api-regression-model')

urlpatterns = [
    # Web UI endpoints
    path('', views_web.home, name='home'),
    path('upload/', views_web.upload, name='upload'),
    path('history/', views_web.history, name='history'),
    path('sessions/<int:session_id>/', views_web.session_detail, name='session_detail'),
    path('sessions/<int:session_id>/analyze/', views_web.session_analyze, name='session_analyze'),
    path('sessions/<int:session_id>/results/', views_web.results, name='results'),

    # API endpoints
    path('', include(router.urls)),
]
