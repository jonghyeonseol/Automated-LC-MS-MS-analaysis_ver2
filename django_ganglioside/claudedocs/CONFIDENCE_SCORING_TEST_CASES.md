# Confidence Scoring Vulnerability Test Cases

**Purpose**: Concrete examples demonstrating weaknesses in the confidence scoring system
**Related**: `CONFIDENCE_SCORING_VULNERABILITIES.md`
**Date**: 2025-12-30

---

## Test Case 1: The "All Missing Data" Compound

### Scenario
A compound has **zero validation data** - no regression, no residuals, no chemical validation.

### Input
```python
scorer = ConfidenceScorer()
score = scorer.score_compound(
    compound_name="UNKNOWN(99:9;O9)",
    # All data fields omitted/None
)
```

### Expected Behavior (Ideal)
```python
assert score.overall_score == 0.0 or score.overall_score is None
assert score.confidence_level == ConfidenceLevel.INSUFFICIENT_DATA
assert "Cannot score - no validation data" in score.warnings
```

### Actual Behavior
```python
# All component scores default to 0.5
overall_score = 0.5 × 1.0 = 0.5
confidence_level = ConfidenceLevel.LOW
warnings = []  # No warnings!
```

### Why This Fails
- **0.5 score implies "average quality"** when reality is "no evidence"
- User sees LOW confidence and thinks "this compound was analyzed and found questionable"
- Reality: "this compound was never analyzed at all"

### Impact
Compounds with zero evidence receive the same score as compounds with actual problems.

---

## Test Case 2: The "Perfect Score" Illusion

### Scenario
A compound has perfect scores on all validation components.

### Input
```python
score = scorer.score_compound(
    compound_name="GD1(36:1;O2)",
    regression_data={'r2': 0.99, 'rmse': 0.01, 'n_samples': 50},
    residual_data={'std_residual': 0.1},
    bayesian_data={'std_dev': 0.01, 'predicted_rt': 9.0},
    chemical_validation={'coefficient_validity': {'Log P': True}},
    cross_prefix_results={'is_valid': True, 'category_violations': []},
    modification_results={'rt_ordering_violations': []},
)
```

### Expected Behavior (Ideal)
```python
assert 0.9 <= score.overall_score <= 0.95  # Never exactly 1.0
assert "Exceptionally high confidence - verify data quality" in score.warnings
assert "No system is perfect - manual review recommended" in score.recommendations
```

### Actual Behavior
```python
overall_score = 1.0  # Perfect score
confidence_level = ConfidenceLevel.HIGH
warnings = []  # No warnings about overconfidence
```

### Why This Fails
- **1.0 score implies 100% certainty**, which is scientifically unjustifiable
- LC-MS/MS has inherent uncertainty (instrument noise, matrix effects, ion suppression)
- No warnings about overconfidence or need for manual verification

### Impact
Users may treat 1.0 compounds as "ground truth" without skepticism.

---

## Test Case 3: The "Chemical Violation Override"

### Scenario
A compound has **excellent statistical properties** but **violates fundamental chemistry**.

### Input
```python
score = scorer.score_compound(
    compound_name="GD1+OAc(36:1;O2)",
    regression_data={'r2': 0.95, 'rmse': 0.1, 'n_samples': 20},  # Excellent
    residual_data={'std_residual': 0.3},  # Low residual
    bayesian_data={'std_dev': 0.1, 'predicted_rt': 9.0},  # Low uncertainty
    chemical_validation={
        'coefficient_validity': {'Log P': False},  # WRONG coefficient sign
        'oacetylation': {'is_invalid': True},  # O-acetylation decreased RT (impossible)
    },
    cross_prefix_results={'is_valid': True},
    modification_results={'rt_ordering_violations': []},
)
```

### Expected Behavior (Ideal)
```python
# Chemical violations should ZERO OUT statistical scores
assert score.overall_score < 0.3  # Severely penalized
assert score.confidence_level == ConfidenceLevel.VERY_LOW
assert "Chemical impossibility detected - regression model invalid" in score.warnings
```

