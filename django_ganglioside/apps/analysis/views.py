"""
Django REST Framework ViewSets for analysis app
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

from .models import AnalysisSession, Compound, AnalysisResult, RegressionModel
from .serializers import (
    AnalysisSessionSerializer,
    AnalysisSessionListSerializer,
    AnalysisSessionCreateSerializer,
    CompoundSerializer,
    CompoundListSerializer,
    AnalysisResultSerializer,
    RegressionModelSerializer,
)


class AnalysisSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AnalysisSession

    Endpoints:
    - GET /api/analysis/sessions/ - List all sessions
    - POST /api/analysis/sessions/ - Create new session with file upload
    - GET /api/analysis/sessions/{id}/ - Retrieve session details
    - PUT/PATCH /api/analysis/sessions/{id}/ - Update session
    - DELETE /api/analysis/sessions/{id}/ - Delete session
    - POST /api/analysis/sessions/{id}/analyze/ - Trigger analysis
    - GET /api/analysis/sessions/{id}/results/ - Get analysis results
    - GET /api/analysis/sessions/{id}/status/ - Get analysis status

    Rate Limiting:
    - Standard CRUD: 1000/hour (user throttle)
    - File uploads: 30/hour (upload throttle scope)
    - Analysis operations: 50/hour (analysis throttle scope)
    """
    queryset = AnalysisSession.objects.all()
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'analysis'

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return AnalysisSessionListSerializer
        elif self.action == 'create':
            return AnalysisSessionCreateSerializer
        return AnalysisSessionSerializer

    def get_queryset(self):
        """Filter sessions by current user"""
        return AnalysisSession.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """
        Trigger analysis for a session (synchronous mode)
        POST /api/analysis/sessions/{id}/analyze/

        Query params:
        - async: bool (optional) - If true, queue as background task
        """
        session = self.get_object()

        # Check if already running or completed
        if session.status in ['processing', 'completed']:
            return Response(
                {'error': f'Analysis is already {session.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if async mode requested
        use_async = request.query_params.get('async', 'false').lower() == 'true'

        if use_async:
            # Queue as background task
            from .tasks import run_analysis_async

            task = run_analysis_async.delay(session.id)

            # Update status to pending
            session.status = 'pending'
            session.save(update_fields=['status'])

            return Response({
                'message': 'Analysis queued successfully',
                'session_id': session.id,
                'task_id': task.id,
                'status': 'pending',
                'async': True,
            }, status=status.HTTP_202_ACCEPTED)

        else:
            # Run synchronously (original behavior)
            from .services.analysis_service import AnalysisService

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

                return Response({
                    'message': 'Analysis completed successfully',
                    'session_id': session.id,
                    'status': session.status,
                    'results': AnalysisResultSerializer(result).data,
                    'async': False,
                }, status=status.HTTP_200_OK)

            except (ValueError, KeyError, TypeError) as e:
                # Mark as failed - data validation or processing errors
                logger.error(f"Analysis validation error for session {session.id}: {e}")
                session.status = 'failed'
                session.error_message = str(e)
                session.completed_at = timezone.now()
                session.save()

                return Response(
                    {'error': f'Analysis failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            except Exception as e:
                # Unexpected errors - log with full traceback
                logger.exception(f"Unexpected error during analysis for session {session.id}: {e}")
                session.status = 'failed'
                session.error_message = f"Unexpected error: {str(e)}"
                session.completed_at = timezone.now()
                session.save()

                return Response(
                    {'error': f'Analysis failed unexpectedly: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

    @action(detail=True, methods=['post'], url_path='analyze-async')
    def analyze_async(self, request, pk=None):
        """
        Trigger analysis for a session as background task
        POST /api/analysis/sessions/{id}/analyze-async/

        Returns task ID for monitoring progress
        """
        session = self.get_object()

        # Check if already running or completed
        if session.status in ['processing', 'completed']:
            return Response(
                {'error': f'Analysis is already {session.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from .tasks import run_analysis_async

        try:
            # Queue background task
            task = run_analysis_async.delay(session.id)

            return Response({
                'message': 'Analysis queued successfully',
                'session_id': session.id,
                'task_id': task.id,
                'status': 'queued',
                'monitor_url': f'/api/analysis/sessions/{session.id}/task-status/?task_id={task.id}',
            }, status=status.HTTP_202_ACCEPTED)

        except ImportError as e:
            # Celery not available
            logger.error(f"Celery not available: {e}")
            return Response(
                {'error': 'Background task system unavailable'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            # Unexpected errors queuing task
            logger.exception(f"Failed to queue analysis for session {session.id}: {e}")
            return Response(
                {'error': f'Failed to queue analysis: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='task-status')
    def task_status(self, request, pk=None):
        """
        Check status of background task
        GET /api/analysis/sessions/{id}/task-status/?task_id=<task_id>
        """
        from celery.result import AsyncResult

        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response(
                {'error': 'task_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task_result = AsyncResult(task_id)

        response_data = {
            'task_id': task_id,
            'state': task_result.state,
            'ready': task_result.ready(),
        }

        if task_result.state == 'PENDING':
            response_data['status'] = 'Task is waiting to be executed'

        elif task_result.state == 'PROGRESS':
            response_data['status'] = 'Task is currently running'
            response_data['progress'] = task_result.info

        elif task_result.state == 'SUCCESS':
            response_data['status'] = 'Task completed successfully'
            response_data['result'] = task_result.result

        elif task_result.state == 'FAILURE':
            response_data['status'] = 'Task failed'
            response_data['error'] = str(task_result.info)

        else:
            response_data['status'] = task_result.state

        return Response(response_data)

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """
        Get analysis results
        GET /api/analysis/sessions/{id}/results/
        """
        session = self.get_object()

        if session.status != 'completed':
            return Response(
                {'error': f'Analysis not completed (status: {session.status})'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not hasattr(session, 'result'):
            return Response(
                {'error': 'No results found for this session'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(AnalysisResultSerializer(session.result).data)

    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """
        Get analysis status
        GET /api/analysis/sessions/{id}/status/
        """
        session = self.get_object()

        return Response({
            'session_id': session.id,
            'status': session.status,
            'started_at': session.started_at,
            'completed_at': session.completed_at,
            'duration': session.duration,
            'error_message': session.error_message if session.status == 'failed' else None
        })

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """
        Export results as CSV
        GET /api/analysis/sessions/{id}/export/?format=csv
        """
        session = self.get_object()

        if session.status != 'completed':
            return Response(
                {'error': 'Analysis not completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Import here to avoid circular dependency
        from .services.export_service import ExportService

        export_format = request.query_params.get('format', 'csv')
        service = ExportService()

        try:
            file_response = service.export_session(session, export_format)
            return file_response
        except ValueError as e:
            # Invalid export format or data
            logger.error(f"Export validation error for session {session.id}: {e}")
            return Response(
                {'error': f'Invalid export format or data: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except (IOError, OSError) as e:
            # File system errors
            logger.error(f"Export file system error for session {session.id}: {e}")
            return Response(
                {'error': f'File system error during export: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected export error for session {session.id}: {e}")
            return Response(
                {'error': f'Export failed unexpectedly: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CompoundViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Compound (read-only)

    Endpoints:
    - GET /api/analysis/compounds/ - List all compounds (filtered by session)
    - GET /api/analysis/compounds/{id}/ - Retrieve compound details

    Rate Limiting:
    - 200/hour (compound throttle scope)
    """
    queryset = Compound.objects.all()
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'compound'

    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'list':
            return CompoundListSerializer
        return CompoundSerializer

    def get_queryset(self):
        """Filter compounds by query parameters"""
        queryset = Compound.objects.filter(session__user=self.request.user)

        # Filter by session
        session_id = self.request.query_params.get('session_id', None)
        if session_id is not None:
            queryset = queryset.filter(session_id=session_id)

        # Filter by category
        category = self.request.query_params.get('category', None)
        if category is not None:
            queryset = queryset.filter(category=category)

        # Filter by status
        compound_status = self.request.query_params.get('status', None)
        if compound_status is not None:
            queryset = queryset.filter(status=compound_status)

        # Filter by anchor
        is_anchor = self.request.query_params.get('is_anchor', None)
        if is_anchor is not None:
            queryset = queryset.filter(is_anchor=is_anchor.lower() == 'true')

        return queryset.order_by('session', 'name')


class RegressionModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for RegressionModel (read-only)

    Endpoints:
    - GET /api/analysis/regression-models/ - List all models
    - GET /api/analysis/regression-models/{id}/ - Retrieve model details

    Rate Limiting:
    - 100/hour (regression throttle scope)
    """
    queryset = RegressionModel.objects.all()
    serializer_class = RegressionModelSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'regression'

    def get_queryset(self):
        """Filter models by session"""
        queryset = RegressionModel.objects.filter(session__user=self.request.user)

        session_id = self.request.query_params.get('session_id', None)
        if session_id is not None:
            queryset = queryset.filter(session_id=session_id)

        return queryset.order_by('session', 'prefix_group')
