# Algorithm Version Changelog

## v1.1 - Separated Modified Compounds (2025-10-21) ✅ VALIDATED

**Status**: ✅ Production Ready - Exceeds target R² ≥ 0.90

### Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| R² (LOO) | 0.9737 | ≥ 0.90 | ✅ PASS (+8.2%) |
| R² (K-Fold) | 0.9194 | ≥ 0.90 | ✅ PASS (+2.2%) |
| Improvement | +38.9% | - | ✅ Significant |

### Changes

**Strategy**: Separate regression models for modified vs unmodified gangliosides

**Modifications Detected**:
- +HexNAc (N-acetylhexosamine)
- +dHex (Deoxyhexose)
- +OAc (O-acetylation)
- +NeuAc, +NeuGc (additional sialic acids)

**Implementation**:
```python
if compound.is_modified:
    model = modified_compounds_model
else:
    model = base_compounds_model
```

**Files**:
- `run_simple_tuning.py` - Validation script
- `trace/tuning_results_simple.json` - Full results
- `trace/algorithm_versions/v1.1_separated/` - Archived version

**Validation Data**:
- Dataset: testwork_user.csv (323 compounds, 49 anchors)
- Modified compounds: 89 (27.6%)
- Base compounds: 234 (72.4%)

### Why It Worked

**Root Cause**: Modified compounds have different Log P-RT relationships due to additional sugar moieties

**Evidence**:
- Baseline worst predictions were ALL modified compounds
- GD1+HexNAc(40:1;O2): 2.051 min error (baseline)
- After separation: Errors reduced significantly

**Chemical Justification**: Different modification types alter lipophilicity differently, requiring distinct calibration curves

### Next Steps

- ✅ Archive in trace/ folder
- ⏳ Get stakeholder approval signature
- ⏳ Tag Git: v1.1-validated
- ⏳ Proceed to Week 2 (Visualization)

---

## v1.0 - Baseline (2025-10-21) ❌ BELOW TARGET

**Status**: ❌ Failed validation - R² < 0.90

### Performance

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| R² (LOO) | 0.8246 | ≥ 0.90 | ❌ FAIL |
| R² (K-Fold) | 0.6619 | ≥ 0.90 | ❌ FAIL |
| Overfitting | 0.1502 | < 0.10 | ❌ Too high |

### Issues

1. Modified compounds caused large errors (>2 min)
2. High overfitting (train R²=0.81, test R²=0.66)
3. High variance across folds (σ=0.21)

### Configuration

- Features: Log P only
- Model: LinearRegression()
- Strategy: Single model for all compounds
- Separation: None

**Files**:
- `validate_standalone.py` - Original validator
- `trace/algorithm_versions/v1.0_baseline/` - Archived baseline

### Decision

Proceed to v1.1 with compound type separation

---

## Version Summary

| Version | R² (K-Fold) | Status | Strategy |
|---------|-------------|--------|----------|
| v1.0 | 0.6619 | ❌ Failed | Single model for all |
| v1.1 | 0.9194 | ✅ Success | Separate modified/base | ← **CURRENT**

**Recommended for Production**: v1.1

---

**Last Updated**: 2025-10-21
**Latest Version**: v1.1 (separated modified compounds)
**Validation Status**: ✅ PASSED Week 1 Gate
