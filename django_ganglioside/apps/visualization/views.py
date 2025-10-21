"""
Views for visualization app
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def dashboard(request):
    """Visualization dashboard"""
    return render(request, 'visualization/dashboard.html')
