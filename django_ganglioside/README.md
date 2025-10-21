# Django Ganglioside Analysis Platform

Django-based LC-MS/MS Ganglioside Analysis Platform with 5-Rule Algorithm, background task processing, and comprehensive API.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 12+ (or SQLite for development)
- Redis 6+ (for Celery)
- pip and virtualenv

### Installation

```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements/development.txt

# 3. Copy environment template
cp .env.example .env

# 4. Edit .env with your settings
# For quick start, you can use SQLite:
#   DATABASE_URL=sqlite:///db.sqlite3
#   DEBUG=True

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Run development server
python manage.py runserver
```

### Access Points
- **Web App**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/
- **API Docs (Swagger)**: http://localhost:8000/api/docs/
- **API Docs (ReDoc)**: http://localhost:8000/api/redoc/
- **Health Check**: http://localhost:8000/health/

## 📁 Project Structure

```
django_ganglioside/
├── config/                  # Django settings and configuration
│   ├── settings/
│   │   ├── base.py         # Base settings
│   │   ├── development.py  # Development overrides
│   │   └── production.py   # Production settings
│   ├── urls.py             # Root URL configuration
│   ├── wsgi.py             # WSGI application
│   ├── asgi.py             # ASGI application
│   └── celery.py           # Celery configuration
│
├── apps/                    # Django applications
│   ├── core/               # Core utilities and base models
│   ├── users/              # User management (TODO)
│   ├── analysis/           # Main analysis engine
│   │   ├── models.py       # AnalysisSession, Compound, etc.
│   │   ├── admin.py        # Django admin interface
│   │   ├── serializers.py  # DRF serializers (TODO)
│   │   ├── views.py        # API views (TODO)
│   │   ├── services/       # Business logic (TODO)
│   │   └── tasks.py        # Celery tasks (TODO)
│   ├── rules/              # 5-Rule algorithm modules (TODO)
│   └── visualization/      # Plotly chart generation (TODO)
│
├── requirements/            # Dependency management
│   ├── base.txt            # Core dependencies
│   ├── development.txt     # Dev tools
│   └── production.txt      # Production extras
│
├── static/                  # Static assets
├── media/                   # User uploads
├── templates/               # HTML templates
└── manage.py               # Django management script
```

## 🗄️ Database Models

### AnalysisSession
Represents a complete analysis run with user uploads and configuration.

**Key Fields:**
- `user` - Owner of the analysis
- `status` - pending/uploading/processing/completed/failed
- `data_type` - porcine/human/bovine/mouse/other
- `uploaded_file` - CSV file with LC-MS data
- `r2_threshold` - Regression quality threshold (default: 0.75)
- `outlier_threshold` - Outlier detection sigma (default: 2.5)
- `rt_tolerance` - RT window for fragmentation (default: 0.1 min)

### AnalysisResult
Stores aggregated analysis output and statistics.

**Key Fields:**
- `session` - OneToOne relationship
- `total_compounds`, `valid_compounds`, `outlier_count`, `success_rate`
- `regression_analysis` - JSON: Model coefficients per prefix
- `categorization` - JSON: GM/GD/GT/GQ/GP breakdown
- Rule-specific counts (rule1_valid, rule4_valid, rule5_fragments)

### Compound
Individual ganglioside compound with classification.

**Key Fields:**
- `name`, `rt`, `volume`, `log_p`, `is_anchor`
- `prefix`, `suffix` - Parsed from name
- `a_component` (carbon), `b_component` (unsaturation), `sugar_count`
- `status` - valid/outlier/fragment
- `category` - GM/GD/GT/GQ/GP
- `predicted_rt`, `residual`, `standardized_residual`
- `outlier_reason` - Why it was flagged

### RegressionModel
Stores regression model details per prefix group.

**Key Fields:**
- `prefix_group` - GD1, GM3, etc.
- `coefficients`, `feature_names`, `equation`
- `r2`, `rmse`, `durbin_watson` - Quality metrics
- `n_samples`, `n_anchors` - Training data size

## 🔧 Configuration

### Environment Variables (.env)

```bash
# Django
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/ganglioside_db
# Or SQLite for dev:
# DATABASE_URL=sqlite:///db.sqlite3

# Redis (for Celery)
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Analysis Defaults
DEFAULT_R2_THRESHOLD=0.75
DEFAULT_OUTLIER_THRESHOLD=2.5
DEFAULT_RT_TOLERANCE=0.1

# File Upload
MAX_UPLOAD_SIZE=52428800  # 50MB
```

