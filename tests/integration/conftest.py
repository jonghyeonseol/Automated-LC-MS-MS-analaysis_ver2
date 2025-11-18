#!/usr/bin/env python3
"""
Shared pytest fixtures for integration tests
"""

import os
import sys
import pytest
import pandas as pd
from pathlib import Path

# Add backend and src paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "src"))

# Import Flask app
from app import app as flask_app


@pytest.fixture(scope="session")
def project_root_path():
    """Provide the project root directory path."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope="session")
def sample_data_dir(project_root_path):
    """Provide the sample data directory path."""
    return project_root_path / "data" / "sample"


@pytest.fixture(scope="session")
def samples_data_dir(project_root_path):
    """Provide the samples data directory path."""
    return project_root_path / "data" / "samples"


@pytest.fixture
def flask_client():
    """Create Flask test client."""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def sample_csv_path(sample_data_dir):
    """Provide path to testwork.csv sample file."""
    csv_path = sample_data_dir / "testwork.csv"
    if not csv_path.exists():
        pytest.skip(f"Sample file not found: {csv_path}")
    return csv_path


@pytest.fixture
def user_csv_path(samples_data_dir):
    """Provide path to testwork_user.csv file."""
    csv_path = samples_data_dir / "testwork_user.csv"
    if not csv_path.exists():
        pytest.skip(f"User data file not found: {csv_path}")
    return csv_path


@pytest.fixture
def sample_csv_data(sample_csv_path):
    """Load sample CSV data as DataFrame."""
    return pd.read_csv(sample_csv_path)


@pytest.fixture
def user_csv_data(user_csv_path):
    """Load user CSV data as DataFrame."""
    return pd.read_csv(user_csv_path)


@pytest.fixture
def default_analysis_params():
    """Default analysis parameters for testing."""
    return {
        "data_type": "Porcine",
        "outlier_threshold": 2.5,
        "r2_threshold": 0.75,
        "rt_tolerance": 0.1
    }


@pytest.fixture
def categorizer():
    """Create GangliosideCategorizer instance."""
    from utils.ganglioside_categorizer import GangliosideCategorizer
    return GangliosideCategorizer()


@pytest.fixture
def ganglioside_processor():
    """Create GangliosideProcessor instance."""
    from services.ganglioside_processor import GangliosideProcessor
    return GangliosideProcessor()
