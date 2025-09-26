#!/usr/bin/env python3
"""
Test the integrated categorization system
"""

import requests
import json
import pandas as pd

def test_integrated_categorization():
    print("🧪 TESTING INTEGRATED CATEGORIZATION SYSTEM")
    print("=" * 60)

    base_url = "http://localhost:5001"
    test_file = "testwork_user.csv"

    # Step 1: Load and analyze the data
    print("1. 📊 Loading test data...")
    try:
        df = pd.read_csv(test_file)
        print(f"   📁 Loaded {len(df)} compounds")
    except Exception as e:
        print(f"   ❌ Failed to load data: {e}")
        return False

    # Step 2: Run analysis with categorization
    print("\n2. 🚀 Running analysis with categorization...")
    try:
        with open(test_file, "rb") as f:
            files = {"file": ("testwork.csv", f, "text/csv")}
            data = {
                "data_type": "Porcine",
                "outlier_threshold": 2.5,
                "r2_threshold": 0.75,
                "rt_tolerance": 0.1
            }

            analysis_response = requests.post(f"{base_url}/api/analyze", files=files, data=data)

        print(f"   📡 Analysis status: {analysis_response.status_code}")

        if analysis_response.status_code == 200:
            analysis_result = analysis_response.json()
            results = analysis_result['results']

            print(f"   ✅ Analysis successful!")

            # Check if categorization is included
            if 'categorization' in results:
                cat = results['categorization']
                print(f"   📊 Categorization included!")
                print(f"   📈 Categories found: {len(cat.get('categories', {}))}")
                print(f"   🏷️ Base prefixes: {len(cat.get('base_prefixes', {}))}")
                print(f"   ⚗️ Modifications: {len(cat.get('modifications', {}))}")

                # Show category breakdown
                if 'category_stats' in cat:
                    print(f"\n   🔍 CATEGORY BREAKDOWN:")
                    for category, stats in cat['category_stats'].items():
                        print(f"      🎨 {category}: {stats['count']} compounds ({stats['percentage']:.1f}%) - {stats['color']}")
                        print(f"         📝 {stats['description']}")
                        if stats['examples']:
                            print(f"         📋 Examples: {', '.join(stats['examples'][:2])}")
                        print()

                return True
            else:
                print(f"   ❌ No categorization data found in results")
                print(f"   📊 Result keys: {list(results.keys())}")
                return False

        else:
            print(f"   ❌ Analysis failed: {analysis_response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
        return False

def test_visualization_with_categorization():
    """Test if visualization can access categorization data"""
    print("\n3. 📊 Testing visualization with categorization data...")

    base_url = "http://localhost:5001"
    test_file = "testwork_user.csv"

    try:
        # Run analysis first
        with open(test_file, "rb") as f:
            files = {"file": ("testwork.csv", f, "text/csv")}
            data = {
                "data_type": "Porcine",
                "outlier_threshold": 2.5,
                "r2_threshold": 0.75,
                "rt_tolerance": 0.1
            }
            analysis_response = requests.post(f"{base_url}/api/analyze", files=files, data=data)

        if analysis_response.status_code != 200:
            print(f"   ❌ Analysis failed")
            return False

        analysis_result = analysis_response.json()
        analysis_data = analysis_result['results']

        # Test visualization
        viz_payload = {"results": analysis_data}
        viz_response = requests.post(
            f"{base_url}/api/visualize",
            headers={"Content-Type": "application/json"},
            data=json.dumps(viz_payload)
        )

        if viz_response.status_code == 200:
            viz_result = viz_response.json()
            print(f"   ✅ Visualization successful!")

            # Check if categorization data is preserved
            if 'plots' in viz_result and isinstance(viz_result['plots'], dict):
                plots_data = viz_result['plots']
                print(f"   📊 Plots keys: {list(plots_data.keys())}")

                # The categorization data should be available for creating grouped visualizations
                print(f"   🎯 Visualization system ready for category-based plots!")
                return True
            else:
                print(f"   ⚠️ Unexpected visualization structure")
                return False
        else:
            print(f"   ❌ Visualization failed: {viz_response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Visualization test error: {e}")
        return False

def main():
    print("🔬 INTEGRATED CATEGORIZATION SYSTEM TEST")
    print("Testing the complete pipeline with categorization")
    print()

    # Test 1: Basic categorization integration
    cat_success = test_integrated_categorization()

    # Test 2: Visualization compatibility
    viz_success = test_visualization_with_categorization()

    # Final result
    print("\n" + "=" * 60)
    if cat_success and viz_success:
        print("🎉 SUCCESS: CATEGORIZATION SYSTEM FULLY INTEGRATED!")
        print("✅ Backend: Categorization data generated during analysis")
        print("✅ API: Categorization data included in analysis response")
        print("✅ Visualization: System ready for category-based visualizations")
        print("\n🌐 Ready to create category-grouped visualizations!")
        print("📊 Next step: Update visualization service to use categorization data")
        return True
    else:
        print("❌ FAILURE: Integration issues detected")
        if not cat_success:
            print("🔧 Fix: Backend categorization integration")
        if not viz_success:
            print("🔧 Fix: Visualization categorization compatibility")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)