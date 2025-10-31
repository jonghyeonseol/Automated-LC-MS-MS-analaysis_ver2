#!/usr/bin/env python3
"""
Bayesian Ridge vs Ridge Regression Comparison
Tests if Bayesian Ridge provides better uncertainty quantification and performance
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, BayesianRidge
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.model_selection import LeaveOneOut
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


def cross_validate_model(X, y, model_class, **model_params):
    """Leave-One-Out Cross-Validation with specified model"""
    if len(X) < 3:
        return None, None, None

    loo = LeaveOneOut()
    predictions = []
    actuals = []
    std_predictions = []  # For Bayesian Ridge uncertainty

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = model_class(**model_params)
        model.fit(X_train, y_train)

        if isinstance(model, BayesianRidge):
            pred, std = model.predict(X_test, return_std=True)
            std_predictions.append(std[0])
        else:
            pred = model.predict(X_test)
            std_predictions.append(None)

        predictions.append(pred[0])
        actuals.append(y_test[0])

    validation_r2 = r2_score(actuals, predictions)
    mae = mean_absolute_error(actuals, predictions)
    rmse = np.sqrt(mean_squared_error(actuals, predictions))

    return validation_r2, mae, rmse, std_predictions


def compare_models_for_prefix(df, prefix):
    """Compare Ridge vs Bayesian Ridge for a single prefix group"""

    prefix_group = df[df['prefix'] == prefix]
    anchor_compounds = prefix_group[prefix_group['Anchor'] == 'T']

    n_anchors = len(anchor_compounds)

    if n_anchors < 3:
        return None

    X = anchor_compounds[['Log P']].values
    y = anchor_compounds['RT'].values

    if len(np.unique(X)) < 2:
        return None

    # Ridge Regression
    ridge_val_r2, ridge_mae, ridge_rmse, _ = cross_validate_model(
        X, y, Ridge, alpha=1.0
    )

    # Bayesian Ridge
    bayes_val_r2, bayes_mae, bayes_rmse, bayes_std = cross_validate_model(
        X, y, BayesianRidge
    )

    # Fit full models for coefficient comparison
    ridge_model = Ridge(alpha=1.0)
    ridge_model.fit(X, y)
    ridge_train_r2 = r2_score(y, ridge_model.predict(X))

    bayes_model = BayesianRidge()
    bayes_model.fit(X, y)
    bayes_train_r2 = r2_score(y, bayes_model.predict(X))

    # Get Bayesian Ridge hyperparameters
    alpha_learned = bayes_model.alpha_
    lambda_learned = bayes_model.lambda_

    return {
        'prefix': prefix,
        'n_anchors': n_anchors,
        'ridge_train_r2': ridge_train_r2,
        'ridge_val_r2': ridge_val_r2,
        'ridge_mae': ridge_mae,
        'ridge_rmse': ridge_rmse,
        'bayes_train_r2': bayes_train_r2,
        'bayes_val_r2': bayes_val_r2,
        'bayes_mae': bayes_mae,
        'bayes_rmse': bayes_rmse,
        'bayes_alpha': alpha_learned,
        'bayes_lambda': lambda_learned,
        'avg_uncertainty': np.mean([s for s in bayes_std if s is not None]) if any(bayes_std) else None
    }


def visualize_comparison(results_df):
    """Create visualizations comparing Ridge vs Bayesian Ridge"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Validation R² comparison
    ax = axes[0, 0]
    x = np.arange(len(results_df))
    width = 0.35

    ax.bar(x - width/2, results_df['ridge_val_r2'], width, label='Ridge', alpha=0.8, color='steelblue')
    ax.bar(x + width/2, results_df['bayes_val_r2'], width, label='Bayesian Ridge', alpha=0.8, color='coral')

    ax.set_xlabel('Prefix Group', fontsize=10)
    ax.set_ylabel('Validation R²', fontsize=10)
    ax.set_title('Validation R² Comparison', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(results_df['prefix'], rotation=45, ha='right', fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0.70, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Threshold')

    # Plot 2: MAE comparison
    ax = axes[0, 1]
    ax.bar(x - width/2, results_df['ridge_mae'], width, label='Ridge', alpha=0.8, color='steelblue')
    ax.bar(x + width/2, results_df['bayes_mae'], width, label='Bayesian Ridge', alpha=0.8, color='coral')

    ax.set_xlabel('Prefix Group', fontsize=10)
    ax.set_ylabel('Mean Absolute Error (min)', fontsize=10)
    ax.set_title('Prediction Error Comparison', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(results_df['prefix'], rotation=45, ha='right', fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 3: Overfitting gap comparison
    ax = axes[1, 0]
    ridge_gap = results_df['ridge_train_r2'] - results_df['ridge_val_r2']
    bayes_gap = results_df['bayes_train_r2'] - results_df['bayes_val_r2']

    ax.bar(x - width/2, ridge_gap, width, label='Ridge', alpha=0.8, color='steelblue')
    ax.bar(x + width/2, bayes_gap, width, label='Bayesian Ridge', alpha=0.8, color='coral')

    ax.set_xlabel('Prefix Group', fontsize=10)
    ax.set_ylabel('Overfitting Gap (Train R² - Val R²)', fontsize=10)
    ax.set_title('Overfitting Comparison', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(results_df['prefix'], rotation=45, ha='right', fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 4: Learned regularization (Bayesian Ridge)
    ax = axes[1, 1]
    ax.scatter(results_df['n_anchors'], results_df['bayes_alpha'],
              s=100, alpha=0.6, color='coral', label='Alpha (precision)')
    ax.set_xlabel('Number of Anchors', fontsize=10)
    ax.set_ylabel('Learned Alpha (log scale)', fontsize=10)
    ax.set_yscale('log')
    ax.set_title('Bayesian Ridge: Learned Regularization', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Add uncertainty bars if available
    if 'avg_uncertainty' in results_df.columns and results_df['avg_uncertainty'].notna().any():
        ax2 = ax.twinx()
        ax2.scatter(results_df['n_anchors'], results_df['avg_uncertainty'],
                   s=100, alpha=0.6, color='purple', marker='s', label='Avg Uncertainty')
        ax2.set_ylabel('Average Prediction Uncertainty', fontsize=10, color='purple')
        ax2.tick_params(axis='y', labelcolor='purple')

    plt.tight_layout()
    plt.savefig('bayesian_ridge_comparison.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Visualization saved: bayesian_ridge_comparison.png")
    plt.close()


def main():
    print("="*80)
    print("BAYESIAN RIDGE vs RIDGE REGRESSION COMPARISON")
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

    # Get unique prefixes with sufficient anchors
    prefixes = []
    for prefix in sorted(df['prefix'].unique()):
        prefix_anchors = df[(df['prefix'] == prefix) & (df['Anchor'] == 'T')]
        if len(prefix_anchors) >= 3:
            prefixes.append(prefix)

    print(f"\n📋 Testing {len(prefixes)} prefix groups with n≥3 anchors")

    # Compare models for each prefix
    results = []
    for prefix in prefixes:
        print(f"\n🔬 Analyzing {prefix}...")
        result = compare_models_for_prefix(df, prefix)
        if result:
            results.append(result)

            print(f"   Ridge:          Val R²={result['ridge_val_r2']:.3f}, MAE={result['ridge_mae']:.3f}")
            print(f"   Bayesian Ridge: Val R²={result['bayes_val_r2']:.3f}, MAE={result['bayes_mae']:.3f}")
            print(f"   Bayesian alpha: {result['bayes_alpha']:.2e} (learned regularization)")

            if result['avg_uncertainty']:
                print(f"   Avg uncertainty: ±{result['avg_uncertainty']:.3f} min")

    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY COMPARISON")
    print(f"{'='*80}\n")

    if results:
        results_df = pd.DataFrame(results)

        print("📈 Average Performance:")
        print(f"   Ridge          - Val R²: {results_df['ridge_val_r2'].mean():.3f}, MAE: {results_df['ridge_mae'].mean():.3f}")
        print(f"   Bayesian Ridge - Val R²: {results_df['bayes_val_r2'].mean():.3f}, MAE: {results_df['bayes_mae'].mean():.3f}")

        print(f"\n📊 Overfitting:")
        ridge_gap = (results_df['ridge_train_r2'] - results_df['ridge_val_r2']).mean()
        bayes_gap = (results_df['bayes_train_r2'] - results_df['bayes_val_r2']).mean()
        print(f"   Ridge gap:          {ridge_gap:.3f}")
        print(f"   Bayesian Ridge gap: {bayes_gap:.3f}")

        # Win/loss comparison
        bayes_wins = (results_df['bayes_val_r2'] > results_df['ridge_val_r2']).sum()
        ridge_wins = (results_df['ridge_val_r2'] > results_df['bayes_val_r2']).sum()
        ties = (results_df['ridge_val_r2'] == results_df['bayes_val_r2']).sum()

        print(f"\n🏆 Head-to-Head (Validation R²):")
        print(f"   Bayesian Ridge wins: {bayes_wins}/{len(results_df)}")
        print(f"   Ridge wins:          {ridge_wins}/{len(results_df)}")
        print(f"   Ties:                {ties}/{len(results_df)}")

        # Statistical test
        from scipy.stats import wilcoxon
        if len(results_df) >= 6:
            stat, p_value = wilcoxon(results_df['ridge_val_r2'], results_df['bayes_val_r2'])
            print(f"\n📊 Wilcoxon Signed-Rank Test:")
            print(f"   p-value: {p_value:.4f}")
            if p_value < 0.05:
                print(f"   ✅ Statistically significant difference (α=0.05)")
            else:
                print(f"   ⚠️  No significant difference (α=0.05)")

        # Detailed table
        print(f"\n📋 Detailed Results:")
        display_df = results_df[['prefix', 'n_anchors', 'ridge_val_r2', 'bayes_val_r2', 'ridge_mae', 'bayes_mae']]
        display_df.columns = ['Prefix', 'n', 'Ridge R²', 'Bayes R²', 'Ridge MAE', 'Bayes MAE']
        print(display_df.to_string(index=False, float_format='%.3f'))

        # Create visualization
        visualize_comparison(results_df)

    # Recommendations
    print(f"\n{'='*80}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*80}\n")

    if results:
        results_df = pd.DataFrame(results)

        if results_df['bayes_val_r2'].mean() > results_df['ridge_val_r2'].mean():
            improvement = (results_df['bayes_val_r2'].mean() - results_df['ridge_val_r2'].mean()) * 100
            print(f"✅ Bayesian Ridge shows improvement: +{improvement:.1f}% average R²")
            print(f"   Recommendation: Consider switching to Bayesian Ridge")
        else:
            print(f"⚠️  Ridge performs similarly or better than Bayesian Ridge")
            print(f"   Recommendation: Keep current Ridge implementation")

        print(f"\n🎯 Bayesian Ridge Benefits:")
        print(f"   ✅ Automatic regularization (no manual alpha tuning)")
        print(f"   ✅ Uncertainty quantification (prediction intervals)")
        print(f"   ✅ May be more robust with small samples")

        print(f"\n⚠️  Bayesian Ridge Drawbacks:")
        print(f"   ⚠️  Slower computation (iterative optimization)")
        print(f"   ⚠️  More complex to explain to domain experts")

    print(f"\n{'='*80}")


if __name__ == '__main__':
    main()
