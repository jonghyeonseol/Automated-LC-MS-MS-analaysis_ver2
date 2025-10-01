# Ganglioside Analysis Rules

This module contains individual rule implementations for ganglioside LC-MS/MS data analysis. Each rule is isolated for maintainability and independent testing.

## 📁 Structure

```
backend/rules/
├── __init__.py                      # Module initialization and exports
├── README.md                        # This file
├── rule1_regression.py              # Prefix-based multiple regression
├── rule2_sugar_count.py             # Sugar count calculation
├── rule3_isomer_classification.py   # Structural isomer detection
├── rule4_oacetylation.py            # O-acetylation validation
└── rule5_fragmentation.py           # In-source fragmentation detection
```

## 📊 Rule Overview

### Rule 1: Prefix-based Multiple Regression
**File:** `rule1_regression.py`
**Class:** `Rule1PrefixRegression`

**Purpose:** Groups compounds by prefix and performs multiple regression analysis

**Features used:**
- Log P (lipophilicity)
- Carbon chain length (a_component)
- Unsaturation degree (b_component)
- Oxygen count
- Sugar count
- Sialic acid count
- Modifications (OAc, dHex, HexNAc)

**Output:**
- Valid compounds (within regression threshold)
- Outliers (high residuals)
- Regression models per group

**Key parameters:**
- `r2_threshold`: Minimum R² for valid regression (default: 0.99)
- `outlier_threshold`: Standardized residual threshold (default: ±2.0σ)

---

### Rule 2: Sugar Count Calculation
**File:** `rule2_sugar_count.py`
**Class:** `Rule2SugarCount`

**Purpose:** Calculates total sugar count from ganglioside nomenclature

**Formula:**
```
total_sugars = sialic_acids + neutral_sugars + modifications
             = e-component + (5 - f-component) + additional
```

**Example:**
```
GM1 = M(1) + (5-1) = 5 sugars
GD1 = D(2) + (5-1) = 6 sugars
GT1 = T(3) + (5-1) = 7 sugars
```

**Output:**
- Sugar composition breakdown
- Sialic acid count
- Neutral sugar count
- Additional modifications

---

### Rule 3: Structural Isomer Classification
**File:** `rule3_isomer_classification.py`
**Class:** `Rule3IsomerClassification`

**Purpose:** Identifies and classifies structural isomers

**Recognized isomers:**
- **GD1 series:** GD1a (+HexNAc) vs GD1b (+dHex)
- **GM1 series:** GM1a vs GM1b (sialic acid position)
- **GT1 series:** GT1a vs GT1b vs GT1c (linkage position)
- **GQ1 series:** GQ1b vs GQ1c (species-dependent)

**Output:**
- Isomer type classification
- Species-specific corrections
- Modification-based identification

---

### Rule 4: O-acetylation Validation
**File:** `rule4_oacetylation.py`
**Class:** `Rule4OAcetylation`

**Purpose:** Validates that O-acetylation increases retention time

**Chemistry:**
```
O-acetylation: -OH → -OCOCH₃
Effect: Increases hydrophobicity → Longer RT
```

**Validation:**
```
RT(compound + OAc) > RT(compound)
```

**Output:**
- Valid O-acetylated compounds (RT increased)
- Invalid compounds (unexpected RT behavior)
- RT change statistics

**Key parameters:**
- `min_rt_increase`: Minimum expected RT increase (default: 0.0 min)

---

### Rule 5: In-source Fragmentation Detection
**File:** `rule5_fragmentation.py`
**Class:** `Rule5Fragmentation`

**Purpose:** Detects and consolidates in-source fragmentation products

**Detection criteria:**
1. Same lipid chain (suffix)
2. Similar RT (within ±tolerance)
3. Decreasing sugar count

**Algorithm:**
```
1. Group by lipid chain (36:1;O2, 34:1;O2, etc.)
2. Cluster by RT (±0.1 min tolerance)
3. Within each cluster:
   - Sort by sugar count (descending) and Log P (ascending)
   - Parent = highest sugar count (most complete)
   - Fragments = remaining compounds
4. Consolidate fragment volumes into parent
```

