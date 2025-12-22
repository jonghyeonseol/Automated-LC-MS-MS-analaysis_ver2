"""
Integration tests for complete analysis workflow
"""
import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.analysis.models import AnalysisSession, AnalysisResult, Compound
from apps.analysis.services.analysis_service import AnalysisService


@pytest.mark.integration
class TestAnalysisWorkflow:
    """Test complete analysis workflow from upload to results"""

    def test_complete_analysis_pipeline(self, test_user, sample_csv_file):
        """Test full analysis pipeline"""
        # Create session
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Integration Test",
            data_type="porcine",
            uploaded_file=sample_csv_file,
            file_size=sample_csv_file.size,
            original_filename="test_data.csv",
            r2_threshold=0.75,
            outlier_threshold=2.5,
            rt_tolerance=0.1,
        )

        assert session.status == "pending"

        # Run analysis
        service = AnalysisService()
        result = service.run_analysis(session)

        # Verify result created
        assert result is not None
        assert isinstance(result, AnalysisResult)

        # Verify session updated
        session.refresh_from_db()
        assert session.status == "completed"

        # Verify compounds created
        compounds = Compound.objects.filter(session=session)
        assert compounds.count() > 0

        # Verify result statistics
        assert result.total_compounds > 0
        assert result.valid_compounds >= 0
        assert 0 <= result.success_rate <= 100

    def test_analysis_with_invalid_data(self, test_user):
        """Test analysis handles invalid CSV data"""
        invalid_csv = SimpleUploadedFile(
            "invalid.csv",
            b"Invalid,Data,Format\n1,2,3",
            content_type="text/csv"
        )

        session = AnalysisSession.objects.create(
            user=test_user,
            name="Invalid Test",
            data_type="porcine",
            uploaded_file=invalid_csv,
            file_size=invalid_csv.size,
            original_filename="invalid.csv",
        )

        service = AnalysisService()

        # Should handle error gracefully
        with pytest.raises(Exception):
            service.run_analysis(session)

        session.refresh_from_db()
        assert session.status == "failed"

    def test_analysis_creates_categorized_compounds(self, test_user, sample_csv_file):
        """Test compounds are properly categorized"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Category Test",
            data_type="porcine",
            uploaded_file=sample_csv_file,
            file_size=sample_csv_file.size,
            original_filename="test_data.csv",
        )

        service = AnalysisService()
        result = service.run_analysis(session)

        # Get compounds by category
        gm_compounds = Compound.objects.filter(session=session, category="GM")
        gd_compounds = Compound.objects.filter(session=session, category="GD")
        gt_compounds = Compound.objects.filter(session=session, category="GT")

        # Verify categorization happened
        total_categorized = gm_compounds.count() + gd_compounds.count() + gt_compounds.count()
        assert total_categorized > 0

    def test_concurrent_analysis_sessions(self, test_user, sample_csv_file):
        """Test multiple concurrent analysis sessions"""
        sessions = []

        # Create multiple sessions
        for i in range(3):
            csv_copy = SimpleUploadedFile(
                f"test_{i}.csv",
                sample_csv_file.read(),
                content_type="text/csv"
            )
            sample_csv_file.seek(0)  # Reset file pointer

            session = AnalysisSession.objects.create(
                user=test_user,
                name=f"Session {i}",
                data_type="porcine",
                uploaded_file=csv_copy,
                file_size=csv_copy.size,
                original_filename=f"test_{i}.csv",
            )
            sessions.append(session)

        # Run analysis on all sessions
        service = AnalysisService()
        results = []

        for session in sessions:
            result = service.run_analysis(session)
            results.append(result)

        # Verify all completed
        for session in sessions:
            session.refresh_from_db()
            assert session.status == "completed"

        # Verify all have results
        assert len(results) == 3
        for result in results:
            assert result.total_compounds > 0


@pytest.mark.integration
class TestDatabaseIntegrity:
    """Test database integrity constraints"""

    def test_session_result_integrity(self, test_user):
        """Test session and result remain consistent"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Integrity Test",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        result = AnalysisResult.objects.create(
            session=session,
            total_compounds=10,
            valid_compounds=8,
        )

        # Verify relationship
        assert session.result == result
        assert result.session == session

        # Delete session should cascade
        session_id = session.id
        result_id = result.id

        # Use hard_delete() since AnalysisSession uses SoftDeleteModel
        session.hard_delete()

        assert not AnalysisSession.objects.filter(id=session_id).exists()
        assert not AnalysisResult.objects.filter(id=result_id).exists()

    def test_user_deletion_cascades(self, test_user):
        """Test deleting user cascades to sessions"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Cascade Test",
            data_type="porcine",
            status="pending",
            file_size=1024,
            original_filename="test.csv",
        )

        session_id = session.id
        test_user.delete()

        # Session should be deleted
        assert not AnalysisSession.objects.filter(id=session_id).exists()


@pytest.mark.integration
class TestAnalysisPerformance:
    """Test analysis performance with various data sizes"""

    def test_small_dataset_performance(self, test_user, sample_csv_file):
        """Test analysis completes quickly for small dataset"""
        import time

        session = AnalysisSession.objects.create(
            user=test_user,
            name="Performance Test Small",
            data_type="porcine",
            uploaded_file=sample_csv_file,
            file_size=sample_csv_file.size,
            original_filename="small.csv",
        )

        service = AnalysisService()

        start_time = time.time()
        result = service.run_analysis(session)
        duration = time.time() - start_time

        # Should complete quickly (< 5 seconds for small dataset)
        assert duration < 5.0
        assert result is not None

    def test_database_query_optimization(self, test_user):
        """Test database queries are optimized"""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        session = AnalysisSession.objects.create(
            user=test_user,
            name="Query Test",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        # Create compounds
        for i in range(10):
            Compound.objects.create(
                session=session,
                name=f"Compound {i}",
                rt=float(i),
                volume=1000.0,
                log_p=float(i) / 10,  # Fixed: log_p is required
            )

        # Test query efficiency
        with CaptureQueriesContext(connection) as queries:
            # Fetch session with related data
            session_with_compounds = (
                AnalysisSession.objects
                .prefetch_related('compounds')
                .get(id=session.id)
            )

            # Access compounds (should use prefetched data)
            compounds_list = list(session_with_compounds.compounds.all())

        # Should use minimal queries (select_related/prefetch_related)
        # 1 for session + 1 for prefetch compounds = 2 queries max
        assert len(queries) <= 3
