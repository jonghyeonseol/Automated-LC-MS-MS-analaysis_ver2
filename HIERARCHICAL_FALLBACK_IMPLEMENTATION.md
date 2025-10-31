# Hierarchical Fallback Implementation Guide

**Date**: October 31, 2025
**Solution**: Option A from N3_ANCHOR_SOLUTIONS.md
**Estimated Time**: 1-2 hours
**Expected Impact**: 10-15% accuracy improvement

---

## 🎯 Solution Overview

**Problem**: Groups with n=3 anchors are rejected (validation R²≈0.10), losing 30-40% of compounds.

**Solution**: Route n=3 groups directly to overall regression instead of rejecting them.

**Decision Logic**:
```
For each prefix group:
├─ n ≥ 4 AND validation R² ≥ 0.70? → Use prefix-specific model ✅
├─ n = 3? → Route to overall regression fallback 🔄
└─ n < 3? → Mark as insufficient anchors ❌
```

---

## 📝 Code Changes

### Change #1: Track Compounds for Fallback

**File**: `django_ganglioside/apps/analysis/services/ganglioside_processor.py`

**Location**: Lines 129-280 (inside `_apply_rule1_prefix_regression()`)

**Before** (current logic):
```python
def _apply_rule1_prefix_regression(self, df):
    valid_compounds = []
    outliers = []
    regression_results = {}

    for prefix in prefixes:
        anchor_compounds = prefix_group[prefix_group["Anchor"] == "T"]

        if len(anchor_compounds) >= 2:
            # Try regression
            validation_r2 = self._cross_validate_regression(X, y)

            if r2_for_threshold >= self.r2_threshold:
                # ACCEPT
                apply_model(...)
            else:
                # REJECT all compounds in group as outliers
                for _, row in prefix_group.iterrows():
                    row_dict = row.to_dict()
                    row_dict["outlier_reason"] = f"Rule 1: Low R² = {r2_for_threshold:.3f}"
                    outliers.append(row_dict)
```

**After** (new logic):
```python
def _apply_rule1_prefix_regression(self, df):
    valid_compounds = []
    outliers = []
    regression_results = {}
    fallback_compounds = []  # NEW: Track compounds for fallback

    for prefix in prefixes:
        anchor_compounds = prefix_group[prefix_group["Anchor"] == "T"]
        n_anchors = len(anchor_compounds)

        if n_anchors >= 4:
            # Sufficient samples - try prefix-specific regression
            # ... existing regression code ...

            validation_r2 = self._cross_validate_regression(X, y)
            r2_for_threshold = validation_r2 if validation_r2 is not None else training_r2

            if r2_for_threshold >= self.r2_threshold:
                # ACCEPT prefix-specific model
                apply_model(...)
            else:
                # Prefix model failed → route to fallback
                print(f"   ⚠️  {prefix}: Validation R² too low ({r2_for_threshold:.3f}), routing to fallback")
                fallback_compounds.extend(prefix_group.to_dict('records'))

        elif n_anchors == 3:
            # NEW: Skip prefix-specific, route directly to fallback
            print(f"   🔄 {prefix}: n=3 anchors, routing to overall regression fallback")
            fallback_compounds.extend(prefix_group.to_dict('records'))

        elif n_anchors >= 2:
            # Keep existing logic for n=2 (may overfit, but try it)
            # ... existing code ...

        else:
            # n < 2: insufficient anchors
            for _, row in prefix_group.iterrows():
                row_dict = row.to_dict()
                row_dict["outlier_reason"] = "Rule 1: Insufficient anchor compounds"
                outliers.append(row_dict)
```

---

### Change #2: Apply Overall Regression to Fallback Compounds

**Location**: After the prefix loop, before returning results

**Before** (current fallback logic):
```python
# Fallback: If no regression groups were formed, try overall regression
if len(regression_results) == 0:
    print("   📊 Fallback: Attempting overall regression...")
    # ... apply to ALL compounds in df ...
```

