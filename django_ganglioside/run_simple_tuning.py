#!/usr/bin/env python
"""
Simple Auto-Tuning Script
Uses the standalone validator directly without Django complexity

This is a pragmatic approach to get R² ≥ 0.90 quickly
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.model_selection import KFold, LeaveOneOut
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import re
import json
from datetime import datetime


def preprocess_data(df):
    """Extract prefix and detect modifications"""
    def extract_prefix(name):
        match = re.match(r'^([A-Z]+\d+)', str(name))
        return match.group(1) if match else 'Unknown'

    def detect_modification(name):
        modifications = ['HexNAc', 'dHex', 'OAc', 'NeuAc', 'NeuGc']
        return any(f'+{mod}' in str(name) for mod in modifications)

    df['prefix'] = df['Name'].apply(extract_prefix)
    df['is_modified'] = df['Name'].apply(detect_modification)
    return df


def validate_loo(df, separate_modified=False, use_ridge=False, ridge_alpha=1.0):
    """Leave-One-Out validation with configuration"""
    anchors = df[df['Anchor'] == 'T'].copy()
    non_anchors = df[df['Anchor'] == 'F'].copy()

    n_anchors = len(anchors)
    if n_anchors < 2:
        return {'error': 'Need at least 2 anchors'}

    predictions = []
    actuals = []

    for idx in range(n_anchors):
        test_anchor = anchors.iloc[[idx]].copy()
        train_anchors = anchors.drop(anchors.index[idx]).copy()
        train_df = pd.concat([train_anchors, non_anchors]).reset_index(drop=True)

        # Get test values
        test_rt = test_anchor.iloc[0]['RT']
        test_log_p = test_anchor.iloc[0]['Log P']
        test_prefix = test_anchor.iloc[0]['prefix']
        test_is_modified = test_anchor.iloc[0]['is_modified']

        # Build models per prefix (optionally separated by modification)
        if separate_modified:
            # Separate models for modified vs unmodified
            train_subset = train_df[train_df['is_modified'] == test_is_modified]
        else:
            train_subset = train_df

        prefix_data = train_subset[
            (train_subset['prefix'] == test_prefix) &
            (train_subset['Anchor'] == 'T')
        ]

        if len(prefix_data) >= 2:
            X = prefix_data[['Log P']].values
            y = prefix_data['RT'].values

            if use_ridge:
                model = Ridge(alpha=ridge_alpha)
            else:
                model = LinearRegression()

            model.fit(X, y)
            predicted_rt = model.predict([[test_log_p]])[0]

            predictions.append(predicted_rt)
            actuals.append(test_rt)

    if not predictions:
        return {'error': 'No predictions made'}

    predictions = np.array(predictions)
    actuals = np.array(actuals)

    return {
        'r2': float(r2_score(actuals, predictions)),
        'rmse': float(np.sqrt(mean_squared_error(actuals, predictions))),
        'mae': float(mean_absolute_error(actuals, predictions)),
        'n_predictions': len(predictions)
    }


def validate_kfold(df, n_splits=5, separate_modified=False, use_ridge=False, ridge_alpha=1.0):
    """K-Fold validation with configuration"""
    anchors = df[df['Anchor'] == 'T'].copy()
    non_anchors = df[df['Anchor'] == 'F'].copy()

    if len(anchors) < n_splits:
        return validate_loo(df, separate_modified, use_ridge, ridge_alpha)

    kfold = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_results = []

    for fold_idx, (train_idx, test_idx) in enumerate(kfold.split(anchors), 1):
        anchors_train = anchors.iloc[train_idx].copy()
        anchors_test = anchors.iloc[test_idx].copy()

        train_df = pd.concat([anchors_train, non_anchors]).reset_index(drop=True)

        # Train metrics
        train_actuals = []
        train_predictions = []

        for _, row in anchors_train.iterrows():
            others = anchors_train[anchors_train.index != row.name]
            if separate_modified:
                others = others[others['is_modified'] == row['is_modified']]

            prefix_data = others[others['prefix'] == row['prefix']]

            if len(prefix_data) >= 2:
                X = prefix_data[['Log P']].values
                y = prefix_data['RT'].values

                model = Ridge(alpha=ridge_alpha) if use_ridge else LinearRegression()
                model.fit(X, y)

                pred = model.predict([[row['Log P']]])[0]
                train_actuals.append(row['RT'])
                train_predictions.append(pred)

        # Test metrics
        test_actuals = []
        test_predictions = []

        for _, test_row in anchors_test.iterrows():
            if separate_modified:
                train_subset = anchors_train[anchors_train['is_modified'] == test_row['is_modified']]
            else:
                train_subset = anchors_train

            prefix_data = train_subset[train_subset['prefix'] == test_row['prefix']]

            if len(prefix_data) >= 2:
                X = prefix_data[['Log P']].values
                y = prefix_data['RT'].values

                model = Ridge(alpha=ridge_alpha) if use_ridge else LinearRegression()
                model.fit(X, y)

                pred = model.predict([[test_row['Log P']]])[0]
                test_actuals.append(test_row['RT'])
                test_predictions.append(pred)

        if train_actuals and test_actuals:
            r2_train = r2_score(train_actuals, train_predictions)
            r2_test = r2_score(test_actuals, test_predictions)

            fold_results.append({
                'r2_train': r2_train,
                'r2_test': r2_test,
                'rmse_test': np.sqrt(mean_squared_error(test_actuals, test_predictions)),
                'overfitting': r2_train - r2_test
            })

    if not fold_results:
        return {'error': 'No valid folds'}

    return {
        'mean_r2_train': float(np.mean([f['r2_train'] for f in fold_results])),
        'mean_r2_test': float(np.mean([f['r2_test'] for f in fold_results])),
        'std_r2_test': float(np.std([f['r2_test'] for f in fold_results])),
        'mean_rmse_test': float(np.mean([f['rmse_test'] for f in fold_results])),
        'mean_overfitting': float(np.mean([f['overfitting'] for f in fold_results])),
        'n_folds': len(fold_results)
    }


def main():
    print("="*80)
    print("SIMPLE AUTO-TUNING")
    print("="*80)

    # Load data
    data_file = '../data/samples/testwork_user.csv'
    print(f"\nLoading: {data_file}")
    df = pd.read_csv(data_file)
    df = preprocess_data(df)

    print(f"✅ Loaded {len(df)} compounds ({len(df[df['Anchor']=='T'])} anchors)")
    print(f"   Modified compounds: {len(df[df['is_modified']==True])}")
    print(f"   Base compounds: {len(df[df['is_modified']==False])}")
    print("")

    # Baseline
    print("\n" + "-"*80)
    print("BASELINE (current algorithm)")
    print("-"*80)
    loo_base = validate_loo(df, separate_modified=False, use_ridge=False)
    kfold_base = validate_kfold(df, n_splits=5, separate_modified=False, use_ridge=False)
    print(f"LOO R²:     {loo_base['r2']:.4f}")
    print(f"K-Fold R²:  {kfold_base['mean_r2_test']:.4f}")
    print(f"Overfitting: {kfold_base['mean_overfitting']:.4f}")

    # Iteration 1: Separate modified
    print("\n" + "-"*80)
    print("ITERATION 1: Separate modified compounds")
    print("-"*80)
    loo_1 = validate_loo(df, separate_modified=True, use_ridge=False)
    kfold_1 = validate_kfold(df, n_splits=5, separate_modified=True, use_ridge=False)
    print(f"LOO R²:     {loo_1['r2']:.4f} (target: ≥0.85)")
    print(f"K-Fold R²:  {kfold_1['mean_r2_test']:.4f}")
    print(f"Overfitting: {kfold_1['mean_overfitting']:.4f}")

    if kfold_1['mean_r2_test'] >= 0.90 and kfold_1['mean_overfitting'] < 0.10:
        print("✅ SUCCESS! Target achieved")
        return

    # Iteration 2: Add Ridge
    print("\n" + "-"*80)
    print("ITERATION 2: Add Ridge regularization (alpha=1.0)")
    print("-"*80)
    loo_2 = validate_loo(df, separate_modified=True, use_ridge=True, ridge_alpha=1.0)
    kfold_2 = validate_kfold(df, n_splits=5, separate_modified=True, use_ridge=True, ridge_alpha=1.0)
    print(f"LOO R²:     {loo_2['r2']:.4f} (target: ≥0.90)")
    print(f"K-Fold R²:  {kfold_2['mean_r2_test']:.4f} (target: ≥0.90)")
    print(f"Overfitting: {kfold_2['mean_overfitting']:.4f} (target: <0.10)")

    if kfold_2['mean_r2_test'] >= 0.90 and kfold_2['mean_overfitting'] < 0.10:
        print("✅ SUCCESS! Target achieved")
    else:
        print("⚠️  Partial success - may need manual review")

    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'baseline': {'loo': loo_base, 'kfold': kfold_base},
        'iteration1': {'loo': loo_1, 'kfold': kfold_1},
        'iteration2': {'loo': loo_2, 'kfold': kfold_2}
    }

    output_file = 'trace/tuning_results_simple.json'
    Path('trace').mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_file}")
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
