# 4-Week Master Plan: Django Ganglioside Migration with ALCOA++ Compliance
## **APPROVED PLAN** - Conservative Timeline with Full Scope

**Project**: Migration from Flask to Django with Algorithm Validation
**Duration**: 4 weeks (20 working days)
**Approach**: Conservative with realistic buffers
**Scope**: Complete migration including all 4 priorities + deployment
**Gate**: Must achieve R² ≥ 0.90 before proceeding to Django features

**Created**: 2025-10-21
**Status**: ✅ APPROVED - Execution started

---

## Week 1: Algorithm Validation & ALCOA++ Foundation (Days 1-5)

### **CRITICAL GATE**: Must achieve R² ≥ 0.90 to proceed

**Current Baseline Performance**:
- LOO R² = 0.8246 (below target)
- K-Fold R² = 0.6619 (significant overfitting)
- Overfitting score = 0.2076 (too high)
- Root cause: Modified compounds (+HexNAc) failing, 9 features causing overfitting

**Day 1-2: Auto-Tuner Development & Iteration 1-2** ⏳ IN PROGRESS
- ✅ Build `apps/analysis/services/algorithm_tuner.py` module (COMPLETE)
- ✅ Build `apps/analysis/services/ganglioside_processor_tuned.py` (COMPLETE)
- ✅ Create `run_autotuner.py` script (COMPLETE)
- Implement tuning history tracking with ALCOA++ compliance
- **Iteration 1**: Separate modified vs unmodified compounds
  - Detect +HexNAc, +dHex, +OAc modifications
  - Create separate regression models
  - Validate (target: R² ≥ 0.85)
  - Archive in `trace/algorithm_versions/v1.1_separated/`
- **Iteration 2**: Reduce features from 9 → 2 (Log P + carbon chain)
  - Update GangliosideProcessor
  - Validate (target: R² ≥ 0.88, overfitting < 0.15)
  - Archive in `trace/algorithm_versions/v1.2_reduced/`

**Day 3: Auto-Tuner Iteration 3-4**
- **Iteration 3**: Add Ridge regularization (α=1.0)
  - Replace LinearRegression → Ridge
  - Tune alpha parameter (0.1, 1.0, 10.0)
  - Validate (target: R² ≥ 0.90, overfitting < 0.10)
  - Archive in `trace/algorithm_versions/v1.3_ridge/`
- **Iteration 4**: Pool related prefix groups (if needed)
  - Combine GM1/GM2/GM3 → GM*
  - Increase sample size per model
  - Validate (target: R² ≥ 0.90)

**Day 4: Final Validation & ALCOA++ Completion**
- Run comprehensive validation suite:
  - Leave-One-Out (must be ≥ 0.90)
  - 5-Fold cross-validation (must be ≥ 0.90)
  - 10-Fold for stability check
- Complete trace/ folder structure:
  - Populate `trace/validation_runs/` with all runs
  - Create comparison reports
  - Generate signature templates
- Document tuning history in `trace/algorithm_versions/changelog.md`

**Day 5: Manual Review & Approval**
- Review all validation results
- Analyze per-compound predictions
- Get stakeholder sign-off
- Complete `trace/signatures/validation_approval.txt`
- **BUFFER DAY** for any issues from Days 1-4
- Tag Git: `v1.0-validated`

**Week 1 Deliverables**:
- ✅ Algorithm with R² ≥ 0.90 (validated)
- ✅ Complete ALCOA++ audit trail
- ✅ Signed validation approval
- ✅ Tuning history documentation

---

## Week 2: Visualization Dashboard & API Foundation (Days 6-10)

**Prerequisites**: Week 1 gate passed (R² ≥ 0.90)

**Day 6-7: Validation Results Dashboard**
- Create `apps/visualization/` Django app
- Build dashboard views and templates:
  - R² comparison chart (LOO vs K-Fold vs Bootstrap)
  - Actual vs Predicted RT scatter plot (Plotly.js)
  - Residual distribution histogram
  - Overfitting indicator gauge
  - Per-fold performance breakdown
- Add per-compound performance table (sortable, filterable)
- Implement color-coding by error magnitude
- Export functionality (CSV/Excel)

**Day 8: Real-Time Progress & History**
- Set up Django Channels for WebSocket support
- Install Redis for channel layer
- Create progress tracking during validation
- Build validation history timeline
- Add side-by-side run comparison
- Trend analysis visualization (improving/degrading)

**Day 9: Analysis Results Visualization**
- Ganglioside category breakdown (pie/bar charts)
- Regression model display per prefix group
- Plot regression lines with confidence intervals
- Diagnostic plots:
  - Q-Q plot for normality
  - Cook's distance (outlier detection)
  - Leverage plot
  - Residuals vs Fitted values
