# Ganglioside Analysis Platform v2.0
## Django-Based LC-MS/MS Analysis with 5-Rule Algorithm

[![CI/CD](https://github.com/your-org/ganglioside/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-org/ganglioside/actions)
[![Coverage](https://img.shields.io/badge/coverage-82%25-brightgreen.svg)](https://github.com/your-org/ganglioside)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/django-4.2-green.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Production-ready Django platform for automated ganglioside identification and validation from LC-MS/MS data using a proprietary 5-rule algorithm with real-time WebSocket updates, background task processing, and comprehensive API.

---

## 🎯 Features

- ✅ **5-Rule Analysis Algorithm** - Proprietary ganglioside identification system
- ✅ **Real-time Updates** - WebSocket progress notifications via Django Channels
- ✅ **Background Processing** - Async analysis with Celery + Redis
- ✅ **REST API** - Comprehensive DRF-based API with auto-generated docs
- ✅ **Production Database** - PostgreSQL with optimized queries
- ✅ **Docker Support** - Full containerization with docker-compose
- ✅ **CI/CD Pipeline** - Automated testing, security scanning, deployment
- ✅ **Admin Panel** - Django admin for data management
- ✅ **70+ Tests** - Unit, integration, and performance tests (82% coverage)
- ✅ **Comprehensive Docs** - Deployment, testing, API, Docker guides

---

## 🚀 Quick Start

### Option 1: Docker (Recommended - Production Ready)

```bash
# Navigate to project directory
cd django_ganglioside

# Create environment file
cp .env.example .env

# Build and start all 7 services
docker-compose build
docker-compose up -d

# Run database migrations
docker-compose exec django python manage.py migrate

# Create admin user
docker-compose exec django python manage.py createsuperuser

# Access the application
open http://localhost
```

**All Services Running:**
- 🌐 Web application: http://localhost (Django + Gunicorn)
- 👤 Admin panel: http://localhost/admin (username: admin, password: admin123)
- 📚 API docs: http://localhost/api/schema/swagger-ui/
- ❤️ Health check: http://localhost/health
- 🔌 WebSocket: ws://localhost:8001 (Real-time updates)
- ⚙️ Celery Worker: Background task processing
- ⏰ Celery Beat: Scheduled tasks

### Option 2: Local Development

```bash
# Prerequisites: Python 3.9+, PostgreSQL 15, Redis 7

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/production.txt

# Copy environment file
cp .env.production .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Start development server
python manage.py runserver
```

---

## 📊 Architecture

### System Overview

```
┌──────────────────────────────────────────────┐
│             Nginx (Reverse Proxy)            │
│        SSL/TLS, Static Files, Rate Limiting  │
└────────────┬───────────────────┬─────────────┘
             │                   │
   ┌─────────▼────────┐  ┌──────▼──────────┐
   │   Django App     │  │   Daphne        │
   │   (Gunicorn)     │  │   (WebSocket)   │
   │   Port 8000      │  │   Port 8001     │
   └────────┬─────────┘  └──────┬──────────┘
            │                   │
            └────────┬──────────┘
                     │
            ┌────────▼─────────┐
            │  Redis (Cache    │
            │  & Message       │
            │  Broker)         │
            └────────┬─────────┘
                     │
        ┌────────────┴──────────────┐
        │                           │
┌───────▼────────┐       ┌─────────▼────────┐
│ Celery Worker  │       │  Celery Beat     │
│ (Background    │       │  (Scheduler)     │
│  Tasks)        │       │                  │
└───────┬────────┘       └─────────┬────────┘
        │                          │
        └──────────┬───────────────┘
                   │
        ┌──────────▼──────────┐
        │   PostgreSQL 15     │
        │   (Production DB)   │
        └─────────────────────┘
```

### Technology Stack

**Backend:**
- Django 4.2 - Web framework
- Django REST Framework 3.14 - API
- Django Channels 4.0 - WebSockets
- Celery 5.3 - Background tasks
- PostgreSQL 15 - Database
- Redis 7 - Cache & broker

**Frontend:**
- HTML5/CSS3/JavaScript
- Plotly.js - Interactive visualizations
- Bootstrap 5 - UI framework

**Infrastructure:**
- Docker & Docker Compose
- Nginx - Reverse proxy
- Gunicorn - WSGI server
- Daphne - ASGI server
- GitHub Actions - CI/CD

**Development:**
- pytest - Testing framework
- Black - Code formatting
- Flake8 - Linting
- Coverage.py - Test coverage

---

## 📁 Project Structure

```
django_ganglioside/
├── apps/                           # Django applications
│   ├── analysis/                   # Core analysis engine
│   │   ├── models.py              # Data models
│   │   ├── views.py               # API views
│   │   ├── serializers.py         # DRF serializers
│   │   ├── services/              # Business logic
│   │   │   ├── analysis_service.py
│   │   │   └── regression_analyzer.py
│   │   ├── tasks.py               # Celery tasks
│   │   ├── consumers.py           # WebSocket consumers
│   │   └── admin.py               # Admin configuration
│   ├── visualization/             # Chart generation
│   └── core/                      # Shared utilities
│
├── config/                        # Django configuration
│   ├── settings/
│   │   ├── base.py               # Base settings
│   │   ├── development.py        # Dev overrides
│   │   └── production.py         # Production config
│   ├── urls.py                   # URL routing
│   ├── wsgi.py                   # WSGI application
│   ├── asgi.py                   # ASGI application
│   └── celery.py                 # Celery config
│
├── tests/                        # Test suite
│   ├── unit/                     # Unit tests
│   ├── integration/              # Integration tests
│   ├── performance/              # Performance tests
│   └── conftest.py               # Test fixtures
│
├── deployment/                   # Deployment configs
│   ├── nginx/                    # Nginx configurations
│   ├── systemd/                  # Systemd service files
│   └── scripts/                  # Deployment scripts
│
├── requirements/                 # Dependencies
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── static/                       # Static files
├── media/                        # User uploads
├── Dockerfile                    # Django container
├── Dockerfile.celery             # Celery container
├── docker-compose.yml            # Full stack
├── Makefile                      # Common commands
├── pytest.ini                    # Test configuration
├── pyproject.toml                # Tool configuration
└── manage.py                     # Django CLI
```

---

## 🔬 The 5-Rule Analysis Algorithm

### Overview

The proprietary 5-rule algorithm identifies and validates gangliosides through sequential analysis:

### Rule 1: Prefix-Based Multiple Regression
Groups compounds by prefix (GD1, GM3, etc.), fits regression model using anchor compounds.

**Features:**
- Log P (lipophilicity)
- Carbon chain length
- Unsaturation count
- Sugar count
- Modifications (OAc, dHex, etc.)

**Model:**
- Ridge regression (α=1.0) with regularization
- R² threshold: 0.75 (configurable)
- Outlier detection: ±2.5σ standardized residuals

**Output:**
- Valid compounds passing regression
- Outliers with reasons
- Model coefficients per prefix group

### Rule 2-3: Sugar Count & Isomer Classification
Calculates total sugars from compound nomenclature.

**Formula:**
```
Total Sugars = e_value + (5 - f_value)
```
Where:
- e ∈ {A:0, M:1, D:2, T:3, Q:4, P:5} (sialic acid count)
- f ∈ {1, 2, 3, 4} (remaining sugars)

**Isomer Detection:**
- Identifies structural isomers (GD1a/b, GQ1b/c)
- Flags when f=1

### Rule 4: O-Acetylation Validation
Validates chemical expectation that O-acetylation increases retention time.

**Logic:**
```python
RT(compound+OAc) > RT(compound_base)
```

**Output:**
- Valid O-acetylated compounds
- Invalid compounds violating expectation

### Rule 5: In-Source Fragmentation Detection
Groups by lipid composition, detects fragments within RT tolerance.

**Algorithm:**
- Group by suffix (lipid composition: a:b;c)
- Within ±0.1 min RT window
- Keep compound with highest sugar count
- Consolidate volumes from suspected fragments

**Output:**
- Filtered compounds (fragments removed)
- Fragmentation events logged

### Categorization
Classifies by sialic acid content (prefix 'e' value):

| Category | Sialic Acids | Color | Example |
|----------|--------------|-------|---------|
| GM | 1 (M) | Blue | GM1, GM3 |
| GD | 2 (D) | Orange | GD1, GD3 |
| GT | 3 (T) | Green | GT1, GT3 |
| GQ | 4 (Q) | Red | GQ1 |
| GP | 5 (P) | Purple | GP1 |

---

## 🧪 Testing

### Run Tests

```bash
# All tests
make test

# With coverage
make coverage

# Specific types
pytest -m unit                    # Unit tests only
pytest -m integration             # Integration tests
pytest -m "not slow"              # Skip slow tests

# Parallel execution
pytest -n auto
```

### Coverage Report

```bash
# Generate HTML report
pytest --cov=apps --cov=config --cov-report=html

# Open report
open htmlcov/index.html
```

### Test Statistics

| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| Models | 20+ | 90% | ✅ |
| Services | 25+ | 88% | ✅ |
| API Views | 25+ | 85% | ✅ |
| Celery Tasks | 15+ | 75% | ✅ |
| **Total** | **70+** | **82%** | ✅ |

---

## 🐳 Docker Deployment

### Using Make (Easiest)

```bash
# Full setup (build + migrate + superuser)
make setup

# Start services
make up

# View logs
make logs

# Run migrations
make migrate

# Stop services
make down

# Clean everything
make clean
```

### Using Docker Compose

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Run migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Stop services
docker-compose down
```

### Services Included

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| postgres | postgres:15-alpine | 5432 | Database |
| redis | redis:7-alpine | 6379 | Cache/Broker |
| django | Custom | 8000 | Web app |
| daphne | Custom | 8001 | WebSocket |
| celery_worker | Custom | - | Tasks |
| celery_beat | Custom | - | Scheduler |
| nginx | nginx:alpine | 80/443 | Proxy |

---

## 📚 API Documentation

### Auto-Generated Docs

- **Swagger UI**: http://localhost:8000/api/docs/
- **ReDoc**: http://localhost:8000/api/redoc/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

### Key Endpoints

**Analysis:**
```
POST   /api/analysis/sessions/          Create analysis session
GET    /api/analysis/sessions/          List user sessions
GET    /api/analysis/sessions/{id}/     Session details
PATCH  /api/analysis/sessions/{id}/     Update session
DELETE /api/analysis/sessions/{id}/     Delete session
GET    /api/analysis/sessions/{id}/compounds/  List compounds
```

**Authentication:**
```
POST   /api/auth/login/                 User login
POST   /api/auth/logout/                User logout
POST   /api/auth/register/              Register new user
GET    /api/auth/me/                    Current user info
```

**Health:**
```
GET    /health/                         System health check
```

### Example Request

```bash
# Create analysis session
curl -X POST http://localhost:8000/api/analysis/sessions/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "name=My Analysis" \
  -F "data_type=porcine" \
  -F "uploaded_file=@data.csv"
```

---

## 🚀 Production Deployment

### Prerequisites

- Ubuntu 22.04 LTS server
- Domain name with DNS configured
- SSL certificate (Let's Encrypt)
- 4GB+ RAM, 2+ CPU cores
- 20GB+ disk space

### Deployment Steps

1. **Server Setup** (30 min)
   - Install dependencies (Python, PostgreSQL, Redis, Nginx)
   - Create deployment user
   - Configure firewall

2. **Application Deployment** (30 min)
   - Clone repository
   - Install Python packages
   - Run migrations
   - Collect static files

3. **Nginx & SSL** (20 min)
   - Configure Nginx reverse proxy
   - Obtain SSL certificate
   - Enable HTTPS redirect

4. **Systemd Services** (15 min)
   - Install service files
   - Enable auto-start
   - Start all services

5. **Verification** (10 min)
   - Test health endpoint
   - Upload sample analysis
   - Verify background tasks

**Total Time:** ~2 hours

### Automated Deployment

```bash
# On production server
cd /var/www/ganglioside
sudo ./deployment/scripts/deploy.sh
```

### Guides

- **Full Guide**: `DEPLOYMENT_GUIDE.md`
- **Checklist**: `PRODUCTION_CHECKLIST.md`
- **Docker Guide**: `DOCKER_GUIDE.md`
- **CI/CD Guide**: `CI_CD_GUIDE.md`

---

## 🛠️ Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/ganglioside.git
cd ganglioside

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements/production.txt

# Set up pre-commit hooks (optional)
pre-commit install

# Run development server
python manage.py runserver
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Run all quality checks
black . && isort . && flake8
```

### Common Commands

```bash
# Django management
python manage.py migrate             # Run migrations
python manage.py makemigrations      # Create migrations
python manage.py createsuperuser     # Create admin user
python manage.py shell               # Interactive shell

# Celery
celery -A config worker -l info      # Start worker
celery -A config beat -l info        # Start scheduler
celery -A config flower              # Monitor (port 5555)

# Testing
pytest                               # Run tests
pytest --cov                         # With coverage
pytest -m unit                       # Unit tests only
```

---

## 📖 Documentation

### Available Guides

| Document | Description | Lines |
|----------|-------------|-------|
| README.md | This file | 600+ |
| DEPLOYMENT_GUIDE.md | Production deployment | 400+ |
| DOCKER_GUIDE.md | Docker usage | 350+ |
| CI_CD_GUIDE.md | CI/CD pipeline | 300+ |
| TESTING_GUIDE.md | Testing practices | 350+ |
| PRODUCTION_CHECKLIST.md | Deployment checklist | 300+ |
| WEEK2_COMPLETE.md | Week 2 summary | 500+ |
| WEEK3_PREVIEW.md | Week 3 roadmap | 400+ |

**Total:** 3,500+ lines of documentation

---

## 🔒 Security

### Features

- ✅ SSL/TLS encryption (HTTPS only)
- ✅ HSTS headers enabled
- ✅ CSRF protection
- ✅ SQL injection prevention (Django ORM)
- ✅ XSS protection
- ✅ Rate limiting (10 req/s API, 2 req/m uploads)
- ✅ Secure password hashing (PBKDF2)
- ✅ Session security
- ✅ File upload validation
- ✅ Automated security scanning (Bandit, Safety)

### Security Scanning

```bash
# Run Bandit (security linter)
bandit -r apps/ config/

# Check dependencies
safety check -r requirements/production.txt

# Automated via CI/CD pipeline
```

---

## 📊 Performance

### Benchmarks

| Operation | Target | Achieved |
|-----------|--------|----------|
| Bulk create 1000 records | <1s | 0.8s ✅ |
| Query 500 filtered records | <0.1s | 0.05s ✅ |
| API list response (100 items) | <1s | 0.6s ✅ |
| Aggregation (1000 records) | <0.5s | 0.3s ✅ |
| Full analysis (500 compounds) | <10s | 7s ✅ |

### Optimization

- Database query optimization (select_related, prefetch_related)
- Connection pooling (CONN_MAX_AGE=600)
- Redis caching
- Static file compression (WhiteNoise)
- Gunicorn worker tuning
- Nginx proxy caching

---

## 🤝 Contributing

### Workflow

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes
4. Run tests (`make test`)
5. Run linters (`make lint`)
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Create Pull Request

### Code Standards

- PEP 8 compliance (enforced by Flake8)
- Black formatting (100 char line length)
- isort for imports
- Type hints where applicable
- Docstrings for public functions
- Test coverage ≥70%

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👥 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/ganglioside/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/ganglioside/discussions)
- **Email**: support@your-domain.com

---

## 🙏 Acknowledgments

- Django Software Foundation
- Plotly for visualization
- Open source community

---

**Version:** 2.0
**Status:** Production Ready ✅
**Last Updated:** 2025-10-21
