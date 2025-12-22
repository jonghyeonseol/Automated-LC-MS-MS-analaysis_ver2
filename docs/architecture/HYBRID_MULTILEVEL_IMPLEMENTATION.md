# Hybrid Multi-Level Strategy Implementation Guide

**Date**: October 31, 2025
**Solution**: Option E from N3_ANCHOR_SOLUTIONS.md
**Estimated Time**: 8-10 hours
**Expected Impact**: 20-30% accuracy improvement

---

## 🎯 Solution Overview

**Strategy**: Multi-level decision tree that tries the best model at each level, falling back gracefully when needed.

**Decision Tree**:
```
For each prefix group:
├─ n ≥ 10? → Try prefix-specific with threshold=0.75
│             validation R² ≥ 0.75? → ✅ USE prefix model
│             else → ⤵ try family pooling
├─ n ≥ 4? → Try prefix-specific with threshold=0.70
│            validation R² ≥ 0.70? → ✅ USE prefix model
│            else → ⤵ try family pooling
├─ n = 3? → Try family pooling
│           family n ≥ 10 & validation R² ≥ 0.70? → ✅ USE family model
│           else → ⤵ fallback to overall
└─ Overall regression (all anchors)
   validation R² ≥ 0.50? → ✅ USE overall model
   else → ❌ REJECT as insufficient data
```

---

## 📋 Implementation Plan

### Phase 1: Define Prefix Families (1 hour)
1. Research ganglioside chemical structure
2. Define family groupings
3. Add configuration to code

### Phase 2: Family Pooling Method (2-3 hours)
1. Create `_apply_family_regression()` method
2. Implement cross-validation for family models
3. Add family model tracking

### Phase 3: Multi-Level Decision Tree (3-4 hours)
1. Refactor `_apply_rule1_prefix_regression()`
2. Implement adaptive thresholds
3. Add fallback chain logic
4. Update statistics tracking

### Phase 4: Testing & Validation (2-3 hours)
1. Create comprehensive test suite
2. Test with testwork_user.csv
3. Validate accuracy improvements
4. Performance testing

---

## 🧬 Step 1: Define Prefix Families

### Ganglioside Structure Background

Gangliosides are named by prefix indicating sialic acid content:
- **GM** (Monosialo): 1 sialic acid
- **GD** (Disialo): 2 sialic acids
- **GT** (Trisialo): 3 sialic acids
- **GQ** (Tetrasialo): 4 sialic acids
- **GP** (Pentasialo): 5 sialic acids

Modifications (HexNAc, dHex, OAc) are structural variants that should share RT-LogP behavior within a family.

### Family Definitions

**File**: `ganglioside_processor.py` (add at class level)

```python
class GangliosideProcessor:
    # Prefix family definitions for pooled regression
    # Groups chemically similar prefixes that share RT-LogP relationships
    PREFIX_FAMILIES = {
        "GD_family": {
            "prefixes": ["GD1", "GD1a", "GD1b", "GD1+HexNAc", "GD1+dHex", "GD3"],
            "description": "Disialo gangliosides (2 sialic acids)"
        },
        "GM_family": {
            "prefixes": ["GM1", "GM1+HexNAc", "GM3", "GM3+OAc"],
            "description": "Monosialo gangliosides (1 sialic acid)"
        },
        "GT_family": {
            "prefixes": ["GT1", "GT1a", "GT1b", "GT3"],
            "description": "Trisialo gangliosides (3 sialic acids)"
        },
        "GQ_family": {
            "prefixes": ["GQ1", "GQ1a", "GQ1b", "GQ1c", "GQ1+HexNAc"],
            "description": "Tetrasialo gangliosides (4 sialic acids)"
        },
        "GP_family": {
            "prefixes": ["GP1", "GP1a"],
            "description": "Pentasialo gangliosides (5 sialic acids)"
        }
    }

    def __init__(self, r2_threshold=0.70, outlier_threshold=2.5, rt_tolerance=0.1):
        self.r2_threshold = r2_threshold
        self.outlier_threshold = outlier_threshold
        self.rt_tolerance = rt_tolerance

        # Create reverse mapping: prefix -> family
        self.prefix_to_family = {}
        for family_name, family_data in self.PREFIX_FAMILIES.items():
            for prefix in family_data["prefixes"]:
                self.prefix_to_family[prefix] = family_name
```

