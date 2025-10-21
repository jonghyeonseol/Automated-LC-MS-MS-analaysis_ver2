# Algorithm Validation Guide

**Purpose**: Validate the 5-rule ganglioside analysis algorithm using MS/MS verified anchor compounds to ensure it's ready for production use.

---

## 🎯 Quick Start - Validate Your Algorithm Now

### 1. Setup (One-time)

```bash
cd django_ganglioside

# If not already done:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/development.txt

# Copy your test data
cp ../data/samples/testwork_user.csv ./test_data.csv
```

### 2. Run Validation (Choose One Method)

#### Option A: Leave-One-Out (Recommended for small datasets)
```bash
python validate_algorithm.py --data test_data.csv --method loo
```

**Best for**: <30 anchor compounds
**Runtime**: ~30 seconds
**Output**: Individual prediction for each anchor

#### Option B: K-Fold Cross-Validation (Recommended for larger datasets)
```bash
python validate_algorithm.py --data test_data.csv --method kfold --folds 5
```

**Best for**: >20 anchor compounds
**Runtime**: ~2 minutes
**Output**: Aggregated metrics across 5 folds

#### Option C: Quick Analysis (No validation, just run algorithm)
```bash
python validate_algorithm.py --data test_data.csv --method quick
```

**Best for**: Quick sanity check
**Runtime**: ~10 seconds
**Output**: Overall statistics only

### 3. Interpret Results

The script will output:
- **R² Score** (0.0-1.0): How well the model predicts RT
  - ≥0.90: Excellent
  - 0.75-0.89: Good
  - 0.50-0.74: Moderate
  - <0.50: Poor (needs tuning)

- **RMSE** (Root Mean Squared Error): Average prediction error in minutes
  - <0.1 min: Excellent
  - 0.1-0.2 min: Good
  - >0.2 min: Check if acceptable for your instrument

- **Overfitting Score** (R²_train - R²_test):
  - <0.05: No overfitting ✅
  - 0.05-0.15: Mild overfitting ⚠️
  - >0.15: Significant overfitting ❌

---

## 📊 Understanding Validation Methods

### Leave-One-Out (LOO)
```
Round 1: Train on anchors [2,3,4,5...N], test on anchor [1]
Round 2: Train on anchors [1,3,4,5...N], test on anchor [2]
...
Round N: Train on anchors [1,2,3,4...N-1], test on anchor [N]
```

**Pros**:
- Uses maximum training data
- Best for small datasets
- No random splitting

**Cons**:
- Computationally expensive for large datasets
- High variance in results

### K-Fold Cross-Validation
```
Fold 1: Train 80% | Test 20%
Fold 2: Train 80% | Test 20%
...
Fold 5: Train 80% | Test 20%
```

**Pros**:
- More stable estimates
- Faster than LOO for large datasets
- Standard practice in ML

**Cons**:
- Needs sufficient anchors (>20 recommended)
- Results depend on random split

### Train/Test Split
```
Single split: Train 80% | Test 20%
```

**Pros**:
- Fastest method
- Mimics real-world deployment

**Cons**:
- Results depend heavily on which anchors are in test set
- Less reliable for small datasets

---

## 🔬 What the Validation Tests

### 1. Regression Quality (R²)
Tests how well Log P predicts RT using anchor compounds.

**What it means**:
- R² = 0.90 means 90% of RT variance is explained by Log P
- High R² = Strong Log P-RT relationship
- Low R² = Weak relationship (may need more features)

### 2. Generalization Ability
Compares performance on training vs test data.

**What it means**:
- If R²_train >> R²_test: Model memorizing, not learning
- If R²_train ≈ R²_test: Model generalizes well
- Overfitting score <0.05 is ideal

### 3. Prediction Accuracy (RMSE, MAE)
Measures average prediction error in minutes.

**What it means**:
- RMSE = 0.1 min = predictions off by ±0.1 min on average
- Lower is better
- Compare to your instrument's RT reproducibility

### 4. Outlier Detection Performance
Tests how well the algorithm identifies true vs false positives.

**What it means**:
- Precision: Of compounds marked "valid", how many are truly valid?
- Recall: Of truly valid compounds, how many did we catch?
- F1 score: Balance between precision and recall

