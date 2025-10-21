"""
URL configuration for visualization app
"""
from django.urls import path
from . import views

app_name = 'visualization'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
]
