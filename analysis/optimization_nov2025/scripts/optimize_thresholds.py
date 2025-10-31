#!/usr/bin/env python3
"""
Threshold Optimization via Grid Search
Finds optimal R² thresholds for each decision level
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, BayesianRidge
from sklearn.metrics import r2_score
from sklearn.model_selection import LeaveOneOut
from itertools import product
import matplotlib.pyplot as plt
import seaborn as sns


def cross_validate_regression(X, y, use_bayesian=False):
    """Leave-One-Out Cross-Validation"""
    if len(X) < 3:
        return None

    loo = LeaveOneOut()
    predictions = []
    actuals = []

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        if use_bayesian:
            model = BayesianRidge()
        else:
            model = Ridge(alpha=1.0)

        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        predictions.append(pred[0])
        actuals.append(y_test[0])

    validation_r2 = r2_score(actuals, predictions)
    return float(validation_r2)


def simulate_algorithm(df, threshold_config, use_bayesian=False):
    """
    Simulate multi-level algorithm with given thresholds

    threshold_config = {
        'level1': 0.75,  # n≥10
        'level2': 0.70,  # n≥4
        'level3': 0.70,  # family
        'level4': 0.50   # overall
    }
    """

    results = {
        'level1_success': 0,
        'level2_success': 0,
        'level3_success': 0,
        'level4_success': 0,
        'total_accepted': 0,
        'total_rejected': 0,
        'avg_validation_r2': [],
        'false_positives': 0  # Groups accepted with val R² < 0.50
    }

    # Extract prefix
    if 'prefix' not in df.columns:
        df['prefix'] = df['Name'].str.extract(r'^([^(]+)')[0]

    prefixes = sorted(df['prefix'].unique())

    for prefix in prefixes:
        prefix_group = df[df['prefix'] == prefix]
        anchor_compounds = prefix_group[prefix_group['Anchor'] == 'T']
        n_anchors = len(anchor_compounds)

        if n_anchors < 2:
            results['level4_success'] += 1
            results['total_accepted'] += 1
            continue

        X = anchor_compounds[['Log P']].values
        y = anchor_compounds['RT'].values

        if len(np.unique(X)) < 2:
            results['level4_success'] += 1
            results['total_accepted'] += 1
            continue

        # Calculate validation R²
        validation_r2 = cross_validate_regression(X, y, use_bayesian=use_bayesian)

        if validation_r2 is None:
            results['level4_success'] += 1
            results['total_accepted'] += 1
            continue

        # Level 1: n ≥ 10
        if n_anchors >= 10:
            if validation_r2 >= threshold_config['level1']:
                results['level1_success'] += 1
                results['total_accepted'] += 1
                results['avg_validation_r2'].append(validation_r2)

                # Check for false positives
                if validation_r2 < 0.50:
                    results['false_positives'] += 1

                continue

        # Level 2: n ≥ 4
        if n_anchors >= 4:
            if validation_r2 >= threshold_config['level2']:
                results['level2_success'] += 1
                results['total_accepted'] += 1
                results['avg_validation_r2'].append(validation_r2)

                if validation_r2 < 0.50:
                    results['false_positives'] += 1

                continue

        # Level 3: n = 3 (family pooling simulation - simplified)
        if n_anchors == 3:
            # Simplified: accept if meets level3 threshold
            if validation_r2 >= threshold_config['level3']:
                results['level3_success'] += 1
                results['total_accepted'] += 1
                results['avg_validation_r2'].append(validation_r2)

                if validation_r2 < 0.50:
                    results['false_positives'] += 1

                continue
            else:
                # Fallback to level 4
                results['level4_success'] += 1
                results['total_accepted'] += 1
                continue

        # Level 4: Overall fallback
        results['level4_success'] += 1
        results['total_accepted'] += 1

    # Calculate metrics
    total_groups = len(prefixes)
    results['acceptance_rate'] = results['total_accepted'] / total_groups if total_groups > 0 else 0
    results['avg_validation_r2'] = np.mean(results['avg_validation_r2']) if results['avg_validation_r2'] else 0
    results['false_positive_rate'] = results['false_positives'] / results['total_accepted'] if results['total_accepted'] > 0 else 0

    return results


def grid_search_thresholds(df, use_bayesian=False):
    """Grid search over threshold combinations"""

    print("\n🔍 Grid Search for Optimal Thresholds...")
    print("   Testing threshold combinations...\n")

    # Define search grid
    level1_range = np.arange(0.60, 0.86, 0.05)  # 0.60 to 0.85
    level2_range = np.arange(0.55, 0.81, 0.05)  # 0.55 to 0.80
    level3_range = np.arange(0.50, 0.76, 0.05)  # 0.50 to 0.75
    level4_range = np.arange(0.40, 0.61, 0.05)  # 0.40 to 0.60

    print(f"   Search space: {len(level1_range)} × {len(level2_range)} × {len(level3_range)} × {len(level4_range)}")
    print(f"   Total combinations: {len(level1_range) * len(level2_range) * len(level3_range) * len(level4_range)}")

    best_config = None
    best_score = -np.inf
    all_results = []

    # Optimization objective: maximize acceptance rate while minimizing false positives
    for t1, t2, t3, t4 in product(level1_range, level2_range, level3_range, level4_range):
        # Constraint: thresholds should be non-increasing
        if not (t1 >= t2 >= t3 >= t4):
            continue

        threshold_config = {
            'level1': t1,
            'level2': t2,
            'level3': t3,
            'level4': t4
        }

        results = simulate_algorithm(df, threshold_config, use_bayesian=use_bayesian)

        # Composite score: maximize acceptance, minimize false positives, maximize avg R²
        score = (
            results['acceptance_rate'] * 0.4 +
            (1 - results['false_positive_rate']) * 0.4 +
            results['avg_validation_r2'] * 0.2
        )

        results['threshold_config'] = threshold_config
        results['composite_score'] = score
        all_results.append(results)

        if score > best_score:
            best_score = score
            best_config = threshold_config
            best_results = results

    print(f"   ✅ Tested {len(all_results)} valid combinations")

    return best_config, best_results, all_results


def visualize_threshold_sensitivity(all_results):
    """Visualize how thresholds affect performance"""

    results_df = pd.DataFrame(all_results)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Acceptance rate vs Level 1 threshold
    ax = axes[0, 0]
    sns.boxplot(data=results_df, x='threshold_config', y='acceptance_rate', ax=ax)
    ax.set_xlabel('Threshold Configuration', fontsize=10)
    ax.set_ylabel('Acceptance Rate', fontsize=10)
    ax.set_title('Acceptance Rate Sensitivity', fontsize=12, fontweight='bold')
    ax.tick_params(axis='x', rotation=90, labelsize=6)
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 2: False positive rate vs thresholds
    ax = axes[0, 1]
    sns.scatterplot(data=results_df, x='avg_validation_r2', y='false_positive_rate',
                   size='acceptance_rate', sizes=(20, 200), alpha=0.6, ax=ax)
    ax.set_xlabel('Average Validation R²', fontsize=10)
    ax.set_ylabel('False Positive Rate', fontsize=10)
    ax.set_title('Quality vs False Positives', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Plot 3: Composite score distribution
    ax = axes[1, 0]
    ax.hist(results_df['composite_score'], bins=30, alpha=0.7, color='steelblue', edgecolor='black')
    ax.axvline(results_df['composite_score'].max(), color='red', linestyle='--',
              linewidth=2, label=f'Best: {results_df["composite_score"].max():.3f}')
    ax.set_xlabel('Composite Score', fontsize=10)
    ax.set_ylabel('Frequency', fontsize=10)
    ax.set_title('Score Distribution', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 4: Level usage with best config
    ax = axes[1, 1]
    best_result = results_df.loc[results_df['composite_score'].idxmax()]
    level_usage = [
        best_result['level1_success'],
        best_result['level2_success'],
        best_result['level3_success'],
        best_result['level4_success']
    ]
    colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']
    ax.bar(['Level 1\n(n≥10)', 'Level 2\n(n≥4)', 'Level 3\n(n=3)', 'Level 4\n(fallback)'],
          level_usage, color=colors, alpha=0.7, edgecolor='black')
    ax.set_ylabel('Number of Groups', fontsize=10)
    ax.set_title('Best Configuration: Level Usage', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig('threshold_optimization.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Visualization saved: threshold_optimization.png")
    plt.close()


def main():
    print("="*80)
    print("THRESHOLD OPTIMIZATION VIA GRID SEARCH")
    print("="*80)

    # Load data
    data_path = '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/data/samples/testwork_user.csv'

    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"❌ Data file not found: {data_path}")
        return

    df['prefix'] = df['Name'].str.extract(r'^([^(]+)')[0]

    print(f"\n📊 Dataset: testwork_user.csv")
    print(f"   Total compounds: {len(df)}")
    print(f"   Total anchors: {len(df[df['Anchor'] == 'T'])}")
    print(f"   Unique prefixes: {df['prefix'].nunique()}")

    # Current thresholds
    current_config = {
        'level1': 0.75,
        'level2': 0.70,
        'level3': 0.70,
        'level4': 0.50
    }

    print(f"\n📋 Current Thresholds:")
    print(f"   Level 1 (n≥10): {current_config['level1']}")
    print(f"   Level 2 (n≥4):  {current_config['level2']}")
    print(f"   Level 3 (n=3):  {current_config['level3']}")
    print(f"   Level 4 (all):  {current_config['level4']}")

    # Test with Ridge
    print(f"\n{'='*80}")
    print("🔧 OPTIMIZATION WITH RIDGE REGRESSION")
    print(f"{'='*80}")

    current_results_ridge = simulate_algorithm(df, current_config, use_bayesian=False)
    best_config_ridge, best_results_ridge, all_results_ridge = grid_search_thresholds(df, use_bayesian=False)

    # Test with Bayesian Ridge
    print(f"\n{'='*80}")
    print("🔧 OPTIMIZATION WITH BAYESIAN RIDGE")
    print(f"{'='*80}")

    current_results_bayes = simulate_algorithm(df, current_config, use_bayesian=True)
    best_config_bayes, best_results_bayes, all_results_bayes = grid_search_thresholds(df, use_bayesian=True)

    # Comparison
    print(f"\n{'='*80}")
    print("📊 RESULTS COMPARISON")
    print(f"{'='*80}\n")

    print("🔵 RIDGE REGRESSION:")
    print(f"\n   Current Configuration:")
    print(f"      Acceptance rate: {current_results_ridge['acceptance_rate']*100:.1f}%")
    print(f"      False positive rate: {current_results_ridge['false_positive_rate']*100:.1f}%")
    print(f"      Avg validation R²: {current_results_ridge['avg_validation_r2']:.3f}")
    print(f"      Composite score: {current_results_ridge['acceptance_rate']*0.4 + (1-current_results_ridge['false_positive_rate'])*0.4 + current_results_ridge['avg_validation_r2']*0.2:.3f}")

    print(f"\n   Optimized Configuration:")
    print(f"      Level 1: {best_config_ridge['level1']:.2f}")
    print(f"      Level 2: {best_config_ridge['level2']:.2f}")
    print(f"      Level 3: {best_config_ridge['level3']:.2f}")
    print(f"      Level 4: {best_config_ridge['level4']:.2f}")
    print(f"      Acceptance rate: {best_results_ridge['acceptance_rate']*100:.1f}%")
    print(f"      False positive rate: {best_results_ridge['false_positive_rate']*100:.1f}%")
    print(f"      Avg validation R²: {best_results_ridge['avg_validation_r2']:.3f}")
    print(f"      Composite score: {best_results_ridge['composite_score']:.3f}")

    print(f"\n🟢 BAYESIAN RIDGE:")
    print(f"\n   Current Configuration:")
    print(f"      Acceptance rate: {current_results_bayes['acceptance_rate']*100:.1f}%")
    print(f"      False positive rate: {current_results_bayes['false_positive_rate']*100:.1f}%")
    print(f"      Avg validation R²: {current_results_bayes['avg_validation_r2']:.3f}")
    print(f"      Composite score: {current_results_bayes['acceptance_rate']*0.4 + (1-current_results_bayes['false_positive_rate'])*0.4 + current_results_bayes['avg_validation_r2']*0.2:.3f}")

    print(f"\n   Optimized Configuration:")
    print(f"      Level 1: {best_config_bayes['level1']:.2f}")
    print(f"      Level 2: {best_config_bayes['level2']:.2f}")
    print(f"      Level 3: {best_config_bayes['level3']:.2f}")
    print(f"      Level 4: {best_config_bayes['level4']:.2f}")
    print(f"      Acceptance rate: {best_results_bayes['acceptance_rate']*100:.1f}%")
    print(f"      False positive rate: {best_results_bayes['false_positive_rate']*100:.1f}%")
    print(f"      Avg validation R²: {best_results_bayes['avg_validation_r2']:.3f}")
    print(f"      Composite score: {best_results_bayes['composite_score']:.3f}")

    # Visualize
    visualize_threshold_sensitivity(all_results_bayes)

    # Recommendations
    print(f"\n{'='*80}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*80}\n")

    if best_results_bayes['composite_score'] > best_results_ridge['composite_score']:
        print(f"✅ Use Bayesian Ridge with optimized thresholds:")
        print(f"   Level 1 (n≥10): {best_config_bayes['level1']:.2f}")
        print(f"   Level 2 (n≥4):  {best_config_bayes['level2']:.2f}")
        print(f"   Level 3 (n=3):  {best_config_bayes['level3']:.2f}")
        print(f"   Level 4 (all):  {best_config_bayes['level4']:.2f}")
        print(f"\n   Expected performance:")
        print(f"      ✅ {best_results_bayes['acceptance_rate']*100:.1f}% acceptance rate")
        print(f"      ✅ {best_results_bayes['false_positive_rate']*100:.1f}% false positive rate")
        print(f"      ✅ {best_results_bayes['avg_validation_r2']:.3f} average R²")
    else:
        print(f"✅ Use Ridge with optimized thresholds:")
        print(f"   Level 1 (n≥10): {best_config_ridge['level1']:.2f}")
        print(f"   Level 2 (n≥4):  {best_config_ridge['level2']:.2f}")
        print(f"   Level 3 (n=3):  {best_config_ridge['level3']:.2f}")
        print(f"   Level 4 (all):  {best_config_ridge['level4']:.2f}")

    print(f"\n{'='*80}")


if __name__ == '__main__':
    main()
