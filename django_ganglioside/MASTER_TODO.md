# Master TODO List - Django Ganglioside Migration
## Complete Long-Term Plan with ALCOA++ Traceability

**Project**: Migration from Flask to Django with Algorithm Validation
**Start Date**: 2025-10-21
**Target R² Requirement**: ≥ 0.90 (Excellent)
**Compliance**: ALCOA++ (Attributable, Legible, Contemporaneous, Original, Accurate, Complete, Consistent, Enduring, Available)

---

## Current Status: Phase 1.1 Complete, Phase 1.2 Next

```
Progress: ████████░░░░░░░░░░░░░░░░░░░░░ 30% Complete
Current Phase: 1.2 - Auto-Tuning
Gate Status: BLOCKED - R² = 0.66-0.82 (need ≥ 0.90)
```

---

## Phase 1: Algorithm Validation & Tuning (CRITICAL - GATE)

### ✅ Phase 1.1: Initial Validation (COMPLETE)

- [x] **Setup Environment**
  - [x] Create Python 3.13 virtual environment (`.venv/`)
  - [x] Install dependencies (pandas, scikit-learn, numpy, Django)
  - [x] Resolve psycopg2/RDKit compatibility issues
  - **Status**: Complete 2025-10-21 14:00
  - **Files**: `.venv/`, `requirements/validation.txt`

- [x] **Build Validation Framework**
  - [x] Create standalone validation script (`validate_standalone.py`)
  - [x] Implement Leave-One-Out cross-validation
  - [x] Implement K-Fold cross-validation
  - [x] Add metrics calculation (R², RMSE, MAE, overfitting)
  - [x] Create interpretation engine
  - **Status**: Complete 2025-10-21 14:15
  - **Files**: `validate_standalone.py` (521 lines)
  - **Trace**: `trace/algorithm_versions/v1.0_baseline/`

- [x] **Run Initial Validation**
  - [x] Leave-One-Out on testwork_user.csv (49 anchors)
  - [x] 5-Fold cross-validation
  - [x] Document results
  - **Status**: Complete 2025-10-21 14:30
  - **Results**: LOO R²=0.8246, K-Fold R²=0.6619
  - **Trace**: `trace/validation_runs/20251021_143000_LOO/`

- [x] **ALCOA++ Audit Trail Setup**
  - [x] Create `trace/` folder structure
  - [x] Save original data with checksum
  - [x] Create validation run template
  - [x] Build `validate_with_trace.sh` script
  - [x] Document ALCOA++ compliance matrix
  - **Status**: Complete 2025-10-21 15:00
  - **Files**: `trace/README.md`, `validate_with_trace.sh`
  - **Checksums**:
    - Data: `sha256:e84f6e12c5f3cc6de53713031971799aa3ba828405a8588f90a34fbf2110620e`
    - Algorithm: `sha256:5eef7337adc17bae39c5a6f53ba3049e634abb82d8e7fb45eb2e8509e8bba11e`

- [x] **Analysis & Documentation**
  - [x] Create `VALIDATION_RESULTS.md`
  - [x] Create `QUICKSTART.md`
  - [x] Identify root causes (modified compounds, overfitting, variance)
  - [x] Determine next steps (auto-tuning required)
  - **Status**: Complete 2025-10-21 14:45

**Phase 1.1 Outcome**: ❌ FAILED - Did not meet R² ≥ 0.90 threshold → Proceed to Phase 1.2

---

### 🔄 Phase 1.2: Auto-Tuning (IN PROGRESS)

**Goal**: Achieve R² ≥ 0.90 through systematic algorithm optimization

- [ ] **Build Auto-Tuner Module**
  - [ ] Create `apps/analysis/services/algorithm_tuner.py`
  - [ ] Implement iterative tuning strategy (max 5 iterations)
  - [ ] Add tuning history tracking
  - **Estimated Time**: 2-3 hours
  - **Dependencies**: Phase 1.1 results

- [ ] **Tuning Strategy - Iteration 1: Separate Modified Compounds**
  - [ ] Detect modified gangliosides (+HexNAc, +dHex, +OAc)
  - [ ] Create separate regression models for:
    - Base gangliosides (GD1, GD3, GM1, GT1, GQ1)
    - Modified gangliosides (separate model)
  - [ ] Run validation
  - **Target**: R² ≥ 0.85
  - **Trace**: `trace/algorithm_versions/v1.1_separated/`

