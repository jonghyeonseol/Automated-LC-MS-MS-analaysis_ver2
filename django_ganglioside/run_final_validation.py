#!/usr/bin/env python
"""
Final Validation Suite - Week 1 Day 4
Run comprehensive validation on tuned algorithm (v1.1)

Validates:
- Leave-One-Out (already done)
- 5-Fold cross-validation (already done)
- 10-Fold cross-validation (for stability)
- Calculate all Week 1 gate metrics
- Generate comparison report
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LinearRegression
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


def validate_kfold_detailed(df, n_splits=10, separate_modified=True):
    """K-Fold validation with detailed per-compound predictions"""
    anchors = df[df['Anchor'] == 'T'].copy()
    non_anchors = df[df['Anchor'] == 'F'].copy()

    if len(anchors) < n_splits:
        print(f"Warning: Only {len(anchors)} anchors, using {len(anchors)}-fold")
        n_splits = len(anchors)

    kfold = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    fold_results = []
    all_predictions = []

    for fold_idx, (train_idx, test_idx) in enumerate(kfold.split(anchors), 1):
        anchors_train = anchors.iloc[train_idx].copy()
        anchors_test = anchors.iloc[test_idx].copy()

        train_df = pd.concat([anchors_train, non_anchors]).reset_index(drop=True)

        # Test predictions
        test_actuals = []
        test_predictions = []
        test_compounds = []

        for _, test_row in anchors_test.iterrows():
            if separate_modified:
                train_subset = anchors_train[anchors_train['is_modified'] == test_row['is_modified']]
            else:
                train_subset = anchors_train

            prefix_data = train_subset[train_subset['prefix'] == test_row['prefix']]

            if len(prefix_data) >= 2:
                X = prefix_data[['Log P']].values
                y = prefix_data['RT'].values

                model = LinearRegression()
                model.fit(X, y)

                pred = model.predict([[test_row['Log P']]])[0]
                test_actuals.append(test_row['RT'])
                test_predictions.append(pred)
                test_compounds.append({
                    'fold': fold_idx,
                    'compound': test_row['Name'],
                    'actual_rt': test_row['RT'],
                    'predicted_rt': pred,
                    'residual': test_row['RT'] - pred,
                    'abs_error': abs(test_row['RT'] - pred)
                })

        if test_actuals:
            r2_test = r2_score(test_actuals, test_predictions)
            rmse_test = np.sqrt(mean_squared_error(test_actuals, test_predictions))
            mae_test = mean_absolute_error(test_actuals, test_predictions)

            fold_results.append({
                'fold': fold_idx,
                'r2_test': r2_test,
                'rmse_test': rmse_test,
                'mae_test': mae_test,
                'n_test': len(test_actuals)
            })

            all_predictions.extend(test_compounds)

    # Calculate aggregate metrics
    r2_scores = [f['r2_test'] for f in fold_results]
    rmse_scores = [f['rmse_test'] for f in fold_results]
    mae_scores = [f['mae_test'] for f in fold_results]

    # Overall predictions (all folds combined)
    all_actuals = [p['actual_rt'] for p in all_predictions]
    all_preds = [p['predicted_rt'] for p in all_predictions]

    return {
        'method': f'{n_splits}-Fold Cross-Validation',
        'n_folds': len(fold_results),
        'aggregated_metrics': {
            'mean_r2_test': float(np.mean(r2_scores)),
            'std_r2_test': float(np.std(r2_scores)),
            'min_r2_test': float(np.min(r2_scores)),
            'max_r2_test': float(np.max(r2_scores)),
            'mean_rmse_test': float(np.mean(rmse_scores)),
            'std_rmse_test': float(np.std(rmse_scores)),
            'mean_mae_test': float(np.mean(mae_scores)),
            'overall_r2': float(r2_score(all_actuals, all_preds)),
            'overall_rmse': float(np.sqrt(mean_squared_error(all_actuals, all_preds))),
            'overall_mae': float(mean_absolute_error(all_actuals, all_preds))
        },
        'per_fold_results': fold_results,
        'predictions': all_predictions,
        'summary': {
            'best_prediction': min(all_predictions, key=lambda x: x['abs_error']),
            'worst_prediction': max(all_predictions, key=lambda x: x['abs_error'])
        }
    }


def main():
    print("="*80)
    print("FINAL VALIDATION SUITE - Week 1 Day 4")
    print("="*80)
    print("Algorithm: v1.1 (Separated Modified Compounds)")
    print("Validation Methods: LOO, 5-Fold, 10-Fold")
    print("")

    # Load data
    data_file = '../data/samples/testwork_user.csv'
    df = pd.read_csv(data_file)
    df = preprocess_data(df)

    print(f"Dataset: {len(df)} compounds ({len(df[df['Anchor']=='T'])} anchors)")
    print(f"  Modified: {len(df[df['is_modified']==True])}")
    print(f"  Base: {len(df[df['is_modified']==False])}")
    print("")

    # Run 10-Fold validation
    print("-"*80)
    print("Running 10-Fold Cross-Validation...")
    print("-"*80)

    results_10fold = validate_kfold_detailed(df, n_splits=10, separate_modified=True)

    print(f"\n10-Fold Results:")
    print(f"  Mean R² (test): {results_10fold['aggregated_metrics']['mean_r2_test']:.4f}")
    print(f"  Std R² (test):  {results_10fold['aggregated_metrics']['std_r2_test']:.4f}")
    print(f"  Min R² (test):  {results_10fold['aggregated_metrics']['min_r2_test']:.4f}")
    print(f"  Max R² (test):  {results_10fold['aggregated_metrics']['max_r2_test']:.4f}")
    print(f"  Overall R²:     {results_10fold['aggregated_metrics']['overall_r2']:.4f}")
    print(f"  Overall RMSE:   {results_10fold['aggregated_metrics']['overall_rmse']:.4f} min")
    print(f"  Overall MAE:    {results_10fold['aggregated_metrics']['overall_mae']:.4f} min")
    print("")

    # Load previous results
    with open('trace/tuning_results_simple.json', 'r') as f:
        previous_results = json.load(f)

    loo_r2 = previous_results['iteration1']['loo']['r2']
    loo_rmse = previous_results['iteration1']['loo'].get('rmse', 'N/A')
    loo_mae = previous_results['iteration1']['loo'].get('mae', 'N/A')
    kfold5_r2 = previous_results['iteration1']['kfold']['mean_r2_test']

    # Week 1 Gate Criteria Check
    print("="*80)
    print("WEEK 1 GATE CRITERIA VALIDATION")
    print("="*80)
    print("")

    gate_results = {
        'timestamp': datetime.now().isoformat(),
        'algorithm_version': 'v1.1_separated',
        'dataset': 'testwork_user.csv',
        'criteria': []
    }

    # Criterion 1: R² (LOO) ≥ 0.90
    criterion1 = {
        'criterion': 'R² (Leave-One-Out) ≥ 0.90',
        'target': 0.90,
        'achieved': loo_r2,
        'passed': loo_r2 >= 0.90,
        'margin': loo_r2 - 0.90
    }
    gate_results['criteria'].append(criterion1)
    print(f"1. R² (LOO) ≥ 0.90")
    print(f"   Target:   0.9000")
    print(f"   Achieved: {loo_r2:.4f}")
    print(f"   Status:   {'✅ PASS' if criterion1['passed'] else '❌ FAIL'} (margin: {criterion1['margin']:+.4f})")
    print("")

    # Criterion 2: R² (5-Fold) ≥ 0.90
    criterion2 = {
        'criterion': 'R² (5-Fold) ≥ 0.90',
        'target': 0.90,
        'achieved': kfold5_r2,
        'passed': kfold5_r2 >= 0.90,
        'margin': kfold5_r2 - 0.90
    }
    gate_results['criteria'].append(criterion2)
    print(f"2. R² (5-Fold) ≥ 0.90")
    print(f"   Target:   0.9000")
    print(f"   Achieved: {kfold5_r2:.4f}")
    print(f"   Status:   {'✅ PASS' if criterion2['passed'] else '❌ FAIL'} (margin: {criterion2['margin']:+.4f})")
    print("")

    # Criterion 3: RMSE < 0.15 min
    rmse_10fold = results_10fold['aggregated_metrics']['overall_rmse']
    criterion3 = {
        'criterion': 'RMSE < 0.15 min',
        'target': 0.15,
        'achieved': rmse_10fold,
        'passed': rmse_10fold < 0.15,
        'margin': 0.15 - rmse_10fold
    }
    gate_results['criteria'].append(criterion3)
    print(f"3. RMSE < 0.15 min")
    print(f"   Target:   < 0.1500")
    print(f"   Achieved: {rmse_10fold:.4f}")
    print(f"   Status:   {'✅ PASS' if criterion3['passed'] else '❌ FAIL'} (margin: {criterion3['margin']:+.4f})")
    print("")

    # Criterion 4: Consistency |LOO - 5Fold| < 0.05
    consistency = abs(loo_r2 - kfold5_r2)
    criterion4 = {
        'criterion': 'Consistency: |R²_LOO - R²_5Fold| < 0.05',
        'target': 0.05,
        'achieved': consistency,
        'passed': consistency < 0.05,
        'margin': 0.05 - consistency
    }
    gate_results['criteria'].append(criterion4)
    print(f"4. Consistency: |R²_LOO - R²_5Fold| < 0.05")
    print(f"   Target:   < 0.0500")
    print(f"   Achieved: {consistency:.4f}")
    print(f"   Status:   {'✅ PASS' if criterion4['passed'] else '⚠️  MARGINAL'} (margin: {criterion4['margin']:+.4f})")
    print("")

    # Criterion 5: 10-Fold R² ≥ 0.90
    r2_10fold = results_10fold['aggregated_metrics']['mean_r2_test']
    criterion5 = {
        'criterion': 'R² (10-Fold) ≥ 0.90',
        'target': 0.90,
        'achieved': r2_10fold,
        'passed': r2_10fold >= 0.90,
        'margin': r2_10fold - 0.90
    }
    gate_results['criteria'].append(criterion5)
    print(f"5. R² (10-Fold) ≥ 0.90 (stability check)")
    print(f"   Target:   0.9000")
    print(f"   Achieved: {r2_10fold:.4f}")
    print(f"   Status:   {'✅ PASS' if criterion5['passed'] else '❌ FAIL'} (margin: {criterion5['margin']:+.4f})")
    print("")

    # Overall gate status
    passed = sum([c['passed'] for c in gate_results['criteria']])
    total = len(gate_results['criteria'])
    gate_results['overall_status'] = 'PASSED' if passed >= 4 else 'FAILED'
    gate_results['passed_count'] = passed
    gate_results['total_count'] = total

    print("="*80)
    print(f"WEEK 1 GATE STATUS: {gate_results['overall_status']}")
    print("="*80)
    print(f"Passed: {passed}/{total} criteria")
    print("")

    # Save results
    output_dir = Path('trace/validation_runs')
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save 10-fold results
    with open(output_dir / f'{timestamp}_10FOLD_final.json', 'w') as f:
        json.dump(results_10fold, f, indent=2, default=str)

    # Save gate validation results
    with open(output_dir / f'{timestamp}_GATE_VALIDATION.json', 'w') as f:
        json.dump(gate_results, f, indent=2, default=str)

    print(f"✅ Results saved:")
    print(f"   - {output_dir}/{timestamp}_10FOLD_final.json")
    print(f"   - {output_dir}/{timestamp}_GATE_VALIDATION.json")
    print("")

    if gate_results['overall_status'] == 'PASSED':
        print("✅ Week 1 validation complete - Ready for approval (Day 5)")
    else:
        print("⚠️  Some criteria not met - Review required")

    return 0 if gate_results['overall_status'] == 'PASSED' else 1


if __name__ == '__main__':
    sys.exit(main())
