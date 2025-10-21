# Week 2 Implementation Plan - Advanced Features

**Dates**: Days 6-10 (2 working weeks from 2025-10-21)
**Goal**: Implement Django Channels (WebSocket) + Celery (Background Tasks)
**Prerequisites**: Redis installation
**Reference**: `ADVANCED_FEATURES_SETUP.md`

---

## Overview

Week 2 focuses on implementing advanced features that enhance the user experience and system scalability:

1. **Django Channels**: Real-time WebSocket updates during analysis
2. **Celery**: Background task processing for async analyses
3. **PostgreSQL**: Production-ready database migration
4. **Integration Testing**: Ensure all components work together

---

## Prerequisites Checklist

Before starting Week 2:

- [x] Week 1 algorithm validation complete (R² ≥ 0.90)
- [x] Django migration complete
- [x] System verified and working
- [ ] Redis installed and running
- [ ] Development environment ready

---

## Day 6-7: Django Channels (WebSocket) Implementation

**Estimated Time**: 12-16 hours (2 days)

### Hour-by-Hour Breakdown

#### Day 6 Morning (Hours 1-4): Setup & Configuration

**Hour 1: Redis Installation**
- [ ] Install Redis (macOS: `brew install redis` or Linux: `apt install redis-server`)
- [ ] Start Redis server
- [ ] Test connection: `redis-cli ping` → Should return `PONG`
- [ ] Configure Redis to start on boot

**Hour 2: Install Channels Packages**
- [ ] Activate virtual environment
- [ ] Install: `pip install channels[daphne]==4.0.0`
- [ ] Install: `pip install channels-redis==4.1.0`
- [ ] Update requirements: `pip freeze > requirements/production.txt`
- [ ] Verify installation: `python -c "import channels; print(channels.__version__)"`

**Hour 3: Configure Django Settings**
- [ ] Add `'daphne'` to INSTALLED_APPS (first position)
- [ ] Set `ASGI_APPLICATION = 'config.asgi.application'`
- [ ] Configure CHANNEL_LAYERS with Redis URL
- [ ] Test: `python manage.py check`

**Hour 4: Update ASGI Configuration**
- [ ] Edit `config/asgi.py`
- [ ] Import ProtocolTypeRouter, URLRouter, AuthMiddlewareStack
- [ ] Create protocol router with HTTP and WebSocket
- [ ] Test ASGI app loads: `python -c "from config.asgi import application"`

---

#### Day 6 Afternoon (Hours 5-8): Create WebSocket Consumer

**Hour 5: Create Consumer File**
- [ ] Create `apps/analysis/consumers.py`
- [ ] Import AsyncWebsocketConsumer
- [ ] Create AnalysisProgressConsumer class
- [ ] Implement connect() method (join room group)
- [ ] Implement disconnect() method (leave room group)

**Hour 6: Message Handlers**
- [ ] Implement analysis_progress() handler
- [ ] Implement analysis_complete() handler
- [ ] Implement analysis_error() handler
- [ ] Add JSON serialization for all messages

**Hour 7: WebSocket Routing**
- [ ] Create `apps/analysis/routing.py`
- [ ] Define websocket_urlpatterns
- [ ] Add route: `ws/analysis/<session_id>/`
- [ ] Link to AnalysisProgressConsumer

**Hour 8: Test Consumer**
- [ ] Start Daphne: `daphne -b 0.0.0.0 -p 8000 config.asgi:application`
- [ ] Test WebSocket connection in browser console
- [ ] Verify channel layer works: `python manage.py shell` → test async_to_sync

---

#### Day 7 Morning (Hours 9-12): Update Analysis Service

**Hour 9: Add Progress Methods**
- [ ] Edit `apps/analysis/services/analysis_service.py`
- [ ] Import get_channel_layer, async_to_sync
- [ ] Create `_send_progress()` method
- [ ] Create `_send_complete()` method
- [ ] Create `_send_error()` method

**Hour 10: Integrate Progress Updates**
- [ ] Update `run_analysis()` to call `_send_progress()`
- [ ] Add progress at: loading (5%), preprocessing (10%), rule1 (20%), etc.
- [ ] Add completion notification at end
- [ ] Add error notification in except block

**Hour 11: Test Progress Updates**
- [ ] Start Daphne server
- [ ] Open browser dev tools
- [ ] Upload test CSV and analyze
- [ ] Verify WebSocket messages received
- [ ] Check progress percentages

**Hour 12: Debug & Fix Issues**
- [ ] Fix any connection issues
- [ ] Verify message format
- [ ] Test error handling
- [ ] Document any issues found

---

#### Day 7 Afternoon (Hours 13-16): Frontend Integration

**Hour 13: Update Template**
- [ ] Edit `templates/analysis/session_detail.html`
- [ ] Add progress bar HTML
- [ ] Add WebSocket connection script
- [ ] Set WebSocket URL with session ID

