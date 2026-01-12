# Scientific Credibility Roadmap
## LC-MS/MS Ganglioside Analysis Platform

**Created**: 2025-12-30
**Goal**: Transform from "data management tool" to "scientifically credible validation tool"

---

## Current State Assessment

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Minimum samples per prefix | 3 | 10+ | -7 |
| Sample/feature ratio | n/p ≈ 1 | n/p ≥ 5 | Critical |
| External validation | None | Required | Missing |
| Heteroscedasticity handling | Ignored | Weighted LS | Missing |
| Extrapolation warnings | None | Explicit | ✅ Added |
| Statistical diagnostics | Basic | Comprehensive | Partial |
| Confidence calibration | Arbitrary | Validated | Missing |

---

## Phase 1: Immediate Safeguards (COMPLETED)

### ✅ 1.1 Input Validation (`input_validator.py`)
- [x] Case-insensitive column normalization
- [x] Robust anchor boolean parsing
- [x] NaN detection and explicit rejection
- [x] Physical bounds validation
- [x] Duplicate compound detection
- [x] Reserved column protection
- [x] CSV injection prevention
- [x] Transparent row dropping with details

### ✅ 1.2 Statistical Safeguards (`statistical_safeguards.py`)
- [x] Sample-size-aware R² thresholds
- [x] Confidence level classification (UNRELIABLE/LOW/MODERATE/HIGH)
- [x] Cross-validation meaningfulness assessment
- [x] Extrapolation detection with severity levels
- [x] Heteroscedasticity testing (Breusch-Pagan)
- [x] VIF calculation for multicollinearity
- [x] Outlier detection validity assessment

### Tests Created
- [x] 68 tests for InputValidator
- [x] 45 tests for StatisticalSafeguards
- [x] All 113 tests passing

---

## Phase 2: Integration (1-2 Weeks)

### 2.1 Integrate Safeguards into Pipeline
**Priority**: HIGH
**Effort**: 3-5 days

```python
# In ganglioside_processor_v3.py
from .input_validator import InputValidator
from .statistical_safeguards import StatisticalSafeguards

class GangliosideProcessorV3:
    def __init__(self):
        self.input_validator = InputValidator()
        self.safeguards = StatisticalSafeguards()
    
    def process(self, df, ...):
        # 1. Validate input first
        validation = self.input_validator.validate(df)
        if not validation.is_valid:
            return ProcessingResult(
                success=False,
                errors=validation.errors,
                validation_details=validation.to_dict()
            )
        
        # 2. After regression, run diagnostics
        diagnostics = self.safeguards.run_full_diagnostics(
            X=X, y=y, residuals=residuals,
            feature_names=features,
            X_predict=X_test
        )
        
        # 3. Include in results
        return ProcessingResult(
            statistical_diagnostics=diagnostics.to_dict()
        )
```

### 2.2 API Response Enhancement
**Priority**: HIGH
**Effort**: 1-2 days

```python
# Enhanced API response structure
{
    "success": true,
    "validation": {
        "rows_received": 100,
        "rows_processed": 95,
        "dropped_rows": [...],
        "warnings": [...]
    },
    "regression_analysis": {
        "GD1": {
            "r2": 0.85,
            "diagnostics": {
                "confidence_level": "moderate",
                "sample_assessment": {...},
                "extrapolation": {...},
                "heteroscedasticity": {...},
                "warnings": [...],
                "recommendations": [...]
            }
        }
    }
}
```

### 2.3 Update Confidence Scoring
**Priority**: MEDIUM
**Effort**: 2-3 days

- Integrate `StatisticalSafeguards.confidence_level` into `ConfidenceScorer`
- Penalize LOW/UNRELIABLE confidence levels
- Add sample size to confidence calculation
- Calibrate weights against ground truth (if available)

---

## Phase 3: Honest Uncertainty Communication (2-4 Weeks)

### 3.1 User-Facing Confidence Display
**Priority**: HIGH
**Effort**: 3-5 days

```python
# Clear, honest messaging
confidence_messages = {
    ConfidenceLevel.UNRELIABLE: {
        "icon": "⚠️",
        "color": "red",
        "message": "Results unreliable (n={n} samples)",
        "recommendation": "Add {needed} more anchors for reliable results"
    },
    ConfidenceLevel.LOW: {
        "icon": "🟡",
        "color": "yellow", 
        "message": "Low confidence (n={n} samples)",
        "recommendation": "Consider adding more anchors"
    },
    ConfidenceLevel.MODERATE: {
        "icon": "🟢",
        "color": "green",
        "message": "Moderate confidence (n={n} samples)"
    },
    ConfidenceLevel.HIGH: {
        "icon": "✅",
        "color": "green",
        "message": "High confidence (n={n} samples)"
    }
}
```

### 3.2 Extrapolation Warnings in UI
**Priority**: MEDIUM
**Effort**: 2-3 days

- Highlight extrapolated predictions in results table
- Show extrapolation severity (mild/moderate/severe)
- Recommend adding anchors in extrapolation range

### 3.3 Diagnostic Reports
**Priority**: MEDIUM
**Effort**: 3-5 days

Generate downloadable reports with:
- Residual plots (if n sufficient)
- QQ plots for normality
- Heteroscedasticity visualization
- VIF table for multicollinearity
- Sample size recommendations

---

## Phase 4: External Validation (1-2 Months)

### 4.1 Collect Ground Truth Data
**Priority**: CRITICAL
**Effort**: Ongoing

Requirements:
- Known correct compound identifications
- Multiple LC-MS systems/methods for comparison
- Different sample types (porcine, bovine, human)
- Minimum 50+ validated compounds per category

### 4.2 Train/Test Split Architecture
**Priority**: HIGH
**Effort**: 1 week