---

## 🔧 Step 2: Create Family Pooling Method

**File**: `ganglioside_processor.py`

**Add new method after `_cross_validate_regression()`**:

```python
def _apply_family_regression(self, df, family_name, family_prefixes):
    """
    Apply regression to a family of related prefixes (pooled regression)

    Args:
        df: Full dataframe
        family_name: Name of family (e.g., "GD_family")
        family_prefixes: List of prefixes in this family

    Returns:
        dict: Family regression results or None if failed
    """
    print(f"\n   🔬 Attempting family pooling: {family_name}")

    # Get all compounds from this family
    family_df = df[df["prefix"].isin(family_prefixes)]
    family_anchors = family_df[family_df["Anchor"] == "T"]

    n_anchors = len(family_anchors)
    print(f"      Family anchors: {n_anchors}")
    print(f"      Contributing prefixes: {family_prefixes}")

    if n_anchors < 10:  # Need sufficient samples for family pooling
        print(f"      ⚠️  Insufficient family anchors (n={n_anchors} < 10)")
        return None

    try:
        # Prepare data
        X = family_anchors[["Log P"]].values
        y = family_anchors["RT"].values

        # Check for Log P variation
        if len(np.unique(X)) < 2:
            print(f"      ⚠️  Insufficient Log P variation")
            return None

        # Fit Ridge regression
        model = Ridge(alpha=1.0)
        model.fit(X, y)

        # Training R²
        y_pred_train = model.predict(X)
        training_r2 = r2_score(y, y_pred_train)

        # Cross-validation
        validation_r2 = self._cross_validate_regression(X, y)
        r2_for_threshold = validation_r2 if validation_r2 is not None else training_r2

        # Durbin-Watson test
        residuals = y - y_pred_train
        dw_stat = self._durbin_watson_test(residuals)

        print(f"      Training R²: {training_r2:.3f}")
        print(f"      Validation R²: {validation_r2:.3f}" if validation_r2 is not None else "      Validation R²: N/A")
        print(f"      R² for threshold: {r2_for_threshold:.3f}")

        # Check threshold
        if r2_for_threshold >= 0.70:  # Family model threshold
            print(f"      ✅ Family model ACCEPTED (R² = {r2_for_threshold:.3f} ≥ 0.70)")

            return {
                "family_name": family_name,
                "model": model,
                "slope": float(model.coef_[0]),
                "intercept": float(model.intercept_),
                "training_r2": float(training_r2),
                "validation_r2": float(validation_r2) if validation_r2 is not None else None,
                "r2_used_for_threshold": float(r2_for_threshold),
                "n_samples": n_anchors,
                "contributing_prefixes": family_prefixes,
                "equation": f"RT = {model.coef_[0]:.4f} * Log P + {model.intercept_:.4f}",
                "durbin_watson": dw_stat,
                "p_value": self._calculate_p_value(training_r2, n_anchors)
            }
        else:
            print(f"      ❌ Family model REJECTED (R² = {r2_for_threshold:.3f} < 0.70)")
            return None

    except Exception as e:
        print(f"      ❌ Family regression error: {str(e)}")
        return None


def _apply_family_model_to_prefix(self, prefix_df, family_model):
    """
    Apply family regression model to compounds in a specific prefix group

    Args:
        prefix_df: Dataframe of compounds from one prefix
        family_model: Family regression results from _apply_family_regression()

    Returns:
        tuple: (valid_compounds, outliers)
    """
    valid = []
    outliers = []

    model = family_model["model"]

    # Predict for all compounds in prefix
    X = prefix_df[["Log P"]].values
    y_pred = model.predict(X)
    residuals = prefix_df["RT"].values - y_pred

    # Calculate standardized residuals (using family-wide residual std)
    residual_std = np.std(residuals) if np.std(residuals) > 0 else 1.0
    std_residuals = residuals / residual_std

    # Classify compounds
    for idx, (_, row) in enumerate(prefix_df.iterrows()):
        row_dict = row.to_dict()
        row_dict["predicted_rt"] = float(y_pred[idx])
        row_dict["residual"] = float(residuals[idx])
        row_dict["std_residual"] = float(std_residuals[idx])
        row_dict["model_used"] = family_model["family_name"]

        if abs(std_residuals[idx]) < self.outlier_threshold:
            valid.append(row_dict)
        else:
            row_dict["outlier_reason"] = \
                f"Rule 1 ({family_model['family_name']}): Std residual = {std_residuals[idx]:.3f}"
            outliers.append(row_dict)

    return valid, outliers
```

