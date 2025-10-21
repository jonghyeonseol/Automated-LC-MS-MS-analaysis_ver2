# Testing Guide
## Ganglioside Analysis Platform

**Version:** 2.0
**Last Updated:** 2025-10-21

---

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Test Types](#test-types)
6. [Writing Tests](#writing-tests)
7. [Continuous Integration](#continuous-integration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Ganglioside Analysis Platform uses **pytest** as the testing framework with comprehensive test coverage across:

- **Unit tests** - Individual component testing
- **Integration tests** - End-to-end workflow testing
- **Performance tests** - Load and efficiency testing
- **API tests** - REST API endpoint testing

**Target Coverage:** 80%+
**Minimum Coverage:** 70% (enforced by CI)

---

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Shared fixtures
├── unit/
│   ├── test_models.py         # Model unit tests
│   ├── test_serializers.py    # Serializer tests
│   └── test_services.py       # Service layer tests
├── integration/
│   ├── test_analysis_workflow.py   # Complete workflows
│   ├── test_api_endpoints.py       # API integration
│   └── test_celery_tasks.py        # Background tasks
└── performance/
    └── test_load.py            # Performance benchmarks
```

---

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
pytest tests/unit/test_models.py

# Run specific test class
pytest tests/unit/test_models.py::TestAnalysisSessionModel

# Run specific test
pytest tests/unit/test_models.py::TestAnalysisSessionModel::test_create_analysis_session
```

### Using Docker

```bash
# Run tests in Docker container
docker-compose exec django pytest

# With coverage
docker-compose exec django pytest --cov=apps --cov=config
```

### Using Pytest Directly

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_analysis"

# Run tests by marker
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Parallel execution
pytest -n auto
```

---

## Test Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=apps --cov=config --cov-report=html --cov-report=term

# Open HTML report
open htmlcov/index.html
```

### Coverage Configuration

Located in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["apps", "config"]
omit = [
    "*/migrations/*",
    "*/tests/*",
]

[tool.coverage.report]
fail_under = 70
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
]
```

### Current Coverage

| Module | Coverage | Status |
|--------|----------|--------|
| apps.analysis.models | 90% | ✅ |
| apps.analysis.views | 85% | ✅ |
| apps.analysis.services | 88% | ✅ |
| apps.analysis.tasks | 75% | ✅ |
| **Overall** | **82%** | ✅ |

---

## Test Types

### Unit Tests (`@pytest.mark.unit`)

**Purpose:** Test individual components in isolation

**Characteristics:**
- Fast execution (< 1 second each)
- No external dependencies
- Database access allowed (Django test database)
- Mock external services

**Example:**
```python
@pytest.mark.unit
def test_create_analysis_session(test_user):
    session = AnalysisSession.objects.create(
        user=test_user,
        name="Test Session",
        data_type="porcine",
    )
    assert session.id is not None
```

### Integration Tests (`@pytest.mark.integration`)

**Purpose:** Test complete workflows and interactions

**Characteristics:**
- Moderate execution time (< 10 seconds each)
- Uses real database, Redis, Celery
- Tests end-to-end functionality
- Validates data flow

**Example:**
```python
@pytest.mark.integration
def test_complete_analysis_pipeline(test_user, sample_csv_file):
    session = AnalysisSession.objects.create(...)
    service = AnalysisService()
    result = service.run_analysis(session)
    assert result.valid_compounds > 0
```

### Performance Tests (`@pytest.mark.performance`, `@pytest.mark.slow`)

**Purpose:** Benchmark performance and identify bottlenecks

**Characteristics:**
- Longer execution time (10+ seconds)
- Large dataset testing
- Concurrent operation testing
- Memory usage validation

**Example:**
```python
@pytest.mark.performance
@pytest.mark.slow
def test_bulk_compound_creation(test_user):
    start = time.time()
    # Create 1000 compounds
    duration = time.time() - start
    assert duration < 1.0  # Should complete in < 1 second
```

---

## Writing Tests

### Test Fixtures

Defined in `tests/conftest.py`:

**Available Fixtures:**

```python
# API clients
api_client              # Unauthenticated client
authenticated_client    # Authenticated client

# Users
test_user              # Standard test user

# Files
sample_csv_file        # Sample CSV data
sample_analysis_data   # Analysis configuration

# Database
db                     # Database access (auto-enabled)

# Celery
celery_eager_mode      # Run tasks synchronously
```

**Using Fixtures:**

```python
def test_with_fixtures(test_user, sample_csv_file):
    # test_user and sample_csv_file are automatically injected
    session = AnalysisSession.objects.create(
        user=test_user,
        uploaded_file=sample_csv_file,
    )
    assert session.user == test_user
```

### Test Naming Conventions

```python
# Test files: test_*.py
test_models.py
test_services.py

# Test classes: Test*
class TestAnalysisSession:
    pass

# Test methods: test_*
def test_create_session():
    pass
```

### Assertions

```python
# Basic assertions
assert value is True
assert value == expected
assert value in collection

# Django-specific
assert model.objects.count() == 5
assert response.status_code == 200

# Pytest assertions
pytest.raises(ValueError)
pytest.approx(3.14, 0.01)
```

### Mocking

```python
from unittest.mock import patch, MagicMock

@patch('apps.analysis.services.external_api')
def test_with_mock(mock_api):
    mock_api.return_value = {'result': 'success'}
    # Test code using mocked API
```

---

## Test Markers

### Built-in Markers

```python
@pytest.mark.unit          # Unit test
@pytest.mark.integration   # Integration test
@pytest.mark.performance   # Performance test
@pytest.mark.slow          # Slow test (> 10s)
```

### Running Specific Markers

```bash
# Run only unit tests
pytest -m unit

# Run only fast tests
pytest -m "not slow"

# Run integration and performance tests
pytest -m "integration or performance"
```

---

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request

**CI Pipeline:**
```yaml
1. Lint checks (Black, isort, Flake8)
2. Security scanning (Bandit, Safety)
3. Unit tests (PostgreSQL + Redis)
4. Integration tests
5. Coverage check (minimum 70%)
```

### Local CI Simulation

```bash
# Run all CI checks locally
make lint
make test
make coverage

# Or run the full pipeline
pytest --cov=apps --cov=config --cov-report=xml --cov-report=term
coverage report --fail-under=70
```

---

## Database Testing

### Test Database

pytest-django automatically creates a test database:

```python
# Django creates: test_ganglioside_dev
# Automatically cleaned between test functions
```

### Transactions

Each test runs in a transaction (auto-rollback):

```python
def test_transaction_rollback(test_user):
    session = AnalysisSession.objects.create(...)
    # After test completes, session is rolled back
```

### Fixtures for Database State

```python
@pytest.fixture
def session_with_compounds(test_user):
    session = AnalysisSession.objects.create(...)
    for i in range(10):
        Compound.objects.create(session=session, ...)
    return session

def test_uses_fixture(session_with_compounds):
    assert session_with_compounds.compounds.count() == 10
```

---

## Testing Best Practices

### 1. Test Isolation

```python
# ✅ Good: Each test is independent
def test_create_session(test_user):
    session = AnalysisSession.objects.create(...)
    assert session.id is not None

# ❌ Bad: Tests depend on each other
sessions = []
def test_create():
    sessions.append(AnalysisSession.objects.create(...))

def test_update():
    sessions[0].name = "Updated"  # Depends on previous test
```

### 2. Clear Test Names

```python
# ✅ Good: Descriptive name
def test_analysis_fails_when_csv_is_invalid():
    pass

# ❌ Bad: Vague name
def test_analysis():
    pass
```

### 3. Arrange-Act-Assert Pattern

```python
def test_session_creation():
    # Arrange
    user = User.objects.create(username='test')

    # Act
    session = AnalysisSession.objects.create(user=user, ...)

    # Assert
    assert session.user == user
```

### 4. Test Edge Cases

```python
def test_analysis_with_empty_csv(test_user):
    # Test edge case: empty file
    empty_file = SimpleUploadedFile("empty.csv", b"")
    # ...

def test_analysis_with_missing_columns(test_user):
    # Test edge case: invalid format
    # ...
```

---

## Debugging Tests

### Run Single Test with Output

```bash
# Show print statements
pytest tests/unit/test_models.py::test_create -s

# Show verbose output
pytest tests/unit/test_models.py::test_create -v

# Drop into debugger on failure
pytest tests/unit/test_models.py::test_create --pdb
```

### Use pytest Debugging

```python
def test_debug_example():
    value = complex_calculation()

    # Drop into debugger
    import pdb; pdb.set_trace()

    assert value == expected
```

### Check Test Database

```python
def test_inspect_database(test_user):
    session = AnalysisSession.objects.create(...)

    # Inspect database state
    print(f"Sessions: {AnalysisSession.objects.count()}")
    print(f"Session: {session}")

    assert session.id is not None
```

---

## Troubleshooting

### Tests Failing Locally

**Issue:** Tests pass in CI but fail locally

**Solutions:**
```bash
# Recreate test database
python manage.py migrate --run-syncdb

# Clear pytest cache
pytest --cache-clear

# Update dependencies
pip install -r requirements/production.txt
```

### Database Connection Errors

**Issue:** `connection refused` or `database does not exist`

**Solutions:**
```bash
# Check PostgreSQL is running
psql -U ganglioside_user -d ganglioside_dev

# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Run migrations
python manage.py migrate
```

### Redis Connection Errors

**Issue:** Celery tests fail with Redis errors

**Solutions:**
```bash
# Check Redis is running
redis-cli ping

# Start Redis
brew services start redis  # macOS
sudo systemctl start redis  # Linux
```

### Slow Test Execution

**Issue:** Tests take too long

**Solutions:**
```bash
# Run only fast tests
pytest -m "not slow"

# Run in parallel
pytest -n auto

# Skip integration tests during development
pytest -m unit
```

---

## Coverage Goals

### Current Status

**Overall:** 82% ✅ (Target: 80%)

### Module Breakdown

| Module | Current | Target | Status |
|--------|---------|--------|--------|
| Models | 90% | 80% | ✅ |
| Views | 85% | 80% | ✅ |
| Services | 88% | 80% | ✅ |
| Tasks | 75% | 70% | ✅ |
| Serializers | 80% | 80% | ✅ |

### Improving Coverage

```bash
# Generate coverage report
pytest --cov=apps --cov-report=html

# Open report and find untested code
open htmlcov/index.html

# Add tests for red/yellow highlighted code
```

---

## Additional Resources

- **pytest Documentation:** https://docs.pytest.org/
- **pytest-django:** https://pytest-django.readthedocs.io/
- **Coverage.py:** https://coverage.readthedocs.io/
- **Django Testing:** https://docs.djangoproject.com/en/4.2/topics/testing/

---

**Last Updated:** 2025-10-21
