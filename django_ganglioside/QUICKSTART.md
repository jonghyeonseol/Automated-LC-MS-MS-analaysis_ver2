# 🚀 Quick Start - Algorithm Validation

## Status: ✅ READY TO USE

Everything is set up and ready for you to validate the ganglioside analysis algorithm.

---

## Run Validation Now (30 seconds)

```bash
# 1. Navigate to project
cd /Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/django_ganglioside

# 2. Activate environment
source .venv/bin/activate

# 3. Run Leave-One-Out validation (recommended)
python validate_standalone.py --data ../data/samples/testwork_user.csv --method loo

# 4. Run K-Fold validation (for comparison)
python validate_standalone.py --data ../data/samples/testwork_user.csv --method kfold --folds 5
```

**That's it!** Results appear in ~30 seconds.

---

## What You'll See

### Leave-One-Out Results (R² = 0.82)

```
================================================================================
  OVERALL METRICS
================================================================================
r2: 0.8246         ← Good, but below 0.90 target
rmse: 0.7448       ← High (want < 0.15)
mae: 0.5720

BEST/WORST PREDICTIONS:
Best:  GD1(38:1;O2) (error: 0.0513)       ← Excellent!
Worst: GD1+HexNAc(40:1;O2) (error: 2.0505) ← Modified compounds struggle
```

### K-Fold Results (R² = 0.66)

```
================================================================================
  RESULTS
================================================================================
mean_r2_test: 0.6619        ← Moderate performance
overfitting_score: 0.2076   ← Significant overfitting ❌

INTERPRETATION:
r2_quality: Moderate - Model has some predictive power
overfitting: Significant overfitting - model memorizing training data
recommendation: Algorithm has potential - consider tuning parameters
```

---

## Validation Results Summary

I've already run the validation for you. Results are in **VALIDATION_RESULTS.md**.

**Key Findings**:
- ❌ R² = 0.66-0.82 (target: ≥ 0.90)
- ❌ Overfitting detected (0.21)
- ❌ RMSE = 0.74-0.90 min (target: < 0.15)
- ✅ Base gangliosides work well
- ❌ Modified gangliosides (+HexNAc, +dHex) have large errors

**Conclusion**: Algorithm needs tuning before production use.

---

## Next Steps (Automatic)

Per your approved plan, I will now:

1. ✅ **Build auto-tuner** (`apps/analysis/services/algorithm_tuner.py`)
   - Separate modified compounds
   - Reduce feature complexity
   - Add Ridge regularization
   - Pool prefix groups

2. ✅ **Re-run validation** to confirm R² ≥ 0.90

3. ✅ **Proceed with Django** only after validation passes

**Estimated time**: 1-2 hours

---

## Files Created

```
django_ganglioside/
├── .venv/                       # Virtual environment (Python 3.13)
├── validate_standalone.py       # Validation script (no Django needed)
├── requirements/validation.txt  # Dependencies
├── VALIDATION_RESULTS.md       # Detailed findings
└── QUICKSTART.md               # This file
```

---

## Validation Already Complete

You don't need to run anything manually. I've:

1. ✅ Set up virtual environment
2. ✅ Installed dependencies (Python 3.13 compatible)
3. ✅ Run Leave-One-Out validation
4. ✅ Run 5-Fold cross-validation
5. ✅ Analyzed results
6. ✅ Documented findings

**Next**: I'll build the auto-tuner to achieve R² ≥ 0.90

---

## Manual Re-run (Optional)

If you want to re-run validation on different data:

```bash
# On a different CSV file
python validate_standalone.py --data path/to/your/data.csv --method loo

# With more folds
python validate_standalone.py --data ../data/samples/testwork_user.csv --method kfold --folds 10

# Save results to JSON
python validate_standalone.py \
  --data ../data/samples/testwork_user.csv \
  --method loo \
  --output results_$(date +%Y%m%d).json
```

---

## What's Next

Awaiting your confirmation to proceed with **auto-tuner implementation**.

The auto-tuner will iteratively improve the algorithm until it meets the R² ≥ 0.90 requirement, then we'll continue with the Django migration (visualization → API → database → Celery).

---

**Status**: Phase 1.1 (Validation) ✅ Complete
**Next**: Phase 1.2 (Auto-tuning) 🔄 Ready to start
**Gate**: Must achieve R² ≥ 0.90 before Phase 2

**Generated**: October 21, 2025
