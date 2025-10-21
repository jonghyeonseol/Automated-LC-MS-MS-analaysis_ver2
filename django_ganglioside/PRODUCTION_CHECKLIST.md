# Production Deployment Checklist
## Ganglioside Analysis Platform v2.0

**Last Updated:** 2025-10-21

---

## Pre-Deployment Checklist

### ✅ Code Quality

- [ ] All tests passing (`make test`)
- [ ] Test coverage ≥ 70% (`make coverage`)
- [ ] Code linting passed (`make lint`)
- [ ] Security scan passed (Bandit, Safety)
- [ ] No TODO/FIXME comments in production code
- [ ] All code reviewed and approved
- [ ] Version number updated

### ✅ Configuration

- [ ] `.env.production` created with production values
- [ ] `SECRET_KEY` set to strong random value
- [ ] `DEBUG=False` in production settings
- [ ] `ALLOWED_HOSTS` configured correctly
- [ ] Database credentials secured
- [ ] Redis URL configured
- [ ] Email settings configured
- [ ] Sentry DSN added (if using error tracking)

### ✅ Database

- [ ] PostgreSQL 15 installed
- [ ] Production database created
- [ ] Database user created with strong password
- [ ] Database migrations run successfully
- [ ] Backup system configured
- [ ] Database connection pooling enabled
- [ ] Database performance tuned

### ✅ Security

