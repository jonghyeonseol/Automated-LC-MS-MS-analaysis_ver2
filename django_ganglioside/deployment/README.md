# Deployment Files

This directory contains all production deployment configuration files for the Ganglioside Analysis Platform.

## Directory Structure

```
deployment/
├── nginx/
│   └── ganglioside.conf          # Nginx reverse proxy configuration
├── systemd/
│   ├── ganglioside-django.service        # Gunicorn WSGI server
│   ├── ganglioside-daphne.service        # Daphne WebSocket server
│   ├── ganglioside-celery-worker.service # Celery background worker
│   └── ganglioside-celery-beat.service   # Celery periodic task scheduler
└── scripts/
    └── deploy.sh                 # Automated deployment script
```

## Quick Start

### 1. Nginx Configuration

Copy to server and enable:

```bash
sudo cp nginx/ganglioside.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/ganglioside.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Before enabling:**
- Replace `your-domain.com` with your actual domain
- Update SSL certificate paths
- Adjust rate limiting if needed

### 2. Systemd Services

Copy service files:

```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Enable and start:

```bash
sudo systemctl enable ganglioside-django ganglioside-daphne ganglioside-celery-worker ganglioside-celery-beat
sudo systemctl start ganglioside-django ganglioside-daphne ganglioside-celery-worker ganglioside-celery-beat
```

**Before starting:**
- Update `WorkingDirectory` paths in service files
- Update `User` and `Group` if not using `ganglioside`
- Ensure `/var/log/celery` exists with proper permissions

### 3. Deployment Script

Make executable and run:

```bash
chmod +x scripts/deploy.sh
sudo ./scripts/deploy.sh
```

This script will:
1. Pull latest code from git
2. Install dependencies
3. Run migrations
4. Collect static files
5. Restart all services
6. Verify service status

## Service Details

### ganglioside-django.service

**Purpose:** Runs Django application via Gunicorn WSGI server

**Listens on:** 127.0.0.1:8000

**Configuration:** `gunicorn.conf.py` in project root

**Logs:** `sudo journalctl -u ganglioside-django -f`

### ganglioside-daphne.service

**Purpose:** Handles WebSocket connections for real-time updates

**Listens on:** 127.0.0.1:8001

**Uses:** Django Channels + Redis

**Logs:** `sudo journalctl -u ganglioside-daphne -f`

### ganglioside-celery-worker.service

**Purpose:** Processes background analysis tasks

**Workers:** 4 (configurable)

**Logs:** `/var/log/celery/ganglioside_worker.log`

### ganglioside-celery-beat.service

**Purpose:** Schedules periodic tasks (cleanup, backups)

**Uses:** django-celery-beat for database-backed scheduling

**Logs:** `/var/log/celery/ganglioside_beat.log`

## Nginx Configuration Details

### Upstream Servers

- **django_app:** Gunicorn on port 8000
- **websocket_app:** Daphne on port 8001

### Rate Limiting

- **API endpoints:** 10 requests/second
- **File uploads:** 2 requests/minute