**After** (improved fallback logic):
```python
# Apply overall regression to fallback compounds
if fallback_compounds or len(regression_results) == 0:
    print(f"   📊 Overall Regression Fallback:")
    print(f"      Compounds routed to fallback: {len(fallback_compounds)}")

    # Get all anchor compounds across ALL groups
    all_anchors = df[df["Anchor"] == "T"]

    if len(all_anchors) >= 3:
        try:
            # Overall regression with all anchors
            X_overall = all_anchors[["Log P"]].values
            y_overall = all_anchors["RT"].values

            if len(np.unique(X_overall)) >= 2:
                model_overall = Ridge(alpha=1.0)
                model_overall.fit(X_overall, y_overall)
                y_pred_overall = model_overall.predict(X_overall)
                training_r2_overall = r2_score(y_overall, y_pred_overall)

                # Cross-validate overall model
                validation_r2_overall = self._cross_validate_regression(X_overall, y_overall)
                r2_overall = validation_r2_overall if validation_r2_overall is not None else training_r2_overall

                print(f"      Overall model R²: {r2_overall:.3f} (validation)")
                print(f"      Using {len(all_anchors)} anchor compounds")

                if r2_overall >= 0.50:  # Relaxed threshold for overall model
                    # Apply overall model to fallback compounds
                    fallback_df = pd.DataFrame(fallback_compounds)

                    X_fallback = fallback_df[["Log P"]].values
                    y_pred_fallback = model_overall.predict(X_fallback)
                    residuals_fallback = fallback_df["RT"].values - y_pred_fallback

                    # Calculate residual statistics using ALL predictions
                    all_X = df[["Log P"]].values
                    all_pred = model_overall.predict(all_X)
                    all_residuals = df["RT"].values - all_pred
                    residual_std = np.std(all_residuals) if np.std(all_residuals) > 0 else 1.0

                    # Store overall regression results
                    regression_results["Overall_Fallback"] = {
                        "slope": float(model_overall.coef_[0]),
                        "intercept": float(model_overall.intercept_),
                        "r2": float(training_r2_overall),
                        "training_r2": float(training_r2_overall),
                        "validation_r2": float(validation_r2_overall) if validation_r2_overall is not None else None,
                        "r2_used_for_threshold": float(r2_overall),
                        "n_samples": len(all_anchors),
                        "n_fallback_compounds": len(fallback_compounds),
                        "equation": f"RT = {model_overall.coef_[0]:.4f} * Log P + {model_overall.intercept_:.4f}",
                        "durbin_watson": self._durbin_watson_test(all_residuals),
                        "p_value": self._calculate_p_value(training_r2_overall, len(all_anchors))
                    }

                    # Classify fallback compounds
                    for idx, compound in enumerate(fallback_compounds):
                        compound["predicted_rt"] = float(y_pred_fallback[idx])
                        compound["residual"] = float(residuals_fallback[idx])
                        compound["std_residual"] = float(residuals_fallback[idx] / residual_std)
                        compound["model_used"] = "Overall_Fallback"

                        if abs(compound["std_residual"]) < self.outlier_threshold:
                            valid_compounds.append(compound)
                        else:
                            compound["outlier_reason"] = f"Rule 1 (Fallback): Std residual = {compound['std_residual']:.3f}"
                            outliers.append(compound)

                    print(f"      ✅ Fallback succeeded: {len([c for c in fallback_compounds if abs(c['std_residual']) < self.outlier_threshold])} valid, {len([c for c in fallback_compounds if abs(c['std_residual']) >= self.outlier_threshold])} outliers")

                else:
                    # Overall model R² too low
                    print(f"      ❌ Overall model R² too low ({r2_overall:.3f} < 0.50)")
                    for compound in fallback_compounds:
                        compound["outlier_reason"] = f"Rule 1 (Fallback): Overall R² too low ({r2_overall:.3f})"
                        outliers.append(compound)

        except Exception as e:
            print(f"   ❌ Fallback regression failed: {str(e)}")
            for compound in fallback_compounds:
                compound["outlier_reason"] = "Rule 1 (Fallback): Regression error"
                outliers.append(compound)
    else:
        # Not enough anchors for overall regression
        print(f"   ❌ Insufficient anchors for overall regression (n={len(all_anchors)})")
        for compound in fallback_compounds:
            compound["outlier_reason"] = "Rule 1 (Fallback): Insufficient total anchors"
            outliers.append(compound)
```

