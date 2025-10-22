# CLAUDE.md

This file provides guidance to Claude Code when working with this Django-based Ganglioside Analysis Platform.

## Project Overview

**LC-MS/MS Ganglioside Analysis Platform** - Automated identification and validation of ganglioside compounds from liquid chromatography-mass spectrometry data using a proprietary 5-rule algorithm.

**Domain**: Analytical chemistry, lipidomics, mass spectrometry data analysis
**Stack**: Django 4.2 + Django REST Framework + Celery + Docker
**Python Version**: 3.9 (Docker), 3.13+ (local development)

---

## Quick Start with Docker

### Running the Application

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Common Operations

```bash
# Run migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Access Django shell
docker-compose exec django python manage.py shell

# Run tests
docker-compose exec django pytest
```

---

## Architecture

### Django Apps

1. **apps/analysis/** - Core analysis engine
   - Models: AnalysisSession, Compound, RegressionResult
   - Services: GangliosideProcessor (5-rule algorithm)
   - API: REST endpoints for analysis workflow

2. **apps/visualization/** - Plotly chart generation
   - 2D scatter plots (RT vs Log P)
   - 3D distribution plots
   - Category-based visualizations

3. **config/** - Django settings and configuration
   - settings/base.py - Common settings
   - settings/development.py - Dev environment
   - settings/production.py - Production environment

### The 5-Rule Analysis Pipeline

**Rule 1: Prefix-Based Multiple Regression**
- Groups compounds by prefix (GD1, GM3, GT1, etc.)
- Fits regression model: RT ~ Log P + features
- Features: carbon length, unsaturation, sugar count, modifications
- Model: Ridge regression (α=1.0)
- Validation: R² ≥ 0.75, outlier detection ±2.5σ

**Rule 2-3: Sugar Count & Isomer Classification**
- Parses compound names: `PREFIX(a:b;c)`
- Calculates total sugars from prefix
- Identifies structural isomers

**Rule 4: O-Acetylation Validation**
- Validates RT(compound+OAc) > RT(compound_base)

**Rule 5: Fragmentation Detection**
- Groups by lipid composition within ±0.1 min RT window
- Consolidates fragmented compounds

---

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| **Django** | 8000 | Web app (Gunicorn) |
| **Daphne** | 8001 | WebSocket server |
| **PostgreSQL** | 5432 | Database |
| **Redis** | 6379 | Cache & message broker |
| **Celery Worker** | - | Background tasks |
| **Celery Beat** | - | Task scheduler |
| **Nginx** | 80, 443 | Reverse proxy |

---

## Key Files

### Configuration
- `config/settings/base.py` - Base Django settings
- `config/asgi.py` - ASGI configuration for Channels
- `config/celery.py` - Celery configuration
- `.env` - Environment variables

### Docker
- `Dockerfile` - Django + Gunicorn image
- `Dockerfile.celery` - Celery worker image
- `docker-compose.yml` - Service orchestration
- `gunicorn.conf.py` - Gunicorn configuration

### Requirements
- `requirements/base.txt` - Core dependencies
- `requirements/development.txt` - Dev tools
- `requirements/production.txt` - Production packages

---

## API Endpoints

### Analysis
- `POST /api/analysis/upload/` - Upload CSV file
- `POST /api/analysis/analyze/` - Run 5-rule algorithm
- `GET /api/analysis/sessions/` - List analysis sessions
- `GET /api/analysis/sessions/{id}/` - Get session details
- `DELETE /api/analysis/sessions/{id}/` - Delete session

### Visualization
- `POST /api/visualization/generate/` - Generate charts
- `GET /api/visualization/charts/{id}/` - Get chart HTML

### Documentation
- `GET /api/schema/` - OpenAPI schema
- `GET /api/schema/swagger-ui/` - Interactive API docs
- `GET /api/schema/redoc/` - Alternative API docs

---

## Data Format

### Input CSV Requirements
```csv
Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),9.572,1000000,1.53,T
GM1(36:1;O2),10.452,500000,4.00,F
```

**Required columns:**
- `Name` - Compound identifier (format: PREFIX(a:b;c))
- `RT` - Retention time (minutes, float)
- `Volume` - Peak volume/area (float)
- `Log P` - Lipophilicity (float)
- `Anchor` - Training flag ("T" = train, "F" = test)

### Compound Naming Convention
```
PREFIX(a:b;c)[+MODIFICATIONS]

Examples:
- GD1(36:1;O2) → GD1 prefix, C36 chain, 1 unsaturation, O2
- GD1+dHex(36:1;O2) → GD1 with deoxyhexose modification
- GM3+OAc(18:1;O2) → GM3 with O-acetylation
```

---

## Development Workflow

### Making Code Changes

1. Edit code locally
2. Rebuild affected services:
   ```bash
   docker-compose build django
   docker-compose up -d
   ```

### Database Changes

1. Create migration:
   ```bash
   docker-compose exec django python manage.py makemigrations
   ```

2. Apply migration:
   ```bash
   docker-compose exec django python manage.py migrate
   ```

### Adding Dependencies

1. Add package to `requirements/base.txt` or `requirements/production.txt`
2. Rebuild images:
   ```bash
   docker-compose build --no-cache
   ```

---

## Testing

### Run All Tests
```bash
docker-compose exec django pytest
```

### Run Specific Tests
```bash
docker-compose exec django pytest apps/analysis/tests/
docker-compose exec django pytest apps/analysis/tests/test_processor.py
```

### With Coverage
```bash
docker-compose exec django pytest --cov=apps --cov-report=html
```

---

## Environment Variables

### Required Variables (.env file)
```bash
# Django
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://ganglioside_user:password@postgres:5432/ganglioside_prod

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Analysis Settings
DEFAULT_R2_THRESHOLD=0.75
DEFAULT_OUTLIER_THRESHOLD=2.5
DEFAULT_RT_TOLERANCE=0.1

# File Upload (50MB in bytes)
MAX_UPLOAD_SIZE=52428800
```

---

## Troubleshooting

### Services Won't Start
```bash
# Check logs
docker-compose logs django

# Restart services
docker-compose restart

# Complete reset
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Database Connection Errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Restart
docker-compose restart postgres
```

### Celery Not Processing Tasks
```bash
# Check worker logs
docker-compose logs celery_worker

# Restart workers
docker-compose restart celery_worker celery_beat
```

---

## Production Deployment

See `DEPLOYMENT_GUIDE.md` for comprehensive production deployment instructions.

### Quick Production Checklist
- [ ] Set strong `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Set strong database password
- [ ] Enable SSL/TLS (HTTPS)
- [ ] Configure Sentry for error tracking
- [ ] Set up database backups
- [ ] Configure email notifications
- [ ] Enable rate limiting
- [ ] Review security settings

---

## Resources

- **Docker Guide**: `DOCKER_DEPLOYMENT_QUICKSTART.md`
- **Testing Guide**: `TESTING_GUIDE.md`
- **API Documentation**: http://localhost/api/docs (when running)
- **Admin Panel**: http://localhost/admin

---

**Last Updated**: October 22, 2025
**Version**: 2.0 (Django Migration Complete)
