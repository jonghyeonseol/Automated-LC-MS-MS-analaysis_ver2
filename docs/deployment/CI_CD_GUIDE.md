# CI/CD Pipeline Guide
## Ganglioside Analysis Platform

**Version:** 2.0
**Last Updated:** 2025-10-21

---

## Overview

The CI/CD pipeline automates testing, building, and deployment using **GitHub Actions**. Every push to `main` or `develop` branches triggers the pipeline.

---

## Pipeline Stages

### 1. Code Quality Checks (Lint Job)

**Runs on:** Every push and pull request

**Tools:**
- **Black** - Code formatting
- **isort** - Import sorting
- **Flake8** - Code linting

**Commands:**
```bash
# Run locally
make lint

# Auto-fix issues
make format
```

**Configuration:**
- `.flake8` - Flake8 rules
- `pyproject.toml` - Black and isort settings

---

### 2. Security Scanning (Security Job)

**Runs on:** Every push and pull request

**Tools:**
- **Bandit** - Python security linter
- **Safety** - Dependency vulnerability scanner

**What it checks:**
- SQL injection vulnerabilities
- Hardcoded secrets
- Insecure dependencies
- Known CVEs in packages

**Reports:**
- Uploaded as GitHub Actions artifacts
- Available in the Actions tab

---

### 3. Automated Testing (Test Job)

**Runs on:** Every push and pull request

**Services:**
- PostgreSQL 15 (test database)
- Redis 7 (cache/broker)

**Test Coverage:**
- Minimum required: 70%
- Target: 80%+

**Commands:**
```bash
# Run locally
make test

# With coverage
make coverage
```

**Outputs:**
- Coverage report (HTML + XML)
- Test results
- Performance metrics

---

### 4. Docker Image Build (Build Job)

**Runs on:** Pushes to main/develop (after tests pass)

**Images built:**
1. `ganglioside:latest` - Django application
2. `ganglioside-celery:latest` - Celery worker

**Registry:**
- Docker Hub (configurable)
- GitHub Container Registry (alternative)

**Image optimization:**
- Multi-stage builds (reduces size by 60%)
- Layer caching via GitHub Actions cache
- Security scanning built-in

---

### 5. Production Deployment (Deploy Job)

**Runs on:** Pushes to `main` branch only

**Process:**
1. SSH into production server
2. Pull latest code from Git
3. Run deployment script
4. Verify health endpoint

**Requirements:**
- Production server accessible via SSH
- GitHub Secrets configured (see below)

---

## GitHub Secrets Configuration

Navigate to **Settings → Secrets and variables → Actions** and add:

### Required Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `DOCKER_USERNAME` | Docker Hub username | `youruser` |
| `DOCKER_PASSWORD` | Docker Hub password/token | `dckr_pat_xxxxx` |
| `DEPLOY_HOST` | Production server hostname | `prod.example.com` |
| `DEPLOY_USER` | SSH username | `ganglioside` |
| `DEPLOY_SSH_KEY` | Private SSH key | `-----BEGIN RSA...` |

### Optional Secrets

| Secret Name | Description |
|------------|-------------|
| `SENTRY_DSN` | Sentry error tracking DSN |
| `SLACK_WEBHOOK` | Slack notification webhook |

---

## Workflow File

Location: `.github/workflows/ci-cd.yml`

### Trigger Conditions

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
```

### Job Dependencies

```
Lint ────────┐
             ├──→ Build ──→ Deploy (main only)
Security ────┤
             │
Test ────────┘
```

---

## Local Testing

### Run Linting

```bash
# Check formatting
black --check .

# Check imports
isort --check-only .

# Check code quality
flake8 .
```

### Run Security Checks

```bash
# Install tools
pip install bandit safety

# Run Bandit
bandit -r apps/ config/

# Check dependencies
safety check
```

### Run Tests

```bash
# Using Docker
make test

# Using local Python
pytest

