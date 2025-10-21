"""
Web views for analysis app (template-based UI)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse

from .models import AnalysisSession


@login_required
def home(request):
    """Home page"""
    recent_sessions = AnalysisSession.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    context = {
        'recent_sessions': recent_sessions,
    }
    return render(request, 'analysis/home.html', context)


@login_required
def upload(request):
    """Upload CSV file for analysis"""
    if request.method == 'POST':
        from .serializers import AnalysisSessionCreateSerializer

        serializer = AnalysisSessionCreateSerializer(
            data=request.POST,
            files=request.FILES,
            context={'request': request}
        )

        if serializer.is_valid():
            session = serializer.save()
            messages.success(request, f'File uploaded successfully! Session ID: {session.id}')
            return redirect('analysis:session_detail', session_id=session.id)
        else:
            messages.error(request, f'Upload failed: {serializer.errors}')

    return render(request, 'analysis/upload.html')


@login_required
def history(request):
    """List all analysis sessions"""
    sessions = AnalysisSession.objects.filter(
        user=request.user
    ).order_by('-created_at')

    context = {
        'sessions': sessions,
    }
    return render(request, 'analysis/history.html', context)


@login_required
def session_detail(request, session_id):
    """View analysis session details"""
    session = get_object_or_404(
        AnalysisSession,
        id=session_id,
        user=request.user
    )

    context = {
        'session': session,
    }
    return render(request, 'analysis/session_detail.html', context)


@login_required
def session_analyze(request, session_id):
    """Trigger analysis (AJAX endpoint)"""
    session = get_object_or_404(
        AnalysisSession,
        id=session_id,
        user=request.user
    )

    if session.status in ['processing', 'completed']:
        return JsonResponse({
            'success': False,
            'error': f'Analysis is already {session.status}'
        }, status=400)

    # Import service
    from .services.analysis_service import AnalysisService
    from django.utils import timezone

    try:
        # Update status
        session.status = 'processing'
        session.started_at = timezone.now()
        session.save()

        # Run analysis
        service = AnalysisService()
        result = service.run_analysis(session)

        # Update status
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()

        return JsonResponse({
            'success': True,
            'message': 'Analysis completed successfully',
            'session_id': session.id,
            'redirect_url': f'/analysis/sessions/{session.id}/'
        })

    except Exception as e:
        # Mark as failed
        session.status = 'failed'
        session.error_message = str(e)
        session.completed_at = timezone.now()
        session.save()

        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def results(request, session_id):
    """View analysis results"""
    session = get_object_or_404(
        AnalysisSession,
        id=session_id,
        user=request.user
    )

    if session.status != 'completed':
        messages.warning(request, f'Analysis not completed (status: {session.status})')
        return redirect('analysis:session_detail', session_id=session.id)

    if not hasattr(session, 'result'):
        messages.error(request, 'No results found for this session')
        return redirect('analysis:session_detail', session_id=session.id)

    context = {
        'session': session,
        'result': session.result,
        'compounds': session.compounds.all(),
        'regression_models': session.regression_models.all(),
    }
    return render(request, 'analysis/results.html', context)
