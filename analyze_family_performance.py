#!/usr/bin/env python3
"""
Family Model Performance Analysis
Analyzes why some families pool well (high R²) and others don't
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import LeaveOneOut
import matplotlib.pyplot as plt
import seaborn as sns

# Prefix families (same as in code)
PREFIX_FAMILIES = {
    "GD_family": ["GD1", "GD1a", "GD1b", "GD1+HexNAc", "GD1+dHex", "GD3"],
    "GM_family": ["GM1", "GM1+HexNAc", "GM3", "GM3+OAc"],
    "GT_family": ["GT1", "GT1a", "GT1b", "GT3"],
    "GQ_family": ["GQ1", "GQ1a", "GQ1b", "GQ1c", "GQ1+HexNAc"],
    "GP_family": ["GP1", "GP1a"]
}


def cross_validate_regression(X, y):
    """Leave-One-Out Cross-Validation"""
    if len(X) < 3:
        return None

    loo = LeaveOneOut()
    predictions = []
    actuals = []

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = Ridge(alpha=1.0)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        predictions.append(pred[0])
        actuals.append(y_test[0])

    validation_r2 = r2_score(actuals, predictions)
    return float(validation_r2)


def analyze_family(df, family_name, family_prefixes):
    """Analyze a single family's pooling performance"""

    print(f"\n{'='*80}")
    print(f"📊 {family_name}")
    print(f"{'='*80}")

    # Get family data
    family_df = df[df['prefix'].isin(family_prefixes)]
    family_anchors = family_df[family_df['Anchor'] == 'T']

    print(f"\n📋 Family Composition:")
    for prefix in family_prefixes:
        prefix_anchors = family_df[(family_df['prefix'] == prefix) & (family_df['Anchor'] == 'T')]
        n = len(prefix_anchors)
        if n > 0:
            print(f"   {prefix}: {n} anchors")

    print(f"\n📈 Total: {len(family_anchors)} pooled anchors")

    if len(family_anchors) < 10:
        print(f"   ⚠️  Insufficient anchors for family pooling (< 10)")
        return None

    # Check Log P variation
    X = family_anchors[['Log P']].values
    y = family_anchors['RT'].values

    log_p_range = X.max() - X.min()
    log_p_std = X.std()
    rt_range = y.max() - y.min()
    rt_std = y.std()

    print(f"\n📊 Feature Statistics:")
    print(f"   Log P: range={log_p_range:.3f}, std={log_p_std:.3f}")
    print(f"   RT: range={rt_range:.3f}, std={rt_std:.3f}")

    # Check within-prefix consistency
    print(f"\n🔍 Within-Prefix Analysis:")
    prefix_r2_values = []

    for prefix in family_prefixes:
        prefix_anchors = family_df[(family_df['prefix'] == prefix) & (family_df['Anchor'] == 'T')]
        if len(prefix_anchors) >= 3:
            X_prefix = prefix_anchors[['Log P']].values
            y_prefix = prefix_anchors['RT'].values

            if len(np.unique(X_prefix)) >= 2:
                model = Ridge(alpha=1.0)
                model.fit(X_prefix, y_prefix)
                y_pred = model.predict(X_prefix)
                prefix_r2 = r2_score(y_prefix, y_pred)
                prefix_r2_values.append(prefix_r2)
                print(f"   {prefix}: R²={prefix_r2:.3f} (n={len(prefix_anchors)})")

    if prefix_r2_values:
        avg_prefix_r2 = np.mean(prefix_r2_values)
        print(f"\n   Average within-prefix R²: {avg_prefix_r2:.3f}")

    # Fit family model
    model = Ridge(alpha=1.0)
    model.fit(X, y)

    training_r2 = r2_score(y, model.predict(X))
    validation_r2 = cross_validate_regression(X, y)

    print(f"\n🎯 Family Model Performance:")
    print(f"   Training R²: {training_r2:.3f}")
    print(f"   Validation R²: {validation_r2:.3f}")
    print(f"   Overfitting gap: {training_r2 - validation_r2:.3f}")

    # Threshold check
    r2_check = validation_r2 if validation_r2 is not None else training_r2
    threshold = 0.70

    if r2_check >= threshold:
        print(f"   ✅ PASS (R²={r2_check:.3f} >= {threshold})")
        status = "PASS"
    else:
        print(f"   ❌ FAIL (R²={r2_check:.3f} < {threshold})")
        status = "FAIL"

    # Analyze residuals by prefix
    y_pred = model.predict(X)
    residuals = y - y_pred

    print(f"\n📉 Residual Analysis by Prefix:")
    for prefix in family_prefixes:
        prefix_mask = family_anchors['prefix'] == prefix
        if prefix_mask.sum() > 0:
            prefix_residuals = residuals[prefix_mask.values]
            residual_mean = prefix_residuals.mean()
            residual_std = prefix_residuals.std()
            print(f"   {prefix}: mean={residual_mean:.3f}, std={residual_std:.3f}")

    return {
        'family_name': family_name,
        'n_anchors': len(family_anchors),
        'log_p_range': log_p_range,
        'log_p_std': log_p_std,
        'rt_range': rt_range,
        'rt_std': rt_std,
        'training_r2': training_r2,
        'validation_r2': validation_r2,
        'status': status,
        'coefficient': model.coef_[0],
        'intercept': model.intercept_
    }


