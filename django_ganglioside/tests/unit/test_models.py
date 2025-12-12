"""
Unit tests for Django models
"""
import pytest
from django.contrib.auth.models import User
from apps.analysis.models import (
    AnalysisSession,
    AnalysisResult,
    Compound,
)


@pytest.mark.unit
class TestAnalysisSessionModel:
    """Test AnalysisSession model"""

    def test_create_analysis_session(self, test_user):
        """Test creating an analysis session"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="pending",
            file_size=1024,
            original_filename="test.csv",
            r2_threshold=0.75,
            outlier_threshold=2.5,
            rt_tolerance=0.1,
        )

        assert session.id is not None
        assert session.user == test_user
        assert session.name == "Test Session"
        assert session.status == "pending"
        assert session.data_type == "porcine"

    def test_session_str_representation(self, test_user):
        """Test string representation of session"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="pending",
            file_size=1024,
            original_filename="test.csv",
        )

        # __str__ returns "{name} - {status_display}"
        assert str(session) == "Test Session - Pending"

    def test_session_status_choices(self, test_user):
        """Test valid status choices"""
        valid_statuses = ['pending', 'processing', 'completed', 'failed']

        for status in valid_statuses:
            session = AnalysisSession.objects.create(
                user=test_user,
                name=f"Session {status}",
                data_type="porcine",
                status=status,
                file_size=1024,
                original_filename="test.csv",
            )
            assert session.status == status

    def test_session_timestamps(self, test_user):
        """Test automatic timestamp creation"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="pending",
            file_size=1024,
            original_filename="test.csv",
        )

        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.created_at <= session.updated_at


@pytest.mark.unit
class TestAnalysisResultModel:
    """Test AnalysisResult model"""

    def test_create_analysis_result(self, test_user):
        """Test creating an analysis result"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        result = AnalysisResult.objects.create(
            session=session,
            total_compounds=100,
            valid_compounds=80,
            outlier_count=15,  # Fixed: was 'outliers'
            success_rate=80.0,
        )

        assert result.id is not None
        assert result.session == session
        assert result.total_compounds == 100
        assert result.valid_compounds == 80
        assert result.success_rate == 80.0
        assert result.outlier_count == 15

    def test_result_one_to_one_with_session(self, test_user):
        """Test one-to-one relationship with session"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        result = AnalysisResult.objects.create(
            session=session,
            total_compounds=100,
            valid_compounds=80,
        )

        # Access result from session
        assert session.result == result

        # Access session from result
        assert result.session == session

    def test_result_json_fields(self, test_user):
        """Test JSON fields store data correctly"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        regression_analysis = {
            'GD1': {'r2': 0.85, 'coefficients': [1.2, -0.5]},
            'GM3': {'r2': 0.92, 'coefficients': [1.5, -0.3]},
        }

        result = AnalysisResult.objects.create(
            session=session,
            total_compounds=100,
            regression_analysis=regression_analysis,  # Fixed: was 'regression_data'
        )

        assert result.regression_analysis == regression_analysis
        assert result.regression_analysis['GD1']['r2'] == 0.85


@pytest.mark.unit
class TestCompoundModel:
    """Test Compound model"""

    def test_create_compound(self, test_user):
        """Test creating a compound"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        compound = Compound.objects.create(
            session=session,
            name="GD1(36:1;O2)",
            rt=9.572,
            volume=1000000.0,
            log_p=1.53,
            status="valid",
            category="GD",
        )

        assert compound.id is not None
        assert compound.session == session
        assert compound.name == "GD1(36:1;O2)"
        assert compound.rt == 9.572
        assert compound.status == "valid"

    def test_compound_foreign_key_cascade(self, test_user):
        """Test cascade delete when session is deleted"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        compound = Compound.objects.create(
            session=session,
            name="GD1(36:1;O2)",
            rt=9.572,
            volume=1000000.0,
            log_p=1.53,  # Fixed: log_p is required
        )

        compound_id = compound.id
        # Use hard_delete() since AnalysisSession uses SoftDeleteModel
        session.hard_delete()

        # Compound should be deleted via CASCADE
        assert not Compound.objects.filter(id=compound_id).exists()

    def test_compound_ordering(self, test_user):
        """Test compounds are ordered by RT"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        # Create compounds in random order (log_p is required)
        Compound.objects.create(session=session, name="C3", rt=10.5, volume=1000, log_p=3.0)
        Compound.objects.create(session=session, name="C1", rt=8.5, volume=1000, log_p=1.0)
        Compound.objects.create(session=session, name="C2", rt=9.5, volume=1000, log_p=2.0)

        # Retrieve and check order
        compounds = list(Compound.objects.filter(session=session))
        assert compounds[0].name == "C1"  # RT 8.5
        assert compounds[1].name == "C2"  # RT 9.5
        assert compounds[2].name == "C3"  # RT 10.5


@pytest.mark.unit
class TestModelRelationships:
    """Test relationships between models"""

    def test_user_sessions_relationship(self, test_user):
        """Test user can have multiple sessions"""
        session1 = AnalysisSession.objects.create(
            user=test_user,
            name="Session 1",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test1.csv",
        )

        session2 = AnalysisSession.objects.create(
            user=test_user,
            name="Session 2",
            data_type="bovine",
            status="pending",
            file_size=2048,
            original_filename="test2.csv",
        )

        user_sessions = AnalysisSession.objects.filter(user=test_user)
        assert user_sessions.count() == 2
        assert session1 in user_sessions
        assert session2 in user_sessions

    def test_session_compounds_relationship(self, test_user):
        """Test session can have multiple compounds"""
        session = AnalysisSession.objects.create(
            user=test_user,
            name="Test Session",
            data_type="porcine",
            status="completed",
            file_size=1024,
            original_filename="test.csv",
        )

        compounds = [
            Compound.objects.create(
                session=session,
                name=f"Compound {i}",
                rt=float(i),
                volume=1000.0,
                log_p=float(i) * 0.5,  # Fixed: log_p is required
            )
            for i in range(5)
        ]

        session_compounds = Compound.objects.filter(session=session)
        assert session_compounds.count() == 5

        for compound in compounds:
            assert compound in session_compounds
