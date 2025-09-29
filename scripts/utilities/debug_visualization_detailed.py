#!/usr/bin/env python3
"""
Detailed diagnosis of the visualization issue
"""

import requests
import json

def debug_visualization():
    print("🔍 DETAILED VISUALIZATION DIAGNOSIS")
    print("=" * 50)

    base_url = "http://localhost:5001"

    # Step 1: Run analysis
    print("1. Running analysis...")
    try:
        with open("data/sample/testwork.csv", "rb") as f:
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
            return

        analysis_result = analysis_response.json()
        print(f"   ✅ Analysis successful")

        # Debug analysis results structure
        analysis_data = analysis_result['results']
        print(f"   📊 Analysis result keys: {list(analysis_data.keys())}")

        # Check if there are regression results
        rule1_key = None
        for key in analysis_data.keys():
            if 'rule1' in key.lower():
                rule1_key = key
                break

        if rule1_key and 'regression_results' in analysis_data[rule1_key]:
            regression_results = analysis_data[rule1_key]['regression_results']
            print(f"   📈 Regression models found: {len(regression_results)}")
            for name, info in regression_results.items():
                print(f"      - {name}: R² = {info.get('r2', 'N/A')}")
        else:
            print(f"   ❌ NO REGRESSION MODELS FOUND!")
            print(f"   Available keys in analysis: {list(analysis_data.keys())}")
            if rule1_key:
                print(f"   Rule1 keys: {list(analysis_data[rule1_key].keys())}")

    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
        return

    # Step 2: Test visualization with detailed debugging
    print("\n2. Testing visualization...")
    try:
        viz_payload = {"results": analysis_data}

        viz_response = requests.post(
            f"{base_url}/api/visualize",
            headers={"Content-Type": "application/json"},
            data=json.dumps(viz_payload)
        )

        print(f"   Status: {viz_response.status_code}")

        if viz_response.status_code == 200:
            viz_result = viz_response.json()
            print(f"   ✅ Visualization response received")

            # Detailed structure analysis
            print(f"   📊 Top level keys: {list(viz_result.keys())}")

            if 'plots' in viz_result:
                plots = viz_result['plots']
                print(f"   📊 Plots structure type: {type(plots)}")
                print(f"   📊 Plots keys: {list(plots.keys())}")

                # Check nested structure
                if 'plots' in plots:
                    nested_plots = plots['plots']
                    print(f"   📊 NESTED plots found: {list(nested_plots.keys())}")

                    # Check each plot's content
                    for plot_name, plot_content in nested_plots.items():
                        if plot_content and isinstance(plot_content, str):
                            print(f"      ✅ {plot_name}: {len(plot_content)} chars")
                            # Check if it's actually HTML/Plotly
                            if 'plotly' in plot_content.lower() or 'div' in plot_content.lower():
                                print(f"         📈 Contains Plotly content")
                            else:
                                print(f"         ❌ No Plotly content detected")
                        else:
                            print(f"      ❌ {plot_name}: EMPTY or invalid type")
                else:
                    # Direct plots (old structure)
                    for plot_name, plot_content in plots.items():
                        if plot_content and isinstance(plot_content, str):
                            print(f"      ✅ {plot_name}: {len(plot_content)} chars")
                        else:
                            print(f"      ❌ {plot_name}: EMPTY")
            else:
                print(f"   ❌ NO 'plots' key in response!")
                print(f"   Available keys: {list(viz_result.keys())}")
        else:
            print(f"   ❌ Visualization failed: {viz_response.status_code}")
            print(f"   Error: {viz_response.text}")

    except Exception as e:
        print(f"   ❌ Visualization error: {e}")

    # Step 3: Check specific frontend requirements
    print("\n3. Frontend compatibility check...")
    if 'viz_result' in locals() and viz_result and 'plots' in viz_result:
        plots_data = viz_result['plots'].get('plots', viz_result['plots'])

        frontend_expectations = [
            'regression_scatter',
            '3d_distribution',
            'scatter',
            'dashboard'
        ]

        found_plots = []
        for expected in frontend_expectations:
            if expected in plots_data and plots_data[expected]:
                found_plots.append(expected)
                print(f"   ✅ {expected}: Available")
            else:
                print(f"   ❌ {expected}: Missing")

        if found_plots:
            print(f"   📊 Frontend will find: {found_plots}")
        else:
            print(f"   ❌ NO PLOTS MATCH FRONTEND EXPECTATIONS!")

if __name__ == "__main__":
    debug_visualization()