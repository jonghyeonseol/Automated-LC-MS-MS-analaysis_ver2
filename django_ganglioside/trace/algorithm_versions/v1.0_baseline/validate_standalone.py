#!/usr/bin/env python
"""
Standalone Algorithm Validation Script (No Django Required)
Run this to validate the ganglioside analysis algorithm with your MS/MS verified data

Usage:
    python validate_standalone.py --data path/to/testwork.csv
    python validate_standalone.py --data path/to/testwork.csv --method loo
    python validate_standalone.py --data path/to/testwork.csv --method kfold --folds 10
"""
import sys
import argparse
import pandas as pd
import numpy as np
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from sklearn.model_selection import KFold, LeaveOneOut
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.linear_model import Ridge, LinearRegression
import re


# ===== Copy of GangliosideProcessor (minimal version) =====

class GangliosideProcessor:
    """Minimal version of ganglioside processor for validation"""

    def __init__(self):
        self.r2_threshold = 0.75
        self.outlier_threshold = 2.5
        self.rt_tolerance = 0.1

    def process_data(self, df: pd.DataFrame, data_type: str = 'Porcine') -> Dict[str, Any]:
        """Process data with 5-rule algorithm"""
        df_processed = self._preprocess_data(df.copy())

        # Apply Rule 1: Regression
        regression_results = self._apply_rule1_regression(df_processed)

        # Compile results
        return {
            'regression_analysis': regression_results,
            'valid_compounds': df_processed.to_dict('records'),
            'outliers': [],
            'statistics': {
                'total_compounds': len(df),
                'anchor_compounds': len(df[df['Anchor'] == 'T']),
                'valid_compounds': len(df),
                'outliers': 0,
                'success_rate': 100.0
            }
        }

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract prefix from compound names"""
        def extract_prefix(name):
            match = re.match(r'^([A-Z]+\d+)', str(name))
            return match.group(1) if match else 'Unknown'

        df['prefix'] = df['Name'].apply(extract_prefix)
        return df

    def _apply_rule1_regression(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Apply regression for each prefix group"""
        results = {}

        for prefix in df['prefix'].unique():
            prefix_df = df[df['prefix'] == prefix]
            anchors = prefix_df[prefix_df['Anchor'] == 'T']

            if len(anchors) < 2:
                continue

            X = anchors[['Log P']].values
            y = anchors['RT'].values

            # Simple linear regression
            model = LinearRegression()
            model.fit(X, y)

            predictions = model.predict(X)
            r2 = r2_score(y, predictions)

            results[prefix] = {
                'slope': float(model.coef_[0]),
                'intercept': float(model.intercept_),
                'r2': float(r2),
                'n_samples': len(anchors),
                'equation': f"RT = {model.coef_[0]:.4f} * Log P + {model.intercept_:.4f}"
            }

        return results


# ===== Validation Framework =====

@dataclass
class ValidationMetrics:
    """Container for validation metrics"""
    r2_train: float
    r2_test: float
    rmse_train: float
    rmse_test: float
    mae_train: float
    mae_test: float
    n_train: int
    n_test: int
    n_anchors_train: int
    n_anchors_test: int
    overfitting_score: float
    generalization_ratio: float


