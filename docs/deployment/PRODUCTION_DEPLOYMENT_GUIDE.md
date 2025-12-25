# Production Deployment Guide - Django Ganglioside Platform

**Date**: 2025-10-21
**Version**: Django 2.0.0
**Target**: Production Server Deployment

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Database Configuration (PostgreSQL)](#database-configuration-postgresql)
4. [Environment Variables](#environment-variables)
5. [Static Files](#static-files)
6. [WSGI Server (Gunicorn)](#wsgi-server-gunicorn)
7. [Reverse Proxy (Nginx)](#reverse-proxy-nginx)
8. [SSL/TLS Configuration](#ssltls-configuration)
9. [Systemd Service](#systemd-service)
10. [Security Checklist](#security-checklist)
11. [Monitoring & Logging](#monitoring--logging)
12. [Backup & Recovery](#backup--recovery)
13. [Deployment Checklist](#deployment-checklist)

---

## Prerequisites

### System Requirements

- **OS**: Ubuntu 22.04 LTS or similar Linux distribution
- **Python**: 3.9+
- **RAM**: Minimum 2GB (4GB+ recommended)
- **Disk**: 20GB+ available
- **Network**: Static IP or domain name

### Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and build tools
sudo apt install -y python3.9 python3.9-venv python3.9-dev python3-pip

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib libpq-dev

# Install Nginx
sudo apt install -y nginx

# Install system dependencies
sudo apt install -y build-essential git curl
```

---

## Server Setup

### 1. Create Deployment User

```bash
# Create user
sudo adduser ganglioside
sudo usermod -aG sudo ganglioside

# Switch to user
su - ganglioside
```

### 2. Clone Repository

```bash
cd /home/ganglioside
git clone https://github.com/yourusername/Automated-LC-MS-MS-analaysis_ver2.git
cd Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside
```

### 3. Create Virtual Environment

```bash
python3.9 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 4. Install Dependencies

```bash
# Install production requirements
pip install -r requirements/production.txt

# Verify installation
pip list
```

---

## Database Configuration (PostgreSQL)

### 1. Create PostgreSQL Database

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
CREATE DATABASE ganglioside_db;
CREATE USER ganglioside_user WITH PASSWORD 'your_secure_password_here';

# Grant privileges
ALTER ROLE ganglioside_user SET client_encoding TO 'utf8';
ALTER ROLE ganglioside_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE ganglioside_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ganglioside_db TO ganglioside_user;

# Exit
\q
```

### 2. Configure PostgreSQL Connection

**File**: `config/settings/production.py`

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'ganglioside_db'),
        'USER': os.getenv('DB_USER', 'ganglioside_user'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

### 3. Test Database Connection

```bash
# Install psycopg2
pip install psycopg2-binary

# Test connection
python manage.py check --database default
```

---

## Environment Variables

### 1. Create Production Environment File

**File**: `/home/ganglioside/.env.production`

```bash
# Django Settings
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY='your-super-secret-key-here-min-50-chars-random-string'
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com,your.server.ip

# Database
DB_NAME=ganglioside_db
DB_USER=ganglioside_user
DB_PASSWORD=your_secure_password_here
DB_HOST=localhost
DB_PORT=5432

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True

# Static/Media Files
STATIC_ROOT=/home/ganglioside/static
MEDIA_ROOT=/home/ganglioside/media

# Optional: Redis (for Celery/Channels)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
```

### 2. Generate SECRET_KEY

```python
# Generate secure secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Load Environment Variables

```bash
# Add to ~/.bashrc or ~/.profile
echo 'export $(cat /home/ganglioside/.env.production | xargs)' >> ~/.bashrc
source ~/.bashrc
```

---

## Static Files

### 1. Create Static Directories

```bash
# Create directories
sudo mkdir -p /home/ganglioside/static
sudo mkdir -p /home/ganglioside/media
sudo chown -R ganglioside:ganglioside /home/ganglioside/static
sudo chown -R ganglioside:ganglioside /home/ganglioside/media
```

### 2. Collect Static Files

```bash
# Activate venv and set settings
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.production

# Collect static files
python manage.py collectstatic --noinput

# Verify
ls -la /home/ganglioside/static
```

---

## WSGI Server (Gunicorn)

### 1. Install Gunicorn

```bash
pip install gunicorn
```

### 2. Test Gunicorn

```bash
# Test run
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4

# Access: http://your-server-ip:8000
# Press Ctrl+C to stop
```

### 3. Create Gunicorn Configuration

**File**: `/home/ganglioside/django_ganglioside/gunicorn_config.py`

```python
"""Gunicorn configuration for production"""
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "/home/ganglioside/logs/gunicorn_access.log"
errorlog = "/home/ganglioside/logs/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "ganglioside_django"

# Server mechanics
daemon = False
pidfile = "/home/ganglioside/gunicorn.pid"
user = "ganglioside"
group = "ganglioside"
```

### 4. Create Log Directory

```bash
mkdir -p /home/ganglioside/logs
```

---

## Reverse Proxy (Nginx)

### 1. Create Nginx Configuration

**File**: `/etc/nginx/sites-available/ganglioside`

```nginx
upstream ganglioside_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (will be added later with Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_timeout 10m;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Max upload size (for CSV files)
    client_max_body_size 100M;

    # Static files
    location /static/ {
        alias /home/ganglioside/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /home/ganglioside/media/;
        expires 7d;
    }

    # Proxy to Django
    location / {
        proxy_pass http://ganglioside_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Timeouts
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Logging
    access_log /var/log/nginx/ganglioside_access.log;
    error_log /var/log/nginx/ganglioside_error.log;
}
```

### 2. Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/ganglioside /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

---

## SSL/TLS Configuration

### Using Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Certificate Auto-Renewal

```bash
# Certbot automatically creates a cron job
# Verify:
sudo systemctl status certbot.timer
```

---

## Systemd Service

### 1. Create Gunicorn Service

**File**: `/etc/systemd/system/ganglioside.service`

```ini
[Unit]
Description=Ganglioside Django Application
After=network.target postgresql.service

[Service]
Type=notify
User=ganglioside
Group=ganglioside
WorkingDirectory=/home/ganglioside/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside
Environment="PATH=/home/ganglioside/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside/venv/bin"
EnvironmentFile=/home/ganglioside/.env.production
ExecStart=/home/ganglioside/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside/venv/bin/gunicorn \
    --config /home/ganglioside/django_ganglioside/gunicorn_config.py \
    config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable ganglioside.service

# Start service
sudo systemctl start ganglioside.service

# Check status
sudo systemctl status ganglioside.service

# View logs
sudo journalctl -u ganglioside.service -f
```

---

## Security Checklist

### Django Settings

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` is long, random, and secret
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] `SECURE_HSTS_SECONDS = 31536000`
- [ ] CORS properly configured (if needed)

### Server Security

- [ ] Firewall enabled (UFW)
- [ ] SSH key-based authentication
- [ ] Fail2ban installed
- [ ] Regular security updates
- [ ] Non-root user for deployment

### Firewall Configuration

```bash
# Install UFW
sudo apt install -y ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Install Fail2ban

```bash
# Install
sudo apt install -y fail2ban

# Configure
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Start service
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## Monitoring & Logging

### 1. Application Logs

**Django Logging Configuration** (`config/settings/production.py`):

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/home/ganglioside/logs/django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/home/ganglioside/logs/django_errors.log',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
        'apps': {
            'handlers': ['file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### 2. View Logs

```bash
# Django logs
tail -f /home/ganglioside/logs/django.log

# Gunicorn logs
tail -f /home/ganglioside/logs/gunicorn_access.log
tail -f /home/ganglioside/logs/gunicorn_error.log

# Nginx logs
sudo tail -f /var/log/nginx/ganglioside_access.log
sudo tail -f /var/log/nginx/ganglioside_error.log

# Systemd logs
sudo journalctl -u ganglioside.service -f
```

---

## Backup & Recovery

### 1. Database Backup Script

**File**: `/home/ganglioside/backup_db.sh`

```bash
#!/bin/bash

# Configuration
DB_NAME="ganglioside_db"
DB_USER="ganglioside_user"
BACKUP_DIR="/home/ganglioside/backups/db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup created: $BACKUP_FILE"
```

### 2. Media Files Backup

```bash
#!/bin/bash

# Backup media files
MEDIA_DIR="/home/ganglioside/media"
BACKUP_DIR="/home/ganglioside/backups/media"
DATE=$(date +%Y%m%d)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/media_${DATE}.tar.gz $MEDIA_DIR

# Keep only last 7 days
find $BACKUP_DIR -name "media_*.tar.gz" -mtime +7 -delete
```

### 3. Automate Backups with Cron

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/ganglioside/backup_db.sh >> /home/ganglioside/logs/backup.log 2>&1
0 3 * * * /home/ganglioside/backup_media.sh >> /home/ganglioside/logs/backup.log 2>&1
```

### 4. Database Restore

```bash
# Restore from backup
gunzip -c /path/to/backup.sql.gz | psql -U ganglioside_user ganglioside_db
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Code reviewed and tested
- [ ] All tests passing
- [ ] Database migrations created
- [ ] Static files collected
- [ ] Environment variables configured
- [ ] SSL certificate obtained
- [ ] Backup procedures tested

### Deployment Steps

```bash
# 1. Stop service
sudo systemctl stop ganglioside.service

# 2. Pull latest code
cd /home/ganglioside/Automated-LC-MS-MS-analaysis_ver2
git pull origin main

# 3. Activate venv
cd Regression/django_ganglioside
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements/production.txt

# 5. Run migrations
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate

# 6. Collect static files
python manage.py collectstatic --noinput

# 7. Restart service
sudo systemctl start ganglioside.service

# 8. Verify
sudo systemctl status ganglioside.service
curl https://yourdomain.com
```

### Post-Deployment

- [ ] Service started successfully
- [ ] Website accessible
- [ ] Admin panel working
- [ ] API endpoints functional
- [ ] Static files loading
- [ ] Database accessible
- [ ] Logs showing no errors

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u ganglioside.service -n 50

# Check Gunicorn directly
source venv/bin/activate
gunicorn config.wsgi:application --bind 127.0.0.1:8000

# Check permissions
ls -la /home/ganglioside/django_ganglioside
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -U ganglioside_user -d ganglioside_db -h localhost

# Check Django database settings
python manage.py check --database default
```

### Static Files Not Loading

```bash
# Re-collect static files
python manage.py collectstatic --noinput

# Check Nginx configuration
sudo nginx -t

# Check permissions
ls -la /home/ganglioside/static
```

---

## Maintenance

### Regular Tasks

**Daily**:
- Monitor logs for errors
- Check disk space
- Verify backups completed

**Weekly**:
- Review application performance
- Check for security updates
- Test backup restoration

**Monthly**:
- Update dependencies
- Review and archive old logs
- Performance optimization review

---

## Additional Resources

- Django Deployment Checklist: https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/
- Gunicorn Documentation: https://docs.gunicorn.org/
- Nginx Documentation: https://nginx.org/en/docs/
- PostgreSQL Documentation: https://www.postgresql.org/docs/

---

**Last Updated**: 2025-10-21
**Status**: Production Deployment Ready
