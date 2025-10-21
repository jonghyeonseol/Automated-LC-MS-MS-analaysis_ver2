# Archived Flask Backend - 2025-10-21

**Status**: ARCHIVED - No longer in use

This directory contains the original Flask-based backend that has been **fully replaced by Django**.

## What's Archived

- `app.py` - Flask application (main entry point)
- `app_backup.py` - Flask backup version
- `backend/` - Flask backend directory with API, services, models

## Migration Status

✅ **Fully migrated to Django** (django_ganglioside/)
- All business logic moved to Django services
- All API endpoints being rebuilt with Django REST Framework
- Database models recreated in Django ORM
- ALCOA++ compliance maintained

## Why Archived

To prevent overfitting to old Flask architecture and ensure clean Django-only development.
All future development happens in `django_ganglioside/`.

## Reference Only

These files are kept for reference purposes only in case we need to:
- Verify business logic during migration
- Compare old vs new implementations
- Debug migration issues

**DO NOT USE THESE FILES FOR DEVELOPMENT**

---

**Archived Date**: 2025-10-21
**Reason**: Full Django migration
**Django Location**: ../django_ganglioside/