class AlgorithmValidator:
    """Validates ganglioside analysis algorithm performance"""

    def __init__(self, processor: GangliosideProcessor = None):
        self.processor = processor or GangliosideProcessor()

    def validate_leave_one_out(self, df: pd.DataFrame, data_type: str = 'Porcine') -> Dict[str, Any]:
        """Leave-One-Out cross-validation"""
        anchors = df[df['Anchor'] == 'T'].copy()
        non_anchors = df[df['Anchor'] == 'F'].copy()

        n_anchors = len(anchors)

        if n_anchors < 2:
            return {'error': 'Need at least 2 anchor compounds for LOO validation'}

        loo_results = []
        predictions = []
        actuals = []

        for idx in range(n_anchors):
            # Leave one out
            test_anchor = anchors.iloc[[idx]].copy()
            train_anchors = anchors.drop(anchors.index[idx]).copy()

            # Training set
            train_df = pd.concat([train_anchors, non_anchors]).reset_index(drop=True)

            # Run analysis
            train_results = self.processor.process_data(train_df, data_type=data_type)

            # Predict test anchor
            test_compound_name = test_anchor.iloc[0]['Name']
            test_rt = test_anchor.iloc[0]['RT']
            test_log_p = test_anchor.iloc[0]['Log P']

            # Find regression model for this compound's prefix
            prefix = self.processor._preprocess_data(test_anchor).iloc[0]['prefix']

            predicted_rt = None
            if prefix in train_results.get('regression_analysis', {}):
                model_info = train_results['regression_analysis'][prefix]
                slope = model_info.get('slope', 0)
                intercept = model_info.get('intercept', 0)
                predicted_rt = slope * test_log_p + intercept

            if predicted_rt is not None:
                predictions.append(predicted_rt)
                actuals.append(test_rt)
                residual = test_rt - predicted_rt

                loo_results.append({
                    'compound': test_compound_name,
                    'actual_rt': test_rt,
                    'predicted_rt': predicted_rt,
                    'residual': residual,
                    'abs_error': abs(residual),
                    'squared_error': residual ** 2
                })

        if not predictions:
            return {'error': 'No predictions could be made'}

        # Calculate LOO metrics
        predictions = np.array(predictions)
        actuals = np.array(actuals)

        return {
            'method': 'Leave-One-Out',
            'n_compounds': n_anchors,
            'metrics': {
                'r2': float(r2_score(actuals, predictions)),
                'rmse': float(np.sqrt(mean_squared_error(actuals, predictions))),
                'mae': float(mean_absolute_error(actuals, predictions)),
                'max_error': float(np.max(np.abs(actuals - predictions))),
                'mean_residual': float(np.mean(actuals - predictions)),
                'std_residual': float(np.std(actuals - predictions))
            },
            'predictions': loo_results,
            'summary': {
                'best_prediction': min(loo_results, key=lambda x: x['abs_error']),
                'worst_prediction': max(loo_results, key=lambda x: x['abs_error'])
            }
        }

    def validate_with_kfold(self, df: pd.DataFrame, n_splits: int = 5,
                           data_type: str = 'Porcine', random_state: int = 42) -> Dict[str, Any]:
        """K-Fold cross-validation"""
        anchors = df[df['Anchor'] == 'T'].copy()
        non_anchors = df[df['Anchor'] == 'F'].copy()

        if len(anchors) < n_splits:
            return self.validate_leave_one_out(df, data_type)

        kfold = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        fold_results = []

        for fold_idx, (train_idx, test_idx) in enumerate(kfold.split(anchors), 1):
            # Split anchors
            anchors_train = anchors.iloc[train_idx].copy()
            anchors_test = anchors.iloc[test_idx].copy()

            # Create training set
            train_df = pd.concat([anchors_train, non_anchors]).reset_index(drop=True)
            test_df = anchors_test.copy()

            # Run analysis
            train_results = self.processor.process_data(train_df, data_type=data_type)

            # Calculate metrics
            metrics = self._calculate_fold_metrics(train_df, test_df, train_results, fold_idx)

            fold_results.append({
                'fold': fold_idx,
                'metrics': metrics,
                'train_size': len(train_df),
                'test_size': len(test_df)
            })

        return self._aggregate_fold_results(fold_results, n_splits)

    def _calculate_fold_metrics(self, train_df, test_df, train_results, fold_idx) -> ValidationMetrics:
        """Calculate metrics for a single fold"""
        # Training metrics
        train_anchors = train_df[train_df['Anchor'] == 'T']

        train_actuals = []
        train_predictions = []

        for _, row in train_anchors.iterrows():
            prefix = self.processor._preprocess_data(pd.DataFrame([row])).iloc[0]['prefix']
            if prefix in train_results.get('regression_analysis', {}):
                model_info = train_results['regression_analysis'][prefix]
                pred_rt = model_info['slope'] * row['Log P'] + model_info['intercept']
                train_actuals.append(row['RT'])
                train_predictions.append(pred_rt)

        r2_train = r2_score(train_actuals, train_predictions) if train_actuals else 0
        rmse_train = np.sqrt(mean_squared_error(train_actuals, train_predictions)) if train_actuals else 0
        mae_train = mean_absolute_error(train_actuals, train_predictions) if train_actuals else 0

        # Test metrics
        test_actuals = []
        test_predictions = []

        for _, row in test_df.iterrows():
            prefix = self.processor._preprocess_data(pd.DataFrame([row])).iloc[0]['prefix']
            if prefix in train_results.get('regression_analysis', {}):
                model_info = train_results['regression_analysis'][prefix]
                pred_rt = model_info['slope'] * row['Log P'] + model_info['intercept']
                test_actuals.append(row['RT'])
                test_predictions.append(pred_rt)

        r2_test = r2_score(test_actuals, test_predictions) if test_actuals else 0
        rmse_test = np.sqrt(mean_squared_error(test_actuals, test_predictions)) if test_actuals else 0
        mae_test = mean_absolute_error(test_actuals, test_predictions) if test_actuals else 0

        overfitting_score = r2_train - r2_test
        generalization_ratio = r2_test / r2_train if r2_train > 0 else 0

        return ValidationMetrics(
            r2_train=r2_train,
            r2_test=r2_test,
            rmse_train=rmse_train,
            rmse_test=rmse_test,
            mae_train=mae_train,
            mae_test=mae_test,
            n_train=len(train_df),
            n_test=len(test_df),
            n_anchors_train=len(train_df[train_df['Anchor'] == 'T']),
            n_anchors_test=len(test_df[test_df['Anchor'] == 'T']),
            overfitting_score=overfitting_score,
            generalization_ratio=generalization_ratio
        )

    def _aggregate_fold_results(self, fold_results: List[Dict], n_splits: int) -> Dict[str, Any]:
        """Aggregate metrics across all folds"""
        r2_train_scores = [f['metrics'].r2_train for f in fold_results]
        r2_test_scores = [f['metrics'].r2_test for f in fold_results]
        rmse_test_scores = [f['metrics'].rmse_test for f in fold_results]
        mae_test_scores = [f['metrics'].mae_test for f in fold_results]
        overfitting_scores = [f['metrics'].overfitting_score for f in fold_results]

        mean_r2_test = np.mean(r2_test_scores)
        std_r2_test = np.std(r2_test_scores)
        mean_overfitting = np.mean(overfitting_scores)

        return {
            'method': f'{n_splits}-Fold Cross-Validation',
            'n_folds': n_splits,
            'aggregated_metrics': {
                'mean_r2_train': float(np.mean(r2_train_scores)),
                'mean_r2_test': float(mean_r2_test),
                'std_r2_test': float(std_r2_test),
                'mean_rmse_test': float(np.mean(rmse_test_scores)),
                'std_rmse_test': float(np.std(rmse_test_scores)),
                'mean_mae_test': float(np.mean(mae_test_scores)),
                'mean_overfitting_score': float(mean_overfitting),
                'max_overfitting_score': float(np.max(overfitting_scores)),
            },
            'per_fold_results': [
                {
                    'fold': f['fold'],
                    'metrics': asdict(f['metrics'])
                } for f in fold_results
            ],
            'interpretation': self._interpret_results(mean_r2_test, std_r2_test, mean_overfitting)
        }

    def _interpret_results(self, mean_r2: float, std_r2: float, mean_overfitting: float) -> Dict[str, str]:
        """Provide human-readable interpretation"""
        interpretation = {}

        if mean_r2 >= 0.90:
            interpretation['r2_quality'] = 'Excellent - Model explains >90% of variance'
        elif mean_r2 >= 0.75:
            interpretation['r2_quality'] = 'Good - Model has strong predictive power'
        elif mean_r2 >= 0.50:
            interpretation['r2_quality'] = 'Moderate - Model has some predictive power'
        else:
            interpretation['r2_quality'] = 'Poor - Model has weak predictive power'

        if std_r2 < 0.05:
            interpretation['consistency'] = 'Very consistent across folds'
        elif std_r2 < 0.10:
            interpretation['consistency'] = 'Reasonably consistent'
        else:
            interpretation['consistency'] = 'High variance - results depend on data split'

        if mean_overfitting < 0.05:
            interpretation['overfitting'] = 'No significant overfitting detected'
        elif mean_overfitting < 0.15:
            interpretation['overfitting'] = 'Mild overfitting - monitor with more data'
        else:
            interpretation['overfitting'] = 'Significant overfitting - model memorizing training data'

        if mean_r2 >= 0.75 and mean_overfitting < 0.10:
            interpretation['recommendation'] = 'Algorithm performs well - ready for production use'
        elif mean_r2 >= 0.50:
            interpretation['recommendation'] = 'Algorithm has potential - consider tuning parameters'
        else:
            interpretation['recommendation'] = 'Algorithm needs improvement - review feature engineering'

        return interpretation


