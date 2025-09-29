#!/usr/bin/env python3
"""
Direct test of categorization integration
"""

import sys
import pandas as pd

# Import from new structure
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from src.services.ganglioside_processor import GangliosideProcessor


def test_direct_integration():
    print("🧪 DIRECT CATEGORIZATION INTEGRATION TEST")
    print("=" * 50)

    # Load test data
    df = pd.read_csv('../../data/samples/testwork_user.csv')
    print(f"📁 Loaded {len(df)} compounds")

    # Create processor
    processor = GangliosideProcessor()
    print("✅ Processor created")

    # Test categorization method directly
    try:
        cat_results = processor._generate_categorization_results(df)
        print("✅ Categorization successful!")
        print(f"📊 Categories: {len(cat_results.get('categories', {}))}")
        print(f"🏷️ Category stats: {len(cat_results.get('category_stats', {}))}")

        if 'category_stats' in cat_results:
            print("\n🔍 Category breakdown:")
            for cat, stats in cat_results['category_stats'].items():
                print(f"   {cat}: {stats['count']} compounds ({stats['percentage']:.1f}%)")

        return True
    except Exception as e:
        print(f"❌ Categorization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_analysis():
    print("\n🔬 FULL ANALYSIS WITH CATEGORIZATION TEST")
    print("=" * 50)

    # Load test data
    df = pd.read_csv('../../data/samples/testwork_user.csv')

    # Create processor and run full analysis
    processor = GangliosideProcessor()

    try:
        results = processor.process_data(df, "Porcine")
        print("✅ Full analysis completed")

        if 'categorization' in results:
            print("✅ Categorization data found in results!")
            cat = results['categorization']
            print(f"📊 Categories: {len(cat.get('categories', {}))}")
            return True
        else:
            print("❌ No categorization data in results")
            print(f"📊 Result keys: {list(results.keys())}")
            return False

    except Exception as e:
        print(f"❌ Full analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🔧 TESTING CATEGORIZATION INTEGRATION")
    print()

    # Test 1: Direct categorization method
    direct_success = test_direct_integration()

    # Test 2: Full analysis pipeline
    full_success = test_full_analysis()

    print("\n" + "=" * 50)
    if direct_success and full_success:
        print("🎉 SUCCESS: Categorization fully integrated!")
    else:
        print("❌ FAILURE: Integration issues detected")
        if not direct_success:
            print("   🔧 Fix: Direct categorization method")
        if not full_success:
            print("   🔧 Fix: Full analysis pipeline integration")