```python
# Proper holdout validation
class ValidationFramework:
    def __init__(self, holdout_fraction=0.2):
        self.holdout_fraction = holdout_fraction
    
    def evaluate_model(self, df):
        # 1. Split data (stratified by prefix)
        train, test = self.stratified_split(df)
        
        # 2. Train on training set only
        model = self.fit(train)
        
        # 3. Evaluate on holdout
        metrics = self.evaluate(model, test)
        
        return {
            "training_r2": model.r2,
            "holdout_r2": metrics["r2"],  # TRUE generalization
            "overfit_ratio": model.r2 / metrics["r2"]
        }
```

### 4.3 Cross-Method Validation
**Priority**: HIGH
**Effort**: 2-4 weeks

Compare predictions across:
- Different LC systems
- Different columns (C18 vs C8)
- Different mobile phases
- Different temperatures

Establish confidence only when predictions are consistent.

---

## Phase 5: Robust Regression Methods (2-4 Weeks)

### 5.1 Implement Weighted Least Squares
**Priority**: HIGH
**Effort**: 1 week

```python
from sklearn.linear_model import Ridge

class WeightedRegression:
    def fit(self, X, y, weights=None):
        if weights is None:
            # Estimate weights from residual variance
            initial_fit = Ridge(alpha=1.0).fit(X, y)
            residuals = y - initial_fit.predict(X)
            weights = 1 / (residuals**2 + 1e-6)
        
        # Weighted fit
        sample_weight = weights / weights.sum()
        self.model = Ridge(alpha=1.0).fit(X, y, sample_weight=sample_weight)
```

### 5.2 Implement Robust Regression
**Priority**: MEDIUM
**Effort**: 1 week

```python
from sklearn.linear_model import HuberRegressor, RANSACRegressor

class RobustRegressionFallback:
    """Fallback to robust methods when OLS/Ridge assumptions violated."""
    
    def fit(self, X, y, diagnostics):
        if diagnostics.heteroscedasticity_detected:
            return HuberRegressor().fit(X, y)
        
        if diagnostics.outlier_warning:
            return RANSACRegressor().fit(X, y)
        
        return Ridge(alpha=1.0).fit(X, y)
```

### 5.3 Bootstrap Stability Assessment
**Priority**: MEDIUM
**Effort**: 1 week

```python
def assess_stability(X, y, n_bootstrap=100):
    """Assess model stability via bootstrap."""
    coefficients = []
    
    for _ in range(n_bootstrap):
        idx = np.random.choice(len(X), len(X), replace=True)
        model = Ridge(alpha=1.0).fit(X[idx], y[idx])
        coefficients.append(model.coef_)
    
    coefficients = np.array(coefficients)
    
    return {
        "coef_mean": coefficients.mean(axis=0),
        "coef_std": coefficients.std(axis=0),
        "stability_score": 1 - coefficients.std(axis=0).mean()
    }
```

---

## Phase 6: Long-Term Improvements (3-6 Months)

### 6.1 Bayesian Model Averaging
**Priority**: LOW
**Effort**: 2-4 weeks

Instead of picking single model, average across:
- Different regularization strengths
- Different feature subsets
- Different model types

### 6.2 Hierarchical/Pooled Models
**Priority**: MEDIUM
**Effort**: 2-4 weeks

Pool data across similar prefixes to increase effective sample size:
- Partial pooling between GD1, GD2, GD3
- Share information between similar glycolipid classes

### 6.3 Active Learning
**Priority**: LOW
**Effort**: 1-2 months

Recommend which compounds to add as anchors for maximum information gain.

---

## Success Metrics

### Immediate (Phase 1-2)
- [x] All inputs validated with transparent reporting
- [x] Extrapolation warnings implemented
- [ ] Confidence levels displayed in API response
- [ ] No more silent failures

### Short-Term (Phase 3-4)
- [ ] Holdout R² > 0.70 for validated datasets
- [ ] Overfit ratio < 1.2 (training R² / holdout R²)
- [ ] Ground truth validation dataset collected
- [ ] Cross-method consistency > 80%

### Long-Term (Phase 5-6)
- [ ] False positive rate < 5%
- [ ] False negative rate < 10%
- [ ] Peer-reviewed validation published
- [ ] Community-accepted thresholds established

---

## Technical Debt to Address

### High Priority
1. Consolidate two regression implementations (Ridge vs Bayesian)
2. Remove circular reasoning in chemical validation
3. Fix adjusted R² formula for regularized regression

### Medium Priority
4. Add comprehensive logging for debugging
5. Create regression diagnostics visualization
6. Implement proper caching for repeated analyses

### Low Priority
7. Add unit tests for edge cases in existing code
8. Refactor duplicate code between V1/V2/V3 processors
9. Document chemical assumptions with citations

---

## Dependencies and Prerequisites

### For Phase 2
- Integration approval for API changes
- Frontend support for new response format

### For Phase 4
- Access to validated compound library
- Multiple LC-MS datasets for comparison
- Domain expert review of validation criteria

### For Phase 5-6
- Computational resources for bootstrap/BMA
- Statistical consultation for model selection

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Ground truth data unavailable | Medium | High | Start with simulated validation |
| Users resist honest uncertainty | Medium | Medium | Gradual rollout with education |
| Performance regression | Low | Medium | Comprehensive test coverage |
| Breaking API changes | Medium | High | Versioned API endpoints |

---

## Next Steps

1. **This Week**: Integrate `InputValidator` and `StatisticalSafeguards` into V3 processor
2. **Next Week**: Update API responses to include diagnostics
3. **2 Weeks**: Deploy to staging for user feedback
4. **1 Month**: Begin ground truth data collection
5. **2 Months**: Implement holdout validation framework