### Analysis Parameters

Adjustable via API or admin panel:
- **r2_threshold** (0.5 - 0.999): Minimum R² for regression validity
  - Too high (>0.90) risks overfitting with small samples
  - Recommended: 0.70 - 0.85 for LC-MS data
- **outlier_threshold** (1.0 - 5.0σ): Standardized residual cutoff
  - Recommended: 2.0 - 3.0σ
- **rt_tolerance** (0.01 - 0.5 min): RT window for fragmentation detection
  - Instrument-dependent, typically 0.05 - 0.2 min

## 🔬 The 5-Rule Algorithm

### Rule 1: Prefix-Based Multiple Regression
Groups compounds by prefix (GD1, GM3, etc.), fits regression model using anchor compounds.
- **Features**: Log P, carbon chain, sugar count, modifications
- **Model**: Ridge regression (regularized) or Linear
- **Output**: Valid compounds, outliers, regression coefficients

### Rule 2-3: Sugar Count & Isomer Classification
Calculates total sugars from compound name, identifies structural isomers.
- **Formula**: `e_value + (5 - f_value)` where e∈{A,M,D,T,Q,P}
- **Isomers**: GD1a/b, GQ1b/c when f=1

### Rule 4: O-Acetylation Validation
Validates that O-acetylated compounds have higher RT than base.
- **Logic**: `RT(compound+OAc) > RT(compound_base)`

### Rule 5: In-Source Fragmentation Detection
Groups by lipid composition, detects fragments within RT tolerance.
- **Method**: Within ±RT_tolerance, keeps highest sugar count
- **Volume consolidation**: Merges suspected fragment volumes

### Categorization
Classifies by sialic acid content:
- **GM** (M=1): Monosialogangliosides
- **GD** (D=2): Disialogangliosides
- **GT** (T=3): Trisialogangliosides
- **GQ** (Q=4): Tetrasialogangliosides
- **GP** (P=5): Pentasialogangliosides

## 🚀 Development Commands

### Django Management
```bash
# Run migrations
python manage.py migrate

# Create migrations after model changes
python manage.py makemigrations

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Open Django shell
python manage.py shell

# Run tests
python manage.py test

# Or use pytest
pytest
```

### Celery (Background Tasks)
```bash
# Start Celery worker
celery -A config worker -l info

# Start Celery Beat (scheduled tasks)
celery -A config beat -l info

# Start both with:
celery -A config worker -B -l info

# Monitor tasks (Flower)
pip install flower
celery -A config flower
# Access at http://localhost:5555
```

### Code Quality
```bash
# Format code with Black
black .

# Sort imports
isort .

# Lint with flake8
flake8

# Type checking
mypy apps/

# Run all quality checks
black . && isort . && flake8 && mypy apps/
```

## 📊 API Endpoints

### Analysis
- `POST /api/analysis/sessions/` - Create new analysis session
- `GET /api/analysis/sessions/` - List user's sessions
- `GET /api/analysis/sessions/{id}/` - Session details
- `POST /api/analysis/sessions/{id}/upload/` - Upload CSV file
- `POST /api/analysis/sessions/{id}/start/` - Start analysis (triggers Celery task)
- `GET /api/analysis/sessions/{id}/results/` - Get analysis results
- `GET /api/analysis/sessions/{id}/compounds/` - List compounds
- `GET /api/analysis/sessions/{id}/export/` - Export results as CSV

### Visualization
- `GET /api/visualization/{session_id}/scatter/` - 2D RT vs Log P plot
- `GET /api/visualization/{session_id}/3d/` - 3D distribution
- `GET /api/visualization/{session_id}/categories/` - Category plots

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/register/` - New user registration
- `GET /api/auth/me/` - Current user info

### Health
- `GET /health/` - System health check (database + Redis)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test file
pytest apps/analysis/tests/test_models.py

# Run tests in parallel
pytest -n auto

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False`
- [ ] Configure `SECRET_KEY` (use strong random key)
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Use PostgreSQL (not SQLite)
- [ ] Configure Redis for Celery
- [ ] Set up Gunicorn + Nginx
- [ ] Enable SSL/HTTPS
- [ ] Configure static file serving (WhiteNoise or CDN)
- [ ] Set up database backups
- [ ] Configure Sentry for error tracking
- [ ] Set up monitoring (e.g., Datadog, Prometheus)