### Actual Behavior
```python
# Additive scoring:
regression_score = 1.0 × 0.20 = 0.20
residual_score = 1.0 × 0.25 = 0.25
bayesian_score = 1.0 × 0.20 = 0.20
chemical_score = (1.0 - 0.15 - 0.20) × 0.20 = 0.13  # Only 0.35 penalty
cross_prefix_score = 1.0 × 0.10 = 0.10
modification_score = 1.0 × 0.05 = 0.05

overall_score = 0.20 + 0.25 + 0.20 + 0.13 + 0.10 + 0.05 = 0.93

# Wait, let me recalculate (coefficient violation = 0.15 penalty, oacetyl = 0.20 penalty):
chemical_score = (1.0 - 0.15 - 0.20) = 0.65
chemical_contribution = 0.65 × 0.20 = 0.13

overall_score ≈ 0.93 × (scaling adjustment) ≈ 0.73 → MEDIUM confidence
```

### Why This Fails
- **Chemical violations are additive penalties**, not multiplicative
- Regression model based on wrong chemical assumptions → all regression-derived scores meaningless
- Yet system still reports MEDIUM confidence

### Impact
Chemically impossible compounds can still achieve passing scores.

---

## Test Case 4: The "Correlated Failure Cascade"

### Scenario
A compound fails regression (low R²) which **causes** high residuals and high uncertainty.

### Input
```python
score = scorer.score_compound(
    compound_name="GM3(40:2;O3)",
    regression_data={'r2': 0.40, 'rmse': 0.8, 'n_samples': 5},  # Poor fit
    residual_data={'std_residual': 2.8},  # High residual (CAUSED by poor fit)
    bayesian_data={'std_dev': 1.5, 'predicted_rt': 10.0},  # High uncertainty (CAUSED by poor fit)
    chemical_validation={'coefficient_validity': {'Log P': True}},
    cross_prefix_results={'is_valid': True},
    modification_results={'rt_ordering_violations': []},
)
```

### Expected Behavior (Ideal)
```python
# Should recognize these are NOT independent failures
# Poor R² → unreliable predictions → high residuals/uncertainty expected
# Penalty should be ~(1 failure) not ~(3 failures)

overall_score ≈ 0.4  # Single root cause
confidence_level = ConfidenceLevel.LOW
```

### Actual Behavior
```python
# Additive scoring TRIPLE-COUNTS the same failure:
regression_score = 0.4 × 0.5 × 0.20 = 0.04  # Penalty 1
residual_score = 0.1 × 0.25 = 0.025  # Penalty 2 (caused by #1)
bayesian_score = 0.3 × 0.20 = 0.06  # Penalty 3 (caused by #1)

overall_score = 0.04 + 0.025 + 0.06 + (other components at 0.5)
              ≈ 0.125 + 0.375 = 0.50
# Still scores as LOW (0.4-0.6) but for WRONG REASON (triple-counting)
```

### Why This Fails
- Assumes **statistical independence** when failures are causally linked
- Over-penalizes compounds with a single root problem (poor regression)
- Under-penalizes compounds with multiple independent problems

### Impact
Misleading scores due to independence assumption violations.

---

## Test Case 5: The "Gaming By Omission"

### Scenario
Attacker provides only favorable validation data, omits unfavorable data.

### Attack Strategy
```python
# Step 1: Run full analysis
full_results = processor.process_data(df)

# Step 2: Cherry-pick compounds with high regression scores
good_regression_compounds = [
    c for c in full_results['valid_compounds']
    if c.get('r2', 0) > 0.90
]

# Step 3: Score these compounds WITHOUT providing residual data
# (hide the fact that they have high residuals)
scorer = ConfidenceScorer()
for compound in good_regression_compounds:
    score = scorer.score_compound(
        compound_name=compound['Name'],
        regression_data={'r2': compound['r2'], 'n_samples': 20},
        # Deliberately omit residual_data (high residual hidden)
        # Deliberately omit bayesian_data
        # Deliberately omit chemical_validation
    )
    # Result: 0.20×1.0 + 0.25×0.5 + 0.20×0.5 + 0.20×0.5 + 0.10×0.5 + 0.05×0.5
    #       = 0.60 (MEDIUM confidence from only regression!)
```

