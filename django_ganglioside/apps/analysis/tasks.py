"""
Celery Tasks for Asynchronous Analysis Processing

This module defines background tasks for running ganglioside analysis,
notifications, and periodic cleanup operations.
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.utils import timezone
from datetime import timedelta

logger = get_task_logger(__name__)


@shared_task(bind=True, name='analysis.run_analysis_async')
def run_analysis_async(self, session_id):
    """
    Run ganglioside analysis asynchronously in background.

    Args:
        self: Celery task instance (bound)
        session_id: ID of AnalysisSession to process

    Returns:
        dict: Analysis result summary
    """
    from apps.analysis.models import AnalysisSession
    from apps.analysis.services.analysis_service import AnalysisService

    logger.info(f"Starting async analysis for session {session_id}")

    try:
        # Get session
        session = AnalysisSession.objects.get(id=session_id)

        # Update status to processing
        session.status = 'processing'
        session.started_at = timezone.now()
        session.save(update_fields=['status', 'started_at'])

        # Update task progress
        self.update_state(
            state='PROGRESS',
            meta={'current': 10, 'total': 100, 'status': 'Initializing...'}
        )

        # Run analysis
        service = AnalysisService()
        result = service.run_analysis(session)

        # Update session status
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save(update_fields=['status', 'completed_at'])

        logger.info(f"Completed analysis for session {session_id}")

        return {
            'session_id': session_id,
            'status': 'completed',
            'total_compounds': result.total_compounds,
            'valid_compounds': result.valid_compounds,
            'success_rate': float(result.success_rate),
        }

    except AnalysisSession.DoesNotExist:
        logger.error(f"Session {session_id} not found")
        raise

    except (ValueError, KeyError, TypeError) as e:
        # Data validation or processing errors
        logger.error(f"Analysis validation error for session {session_id}: {str(e)}")

        # Update session status to failed
        try:
            session = AnalysisSession.objects.get(id=session_id)
            session.status = 'failed'
            session.error_message = f"Validation error: {str(e)}"
            session.completed_at = timezone.now()
            session.save(update_fields=['status', 'error_message', 'completed_at'])
        except AnalysisSession.DoesNotExist:
            logger.warning(f"Session {session_id} not found when updating status to failed")
        except Exception as db_error:
            logger.exception(f"Database error updating session {session_id} status: {db_error}")

        raise

    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected error during analysis for session {session_id}: {str(e)}")

        # Update session status to failed
        try:
            session = AnalysisSession.objects.get(id=session_id)
            session.status = 'failed'
            session.error_message = f"Unexpected error: {str(e)}"
            session.completed_at = timezone.now()
            session.save(update_fields=['status', 'error_message', 'completed_at'])
        except AnalysisSession.DoesNotExist:
            logger.warning(f"Session {session_id} not found when updating status to failed")
        except Exception as db_error:
            logger.exception(f"Database error updating session {session_id} status: {db_error}")

        raise


@shared_task(name='analysis.cleanup_old_sessions')
def cleanup_old_sessions(days=30):
    """
    Periodic task to clean up old analysis sessions.

    Args:
        days: Number of days to retain sessions (default: 30)

    Returns:
        dict: Cleanup summary
    """
    from apps.analysis.models import AnalysisSession

    logger.info(f"Starting cleanup of sessions older than {days} days")

    cutoff_date = timezone.now() - timedelta(days=days)

    # Find old sessions
    old_sessions = AnalysisSession.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed']
    )

    count = old_sessions.count()

    if count > 0:
        # Delete associated files
        for session in old_sessions:
            if session.uploaded_file:
                try:
                    session.uploaded_file.delete(save=False)
                    logger.debug(f"Deleted file for session {session.id}")
                except (IOError, OSError) as e:
                    # File system errors during deletion
                    logger.warning(f"File system error deleting file for session {session.id}: {e}")
                except Exception as e:
                    # Other unexpected errors
                    logger.exception(f"Unexpected error deleting file for session {session.id}: {e}")

        # Delete sessions (cascade will delete related objects)
        deleted_count, _ = old_sessions.delete()

        logger.info(f"Cleaned up {deleted_count} old sessions")
    else:
        logger.info("No old sessions to clean up")

    return {
        'cutoff_date': cutoff_date.isoformat(),
        'sessions_deleted': count,
    }


@shared_task(name='analysis.send_analysis_notification')
def send_analysis_notification(session_id, email):
    """
    Send email notification when analysis is complete.

    Args:
        session_id: ID of completed AnalysisSession
        email: Email address to notify

    Returns:
        dict: Notification status

    Note:
        This is a stub implementation. Email backend needs to be configured
        in Django settings for actual email sending.
    """
    from apps.analysis.models import AnalysisSession
    from django.core.mail import send_mail
    from django.conf import settings

    logger.info(f"Sending notification for session {session_id} to {email}")

    try:
        session = AnalysisSession.objects.get(id=session_id)

        subject = f"Analysis Complete: {session.name}"
        message = f"""