**Hour 14: WebSocket Client Logic**
- [ ] Implement onopen handler
- [ ] Implement onmessage handler (update progress bar)
- [ ] Implement onclose handler (fallback to refresh)
- [ ] Implement onerror handler

**Hour 15: Test Full Workflow**
- [ ] Upload CSV file
- [ ] Click analyze
- [ ] Watch real-time progress bar
- [ ] Verify automatic redirect on completion
- [ ] Test with different file sizes

**Hour 16: Polish & Documentation**
- [ ] Add loading animations
- [ ] Add percentage display
- [ ] Improve error messages
- [ ] Document WebSocket usage
- [ ] Create troubleshooting guide

---

### Day 6-7 Deliverables

- [ ] Redis installed and configured
- [ ] Django Channels fully set up
- [ ] WebSocket consumer working
- [ ] Real-time progress bar functional
- [ ] Automatic page transitions
- [ ] Documentation updated

**Success Criteria**:
- WebSocket connection established
- Progress updates visible in real-time
- No page refresh needed
- Error handling works

---

## Day 8: Celery (Background Tasks) Implementation

**Estimated Time**: 6-8 hours (1 day)

### Hour-by-Hour Breakdown

#### Morning (Hours 1-4): Celery Setup

**Hour 1: Install Celery**
- [ ] Install: `pip install celery[redis]==5.3.4`
- [ ] Install: `pip install django-celery-beat==2.5.0`
- [ ] Install: `pip install django-celery-results==2.5.1`
- [ ] Install: `pip install flower==2.0.1`
- [ ] Update requirements

**Hour 2: Configure Celery**
- [ ] Uncomment `config/celery.py`
- [ ] Verify app configuration
- [ ] Add beat schedule for cleanup task
- [ ] Uncomment `config/__init__.py` imports

**Hour 3: Update Settings**
- [ ] Add `django_celery_beat` to INSTALLED_APPS
- [ ] Add `django_celery_results` to INSTALLED_APPS
- [ ] Verify CELERY_BROKER_URL points to Redis
- [ ] Run migrations: `python manage.py migrate`

**Hour 4: Test Celery**
- [ ] Start worker: `celery -A config worker -l info`
- [ ] Create debug task
- [ ] Queue test task: `debug_task.delay()`
- [ ] Verify task executes

---

#### Afternoon (Hours 5-8): Create Tasks & Integration

**Hour 5: Create Analysis Tasks**
- [ ] Create `apps/analysis/tasks.py`
- [ ] Implement `run_analysis_async(session_id)`
- [ ] Add try/except for error handling
- [ ] Store task ID in session model
- [ ] Add status updates

**Hour 6: Create Periodic Tasks**
- [ ] Implement `cleanup_old_sessions(days=30)`
- [ ] Implement `send_analysis_notification(session_id, email)` (stub)
- [ ] Configure beat schedule in celery.py
- [ ] Test periodic task manually

**Hour 7: Update ViewSet**
- [ ] Edit `apps/analysis/views.py`
- [ ] Import `run_analysis_async`
- [ ] Update `analyze` action to queue task
- [ ] Return task ID in response (202 Accepted)
- [ ] Update status to 'pending'