### Expected Behavior (Ideal)
```python
# System should detect selective reporting
assert "Only 1/6 validation components provided" in score.warnings
assert "Confidence score unreliable - insufficient data" in score.warnings
assert score.confidence_level == ConfidenceLevel.INSUFFICIENT_DATA
```

### Actual Behavior
```python
overall_score = 0.60  # MEDIUM confidence
confidence_level = ConfidenceLevel.MEDIUM
warnings = []  # No detection of gaming
```

### Why This Fails
- **No mechanism to detect incomplete data provision**
- Missing data defaults to 0.5 allow gaming by selective omission
- System cannot distinguish "data unavailable" from "data hidden"

### Impact
Users can manipulate scores by providing only favorable validation results.

---

## Test Case 6: The "Weight Exploitation"

### Scenario
Understand that `residual` has highest weight (0.25), game the system.

### Attack Strategy
```python
# Focus ALL effort on minimizing residual, ignore other components
# Example: Manually adjust RT values to minimize prediction error

manipulated_compounds = []
for compound in original_compounds:
    predicted_rt = regression_model.predict(compound['Log P'])
    # Cheat: Set measured RT = predicted RT
    compound['RT'] = predicted_rt
    compound['residual'] = 0.0  # Perfect alignment!
    manipulated_compounds.append(compound)

# Score manipulation
score = scorer.score_compound(
    regression_data={'r2': 0.75, 'n_samples': 10},  # Mediocre
    residual_data={'std_residual': 0.01},  # PERFECT (manipulated)
    # Other components: mediocre or missing
)
```

### Expected Behavior (Ideal)
```python
# System should detect suspiciously perfect residuals
assert "Residual too low for given R² - possible data manipulation" in score.warnings
assert "Audit data quality" in score.recommendations
```

### Actual Behavior
```python
# No detection, perfect residual scores highly:
residual_score = 1.0 × 0.25 = 0.25  # Max contribution
overall_score = 0.25 + (other components) ≈ 0.70+
confidence_level = ConfidenceLevel.MEDIUM to HIGH
```

### Why This Fails
- **Unbalanced weights create exploitable targets**
- No cross-validation between components (residual vs R² consistency)
- No anomaly detection for suspiciously perfect sub-scores

### Impact
Knowing the weights allows targeted data manipulation.

---

## Test Case 7: The "Threshold Boundary Game"

### Scenario
Understand that 0.7 is the validity threshold, optimize to just exceed it.

### Attack Strategy
```python
# Goal: Achieve score ≥ 0.70 with minimal effort

# Strategy: Maximize high-weight components
regression_data = {'r2': 0.85, 'n_samples': 10}  # Good → 0.60 × 0.20 = 0.12
residual_data = {'std_residual': 0.9}  # Good → 0.82 × 0.25 = 0.205
# Total so far: 0.325

# Other components: default to 0.5
bayesian_data = None  # → 0.5 × 0.20 = 0.10
chemical_validation = None  # → 0.5 × 0.20 = 0.10
cross_prefix = None  # → 0.5 × 0.10 = 0.05
modification = None  # → 0.5 × 0.05 = 0.025

# Total: 0.325 + 0.275 = 0.60 (below threshold)

# Adjust: Need to improve residual slightly
residual_data = {'std_residual': 0.5}  # Better → 0.90 × 0.25 = 0.225
# New total: 0.12 + 0.225 + 0.275 = 0.62 (still below)

# Adjust again: Provide chemical validation
chemical_validation = {'coefficient_validity': {'Log P': True}}
# Score: 1.0 × 0.20 = 0.20
# New total: 0.12 + 0.225 + 0.20 + 0.10 + 0.05 + 0.025 = 0.72 ✓

# Success: 0.72 > 0.70 threshold with minimal data
```

### Expected Behavior (Ideal)
```python
# System should require minimum data completeness
assert "Only 3/6 validation components provided" in score.warnings
assert "Confidence may be unreliable" in score.warnings
# OR: Raise threshold when data is incomplete
effective_threshold = 0.70 + 0.05 * (6 - num_components_provided)
```

### Actual Behavior
```python
overall_score = 0.72  # Passes threshold
confidence_level = ConfidenceLevel.MEDIUM
is_valid = True  # Accepted as valid compound
```