---

### Change #3: Update Statistics Reporting

**Location**: End of `_apply_rule1_prefix_regression()` method

**Add**:
```python
# Print summary
print(f"\n   📊 Rule 1 Summary:")
print(f"      Prefix-specific models: {len([k for k in regression_results.keys() if k != 'Overall_Fallback'])}")
print(f"      Overall fallback used: {'Yes' if 'Overall_Fallback' in regression_results else 'No'}")
if 'Overall_Fallback' in regression_results:
    n_fallback = regression_results['Overall_Fallback']['n_fallback_compounds']
    print(f"      Compounds via fallback: {n_fallback}")
print(f"      Total valid: {len(valid_compounds)}")
print(f"      Total outliers: {len(outliers)}")
```

---

## 🧪 Testing

### Test Script

Create `test_hierarchical_fallback.py`:

```python
#!/usr/bin/env python3
"""
Test hierarchical fallback implementation
"""

import pandas as pd
from apps.analysis.services.ganglioside_processor import GangliosideProcessor

def test_n3_fallback():
    """Test that n=3 groups use fallback instead of being rejected"""

    # Load test data
    df = pd.read_csv('/path/to/testwork_user.csv')

    print("=" * 80)
    print("HIERARCHICAL FALLBACK TEST")
    print("=" * 80)
    print()

    # Run analysis
    processor = GangliosideProcessor()
    results = processor.process_data(df, 'porcine')

    # Check regression results
    regression = results['regression_analysis']

    print("📊 Regression Models:")
    for prefix, data in regression.items():
        print(f"\n   {prefix}:")
        print(f"      Samples: {data['n_samples']}")
        print(f"      R²: {data['r2']:.3f}")
        print(f"      Validation R²: {data.get('validation_r2', 'N/A')}")

        if prefix == "Overall_Fallback":
            print(f"      Fallback compounds: {data.get('n_fallback_compounds', 0)}")

    # Analyze outcomes for n=3 groups
    print("\n📈 n=3 Group Outcomes:")

    n3_groups = ["GD1+HexNAc", "GD1+dHex", "GD3", "GT1"]
    for group in n3_groups:
        # Count compounds in this group
        group_compounds = df[df['Name'].str.startswith(group)]
        n_total = len(group_compounds)

        # Count valid vs outliers
        valid = results['valid_compounds']
        outliers = results['outliers']

        n_valid = len([c for c in valid if c['Name'].startswith(group)])
        n_outliers = len([c for c in outliers if c['Name'].startswith(group)])

        print(f"\n   {group}:")
        print(f"      Total compounds: {n_total}")
        print(f"      Valid: {n_valid}")
        print(f"      Outliers: {n_outliers}")
        print(f"      Success rate: {n_valid/n_total*100:.1f}%")

    # Overall statistics
    stats = results['statistics']
    print(f"\n📊 Overall Statistics:")
    print(f"   Success rate: {stats['success_rate']:.1f}%")
    print(f"   Valid compounds: {stats['valid_compounds']}")
    print(f"   Outliers: {stats['outliers']}")

    # Expected outcome: n=3 groups should use fallback, not be rejected
    assert "Overall_Fallback" in regression, "Overall fallback model should be present"
    assert regression["Overall_Fallback"]["n_fallback_compounds"] > 0, "Fallback should process compounds"

    print("\n✅ Hierarchical fallback test PASSED")

if __name__ == '__main__':
    test_n3_fallback()
```