**Hour 8: Test & Monitor**
- [ ] Start Celery worker
- [ ] Start Celery beat
- [ ] Start Flower: `celery -A config flower`
- [ ] Queue analysis task
- [ ] Monitor in Flower (http://localhost:5555)
- [ ] Verify task completes

---

### Day 8 Deliverables

- [ ] Celery fully configured
- [ ] Background analysis task working
- [ ] Periodic cleanup task configured
- [ ] Flower monitoring accessible
- [ ] Task queue operational

**Success Criteria**:
- Tasks execute in background
- Multiple analyses can run concurrently
- Flower shows task status
- Periodic tasks scheduled

---

## Day 9: PostgreSQL Migration

**Estimated Time**: 4-6 hours (1 day)

### Hour-by-Hour Breakdown

#### Morning (Hours 1-3): PostgreSQL Setup

**Hour 1: Install PostgreSQL**
- [ ] Install PostgreSQL (macOS: `brew install postgresql` or Linux: `apt install postgresql`)
- [ ] Start PostgreSQL service
- [ ] Verify: `psql --version`

**Hour 2: Create Database**
- [ ] Switch to postgres user: `sudo -u postgres psql`
- [ ] Create database: `CREATE DATABASE ganglioside_db;`
- [ ] Create user: `CREATE USER ganglioside_user WITH PASSWORD 'secure_password';`
- [ ] Grant privileges
- [ ] Test connection: `psql -U ganglioside_user -d ganglioside_db`

**Hour 3: Configure Django**
- [ ] Install: `pip install psycopg2-binary`
- [ ] Update .env with PostgreSQL credentials
- [ ] Update `config/settings/base.py` DATABASES
- [ ] Test: `python manage.py check --database default`

---

#### Afternoon (Hours 4-6): Data Migration

**Hour 4: Backup SQLite**
- [ ] Export SQLite data: `python manage.py dumpdata > backup.json`
- [ ] Copy db.sqlite3 to backup location
- [ ] Verify backup file size

**Hour 5: Run Migrations**
- [ ] Run migrations on PostgreSQL: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Verify schema created

**Hour 6: Import Data**
- [ ] Load data: `python manage.py loaddata backup.json`
- [ ] Verify data counts match
- [ ] Test queries in shell
- [ ] Run test analysis
- [ ] Verify all functionality works

---

### Day 9 Deliverables

- [ ] PostgreSQL installed and configured
- [ ] Database created with proper permissions
- [ ] All data migrated from SQLite
- [ ] System working with PostgreSQL
- [ ] Performance tested

**Success Criteria**:
- All data successfully migrated
- No data loss
- Application works with PostgreSQL
- Performance acceptable

---

## Day 10: Integration Testing & Buffer

**Estimated Time**: 4-6 hours (buffer day)

### Testing Checklist

#### Channels Testing
- [ ] WebSocket connection stability
- [ ] Progress updates accurate
- [ ] Multiple concurrent connections
- [ ] Reconnection after disconnect
- [ ] Error handling

#### Celery Testing
- [ ] Task queuing works
- [ ] Multiple concurrent tasks
- [ ] Task failure handling
- [ ] Periodic tasks execute
- [ ] Flower monitoring accurate

#### PostgreSQL Testing
- [ ] Data integrity verified
- [ ] Query performance acceptable
- [ ] Concurrent write operations
- [ ] Connection pooling works
- [ ] Backup/restore tested

#### Integration Testing
- [ ] Channels + Celery work together
- [ ] WebSocket updates from Celery tasks
- [ ] PostgreSQL handles load
- [ ] No resource leaks
- [ ] Error handling end-to-end

---

### Day 10 Deliverables

- [ ] All integration tests passing
- [ ] Performance benchmarks recorded
- [ ] Bug fixes completed
- [ ] Documentation updated
- [ ] Week 2 complete!

---

## Week 2 Success Criteria

### Technical Criteria
- [ ] Real-time WebSocket progress working
- [ ] Celery background tasks operational
- [ ] PostgreSQL deployed and tested
- [ ] Flower monitoring accessible
- [ ] All systems integrated

### Quality Criteria
- [ ] No data loss during PostgreSQL migration
- [ ] WebSocket connection stable
- [ ] Task execution reliable
- [ ] Performance acceptable
- [ ] Error handling robust

### Documentation Criteria
- [ ] Setup instructions updated
- [ ] Troubleshooting guide created
- [ ] Configuration documented
- [ ] API changes documented

---

## Common Issues & Solutions

### Redis Issues
**Problem**: `Connection refused to Redis`
**Solution**: Ensure Redis is running: `redis-cli ping`

### Channels Issues
**Problem**: WebSocket connection fails
**Solution**: Check ASGI routing, verify Daphne running

### Celery Issues
**Problem**: Tasks not executing
**Solution**: Verify worker running, check Redis connection

### PostgreSQL Issues
**Problem**: Connection error
**Solution**: Check credentials, verify PostgreSQL service running

---

## Production Readiness Checklist

After Week 2:
- [ ] Redis configured for production
- [ ] Celery workers configured as systemd services
- [ ] PostgreSQL tuned for performance
- [ ] WebSocket Nginx configuration ready
- [ ] All secrets in environment variables
- [ ] Logging configured
- [ ] Monitoring in place

---

## Next Steps: Week 3 Preview

After completing Week 2:

**Week 3 Day 11-12**: Production Deployment
- Deploy to production server
- Configure Nginx for WebSocket
- Set up systemd services
- SSL certificate configuration

**Week 3 Day 13-14**: Comprehensive Testing
- Unit tests (>80% coverage)
- Integration tests
- Performance tests
- Security audit

**Week 3 Day 15**: Monitoring & Operations
- Set up error tracking
- Configure alerting
- Automate backups
- Create runbook

---

## Resources

### Documentation
- `ADVANCED_FEATURES_SETUP.md` - Detailed implementation guide
- `PRODUCTION_DEPLOYMENT_GUIDE.md` - Production deployment
- Django Channels docs: https://channels.readthedocs.io/
- Celery docs: https://docs.celeryq.dev/

### Tools
- Redis: http://localhost:6379
- Flower: http://localhost:5555
- Django Admin: http://localhost:8000/admin/
- API Docs: http://localhost:8000/api/docs/

---

**Last Updated**: 2025-10-21
**Status**: Ready to Begin Week 2
**Estimated Duration**: 2 working weeks (40-48 hours)
**Next Action**: Install Redis

**🚀 Let's build advanced features! 🚀**