# With coverage
pytest --cov=apps --cov=config --cov-report=html
```

---

## Deployment Process

### Automatic Deployment

**Triggered by:** Push to `main` branch

**Steps:**
1. ✅ All tests pass
2. ✅ Docker images built
3. 🚀 SSH to production server
4. 📥 Pull latest code
5. 🔄 Run migrations
6. 📦 Collect static files
7. ♻️ Restart services
8. ✅ Health check verification

### Manual Deployment

```bash
# On production server
cd /var/www/ganglioside
sudo ./deployment/scripts/deploy.sh
```

---

## Monitoring Pipeline

### View Pipeline Status

GitHub Actions tab shows:
- ✅ Passing jobs (green checkmark)
- ❌ Failed jobs (red X)
- ⏳ Running jobs (yellow circle)

### View Logs

1. Go to **Actions** tab
2. Click on workflow run
3. Click on job name
4. Expand steps to see detailed logs

### Download Artifacts

Available artifacts:
- Test coverage reports (HTML)
- Security scan results (JSON)
- Performance test results

---

## Branch Protection Rules

**Recommended settings for `main` branch:**

1. Go to **Settings → Branches → Branch protection rules**
2. Add rule for `main`
3. Enable:
   - ✅ Require pull request reviews
   - ✅ Require status checks to pass
   - ✅ Require branches to be up to date
   - ✅ Include administrators

**Required status checks:**
- `Code Quality Checks`
- `Tests (Django + PostgreSQL + Redis)`

---

## Rollback Procedure

### Automatic Rollback

If health check fails after deployment, manually rollback:

```bash
# SSH to production
ssh ganglioside@prod.example.com

# Revert to previous commit
cd /var/www/ganglioside
git log --oneline -5  # Find previous commit
git reset --hard <previous-commit-hash>

# Redeploy
sudo ./deployment/scripts/deploy.sh
```

### Database Rollback

```bash
# Restore from backup
gunzip < /var/backups/ganglioside/db_YYYYMMDD.sql.gz | \
    sudo -u postgres psql ganglioside_prod
```

---

## Performance Optimization

### Parallel Jobs

Jobs run in parallel when possible:

```
Lint (2 min) ────┐
                 ├──→ Build (5 min) ──→ Deploy (3 min)
Security (3 min) │
                 │
Test (8 min) ────┘
```

**Total time:** ~18 minutes (vs 23 minutes sequential)

### Caching

Caching speeds up builds by 50%:

```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

**Cached items:**
- Python packages
- Docker layers
- npm modules (if frontend added)

---

## Troubleshooting

### Pipeline Fails on Lint

**Error:** "Black would reformat X files"

**Fix:**
```bash
# Format code locally
make format

# Commit changes
git add .
git commit -m "Apply code formatting"
git push
```

### Pipeline Fails on Tests

**Error:** "Test coverage below 70%"

**Fix:**
```bash
# Run coverage locally
make coverage

# Add tests to increase coverage
# Target untested files shown in report
```

### Pipeline Fails on Build

**Error:** "Docker build failed"

**Fix:**
```bash
# Test Docker build locally
docker-compose build

# Check Dockerfile syntax
# Verify all COPY paths exist
```

### Deployment Fails

**Error:** "SSH connection failed"

**Fix:**
1. Verify `DEPLOY_SSH_KEY` secret is correct
2. Check server firewall allows SSH
3. Verify `DEPLOY_USER` has permissions

**Error:** "Health check failed"

**Fix:**
```bash
# SSH to server
ssh ganglioside@prod.example.com

# Check service status
sudo systemctl status ganglioside-django

# View logs
sudo journalctl -u ganglioside-django -n 50
```

---

## Best Practices

### Commit Messages

Use conventional commits:
```
feat: add CSV export functionality
fix: resolve PostgreSQL connection timeout
chore: update dependencies
docs: improve deployment guide
test: add integration tests for analysis service
```

### Pull Request Workflow

1. Create feature branch from `develop`
2. Make changes and commit
3. Push and create PR to `develop`
4. Wait for CI checks to pass
5. Request code review
6. Merge after approval
7. Delete feature branch

### Release Process

1. Merge `develop` → `main`
2. Tag release: `git tag v1.0.0`
3. Push tags: `git push --tags`
4. Automatic deployment to production
5. Monitor health checks

---

## Metrics & Reporting

### Pipeline Metrics

Track in GitHub Insights:
- Average pipeline duration
- Success rate
- Failed job frequency
- Deployment frequency

### Coverage Trends

Monitor test coverage over time:
- Target: 80%+ coverage
- Minimum: 70% (enforced by CI)
- Review coverage reports in artifacts

---

## Advanced Configuration

### Matrix Builds

Test against multiple Python versions:

```yaml
strategy:
  matrix:
    python-version: [3.9, 3.10, 3.11]
```

### Scheduled Runs

Run security scans nightly:

```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily
```

### Environment-Specific Deployments

```yaml
deploy-staging:
  if: github.ref == 'refs/heads/develop'
  environment: staging

deploy-production:
  if: github.ref == 'refs/heads/main'
  environment: production
```

---

## Additional Resources

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **Docker Build Best Practices:** https://docs.docker.com/develop/dev-best-practices/
- **Python Testing Guide:** https://docs.pytest.org/
- **Security Best Practices:** https://owasp.org/

---

**Last Updated:** 2025-10-21
