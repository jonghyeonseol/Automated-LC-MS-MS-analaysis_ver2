"""
Core app URLs - Health check endpoints
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.health_check, name='health-check'),
]
