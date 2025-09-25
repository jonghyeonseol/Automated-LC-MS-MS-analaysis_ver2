#!/usr/bin/env python3
"""
Quick test to verify the regression fix works
"""

import sys
import os
import pandas as pd

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from backend.services.ganglioside_processor import GangliosideProcessor

def quick_test():
    print("🧬 Quick Test - Fixed Regression Analysis")
    print("=" * 45)

    # Load data
    df = pd.read_csv("data/sample/testwork.csv")
    print(f"📄 Loaded: {len(df)} compounds")

    # Test processor
    processor = GangliosideProcessor()

    print("🔍 Settings:")
    settings = processor.get_settings()
    print(f"   R² threshold: {settings['r2_threshold']}")
    print(f"   Outlier threshold: {settings['outlier_threshold']}")

    # Run analysis
    results = processor.process_data(df, "Porcine")

    # Show results
    stats = results["statistics"]
    print(f"\n📊 Results:")
    print(f"   Success rate: {stats['success_rate']:.1f}%")
    print(f"   Valid compounds: {stats['valid_compounds']}")
    print(f"   Outliers: {stats['outliers']}")
    print(f"   Available keys: {list(results.keys())}")

    # Try different key names
    rule1_key = None
    for key in results.keys():
        if 'rule1' in key.lower():
            rule1_key = key
            break

    if rule1_key and 'regression_results' in results[rule1_key]:
        print(f"   Regression models: {len(results[rule1_key]['regression_results'])}")
        if results[rule1_key]['regression_results']:
            for name, info in results[rule1_key]['regression_results'].items():
                print(f"   Model '{name}': R² = {info['r2']:.3f}")
                print(f"      {info['equation']}")

    # Check if fixed
    has_models = len(results['rule1_results']['regression_results']) > 0
    good_success_rate = stats['success_rate'] > 50

    if has_models and good_success_rate:
        print(f"\n✅ FIXED! Regression analysis is now working!")
        return True
    else:
        print(f"\n❌ Still needs work...")
        return False

if __name__ == "__main__":
    success = quick_test()
    if success:
        print("🎉 Ready to use!")
    else:
        print("❌ Needs more fixes...")
    exit(0 if success else 1)