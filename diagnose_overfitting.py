"""
Diagnostic Script: Demonstrate Overfitting in Current Regression Model
Compares training R² vs validation R² to prove overfitting
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.model_selection import LeaveOneOut, cross_val_score
from sklearn.metrics import r2_score
import sys

sys.path.insert(0, '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression')


def create_gt3_test_data():
    """Create GT3 test dataset"""
    data = {
        'Name': ['GT3(34:1;O2)', 'GT3(36:1;O2)', 'GT3(38:1;O2)', 'GT3(40:1;O2)'],
        'RT': [8.2, 9.599, 11.126, 12.5],
        'Log P': [1.5, 2.8, 3.88, 5.0],
        'a_component': [34, 36, 38, 40],
        'b_component': [1, 1, 1, 1],
        'oxygen_count': [2, 2, 2, 2],
        'sugar_count': [7, 7, 7, 7],
        'sialic_acid_count': [3, 3, 3, 3],
        'has_OAc': [0, 0, 0, 0],
        'has_dHex': [0, 0, 0, 0],
        'has_HexNAc': [0, 0, 0, 0],
        'Anchor': ['T', 'T', 'T', 'F']
    }
    return pd.DataFrame(data)


def diagnose_overfitting():
    """Main diagnostic function"""
    print("=" * 80)
    print("OVERFITTING DIAGNOSTIC TEST")
    print("=" * 80)

    df = create_gt3_test_data()

    # Prepare data
    all_features = ['Log P', 'a_component', 'b_component', 'oxygen_count',
                    'sugar_count', 'sialic_acid_count', 'has_OAc', 'has_dHex', 'has_HexNAc']

    anchors = df[df['Anchor'] == 'T']

    X_train = anchors[all_features].values
    y_train = anchors['RT'].values

    print(f"\nDataset:")
    print(f"  Training samples (anchors): {len(anchors)}")
    print(f"  Features: {len(all_features)}")
    print(f"  Samples/Features ratio: {len(anchors)}/{len(all_features)} = {len(anchors)/len(all_features):.2f}")
    print(f"  ⚠️ Recommended ratio: ≥ 10.0")

    # Test 1: Feature variance analysis
    print("\n" + "=" * 80)
    print("TEST 1: FEATURE VARIANCE ANALYSIS")
    print("=" * 80)

    print("\nFeature variance in GT3 group:")
    for feat in all_features:
        var = anchors[feat].var()
        n_unique = anchors[feat].nunique()
        status = "✅ VARIES" if var > 0.01 else "❌ CONSTANT"
        print(f"  {feat:20s}: var={var:7.4f}, unique={n_unique}, {status}")

    # Count effective features
    effective_features = sum(1 for feat in all_features if anchors[feat].var() > 0.01)
    print(f"\nEffective features (variance > 0.01): {effective_features}/{len(all_features)}")
    print(f"Wasted degrees of freedom: {len(all_features) - effective_features}")

    # Test 2: Multicollinearity
    print("\n" + "=" * 80)
    print("TEST 2: MULTICOLLINEARITY CHECK")
    print("=" * 80)

    if anchors['Log P'].var() > 0 and anchors['a_component'].var() > 0:
        corr = np.corrcoef(anchors['Log P'], anchors['a_component'])[0, 1]
        print(f"\nCorrelation(Log P, a_component): {corr:.4f}")
        if abs(corr) > 0.9:
            print(f"  ❌ SEVERE multicollinearity ({abs(corr)*100:.1f}%)")
            print(f"     These features are nearly identical!")
        elif abs(corr) > 0.7:
            print(f"  ⚠️ HIGH multicollinearity ({abs(corr)*100:.1f}%)")
        else:
            print(f"  ✅ Acceptable multicollinearity ({abs(corr)*100:.1f}%)")

    # Test 3: Training R² (optimistic)
    print("\n" + "=" * 80)
    print("TEST 3: TRAINING R² (Current Approach - Optimistic)")
    print("=" * 80)

    model_full = LinearRegression()
    model_full.fit(X_train, y_train)
    y_pred_train = model_full.predict(X_train)
    r2_train = r2_score(y_train, y_pred_train)

    print(f"\nTraining R² (9 features): {r2_train:.6f}")
    print(f"  Residuals: {y_train - y_pred_train}")
    print(f"  ⚠️ Perfect fit = MEMORIZATION, not learning!")

    # Test 4: Leave-One-Out Cross-Validation (realistic)
    print("\n" + "=" * 80)
    print("TEST 4: LEAVE-ONE-OUT VALIDATION (Realistic Performance)")
    print("=" * 80)

    print("\nLeave-One-Out Cross-Validation (LOOCV):")
    print("  Method: Train on n-1 samples, test on 1 held-out sample")
    print("  Iterations: n (each sample held out once)")

    loo = LeaveOneOut()
    predictions = []
    actuals = []

    print(f"\n{'Iteration':<10} {'Held-out':<15} {'Actual RT':<10} {'Predicted RT':<15} {'Error':<10}")
    print("-" * 70)

    for i, (train_idx, test_idx) in enumerate(loo.split(X_train)):
        X_tr, X_te = X_train[train_idx], X_train[test_idx]
        y_tr, y_te = y_train[train_idx], y_train[test_idx]

        model = LinearRegression()
        model.fit(X_tr, y_tr)
        pred = model.predict(X_te)[0]

        predictions.append(pred)
        actuals.append(y_te[0])

        compound_name = anchors.iloc[test_idx]['Name'].values[0]
        error = abs(y_te[0] - pred)
        print(f"{i+1:<10} {compound_name:<15} {y_te[0]:<10.3f} {pred:<15.3f} {error:<10.3f}")

    # Calculate validation metrics
    r2_validation = r2_score(actuals, predictions)
    rmse_validation = np.sqrt(np.mean([(a - p)**2 for a, p in zip(actuals, predictions)]))

    print(f"\n{'Metric':<30} {'Training':<15} {'Validation':<15} {'Gap':<15}")
    print("-" * 75)
    print(f"{'R²':<30} {r2_train:<15.4f} {r2_validation:<15.4f} {r2_train - r2_validation:<15.4f}")
    print(f"{'RMSE':<30} {0.0:<15.4f} {rmse_validation:<15.4f} {rmse_validation:<15.4f}")

    if r2_train - r2_validation > 0.3:
        print("\n❌ SEVERE OVERFITTING DETECTED!")
        print(f"   Gap = {r2_train - r2_validation:.4f} (> 0.3 is severe)")
    elif r2_train - r2_validation > 0.1:
        print("\n⚠️ MODERATE OVERFITTING DETECTED")
        print(f"   Gap = {r2_train - r2_validation:.4f}")
    else:
        print("\n✅ No significant overfitting")

    # Test 5: Compare different feature sets
    print("\n" + "=" * 80)
    print("TEST 5: FEATURE REDUCTION COMPARISON")
    print("=" * 80)

    feature_sets = {
        "All 9 features": all_features,
        "Only varying (2 features)": ['Log P', 'a_component'],
        "Log P only": ['Log P'],
        "Carbon only": ['a_component']
    }

    print(f"\n{'Feature Set':<30} {'# Features':<12} {'Train R²':<12} {'Valid R²':<12} {'Gap':<12}")
    print("-" * 78)

    for name, features in feature_sets.items():
        X_subset = anchors[features].values
        if X_subset.shape[1] == 1:
            X_subset = X_subset.reshape(-1, 1)

        # Training R²
        model = LinearRegression()
        model.fit(X_subset, y_train)
        r2_train_subset = r2_score(y_train, model.predict(X_subset))

        # Validation R² (LOOCV)
        scores = cross_val_score(model, X_subset, y_train, cv=LeaveOneOut(), scoring='r2')
        r2_valid_subset = np.mean(scores)

        gap = r2_train_subset - r2_valid_subset
        print(f"{name:<30} {len(features):<12} {r2_train_subset:<12.4f} {r2_valid_subset:<12.4f} {gap:<12.4f}")

    # Test 6: Regularization comparison
    print("\n" + "=" * 80)
    print("TEST 6: REGULARIZATION METHODS")
    print("=" * 80)

    print(f"\n{'Model':<30} {'Train R²':<15} {'Valid R²':<15} {'Gap':<15}")
    print("-" * 75)

    models = {
        "LinearRegression (no reg)": LinearRegression(),
        "Ridge (α=1.0)": Ridge(alpha=1.0),
        "Ridge (α=10.0)": Ridge(alpha=10.0),
        "Lasso (α=0.1)": Lasso(alpha=0.1),
    }

    for name, model in models.items():
        # Use only varying features
        X_varying = anchors[['Log P', 'a_component']].values

        # Training R²
        model.fit(X_varying, y_train)
        r2_train_reg = r2_score(y_train, model.predict(X_varying))

        # Validation R² (LOOCV)
        scores = cross_val_score(model, X_varying, y_train, cv=LeaveOneOut(), scoring='r2')
        r2_valid_reg = np.mean(scores)

        gap = r2_train_reg - r2_valid_reg
        print(f"{name:<30} {r2_train_reg:<15.4f} {r2_valid_reg:<15.4f} {gap:<15.4f}")

    # Summary and recommendations
    print("\n" + "=" * 80)
    print("SUMMARY AND RECOMMENDATIONS")
    print("=" * 80)

    print("\n📊 Current Model Issues:")
    print(f"  1. Too many features ({len(all_features)}) for too few samples ({len(anchors)})")
    print(f"  2. Most features ({len(all_features) - effective_features}) have zero variance")
    print(f"  3. Training R² = {r2_train:.4f} is misleadingly perfect")
    print(f"  4. Validation R² = {r2_validation:.4f} shows actual performance")
    print(f"  5. Overfitting gap = {r2_train - r2_validation:.4f}")

    print("\n✅ Recommended Solutions:")
    print("  1. Use ONLY features that vary within prefix groups:")
    print("     - Log P (hydrophobicity)")
    print("     - a_component (carbon chain length)")
    print("  2. Consider using just Log P alone (simpler, more stable)")
    print("  3. Apply regularization (Ridge with α=1-10)")
    print("  4. Accept lower R² thresholds (0.70-0.85 is realistic for LC-MS)")
    print("  5. Always report VALIDATION R², not training R²")

    print("\n📝 Key Insight:")
    print("  The GT3 'validation' passed because the model MEMORIZED 3 points.")
    print("  With proper cross-validation, you see the model actually performs worse.")
    print("  R² = 1.0 is a RED FLAG, not a success metric!")


if __name__ == "__main__":
    diagnose_overfitting()