- Interactive filtering by category/modification

**Day 10: DRF Serializers & ViewSets**
- Create `apps/analysis/serializers.py`:
  - AnalysisSessionSerializer
  - CompoundSerializer
  - RegressionModelSerializer
  - ValidationResultSerializer (new model)
- Create `apps/analysis/views.py`:
  - AnalysisSessionViewSet
  - CompoundViewSet
  - ValidationViewSet
- Set up API router with versioning (v1/)
- Add authentication (Token) and permissions
- **BUFFER TIME** for visualization debugging

**Week 2 Deliverables**:
- ✅ Interactive validation dashboard
- ✅ Real-time progress tracking (WebSocket)
- ✅ Analysis visualization with diagnostic plots
- ✅ DRF API foundation (serializers + viewsets)

---

## Week 3: Database Persistence & Background Tasks (Days 11-15)

**Day 11: PostgreSQL Setup & Models Extension**
- Install PostgreSQL locally
- Create database `ganglioside_dev`
- Configure `.env` with database credentials
- Extend models:
  - Add `ValidationResult` model
  - Add `TuningHistory` model
  - Add `AuditLog` model (ALCOA++)
  - Update relationships
- Run migrations
- Create initial data fixtures

**Day 12: API Endpoints & Documentation**
- Analysis endpoints:
  - `POST /api/v1/analysis/` - Create analysis
  - `GET /api/v1/analysis/{id}/` - Retrieve results
  - `POST /api/v1/analysis/{id}/validate/` - Run validation
  - `GET /api/v1/analysis/{id}/export/` - Export results
- Validation endpoints:
  - `POST /api/v1/validate/` - Run standalone validation
  - `GET /api/v1/validate/{id}/` - Get results
  - `GET /api/v1/validate/history/` - List all validations
- Generate Swagger/ReDoc documentation
- Create Postman collection

**Day 13: Service Layer & Data Migration**
- Create `apps/analysis/services/analysis_service.py`:
  - Orchestrates processor + validator
  - Handles database transactions
  - Manages file uploads
- Create `apps/analysis/services/validation_service.py`:
  - Runs validation with ALCOA++ trace
  - Saves to both database and trace/ folder
  - Generates signatures
- Integrate trace/ folder with database:
  - Store trace references in DB
  - Add ALCOA++ metadata fields
  - Link validation runs to records

**Day 14: Celery Setup & Task Definitions**
- Install Redis (if not already from Channels)
- Configure Celery broker in `config/celery.py`
- Create worker processes
- Define tasks in `apps/analysis/tasks.py`:
  - `run_analysis_task(session_id)`
  - `run_validation_task(data_file, method)`
  - `export_results_task(session_id, format)`
  - `cleanup_old_results_task()`
- Implement progress tracking via Celery states
- Send WebSocket updates from tasks

**Day 15: Notifications & ALCOA++ Integration**
- Email notifications:
  - Analysis complete
  - Validation results ready
  - Error notifications
- Webhook support for external systems
- Link Celery tasks to audit logs
- **BUFFER DAY** for database/Celery integration issues

**Week 3 Deliverables**:
- ✅ PostgreSQL database with all models
- ✅ Complete REST API with documentation
- ✅ Service layer connecting components
- ✅ Celery background tasks with progress tracking
- ✅ Email/webhook notifications

---

## Week 4: Testing, Documentation & Deployment (Days 16-20)

**Day 16-17: Comprehensive Testing**
- Unit tests (target >80% coverage):
  - Algorithm functions (processor, validator, tuner)
  - Serializers and ViewSets
  - Service layer
  - Celery tasks
- Integration tests:
  - End-to-end analysis workflow
  - Database transactions
  - API endpoints
  - WebSocket connections
- Performance tests:
  - Large datasets (1000+ compounds)
  - Concurrent validations
  - API response times

**Day 18: Documentation**
- User documentation:
  - Quick start guide
  - How to run analysis
  - Validation guide (ALCOA++ procedures)
  - Troubleshooting guide
- Developer documentation:
  - Architecture overview
  - Database schema diagrams
  - Algorithm explanation
  - API integration examples
  - Contribution guide
- ALCOA++ compliance documentation:
  - Audit trail procedures
  - Data integrity verification steps
  - Signature requirements
  - Retention policies

**Day 19: Dockerization & CI/CD**
- Create Dockerfiles:
  - Django app container
  - Celery worker container
  - Redis container (or use external)
  - PostgreSQL container (or use external)
- Docker Compose:
  - Development environment
  - Production environment
  - Volume management for trace/ folder
