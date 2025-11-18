# CI/CD Quick Reference Guide

Quick commands and configurations for the CI/CD pipeline.

## Quick Start

```bash
# Install development tools
pip install -r requirements/test.txt
pip install -r requirements/lint.txt

# Setup pre-commit hooks
pre-commit install

# Run all pre-commit checks
pre-commit run --all-files
```

---

## Local Testing Commands

### Run Tests
```bash
# All tests with coverage
pytest --cov=apps --cov=config --cov-report=html

# Fast tests only
pytest -m "not slow"

# Specific app
pytest apps/analysis/tests/

# Parallel execution
pytest -n auto

# With verbose output
pytest -vv

# Stop on first failure
pytest -x

# Coverage check (fail if below 70%)
pytest --cov=apps --cov-report=term-missing --cov-fail-under=70
```

### Code Quality
```bash
# Format code (auto-fix)
black apps/ config/ tests/
isort apps/ config/ tests/

# Check formatting (no changes)
black --check apps/ config/ tests/
isort --check-only apps/ config/ tests/

# Linting
flake8 apps/ config/ tests/
pylint apps/ config/

# Type checking
mypy apps/ config/

# All checks at once
pre-commit run --all-files
```

### Security Scanning
```bash
# Code security
bandit -r apps/ config/

# Dependency vulnerabilities
safety check
pip-audit

# Secret detection
gitleaks detect --source . --verbose

# All security checks
bandit -r apps/ config/ && safety check && pip-audit
```

---

## Docker Commands

### Build Images
```bash
# Build Django image
docker build -t ganglioside:dev -f Dockerfile .

# Build Celery image
docker build -t ganglioside-celery:dev -f Dockerfile.celery .

# Build without cache
docker build --no-cache -t ganglioside:dev .
```

### Security Scanning
```bash
# Trivy scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ganglioside:dev

# Dockle scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  goodwithtech/dockle ganglioside:dev

# Grype scan
grype ganglioside:dev
```

### Test Images
```bash
# Run Django container
docker run --rm -p 8000:8000 ganglioside:dev

# Check Python version
docker run --rm ganglioside:dev python --version

# Check Django version
docker run --rm ganglioside:dev django-admin --version

# Interactive shell
docker run --rm -it ganglioside:dev /bin/bash
```

---

## GitHub Actions Commands

### Workflow Management
```bash
# List all workflows
gh workflow list

# View workflow runs
gh run list --workflow=ci.yml

# Watch workflow run
gh run watch

# View workflow logs
gh run view --log

# Re-run failed jobs
gh run rerun <run-id> --failed

# Cancel workflow run
gh run cancel <run-id>
```

### Secrets Management
```bash
# List secrets
gh secret list

# Set secret
gh secret set DOCKER_USERNAME
gh secret set DOCKER_PASSWORD < token.txt

# Delete secret
gh secret delete SECRET_NAME
```

---

## Coverage Commands

### Generate Reports
```bash
# HTML report
pytest --cov=apps --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=apps --cov-report=term-missing

# XML report (for CI)
pytest --cov=apps --cov-report=xml

# Multiple formats
pytest --cov=apps --cov-report=html --cov-report=xml --cov-report=term
```

### Coverage Analysis
```bash
# Show coverage summary
coverage report

# Show missing lines
coverage report --show-missing

# Check threshold
coverage report --fail-under=70

# Generate HTML
coverage html
```

---

## Common Workflows

### Before Pushing Code
```bash
# 1. Format code
black apps/ config/ tests/
isort apps/ config/ tests/

# 2. Run linters
flake8 apps/ config/ tests/
mypy apps/ config/

# 3. Run tests
pytest --cov=apps --cov-report=term-missing

# 4. Security scan
bandit -r apps/ config/

# 5. Pre-commit checks
pre-commit run --all-files

# 6. Commit and push
git add .
git commit -m "Your message"
git push
```

### Creating a Pull Request
```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Make changes and commit
git add .
git commit -m "Add feature"

# 3. Push branch
git push -u origin feature/your-feature

# 4. Create PR
gh pr create --title "Add feature" --body "Description"

# 5. Watch CI status
gh pr checks

# 6. View PR
gh pr view --web
```