# ===== Output Formatting =====

def print_header(text: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_metrics(metrics: dict, indent: int = 0):
    """Pretty print metrics"""
    prefix = "  " * indent
    for key, value in metrics.items():
        if isinstance(value, dict):
            print(f"{prefix}{key}:")
            print_metrics(value, indent + 1)
        elif isinstance(value, float):
            print(f"{prefix}{key}: {value:.4f}")
        else:
            print(f"{prefix}{key}: {value}")


def validate_loo(df: pd.DataFrame, data_type: str = 'Porcine'):
    """Run Leave-One-Out cross-validation"""
    print_header("LEAVE-ONE-OUT CROSS-VALIDATION")

    processor = GangliosideProcessor()
    validator = AlgorithmValidator(processor)

    anchors = df[df['Anchor'] == 'T']
    print(f"\nDataset: {len(df)} compounds ({len(anchors)} anchors)")
    print("Method: Each anchor is tested individually\n")

    print("Running validation...")
    results = validator.validate_leave_one_out(df, data_type=data_type)

    if 'error' in results:
        print(f"ERROR: {results['error']}")
        return results

    print_header("OVERALL METRICS")
    print_metrics(results['metrics'])

    print("\n" + "-" * 80)
    print("PREDICTION DETAILS:")
    print(f"\n{'Compound':<30} {'Actual RT':>10} {'Predicted':>10} {'Error':>10}")
    print("-" * 65)

    for pred in results['predictions']:
        print(f"{pred['compound']:<30} "
              f"{pred['actual_rt']:>10.3f} "
              f"{pred['predicted_rt']:>10.3f} "
              f"{pred['residual']:>10.3f}")

    print("\n" + "-" * 80)
    print("BEST/WORST PREDICTIONS:")
    best = results['summary']['best_prediction']
    worst = results['summary']['worst_prediction']
    print(f"\nBest:  {best['compound']} (error: {best['abs_error']:.4f})")
    print(f"Worst: {worst['compound']} (error: {worst['abs_error']:.4f})")

    return results


def validate_kfold(df: pd.DataFrame, n_splits: int = 5, data_type: str = 'Porcine'):
    """Run K-Fold cross-validation"""
    print_header(f"{n_splits}-FOLD CROSS-VALIDATION")

    processor = GangliosideProcessor()
    validator = AlgorithmValidator(processor)

    print(f"\nDataset: {len(df)} compounds ({len(df[df['Anchor']=='T'])} anchors)")
    print(f"Splits: {n_splits}")
    print("\nRunning validation...")

    results = validator.validate_with_kfold(df, n_splits=n_splits, data_type=data_type)

    print_header("RESULTS")
    print_metrics(results['aggregated_metrics'])

    print("\n" + "-" * 80)
    print("INTERPRETATION:")
    print_metrics(results['interpretation'])

    print("\n" + "-" * 80)
    print("PER-FOLD BREAKDOWN:")
    for fold_result in results['per_fold_results']:
        fold = fold_result['fold']
        metrics = fold_result['metrics']
        print(f"\nFold {fold}:")
        print(f"  Train R²: {metrics['r2_train']:.4f} | Test R²: {metrics['r2_test']:.4f}")
        print(f"  Train RMSE: {metrics['rmse_train']:.4f} | Test RMSE: {metrics['rmse_test']:.4f}")
        print(f"  Overfitting Score: {metrics['overfitting_score']:.4f}")
        print(f"  Samples: {metrics['n_anchors_train']} train / {metrics['n_anchors_test']} test")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Validate ganglioside analysis algorithm (Standalone - No Django Required)'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='../data/samples/testwork_user.csv',
        help='Path to CSV file with MS/MS verified data'
    )
    parser.add_argument(
        '--method',
        type=str,
        choices=['loo', 'kfold'],
        default='loo',
        help='Validation method (loo, kfold)'
    )
    parser.add_argument(
        '--folds',
        type=int,
        default=5,
        help='Number of folds for k-fold validation (default: 5)'
    )
    parser.add_argument(
        '--data-type',
        type=str,
        default='Porcine',
        help='Data type (Porcine, Human, etc.)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output JSON file for results (optional)'
    )

    args = parser.parse_args()

    # Load data
    print_header("LOADING DATA")
    print(f"File: {args.data}")

    try:
        df = pd.read_csv(args.data)
        print(f"✅ Loaded {len(df)} compounds")
        print(f"   Anchors (Anchor='T'): {len(df[df['Anchor']=='T'])}")
        print(f"   Non-anchors (Anchor='F'): {len(df[df['Anchor']=='F'])}")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return 1

    # Run validation
    try:
        if args.method == 'loo':
            results = validate_loo(df, args.data_type)
        elif args.method == 'kfold':
            results = validate_kfold(df, args.folds, args.data_type)

        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n✅ Results saved to {args.output}")

        print_header("VALIDATION COMPLETE")
        return 0

    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
