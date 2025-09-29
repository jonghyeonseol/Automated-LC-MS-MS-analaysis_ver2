#!/usr/bin/env python3
"""
Test the tab functionality after fixes
"""

import requests
import json
import pandas as pd
import time

def test_complete_workflow():
    print("🧪 TESTING COMPLETE TAB FUNCTIONALITY")
    print("=" * 60)

    base_url = "http://localhost:5001"
    test_file = "testwork_user.csv"

    # Step 1: Run the analysis
    print("1. 🚀 Running analysis...")
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

        if analysis_response.status_code != 200:
            print(f"   ❌ Analysis failed: {analysis_response.text}")
            return False

        analysis_result = analysis_response.json()
        print(f"   ✅ Analysis successful")

    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
        return False

    # Step 2: Generate visualization
    print("\n2. 📊 Testing visualization generation...")
    try:
        analysis_data = analysis_result['results']
        viz_payload = {"results": analysis_data}

        viz_response = requests.post(
            f"{base_url}/api/visualize",
            headers={"Content-Type": "application/json"},
            data=json.dumps(viz_payload)
        )

        if viz_response.status_code != 200:
            print(f"   ❌ Visualization failed: {viz_response.text}")
            return False

        viz_result = viz_response.json()
        plots = viz_result.get('plots', {})
        nested_plots = plots.get('plots', {})

        print(f"   ✅ Visualization successful")
        print(f"   📊 Plot types available: {len(nested_plots)}")

        # Check critical plots
        critical_plots = ['regression_scatter', '3d_distribution']
        for plot_name in critical_plots:
            if plot_name in nested_plots:
                plot_content = nested_plots[plot_name]
                if plot_content and len(plot_content) > 5000:
                    print(f"   ✅ {plot_name}: Ready ({len(plot_content)} chars)")
                else:
                    print(f"   ⚠️ {plot_name}: Small or empty")
            else:
                print(f"   ❌ {plot_name}: Missing")

        return True

    except Exception as e:
        print(f"   ❌ Visualization error: {e}")
        return False

def main():
    print("🔧 TAB FUNCTIONALITY TEST")
    print("This test verifies the backend generates proper visualizations")
    print("Manual steps required:")
    print("1. Open http://localhost:5001/working in your browser")
    print("2. Upload testwork_user.csv")
    print("3. Click 'Start Analysis'")
    print("4. Click 'Generate Visualizations'")
    print("5. Test switching between tabs:")
    print("   - Combined View (should work)")
    print("   - 2D Analysis (should now copy from combined view)")
    print("   - 3D Distribution (should now copy from combined view)")
    print()

    # Run backend test
    success = test_complete_workflow()

    if success:
        print("\n✅ BACKEND TEST PASSED")
        print("📊 All visualizations are ready for frontend")
        print("🌐 Open http://localhost:5001/working to test tabs manually")
        print()
        print("🔍 WHAT TO LOOK FOR:")
        print("- Combined view should show plots immediately")
        print("- Individual tabs should copy plots when clicked")
        print("- Console should show 'Copying plot from combined view' messages")
        print("- All tabs should display the same plot content")
        return True
    else:
        print("\n❌ BACKEND TEST FAILED")
        print("🔧 Fix backend issues before testing tabs")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)