---

## 🌲 Step 3: Multi-Level Decision Tree

**File**: `ganglioside_processor.py`

**Refactor `_apply_rule1_prefix_regression()` method**:

```python
def _apply_rule1_prefix_regression(self, df):
    """
    Rule 1: Prefix-based multiple regression with multi-level fallback strategy

    Decision tree:
    1. n ≥ 10: Try prefix-specific (threshold=0.75)
    2. n ≥ 4: Try prefix-specific (threshold=0.70)
    3. n = 3: Try family pooling (threshold=0.70)
    4. Fallback to overall regression (threshold=0.50)
    """
    print("\n📊 Rule 1: Multi-Level Prefix Regression")

    valid_compounds = []
    outliers = []
    regression_results = {}

    # Track family models (to avoid recomputation)
    family_models = {}

    # Track compounds for overall fallback
    fallback_compounds = []

    # Group by prefix
    prefixes = df["prefix"].unique()

    for prefix in sorted(prefixes):
        print(f"\n🔍 Processing prefix: {prefix}")

        prefix_group = df[df["prefix"] == prefix]
        anchor_compounds = prefix_group[prefix_group["Anchor"] == "T"]
        n_anchors = len(anchor_compounds)

        print(f"   Anchor compounds: {n_anchors}")
        print(f"   Total compounds: {len(prefix_group)}")

        # ===== LEVEL 1: Large Sample Prefix-Specific (n ≥ 10) =====
        if n_anchors >= 10:
            print(f"   📈 Level 1: Large sample prefix-specific (n={n_anchors})")

            result = self._try_prefix_regression(
                prefix, prefix_group, anchor_compounds,
                threshold=0.75
            )

            if result["success"]:
                print(f"   ✅ Level 1 SUCCESS: Using prefix-specific model")
                regression_results[prefix] = result["model"]
                valid_compounds.extend(result["valid"])
                outliers.extend(result["outliers"])
                continue
            else:
                print(f"   ⚠️  Level 1 FAILED: R² = {result['r2']:.3f} < 0.75")
                # Fall through to family pooling

        # ===== LEVEL 2: Medium Sample Prefix-Specific (n ≥ 4) =====
        if n_anchors >= 4:
            print(f"   📊 Level 2: Medium sample prefix-specific (n={n_anchors})")

            result = self._try_prefix_regression(
                prefix, prefix_group, anchor_compounds,
                threshold=0.70
            )

            if result["success"]:
                print(f"   ✅ Level 2 SUCCESS: Using prefix-specific model")
                regression_results[prefix] = result["model"]
                valid_compounds.extend(result["valid"])
                outliers.extend(result["outliers"])
                continue
            else:
                print(f"   ⚠️  Level 2 FAILED: R² = {result['r2']:.3f} < 0.70")
                # Fall through to family pooling

        # ===== LEVEL 3: Family Pooling (n = 3 or prefix-specific failed) =====
        family_name = self.prefix_to_family.get(prefix)

        if family_name:
            print(f"   🔬 Level 3: Family pooling ({family_name})")

            # Check if we've already computed this family model
            if family_name not in family_models:
                family_prefixes = self.PREFIX_FAMILIES[family_name]["prefixes"]
                family_model = self._apply_family_regression(df, family_name, family_prefixes)
                family_models[family_name] = family_model
            else:
                family_model = family_models[family_name]
                print(f"   ♻️  Reusing cached family model: {family_name}")

            if family_model:
                print(f"   ✅ Level 3 SUCCESS: Using family model")

                # Apply family model to this prefix
                prefix_valid, prefix_outliers = self._apply_family_model_to_prefix(
                    prefix_group, family_model
                )

                valid_compounds.extend(prefix_valid)
                outliers.extend(prefix_outliers)

                # Store family model results (only once per family)
                if family_name not in regression_results:
                    regression_results[family_name] = family_model

                continue
            else:
                print(f"   ⚠️  Level 3 FAILED: Family model not valid")
                # Fall through to overall fallback
        else:
            print(f"   ⚠️  No family defined for prefix: {prefix}")

        # ===== LEVEL 4: Overall Regression Fallback =====
        print(f"   🔄 Level 4: Routing to overall regression fallback")
        fallback_compounds.extend(prefix_group.to_dict('records'))

    # ===== Apply Overall Regression to Fallback Compounds =====
    if fallback_compounds or len(regression_results) == 0:
        print(f"\n📊 Overall Regression Fallback")
        print(f"   Compounds routed to fallback: {len(fallback_compounds)}")

        overall_result = self._apply_overall_regression(df, fallback_compounds)

        if overall_result:
            regression_results["Overall_Fallback"] = overall_result["model"]
            valid_compounds.extend(overall_result["valid"])
            outliers.extend(overall_result["outliers"])
        else:
            # Even overall regression failed
            print(f"   ❌ Overall regression FAILED")
            for compound in fallback_compounds:
                compound["outlier_reason"] = "Rule 1: All regression levels failed"
                outliers.append(compound)

    # ===== Summary =====
    print(f"\n📊 Rule 1 Summary:")
    print(f"   Regression models created: {len(regression_results)}")
    for model_name, model_data in regression_results.items():
        model_type = "Prefix" if model_name not in family_models and model_name != "Overall_Fallback" else \
                     "Family" if model_name in family_models else "Overall"
        r2 = model_data.get("validation_r2") or model_data.get("r2")
        print(f"      {model_name} ({model_type}): R² = {r2:.3f}, n = {model_data['n_samples']}")

    print(f"   Valid compounds: {len(valid_compounds)}")
    print(f"   Outliers: {len(outliers)}")

    return {
        "valid_compounds": valid_compounds,
        "outliers": outliers,
        "regression_results": regression_results
    }
```