**Example:**
```
GT1(36:1;O2) - RT: 8.70, Sugar: 7, Volume: 1,200,000  ✅ Parent
GD1(36:1;O2) - RT: 8.72, Sugar: 6, Volume: 300,000   ❌ Fragment
GM1(36:1;O2) - RT: 8.71, Sugar: 5, Volume: 200,000   ❌ Fragment

→ GT1 final volume: 1,700,000 (consolidated)
```

**Output:**
- Final compounds (with consolidated volumes)
- Fragment candidates
- Consolidation statistics

**Key parameters:**
- `rt_tolerance`: RT window for co-elution (default: ±0.1 min)

---

## 🔧 Usage

### Individual Rule Usage

```python
from backend.rules import Rule1PrefixRegression, Rule2SugarCount

# Create rule instance
rule1 = Rule1PrefixRegression(r2_threshold=0.99, outlier_threshold=2.0)

# Apply rule to data
results = rule1.apply(preprocessed_df)

# Access results
valid_compounds = results['valid_compounds']
outliers = results['outliers']
regression_models = results['regression_results']
```

### Complete Analysis Pipeline

```python
from backend.rules import (
    Rule1PrefixRegression,
    Rule2SugarCount,
    Rule3IsomerClassification,
    Rule4OAcetylation,
    Rule5Fragmentation
)

# Initialize all rules
rule1 = Rule1PrefixRegression()
rule2 = Rule2SugarCount()
rule3 = Rule3IsomerClassification()
rule4 = Rule4OAcetylation()
rule5 = Rule5Fragmentation()

# Apply rules sequentially
results_r1 = rule1.apply(df)
results_r2 = rule2.apply(df)
results_r3 = rule3.apply(df, data_type="Porcine")
results_r4 = rule4.apply(df)
results_r5 = rule5.apply(df)
```

---

## 🧪 Testing Individual Rules

Each rule can be tested independently:

```python
# Test Rule 2 with sample data
import pandas as pd
from backend.rules import Rule2SugarCount

test_data = pd.DataFrame({
    'Name': ['GM1(36:1;O2)', 'GD1(36:1;O2)', 'GT1(36:1;O2)'],
    'prefix': ['GM1', 'GD1', 'GT1']
})

rule2 = Rule2SugarCount()
results = rule2.apply(test_data)

for compound, sugar_info in results['sugar_analysis'].items():
    print(f"{compound}: {sugar_info['total_sugars']} sugars")
    print(f"  Formula: {sugar_info['formula']}")
```

---

## 📝 Adding New Rules

To add a new rule:

1. Create `backend/rules/rule6_newrule.py`
2. Implement class with `apply()` method
3. Add to `__init__.py` exports
4. Update `RULE_DESCRIPTIONS` in `__init__.py`
5. Document in this README

**Template:**
```python
class Rule6NewRule:
    def __init__(self, param1, param2):
        self.param1 = param1
        print("🔬 Rule 6: New Rule initialized")

    def apply(self, df: pd.DataFrame) -> Dict[str, Any]:
        print("\n🔬 Applying Rule 6: New Rule")

        # Your logic here

        return {
            "results": ...,
            "statistics": ...
        }
```

---

## 🎯 Design Principles

1. **Independence:** Each rule is self-contained
2. **Testability:** Rules can be tested in isolation
3. **Maintainability:** Changes to one rule don't affect others
4. **Clarity:** Clear documentation and naming
5. **Consistency:** All rules follow the same pattern:
   - `__init__()` for configuration
   - `apply(df)` for execution
   - Return dictionary with results and statistics

---

## 📚 References

- Ganglioside nomenclature: [IUPAC-IUB recommendations](https://www.chem.qmul.ac.uk/iupac/misc/glylp.html)
- Multiple regression: [scikit-learn LinearRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html)
- In-source fragmentation: LC-MS/MS methodology literature

---

## 🤝 Contributing

When modifying rules:
1. Maintain backward compatibility
2. Add unit tests for new features
3. Update documentation
4. Test with sample datasets
5. Update version history