### Running the Test

```bash
# Docker
docker-compose exec django python test_hierarchical_fallback.py

# Local
python test_hierarchical_fallback.py
```

---

## 📊 Expected Results

### Before Implementation

```
Rule 1 Results:
   GD1 (n=23): ✅ ACCEPT (prefix-specific)
   GM1 (n=4): ✅ ACCEPT (prefix-specific)
   GD1+HexNAc (n=3): ❌ REJECT (low validation R²)
   GD1+dHex (n=3): ❌ REJECT (low validation R²)
   GD3 (n=3): ❌ REJECT (low validation R²)
   GT1 (n=3): ❌ REJECT (low validation R²)

Success rate: ~60% (many compounds lost)
```

### After Implementation

```
Rule 1 Results:
   GD1 (n=23): ✅ ACCEPT (prefix-specific)
   GM1 (n=4): ✅ ACCEPT (prefix-specific)
   GD1+HexNAc (n=3): 🔄 FALLBACK (overall regression)
   GD1+dHex (n=3): 🔄 FALLBACK (overall regression)
   GD3 (n=3): 🔄 FALLBACK (overall regression)
   GT1 (n=3): 🔄 FALLBACK (overall regression)

Overall_Fallback model:
   - Uses all 49 anchor compounds
   - Validation R²: ~0.65 (expected)
   - Processes ~150 compounds from n=3 groups

Success rate: ~75-80% (+15-20 percentage points)
```

---

## 🚀 Deployment Steps

### Step 1: Backup Current Code
```bash
cd django_ganglioside/apps/analysis/services/
cp ganglioside_processor.py ganglioside_processor.py.backup
```

### Step 2: Apply Code Changes
- Implement Change #1 (track fallback compounds)
- Implement Change #2 (apply overall regression)
- Implement Change #3 (update reporting)

### Step 3: Test with Real Data
```bash
python test_hierarchical_fallback.py
```

### Step 4: Validate Results
- Check that n=3 groups use fallback (not rejected)
- Verify overall model has validation R² ≥ 0.50
- Confirm success rate increased by 10-20%

### Step 5: Deploy to Production
```bash
# Docker deployment
docker-compose build django
docker-compose up -d

# Check logs
docker-compose logs -f django
```

### Step 6: Monitor
- Track success rates across datasets
- Monitor validation vs training R² for overall model
- Collect user feedback

---

## 🔄 Rollback Procedure

If issues occur:

```bash
cd django_ganglioside/apps/analysis/services/
cp ganglioside_processor.py.backup ganglioside_processor.py

# Restart services
docker-compose restart django
```

---

## 📈 Success Metrics

Track these metrics before/after:

1. **Success Rate**: % of compounds passing all rules
   - Before: ~60%
   - After: ~75-80%
   - Target: +10-20 percentage points

2. **Rejection Rate (Rule 1)**: % of compounds rejected in Rule 1
   - Before: ~40%
   - After: ~10-15%
   - Target: <20%

3. **Fallback Usage**: Number of compounds using overall regression
   - Before: 0-10 (only when no groups form)
   - After: 100-200 (includes all n=3 groups)
   - Target: Cover all n=3 compounds

4. **Overall Model Quality**: Validation R² of fallback model
   - Target: ≥ 0.50
   - Ideal: ≥ 0.60

---

## 💡 Next Steps After Deployment

Once hierarchical fallback is working:

1. **Collect Data**: Monitor success rates for 1 week
2. **Analyze Patterns**: Which compounds still fail? Why?
3. **Consider Phase 2**: Implement prefix pooling (GD family)
4. **Document Learnings**: Update user documentation

---

**Status**: ⏳ READY TO IMPLEMENT
**Priority**: 🔴 HIGH (addresses 67% false positive rate)
**Confidence**: 🟢 HIGH (simple, low-risk change)
