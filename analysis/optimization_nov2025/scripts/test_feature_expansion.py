#!/usr/bin/env python3
"""
Feature Expansion Testing
Compare univariate (Log P only) vs multivariate regression
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge, BayesianRidge
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import LeaveOneOut
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt


def extract_features(df):
    """Extract features from compound names"""

    # Parse compound name: PREFIX(a:b;c)
    df['a_component'] = df['Name'].str.extract(r'\((\d+):')[0].astype(float)  # Carbon length
    df['b_component'] = df['Name'].str.extract(r':(\d+);')[0].astype(float)  # Unsaturation
    df['c_component'] = df['Name'].str.extract(r';O(\d+)\)')[0].astype(float)  # Oxygen

    # Modifications
    df['has_OAc'] = df['Name'].str.contains(r'\+OAc', regex=True).astype(int)
    df['has_dHex'] = df['Name'].str.contains(r'\+dHex', regex=True).astype(int)
    df['has_HexNAc'] = df['Name'].str.contains(r'\+HexNAc', regex=True).astype(int)

    # Sialic acid count (from prefix letter)
    sialic_map = {'M': 1, 'D': 2, 'T': 3, 'Q': 4, 'P': 5}
    df['sialic_acids'] = df['prefix'].str.extract(r'G([MDTQP])')[0].map(sialic_map)

    return df


def cross_validate_model(X, y, use_bayesian=False, standardize=False):
    """Leave-One-Out Cross-Validation"""
    if len(X) < 3:
        return None, None

    loo = LeaveOneOut()
    predictions = []
    actuals = []

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        # Standardize if requested
        if standardize and X_train.shape[1] > 1:
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)

        if use_bayesian:
            model = BayesianRidge()
        else:
            model = Ridge(alpha=1.0)

        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        predictions.append(pred[0])
        actuals.append(y_test[0])

    validation_r2 = r2_score(actuals, predictions)
    mae = mean_absolute_error(actuals, predictions)

    return validation_r2, mae


def test_feature_combinations(df, prefix):
    """Test different feature combinations for a prefix group"""

    prefix_group = df[df['prefix'] == prefix]
    anchor_compounds = prefix_group[prefix_group['Anchor'] == 'T']

    n_anchors = len(anchor_compounds)

    if n_anchors < 3:
        return None

    y = anchor_compounds['RT'].values

    # Feature combination 1: Log P only (current)
    X1 = anchor_compounds[['Log P']].values

    # Feature combination 2: Log P + Carbon length
    features_available = ['Log P', 'a_component']
    X2 = anchor_compounds[features_available].dropna()
    y2 = anchor_compounds.loc[X2.index, 'RT'].values
    X2 = X2.values

    # Feature combination 3: Log P + Carbon + Unsaturation
    features_available = ['Log P', 'a_component', 'b_component']
    X3 = anchor_compounds[features_available].dropna()
    y3 = anchor_compounds.loc[X3.index, 'RT'].values
    X3 = X3.values

    # Feature combination 4: All chemical features
    features_available = ['Log P', 'a_component', 'b_component', 'has_OAc', 'has_dHex', 'has_HexNAc']
    X4 = anchor_compounds[features_available].dropna()
    y4 = anchor_compounds.loc[X4.index, 'RT'].values
    X4 = X4.values

    results = {
        'prefix': prefix,
        'n_anchors': n_anchors
    }

    # Test each combination with Ridge
    if len(np.unique(X1[:, 0])) >= 2:
        val_r2, mae = cross_validate_model(X1, y, use_bayesian=False)
        results['ridge_1feat_r2'] = val_r2
        results['ridge_1feat_mae'] = mae

    if X2.shape[0] >= 3 and len(np.unique(X2[:, 0])) >= 2:
        val_r2, mae = cross_validate_model(X2, y2, use_bayesian=False, standardize=True)
        results['ridge_2feat_r2'] = val_r2
        results['ridge_2feat_mae'] = mae

    if X3.shape[0] >= 3 and len(np.unique(X3[:, 0])) >= 2:
        val_r2, mae = cross_validate_model(X3, y3, use_bayesian=False, standardize=True)
        results['ridge_3feat_r2'] = val_r2
        results['ridge_3feat_mae'] = mae

    if X4.shape[0] >= 3 and len(np.unique(X4[:, 0])) >= 2:
        val_r2, mae = cross_validate_model(X4, y4, use_bayesian=False, standardize=True)
        results['ridge_allfeat_r2'] = val_r2
        results['ridge_allfeat_mae'] = mae

    # Test with Bayesian Ridge
    if len(np.unique(X1[:, 0])) >= 2:
        val_r2, mae = cross_validate_model(X1, y, use_bayesian=True)
        results['bayes_1feat_r2'] = val_r2
        results['bayes_1feat_mae'] = mae

    if X2.shape[0] >= 3 and len(np.unique(X2[:, 0])) >= 2:
        val_r2, mae = cross_validate_model(X2, y2, use_bayesian=True, standardize=True)
        results['bayes_2feat_r2'] = val_r2
        results['bayes_2feat_mae'] = mae

    if X3.shape[0] >= 3 and len(np.unique(X3[:, 0])) >= 2:
        val_r2, mae = cross_validate_model(X3, y3, use_bayesian=True, standardize=True)
        results['bayes_3feat_r2'] = val_r2
        results['bayes_3feat_mae'] = mae

    if X4.shape[0] >= 3 and len(np.unique(X4[:, 0])) >= 2:
        val_r2, mae = cross_validate_model(X4, y4, use_bayesian=True, standardize=True)
        results['bayes_allfeat_r2'] = val_r2
        results['bayes_allfeat_mae'] = mae

    return results


def visualize_feature_comparison(results_df):
    """Visualize feature expansion results"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Ridge - R² by feature count
    ax = axes[0, 0]
    feature_cols = ['ridge_1feat_r2', 'ridge_2feat_r2', 'ridge_3feat_r2', 'ridge_allfeat_r2']
    feature_labels = ['Log P\nonly', 'Log P +\nCarbon', 'Log P + Carbon\n+ Unsat', 'All\nFeatures']

    for idx, prefix in enumerate(results_df['prefix']):
        values = [results_df.loc[idx, col] for col in feature_cols if col in results_df.columns]
        x_vals = list(range(len(values)))
        ax.plot(x_vals, values, marker='o', alpha=0.6, label=prefix)

    ax.set_xlabel('Feature Combination', fontsize=10)
    ax.set_ylabel('Validation R²', fontsize=10)
    ax.set_title('Ridge: Feature Expansion Effect', fontsize=12, fontweight='bold')
    ax.set_xticks(range(4))
    ax.set_xticklabels(feature_labels, fontsize=8)
    ax.legend(fontsize=7, ncol=2, loc='best')
    ax.grid(True, alpha=0.3)

    # Plot 2: Bayesian Ridge - R² by feature count
    ax = axes[0, 1]
    feature_cols = ['bayes_1feat_r2', 'bayes_2feat_r2', 'bayes_3feat_r2', 'bayes_allfeat_r2']

    for idx, prefix in enumerate(results_df['prefix']):
        values = [results_df.loc[idx, col] for col in feature_cols if col in results_df.columns]
        x_vals = list(range(len(values)))
        ax.plot(x_vals, values, marker='o', alpha=0.6, label=prefix)

    ax.set_xlabel('Feature Combination', fontsize=10)
    ax.set_ylabel('Validation R²', fontsize=10)
    ax.set_title('Bayesian Ridge: Feature Expansion Effect', fontsize=12, fontweight='bold')
    ax.set_xticks(range(4))
    ax.set_xticklabels(feature_labels, fontsize=8)
    ax.legend(fontsize=7, ncol=2, loc='best')
    ax.grid(True, alpha=0.3)

    # Plot 3: Average improvement
    ax = axes[1, 0]

    ridge_avg = []
    bayes_avg = []
    for feat_idx in range(1, 5):
        ridge_col = f'ridge_{["1feat", "2feat", "3feat", "allfeat"][feat_idx-1]}_r2'
        bayes_col = f'bayes_{["1feat", "2feat", "3feat", "allfeat"][feat_idx-1]}_r2'

        if ridge_col in results_df.columns:
            ridge_avg.append(results_df[ridge_col].mean())
        if bayes_col in results_df.columns:
            bayes_avg.append(results_df[bayes_col].mean())

    x = np.arange(len(ridge_avg))
    width = 0.35

    ax.bar(x - width/2, ridge_avg, width, label='Ridge', alpha=0.8, color='steelblue')
    ax.bar(x + width/2, bayes_avg, width, label='Bayesian', alpha=0.8, color='coral')

    ax.set_xlabel('Feature Combination', fontsize=10)
    ax.set_ylabel('Average Validation R²', fontsize=10)
    ax.set_title('Average Performance by Feature Count', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(feature_labels, fontsize=8)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 4: Sample size vs benefit
    ax = axes[1, 1]

    if 'ridge_1feat_r2' in results_df.columns and 'ridge_allfeat_r2' in results_df.columns:
        improvement = results_df['ridge_allfeat_r2'] - results_df['ridge_1feat_r2']
        ax.scatter(results_df['n_anchors'], improvement, s=100, alpha=0.6, color='steelblue', label='Ridge')

    if 'bayes_1feat_r2' in results_df.columns and 'bayes_allfeat_r2' in results_df.columns:
        improvement = results_df['bayes_allfeat_r2'] - results_df['bayes_1feat_r2']
        ax.scatter(results_df['n_anchors'], improvement, s=100, alpha=0.6, color='coral', label='Bayesian')

    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('Number of Anchors', fontsize=10)
    ax.set_ylabel('R² Improvement\n(All Features - Log P only)', fontsize=10)
    ax.set_title('Benefit of Feature Expansion by Sample Size', fontsize=12, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('feature_expansion_analysis.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Visualization saved: feature_expansion_analysis.png")
    plt.close()


def main():
    print("="*80)
    print("FEATURE EXPANSION ANALYSIS")
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

    # Extract features
    df = extract_features(df)

    print(f"\n📊 Dataset: testwork_user.csv")
    print(f"   Total compounds: {len(df)}")
    print(f"   Total anchors: {len(df[df['Anchor'] == 'T'])}")

    print(f"\n📋 Available Features:")
    print(f"   ✅ Log P (lipophilicity)")
    print(f"   ✅ Carbon length (a_component)")
    print(f"   ✅ Unsaturation (b_component)")
    print(f"   ✅ Modifications (OAc, dHex, HexNAc)")
    print(f"   ✅ Sialic acid count")

    # Get prefixes with sufficient data
    prefixes = []
    for prefix in sorted(df['prefix'].unique()):
        prefix_anchors = df[(df['prefix'] == prefix) & (df['Anchor'] == 'T')]
        if len(prefix_anchors) >= 3:
            prefixes.append(prefix)

    print(f"\n📋 Testing {len(prefixes)} prefix groups")

    # Test feature combinations
    results = []
    for prefix in prefixes:
        print(f"\n🔬 Analyzing {prefix}...")
        result = test_feature_combinations(df, prefix)
        if result:
            results.append(result)

            print(f"   Ridge (Log P only):      R²={result.get('ridge_1feat_r2', 0):.3f}")
            print(f"   Ridge (All features):    R²={result.get('ridge_allfeat_r2', 0):.3f}")
            print(f"   Bayesian (Log P only):   R²={result.get('bayes_1feat_r2', 0):.3f}")
            print(f"   Bayesian (All features): R²={result.get('bayes_allfeat_r2', 0):.3f}")

    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print(f"{'='*80}\n")

    if results:
        results_df = pd.DataFrame(results)

        print("📈 Average R² by Feature Combination:")

        for model_prefix in ['ridge', 'bayes']:
            print(f"\n   {model_prefix.upper()}:")
            for feat_idx, feat_name in enumerate(['1feat', '2feat', '3feat', 'allfeat']):
                col = f'{model_prefix}_{feat_name}_r2'
                if col in results_df.columns:
                    avg_r2 = results_df[col].mean()
                    print(f"      {feat_name}: {avg_r2:.3f}")

        # Improvement analysis
        print(f"\n📊 Feature Expansion Benefit:")

        ridge_improvement = results_df['ridge_allfeat_r2'].mean() - results_df['ridge_1feat_r2'].mean() if 'ridge_allfeat_r2' in results_df.columns else 0
        bayes_improvement = results_df['bayes_allfeat_r2'].mean() - results_df['bayes_1feat_r2'].mean() if 'bayes_allfeat_r2' in results_df.columns else 0

        print(f"   Ridge:    {ridge_improvement:+.3f} (All features - Log P only)")
        print(f"   Bayesian: {bayes_improvement:+.3f} (All features - Log P only)")

        # Visualize
        visualize_feature_comparison(results_df)

    # Recommendations
    print(f"\n{'='*80}")
    print("💡 RECOMMENDATIONS")
    print(f"{'='*80}\n")

    if results:
        if bayes_improvement > 0.05:
            print(f"✅ Feature expansion beneficial with Bayesian Ridge:")
            print(f"   - Use all available features (Log P + Carbon + Unsaturation + Modifications)")
            print(f"   - Expected improvement: +{bayes_improvement:.3f} R²")
        elif abs(bayes_improvement) < 0.05:
            print(f"⚠️  Feature expansion shows minimal benefit:")
            print(f"   - Keep Log P only (simpler, more interpretable)")
            print(f"   - Additional features don't improve prediction significantly")
        else:
            print(f"❌ Feature expansion harmful (overfitting with small samples):")
            print(f"   - Stick to Log P only")
            print(f"   - More features = more overfitting with n<10")

        print(f"\n🎯 Key Insight:")
        if results_df['n_anchors'].mean() < 10:
            print(f"   ⚠️  Average sample size: {results_df['n_anchors'].mean():.1f} anchors")
            print(f"   → Too small for multivariate regression")
            print(f"   → Bayesian Ridge with Log P only is safest choice")

    print(f"\n{'='*80}")


if __name__ == '__main__':
    main()