Adjust in `nginx/ganglioside.conf`:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=2r/m;
```

### Static Files

Served directly by Nginx from:
- `/var/www/ganglioside/static/` → `/static/`
- `/var/www/ganglioside/media/` → `/media/`

Cache duration:
- Static files: 30 days
- Media files: 7 days

### WebSocket Proxying

URL path `/ws/` is proxied to Daphne with proper upgrade headers:

```nginx
location /ws/ {
    proxy_pass http://websocket_app;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## Deployment Workflow

### Initial Deployment

1. Provision server (Ubuntu 22.04 LTS)
2. Install dependencies (Python, PostgreSQL, Redis, Nginx)
3. Create deployment user and directories
4. Clone repository to `/var/www/ganglioside`
5. Set up Python virtual environment
6. Install Python dependencies
7. Configure environment variables (`.env.production`)
8. Run database migrations
9. Collect static files
10. Configure Nginx
11. Obtain SSL certificate (Let's Encrypt)
12. Install systemd services
13. Start and verify all services

See `DEPLOYMENT_GUIDE.md` for detailed instructions.

### Subsequent Deployments

Use the deployment script:

```bash
sudo /var/www/ganglioside/deployment/scripts/deploy.sh
```

Or manually:

```bash
# Pull latest code
cd /var/www/ganglioside
git pull origin main

# Install dependencies
venv/bin/pip install -r requirements/production.txt

# Run migrations
venv/bin/python manage.py migrate

# Collect static files
venv/bin/python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart ganglioside-django
sudo systemctl restart ganglioside-daphne
sudo systemctl restart ganglioside-celery-worker
sudo systemctl restart ganglioside-celery-beat

# Reload Nginx
sudo systemctl reload nginx
```

## Monitoring

### Health Checks

```bash
# Application health
curl https://your-domain.com/health

# Service status
systemctl status ganglioside-django
systemctl status ganglioside-daphne
systemctl status ganglioside-celery-worker
systemctl status ganglioside-celery-beat

# Redis connectivity
redis-cli ping

# PostgreSQL connectivity
psql -U ganglioside_user -d ganglioside_prod -c "SELECT 1;"
```

### Log Aggregation

```bash
# All services
sudo journalctl -f -u ganglioside-*

# Individual services
sudo journalctl -f -u ganglioside-django
sudo journalctl -f -u ganglioside-daphne
tail -f /var/log/celery/ganglioside_worker.log
tail -f /var/log/celery/ganglioside_beat.log

# Nginx logs
tail -f /var/log/nginx/ganglioside_access.log
tail -f /var/log/nginx/ganglioside_error.log
```

## Troubleshooting

### Services Won't Start

1. Check service logs: `sudo journalctl -u ganglioside-django -n 50`
2. Verify environment file exists: `/var/www/ganglioside/.env.production`
3. Check file permissions: `ls -la /var/www/ganglioside`
4. Verify Python packages installed: `venv/bin/pip list`

### 502 Bad Gateway

1. Ensure Gunicorn is running: `systemctl status ganglioside-django`
2. Check Nginx can connect: `curl http://127.0.0.1:8000`
3. Review Nginx error logs: `tail /var/log/nginx/ganglioside_error.log`

### WebSocket Failures

1. Ensure Daphne is running: `systemctl status ganglioside-daphne`
2. Verify Redis is accessible: `redis-cli ping`
3. Check channel layer configuration in settings

### Celery Tasks Not Processing

1. Check worker is running: `systemctl status ganglioside-celery-worker`
2. Verify Redis connectivity: `redis-cli KEYS "celery*"`
3. Check task queue: Use Flower monitoring tool
4. Review worker logs: `tail -f /var/log/celery/ganglioside_worker.log`

## Security Notes

- **Firewall:** Only ports 80, 443, and SSH should be exposed
- **User isolation:** Services run as `ganglioside` user, not root
- **SSL/TLS:** Enforced via Nginx (HTTPS redirect)
- **HSTS:** Strict-Transport-Security header enabled
- **Rate limiting:** Protects against abuse
- **File upload limits:** Max 50MB enforced at multiple layers

## Performance Tuning

### Gunicorn Workers

Default: `(2 x CPU cores) + 1`

Adjust in `gunicorn.conf.py`:

```python
workers = 8  # For 4-core server
```

### PostgreSQL Connection Pooling

Configured in production settings:

```python
DATABASES['default']['CONN_MAX_AGE'] = 600  # 10 minutes
```

### Static File Caching

WhiteNoise compresses and caches static files. Run collectstatic after changes:

```bash
python manage.py collectstatic --noinput
```

## Backup & Recovery

### Database Backups

Automated daily backups at 2 AM (see `scripts/backup_db.sh`).

Manual backup:

```bash
pg_dump -U ganglioside_user ganglioside_prod | gzip > backup_$(date +%Y%m%d).sql.gz
```

Restore:

```bash
gunzip < backup_20251021.sql.gz | psql -U ganglioside_user ganglioside_prod
```

### Media File Backups

```bash
tar -czf media_backup_$(date +%Y%m%d).tar.gz /var/www/ganglioside/media/
```

## Additional Resources

- **Full Deployment Guide:** `../DEPLOYMENT_GUIDE.md`
- **Production Settings:** `../config/settings/production.py`
- **Gunicorn Config:** `../gunicorn.conf.py`
- **Environment Template:** `../.env.production`

---

**Last Updated:** 2025-10-21