def visualize_families(df):
    """Create visualization comparing all families"""

    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    axes = axes.flatten()

    for idx, (family_name, family_prefixes) in enumerate(PREFIX_FAMILIES.items()):
        ax = axes[idx]

        family_df = df[df['prefix'].isin(family_prefixes)]
        family_anchors = family_df[family_df['Anchor'] == 'T']

        if len(family_anchors) < 3:
            ax.text(0.5, 0.5, f'{family_name}\nInsufficient data',
                   ha='center', va='center', fontsize=12)
            ax.set_title(family_name)
            continue

        # Plot each prefix with different color
        colors = plt.cm.Set2(np.linspace(0, 1, len(family_prefixes)))

        for prefix_idx, prefix in enumerate(family_prefixes):
            prefix_anchors = family_anchors[family_anchors['prefix'] == prefix]
            if len(prefix_anchors) > 0:
                ax.scatter(prefix_anchors['Log P'], prefix_anchors['RT'],
                          label=prefix, alpha=0.7, s=100, color=colors[prefix_idx])

        # Fit and plot family regression line
        X = family_anchors[['Log P']].values
        y = family_anchors['RT'].values

        model = Ridge(alpha=1.0)
        model.fit(X, y)

        X_line = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
        y_line = model.predict(X_line)

        validation_r2 = cross_validate_regression(X, y)
        r2_display = validation_r2 if validation_r2 is not None else r2_score(y, model.predict(X))

        ax.plot(X_line, y_line, 'k--', linewidth=2, alpha=0.5,
               label=f'Family model (R²={r2_display:.3f})')

        ax.set_xlabel('Log P', fontsize=10)
        ax.set_ylabel('RT (min)', fontsize=10)
        ax.set_title(f'{family_name}\n(n={len(family_anchors)} anchors)', fontsize=11)
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)

    # Remove extra subplot
    if len(PREFIX_FAMILIES) < len(axes):
        fig.delaxes(axes[-1])

    plt.tight_layout()
    plt.savefig('family_performance_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Visualization saved: family_performance_analysis.png")
    plt.close()


def main():
    print("="*80)
    print("FAMILY MODEL PERFORMANCE ANALYSIS")
    print("="*80)

    # Load data
    data_path = '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/data/samples/testwork_user.csv'

    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"❌ Data file not found: {data_path}")
        return

    # Extract prefix
    df['prefix'] = df['Name'].str.extract(r'^([^(]+)')[0]

    print(f"\n📊 Dataset: testwork_user.csv")
    print(f"   Total compounds: {len(df)}")
    print(f"   Total anchors: {len(df[df['Anchor'] == 'T'])}")

    # Analyze each family
    results = []
    for family_name, family_prefixes in PREFIX_FAMILIES.items():
        result = analyze_family(df, family_name, family_prefixes)
        if result:
            results.append(result)

    # Summary comparison
    print(f"\n{'='*80}")
    print("📊 FAMILY COMPARISON SUMMARY")
    print(f"{'='*80}\n")

    if results:
        summary_df = pd.DataFrame(results)
        print(summary_df[['family_name', 'n_anchors', 'training_r2', 'validation_r2', 'status']].to_string(index=False))

        print(f"\n🎯 Success Rate:")
        success_count = (summary_df['status'] == 'PASS').sum()
        total_count = len(summary_df)
        print(f"   {success_count}/{total_count} families pass threshold (R² >= 0.70)")

        print(f"\n📈 Average Performance:")
        print(f"   Training R²: {summary_df['training_r2'].mean():.3f}")
        print(f"   Validation R²: {summary_df['validation_r2'].mean():.3f}")
        print(f"   Average overfitting gap: {(summary_df['training_r2'] - summary_df['validation_r2']).mean():.3f}")

    # Create visualization
    visualize_families(df)

    # Recommendations
    print(f"\n{'='*80}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*80}\n")

    if results:
        failed_families = [r for r in results if r['status'] == 'FAIL']

        if failed_families:
            print("⚠️  Failed Families Analysis:")
            for family in failed_families:
                print(f"\n   {family['family_name']}:")
                print(f"      - Validation R²: {family['validation_r2']:.3f}")
                print(f"      - Possible reasons:")

                if family['log_p_std'] < 1.0:
                    print(f"        • Low Log P variation (std={family['log_p_std']:.3f})")

                if family['n_anchors'] < 15:
                    print(f"        • Small sample size (n={family['n_anchors']})")

                if family['training_r2'] - family['validation_r2'] > 0.1:
                    print(f"        • Overfitting (gap={family['training_r2'] - family['validation_r2']:.3f})")

                print(f"      - Recommendation: Use overall fallback for this family")

        passed_families = [r for r in results if r['status'] == 'PASS']
        if passed_families:
            print(f"\n✅ Successful Families:")
            for family in passed_families:
                print(f"   {family['family_name']}: R²={family['validation_r2']:.3f} (n={family['n_anchors']})")

    print(f"\n{'='*80}")


if __name__ == '__main__':
    main()