---

## 📈 Expected Results for Your Data

Based on the test data (`testwork_user.csv`):

### Expected Metrics (GD1 compounds, Porcine data)
```
Dataset: ~30-50 compounds
Anchors: ~20-30 (Anchor='T')
Method: Leave-One-Out recommended

Expected Performance:
  R² (LOO):        0.85 - 0.95
  RMSE (LOO):      0.10 - 0.20 min
  MAE (LOO):       0.08 - 0.15 min
  Overfitting:     <0.05 (minimal)

Interpretation:
  ✅ If R² > 0.85: Algorithm works well, ready for use
  ⚠️  If R² 0.70-0.85: Acceptable, but consider tuning
  ❌ If R² < 0.70: Need to investigate data quality
```

### Common Issues and Solutions

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| R² < 0.50 | Weak Log P-RT correlation | Check if data is correctly labeled |
| High overfitting (>0.20) | Too many features, too few samples | Reduce features (see REGRESSION_MODEL_EVALUATION.md) |
| RMSE > 0.3 min | Outliers in anchors | Review anchor compound quality |
| Different R² per fold | Heterogeneous data | Ensure consistent sample preparation |

---

## 🛠️ Advanced Usage

### Save Results to File
```bash
python validate_algorithm.py --data test_data.csv --method kfold --output results.json
```

### Customize Parameters
```bash
# Change number of folds
python validate_algorithm.py --data test_data.csv --method kfold --folds 10

# Change test size for train/test split
python validate_algorithm.py --data test_data.csv --method split --test-size 0.3

# Specify data type
python validate_algorithm.py --data test_data.csv --method loo --data-type Human
```

### Batch Validation
```bash
# Validate multiple datasets
for file in data/*.csv; do
    echo "Validating $file"
    python validate_algorithm.py --data "$file" --method loo --output "results/$(basename $file .csv)_results.json"
done
```

---

## 📊 Example Output

### Leave-One-Out Output
```
================================================================================
  LEAVE-ONE-OUT CROSS-VALIDATION
================================================================================

Dataset: 30 compounds (25 anchors)
Method: Each anchor is tested individually

Running validation...

================================================================================
  OVERALL METRICS
================================================================================
r2: 0.8921
rmse: 0.1234
mae: 0.0987
max_error: 0.3456
mean_residual: 0.0012
std_residual: 0.1200

--------------------------------------------------------------------------------
PREDICTION DETAILS:
Compound                       Actual RT  Predicted      Error
-----------------------------------------------------------------
GD1(34:1;O2)                       7.588      7.612     -0.024
GD1(35:1;O2)                       8.386      8.401     -0.015
GD1(36:1;O2)                       9.144      9.123      0.021
...

--------------------------------------------------------------------------------
BEST/WORST PREDICTIONS:
Best:  GD1(36:1;O2) (error: 0.0021)
Worst: GD1(40:3;O2) (error: 0.3456)

================================================================================
  VALIDATION COMPLETE
================================================================================
```

### K-Fold Output
```
================================================================================
  5-FOLD CROSS-VALIDATION
================================================================================

Dataset: 30 compounds (25 anchors)
Splits: 5

Running validation...

================================================================================
  RESULTS
================================================================================
mean_r2_train: 0.9234
mean_r2_test: 0.8876
std_r2_test: 0.0421
mean_rmse_test: 0.1345
std_rmse_test: 0.0234
mean_mae_test: 0.1012
mean_overfitting_score: 0.0358
max_overfitting_score: 0.0567

--------------------------------------------------------------------------------
INTERPRETATION:
r2_quality: Good - Model has strong predictive power
consistency: Very consistent across folds
overfitting: No significant overfitting detected
recommendation: Algorithm performs well - ready for production use

--------------------------------------------------------------------------------
PER-FOLD BREAKDOWN:
Fold 1:
  Train R²: 0.9312 | Test R²: 0.8923
  Train RMSE: 0.0987 | Test RMSE: 0.1321
  Overfitting Score: 0.0389
  Samples: 24 train / 6 test
...
```

---

## 🚦 Decision Matrix: When to Proceed

