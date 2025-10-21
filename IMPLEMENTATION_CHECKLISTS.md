# Implementation Checklists - Django Ganglioside Platform

**Purpose**: Step-by-step checklists for implementing remaining features
**Reference Documents**:
- `ADVANCED_FEATURES_SETUP.md`
- `PRODUCTION_DEPLOYMENT_GUIDE.md`
- `UPDATED_DEVELOPMENT_PLAN.md`

---

## Table of Contents

1. [Django Channels Checklist](#django-channels-checklist)
2. [Celery Checklist](#celery-checklist)
3. [PostgreSQL Migration Checklist](#postgresql-migration-checklist)
4. [Production Deployment Checklist](#production-deployment-checklist)
5. [Testing Checklist](#testing-checklist)
6. [Security Hardening Checklist](#security-hardening-checklist)
7. [CI/CD Pipeline Checklist](#cicd-pipeline-checklist)

---

## Django Channels Checklist

### Prerequisites
- [ ] Redis installed and running
- [ ] Django application working
- [ ] Terminal access with pip

### Installation (15 minutes)
- [ ] Activate virtual environment
- [ ] Install channels: `pip install channels[daphne]==4.0.0`
- [ ] Install channels-redis: `pip install channels-redis==4.1.0`
- [ ] Update requirements: `pip freeze > requirements/production.txt`
- [ ] Test Redis: `redis-cli ping` → Should return "PONG"

### Configuration (30 minutes)
- [ ] Add `'daphne'` to INSTALLED_APPS (first position in list)
- [ ] Set `ASGI_APPLICATION = 'config.asgi.application'` in settings
- [ ] Add CHANNEL_LAYERS configuration with Redis URL
- [ ] Run `python manage.py check` → Should pass

### ASGI Setup (20 minutes)
- [ ] Edit `config/asgi.py`
- [ ] Import: ProtocolTypeRouter, URLRouter, AuthMiddlewareStack, AllowedHostsOriginValidator
- [ ] Create protocol router with HTTP and WebSocket handlers
- [ ] Test import: `python -c "from config.asgi import application"`

### WebSocket Consumer (45 minutes)
- [ ] Create `apps/analysis/consumers.py`
- [ ] Import AsyncWebsocketConsumer
- [ ] Create AnalysisProgressConsumer class
- [ ] Implement connect() - join room group, accept connection
- [ ] Implement disconnect() - leave room group
- [ ] Implement analysis_progress() - send progress update
- [ ] Implement analysis_complete() - send completion message
- [ ] Implement analysis_error() - send error message

### Routing (10 minutes)
- [ ] Create `apps/analysis/routing.py`
- [ ] Import re_path and consumers
- [ ] Define websocket_urlpatterns with route: `ws/analysis/(?P<session_id>\d+)/$`
- [ ] Link to AnalysisProgressConsumer.as_asgi()

### Service Integration (30 minutes)
- [ ] Edit `apps/analysis/services/analysis_service.py`
- [ ] Import get_channel_layer, async_to_sync, timezone
- [ ] Create _send_progress(session_id, message, percentage, step)
- [ ] Create _send_complete(session_id, success, redirect_url)
- [ ] Create _send_error(session_id, error_message)
- [ ] Update run_analysis() to call progress methods at key points

### Frontend (30 minutes)
- [ ] Edit `templates/analysis/session_detail.html`
- [ ] Add progress bar HTML with id="progressBar"
- [ ] Add progress message div with id="progressMessage"
- [ ] Create WebSocket connection in JavaScript
- [ ] Implement onmessage handler to update progress bar
- [ ] Implement onclose handler for fallback
- [ ] Implement onerror handler

### Testing (30 minutes)
- [ ] Start Daphne: `daphne -b 0.0.0.0 -p 8000 config.asgi:application`
- [ ] Open browser to session detail page
- [ ] Open browser dev tools Network tab (filter: WS)
- [ ] Upload and analyze a file
- [ ] Verify WebSocket connection established
- [ ] Verify progress messages received
- [ ] Verify progress bar updates
- [ ] Verify automatic redirect on completion

### Troubleshooting
- [ ] If WebSocket fails: Check ASGI routing in config/asgi.py
- [ ] If no messages: Verify channel layer in Django shell
- [ ] If connection drops: Check Redis is running
- [ ] If progress not updating: Check _send_progress calls in service

**Total Time**: ~3-4 hours

---

## Celery Checklist

### Prerequisites
- [ ] Redis installed and running
- [ ] Django application working
- [ ] Virtual environment activated

### Installation (15 minutes)
- [ ] Install celery: `pip install celery[redis]==5.3.4`
- [ ] Install beat: `pip install django-celery-beat==2.5.0`
- [ ] Install results: `pip install django-celery-results==2.5.1`
- [ ] Install flower: `pip install flower==2.0.1`
- [ ] Update requirements

### Configuration (20 minutes)
- [ ] Uncomment `config/celery.py` (already exists)
- [ ] Verify app = Celery('ganglioside')
- [ ] Check autodiscover_tasks()
- [ ] Add beat_schedule for periodic tasks
- [ ] Uncomment celery imports in `config/__init__.py`

### Settings Update (15 minutes)
- [ ] Add `'django_celery_beat'` to INSTALLED_APPS
- [ ] Add `'django_celery_results'` to INSTALLED_APPS
- [ ] Verify CELERY_BROKER_URL points to Redis
- [ ] Verify CELERY_RESULT_BACKEND = 'django-db'
- [ ] Run migrations: `python manage.py migrate`

### Create Tasks (45 minutes)
- [ ] Create `apps/analysis/tasks.py`
- [ ] Import shared_task, timezone, AnalysisSession, AnalysisService
- [ ] Create run_analysis_async(session_id):
  - [ ] Get session object
  - [ ] Update status to 'processing'
  - [ ] Store celery_task_id
  - [ ] Run analysis with service
  - [ ] Update status to 'completed' or 'failed'
  - [ ] Return result dict
- [ ] Create cleanup_old_sessions(days=30):
  - [ ] Calculate cutoff date
  - [ ] Filter old sessions
  - [ ] Delete old sessions
  - [ ] Return count
- [ ] Create send_analysis_notification(session_id, email):
  - [ ] Get session
  - [ ] Compose email message
  - [ ] Send email
  - [ ] Return success

### ViewSet Integration (20 minutes)
- [ ] Edit `apps/analysis/views.py`
- [ ] Import run_analysis_async from tasks
- [ ] Update analyze action:
  - [ ] Check session status
  - [ ] Queue task with .delay()
  - [ ] Store task.id in session
  - [ ] Update status to 'pending'
  - [ ] Return 202 Accepted with task_id

### Testing (30 minutes)
- [ ] Terminal 1: Start Django: `python manage.py runserver`
- [ ] Terminal 2: Start worker: `celery -A config worker -l info`
- [ ] Terminal 3: Start beat: `celery -A config beat -l info`
- [ ] Terminal 4: Start flower: `celery -A config flower`
- [ ] Open flower: http://localhost:5555
- [ ] Queue a task via API or web UI
- [ ] Monitor task in Flower
- [ ] Verify task completes
- [ ] Check database for results
- [ ] Test periodic task manually
- [ ] Test error handling (invalid session ID)

### Production Setup (30 minutes)
- [ ] Create systemd service for worker (see PRODUCTION_DEPLOYMENT_GUIDE.md)
- [ ] Create systemd service for beat
- [ ] Create log directories
- [ ] Test systemd services
- [ ] Configure log rotation

**Total Time**: ~3-4 hours

---

## PostgreSQL Migration Checklist

### Prerequisites
- [ ] PostgreSQL installed on system
- [ ] Current SQLite database working
- [ ] Backup of all data

### Installation (15 minutes)
**macOS**:
- [ ] Install: `brew install postgresql`
- [ ] Start service: `brew services start postgresql`

**Linux**:
- [ ] Install: `sudo apt install postgresql postgresql-contrib libpq-dev`
- [ ] Start service: `sudo systemctl start postgresql`

- [ ] Verify: `psql --version`

### Database Creation (20 minutes)
- [ ] Switch to postgres user: `sudo -u postgres psql`
- [ ] Create database:
  ```sql
  CREATE DATABASE ganglioside_db;
  ```
- [ ] Create user:
  ```sql
  CREATE USER ganglioside_user WITH PASSWORD 'your_secure_password';
  ```
- [ ] Grant privileges:
  ```sql
  ALTER ROLE ganglioside_user SET client_encoding TO 'utf8';
  ALTER ROLE ganglioside_user SET default_transaction_isolation TO 'read committed';
  ALTER ROLE ganglioside_user SET timezone TO 'UTC';
  GRANT ALL PRIVILEGES ON DATABASE ganglioside_db TO ganglioside_user;
  ```
- [ ] Exit psql: `\q`
- [ ] Test connection: `psql -U ganglioside_user -d ganglioside_db -h localhost`

### Django Configuration (15 minutes)
- [ ] Install psycopg2: `pip install psycopg2-binary`
- [ ] Create/update `.env` file with:
  ```
  DB_NAME=ganglioside_db
  DB_USER=ganglioside_user
  DB_PASSWORD=your_secure_password
  DB_HOST=localhost
  DB_PORT=5432
  ```
- [ ] Update `config/settings/base.py` DATABASES to use PostgreSQL
- [ ] Test configuration: `python manage.py check --database default`

### Data Backup (20 minutes)
- [ ] Backup SQLite data:
  ```bash
  python manage.py dumpdata > backup_$(date +%Y%m%d).json
  ```
- [ ] Copy SQLite file:
  ```bash
  cp db.sqlite3 db.sqlite3.backup_$(date +%Y%m%d)
  ```
- [ ] Verify backup file size (should be >0 bytes)
- [ ] Count records in backup:
  ```bash
  grep -c "model" backup_*.json
  ```

### Migration (30 minutes)
- [ ] Run migrations on PostgreSQL:
  ```bash
  python manage.py migrate
  ```
- [ ] Create superuser:
  ```bash
  python manage.py createsuperuser
  ```
- [ ] Load data from backup:
  ```bash
  python manage.py loaddata backup_*.json
  ```
- [ ] Check for errors in output

### Verification (20 minutes)
- [ ] Start server: `python manage.py runserver`
- [ ] Check counts in Django shell:
  ```python
  from apps.analysis.models import *
  AnalysisSession.objects.count()
  Compound.objects.count()
  RegressionModel.objects.count()
  ```
- [ ] Compare counts to SQLite
- [ ] Login to admin panel
- [ ] Browse records
- [ ] Run a test analysis
- [ ] Verify results saved
- [ ] Check analysis history

### Performance Tuning (15 minutes)
- [ ] Create database indexes (already in models)
- [ ] Configure connection pooling if needed
- [ ] Test query performance
- [ ] Monitor slow queries

### Troubleshooting
- [ ] If migration fails: Check PostgreSQL service running
- [ ] If authentication fails: Verify password in .env
- [ ] If data load fails: Check for model conflicts
- [ ] If performance slow: Add database indexes

**Total Time**: ~2-3 hours

---

## Production Deployment Checklist

### Server Preparation (30 minutes)
- [ ] Ubuntu 22.04 server provisioned
- [ ] SSH access configured
- [ ] Sudo privileges available
- [ ] Domain name configured (optional)

### System Updates (15 minutes)
- [ ] Update system: `sudo apt update && sudo apt upgrade -y`
- [ ] Install Python: `sudo apt install python3.9 python3.9-venv python3-pip`
- [ ] Install PostgreSQL: `sudo apt install postgresql postgresql-contrib libpq-dev`
- [ ] Install Nginx: `sudo apt install nginx`
- [ ] Install Redis: `sudo apt install redis-server`
- [ ] Install build tools: `sudo apt install build-essential git curl`

### User Setup (10 minutes)
- [ ] Create user: `sudo adduser ganglioside`
- [ ] Add to sudo: `sudo usermod -aG sudo ganglioside`
- [ ] Switch to user: `su - ganglioside`

### Application Setup (30 minutes)
- [ ] Clone repository
- [ ] Create virtual environment
- [ ] Install requirements: `pip install -r requirements/production.txt`
- [ ] Create `.env.production` with all variables
- [ ] Set environment variables

### Database Setup (20 minutes)
- [ ] Create PostgreSQL database
- [ ] Create database user
- [ ] Grant privileges
- [ ] Run migrations
- [ ] Create superuser

### Static Files (15 minutes)
- [ ] Create static directory: `/home/ganglioside/static`
- [ ] Create media directory: `/home/ganglioside/media`
- [ ] Collect static files: `python manage.py collectstatic`
- [ ] Set permissions

### Gunicorn Setup (20 minutes)
- [ ] Install: `pip install gunicorn`
- [ ] Create gunicorn_config.py
- [ ] Test Gunicorn: `gunicorn config.wsgi:application --bind 0.0.0.0:8000`
- [ ] Create systemd service
- [ ] Enable and start service

### Nginx Configuration (30 minutes)
- [ ] Create nginx config file
- [ ] Configure upstream
- [ ] Configure static/media serving
- [ ] Configure proxy pass
- [ ] Test config: `sudo nginx -t`
- [ ] Enable site
- [ ] Restart Nginx

### SSL Certificate (20 minutes)
- [ ] Install certbot: `sudo apt install certbot python3-certbot-nginx`
- [ ] Obtain certificate: `sudo certbot --nginx -d yourdomain.com`
- [ ] Test auto-renewal: `sudo certbot renew --dry-run`

### Celery Services (30 minutes)
- [ ] Create systemd service for worker
- [ ] Create systemd service for beat
- [ ] Create log directories
- [ ] Enable services
- [ ] Start services
- [ ] Verify running

### Firewall (15 minutes)
- [ ] Install UFW: `sudo apt install ufw`
- [ ] Allow SSH: `sudo ufw allow 22`
- [ ] Allow HTTP: `sudo ufw allow 80`
- [ ] Allow HTTPS: `sudo ufw allow 443`
- [ ] Enable: `sudo ufw enable`

### Monitoring Setup (30 minutes)
- [ ] Configure Django logging
- [ ] Set up log rotation
- [ ] Install fail2ban: `sudo apt install fail2ban`
- [ ] Configure fail2ban
- [ ] Test error tracking

### Final Verification (30 minutes)
- [ ] Website accessible via HTTPS
- [ ] Static files loading
- [ ] Media uploads working
- [ ] Admin panel accessible
- [ ] API endpoints functional
- [ ] WebSocket connections working
- [ ] Celery tasks processing
- [ ] Database queries fast
- [ ] All services running

**Total Time**: 6-8 hours

---

## Testing Checklist

### Unit Tests (>80% coverage)

**Algorithm Tests**:
- [ ] Test GangliosideProcessor.process_data()
- [ ] Test each rule function separately
- [ ] Test edge cases (empty data, invalid format)
- [ ] Test error handling

**Serializer Tests**:
- [ ] Test AnalysisSessionSerializer validation
- [ ] Test CompoundSerializer
- [ ] Test RegressionModelSerializer
- [ ] Test create/update operations

**ViewSet Tests**:
- [ ] Test AnalysisSessionViewSet CRUD
- [ ] Test analyze action
- [ ] Test results action
- [ ] Test export action
- [ ] Test permissions

**Service Tests**:
- [ ] Test AnalysisService.run_analysis()
- [ ] Test ExportService
- [ ] Test error handling
- [ ] Test transaction rollback

**Celery Task Tests**:
- [ ] Test run_analysis_async
- [ ] Test cleanup_old_sessions
- [ ] Test error handling
- [ ] Test retries

### Integration Tests

**Complete Workflow**:
- [ ] Upload CSV → Analyze → View Results
- [ ] Test with multiple file types
- [ ] Test with large files
- [ ] Test concurrent analyses

**API Tests**:
- [ ] Test authentication
- [ ] Test all endpoints
- [ ] Test error responses
- [ ] Test pagination

**WebSocket Tests**:
- [ ] Test connection
- [ ] Test message delivery
- [ ] Test reconnection
- [ ] Test multiple connections

### Performance Tests

**Load Testing**:
- [ ] 10 concurrent analyses
- [ ] 100 concurrent API requests
- [ ] Large dataset (1000+ compounds)
- [ ] Database query performance

**Benchmarks**:
- [ ] Analysis execution time
- [ ] API response times
- [ ] WebSocket latency
- [ ] Database query times

### Coverage Report

- [ ] Run: `pytest --cov=apps --cov-report=html`
- [ ] Check coverage >80%
- [ ] Identify untested code
- [ ] Add tests for gaps

**Total Time**: 12-16 hours

---

## Security Hardening Checklist

### Django Security Settings
- [ ] DEBUG = False
- [ ] SECRET_KEY is long and random
- [ ] ALLOWED_HOSTS properly configured
- [ ] SECURE_SSL_REDIRECT = True
- [ ] SESSION_COOKIE_SECURE = True
- [ ] CSRF_COOKIE_SECURE = True
- [ ] SECURE_HSTS_SECONDS = 31536000
- [ ] SECURE_BROWSER_XSS_FILTER = True
- [ ] SECURE_CONTENT_TYPE_NOSNIFF = True
- [ ] X_FRAME_OPTIONS = 'DENY'

### Server Security
- [ ] SSH key-based authentication only
- [ ] Disable root SSH login
- [ ] Firewall (UFW) enabled
- [ ] Fail2ban installed and configured
- [ ] Regular security updates configured
- [ ] Non-root user for application

### Application Security
- [ ] SQL injection prevention (ORM usage)
- [ ] XSS prevention (template escaping)
- [ ] CSRF protection enabled
- [ ] File upload validation
- [ ] Rate limiting configured
- [ ] Input validation on all forms

### Database Security
- [ ] PostgreSQL password strong
- [ ] Database user limited privileges
- [ ] Connection encryption (SSL)
- [ ] Regular backups
- [ ] Backup encryption

### Monitoring
- [ ] Error logging configured
- [ ] Security event logging
- [ ] Failed login tracking
- [ ] Suspicious activity alerts

**Total Time**: 4-6 hours

---

## CI/CD Pipeline Checklist

### Docker Setup
- [ ] Create Dockerfile for Django app
- [ ] Create Dockerfile for Celery worker
- [ ] Create Dockerfile for Nginx (optional)
- [ ] Create docker-compose.yml for development
- [ ] Create docker-compose.prod.yml for production
- [ ] Test Docker build locally
- [ ] Test Docker Compose locally

### GitHub Actions
- [ ] Create `.github/workflows/test.yml`:
  - [ ] Checkout code
  - [ ] Set up Python
  - [ ] Install dependencies
  - [ ] Run tests
  - [ ] Upload coverage
- [ ] Create `.github/workflows/lint.yml`:
  - [ ] Run flake8
  - [ ] Run black --check
  - [ ] Run bandit (security)
- [ ] Create `.github/workflows/deploy.yml`:
  - [ ] Build Docker images
  - [ ] Push to registry
  - [ ] Deploy to staging (automatic)
  - [ ] Deploy to production (manual approval)

### Container Registry
- [ ] Set up Docker Hub or GitHub Container Registry
- [ ] Create repository secrets
- [ ] Test image push
- [ ] Test image pull

### Deployment Automation
- [ ] Create deploy script
- [ ] Set up staging environment
- [ ] Test automated deployment
- [ ] Create rollback procedure

**Total Time**: 8-12 hours

---

## Quick Reference

### Time Estimates Summary

| Task | Estimated Time |
|------|----------------|
| Django Channels | 3-4 hours |
| Celery | 3-4 hours |
| PostgreSQL Migration | 2-3 hours |
| Production Deployment | 6-8 hours |
| Comprehensive Testing | 12-16 hours |
| Security Hardening | 4-6 hours |
| CI/CD Pipeline | 8-12 hours |
| **Total** | **38-53 hours** |

### Priority Order

1. Django Channels (real-time progress)
2. Celery (background tasks)
3. PostgreSQL (production database)
4. Testing (quality assurance)
5. Production Deployment
6. Security Hardening
7. CI/CD Pipeline

---

**Last Updated**: 2025-10-21
**Status**: Ready to Use
**Version**: 1.0