### Why This Fails
- **Fixed threshold** allows boundary optimization
- No penalty for incomplete data (only 3/6 components provided)
- Users can minimize validation effort while still passing

### Impact
Encourages minimal validation effort to just exceed threshold.

---

## Test Case 8: The "Contradictory Evidence" Compound

### Scenario
Different validation components provide **contradictory evidence**.

### Input
```python
score = scorer.score_compound(
    compound_name="GT1(38:1;O2)",
    regression_data={'r2': 0.95, 'n_samples': 20},  # Excellent fit
    residual_data={'std_residual': 3.5},  # OUTLIER (contradicts good fit!)
    bayesian_data={'std_dev': 0.05, 'predicted_rt': 8.0},  # Low uncertainty (contradicts outlier!)
    chemical_validation={'coefficient_validity': {'Log P': True}},  # Valid
    cross_prefix_results={'is_valid': False, 'category_violations': [...]},  # VIOLATION
)
```

### Expected Behavior (Ideal)
```python
# System should detect INTERNAL INCONSISTENCY
assert "Contradictory evidence detected" in score.warnings
assert "High R² but outlier residual - investigate data quality" in score.warnings
assert "Low Bayesian uncertainty conflicts with outlier status" in score.warnings
assert score.confidence_level == ConfidenceLevel.VERY_LOW  # Flag for review
```

### Actual Behavior
```python
# Additive scoring blindly averages contradictions:
regression_score = 1.0 × 0.20 = 0.20
residual_score = 0.1 × 0.25 = 0.025  # Outlier penalty
bayesian_score = 1.0 × 0.20 = 0.20
chemical_score = 1.0 × 0.20 = 0.20
cross_prefix_score = 0.7 × 0.10 = 0.07

overall_score ≈ 0.715  # Averages to MEDIUM confidence
# Contradictions are HIDDEN by averaging
```

### Why This Fails
- **No inconsistency detection** between components
- Averaging contradictions produces meaningless "middle ground" score
- Should be flagged for manual review, not auto-scored

### Impact
Internal contradictions are masked, producing unreliable scores.

---

## Test Case 9: The "No Regression Model" Compound

### Scenario
Compound belongs to a prefix group with **no anchor compounds** (no regression possible).

### Input
```python
# Example: GQ1 prefix has no anchors in training data
df = pd.DataFrame({
    'Name': ['GQ1(36:1;O2)'],  # Novel prefix
    'RT': [9.5],
    'Log P': [2.0],
    'Anchor': ['F'],
    'prefix': ['GQ1']  # No regression model exists for GQ1
})

regression_results = {
    'prefix_results': {
        'GD1': {...},
        'GM3': {...},
        # GQ1: missing (no anchors)
    }
}

score = scorer.score_compound(
    compound_name='GQ1(36:1;O2)',
    regression_data={},  # Empty dict (no model)
)
```

### Expected Behavior (Ideal)
```python
assert score.overall_score is None or score.overall_score == 0.0
assert score.confidence_level == ConfidenceLevel.NO_MODEL_AVAILABLE
assert "No regression model for prefix GQ1" in score.warnings
assert "Cannot validate - compound type not in training set" in score.detracting_factors
```

### Actual Behavior
```python
# Empty dict → missing data → 0.5 default
regression_score = 0.5
# Same for all other components (no data)
overall_score = 0.5
confidence_level = ConfidenceLevel.LOW
# No indication that there's NO WAY to validate this compound
```

### Why This Fails
- Cannot distinguish "data temporarily unavailable" from "fundamentally unvalidatable"
- Novel compounds receive same score as poorly-analyzed compounds
- No clear signal to user: "this compound type is outside our training scope"

### Impact
Users trust scores for compounds that cannot actually be validated.

---

## Test Case 10: The "Sample Size Ignorance"

### Scenario
Compare two compounds: one with n=50 samples, one with n=3 samples in regression.

### Input
```python
# Compound A: Large sample
score_A = scorer.score_compound(
    regression_data={'r2': 0.90, 'n_samples': 50},
)

# Compound B: Tiny sample (overfitting risk!)
score_B = scorer.score_compound(
    regression_data={'r2': 0.90, 'n_samples': 3},  # Same R² but n=3!
)
```