- GitHub Actions:
  - Run tests on push
  - Linting (flake8, black)
  - Security checks (bandit)
  - Auto-deploy to staging

**Day 20: Production Deployment Preparation**
- Configure production server (nginx reverse proxy)
- SSL certificates setup
- Environment variable management
- Database backup/restore procedures
- Set up monitoring:
  - Application logging (Sentry/LogRocket)
  - Performance monitoring (APM)
  - Alerting rules
- Zero-downtime deployment scripts
- Rollback procedures
- **FINAL BUFFER DAY** for any remaining issues

**Week 4 Deliverables**:
- ✅ Comprehensive test suite (>80% coverage)
- ✅ Complete user + developer documentation
- ✅ Docker containers + Docker Compose
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ Production deployment ready
- ✅ Monitoring and alerting configured

---

## Success Criteria by Week

### Week 1 Gate (MUST PASS):
- [ ] R² ≥ 0.90 (Leave-One-Out)
- [ ] R² ≥ 0.90 (5-Fold)
- [ ] Overfitting < 0.10
- [ ] RMSE < 0.15 min
- [ ] Consistency: |R²_LOO - R²_KFold| < 0.05
- [ ] Complete ALCOA++ trace with signatures

### Week 2 Completion:
- [ ] Interactive dashboard deployed
- [ ] Real-time validation progress visible
- [ ] DRF API endpoints functional
- [ ] Swagger documentation generated

### Week 3 Completion:
- [ ] Database fully integrated
- [ ] All API endpoints working
- [ ] Celery tasks processing analyses
- [ ] Email notifications sending

### Week 4 Completion:
- [ ] >80% test coverage
- [ ] All documentation complete
- [ ] Docker deployment working
- [ ] CI/CD pipeline passing

---

## Risk Mitigation

| Risk | Likelihood | Mitigation | Buffer |
|------|------------|------------|--------|
| Can't achieve R² ≥ 0.90 | Medium | Expert review, ensemble methods, relax to 0.85 | Day 5 |
| Modified compounds still fail | Medium | Separate pipeline, exclude from current scope | Day 5 |
| Django Channels issues | Low | Fallback to polling, simpler progress tracking | Day 10 |
| Celery configuration problems | Medium | Use synchronous processing temporarily | Day 15 |
| PostgreSQL performance | Low | Optimize queries, add indexes | Day 15 |
| Testing takes longer | Medium | Reduce coverage target to 70% | Day 17 |
| Deployment complications | Low | Deploy to staging only, defer production | Day 20 |

---

## Daily Time Allocation

**Conservative estimates with 8-hour days:**
- Algorithm development: 4-6 hours coding
- Testing/validation: 1-2 hours
- Documentation: 1 hour
- Code review/debugging: 1-2 hours

**Total**: ~100-120 hours of work over 4 weeks

---

## Phased Rollout Strategy

If timeline becomes tight, prioritize:
1. **Phase 1 (Week 1)**: MUST complete - algorithm validation
2. **Phase 2 (Week 2)**: Dashboard + basic API
3. **Phase 3 (Week 3)**: Database + Celery (can defer)
4. **Phase 4 (Week 4)**: Testing + deployment (can extend)

**Minimum viable product**: Weeks 1-2 only (validated algorithm + visualization)

---

## ALCOA++ Checkpoints

Throughout all 4 weeks, maintain compliance:
- **Daily**: Update audit_trail.csv
- **Per validation**: Create trace/validation_runs/ entry
- **Per algorithm change**: Archive in trace/algorithm_versions/
- **Weekly**: Review signatures and approvals
- **End of project**: Final compliance audit

---

## Current Status (2025-10-21)

### Completed:
- ✅ Initial validation (LOO R²=0.82, K-Fold R²=0.66)
- ✅ ALCOA++ trace/ structure created
- ✅ `algorithm_tuner.py` module built
- ✅ `ganglioside_processor_tuned.py` built
- ✅ `run_autotuner.py` script created

### In Progress:
- 🔄 Week 1 Day 1-2: Running auto-tuner iterations 1-2

### Next Immediate Actions:
1. Run auto-tuner: `python run_autotuner.py --data ../data/samples/testwork_user.csv`
2. Check if Iteration 1 achieves R² ≥ 0.85
3. Continue iterations until R² ≥ 0.90
4. Complete Week 1 validation gate

---

**Last Updated**: 2025-10-21 15:30
**Current Week**: Week 1 (Days 1-2)
**Progress**: 5% overall (Week 1 in progress)
**Next Milestone**: Achieve R² ≥ 0.90 (Week 1 gate)
**Estimated Completion**: 2025-11-15 (4 weeks from start)