Your ganglioside analysis has been completed.

Session: {session.name}
Status: {session.get_status_display()}
Total Compounds: {session.result.total_compounds if hasattr(session, 'result') else 'N/A'}
Success Rate: {session.result.success_rate if hasattr(session, 'result') else 'N/A'}%

View results at: {settings.BASE_URL}/analysis/sessions/{session_id}/

Best regards,
Ganglioside Analysis Platform
        """

        # Send email (requires email backend configuration)
        # send_mail(
        #     subject,
        #     message,
        #     settings.DEFAULT_FROM_EMAIL,
        #     [email],
        #     fail_silently=False,
        # )

        logger.info(f"Notification sent successfully (stub)")

        return {
            'session_id': session_id,
            'email': email,
            'status': 'sent (stub)',
        }

    except AnalysisSession.DoesNotExist:
        logger.error(f"Session {session_id} not found for notification")
        raise

    except (ValueError, KeyError) as e:
        # Data formatting errors
        logger.error(f"Invalid notification data for session {session_id}: {e}")
        raise

    except Exception as e:
        # Unexpected errors (email sending, etc.)
        logger.exception(f"Unexpected error sending notification for session {session_id}: {e}")
        raise


@shared_task(name='analysis.export_results_async')
def export_results_async(session_id, export_format='csv'):
    """
    Export analysis results to file asynchronously.

    Args:
        session_id: ID of AnalysisSession
        export_format: Export format ('csv', 'excel', 'json')

    Returns:
        dict: Export summary with file path
    """
    from apps.analysis.models import AnalysisSession, Compound
    import pandas as pd
    from pathlib import Path

    logger.info(f"Exporting results for session {session_id} as {export_format}")

    try:
        session = AnalysisSession.objects.get(id=session_id)

        if session.status != 'completed':
            raise ValueError(f"Session {session_id} is not completed")

        # Get all compounds
        compounds = Compound.objects.filter(session=session).values(
            'name', 'rt', 'volume', 'log_p', 'is_anchor',
            'prefix', 'suffix', 'category', 'status',
            'predicted_rt', 'residual', 'standardized_residual'
        )

        df = pd.DataFrame(compounds)

        # Create export directory
        export_dir = Path('media/exports')
        export_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"session_{session_id}_export_{timestamp}"

        # Export based on format
        if export_format == 'csv':
            filepath = export_dir / f"{filename}.csv"
            df.to_csv(filepath, index=False)

        elif export_format == 'excel':
            filepath = export_dir / f"{filename}.xlsx"
            df.to_excel(filepath, index=False, engine='openpyxl')

        elif export_format == 'json':
            filepath = export_dir / f"{filename}.json"
            df.to_json(filepath, orient='records', indent=2)

        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        logger.info(f"Export complete: {filepath}")

        return {
            'session_id': session_id,
            'format': export_format,
            'filepath': str(filepath),
            'rows': len(df),
        }

    except AnalysisSession.DoesNotExist:
        logger.error(f"Session {session_id} not found for export")
        raise

    except ValueError as e:
        # Invalid export format or session not completed
        logger.error(f"Export validation error for session {session_id}: {e}")
        raise

    except (IOError, OSError) as e:
        # File system errors during export
        logger.error(f"File system error during export for session {session_id}: {e}")
        raise

    except Exception as e:
        # Unexpected errors
        logger.exception(f"Unexpected export error for session {session_id}: {e}")
        raise


@shared_task(bind=True, name='analysis.batch_analysis')
def batch_analysis(self, session_ids):
    """
    Process multiple analysis sessions in batch.

    Args:
        self: Celery task instance (bound)
        session_ids: List of AnalysisSession IDs to process

    Returns:
        dict: Batch processing summary
    """
    logger.info(f"Starting batch analysis for {len(session_ids)} sessions")

    results = []
    total = len(session_ids)

    for i, session_id in enumerate(session_ids):
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i + 1,
                'total': total,
                'status': f'Processing session {session_id}...'
            }
        )

        try:
            # Queue individual analysis task
            result = run_analysis_async.delay(session_id)
            results.append({
                'session_id': session_id,
                'task_id': result.id,
                'status': 'queued',
            })
        except ImportError as e:
            # Celery not available
            logger.error(f"Celery unavailable for session {session_id}: {e}")
            results.append({
                'session_id': session_id,
                'status': 'failed',
                'error': 'Background task system unavailable',
            })
        except Exception as e:
            # Unexpected errors queuing task
            logger.exception(f"Failed to queue session {session_id}: {e}")
            results.append({
                'session_id': session_id,
                'status': 'failed',
                'error': str(e),
            })

    logger.info(f"Batch analysis queued: {len(results)} tasks")

    return {
        'total_sessions': total,
        'queued': len([r for r in results if r['status'] == 'queued']),
        'failed': len([r for r in results if r['status'] == 'failed']),
        'results': results,
    }
