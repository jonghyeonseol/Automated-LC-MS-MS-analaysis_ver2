# Complete CI/CD Pipeline Guide

## Overview

This document describes the complete CI/CD pipeline for the LC-MS/MS Ganglioside Analysis Platform. The pipeline implements industry best practices with comprehensive testing, security scanning, and automated deployments.

## Table of Contents

- [Pipeline Architecture](#pipeline-architecture)
- [Workflows](#workflows)
- [Setup Instructions](#setup-instructions)
- [Required Secrets](#required-secrets)
- [Testing Strategy](#testing-strategy)
- [Security Scanning](#security-scanning)
- [Deployment Process](#deployment-process)
- [Troubleshooting](#troubleshooting)

---

## Pipeline Architecture

### Workflow Files

```
.github/workflows/
├── ci.yml              # Main CI/CD pipeline (test, lint, build, deploy)
├── docker-build.yml    # Docker image building and scanning
└── security-scan.yml   # Comprehensive security scanning
```

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────┐
│                       CI/CD PIPELINE                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. CODE QUALITY                                                │
│     ├─ Black (formatting)                                       │
│     ├─ isort (import sorting)                                   │
│     ├─ Flake8 (style guide)                                     │
│     ├─ Pylint (code analysis)                                   │
│     └─ mypy (type checking)                                     │
│                                                                 │
│  2. SECURITY SCANNING                                           │
│     ├─ Bandit (security linter)                                 │
│     ├─ Safety (dependency vulnerabilities)                      │
│     ├─ pip-audit (dependency audit)                             │
│     └─ CodeQL (advanced static analysis)                        │
│                                                                 │
│  3. TESTING                                                     │
│     ├─ Django system checks                                     │
│     ├─ Database migrations                                      │
│     ├─ Pytest (unit + integration)                              │
│     ├─ Coverage report (target: 75%+)                           │
│     └─ Codecov upload                                           │
│                                                                 │
│  4. DOCKER BUILD                                                │
│     ├─ Build Django image                                       │
│     ├─ Build Celery image                                       │
│     ├─ Trivy security scan                                      │
│     ├─ Dockle best practices                                    │
│     └─ Push to registry                                         │
│                                                                 │
│  5. DEPLOYMENT                                                  │
│     ├─ Deploy to Staging (develop branch)                       │
│     ├─ Run smoke tests                                          │
│     ├─ Deploy to Production (main branch, manual approval)      │
│     └─ Create GitHub release                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workflows

### 1. Main CI/CD Pipeline (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main`

**Jobs:**

#### 1.1 Lint & Code Quality
- Runs: Black, isort, Flake8, Pylint, mypy
- Fails on: Formatting errors, style violations, type errors
- Artifacts: Lint results

#### 1.2 Security Scanning
- Runs: Bandit, Safety, pip-audit
- Continues on error (reports issues but doesn't block)
- Artifacts: Security reports (JSON)

#### 1.3 Tests & Coverage
- Services: PostgreSQL 15, Redis 7
- Runs: Django checks, migrations, pytest
- Coverage threshold: 70% minimum, 75% target
- Uploads: Coverage to Codecov
- Artifacts: Coverage HTML, XML, JUnit reports

#### 1.4 Build & Scan Docker Images
- Builds: Django + Celery images
- Scans: Trivy vulnerability scanner
- Uploads: Scan results to GitHub Security
- Push: Only on non-PR events

#### 1.5 Deploy to Staging
- Triggers: Push to `develop` branch
- Deploys: Via SSH to staging server
- Verifies: Health checks
- Environment: `staging`

#### 1.6 Deploy to Production
- Triggers: Push to `main` branch
- Requires: Manual approval (GitHub environment)
- Deploys: Via SSH to production server
- Creates: GitHub release
- Rollback: Automatic on failure
- Environment: `production`

#### 1.7 Performance Testing (Optional)
- Triggers: Pull requests only
- Tools: Locust (load testing)
- Artifacts: Performance reports

---

### 2. Docker Build & Security Scan (`docker-build.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main`
- Tags matching `v*`
- Weekly schedule (Monday 3 AM UTC)
- Manual workflow dispatch

**Jobs:**

#### 2.1 Build Django Image
- Multi-platform: linux/amd64, linux/arm64
- Security scans: Trivy, Dockle
- Tests: Python version, Django version
- Tags: branch, PR, semver, SHA, latest
- Uploads: SARIF to GitHub Security

#### 2.2 Build Celery Image
- Same process as Django image
- Separate vulnerability scanning
- Independent tagging

#### 2.3 Analyze Image Sizes
- Runs: On pull requests
- Tools: docker history, Dive
- Helps: Monitor image bloat

---

### 3. Security Scanning (`security-scan.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main`
- Daily schedule (2 AM UTC)
- Manual workflow dispatch

**Jobs:**

#### 3.1 Dependency Vulnerability Scan
- Tools: Safety, pip-audit
- Output: JSON reports, CycloneDX SBOM
- Artifacts: Vulnerability reports

#### 3.2 Static Application Security Testing (SAST)
- Tool: Bandit
- Scans: apps/, config/
- Output: SARIF (uploaded to GitHub Security)
- Severity: Medium and above

#### 3.3 CodeQL Analysis
- Language: Python
- Queries: Security and quality
- Integration: GitHub Security tab

#### 3.4 Secret Scanning
- Tools: Gitleaks, TruffleHog
- Scope: Full repository history
- Verified secrets only

#### 3.5 Docker Image Security
- Tools: Trivy, Grype (Anchore)
- Scans: OS packages, libraries
- Severity: Critical, High, Medium

#### 3.6 License Compliance
- Tool: pip-licenses
- Checks: GPL violations
- Output: JSON, Markdown reports

#### 3.7 SBOM Generation
- Format: CycloneDX, SPDX
- Attached to releases
- Retention: 90 days

---

## Setup Instructions

### 1. Local Development Setup

#### Install Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

#### Install Development Dependencies
```bash
# Testing dependencies
pip install -r requirements/test.txt

# Linting tools
pip install -r requirements/lint.txt
```

#### Run Tests Locally
```bash
# All tests with coverage
pytest --cov=apps --cov=config --cov-report=html

# Specific test categories
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Parallel testing
pytest -n auto
```

#### Run Linters Locally
```bash
# Format code
black apps/ config/ tests/
isort apps/ config/ tests/

# Check linting
flake8 apps/ config/ tests/
pylint apps/ config/
mypy apps/ config/

# Security scan
bandit -r apps/ config/
safety check
pip-audit
```

---

### 2. GitHub Repository Setup

#### Enable GitHub Features

1. **GitHub Actions**
   - Enable Actions in repository settings
   - Allow read/write permissions for workflows

2. **GitHub Security**
   - Enable Dependabot alerts
   - Enable Dependabot security updates
   - Enable Code scanning (CodeQL)
   - Enable Secret scanning

3. **Branch Protection**
   ```
   main branch:
   - Require pull request reviews
   - Require status checks to pass
   - Require branches to be up to date
   - Include administrators

   Status checks:
   - lint
   - security
   - test
   - build
   ```

---

## Required Secrets

### GitHub Secrets Configuration

Navigate to **Settings → Secrets and variables → Actions**

#### Docker Hub
```yaml
DOCKER_USERNAME: your-dockerhub-username
DOCKER_PASSWORD: your-dockerhub-token
```

#### Codecov (Optional)
```yaml
CODECOV_TOKEN: your-codecov-token
```

#### Staging Environment
```yaml
STAGING_HOST: staging.ganglioside.example.com
STAGING_USER: deploy
STAGING_SSH_KEY: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...
  -----END OPENSSH PRIVATE KEY-----
```

#### Production Environment
```yaml
PRODUCTION_HOST: ganglioside.example.com
PRODUCTION_USER: deploy
PRODUCTION_SSH_KEY: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  ...
  -----END OPENSSH PRIVATE KEY-----
```

#### Gitleaks (Optional)
```yaml
GITLEAKS_LICENSE: your-gitleaks-license-key
```

---

### GitHub Environment Setup

#### Create Environments

1. **Staging Environment**
   - Name: `staging`
   - URL: https://staging.ganglioside.example.com
   - Protection: None (auto-deploy on develop)

2. **Production Environment**
   - Name: `production`
   - URL: https://ganglioside.example.com
   - Protection:
     - Required reviewers (1-2 people)
     - Wait timer: 5 minutes
     - Deployment branches: main only

---

## Testing Strategy

### Coverage Requirements

- **Target**: 75%+
- **Minimum**: 70%
- **Fail below**: 70%

### Test Categories

```python
# Unit tests
@pytest.mark.unit
def test_regression_model():
    ...

# Integration tests
@pytest.mark.integration
def test_analysis_pipeline():
    ...

# Slow tests
@pytest.mark.slow
def test_full_dataset():
    ...

# End-to-end tests
@pytest.mark.e2e
def test_user_workflow():
    ...
```

### Running Tests

```bash
# All tests
pytest

# By marker
pytest -m unit
pytest -m integration
pytest -m "not slow"

# With coverage
pytest --cov=apps --cov-report=term-missing

# Parallel
pytest -n auto

# Verbose
pytest -vv

# Stop on first failure
pytest -x
```

---

## Security Scanning

### Security Tools Matrix

| Tool | Purpose | Scope | Frequency |
|------|---------|-------|-----------|
| **Bandit** | Python SAST | Code | Every commit |
| **Safety** | Dependency vulnerabilities | pip packages | Daily |
| **pip-audit** | Dependency audit | pip packages | Daily |
| **CodeQL** | Advanced SAST | Code | Every commit |
| **Gitleaks** | Secret detection | Git history | Every commit |
| **TruffleHog** | Secret detection | Git history | Every commit |
| **Trivy** | Container scanning | Docker images | Every build |
| **Grype** | Container scanning | Docker images | Every build |
| **Dockle** | Container best practices | Docker images | Every build |

### Viewing Security Results

1. **GitHub Security Tab**
   - Navigate to Security → Code scanning alerts
   - View Trivy, Bandit, CodeQL results

2. **Workflow Artifacts**
   - Download JSON/SARIF reports
   - Review detailed findings

3. **Dependabot**
   - Security → Dependabot alerts
   - Automated PR creation

---

## Deployment Process

### Deployment Flow

```
┌──────────────────────────────────────────────────────┐
│                  DEPLOYMENT FLOW                     │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Developer pushes to branch                          │
│         ↓                                            │
│  CI/CD runs (lint, test, build)                      │
│         ↓                                            │
│  ┌─────────────────┐      ┌────────────────────┐    │
│  │  develop branch │      │    main branch     │    │
│  │       ↓         │      │        ↓           │    │
│  │  Auto-deploy    │      │  Manual approval   │    │
│  │  to Staging     │      │        ↓           │    │
│  │       ↓         │      │  Deploy to Prod    │    │
│  │  Smoke tests    │      │        ↓           │    │
│  └─────────────────┘      │  Create release    │    │
│                           │        ↓           │    │
│                           │  Smoke tests       │    │
│                           │        ↓           │    │
│                           │  Rollback if fail  │    │
│                           └────────────────────┘    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Deployment Checklist

#### Pre-deployment
- [ ] All tests passing
- [ ] Code review approved
- [ ] Security scans clean
- [ ] Docker images built
- [ ] Database migrations tested

#### Staging Deployment
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Manual QA testing
- [ ] Performance testing

#### Production Deployment
- [ ] Create deployment PR
- [ ] Get approval from reviewers
- [ ] Schedule maintenance window
- [ ] Deploy to production
- [ ] Monitor logs
- [ ] Verify health checks
- [ ] Rollback plan ready

---

## Troubleshooting

### Common Issues

#### 1. Tests Failing in CI but Passing Locally

**Cause**: Environment differences

**Solution**:
```bash
# Use CI environment variables locally
export DJANGO_SETTINGS_MODULE=config.settings.development
export DATABASE_URL=postgresql://test_user:test_password@localhost:5432/ganglioside_test

# Run tests
pytest
```

#### 2. Docker Build Failing

**Cause**: Cache issues, dependency conflicts

**Solution**:
```bash
# Clear build cache
docker builder prune -af

# Build without cache
docker build --no-cache -t ganglioside:test .

# Check Dockerfile syntax
docker build --check .
```

#### 3. Coverage Threshold Not Met

**Cause**: New code without tests

**Solution**:
```bash
# Check coverage report
pytest --cov=apps --cov-report=term-missing

# Identify untested code
coverage html
open htmlcov/index.html
```

#### 4. Security Scan Blocking Deployment

**Cause**: Vulnerabilities detected

**Solution**:
```bash
# Check specific vulnerabilities
safety check --full-report
pip-audit --desc

# Update dependencies
pip-audit --fix

# Create exception if false positive
# Add to .bandit config or safety policy
```

#### 5. Deployment SSH Failures

**Cause**: SSH key issues, network problems

**Solution**:
```bash
# Test SSH connection
ssh -i deploy_key deploy@staging.example.com

# Check SSH key format (must be OpenSSH)
ssh-keygen -p -m PEM -f deploy_key

# Verify secret in GitHub
```

---

## Workflow Status Badges

Add to README.md:

```markdown
[![CI/CD Pipeline](https://github.com/username/ganglioside/actions/workflows/ci.yml/badge.svg)](https://github.com/username/ganglioside/actions/workflows/ci.yml)
[![Docker Build](https://github.com/username/ganglioside/actions/workflows/docker-build.yml/badge.svg)](https://github.com/username/ganglioside/actions/workflows/docker-build.yml)
[![Security Scan](https://github.com/username/ganglioside/actions/workflows/security-scan.yml/badge.svg)](https://github.com/username/ganglioside/actions/workflows/security-scan.yml)
[![codecov](https://codecov.io/gh/username/ganglioside/branch/main/graph/badge.svg)](https://codecov.io/gh/username/ganglioside)
```

---

## Best Practices

### For Developers

1. **Run pre-commit hooks** before pushing
2. **Write tests** for all new code (aim for 80%+ coverage)
3. **Keep dependencies updated** via Dependabot
4. **Review security alerts** promptly
5. **Test locally** before creating PR

### For CI/CD

1. **Fail fast** - Run quick checks first
2. **Cache dependencies** for faster builds
3. **Parallel execution** where possible
4. **Artifacts retention** - Balance cost vs history
5. **Notifications** - Set up Slack/email alerts

### For Security

1. **Automated scanning** on every commit
2. **Regular updates** via scheduled workflows
3. **SBOM generation** for compliance
4. **Secret rotation** every 90 days
5. **Audit logs** - Review deployment history

---

## Metrics & Monitoring

### Key Metrics

- **Build time**: Target < 10 minutes
- **Test coverage**: Target 75%+
- **Security vulnerabilities**: Target 0 high/critical
- **Deployment frequency**: Track via GitHub Insights
- **Failure rate**: Monitor in Actions tab

### Monitoring Tools

- GitHub Actions dashboard
- Codecov reports
- GitHub Security tab
- Docker Hub repository
- Deployment logs

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Django Testing Guide](https://docs.djangoproject.com/en/5.0/topics/testing/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

---

**Last Updated**: 2025-11-18
**Version**: 1.0
**Maintainer**: Development Team