### Deploying to Production
```bash
# 1. Merge to main
git checkout main
git pull origin main
git merge develop

# 2. Tag release
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 3. Monitor deployment
gh run watch

# 4. Verify deployment
curl -f https://ganglioside.example.com/health
```

---

## Configuration Files

### pyproject.toml
```toml
[tool.black]
line-length = 100
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.9"
warn_return_any = true

[tool.coverage.run]
source = ["apps", "config"]
omit = ["*/migrations/*", "*/tests/*"]

[tool.coverage.report]
fail_under = 70
```

### .flake8
```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,*/migrations/*
ignore = E203,E501,W503
```

### pytest.ini
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.development
testpaths = tests
addopts = --reuse-db --strict-markers
```

---

## Environment Variables for CI

### Testing
```bash
DJANGO_SETTINGS_MODULE=config.settings.development
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/ganglioside_test
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=test-secret-key-for-ci
DEBUG=False
```

### Docker Build
```bash
DOCKER_BUILDKIT=1
COMPOSE_DOCKER_CLI_BUILD=1
```

---

## Troubleshooting Quick Fixes

### Tests failing locally
```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres
python manage.py migrate

# Clear pytest cache
pytest --cache-clear

# Reinstall dependencies
pip install -r requirements/production.txt --force-reinstall
```

### Coverage too low
```bash
# Identify untested files
coverage report --show-missing

# Generate HTML report
coverage html
open htmlcov/index.html

# Test specific file
pytest apps/analysis/tests/test_processor.py --cov=apps.analysis.services.processor
```

### Docker build failing
```bash
# Clear Docker cache
docker builder prune -af

# Build with verbose output
docker build --progress=plain -t ganglioside:dev .

# Check disk space
docker system df
docker system prune -af
```

### Pre-commit hooks failing
```bash
# Update hooks
pre-commit autoupdate

# Clear cache
pre-commit clean

# Reinstall
pre-commit uninstall
pre-commit install

# Skip hooks (emergency only)
git commit --no-verify
```

---

## Monitoring & Debugging

### View CI Logs
```bash
# Latest run
gh run view --log

# Specific job
gh run view <run-id> --job=<job-id> --log

# Failed runs only
gh run list --status=failure
```

### Download Artifacts
```bash
# List artifacts
gh run view <run-id> --artifacts

# Download artifact
gh run download <run-id> -n coverage-reports
```

### Check Security Alerts
```bash
# Dependabot alerts
gh api /repos/:owner/:repo/dependabot/alerts

# Code scanning alerts
gh api /repos/:owner/:repo/code-scanning/alerts

# Secret scanning alerts
gh api /repos/:owner/:repo/secret-scanning/alerts
```

---

## Performance Optimization

### Speed Up Tests
```bash
# Use pytest-xdist (parallel)
pytest -n auto

# Use --reuse-db
pytest --reuse-db

# Skip slow tests
pytest -m "not slow"

# Create database once
pytest --create-db
pytest --reuse-db
```

### Speed Up Docker Builds
```bash
# Use BuildKit
export DOCKER_BUILDKIT=1

# Multi-stage builds
# (already implemented in Dockerfile)

# Cache dependencies
# (already implemented in workflow)
```

---

## Useful Links

- **GitHub Actions**: https://github.com/YOUR_ORG/ganglioside/actions
- **Codecov**: https://codecov.io/gh/YOUR_ORG/ganglioside
- **Docker Hub**: https://hub.docker.com/r/YOUR_USER/ganglioside
- **Staging**: https://staging.ganglioside.example.com
- **Production**: https://ganglioside.example.com

---

## Badges for README

```markdown
[![CI/CD](https://github.com/YOUR_ORG/ganglioside/workflows/CI%2FCD%20Pipeline/badge.svg)](https://github.com/YOUR_ORG/ganglioside/actions)
[![codecov](https://codecov.io/gh/YOUR_ORG/ganglioside/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_ORG/ganglioside)
[![Docker](https://img.shields.io/docker/v/YOUR_USER/ganglioside?label=docker)](https://hub.docker.com/r/YOUR_USER/ganglioside)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
```

---

**Last Updated**: 2025-11-18
**Quick Reference Version**: 1.0