### ✅ READY FOR PRODUCTION
- R² (test) ≥ 0.75
- Overfitting score <0.10
- RMSE acceptable for your application
- Consistent results across folds (if using k-fold)

**Action**: Proceed with Django migration and deployment

### ⚠️ NEEDS TUNING
- R² (test) 0.50-0.75
- Overfitting score 0.10-0.20
- High variance across folds

**Action**:
1. Review `REGRESSION_MODEL_EVALUATION.md`
2. Reduce features (use only Log P + carbon chain)
3. Increase R² threshold from 0.99 to 0.75
4. Add regularization (Ridge regression)
5. Re-validate

### ❌ NEEDS INVESTIGATION
- R² (test) <0.50
- Overfitting score >0.20
- Predictions consistently poor

**Action**:
1. Check data quality (anchor compounds correctly labeled?)
2. Verify Log P calculations
3. Check for systematic RT shift
4. Review sample preparation protocol
5. Consider if different features are needed

---

## 🔍 Debugging Tips

### Low R² (<0.70)
```python
# Manually inspect data
import pandas as pd
df = pd.read_csv('test_data.csv')

# Check anchor distribution
anchors = df[df['Anchor'] == 'T']
print(anchors[['Name', 'RT', 'Log P']])

# Plot RT vs Log P
import matplotlib.pyplot as plt
plt.scatter(anchors['Log P'], anchors['RT'])
plt.xlabel('Log P')
plt.ylabel('RT (min)')
plt.title('Anchor Compounds RT vs Log P')
plt.show()

# Should show clear linear trend
```

### High Overfitting (>0.15)
```python
# Check sample sizes
python validate_algorithm.py --data test_data.csv --method quick

# If "Samples: 3" and "Features: 9" → PROBLEM
# Solution: Reduce features in ganglioside_processor.py
# Change feature_names = ["Log P", "a_component"] only
```

### Inconsistent Fold Results
```python
# Increase number of folds
python validate_algorithm.py --data test_data.csv --method kfold --folds 10

# Use LOO for maximum stability
python validate_algorithm.py --data test_data.csv --method loo
```

---

## 📁 Files Created

```
django_ganglioside/
├── apps/analysis/services/
│   ├── ganglioside_processor.py       # Copied from src/
│   ├── ganglioside_categorizer.py     # Copied from src/utils/
│   ├── regression_analyzer.py         # Copied from src/
│   └── algorithm_validator.py         # NEW: Validation framework
│
└── validate_algorithm.py               # NEW: Standalone validation script
```

---

## 🎓 What You're Testing

The validation tests these components of the 5-rule algorithm:

1. **Rule 1** (Regression):
   - Can anchor compounds predict RT from Log P?
   - Is the model generalizable or overfitting?
   - How accurate are predictions?

2. **Outlier Detection**:
   - Are true valid compounds correctly identified?
   - Are problematic compounds flagged?

3. **Feature Importance**:
   - Do additional features (carbon chain, sugar count) help?
   - Or do they just cause overfitting?

4. **Robustness**:
   - Does performance depend on which data is used for training?
   - Is the algorithm stable?

---

## 📞 Next Steps After Validation

### If Algorithm Validates Successfully (R² > 0.75)
1. ✅ Document validation results
2. ✅ Proceed with Django API development
3. ✅ Create serializers and views
4. ✅ Deploy to production

### If Algorithm Needs Tuning (R² 0.50-0.75)
1. ⚠️ Implement recommended fixes from REGRESSION_MODEL_EVALUATION.md
2. ⚠️ Re-validate with tuned parameters
3. ⚠️ Repeat until R² > 0.75
4. ⚠️ Then proceed with Django development

### If Algorithm Fails Validation (R² < 0.50)
1. ❌ Review data quality
2. ❌ Investigate algorithm assumptions
3. ❌ Consider alternative approaches
4. ❌ Do NOT proceed to production

---

## 🚀 Run Validation Now!

```bash
cd django_ganglioside
source venv/bin/activate
python validate_algorithm.py --data ../data/samples/testwork_user.csv --method loo
```

This will give you **definitive proof** that your algorithm works before investing time in the full Django migration!