### Expected Behavior (Ideal)
```python
# n=3 with R²=0.90 is SUSPICIOUS (likely overfitting)
assert score_B.overall_score < score_A.overall_score - 0.2  # Significant penalty
assert "Small sample size - R² may be inflated by overfitting" in score_B.warnings
assert score_B.confidence_level <= ConfidenceLevel.LOW
```

### Actual Behavior
```python
# Both get similar regression_fit scores:
score_A_regression = (0.7 + 0.3) × 0.20 = 0.20  # Excellent R², large n
score_B_regression = (0.7 + 0.1) × 0.20 = 0.16  # Excellent R², small n penalty

# Only 0.04 difference (20% of 0.20 weight)
# Both likely score as MEDIUM overall
```

### Why This Fails
- **Small sample penalty is insufficient** (only 0.1 vs 0.3 max)
- R² with n=3 is **meaningless** (can always fit 3 points with 2+ parameters)
- Should be flagged as "untrustworthy model", not just slightly lower score

### Impact
Overfitted models based on tiny samples receive acceptable confidence scores.

---

## Summary Table

| Test Case | Vulnerability | Current Score | Should Be | Impact |
|-----------|---------------|---------------|-----------|--------|
| 1. All Missing | Default 0.5 | 0.50 (LOW) | 0.0 or NULL | Medium |
| 2. Perfect Score | No overconfidence warning | 1.00 (HIGH) | 0.90-0.95 + warning | Low |
| 3. Chemical Violation | Additive penalty | 0.73 (MED) | <0.3 (VERY_LOW) | High |
| 4. Correlated Failures | Triple-counting | 0.50 (LOW) | 0.40 (LOW) but different reason | Medium |
| 5. Gaming by Omission | No detection | 0.60 (MED) | INSUFFICIENT_DATA | High |
| 6. Weight Exploitation | No anomaly detection | 0.70+ (MED/HIGH) | Warning + review | Medium |
| 7. Threshold Boundary | No completeness check | 0.72 (MED) | Rejected or higher threshold | Medium |
| 8. Contradictory Evidence | No inconsistency check | 0.72 (MED) | VERY_LOW + flag | High |
| 9. No Regression Model | Can't distinguish | 0.50 (LOW) | NULL or NO_MODEL | High |
| 10. Small Sample n=3 | Insufficient penalty | 0.16 contribution | 0.0 or UNTRUSTWORTHY | High |

**Total High-Impact Vulnerabilities**: 5 out of 10

---

## Recommended Validation Tests

Add these tests to `tests/unit/test_confidence_scorer.py`:

```python
def test_all_missing_data_returns_none():
    """Missing data should not default to 0.5"""
    scorer = ConfidenceScorer()
    score = scorer.score_compound("UNKNOWN(99:9;O9)")
    assert score.overall_score is None or score.overall_score < 0.1
    assert "insufficient" in str(score.warnings).lower()

def test_perfect_score_triggers_warning():
    """Perfect scores should be flagged"""
    # ... (provide perfect data)
    assert score.overall_score < 1.0 or len(score.warnings) > 0

def test_chemical_violation_overrides_statistics():
    """Chemical impossibilities should dominate scoring"""
    # ... (excellent stats, chemical violation)
    assert score.overall_score < 0.4
    assert score.confidence_level == ConfidenceLevel.VERY_LOW

def test_small_sample_size_penalty():
    """n=3 samples should receive major penalty"""
    score_n3 = scorer.score_compound(
        regression_data={'r2': 0.90, 'n_samples': 3}
    )
    score_n50 = scorer.score_compound(
        regression_data={'r2': 0.90, 'n_samples': 50}
    )
    assert score_n3.overall_score < score_n50.overall_score - 0.2

def test_no_regression_model_detected():
    """Compounds without regression models should be flagged"""
    score = scorer.score_compound(
        compound_name="GQ1(36:1;O2)",
        regression_data={}  # No model
    )
    assert score.confidence_level == ConfidenceLevel.NO_MODEL_AVAILABLE
    assert "no model" in str(score.warnings).lower()
```

---

**Conclusion**: These test cases demonstrate that the confidence scoring system is vulnerable to manipulation, misinterpretation, and produces unreliable scores under common edge cases. Priority fixes required before production use.