- [ ] **Tuning Strategy - Iteration 2: Feature Reduction**
  - [ ] Reduce features from 9 → 2 (Log P + carbon chain only)
  - [ ] Remove unnecessary features causing overfitting
  - [ ] Update GangliosideProcessor
  - [ ] Run validation
  - **Target**: R² ≥ 0.88, Overfitting < 0.15
  - **Trace**: `trace/algorithm_versions/v1.2_reduced_features/`

- [ ] **Tuning Strategy - Iteration 3: Ridge Regularization**
  - [ ] Replace LinearRegression → Ridge(alpha=1.0)
  - [ ] Tune alpha parameter (test 0.1, 1.0, 10.0)
  - [ ] Run validation
  - **Target**: R² ≥ 0.90, Overfitting < 0.10
  - **Trace**: `trace/algorithm_versions/v1.3_ridge_regularization/`

- [ ] **Tuning Strategy - Iteration 4: Prefix Pooling**
  - [ ] Pool related prefix groups (GM1/GM2/GM3 → GM*)
  - [ ] Increase sample size per model
  - [ ] Run validation
  - **Target**: R² ≥ 0.90, Consistency ↑
  - **Trace**: `trace/algorithm_versions/v1.4_pooled_prefixes/`

- [ ] **Tuning Strategy - Iteration 5: Manual Review (if needed)**
  - [ ] Analyze remaining outliers
  - [ ] Consider ensemble methods
  - [ ] Expert review of problematic compounds
  - **Target**: R² ≥ 0.90 (strict requirement)

- [ ] **Document Tuning Results**
  - [ ] Update `VALIDATION_RESULTS.md`
  - [ ] Create comparison table (v1.0 vs v1.1-v1.5)
  - [ ] Document changes in `trace/algorithm_versions/changelog.md`

**Phase 1.2 Success Criteria**:
- ✅ R² ≥ 0.90 (Leave-One-Out)
- ✅ R² ≥ 0.90 (5-Fold cross-validation)
- ✅ Overfitting score < 0.10
- ✅ RMSE < 0.15 min
- ✅ Consistency: |R²_LOO - R²_KFold| < 0.05
- ✅ All validation runs traced with ALCOA++ compliance

**Estimated Completion**: 2025-10-22

---

### 🔍 Phase 1.3: Re-Validation (PENDING)

**Prerequisite**: Phase 1.2 must achieve R² ≥ 0.90

- [ ] **Run Final Validation with Tuned Algorithm**
  - [ ] Leave-One-Out validation
  - [ ] 5-Fold cross-validation
  - [ ] 10-Fold cross-validation (for stability check)
  - [ ] Bootstrap validation (optional)
  - **Trace**: `trace/validation_runs/20251022_*_FINAL/`

- [ ] **Compare All Versions**
  - [ ] Create comparison visualization
  - [ ] Generate performance matrix
  - [ ] Document improvement % from baseline
  - **File**: `VALIDATION_COMPARISON.md`

- [ ] **Manual Review & Approval**
  - [ ] Review all per-compound predictions
  - [ ] Verify outliers are truly problematic
  - [ ] Get stakeholder sign-off
  - [ ] Complete signature forms in `trace/signatures/`

- [ ] **Commit Final Algorithm**
  - [ ] Tag Git version: `v1.0-validated`
  - [ ] Archive in `trace/algorithm_versions/v1.0_final/`
  - [ ] Lock baseline for production

**Phase 1.3 Gate**: Must pass before proceeding to Phase 2

---

## Phase 2: Visualization Dashboard (Priority 1)

**Prerequisite**: R² ≥ 0.90 achieved

### 📊 Phase 2.1: Validation Results Dashboard

- [ ] **Create Visualization App**
  - [ ] `apps/visualization/views.py` - Dashboard views
  - [ ] `apps/visualization/templates/` - HTML templates
  - [ ] `apps/visualization/static/` - CSS/JS assets

- [ ] **Plotly Integration**
  - [ ] R² comparison chart (LOO vs K-Fold vs Bootstrap)
  - [ ] Actual vs Predicted RT scatter plot (interactive)
  - [ ] Residual distribution histogram
  - [ ] Overfitting indicator gauge
  - [ ] Per-fold performance breakdown
  - **Library**: Plotly.js for interactive charts