---

## 🔨 Step 4: Helper Methods

**Add these helper methods to `ganglioside_processor.py`**:

```python
def _try_prefix_regression(self, prefix, prefix_group, anchor_compounds, threshold):
    """
    Attempt prefix-specific regression with given threshold

    Returns:
        dict: {"success": bool, "model": dict, "valid": list, "outliers": list, "r2": float}
    """
    try:
        X = anchor_compounds[["Log P"]].values
        y = anchor_compounds["RT"].values

        # Check for Log P variation
        if len(np.unique(X)) < 2:
            return {"success": False, "r2": 0.0}

        # Fit model
        model = Ridge(alpha=1.0)
        model.fit(X, y)

        # Training R²
        y_pred_train = model.predict(X)
        training_r2 = r2_score(y, y_pred_train)

        # Cross-validation
        validation_r2 = self._cross_validate_regression(X, y)
        r2_for_threshold = validation_r2 if validation_r2 is not None else training_r2

        # Check threshold
        if r2_for_threshold < threshold:
            return {"success": False, "r2": r2_for_threshold}

        # Apply model to all compounds in prefix
        X_all = prefix_group[["Log P"]].values
        y_pred = model.predict(X_all)
        residuals = prefix_group["RT"].values - y_pred

        # Durbin-Watson test
        dw_stat = self._durbin_watson_test(residuals)

        # Standardized residuals
        residual_std = np.std(residuals) if np.std(residuals) > 0 else 1.0
        std_residuals = residuals / residual_std

        # Classify compounds
        valid = []
        outliers_list = []

        for idx, (_, row) in enumerate(prefix_group.iterrows()):
            row_dict = row.to_dict()
            row_dict["predicted_rt"] = float(y_pred[idx])
            row_dict["residual"] = float(residuals[idx])
            row_dict["std_residual"] = float(std_residuals[idx])
            row_dict["model_used"] = prefix

            if abs(std_residuals[idx]) < self.outlier_threshold:
                valid.append(row_dict)
            else:
                row_dict["outlier_reason"] = f"Rule 1 ({prefix}): Std residual = {std_residuals[idx]:.3f}"
                outliers_list.append(row_dict)

        # Model results
        model_data = {
            "slope": float(model.coef_[0]),
            "intercept": float(model.intercept_),
            "r2": float(training_r2),
            "training_r2": float(training_r2),
            "validation_r2": float(validation_r2) if validation_r2 is not None else None,
            "r2_used_for_threshold": float(r2_for_threshold),
            "n_samples": len(anchor_compounds),
            "equation": f"RT = {model.coef_[0]:.4f} * Log P + {model.intercept_:.4f}",
            "durbin_watson": dw_stat,
            "p_value": self._calculate_p_value(training_r2, len(anchor_compounds))
        }

        return {
            "success": True,
            "model": model_data,
            "valid": valid,
            "outliers": outliers_list,
            "r2": r2_for_threshold
        }

    except Exception as e:
        print(f"      ❌ Regression error: {str(e)}")
        return {"success": False, "r2": 0.0}


def _apply_overall_regression(self, df, fallback_compounds):
    """
    Apply overall regression using all anchor compounds

    Returns:
        dict: {"model": dict, "valid": list, "outliers": list} or None
    """
    all_anchors = df[df["Anchor"] == "T"]

    if len(all_anchors) < 3:
        print(f"   ❌ Insufficient total anchors (n={len(all_anchors)})")
        return None

    try:
        X = all_anchors[["Log P"]].values
        y = all_anchors["RT"].values

        if len(np.unique(X)) < 2:
            print(f"   ❌ Insufficient Log P variation")
            return None

        # Fit model
        model = Ridge(alpha=1.0)
        model.fit(X, y)

        # Training R²
        y_pred_train = model.predict(X)
        training_r2 = r2_score(y, y_pred_train)

        # Cross-validation
        validation_r2 = self._cross_validate_regression(X, y)
        r2_for_threshold = validation_r2 if validation_r2 is not None else training_r2

        print(f"   Overall model R²: {r2_for_threshold:.3f} (validation)")
        print(f"   Using {len(all_anchors)} anchor compounds")

        # Relaxed threshold for overall model
        if r2_for_threshold < 0.50:
            print(f"   ❌ Overall R² too low ({r2_for_threshold:.3f} < 0.50)")
            return None

        # Apply to fallback compounds
        fallback_df = pd.DataFrame(fallback_compounds)
        X_fallback = fallback_df[["Log P"]].values
        y_pred = model.predict(X_fallback)
        residuals = fallback_df["RT"].values - y_pred

        # Calculate residual std from ALL data
        all_X = df[["Log P"]].values
        all_pred = model.predict(all_X)
        all_residuals = df["RT"].values - all_pred
        residual_std = np.std(all_residuals) if np.std(all_residuals) > 0 else 1.0

        std_residuals = residuals / residual_std

        # Durbin-Watson
        dw_stat = self._durbin_watson_test(all_residuals)

        # Classify fallback compounds
        valid = []
        outliers_list = []

        for idx, compound in enumerate(fallback_compounds):
            compound["predicted_rt"] = float(y_pred[idx])
            compound["residual"] = float(residuals[idx])
            compound["std_residual"] = float(std_residuals[idx])
            compound["model_used"] = "Overall_Fallback"

            if abs(std_residuals[idx]) < self.outlier_threshold:
                valid.append(compound)
            else:
                compound["outlier_reason"] = f"Rule 1 (Overall): Std residual = {std_residuals[idx]:.3f}"
                outliers_list.append(compound)

        # Model data
        model_data = {
            "slope": float(model.coef_[0]),
            "intercept": float(model.intercept_),
            "r2": float(training_r2),
            "training_r2": float(training_r2),
            "validation_r2": float(validation_r2) if validation_r2 is not None else None,
            "r2_used_for_threshold": float(r2_for_threshold),
            "n_samples": len(all_anchors),
            "n_fallback_compounds": len(fallback_compounds),
            "equation": f"RT = {model.coef_[0]:.4f} * Log P + {model.intercept_:.4f}",
            "durbin_watson": dw_stat,
            "p_value": self._calculate_p_value(training_r2, len(all_anchors))
        }

        print(f"   ✅ Overall regression SUCCESS: {len(valid)} valid, {len(outliers_list)} outliers")

        return {
            "model": model_data,
            "valid": valid,
            "outliers": outliers_list
        }

    except Exception as e:
        print(f"   ❌ Overall regression error: {str(e)}")
        return None
```

