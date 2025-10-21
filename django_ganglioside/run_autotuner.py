#!/usr/bin/env python
"""
Run Algorithm Auto-Tuner
Iteratively improves ganglioside algorithm to achieve R² ≥ 0.90

Usage:
    python run_autotuner.py --data ../data/samples/testwork_user.csv
    python run_autotuner.py --data ../data/samples/testwork_user.csv --target-r2 0.90 --max-iter 5
"""

import sys
import argparse
import pandas as pd
from pathlib import Path

# Add apps to path
sys.path.insert(0, str(Path(__file__).parent))

from apps.analysis.services.algorithm_tuner import AlgorithmTuner


def main():
    parser = argparse.ArgumentParser(
        description='Auto-tune ganglioside analysis algorithm'
    )
    parser.add_argument(
        '--data',
        type=str,
        default='../data/samples/testwork_user.csv',
        help='Path to CSV file with MS/MS verified data'
    )
    parser.add_argument(
        '--target-r2',
        type=float,
        default=0.90,
        help='Target R² score (default: 0.90)'
    )
    parser.add_argument(
        '--max-iter',
        type=int,
        default=5,
        help='Maximum tuning iterations (default: 5)'
    )
    parser.add_argument(
        '--data-type',
        type=str,
        default='Porcine',
        help='Data type (Porcine, Human, etc.)'
    )

    args = parser.parse_args()

    # Load data
    print("="*80)
    print("LOADING DATA")
    print("="*80)
    print(f"File: {args.data}")

    try:
        df = pd.read_csv(args.data)
        print(f"✅ Loaded {len(df)} compounds")
        print(f"   Anchors (Anchor='T'): {len(df[df['Anchor']=='T'])}")
        print(f"   Non-anchors (Anchor='F'): {len(df[df['Anchor']=='F'])}")
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return 1

    # Run auto-tuner
    try:
        tuner = AlgorithmTuner()
        best_config, best_result = tuner.tune_iteratively(
            df,
            target_r2=args.target_r2,
            max_iterations=args.max_iter,
            data_type=args.data_type
        )

        # Save tuning history
        tuner.save_tuning_history()

        print("\n" + "="*80)
        print("FINAL RESULTS")
        print("="*80)
        print(f"Best Version: {best_result.version}")
        print(f"R² (LOO):     {best_result.r2_loo:.4f}")
        print(f"R² (K-Fold):  {best_result.r2_kfold:.4f}")
        print(f"RMSE (LOO):   {best_result.rmse_loo:.4f}")
        print(f"Overfitting:  {best_result.overfitting_score:.4f}")
        print(f"")
        print(f"Configuration:")
        print(f"  - Separate modified: {best_config.separate_modified}")
        print(f"  - Features: {best_config.features}")
        print(f"  - Use Ridge: {best_config.use_ridge}")
        if best_config.use_ridge:
            print(f"  - Ridge alpha: {best_config.ridge_alpha}")
        print(f"  - Pool prefixes: {best_config.pool_prefixes}")
        print(f"")
        print(f"Trace location: {best_result.trace_location}")
        print(f"Checksum: {best_result.checksum}")
        print("="*80)

        if best_result.r2_kfold >= args.target_r2:
            print(f"✅ SUCCESS: Algorithm meets target R² ≥ {args.target_r2}")
            return 0
        else:
            print(f"⚠️  PARTIAL SUCCESS: Best R² = {best_result.r2_kfold:.4f} (target: {args.target_r2})")
            print(f"   Consider manual review or additional tuning strategies")
            return 1

    except Exception as e:
        print(f"\n❌ Error during auto-tuning: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
