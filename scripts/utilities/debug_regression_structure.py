#!/usr/bin/env python3
"""
Debug the regression analysis structure to understand the data flow
"""

import requests
import json

def debug_regression_structure():
    print("🔍 DEBUGGING REGRESSION ANALYSIS STRUCTURE")
    print("=" * 50)

    base_url = "http://localhost:5001"

    # Run analysis and examine detailed structure
    print("1. Running analysis with detailed structure inspection...")

    try:
        with open("data/sample/testwork.csv", "rb") as f:
            files = {"file": ("testwork.csv", f, "text/csv")}
            data = {
                "data_type": "Porcine",
                "outlier_threshold": 2.5,
                "r2_threshold": 0.75,
                "rt_tolerance": 0.1
            }

            response = requests.post(f"{base_url}/api/analyze", files=files, data=data)

        if response.status_code != 200:
            print(f"   ❌ Analysis failed: {response.text}")
            return

        result = response.json()
        analysis_data = result['results']

        print(f"   ✅ Analysis successful")
        print(f"   📊 Top level keys: {list(analysis_data.keys())}")

        # Examine each key in detail
        for key, value in analysis_data.items():
            print(f"\n   🔍 Key: {key}")
            print(f"      Type: {type(value)}")

            if isinstance(value, dict):
                print(f"      Dict keys: {list(value.keys())}")

                # Look for regression results specifically
                if 'regression' in key.lower():
                    print(f"      📈 REGRESSION DATA FOUND:")
                    for subkey, subvalue in value.items():
                        print(f"         - {subkey}: {type(subvalue)}")
                        if isinstance(subvalue, dict) and subvalue:
                            print(f"           Contents: {list(subvalue.keys())}")

                            # Check for individual regression models
                            for model_name, model_data in subvalue.items():
                                if isinstance(model_data, dict) and 'r2' in str(model_data):
                                    print(f"           📊 Model '{model_name}': {model_data}")

            elif isinstance(value, list):
                print(f"      List length: {len(value)}")
                if value:
                    print(f"      First item type: {type(value[0])}")
            else:
                print(f"      Value: {str(value)[:100]}...")

        # Check if regression_analysis contains the models
        if 'regression_analysis' in analysis_data:
            regression_data = analysis_data['regression_analysis']
            print(f"\n   🎯 DETAILED REGRESSION ANALYSIS:")

            if isinstance(regression_data, dict):
                for key, value in regression_data.items():
                    print(f"      {key}: {type(value)}")
                    if isinstance(value, dict) and value:
                        print(f"         Keys: {list(value.keys())}")

                        # Look for actual regression models
                        if any('r2' in str(v) or 'equation' in str(v) for v in value.values()):
                            print(f"         🎉 FOUND REGRESSION MODELS!")
                            for model_key, model_value in value.items():
                                print(f"            {model_key}: {model_value}")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_regression_structure()