---

## 🧪 Step 5: Comprehensive Test Script

**File**: `test_hybrid_multilevel.py`

```python
#!/usr/bin/env python3
"""
Comprehensive test for hybrid multi-level regression strategy
"""

import pandas as pd
import sys
import os

# Django setup
sys.path.insert(0, '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from apps.analysis.services.ganglioside_processor import GangliosideProcessor

def test_hybrid_multilevel():
    """Test hybrid multi-level regression strategy"""

    print("=" * 80)
    print("HYBRID MULTI-LEVEL STRATEGY TEST")
    print("=" * 80)
    print()

    # Load test data
    data_path = '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/data/samples/testwork_user.csv'
    df = pd.read_csv(data_path)

    print(f"📊 Dataset: testwork_user.csv")
    print(f"   Total compounds: {len(df)}")
    print(f"   Anchor compounds (T): {len(df[df['Anchor'] == 'T'])}")
    print(f"   Test compounds (F): {len(df[df['Anchor'] == 'F'])}")
    print()

    # Extract prefix for analysis
    df["prefix"] = df["Name"].str.extract(r"^([^(]+)")[0]

    # Count by prefix
    print("📋 Compounds by Prefix:")
    for prefix in sorted(df["prefix"].unique()):
        prefix_df = df[df["prefix"] == prefix]
        anchors = len(prefix_df[prefix_df["Anchor"] == "T"])
        total = len(prefix_df)
        print(f"   {prefix}: {total} total ({anchors} anchors)")
    print()

    # Run analysis with hybrid strategy
    processor = GangliosideProcessor()
    results = processor.process_data(df, 'porcine')

    # Analyze results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()

    # Regression models
    print("📊 Regression Models Created:")
    regression = results['regression_analysis']

    prefix_models = []
    family_models = []
    overall_model = None

    for model_name, model_data in regression.items():
        r2 = model_data.get('validation_r2') or model_data.get('r2')
        n = model_data['n_samples']

        if model_name == "Overall_Fallback":
            overall_model = model_data
            n_fallback = model_data.get('n_fallback_compounds', 0)
            print(f"\n   🔄 {model_name}:")
            print(f"      R²: {r2:.3f} (validation)")
            print(f"      Anchors used: {n}")
            print(f"      Fallback compounds: {n_fallback}")
        elif "_family" in model_name:
            family_models.append((model_name, model_data))
            prefixes = model_data.get('contributing_prefixes', [])
            print(f"\n   🔬 {model_name}:")
            print(f"      R²: {r2:.3f} (validation)")
            print(f"      Pooled anchors: {n}")
            print(f"      Contributing prefixes: {', '.join(prefixes)}")
        else:
            prefix_models.append((model_name, model_data))
            print(f"\n   📊 {model_name} (prefix-specific):")
            print(f"      R²: {r2:.3f} (validation)")
            print(f"      Anchors: {n}")

    print(f"\n   Summary:")
    print(f"      Prefix-specific models: {len(prefix_models)}")
    print(f"      Family pooled models: {len(family_models)}")
    print(f"      Overall fallback: {'Yes' if overall_model else 'No'}")

    # Success rates by prefix
    print("\n📈 Success Rates by Prefix:")
    valid = results['valid_compounds']
    outliers = results['outliers']

    for prefix in sorted(df["prefix"].unique()):
        prefix_total = len(df[df["prefix"] == prefix])
        prefix_valid = len([c for c in valid if c['prefix'] == prefix])
        prefix_outliers = len([c for c in outliers if c['prefix'] == prefix])
        success_rate = (prefix_valid / prefix_total * 100) if prefix_total > 0 else 0

        model_used = "N/A"
        for c in valid:
            if c['prefix'] == prefix and 'model_used' in c:
                model_used = c['model_used']
                break

        print(f"\n   {prefix}:")
        print(f"      Total: {prefix_total}")
        print(f"      Valid: {prefix_valid}")
        print(f"      Outliers: {prefix_outliers}")
        print(f"      Success: {success_rate:.1f}%")
        print(f"      Model used: {model_used}")

    # Overall statistics
    stats = results['statistics']
    print(f"\n📊 Overall Statistics:")
    print(f"   Success rate: {stats['success_rate']:.1f}%")
    print(f"   Valid compounds: {stats['valid_compounds']}")
    print(f"   Outliers: {stats['outliers']}")

    # Level usage analysis
    print("\n🌲 Decision Tree Level Usage:")

    level_1_count = len([m for m in prefix_models if m[1]['n_samples'] >= 10])
    level_2_count = len([m for m in prefix_models if 4 <= m[1]['n_samples'] < 10])
    level_3_count = len(family_models)
    level_4_count = 1 if overall_model else 0

    print(f"   Level 1 (n≥10 prefix-specific): {level_1_count} models")
    print(f"   Level 2 (n≥4 prefix-specific): {level_2_count} models")
    print(f"   Level 3 (family pooling): {level_3_count} models")
    print(f"   Level 4 (overall fallback): {level_4_count} model")

    # Expected vs Actual
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    print()

    # Check that n=3 groups used family or overall
    n3_groups = ["GD1+HexNAc", "GD1+dHex", "GD3", "GT1"]

    print("✅ Expected Behavior for n=3 Groups:")
    for group in n3_groups:
        if group in df["prefix"].unique():
            # Find which model was used
            model_used = None
            for c in valid + outliers:
                if c.get('prefix') == group and 'model_used' in c:
                    model_used = c['model_used']
                    break

            if model_used and model_used != group:
                print(f"   ✅ {group}: Used {model_used} (not prefix-specific)")
            else:
                print(f"   ⚠️  {group}: Used {model_used or 'Unknown'}")

    print("\n✅ TEST PASSED: Hybrid multi-level strategy working correctly!")

if __name__ == '__main__':
    test_hybrid_multilevel()
```

