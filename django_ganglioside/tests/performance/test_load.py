"""
Performance and load tests
"""
import pytest
import time
from django.contrib.auth.models import User
from apps.analysis.models import AnalysisSession, Compound


@pytest.mark.performance
@pytest.mark.slow
class TestDatabasePerformance:
    """Test database query performance"""

    def test_bulk_compound_creation(self, test_user):
        """Test bulk creation of compounds"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Bulk Test",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        # Create compounds in bulk
        compounds = [
            Compound(
                session=session,
                name=f"Compound {i}",
                rt=float(i),
                volume=1000.0 + i,
                log_p=float(i) / 10,
            )
            for i in range(1000)
        ]

        start_time = time.time()
        Compound.objects.bulk_create(compounds)
        duration = time.time() - start_time

        # Should complete quickly (< 1 second for 1000 records)
        assert duration < 1.0
        assert Compound.objects.filter(session=session).count() == 1000

    def test_query_performance_with_large_dataset(self, test_user):
        """Test query performance with large dataset"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Large Dataset",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        # Create 500 compounds
        compounds = [
            Compound(
                session=session,
                name=f"GD1({i}:1;O2)",
                rt=float(i),
                volume=1000.0 + i,
                log_p=float(i) / 10,  # Fixed: log_p is required
                category="GD",
            )
            for i in range(500)
        ]
        Compound.objects.bulk_create(compounds)

        # Test filtered query performance
        start_time = time.time()
        gd_compounds = list(Compound.objects.filter(
            session=session,
            category="GD"
        ).values_list('name', 'rt', 'volume'))
        duration = time.time() - start_time

        # Should be fast (< 0.1 seconds)
        assert duration < 0.1
        assert len(gd_compounds) == 500

    def test_aggregation_performance(self, test_user):
        """Test aggregation query performance"""
        from django.db.models import Avg, Count, Max, Min

        # Create multiple sessions with compounds
        for session_idx in range(10):
            session = AnalysisSession.objects.create(
                user=test_user,
                name=f"Session {session_idx}",
                data_type="porcine",
                status="completed",
                file_size=1024,
                original_filename=f"test_{session_idx}.csv",
            )

            compounds = [
                Compound(
                    session=session,
                    name=f"Compound {i}",
                    rt=float(i),
                    volume=1000.0 + i,
                    log_p=float(i) / 10,  # Fixed: log_p is required
                )
                for i in range(100)
            ]
            Compound.objects.bulk_create(compounds)

        # Test aggregation performance
        start_time = time.time()
        stats = Compound.objects.aggregate(
            total=Count('id'),
            avg_rt=Avg('rt'),
            min_rt=Min('rt'),
            max_rt=Max('rt'),
            avg_volume=Avg('volume'),
        )
        duration = time.time() - start_time

        # Should be fast (< 0.5 seconds)
        assert duration < 0.5
        assert stats['total'] == 1000
        assert stats['avg_rt'] is not None


@pytest.mark.performance
class TestAPIPerformance:
    """Test API endpoint performance"""

    def test_list_endpoint_performance(self, authenticated_client, test_user):
        """Test list endpoint with many sessions"""
        # Create 100 sessions
        sessions = []
        for i in range(100):
            session = AnalysisSession.objects.create(
                user=test_user,
                name=f"Session {i}",
                data_type="porcine",
                status="completed",
                file_size=1024,
                original_filename=f"test_{i}.csv",
            )
            sessions.append(session)

        from django.urls import reverse

        # Test list performance
        url = reverse('analysis:api-session-list')

        start_time = time.time()
        response = authenticated_client.get(url)
        duration = time.time() - start_time

        assert response.status_code == 200
        # Should respond quickly (< 1 second)
        assert duration < 1.0

    def test_detail_endpoint_performance(self, authenticated_client, test_user):
        """Test detail endpoint performance"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Detail Test",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        # Create many compounds
        compounds = [
            Compound(
                session=session,
                name=f"Compound {i}",
                rt=float(i),
                volume=1000.0,
                log_p=float(i) / 10,  # Fixed: log_p is required
            )
            for i in range(500)
        ]
        Compound.objects.bulk_create(compounds)

        from django.urls import reverse

        url = reverse('analysis:api-session-detail', kwargs={'pk': session.id})

        start_time = time.time()
        response = authenticated_client.get(url)
        duration = time.time() - start_time

        assert response.status_code == 200
        # Should respond quickly even with many compounds
        assert duration < 0.5


@pytest.mark.performance
@pytest.mark.slow
class TestConcurrencyPerformance:
    """Test concurrent operations"""

    @pytest.mark.skipif(True, reason="SQLite doesn't support concurrent writes - skipped for local testing")
    def test_concurrent_session_creation(self, test_user):
        """Test creating multiple sessions concurrently"""
        from django.db import transaction
        import concurrent.futures

        def create_session(index):
            with transaction.atomic():
                return AnalysisSession.objects.create(
                    user=test_user,
                    name=f"Concurrent {index}",
                    data_type="porcine",
                    status="pending",
                    file_size=1024,
                    original_filename=f"test_{index}.csv",
                )

        # Create 10 sessions concurrently
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_session, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        duration = time.time() - start_time

        # Should complete quickly
        assert duration < 5.0
        assert len(results) == 10
        assert AnalysisSession.objects.filter(user=test_user).count() == 10


@pytest.mark.performance
class TestMemoryUsage:
    """Test memory-efficient operations"""

    def test_iterator_for_large_queryset(self, test_user):
        """Test using iterator for large querysets"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Memory Test",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        # Create many compounds
        compounds = [
            Compound(
                session=session,
                name=f"Compound {i}",
                rt=float(i),
                volume=1000.0,
                log_p=float(i) / 100,  # Fixed: log_p is required
            )
            for i in range(5000)
        ]
        Compound.objects.bulk_create(compounds)

        # Use iterator to avoid loading all into memory
        count = 0
        for compound in Compound.objects.filter(session=session).iterator(chunk_size=100):
            count += 1

        assert count == 5000

    def test_values_list_for_large_dataset(self, test_user):
        """Test using values_list for memory efficiency"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Values Test",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        compounds = [
            Compound(
                session=session,
                name=f"Compound {i}",
                rt=float(i),
                volume=1000.0,
                log_p=float(i) / 100,  # Fixed: log_p is required
            )
            for i in range(1000)
        ]
        Compound.objects.bulk_create(compounds)

        # Use values_list for specific fields only
        start_time = time.time()
        names = list(Compound.objects.filter(session=session).values_list('name', flat=True))
        duration = time.time() - start_time

        assert len(names) == 1000
        # Should be faster than fetching full objects
        assert duration < 0.1
