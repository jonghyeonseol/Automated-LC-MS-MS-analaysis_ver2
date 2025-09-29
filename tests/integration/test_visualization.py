#!/usr/bin/env python3
"""
Test visualization functionality
"""

import requests
import json

def test_visualization():
    print("📊 Testing Visualization Pipeline")
    print("=" * 40)

    # Step 1: Run analysis to get results
    print("1. Running analysis...")
    with open("data/sample/testwork.csv", "rb") as f:
        files = {"file": ("testwork.csv", f, "text/csv")}
        data = {
            "data_type": "Porcine",
            "outlier_threshold": 2.5,
            "r2_threshold": 0.75,
            "rt_tolerance": 0.1
        }

        analysis_response = requests.post("http://localhost:5001/api/analyze", files=files, data=data)

    print(f"   Analysis status: {analysis_response.status_code}")

    if analysis_response.status_code != 200:
        print(f"   ❌ Analysis failed: {analysis_response.text}")
        return False

    analysis_result = analysis_response.json()
    print(f"   ✅ Analysis successful: {analysis_result['results']['statistics']['success_rate']:.1f}% success rate")

    # Step 2: Test visualization
    print("2. Testing visualization...")

    # Extract analysis results for visualization
    analysis_data = analysis_result['results']

    viz_payload = {
        "results": analysis_data
    }

    viz_response = requests.post(
        "http://localhost:5001/api/visualize",
        headers={"Content-Type": "application/json"},
        data=json.dumps(viz_payload)
    )

    print(f"   Visualization status: {viz_response.status_code}")

    if viz_response.status_code == 200:
        viz_result = viz_response.json()
        print(f"   ✅ Visualization successful!")

        # Check what's in the visualization result
        print(f"   Available keys: {list(viz_result.keys())}")

        if 'plots' in viz_result:
            plots = viz_result['plots']
            print(f"   Plot types available: {list(plots.keys())}")

            # Check if plots have actual content
            for plot_name, plot_content in plots.items():
                if plot_content:
                    content_length = len(str(plot_content))
                    print(f"   - {plot_name}: {content_length} characters")

                    # Check if it contains HTML/JavaScript
                    content_str = str(plot_content)
                    has_plotly = 'plotly' in content_str.lower() or 'plot' in content_str.lower()
                    has_div = '<div' in content_str
                    has_script = '<script' in content_str

                    print(f"     * Has Plotly: {has_plotly}")
                    print(f"     * Has HTML div: {has_div}")
                    print(f"     * Has script: {has_script}")
                else:
                    print(f"   - {plot_name}: EMPTY!")

            return True
        else:
            print(f"   ❌ No 'plots' key in visualization result")
            print(f"   Result keys: {list(viz_result.keys())}")
    else:
        print(f"   ❌ Visualization failed: {viz_response.text}")

    return False

if __name__ == "__main__":
    success = test_visualization()
    if success:
        print(f"\n✅ Visualization pipeline is working!")
    else:
        print(f"\n❌ Visualization has issues - check above for details")
    exit(0 if success else 1)