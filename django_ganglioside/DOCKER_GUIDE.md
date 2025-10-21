# Docker Deployment Guide
## Ganglioside Analysis Platform

**Version:** 2.0
**Last Updated:** 2025-10-21

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker Architecture](#docker-architecture)
3. [Prerequisites](#prerequisites)
4. [Local Development](#local-development)
5. [Production Deployment](#production-deployment)
6. [Common Commands](#common-commands)
7. [Troubleshooting](#troubleshooting)
8. [Performance Tuning](#performance-tuning)

---

## Quick Start

### Using Make (Recommended)

```bash
# Clone repository
git clone https://github.com/your-org/ganglioside.git
cd ganglioside

# Build and start all services
make setup

# Access the application
open http://localhost
```

### Using Docker Compose Directly

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Run migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# View logs
docker-compose logs -f
```

---

## Docker Architecture

### Services

The application consists of 7 Docker services:

1. **postgres** - PostgreSQL 15 database
2. **redis** - Redis 7 cache and message broker
3. **django** - Django application (Gunicorn WSGI)
4. **daphne** - WebSocket server (Django Channels)
5. **celery_worker** - Background task processor
6. **celery_beat** - Periodic task scheduler
7. **nginx** - Reverse proxy and static file server

### Container Communication

```
┌─────────────┐
│   Nginx     │ :80, :443
└──────┬──────┘
       │
   ┌───┴────┬──────────┐
   │        │          │
   ▼        ▼          ▼
┌────────┐ ┌─────────┐ ┌──────────┐
│ Django │ │ Daphne  │ │  Static  │
│  :8000 │ │  :8001  │ │  Files   │
└───┬────┘ └────┬────┘ └──────────┘
    │           │
    ▼           ▼
┌─────────────────────┐
│   Redis :6379       │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌─────────┐  ┌─────────┐
│ Celery  │  │ Celery  │
│ Worker  │  │  Beat   │
└────┬────┘  └────┬────┘
     │            │
     └─────┬──────┘
           ▼
    ┌─────────────┐
    │ PostgreSQL  │
    │    :5432    │
    └─────────────┘
```

### Data Persistence

The following volumes persist data:

- **postgres_data** - Database files
- **redis_data** - Redis persistence
- **static_volume** - Collected Django static files
- **media_volume** - User-uploaded files

---

## Prerequisites

### Required Software

- Docker 20.10+
- Docker Compose 2.0+
- Git
- Make (optional, for convenience)

### System Requirements

- **CPU:** 2+ cores
- **RAM:** 4GB minimum (8GB recommended)
- **Disk:** 10GB free space

### Installation

**macOS:**
```bash
brew install docker docker-compose
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

**Windows:**
- Download Docker Desktop from https://docker.com/

---

## Local Development

### First-Time Setup

```bash
# Clone repository
git clone https://github.com/your-org/ganglioside.git
cd ganglioside

# Build images
make build

# Start services (includes migrations)
make up

# Create superuser
make createsuperuser
```

### Development Workflow

The `docker-compose.override.yml` file automatically applies development settings:

- **Live code reloading** - Changes are reflected immediately
- **Debug mode enabled** - Full error traces
- **Volume mounting** - Source code synced with container

```bash
# Start development servers
make up

# View logs
make logs

# Open Django shell
make shell

# Run tests
make test

# Stop services
make down
```

### Environment Variables

Create `.env` file in project root:

```env
# Django
DEBUG=True
SECRET_KEY=your-secret-key

# Database
POSTGRES_PASSWORD=dev_password

# Email (optional)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

---

## Production Deployment

### Production Configuration

Create `.env.production`:

```env
# Django
DEBUG=False
SECRET_KEY=STRONG_RANDOM_SECRET_KEY_HERE
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database
POSTGRES_PASSWORD=STRONG_DATABASE_PASSWORD

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Deploy to Production Server

```bash
# On production server
git clone https://github.com/your-org/ganglioside.git /var/www/ganglioside
cd /var/www/ganglioside

# Copy production environment
cp .env.production .env

# Build and start
docker-compose -f docker-compose.yml up -d --build

# Run migrations
docker-compose exec django python manage.py migrate

# Collect static files
docker-compose exec django python manage.py collectstatic --noinput

# Create superuser
docker-compose exec django python manage.py createsuperuser
```

### SSL/TLS with Let's Encrypt

Update `docker-compose.yml` to add Certbot:

```yaml
services:
  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

Obtain certificate:

```bash
docker-compose run --rm certbot certonly --webroot \
    -w /var/www/certbot \
    -d your-domain.com \
    -d www.your-domain.com \
    --email your-email@example.com \
    --agree-tos
```

---

## Common Commands

### Service Management

```bash
# Start all services
make up

# Stop all services
make down

# Restart services
make restart

# View service status
make ps

# View resource usage
make top
```

### Django Management

```bash
# Run migrations
make migrate

# Create new migrations
make makemigrations

# Create superuser
make createsuperuser

# Collect static files
make collectstatic

# Open Django shell
make shell

# Open bash in container
make bash
```

### Database Operations

```bash
# Access PostgreSQL shell
make dbshell

# Backup database
make backup-db

# Restore database
cat backup_file.sql | docker-compose exec -T postgres psql -U ganglioside_user -d ganglioside_prod
```

### Testing & Quality

```bash
# Run tests
make test

# Run tests with coverage
make coverage

# Lint code
make lint

# Format code
make format
```

### Logs

```bash
# View all logs
make logs

# View specific service logs
docker-compose logs -f django
docker-compose logs -f celery_worker
docker-compose logs -f postgres

# View last 100 lines
docker-compose logs --tail=100 django
```

### Cleanup

```bash
# Remove containers and volumes
make clean

# Remove all unused Docker resources
docker system prune -a
```

---

## Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker-compose logs django
```

**Common issues:**
- Port already in use: Change port in `docker-compose.yml`
- Missing `.env` file: Copy from `.env.production` template
- Permission denied: Run `chmod +x` on scripts

### Database Connection Errors

**Verify PostgreSQL is running:**
```bash
docker-compose ps postgres
docker-compose logs postgres
```

**Check connection:**
```bash
docker-compose exec postgres pg_isready -U ganglioside_user
```

**Reset database:**
```bash
docker-compose down -v
docker-compose up -d postgres
docker-compose exec django python manage.py migrate
```

### Celery Tasks Not Processing

**Check worker status:**
```bash
docker-compose logs celery_worker
```

**Verify Redis connection:**
```bash
docker-compose exec redis redis-cli ping
```

**Inspect task queue:**
```bash
docker-compose exec redis redis-cli
> KEYS celery*
> LLEN celery
```

### Static Files Not Loading

**Collect static files:**
```bash
make collectstatic
```

**Verify Nginx configuration:**
```bash
docker-compose exec nginx nginx -t
```

**Check volume permissions:**
```bash
docker-compose exec django ls -la /app/static
```

### Out of Memory

**Check resource usage:**
```bash
docker stats
```

**Increase Docker memory:**
- Docker Desktop → Settings → Resources → Memory → 8GB

**Reduce worker processes:**
Edit `gunicorn.conf.py`:
```python
workers = 2  # Reduce from 8
```

---

## Performance Tuning

### Database Optimization

**Connection pooling:**
```python
# config/settings/production.py
DATABASES['default']['CONN_MAX_AGE'] = 600
```

**Increase shared buffers:**
Create `postgres.conf`:
```conf
shared_buffers = 256MB
effective_cache_size = 1GB
```

Mount in `docker-compose.yml`:
```yaml
postgres:
  volumes:
    - ./postgres.conf:/etc/postgresql/postgresql.conf
```

### Gunicorn Workers

Formula: `(2 x CPU cores) + 1`

Edit `gunicorn.conf.py`:
```python
workers = 8  # For 4-core server
worker_class = "gevent"  # For I/O-bound workloads
```

### Redis Optimization

```yaml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### Celery Concurrency

```yaml
celery_worker:
  command: celery -A config worker --loglevel=info --concurrency=8
```

---

## Health Monitoring

### Health Checks

Built-in health checks are configured for all services:

```bash
# Check application health
curl http://localhost/health

# Docker health status
docker-compose ps
```

### Monitoring Tools

**cAdvisor (Container monitoring):**
```yaml
cadvisor:
  image: gcr.io/cadvisor/cadvisor:latest
  ports:
    - "8080:8080"
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
```

**Flower (Celery monitoring):**
```yaml
flower:
  build: .
  command: celery -A config flower --port=5555
  ports:
    - "5555:5555"
```

---

## CI/CD Integration

### GitHub Actions

The `.github/workflows/ci-cd.yml` file provides:

- ✅ Automated testing on push/PR
- ✅ Code linting and security scanning
- ✅ Docker image building
- ✅ Automated deployment to production

### Docker Registry

**Build and push:**
```bash
# Tag image
docker tag ganglioside_django:latest username/ganglioside:v1.0

# Push to Docker Hub
docker push username/ganglioside:v1.0
```

**Pull and run:**
```bash
docker pull username/ganglioside:v1.0
docker run -d -p 8000:8000 username/ganglioside:v1.0
```

---

## Security Best Practices

1. **Don't commit secrets** - Use `.env` files (in `.gitignore`)
2. **Run as non-root** - Containers use `ganglioside` user
3. **Keep images updated** - Regularly rebuild with latest base images
4. **Scan for vulnerabilities** - Use `docker scan` or Trivy
5. **Use multi-stage builds** - Reduces final image size
6. **Enable security headers** - Configured in Nginx
7. **Limit container resources** - Set CPU and memory limits

```yaml
django:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

---

## Additional Resources

- **Official Docker Docs:** https://docs.docker.com/
- **Django Deployment:** https://docs.djangoproject.com/en/4.2/howto/deployment/
- **Gunicorn Configuration:** https://docs.gunicorn.org/
- **Celery Best Practices:** https://docs.celeryproject.org/

---

**Last Updated:** 2025-10-21
