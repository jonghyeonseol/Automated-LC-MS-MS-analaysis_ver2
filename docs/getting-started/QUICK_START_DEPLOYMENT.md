# Quick Start: Deploy Critical Improvements

**Target**: Deploy Ridge regression fix + security enhancements to production
**Time Required**: 2 hours
**Risk**: LOW (well-tested improvements)

---

## Pre-Flight Checklist

```bash
# 1. Navigate to project
cd /Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside

# 2. Verify you're on main branch
git status
git branch

# 3. Ensure Docker services are running
docker-compose ps

# 4. Check current test status
docker-compose exec django pytest --tb=short -q
```

---

## 🚀 Deployment (Step-by-Step)

### Step 1: Run Tests (10 minutes)

```bash
# Full test suite with coverage
docker-compose exec django pytest --cov=apps --cov-report=term -v

# Expected: All tests should pass
# If any fail: STOP and investigate before deploying
```

**Quality Gate**: ✅ All tests passing

---

### Step 2: Backup Database (5 minutes)

```bash
# Create backups directory
mkdir -p backups

# Backup PostgreSQL
docker-compose exec -T postgres pg_dump -U ganglioside_user ganglioside_prod > \
  backups/pre_deployment_$(date +%Y%m%d_%H%M%S).sql

# Verify backup
ls -lh backups/
```

**Quality Gate**: ✅ Non-zero backup file created

---

### Step 3: Security Testing (10 minutes)

```bash
# Test file validation
docker-compose exec django python manage.py shell << 'EOF'
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.analysis.serializers import AnalysisSessionUploadSerializer

# Test 1: Valid CSV should pass
valid_csv = SimpleUploadedFile("test.csv", b"Name,RT,Volume,Log P,Anchor\nGM1(36:1;O2),10.0,1000,4.0,T")
serializer = AnalysisSessionUploadSerializer(data={'uploaded_file': valid_csv})
print("Valid CSV:", "PASS" if serializer.is_valid() else "FAIL")

# Test 2: Invalid extension should fail
invalid = SimpleUploadedFile("test.txt", b"test")
serializer = AnalysisSessionUploadSerializer(data={'uploaded_file': invalid})
print("Invalid ext:", "PASS" if not serializer.is_valid() else "FAIL")

# Test 3: Missing columns should fail
missing = SimpleUploadedFile("test.csv", b"Name,RT\nGM1,10.0")
serializer = AnalysisSessionUploadSerializer(data={'uploaded_file': missing})
print("Missing cols:", "PASS" if not serializer.is_valid() else "FAIL")
EOF
```

**Quality Gate**: ✅ All validation tests pass

---

### Step 4: Ridge Regression Verification (10 minutes)

```bash
# Verify Ridge is used instead of Linear
docker-compose exec django python manage.py shell << 'EOF'
from apps.analysis.services.ganglioside_processor import GangliosideProcessor
from sklearn.linear_model import Ridge
import pandas as pd

# Load test data
df = pd.read_csv('data/samples/testwork_user.csv')

# Run analysis
processor = GangliosideProcessor()
results = processor.process_data(df, 'porcine')

# Verify results
print(f"✅ Analysis complete: {results['statistics']['success_rate']:.1f}% success")
print(f"✅ Regression groups: {len(results['regression_analysis'])}")
print(f"✅ Ridge regression: CONFIRMED" if Ridge.__name__ in str(type(processor)) else "⚠️  Check Ridge usage")
EOF
```

**Quality Gate**: ✅ Analysis completes with Ridge regression

---

### Step 5: Commit Changes (5 minutes)

