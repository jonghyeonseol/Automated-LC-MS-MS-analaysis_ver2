#!/usr/bin/env python3
"""
Debug the visualization data structure
"""

import requests
import json

def debug_visualization_structure():
    print("🔍 Debugging Visualization Data Structure")
    print("=" * 50)

    # Run analysis
    with open("data/sample/testwork.csv", "rb") as f:
        files = {"file": ("testwork.csv", f, "text/csv")}
        data = {
            "data_type": "Porcine",
            "outlier_threshold": 2.5,
            "r2_threshold": 0.75,
            "rt_tolerance": 0.1
        }

        analysis_response = requests.post("http://localhost:5001/api/analyze", files=files, data=data)

    analysis_result = analysis_response.json()
    analysis_data = analysis_result['results']

    # Test visualization
    viz_payload = {"results": analysis_data}
    viz_response = requests.post(
        "http://localhost:5001/api/visualize",
        headers={"Content-Type": "application/json"},
        data=json.dumps(viz_payload)
    )

    viz_result = viz_response.json()

    print("📊 Visualization Response Structure:")
    print(f"Top level keys: {list(viz_result.keys())}")
    print()

    if 'plots' in viz_result:
        plots = viz_result['plots']
        print(f"plots key type: {type(plots)}")
        print(f"plots keys: {list(plots.keys())}")
        print()

        # Check what the frontend is looking for
        frontend_expects = ['regression_scatter', '3d_distribution']

        print("🔍 What frontend expects vs what we have:")
        for expected in frontend_expects:
            if expected in plots:
                print(f"✅ {expected}: Found!")
                content = plots[expected]
                if content:
                    print(f"   Content length: {len(str(content))}")
                else:
                    print(f"   ❌ Content is empty!")
            else:
                print(f"❌ {expected}: MISSING!")

        print()
        print("📋 Available plot keys:")
        for key in plots.keys():
            content = plots[key]
            if isinstance(content, str) and len(content) > 1000:  # Likely contains plot HTML
                print(f"   ✅ {key}: {len(content)} characters (likely a plot)")
            else:
                print(f"   📝 {key}: {content}")

    return viz_result

if __name__ == "__main__":
    result = debug_visualization_structure()