- [ ] SSL/TLS certificate obtained (Let's Encrypt)
- [ ] HTTPS redirect enabled
- [ ] Security headers configured (HSTS, X-Frame-Options, etc.)
- [ ] CORS settings configured
- [ ] Rate limiting enabled
- [ ] Firewall configured (UFW)
- [ ] SSH key-only authentication
- [ ] Root login disabled
- [ ] Fail2ban installed and configured
- [ ] File upload size limits set

### ✅ Services

- [ ] Nginx installed and configured
- [ ] Gunicorn configuration tested
- [ ] Daphne WebSocket server tested
- [ ] Redis server running
- [ ] Celery worker configured
- [ ] Celery beat scheduler configured
- [ ] All systemd services created
- [ ] Services set to auto-start on boot

### ✅ Static Files & Media

- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Static file serving configured (WhiteNoise/Nginx)
- [ ] Media directory created with correct permissions
- [ ] Media backup strategy defined
- [ ] CDN configured (optional)

### ✅ Monitoring & Logging

- [ ] Application logging configured
- [ ] Log rotation set up
- [ ] Error tracking configured (Sentry)
- [ ] Health check endpoint working
- [ ] Uptime monitoring configured
- [ ] Performance monitoring set up (optional)
- [ ] Disk space monitoring enabled
- [ ] Service health monitoring active

### ✅ Backups

- [ ] Database backup script created
- [ ] Automated daily backups scheduled
- [ ] Backup restoration tested
- [ ] Off-site backup configured
- [ ] Media files backup strategy
- [ ] Backup retention policy defined

### ✅ Performance

- [ ] Gunicorn workers optimized (2×CPU+1)
- [ ] PostgreSQL connection pooling enabled
- [ ] Redis caching configured
- [ ] Static file compression enabled
- [ ] Database queries optimized
- [ ] Load testing completed

### ✅ Documentation

- [ ] README.md updated
- [ ] Deployment guide complete
- [ ] API documentation generated
- [ ] User manual created
- [ ] Runbook for common issues
- [ ] Architecture diagram updated

---

## Deployment Steps

### Phase 1: Server Preparation (30 minutes)

1. **Provision Server**
   ```bash
   # Ubuntu 22.04 LTS
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Dependencies**
   ```bash
   # Python, PostgreSQL, Redis, Nginx
   sudo apt install -y python3.9 postgresql-15 redis-server nginx
   ```

3. **Create Deployment User**
   ```bash
   sudo useradd -m -s /bin/bash ganglioside
   sudo mkdir -p /var/www/ganglioside
   sudo chown ganglioside:ganglioside /var/www/ganglioside
   ```

4. **Configure Firewall**
   ```bash
   sudo ufw allow OpenSSH
   sudo ufw allow 'Nginx Full'
   sudo ufw enable
   ```

### Phase 2: Database Setup (15 minutes)

5. **Create Database**
   ```bash
   sudo -u postgres psql
   CREATE DATABASE ganglioside_prod;
   CREATE USER ganglioside_user WITH PASSWORD 'STRONG_PASSWORD';
   GRANT ALL PRIVILEGES ON DATABASE ganglioside_prod TO ganglioside_user;
   \q
   ```

6. **Configure PostgreSQL**
   ```bash
   # Edit /etc/postgresql/15/main/pg_hba.conf
   # Add: local ganglioside_prod ganglioside_user md5
   sudo systemctl restart postgresql
   ```

### Phase 3: Application Deployment (30 minutes)

7. **Clone Repository**
   ```bash
   cd /var/www/ganglioside
   sudo -u ganglioside git clone <repository-url> .
   ```

8. **Create Virtual Environment**
   ```bash
   sudo -u ganglioside python3.9 -m venv venv
   sudo -u ganglioside venv/bin/pip install -r requirements/production.txt
   ```

9. **Configure Environment**
   ```bash
   sudo -u ganglioside cp .env.production .env
   # Edit .env with production values
   ```

10. **Run Migrations**
    ```bash
    sudo -u ganglioside venv/bin/python manage.py migrate
    ```

11. **Create Superuser**
    ```bash
    sudo -u ganglioside venv/bin/python manage.py createsuperuser
    ```

12. **Collect Static Files**
    ```bash
    sudo mkdir -p /var/www/ganglioside/static
    sudo chown ganglioside:ganglioside /var/www/ganglioside/static
    sudo -u ganglioside venv/bin/python manage.py collectstatic --noinput
    ```

### Phase 4: SSL & Nginx (20 minutes)

13. **Install Certbot**
    ```bash
    sudo apt install -y certbot python3-certbot-nginx
    ```

14. **Obtain SSL Certificate**
    ```bash
    sudo certbot certonly --nginx -d your-domain.com
    ```

15. **Configure Nginx**
    ```bash
    sudo cp deployment/nginx/ganglioside.conf /etc/nginx/sites-available/
    sudo ln -s /etc/nginx/sites-available/ganglioside.conf /etc/nginx/sites-enabled/
    # Edit and update domain name
    sudo nginx -t
    sudo systemctl reload nginx
    ```

### Phase 5: Systemd Services (15 minutes)

16. **Install Services**
    ```bash
    sudo cp deployment/systemd/*.service /etc/systemd/system/
    sudo systemctl daemon-reload
    ```

17. **Create Log Directories**
    ```bash
    sudo mkdir -p /var/log/celery /var/run/celery
    sudo chown ganglioside:ganglioside /var/log/celery /var/run/celery
    ```

18. **Enable Services**
    ```bash
    sudo systemctl enable ganglioside-django
    sudo systemctl enable ganglioside-daphne
    sudo systemctl enable ganglioside-celery-worker
    sudo systemctl enable ganglioside-celery-beat
    ```

19. **Start Services**
    ```bash
    sudo systemctl start ganglioside-django
    sudo systemctl start ganglioside-daphne
    sudo systemctl start ganglioside-celery-worker
    sudo systemctl start ganglioside-celery-beat
    ```

### Phase 6: Verification (10 minutes)

20. **Check Service Status**
    ```bash
    sudo systemctl status ganglioside-django
    sudo systemctl status ganglioside-daphne
    sudo systemctl status ganglioside-celery-worker
    sudo systemctl status ganglioside-celery-beat
    ```

21. **Test Health Endpoint**
    ```bash
    curl https://your-domain.com/health
    # Should return: {"status":"ok"}
    ```

22. **Test Admin Panel**
    ```bash
    # Visit: https://your-domain.com/admin
    # Login with superuser credentials
    ```

23. **Test Analysis Upload**
    - Upload sample CSV
    - Verify analysis completes
    - Check results display

### Phase 7: Monitoring & Backups (15 minutes)

24. **Configure Backups**
    ```bash
    sudo crontab -e -u ganglioside
    # Add: 0 2 * * * /var/www/ganglioside/scripts/backup_db.sh
    ```

25. **Set Up Monitoring**
    - Configure Sentry (if using)
    - Set up uptime monitoring
    - Configure disk space alerts

26. **Test Backup Restoration**
    ```bash
    # Run backup script
    /var/www/ganglioside/scripts/backup_db.sh
    # Test restoration on staging
    ```

---

## Post-Deployment Checklist

### ✅ Immediate Verification (First Hour)

- [ ] All services running without errors
- [ ] Health check endpoint responding
- [ ] Admin panel accessible
- [ ] User registration working
- [ ] File upload working
- [ ] Analysis workflow completes successfully
- [ ] WebSocket connections working
- [ ] Celery tasks processing
- [ ] Email notifications working (if configured)
- [ ] No errors in logs

### ✅ First 24 Hours

- [ ] Monitor error rates (Sentry/logs)
- [ ] Check performance metrics
- [ ] Verify backups completed
- [ ] Monitor disk space usage
- [ ] Check service uptime
- [ ] Test from external network
- [ ] Verify SSL certificate auto-renewal setup

### ✅ First Week

- [ ] Review error logs daily
- [ ] Monitor database performance
- [ ] Check backup integrity
- [ ] Review user feedback
- [ ] Monitor resource usage (CPU, RAM, disk)
- [ ] Test disaster recovery procedure

---

## Rollback Plan

If deployment fails:

1. **Stop Services**
   ```bash
   sudo systemctl stop ganglioside-*
   ```

2. **Revert Code**
   ```bash
   cd /var/www/ganglioside
   git reset --hard <previous-commit>
   ```

3. **Restore Database** (if migrations applied)
   ```bash
   gunzip < /var/backups/ganglioside/db_latest.sql.gz | \
       sudo -u postgres psql ganglioside_prod
   ```

4. **Restart Services**
   ```bash
   sudo systemctl start ganglioside-*
   ```

5. **Verify Health**
   ```bash
   curl https://your-domain.com/health
   ```

---

## Common Issues & Solutions

### Services Won't Start

**Check logs:**
```bash
sudo journalctl -u ganglioside-django -n 50
```

**Common causes:**
- Missing environment file → Check `/var/www/ganglioside/.env`
- Permission errors → Run `sudo chown -R ganglioside:ganglioside /var/www/ganglioside`
- Port already in use → Check with `sudo lsof -i :8000`

### 502 Bad Gateway

**Check:**
- Gunicorn running: `sudo systemctl status ganglioside-django`
- Nginx configuration: `sudo nginx -t`
- Nginx error logs: `sudo tail -f /var/log/nginx/error.log`

### Database Connection Errors

**Verify:**
- PostgreSQL running: `sudo systemctl status postgresql`
- Connection string in .env correct
- Database user permissions granted

### Static Files Not Loading

**Fix:**
```bash
sudo -u ganglioside venv/bin/python manage.py collectstatic --noinput
sudo chown -R ganglioside:ganglioside /var/www/ganglioside/static
```

---

## Security Hardening

### Post-Deployment Security

1. **Change Default Passwords**
   - Database passwords
   - Admin user password
   - SSH keys rotated

2. **Review Firewall Rules**
   ```bash
   sudo ufw status verbose
   ```

3. **Enable Automatic Updates**
   ```bash
   sudo dpkg-reconfigure --priority=low unattended-upgrades
   ```

4. **Configure Fail2ban**
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   ```

5. **Scan for Vulnerabilities**
   ```bash
   # Using Docker
   docker scan ganglioside:latest

   # Using Safety
   safety check -r requirements/production.txt
   ```

---

## Performance Optimization

### After Deployment

1. **Monitor Query Performance**
   - Enable Django Debug Toolbar (staging only)
   - Review slow query logs
   - Add database indexes as needed

2. **Optimize Gunicorn Workers**
   - Monitor CPU usage
   - Adjust worker count: `(2 × CPU cores) + 1`

3. **Configure Caching**
   - Enable Redis caching
   - Set cache timeout values
   - Cache frequently accessed data

4. **Enable GZIP Compression**
   - Configure in Nginx
   - Verify with: `curl -H "Accept-Encoding: gzip" -I https://your-domain.com`

---

## Documentation Maintenance

### Keep Updated

- [ ] Update version numbers
- [ ] Document all configuration changes
- [ ] Update architecture diagrams
- [ ] Record deployment dates
- [ ] Document incident resolutions
- [ ] Update runbook with new issues

---

## Success Criteria

### Production Ready When:

- ✅ All tests passing
- ✅ All services running
- ✅ SSL certificate valid
- ✅ Health checks passing
- ✅ Backups automated
- ✅ Monitoring active
- ✅ Documentation complete
- ✅ Load testing passed
- ✅ Security audit complete

---

**Total Deployment Time:** ~2-3 hours

**Status:** READY FOR PRODUCTION ✅

---

**Last Updated:** 2025-10-21