- [ ] **Per-Compound Performance Table**
  - [ ] Sortable/filterable table
  - [ ] Color-coded by error magnitude
  - [ ] Click to see compound details
  - [ ] Export to CSV/Excel

- [ ] **Real-Time Progress Tracking**
  - [ ] Django Channels setup
  - [ ] WebSocket for live updates
  - [ ] Progress bar during validation
  - **Dependency**: `channels`, `redis`

- [ ] **Validation History**
  - [ ] Timeline of all validation runs
  - [ ] Compare runs side-by-side
  - [ ] Trend analysis (improving/degrading)

**Estimated Time**: 3-4 days

---

### 📈 Phase 2.2: Analysis Results Visualization

- [ ] **Ganglioside Category Breakdown**
  - [ ] Pie chart: GM/GD/GT/GQ/GP distribution
  - [ ] Bar chart: Valid vs Outliers per category
  - [ ] Interactive filtering

- [ ] **Regression Model Display**
  - [ ] Plot regression lines per prefix group
  - [ ] Show confidence intervals
  - [ ] Display model equations
  - [ ] Highlight anchor compounds

- [ ] **Diagnostic Plots**
  - [ ] Q-Q plot for residuals (normality check)
  - [ ] Cook's distance (outlier detection)
  - [ ] Leverage plot (influential points)
  - [ ] Residuals vs Fitted values

**Estimated Time**: 2-3 days

---

## Phase 3: API Layer (Priority 2)

**Prerequisite**: Phase 2 complete

### 🔌 Phase 3.1: Django REST Framework Setup

- [ ] **Serializers** (`apps/analysis/serializers.py`)
  - [ ] AnalysisSessionSerializer
  - [ ] CompoundSerializer
  - [ ] RegressionModelSerializer
  - [ ] ValidationResultSerializer (new model)
  - [ ] Nested serializers for relationships

- [ ] **ViewSets** (`apps/analysis/views.py`)
  - [ ] AnalysisSessionViewSet
  - [ ] CompoundViewSet
  - [ ] ValidationViewSet
  - [ ] Custom actions (@action decorators)

- [ ] **URL Configuration**
  - [ ] Router setup
  - [ ] API versioning (v1/)
  - [ ] Nested routes

- [ ] **Authentication & Permissions**
  - [ ] Token authentication
  - [ ] User permissions
  - [ ] Rate limiting

**Estimated Time**: 2 days

---

### 📚 Phase 3.2: API Endpoints

- [ ] **Analysis Endpoints**
  - [ ] `POST /api/v1/analysis/` - Create new analysis
  - [ ] `GET /api/v1/analysis/{id}/` - Retrieve results
  - [ ] `POST /api/v1/analysis/{id}/validate/` - Run validation
  - [ ] `GET /api/v1/analysis/{id}/export/` - Export CSV/JSON

- [ ] **Validation Endpoints**
  - [ ] `POST /api/v1/validate/` - Run standalone validation
  - [ ] `GET /api/v1/validate/{id}/` - Get validation results
  - [ ] `GET /api/v1/validate/history/` - List all validations

- [ ] **Compound Endpoints**
  - [ ] `GET /api/v1/compounds/` - List compounds
  - [ ] `GET /api/v1/compounds/{id}/` - Compound details
  - [ ] `POST /api/v1/compounds/bulk/` - Bulk upload

- [ ] **Documentation**
  - [ ] Swagger/ReDoc auto-generation
  - [ ] API examples with curl/Python
  - [ ] Postman collection

**Estimated Time**: 2-3 days

---

## Phase 4: Database Persistence (Priority 3)

**Prerequisite**: Phase 3 complete

### 💾 Phase 4.1: Database Setup

- [ ] **PostgreSQL Installation**
  - [ ] Install PostgreSQL locally
  - [ ] Create database `ganglioside_dev`
  - [ ] Configure `.env` file

- [ ] **Models Extension**
  - [ ] Add ValidationResult model
  - [ ] Add TuningHistory model
  - [ ] Add AuditLog model (ALCOA++ compliance)
  - [ ] Update relationships

- [ ] **Migrations**
  - [ ] Run `python manage.py makemigrations`
  - [ ] Run `python manage.py migrate`
  - [ ] Create initial data fixtures

**Estimated Time**: 1 day

