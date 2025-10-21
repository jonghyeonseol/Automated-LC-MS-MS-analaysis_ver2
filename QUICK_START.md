# Django Ganglioside Platform - Quick Start Guide

**Status**: ✅ Production Ready
**Date**: 2025-10-21
**Migration**: Flask → Django **COMPLETE**

---

## 🚀 Getting Started (5 Minutes)

### 1. Activate Environment
```bash
cd /Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside
source ../.venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.development
```

### 2. Start Server
```bash
python manage.py runserver
```

### 3. Access Application
- **Web UI**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/ (username: `admin`)
- **API Documentation**: http://localhost:8000/api/docs/

---

## 📋 Common Tasks

### Run Analysis
1. Navigate to http://localhost:8000/upload/
2. Upload CSV file: `../data/samples/testwork_user.csv`
3. Click "Upload and Analyze"
4. View results when complete

### Check System Status
```bash
# Verify no errors
python manage.py check

# Run migrations (if needed)
python manage.py migrate

# Create new admin user
python manage.py createsuperuser
```

### View Database
```bash
# Django admin panel
http://localhost:8000/admin/

# Or use shell
python manage.py shell
>>> from apps.analysis.models import AnalysisSession
>>> AnalysisSession.objects.all()
```

---

## 📁 Project Structure

```
django_ganglioside/
├── apps/
│   ├── analysis/          # Main analysis engine
│   │   ├── models.py      # Database models
│   │   ├── serializers.py # DRF API serialization
│   │   ├── views.py       # API endpoints
│   │   ├── views_web.py   # Web UI views
│   │   └── services/      # Business logic
│   ├── visualization/     # Dashboard
│   ├── core/             # Utilities
│   ├── users/            # Authentication
│   └── rules/            # Rule engine
│
├── config/               # Django settings
├── templates/            # HTML templates
├── static/              # CSS, JS files
├── media/               # User uploads
├── db.sqlite3           # Database
└── manage.py            # Django CLI
```

---

## 🔧 Key Files

### Configuration
- `config/settings/development.py` - Dev settings
- `config/settings/production.py` - Production settings
- `config/urls.py` - URL routing

### Business Logic
- `apps/analysis/services/analysis_service.py` - Main orchestrator
- `apps/analysis/services/ganglioside_processor.py` - 5-rule algorithm
- `apps/analysis/services/export_service.py` - Data export

### API
- `apps/analysis/serializers.py` - API serialization
- `apps/analysis/views.py` - API ViewSets

### Web UI
- `apps/analysis/views_web.py` - Web views
- `templates/analysis/*.html` - UI templates

---

## 📊 API Endpoints

### Sessions
- `POST /api/sessions/` - Create new analysis session
- `GET /api/sessions/` - List all sessions
- `GET /api/sessions/{id}/` - Session details
- `POST /api/sessions/{id}/analyze/` - Trigger analysis
- `GET /api/sessions/{id}/results/` - Get results
- `GET /api/sessions/{id}/export/?format=csv` - Export data

### Compounds
- `GET /api/compounds/` - List compounds
- `GET /api/compounds/?session_id=1` - Filter by session
- `GET /api/compounds/?category=GD` - Filter by category
- `GET /api/compounds/{id}/` - Compound details

### Documentation
- `GET /api/docs/` - Swagger UI
- `GET /api/schema/` - OpenAPI schema

---

## 🧪 Testing

### Quick Test
```bash
# 1. Login to admin: http://localhost:8000/admin/
# 2. Upload test file: http://localhost:8000/upload/
# 3. Use: ../data/samples/testwork_user.csv
# 4. Click "Upload and Analyze"
# 5. Wait for completion (auto-refresh)
# 6. View results with charts
```

### Command-Line Testing
```bash
# Test database
python manage.py shell
>>> from apps.analysis.models import AnalysisSession
>>> AnalysisSession.objects.count()

# Run system check
python manage.py check

# Test algorithm
python run_simple_tuning.py
```

---

## 📚 Documentation

### Essential Reading
- `README.md` - Complete project documentation
- `MIGRATION_COMPLETE.md` - Migration success summary
- `FLASK_TO_DJANGO_MIGRATION.md` - Detailed migration log
- `FUTURE_ENHANCEMENTS.md` - Channels/Celery guides

### Algorithm Documentation
- `REGRESSION_MODEL_EVALUATION.md` - Model validation
- `WEEK1_GATE_VALIDATION.md` - Validation results
- `TUNING_SUCCESS.md` - Tuning process

---

## ⚠️ Important Notes

### What Changed from Flask
- ✅ **Database persistence** - Analyses saved permanently
- ✅ **User authentication** - Multi-user support
- ✅ **RESTful API** - Standard API with docs
- ✅ **Modern UI** - Bootstrap 5 responsive design
- ✅ **Admin panel** - Django admin interface

### Flask Code Location
- **Archived**: `_archived_flask_2025_10_21/`
- **DO NOT USE** - Flask app is deprecated
- All new development in Django only

### Algorithm Preservation
- ✅ **Same 5-rule algorithm** - Zero changes
- ✅ **Same validation metrics** - R² = 0.92
- ✅ **ALCOA++ compliant** - Full audit trail in `trace/`
- ✅ **Identical results** - Same predictions as Flask

---

## 🔄 Future Enhancements (Optional)

### Real-time Progress (Django Channels)
- **Requires**: Redis installation
- **Guide**: See `FUTURE_ENHANCEMENTS.md`
- **Effort**: 2-3 hours
- **Current Solution**: Auto-refresh (works fine)

### Background Tasks (Celery)
- **Requires**: Redis installation
- **Guide**: See `FUTURE_ENHANCEMENTS.md`
- **Effort**: 2-3 hours
- **Current Solution**: Synchronous (works for 5-10s analyses)

### Production Database
- **Requires**: PostgreSQL installation
- **Configuration**: Already in settings
- **Current**: SQLite (fine for development)

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'X'"
```bash
# Ensure virtual environment is activated
source ../.venv/bin/activate

# Reinstall dependencies
pip install -r requirements/development.txt
```

### "OperationalError: no such table"
```bash
# Run migrations
python manage.py migrate
```

### "CSRF verification failed"
```bash
# Make sure you're using POST with CSRF token
# Or use API endpoints with DRF authentication
```

### Static files not loading
```bash
# Collect static files
python manage.py collectstatic --noinput
```

---

## 📞 Support

### Check Status
```bash
# System health
python manage.py check

# Database status
python manage.py showmigrations

# Server logs
# Check terminal output when running runserver
```

### Documentation Locations
- Project root: `/Automated-LC-MS-MS-analaysis_ver2/Regression/`
- Django project: `/Regression/django_ganglioside/`
- Flask archive: `/Regression/_archived_flask_2025_10_21/`

---

**Last Updated**: 2025-10-21
**Status**: ✅ Production Ready
**Version**: Django 2.0.0 (Algorithm v1.1-validated)

**Need help?** See comprehensive documentation in `README.md`
