#!/usr/bin/env python
"""
Standalone Algorithm Validation Script
Run this to validate the ganglioside analysis algorithm with your MS/MS verified data

Usage:
    python validate_algorithm.py --data path/to/testwork.csv
    python validate_algorithm.py --data path/to/testwork.csv --method loo
    python validate_algorithm.py --data path/to/testwork.csv --method kfold --folds 10
"""
import sys
import os
import argparse
import pandas as pd
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()

from apps.analysis.services.ganglioside_processor import GangliosideProcessor
from apps.analysis.services.algorithm_validator import AlgorithmValidator


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
        print(f"  Train R²: {metrics.r2_train:.4f} | Test R²: {metrics.r2_test:.4f}")
        print(f"  Train RMSE: {metrics.rmse_train:.4f} | Test RMSE: {metrics.rmse_test:.4f}")
        print(f"  Overfitting Score: {metrics.overfitting_score:.4f}")
        print(f"  Samples: {metrics.n_train} train / {metrics.n_test} test")

    return results


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


def validate_train_test(df: pd.DataFrame, test_size: float = 0.2, data_type: str = 'Porcine'):
    """Run single train/test split"""
    print_header("TRAIN/TEST SPLIT VALIDATION")

    processor = GangliosideProcessor()
    validator = AlgorithmValidator(processor)

    print(f"\nDataset: {len(df)} compounds ({len(df[df['Anchor']=='T'])} anchors)")
    print(f"Test size: {test_size * 100}%\n")

    print("Running validation...")
    results = validator.validate_train_test_split(df, test_size=test_size, data_type=data_type)

    print_header("RESULTS")
    metrics = results['metrics']

    print(f"\nR² Score:")
    print(f"  Training:   {metrics.r2_train:.4f}")
    print(f"  Test:       {metrics.r2_test:.4f}")
    print(f"  Difference: {metrics.overfitting_score:.4f}")

    print(f"\nRMSE:")
    print(f"  Training: {metrics.rmse_train:.4f}")
    print(f"  Test:     {metrics.rmse_test:.4f}")

    print(f"\nMAE:")
    print(f"  Training: {metrics.mae_train:.4f}")
    print(f"  Test:     {metrics.mae_test:.4f}")

    print(f"\nSample Sizes:")
    print(f"  Train: {metrics.n_train} ({metrics.n_anchors_train} anchors)")
    print(f"  Test:  {metrics.n_test} ({metrics.n_anchors_test} anchors)")

    # Interpretation
    print("\n" + "-" * 80)
    print("INTERPRETATION:")
    if metrics.overfitting_score < 0.05:
        print("✅ No significant overfitting detected")
    elif metrics.overfitting_score < 0.15:
        print("⚠️  Mild overfitting - acceptable for small datasets")
    else:
        print("❌ Significant overfitting - model may be memorizing data")

    if metrics.r2_test >= 0.75:
        print("✅ Strong predictive power on test data")
    elif metrics.r2_test >= 0.50:
        print("⚠️  Moderate predictive power")
    else:
        print("❌ Weak predictive power - algorithm may need tuning")

    return results


def quick_analysis(df: pd.DataFrame, data_type: str = 'Porcine'):
    """Quick analysis without cross-validation"""
    print_header("QUICK ANALYSIS (NO CROSS-VALIDATION)")

    processor = GangliosideProcessor()

    print(f"\nDataset: {len(df)} compounds ({len(df[df['Anchor']=='T'])} anchors)")
    print("\nRunning 5-rule analysis...")

    results = processor.process_data(df, data_type=data_type)

    print_header("RESULTS")

    stats = results['statistics']
    print(f"\nTotal Compounds: {stats['total_compounds']}")
    print(f"Anchor Compounds: {stats['anchor_compounds']}")
    print(f"Valid Compounds: {stats['valid_compounds']}")
    print(f"Outliers: {stats['outliers']}")
    print(f"Success Rate: {stats['success_rate']:.1f}%")

    print("\n" + "-" * 80)
    print("REGRESSION MODELS:")
    for prefix, model in results['regression_analysis'].items():
        print(f"\n{prefix}:")
        print(f"  R²: {model['r2']:.4f}")
        print(f"  Equation: {model['equation']}")
        print(f"  Samples: {model['n_samples']}")

    print("\n" + "-" * 80)
    print("CATEGORIZATION:")
    if 'categorization' in results and 'category_stats' in results['categorization']:
        for category, stats in results['categorization']['category_stats'].items():
            print(f"  {category}: {stats['count']} compounds ({stats['percentage']:.1f}%)")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Validate ganglioside analysis algorithm with MS/MS verified data'
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
        choices=['quick', 'kfold', 'loo', 'split'],
        default='kfold',
        help='Validation method (quick, kfold, loo, split)'
    )
    parser.add_argument(
        '--folds',
        type=int,
        default=5,
        help='Number of folds for k-fold validation (default: 5)'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Test set size for train/test split (default: 0.2)'
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
        if args.method == 'quick':
            results = quick_analysis(df, args.data_type)
        elif args.method == 'kfold':
            results = validate_kfold(df, args.folds, args.data_type)
        elif args.method == 'loo':
            results = validate_loo(df, args.data_type)
        elif args.method == 'split':
            results = validate_train_test(df, args.test_size, args.data_type)

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
