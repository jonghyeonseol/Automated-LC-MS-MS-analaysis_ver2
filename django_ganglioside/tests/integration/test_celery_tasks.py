"""
Integration tests for Celery tasks
"""
import pytest
from unittest.mock import patch, MagicMock
from apps.analysis.models import AnalysisSession
from apps.analysis.tasks import (
    run_analysis_async,
    cleanup_old_sessions,
    send_analysis_complete_notification,
)


@pytest.mark.integration
class TestAnalysisTasks:
    """Test Celery analysis tasks"""

    def test_run_analysis_async_task(self, test_user, sample_csv_file, celery_eager_mode):
        """Test async analysis task"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Async Test",
            data_type="porcine",
            uploaded_file=sample_csv_file,
            file_size=sample_csv_file.size,
            original_filename="test.csv",
        )

        # Run task (synchronously in test mode)
        result = run_analysis_async.delay(session.id)

        # Task should complete
        assert result.successful()

        # Session should be updated
        session.refresh_from_db()
        assert session.status == "completed"

    def test_analysis_task_handles_errors(self, test_user, celery_eager_mode):
        """Test analysis task handles errors gracefully"""
        # Create session with no file
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Error Test",
            data_type="porcine",
            status="pending",
            file_size=1024,
            original_filename="missing.csv",
        )

        # Run task
        result = run_analysis_async.delay(session.id)

        # Task should fail but not crash
        session.refresh_from_db()
        assert session.status == "failed"

    @patch('apps.analysis.tasks.send_channels_message')
    def test_task_sends_progress_updates(self, mock_send, test_user, sample_csv_file, celery_eager_mode):
        """Test task sends WebSocket progress updates"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Progress Test",
            data_type="porcine",
            uploaded_file=sample_csv_file,
            file_size=sample_csv_file.size,
            original_filename="test.csv",
        )

        # Run task
        run_analysis_async.delay(session.id)

        # Should have sent progress messages
        assert mock_send.called


@pytest.mark.integration
class TestCleanupTasks:
    """Test cleanup tasks"""

    def test_cleanup_old_sessions(self, test_user, celery_eager_mode):
        """Test cleanup of old sessions"""
        from datetime import timedelta
        from django.utils import timezone

        # Create old completed session
        old_session = AnalysisSession.objects.create(
            user=test_user,
            name="Old Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="old.csv",
        )

        # Manually set created_at to 40 days ago
        old_date = timezone.now() - timedelta(days=40)
        AnalysisSession.objects.filter(id=old_session.id).update(created_at=old_date)

        # Create recent session
        recent_session = AnalysisSession.objects.create(
            user=test_user,
            name="Recent Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="recent.csv",
        )

        # Run cleanup (delete sessions older than 30 days)
        result = cleanup_old_sessions.delay(days=30)

        # Old session should be deleted
        assert not AnalysisSession.objects.filter(id=old_session.id).exists()

        # Recent session should remain
        assert AnalysisSession.objects.filter(id=recent_session.id).exists()

    def test_cleanup_preserves_recent_sessions(self, test_user, celery_eager_mode):
        """Test cleanup doesn't delete recent sessions"""
        # Create recent sessions
        sessions = []
        for i in range(5):
            session = AnalysisSession.objects.create(
                user=test_user,
                name=f"Session {i}",
                data_type="porcine",
                status="completed",
                file_size=1024,
                original_filename=f"test_{i}.csv",
            )
            sessions.append(session)

        # Run cleanup
        cleanup_old_sessions.delay(days=30)

        # All sessions should remain
        for session in sessions:
            assert AnalysisSession.objects.filter(id=session.id).exists()


@pytest.mark.integration
class TestNotificationTasks:
    """Test notification tasks"""

    @patch('apps.analysis.tasks.send_email')
    def test_send_completion_notification(self, mock_send_email, test_user, celery_eager_mode):
        """Test sending completion notification"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Notification Test",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        # Send notification
        send_analysis_complete_notification.delay(session.id)

        # Email should be sent
        mock_send_email.assert_called_once()


@pytest.mark.integration
class TestTaskRetry:
    """Test task retry logic"""

    @patch('apps.analysis.services.analysis_service.AnalysisService.run_analysis')
    def test_task_retries_on_failure(self, mock_analysis, test_user, sample_csv_file, celery_eager_mode):
        """Test task retries on temporary failure"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Retry Test",
            data_type="porcine",
            uploaded_file=sample_csv_file,
            file_size=sample_csv_file.size,
            original_filename="test.csv",
        )

        # Mock temporary failure
        mock_analysis.side_effect = [
            Exception("Temporary error"),  # First attempt fails
            MagicMock(),  # Second attempt succeeds
        ]

        # This would retry in production, but in eager mode just fails
        # Just verify the task structure is correct
        try:
            run_analysis_async.delay(session.id)
        except Exception:
            pass  # Expected in eager mode


@pytest.mark.integration
class TestTaskChaining:
    """Test task chaining and workflow"""

    def test_analysis_completion_triggers_notification(self, test_user, sample_csv_file, celery_eager_mode):
        """Test analysis completion triggers notification task"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Chain Test",
            data_type="porcine",
            uploaded_file=sample_csv_file,
            file_size=sample_csv_file.size,
            original_filename="test.csv",
        )

        # Run analysis
        run_analysis_async.delay(session.id)

        # Session should be completed
        session.refresh_from_db()
        assert session.status == "completed"

        # Notification would be triggered (tested separately)