---

### 🔄 Phase 4.2: Data Migration from Flask

- [ ] **Create Migration Scripts**
  - [ ] Extract data from Flask sessions
  - [ ] Map to Django models
  - [ ] Handle duplicate detection

- [ ] **Data Import**
  - [ ] Import historical analyses
  - [ ] Import validation results
  - [ ] Verify data integrity (checksums)

- [ ] **Trace Integration**
  - [ ] Store trace/ references in database
  - [ ] Link validation runs to database records
  - [ ] Add ALCOA++ metadata fields

**Estimated Time**: 2 days

---

### 🏗️ Phase 4.3: Service Layer

- [ ] **Create AnalysisService**
  - [ ] Orchestrates processor + validator
  - [ ] Handles database transactions
  - [ ] Manages file uploads
  - **File**: `apps/analysis/services/analysis_service.py`

- [ ] **Create ValidationService**
  - [ ] Runs validation with trace
  - [ ] Saves to database + trace/
  - [ ] Generates signatures
  - **File**: `apps/analysis/services/validation_service.py`

**Estimated Time**: 2 days

---

## Phase 5: Background Tasks (Priority 4)

**Prerequisite**: Phase 4 complete

### ⚙️ Phase 5.1: Celery Setup

- [ ] **Installation & Configuration**
  - [ ] Install Redis
  - [ ] Configure Celery broker
  - [ ] Create `config/celery.py`
  - [ ] Set up worker processes

- [ ] **Task Definitions** (`apps/analysis/tasks.py`)
  - [ ] `run_analysis_task(session_id)`
  - [ ] `run_validation_task(data_file, method)`
  - [ ] `export_results_task(session_id, format)`
  - [ ] `cleanup_old_results_task()`

- [ ] **Progress Tracking**
  - [ ] Use Celery task states
  - [ ] Store progress in database
  - [ ] Send WebSocket updates

**Estimated Time**: 2 days

---

### 📧 Phase 5.2: Notifications

- [ ] **Email Notifications**
  - [ ] Analysis complete
  - [ ] Validation results ready
  - [ ] Error notifications

- [ ] **Webhook Support**
  - [ ] POST results to external URL
  - [ ] Retry logic
  - [ ] Signature verification

**Estimated Time**: 1 day

---

## Phase 6: Testing & Documentation

### 🧪 Phase 6.1: Testing

- [ ] **Unit Tests**
  - [ ] Test algorithm functions (>90% coverage)
  - [ ] Test API endpoints
  - [ ] Test serializers
  - [ ] Test validation logic
  - **Target**: >80% code coverage

- [ ] **Integration Tests**
  - [ ] End-to-end analysis workflow
  - [ ] Database transactions
  - [ ] Celery tasks

- [ ] **Performance Tests**
  - [ ] Large dataset handling (1000+ compounds)
  - [ ] Concurrent validations
  - [ ] API response times

**Estimated Time**: 3-4 days

---

### 📝 Phase 6.2: Documentation

- [ ] **User Documentation**
  - [ ] User guide (how to run analysis)
  - [ ] Validation guide (ALCOA++ compliance)
  - [ ] API documentation
  - [ ] Troubleshooting guide

- [ ] **Developer Documentation**
  - [ ] Architecture overview
  - [ ] Database schema
  - [ ] Algorithm explanation
  - [ ] Contribution guide

- [ ] **ALCOA++ Documentation**
  - [ ] Audit trail procedures
  - [ ] Data integrity verification
  - [ ] Signature requirements
  - [ ] Retention policies

**Estimated Time**: 2-3 days

---

## Phase 7: Deployment

### 🚀 Phase 7.1: Dockerization

- [ ] **Create Dockerfiles**
  - [ ] Django app container
  - [ ] Celery worker container
  - [ ] Redis container
  - [ ] PostgreSQL container

- [ ] **Docker Compose**
  - [ ] Development environment
  - [ ] Production environment
  - [ ] Volume management

**Estimated Time**: 2 days

---

### 🔧 Phase 7.2: CI/CD Pipeline

- [ ] **GitHub Actions**
  - [ ] Run tests on push
  - [ ] Linting (flake8, black)
  - [ ] Security checks (bandit)
  - [ ] Auto-deploy to staging

- [ ] **Deployment Scripts**
  - [ ] Zero-downtime deployment
  - [ ] Database migration automation
  - [ ] Rollback procedures