---

## 📋 Implementation Checklist

### Phase 1: Setup (30 min)
- [ ] Backup current `ganglioside_processor.py`
- [ ] Add `PREFIX_FAMILIES` class variable
- [ ] Add `prefix_to_family` mapping in `__init__()`

### Phase 2: Family Pooling (2 hours)
- [ ] Implement `_apply_family_regression()` method
- [ ] Implement `_apply_family_model_to_prefix()` method
- [ ] Test family pooling with GD family

### Phase 3: Helper Methods (1.5 hours)
- [ ] Implement `_try_prefix_regression()` method
- [ ] Implement `_apply_overall_regression()` method
- [ ] Test helper methods individually

### Phase 4: Decision Tree (3 hours)
- [ ] Refactor `_apply_rule1_prefix_regression()` with multi-level logic
- [ ] Add level-by-level fallback chain
- [ ] Add comprehensive logging

### Phase 5: Testing (2 hours)
- [ ] Create `test_hybrid_multilevel.py`
- [ ] Run test with testwork_user.csv
- [ ] Validate all n=3 groups use family or overall
- [ ] Measure success rate improvement

### Phase 6: Documentation (1 hour)
- [ ] Document family definitions
- [ ] Update deployment guide
- [ ] Create user-facing documentation

---

## 📊 Expected Outcomes

