# Docker Deployment Quick Start Guide
## Ganglioside Analysis Platform v2.0

**Last Updated:** 2025-10-21

---

## Prerequisites Installation

### Step 1: Install Docker Desktop

**For macOS:**

```bash
# Download from Docker website
open https://www.docker.com/products/docker-desktop/

# OR install via Homebrew (requires password)
brew install --cask docker
```

**After installation:**
1. Open Docker Desktop application from `/Applications/Docker.app`
2. Wait for Docker Desktop to start (whale icon in menu bar)
3. Verify installation:

```bash
docker --version
# Should show: Docker version 20.10+

docker-compose --version
# Should show: docker-compose version 2.0+
```

---

## Quick Deployment (5 Minutes)

### Option 1: One-Command Setup (Recommended)

```bash
# Navigate to project directory
cd /Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside

# Run complete setup
make setup
```

**This command will:**
1. Build all Docker images
2. Start all 7 services
3. Run database migrations
4. Create superuser (you'll be prompted)
5. Collect static files

**Access the application:**
- Web App: http://localhost
- Admin Panel: http://localhost/admin
- API Docs: http://localhost/api/docs
- Health Check: http://localhost/health

### Option 2: Manual Step-by-Step

```bash
cd /Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside

# 1. Build Docker images (first time only)
docker-compose build

# 2. Start all services in background
docker-compose up -d

# 3. Wait 10 seconds for services to start
sleep 10

# 4. Run database migrations
docker-compose exec django python manage.py migrate

# 5. Create superuser
docker-compose exec django python manage.py createsuperuser
# Enter username, email, password when prompted

# 6. Collect static files
docker-compose exec django python manage.py collectstatic --noinput

# 7. Verify all services are running
docker-compose ps
```

---

## Services Running

After deployment, you'll have 7 containers running:

| Service | Container Name | Port | Purpose |
|---------|---------------|------|---------|
| **PostgreSQL** | ganglioside_postgres | 5432 | Production database |
| **Redis** | ganglioside_redis | 6379 | Cache & message broker |
| **Django** | ganglioside_django | 8000 | Web application (Gunicorn) |
| **Daphne** | ganglioside_daphne | 8001 | WebSocket server |
| **Celery Worker** | ganglioside_celery_worker | - | Background tasks |
| **Celery Beat** | ganglioside_celery_beat | - | Task scheduler |
| **Nginx** | ganglioside_nginx | 80 | Reverse proxy |

---

## Common Operations

### View Logs

```bash
# All services
make logs

# Or specific service
docker-compose logs -f django
docker-compose logs -f celery_worker
docker-compose logs -f postgres
```

### Stop Services

```bash
make down
# OR
docker-compose down
```

### Restart Services

```bash
make restart
# OR
docker-compose restart
```

### View Running Containers

```bash
make ps
# OR
docker-compose ps
```

### Access Django Shell

```bash
make shell
# OR
docker-compose exec django python manage.py shell
```

### Access Container Bash

```bash
make bash
# OR
docker-compose exec django /bin/bash
```

### Run Database Migrations

```bash
make migrate
# OR
docker-compose exec django python manage.py migrate
```

### Create Superuser

```bash
make createsuperuser
# OR
docker-compose exec django python manage.py createsuperuser
```

### Collect Static Files

```bash
make collectstatic
# OR
docker-compose exec django python manage.py collectstatic --noinput
```

---

## Testing the Deployment

### 1. Health Check

```bash
curl http://localhost/health
# Expected: {"status":"ok"}
```

### 2. Access Admin Panel

Open browser: http://localhost/admin
- Login with superuser credentials
- Verify you can see Analysis Sessions, Compounds, etc.

### 3. Upload Test Analysis

1. Go to http://localhost
2. Click "New Analysis"
3. Upload sample CSV file
4. Watch real-time progress updates
5. View results

### 4. Check API Documentation

Open browser: http://localhost/api/docs
- Swagger UI with all endpoints
- Interactive API testing

---

## Configuration

### Environment Variables

Edit `.env` file in the project root:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# Django
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# Analysis Settings
DEFAULT_R2_THRESHOLD=0.75
DEFAULT_OUTLIER_THRESHOLD=2.5
DEFAULT_RT_TOLERANCE=0.1
```

### Production Settings

For production deployment:

1. **Set Strong Passwords:**
   ```bash
   POSTGRES_PASSWORD=$(openssl rand -base64 32)
   SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
   ```

2. **Configure Domain:**
   ```bash
   ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
   ```

3. **Enable SSL (in production):**
   - Update `docker-compose.yml` Nginx config
   - Add SSL certificates
   - See `DEPLOYMENT_GUIDE.md` for details

---

## Troubleshooting

### Issue: Port Already in Use

```bash
# Find process using port 80
lsof -i :80

# Kill the process (if safe)
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8080:80"  # Use port 8080 instead
```

### Issue: Services Won't Start

```bash
# Check logs
docker-compose logs

# Restart Docker Desktop
# macOS: Click Docker icon → Restart

# Remove all containers and start fresh
docker-compose down -v
docker-compose up -d
```

### Issue: Database Connection Error

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Issue: "Permission Denied" Errors

```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Issue: Out of Disk Space

```bash
# Clean up unused Docker resources
docker system prune -a

# Remove old volumes (WARNING: deletes data)
docker-compose down -v
```

---

## Data Persistence

### Database Data

Database data is stored in Docker volume: `postgres_data`

**Backup database:**
```bash
make backup-db
# OR
docker-compose exec postgres pg_dump -U ganglioside_user ganglioside_prod > backup_$(date +%Y%m%d).sql
```

**Restore database:**
```bash
cat backup_20251021.sql | docker-compose exec -T postgres psql -U ganglioside_user ganglioside_prod
```

### Media Files

User uploads are stored in volume: `media_volume`

**Backup media files:**
```bash
docker run --rm -v ganglioside_media_volume:/data -v $(pwd):/backup alpine tar czf /backup/media_backup.tar.gz -C /data .
```

**Restore media files:**
```bash
docker run --rm -v ganglioside_media_volume:/data -v $(pwd):/backup alpine tar xzf /backup/media_backup.tar.gz -C /data
```

---

## Updating the Application

### Pull Latest Changes

```bash
# Stop services
docker-compose down

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose build
docker-compose up -d

# Run migrations
docker-compose exec django python manage.py migrate

# Collect static files
docker-compose exec django python manage.py collectstatic --noinput
```

### Or use deployment script:

```bash
make deploy
```

---

## Performance Optimization

### Allocate More Resources

Docker Desktop → Settings → Resources:
- **CPUs:** 4 (recommended)
- **Memory:** 8GB (recommended)
- **Disk:** 60GB

### Monitor Resource Usage

```bash
make top
# OR
docker stats
```

---

## Security Considerations

### For Development:

- ✅ Default passwords are OK
- ✅ HTTP (no SSL) is fine
- ✅ DEBUG=True is acceptable

### For Production:

- ❌ Change all default passwords
- ❌ Enable SSL/TLS (HTTPS only)
- ❌ Set DEBUG=False
- ❌ Use environment-specific .env files
- ✅ Enable firewall
- ✅ Keep Docker updated
- ✅ Scan images for vulnerabilities

```bash
# Scan images for vulnerabilities
docker scan ganglioside_django:latest
```

---

## Makefile Commands Reference

| Command | Description |
|---------|-------------|
| `make setup` | Complete initial setup |
| `make build` | Build Docker images |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make restart` | Restart services |
| `make logs` | View all logs |
| `make ps` | Show running containers |
| `make shell` | Open Django shell |
| `make bash` | Open bash in Django container |
| `make migrate` | Run migrations |
| `make makemigrations` | Create migrations |
| `make createsuperuser` | Create admin user |
| `make collectstatic` | Collect static files |
| `make test` | Run tests |
| `make coverage` | Run tests with coverage |
| `make lint` | Run linters |
| `make clean` | Remove containers and volumes |
| `make deploy` | Deploy updates |
| `make health` | Check application health |

---

## Next Steps

### 1. Test the Application

- ✅ Upload sample CSV
- ✅ Run analysis
- ✅ View results
- ✅ Check API endpoints
- ✅ Test WebSocket updates

### 2. Customize Configuration

- Edit `.env` file
- Adjust analysis parameters
- Configure email notifications

### 3. Add Your Data

- Upload your LC-MS/MS data files
- Configure analysis thresholds
- Save and manage sessions

### 4. Monitor Performance

- Check logs: `make logs`
- Monitor resources: `make top`
- Review metrics in admin panel

---

## Getting Help

### Documentation

- **Full Docker Guide:** `DOCKER_GUIDE.md`
- **Deployment Guide:** `DEPLOYMENT_GUIDE.md`
- **Testing Guide:** `TESTING_GUIDE.md`
- **API Docs:** http://localhost/api/docs (when running)

### Common Issues

See `DOCKER_GUIDE.md` → Troubleshooting section

### Support

- GitHub Issues: [Repository URL]
- Documentation: See guides in project root

---

## Quick Reference Card

```bash
# START
make setup              # First time
make up                 # Subsequent starts

# USE
open http://localhost   # Web app
open http://localhost/admin  # Admin panel

# MANAGE
make logs              # View logs
make shell             # Django shell
make migrate           # Run migrations

# STOP
make down              # Stop services

# CLEAN
make clean             # Remove everything
```

---

**Status:** Ready for Deployment ✅
**Total Setup Time:** 5-10 minutes (after Docker Desktop installed)
**Difficulty:** Easy (one command)

---

**Last Updated:** 2025-10-21
