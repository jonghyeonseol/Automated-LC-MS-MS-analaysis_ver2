# Production Deployment Guide
## Ganglioside Analysis Platform

**Version:** 2.0
**Last Updated:** 2025-10-21
**Target:** Ubuntu 22.04 LTS

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Database Configuration](#database-configuration)
4. [Application Deployment](#application-deployment)
5. [Nginx & SSL Setup](#nginx--ssl-setup)
6. [Systemd Services](#systemd-services)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Server Requirements

- **OS:** Ubuntu 22.04 LTS (64-bit)
- **CPU:** 2+ cores (4 recommended)
- **RAM:** 4GB minimum (8GB recommended)
- **Disk:** 20GB minimum (50GB recommended)
- **Network:** Static IP address with domain name

### Required Services

- Python 3.9+
- PostgreSQL 15
- Redis 7+
- Nginx
- Certbot (Let's Encrypt)

---

## Server Setup

### Step 1: Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl wget
```

### Step 2: Install Python 3.9+

```bash
sudo apt install -y python3.9 python3.9-venv python3.9-dev python3-pip
```

### Step 3: Install PostgreSQL 15

```bash
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib-15
```

### Step 4: Install Redis

```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Step 5: Install Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
```

### Step 6: Create Deployment User

```bash
sudo useradd -m -s /bin/bash ganglioside
sudo mkdir -p /var/www/ganglioside
sudo chown ganglioside:ganglioside /var/www/ganglioside
```

### Step 7: Configure Firewall

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

## Database Configuration

### Step 1: Create Production Database

```bash
sudo -u postgres psql <<EOF
CREATE DATABASE ganglioside_prod;
CREATE USER ganglioside_user WITH PASSWORD 'CHANGE_THIS_PASSWORD';
ALTER DATABASE ganglioside_prod OWNER TO ganglioside_user;
GRANT ALL PRIVILEGES ON DATABASE ganglioside_prod TO ganglioside_user;
\q
EOF
```

### Step 2: Configure PostgreSQL Authentication

Edit `/etc/postgresql/15/main/pg_hba.conf`:

```conf
# Add this line
local   ganglioside_prod   ganglioside_user   md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### Step 3: Verify Connection

```bash
sudo -u ganglioside psql -U ganglioside_user -d ganglioside_prod
```

---

## Application Deployment

### Step 1: Clone Repository

```bash
sudo -u ganglioside git clone https://github.com/your-org/ganglioside.git /var/www/ganglioside
cd /var/www/ganglioside
```

### Step 2: Create Virtual Environment

```bash
sudo -u ganglioside python3.9 -m venv venv
sudo -u ganglioside venv/bin/pip install --upgrade pip
```

### Step 3: Install Dependencies

```bash
sudo -u ganglioside venv/bin/pip install -r requirements/production.txt
```

### Step 4: Configure Environment Variables

Create `/var/www/ganglioside/.env.production`:

```bash
sudo -u ganglioside nano /var/www/ganglioside/.env.production
```

Fill in with your production values (see `.env.production` template).

### Step 5: Run Migrations

```bash
sudo -u ganglioside DJANGO_SETTINGS_MODULE=config.settings.production \
    venv/bin/python manage.py migrate
```

### Step 6: Create Superuser

```bash
sudo -u ganglioside DJANGO_SETTINGS_MODULE=config.settings.production \
    venv/bin/python manage.py createsuperuser
```

### Step 7: Collect Static Files

```bash
sudo mkdir -p /var/www/ganglioside/static
sudo mkdir -p /var/www/ganglioside/media
sudo chown -R ganglioside:ganglioside /var/www/ganglioside/static
sudo chown -R ganglioside:ganglioside /var/www/ganglioside/media

sudo -u ganglioside DJANGO_SETTINGS_MODULE=config.settings.production \
    venv/bin/python manage.py collectstatic --noinput
```

---

## Nginx & SSL Setup

### Step 1: Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Step 2: Obtain SSL Certificate

```bash
sudo certbot certonly --nginx -d your-domain.com -d www.your-domain.com
```

### Step 3: Configure Nginx

```bash
sudo cp deployment/nginx/ganglioside.conf /etc/nginx/sites-available/ganglioside
sudo ln -s /etc/nginx/sites-available/ganglioside /etc/nginx/sites-enabled/
```

Edit the configuration to replace `your-domain.com` with your actual domain.

### Step 4: Test and Reload Nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### Step 5: Set Up Auto-Renewal

```bash
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## Systemd Services

### Step 1: Copy Service Files

```bash
sudo cp deployment/systemd/*.service /etc/systemd/system/
```

### Step 2: Create Log Directories

```bash
sudo mkdir -p /var/log/celery
sudo mkdir -p /var/run/celery
sudo chown -R ganglioside:ganglioside /var/log/celery
sudo chown -R ganglioside:ganglioside /var/run/celery
```

### Step 3: Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable ganglioside-django.service
sudo systemctl enable ganglioside-daphne.service
sudo systemctl enable ganglioside-celery-worker.service
sudo systemctl enable ganglioside-celery-beat.service

# Start services
sudo systemctl start ganglioside-django.service
sudo systemctl start ganglioside-daphne.service
sudo systemctl start ganglioside-celery-worker.service
sudo systemctl start ganglioside-celery-beat.service
```

### Step 4: Verify Services

```bash
sudo systemctl status ganglioside-django.service
sudo systemctl status ganglioside-daphne.service
sudo systemctl status ganglioside-celery-worker.service
sudo systemctl status ganglioside-celery-beat.service
```

---

## Monitoring & Logging

### Application Logs

```bash
# Django logs
sudo journalctl -u ganglioside-django -f

# Daphne logs
sudo journalctl -u ganglioside-daphne -f

# Celery worker logs
sudo tail -f /var/log/celery/ganglioside_worker.log

# Celery beat logs
sudo tail -f /var/log/celery/ganglioside_beat.log
```

### Nginx Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/ganglioside_access.log

# Error logs
sudo tail -f /var/log/nginx/ganglioside_error.log
```

### PostgreSQL Logs

```bash
sudo tail -f /var/log/postgresql/postgresql-15-main.log
```

---

## Backup & Recovery

### Database Backup

Create backup script `/var/www/ganglioside/scripts/backup_db.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/ganglioside"
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U ganglioside_user ganglioside_prod | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: db_$DATE.sql.gz"
```

Make it executable:

```bash
chmod +x /var/www/ganglioside/scripts/backup_db.sh
```

### Set Up Cron Job

```bash
sudo crontab -e -u ganglioside
```

Add:

```cron
# Daily database backup at 2 AM
0 2 * * * /var/www/ganglioside/scripts/backup_db.sh
```

### Database Restore

```bash
gunzip < /var/backups/ganglioside/db_YYYYMMDD_HHMMSS.sql.gz | \
    sudo -u postgres psql ganglioside_prod
```

---

## Troubleshooting

### Service Won't Start

Check logs:

```bash
sudo journalctl -u ganglioside-django -n 50
```

Common issues:
- Environment file not found → Check `/var/www/ganglioside/.env.production`
- Permission denied → Run `sudo chown -R ganglioside:ganglioside /var/www/ganglioside`
- Port already in use → Check with `sudo lsof -i :8000`

### 502 Bad Gateway

Check if Gunicorn is running:

```bash
sudo systemctl status ganglioside-django
```

Check Nginx error logs:

```bash
sudo tail -f /var/log/nginx/ganglioside_error.log
```

### WebSocket Connection Fails

Check if Daphne is running:

```bash
sudo systemctl status ganglioside-daphne
```

Verify Redis is running:

```bash
redis-cli ping
```

### Celery Tasks Not Running

Check worker status:

```bash
sudo systemctl status ganglioside-celery-worker
```

Check Redis connection:

```bash
redis-cli
> KEYS *
```

### Static Files Not Loading

Collect static files:

```bash
sudo -u ganglioside DJANGO_SETTINGS_MODULE=config.settings.production \
    venv/bin/python manage.py collectstatic --noinput
```

Check permissions:

```bash
sudo chown -R ganglioside:ganglioside /var/www/ganglioside/static
```

---

## Health Checks

### Manual Health Check

```bash
curl https://your-domain.com/health
```

Expected response: `{"status": "ok"}`

### Service Status

```bash
# Quick status check
for service in ganglioside-django ganglioside-daphne ganglioside-celery-worker ganglioside-celery-beat; do
    systemctl is-active --quiet $service && echo "$service: ✓ RUNNING" || echo "$service: ✗ FAILED"
done
```

---

## Deployment Checklist

- [ ] Server provisioned and updated
- [ ] PostgreSQL database created
- [ ] Redis server running
- [ ] Application code deployed
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] Superuser created
- [ ] Static files collected
- [ ] Nginx configured
- [ ] SSL certificate obtained
- [ ] Systemd services enabled
- [ ] All services started and running
- [ ] Health check endpoint responding
- [ ] Backup cron job configured
- [ ] Monitoring alerts set up
- [ ] DNS properly configured

---

## Security Hardening

### Disable Root SSH Login

Edit `/etc/ssh/sshd_config`:

```conf
PermitRootLogin no
PasswordAuthentication no
```

Restart SSH:

```bash
sudo systemctl restart ssh
```

### Install Fail2ban

```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Configure Automatic Security Updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

---

## Performance Tuning

### PostgreSQL

Edit `/etc/postgresql/15/main/postgresql.conf`:

```conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### Gunicorn Workers

Formula: `(2 x CPU cores) + 1`

Edit `gunicorn.conf.py`:

```python
workers = multiprocessing.cpu_count() * 2 + 1
```

---

## Maintenance

### Restarting Services After Code Update

```bash
sudo /var/www/ganglioside/deployment/scripts/deploy.sh
```

### Manual Service Restart

```bash
sudo systemctl restart ganglioside-django
sudo systemctl restart ganglioside-daphne
sudo systemctl restart ganglioside-celery-worker
sudo systemctl restart ganglioside-celery-beat
```

### Viewing Real-Time Logs

```bash
# All services
sudo journalctl -f -u ganglioside-*

# Specific service
sudo journalctl -f -u ganglioside-django
```

---

## Contact & Support

- **Documentation:** [Link to docs]
- **Issue Tracker:** [Link to GitHub issues]
- **Admin Panel:** https://your-domain.com/admin

---

**End of Deployment Guide**