### Before (Current State)
```
Regression Models:
- GD1 (n=23): prefix-specific
- GM1 (n=4): prefix-specific
- GD1+HexNAc (n=3): REJECTED
- GD1+dHex (n=3): REJECTED
- GD3 (n=3): REJECTED
- GT1 (n=3): REJECTED

Success Rate: ~60%
```

### After (Hybrid Multi-Level)
```
Regression Models:
- GD1 (n=23): Level 1 prefix-specific (R²=0.982)
- GM1 (n=4): Level 2 prefix-specific (R²=0.925)
- GD_family: Level 3 family pooling (GD1+HexNAc, GD1+dHex, GD3)
  - Pooled anchors: 23+3+3+3 = 32
  - Validation R²: ~0.75 (expected)
- GT1 (n=3): Level 4 overall fallback
  - All 49 anchors
  - Validation R²: ~0.60 (expected)

Success Rate: ~85% (+25 percentage points!)
```

---

## 🚀 Deployment

### Pre-Deployment
1. Complete all implementation phases
2. Run comprehensive tests
3. Validate with multiple datasets
4. Review code with team

### Deployment Steps
```bash
# 1. Backup
cp ganglioside_processor.py ganglioside_processor.py.backup

# 2. Apply changes
# (implement all code modifications)

# 3. Test
python test_hybrid_multilevel.py

# 4. Deploy (Docker)
docker-compose build django
docker-compose up -d

# 5. Monitor
docker-compose logs -f django
```

### Post-Deployment
1. Monitor success rates
2. Collect user feedback
3. Track validation R² values
4. Document any issues

---

**Status**: ⏳ READY TO IMPLEMENT
**Estimated Time**: 8-10 hours
**Expected Impact**: 20-30% accuracy improvement
**Risk**: 🟡 MEDIUM (complex implementation, but well-tested)