**Estimated Time**: 2 days

---

### 🌐 Phase 7.3: Production Deployment

- [ ] **Server Setup**
  - [ ] Configure production server
  - [ ] Set up nginx reverse proxy
  - [ ] SSL certificates
  - [ ] Firewall rules

- [ ] **Database Migration**
  - [ ] Backup existing data
  - [ ] Run migrations
  - [ ] Verify data integrity

- [ ] **Monitoring**
  - [ ] Set up logging (Sentry/LogRocket)
  - [ ] Performance monitoring
  - [ ] Alerting rules

**Estimated Time**: 3 days

---

## Timeline Summary

```
Week 1 (Oct 21-25):
  ✅ Day 1: Phase 1.1 - Initial Validation (COMPLETE)
  🔄 Day 2: Phase 1.2 - Auto-Tuning (IN PROGRESS)
  🔄 Day 3: Phase 1.3 - Re-Validation
  ⏳ Day 4-5: Phase 2.1 - Validation Dashboard

Week 2 (Oct 28-Nov 1):
  ⏳ Day 1-2: Phase 2.2 - Analysis Visualization
  ⏳ Day 3-5: Phase 3 - API Layer

Week 3 (Nov 4-8):
  ⏳ Day 1-3: Phase 4 - Database Persistence
  ⏳ Day 4-5: Phase 5 - Celery Tasks

Week 4 (Nov 11-15):
  ⏳ Day 1-3: Phase 6 - Testing & Documentation
  ⏳ Day 4-5: Phase 7 - Deployment
```

**Total Estimated Time**: 4 weeks (80-100 hours)

---

## Success Criteria Checklist

### Phase 1 Gate (MUST PASS to continue):
- [ ] R² ≥ 0.90 (Leave-One-Out)
- [ ] R² ≥ 0.90 (5-Fold cross-validation)
- [ ] Overfitting score < 0.10
- [ ] RMSE < 0.15 min
- [ ] Consistency: |R²_LOO - R²_KFold| < 0.05
- [ ] All validation runs have ALCOA++ trace
- [ ] Manual approval signature obtained

### Final Deployment Checklist:
- [ ] All tests passing (>80% coverage)
- [ ] API documentation complete
- [ ] ALCOA++ audit trail complete
- [ ] Performance benchmarks met
- [ ] Security review passed
- [ ] Backup/restore tested
- [ ] Monitoring configured
- [ ] User training completed

---

## ALCOA++ Traceability Map

| Activity | Trace Location | Checksum | Signature Required |
|----------|----------------|----------|-------------------|
| Original data | `trace/raw_data/` | SHA-256 | No |
| Validation run | `trace/validation_runs/{timestamp}/` | SHA-256 | Yes |
| Algorithm version | `trace/algorithm_versions/v{x}.{y}/` | SHA-256 | Yes (major versions) |
| Audit log | `trace/audit_logs/{date}.log` | N/A | No |
| Git commits | `.git/` | Git SHA-1 | No |
| Database records | PostgreSQL | Auto-increment ID | No |
| Manual approvals | `trace/signatures/` | N/A | Yes |

---

## Blockers & Risks

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| Cannot achieve R² ≥ 0.90 | High - Blocks all phases | Expert review, ensemble methods | Monitoring |
| Modified compounds fail | Medium - Partial algorithm | Separate pipeline for modified | Identified |
| PostgreSQL compatibility | Low - Alternative DBs exist | Use SQLite for dev | N/A |
| Performance issues | Medium - UX degradation | Celery offload, caching | TBD |

---

## Notes & Decisions

**2025-10-21 14:45** - Phase 1.1 Complete
- Initial validation shows R² = 0.66-0.82 (below target)
- Root causes identified: modified compounds, overfitting, variance
- Decision: Proceed to Phase 1.2 (Auto-Tuning)
- ALCOA++ trace system established

**2025-10-21 15:00** - ALCOA++ System Ready
- Full audit trail structure created
- Validation runs now include signatures
- Original data preserved with checksums
- Ready for manual validation audits

---

**Last Updated**: 2025-10-21 15:00
**Current Phase**: 1.2 - Auto-Tuning
**Next Milestone**: Achieve R² ≥ 0.90
**Estimated Completion**: 2025-11-15 (4 weeks)