### Docker Deployment (Recommended)
```bash
# Build image
docker build -t ganglioside-analysis:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f web

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

## 📝 Next Steps (Implementation TODO)

### Phase 1: Complete Core Functionality (Week 1-2)
- [ ] Create DRF serializers for all models
- [ ] Implement API views (ViewSets)
- [ ] Copy and integrate existing analysis services:
  - [ ] GangliosideProcessor
  - [ ] RegressionAnalyzer
  - [ ] VisualizationService
  - [ ] GangliosideCategorizer
- [ ] Create Celery tasks for background analysis
- [ ] Write unit tests for models and services

### Phase 2: User Management (Week 2)
- [ ] Create User model extensions (if needed)
- [ ] Implement authentication endpoints
- [ ] Add user-specific analysis filtering
- [ ] Create user dashboard

### Phase 3: Rules Module (Week 3)
- [ ] Migrate modular rule implementations
- [ ] Create rule configuration system
- [ ] Add rule versioning
- [ ] Implement stepwise analysis API

### Phase 4: Visualization (Week 3-4)
- [ ] Integrate Plotly chart generation
- [ ] Create visualization endpoints
- [ ] Add chart customization options
- [ ] Export plots as images

### Phase 5: Testing & Documentation (Week 4-5)
- [ ] Write comprehensive test suite
- [ ] Create API documentation (Swagger/ReDoc)
- [ ] Write user guide
- [ ] Create developer documentation
- [ ] Add example datasets

### Phase 6: Deployment (Week 5-6)
- [ ] Create Dockerfile
- [ ] Set up docker-compose
- [ ] Configure CI/CD pipeline
- [ ] Deploy to staging environment
- [ ] Performance testing
- [ ] Deploy to production

## 🔗 Migration from Flask

### Key Differences
| Flask (Old) | Django (New) |
|-------------|--------------|
| In-memory sessions | Database-backed sessions |
| No authentication | Built-in user system |
| Synchronous processing | Celery async tasks |
| JSON file storage | PostgreSQL database |
| Manual API routing | DRF ViewSets |
| No admin panel | Auto-generated admin |
| No ORM | Django ORM with migrations |

### Migration Steps
1. ✅ Django project structure created
2. ✅ Models defined (AnalysisSession, Compound, etc.)
3. ✅ Admin interface configured
4. ⏳ Copy analysis services from Flask app
5. ⏳ Create DRF serializers and views
6. ⏳ Implement Celery tasks
7. ⏳ Migrate templates and static files
8. ⏳ Test with existing datasets
9. ⏳ Deploy and switch traffic

### Data Migration
To migrate existing Flask analysis data:
```bash
# Create management command
python manage.py migrate_flask_data --flask-db path/to/old/data

# Or use Django shell for manual migration
python manage.py shell
from apps.analysis.utils import FlaskMigrator
migrator = FlaskMigrator()
migrator.migrate_all()
```

## 📚 Resources

- **Django Docs**: https://docs.djangoproject.com/
- **DRF Docs**: https://www.django-rest-framework.org/
- **Celery Docs**: https://docs.celeryproject.org/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Project CLAUDE.md**: See `../CLAUDE.md` for detailed algorithm documentation

## 🐛 Troubleshooting

### Database connection errors
```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql -U postgres -h localhost
```

### Redis connection errors
```bash
# Check Redis is running
redis-cli ping

# Should return PONG
```

### Celery tasks not running
```bash
# Check worker is running
celery -A config inspect active

# Clear queue
celery -A config purge

# Check Redis queue
redis-cli
> KEYS celery*
```

### Migrations stuck
```bash
# Reset migrations (DANGER: development only)
python manage.py migrate --fake analysis zero
python manage.py migrate

# Or start fresh
rm -rf apps/*/migrations/00*.py
python manage.py makemigrations
python manage.py migrate
```

## 📄 License

[Your License Here]

## 👥 Contributors

[Your Name/Team]

## 📧 Support

For issues and questions:
- GitHub Issues: [Your Repo URL]
- Email: [Your Email]