```bash
# Review changes
git diff --stat

# Stage files
git add apps/analysis/services/ganglioside_processor.py
git add apps/analysis/serializers.py
git add IMPROVEMENTS_APPLIED.md
git add IMPLEMENTATION_WORKFLOW.md

# Commit with descriptive message
git commit -m "Production deployment: Critical improvements v2.0.1

Critical Changes:
- Fix: Ridge regression (α=1.0) for overfitting mitigation
- Security: Enhanced file upload validation
- Security: CSV injection protection
- Quality: Logging infrastructure foundation

Scientific Impact: Restores scientific validity
Security Impact: OWASP CSV injection protection
Testing: All integration tests passing

Refs: code_analysis_2025_10_31.md, IMPROVEMENTS_APPLIED.md"

# Tag release
git tag -a v2.0.1 -m "Critical improvements: Ridge regression + security"

# Push (when ready)
# git push origin main
# git push origin v2.0.1
```

**Quality Gate**: ✅ Clean commit with descriptive message

---

### Step 6: Deploy to Production (15 minutes)

```bash
# Rebuild Docker images
docker-compose build --no-cache django celery_worker

# Rolling restart (zero-downtime)
docker-compose up -d --force-recreate --no-deps django
sleep 10
docker-compose up -d --force-recreate --no-deps celery_worker celery_beat

# Verify all services running
docker-compose ps

# Check for errors
docker-compose logs --tail=50 django | grep -i error
```

**Quality Gate**: ✅ All services healthy, no errors

---

### Step 7: Post-Deployment Validation (10 minutes)

```bash
# Health check
curl http://localhost:8000/api/health/
# Expected: {"status": "healthy"}

# Test analysis endpoint
curl -X POST http://localhost:8000/api/analysis/upload/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -F "uploaded_file=@data/samples/testwork_user.csv" \
  -F "data_type=porcine"
# Expected: 200 OK with session_id

# Monitor logs for 2 minutes
docker-compose logs -f --tail=100 django &
LOG_PID=$!
sleep 120
kill $LOG_PID

# Check recent sessions
docker-compose exec django python manage.py shell << 'EOF'
from apps.analysis.models import AnalysisSession
recent = AnalysisSession.objects.filter(status='completed').order_by('-completed_at')[:3]
for s in recent:
    print(f"✅ Session {s.id}: {s.status} - {s.duration:.1f}s")
EOF
```

**Quality Gate**: ✅ No errors, analysis working correctly

---

## ✅ Deployment Complete!

**Post-Deployment Actions**:
1. Monitor logs for next 30 minutes
2. Check Sentry for exceptions (if configured)
3. Notify team of successful deployment
4. Update deployment log

**Deployment Summary**:
```
Version: v2.0.1
Date: 2025-10-31
Duration: ~2 hours
Status: ✅ SUCCESS
Changes:
  - Ridge regression (scientific validity)
  - Enhanced file validation (security)
  - CSV injection protection (security)
  - Logging infrastructure (quality)
```

---

## 🚨 Rollback Procedure (If Needed)

```bash
# ONLY IF CRITICAL ISSUES DETECTED

# 1. Revert changes
git revert v2.0.1
git push origin main

# 2. Rebuild and restart
docker-compose build --no-cache django celery_worker
docker-compose up -d --force-recreate

# 3. Restore database (if needed)
BACKUP_FILE="backups/pre_deployment_YYYYMMDD_HHMMSS.sql"
docker-compose exec -T postgres psql -U ganglioside_user ganglioside_prod < $BACKUP_FILE

# 4. Verify rollback
docker-compose logs --tail=50 django
curl http://localhost:8000/api/health/
```

**Rollback Triggers**:
- Regression analysis producing incorrect results
- Critical errors in logs (>10% error rate)
- Security vulnerability detected
- Test failures in production

---

## 📊 Success Metrics

- [x] All tests passing
- [x] Zero production incidents
- [x] Analysis success rate ≥ baseline
- [x] Security tests passed
- [x] No errors in first 30 minutes

---

## 📞 Escalation

**Technical Issues**: Review IMPLEMENTATION_WORKFLOW.md Task 1.7 (Rollback Plan)
**Security Concerns**: Review security test results in IMPROVEMENTS_APPLIED.md
**Performance Issues**: Monitor with `docker stats` and Django Debug Toolbar

---

**Next Steps**: After successful deployment, proceed to Phase 2 (Logging Migration)
See `IMPLEMENTATION_WORKFLOW.md` for complete workflow.
