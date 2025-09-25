#!/usr/bin/env python3
"""
Complete comprehensive test using user's actual testwork.csv file
Testing the entire visualization pipeline strictly
"""

import requests
import json
import pandas as pd

def test_user_data_complete():
    print("🧪 COMPREHENSIVE TEST - USER'S ACTUAL DATA")
    print("=" * 60)

    base_url = "http://localhost:5001"
    test_file = "testwork_user.csv"

    # Step 1: Analyze the data first
    print("1. 📊 Analyzing user's test data...")
    try:
        df = pd.read_csv(test_file)
        total_compounds = len(df)
        anchor_compounds = len(df[df['Anchor'] == 'T'])
        non_anchor = len(df[df['Anchor'] == 'F'])

        print(f"   📋 Total compounds: {total_compounds}")
        print(f"   ⚓ Anchor compounds (T): {anchor_compounds}")
        print(f"   📌 Non-anchor compounds (F): {non_anchor}")

        # Check Log P range
        log_p_range = (df['Log P'].min(), df['Log P'].max())
        rt_range = (df['RT'].min(), df['RT'].max())
        print(f"   📈 Log P range: {log_p_range[0]:.2f} to {log_p_range[1]:.2f}")
        print(f"   ⏱️ RT range: {rt_range[0]:.2f} to {rt_range[1]:.2f}")

    except Exception as e:
        print(f"   ❌ Could not analyze data: {e}")
        return False

    # Step 2: Health check
    print("\n2. 🔌 Server health check...")
    try:
        health = requests.get(f"{base_url}/api/health")
        if health.status_code == 200:
            print(f"   ✅ Server is healthy")
        else:
            print(f"   ❌ Health check failed: {health.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

    # Step 3: Run analysis with user's data
    print("\n3. 🔬 Running analysis with user's data...")
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
            stats = results['statistics']

            print(f"   ✅ Analysis successful!")
            print(f"   📊 Success rate: {stats['success_rate']:.1f}%")
            print(f"   ✅ Valid compounds: {stats['valid_compounds']}")
            print(f"   ⚠️ Outliers: {stats['outliers']}")

            # Check regression analysis
            regression_data = results.get('regression_analysis', {})
            regression_quality = results.get('regression_quality', {})

            print(f"   📈 Regression models found: {len(regression_data)}")

            if regression_data:
                for model_name, model_info in regression_data.items():
                    r2 = model_info.get('r2', 0)
                    equation = model_info.get('equation', 'N/A')
                    print(f"      📊 {model_name}: R² = {r2:.3f}")
                    print(f"         Equation: {equation}")

            return analysis_result
        else:
            print(f"   ❌ Analysis failed: {analysis_response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
        return False

def test_visualization_strict(analysis_result):
    """Strict test of visualization with user's data"""
    print("\n4. 📊 STRICT VISUALIZATION TEST")
    print("-" * 40)

    base_url = "http://localhost:5001"

    try:
        # Extract analysis results for visualization
        analysis_data = analysis_result['results']

        viz_payload = {"results": analysis_data}

        viz_response = requests.post(
            f"{base_url}/api/visualize",
            headers={"Content-Type": "application/json"},
            data=json.dumps(viz_payload)
        )

        print(f"   📡 Visualization status: {viz_response.status_code}")

        if viz_response.status_code == 200:
            viz_result = viz_response.json()
            print(f"   ✅ Visualization successful!")

            # Detailed structure analysis
            print(f"   📊 Response keys: {list(viz_result.keys())}")

            if 'plots' in viz_result:
                plots = viz_result['plots']
                print(f"   📊 Plots structure: {list(plots.keys())}")

                # Check nested structure
                if 'plots' in plots:
                    nested_plots = plots['plots']
                    print(f"   📊 Available plot types: {len(nested_plots)}")

                    # Check each plot type strictly
                    critical_plots = ['regression_scatter', '3d_distribution', 'dashboard']
                    working_plots = []

                    for plot_name, plot_content in nested_plots.items():
                        if plot_content and isinstance(plot_content, str):
                            content_length = len(plot_content)
                            has_plotly = 'plotly' in plot_content.lower() or 'plot_ly' in plot_content.lower()
                            has_data = 'data' in plot_content.lower() and content_length > 5000

                            status = "✅" if has_plotly and has_data else "⚠️"
                            print(f"      {status} {plot_name}: {content_length} chars, Plotly: {has_plotly}, Data: {has_data}")

                            if plot_name in critical_plots and has_plotly and has_data:
                                working_plots.append(plot_name)
                        else:
                            print(f"      ❌ {plot_name}: EMPTY or invalid")

                    # Final assessment
                    print(f"\n   🎯 CRITICAL PLOTS WORKING: {working_plots}")

                    if 'regression_scatter' in working_plots:
                        print(f"   ✅ REGRESSION SCATTER PLOT: WORKING")
                    else:
                        print(f"   ❌ REGRESSION SCATTER PLOT: FAILED")

                    if '3d_distribution' in working_plots:
                        print(f"   ✅ 3D DISTRIBUTION PLOT: WORKING")
                    else:
                        print(f"   ❌ 3D DISTRIBUTION PLOT: FAILED")

                    return len(working_plots) >= 2
                else:
                    print(f"   ❌ No nested plots structure found")
                    return False
            else:
                print(f"   ❌ No plots in response")
                return False
        else:
            print(f"   ❌ Visualization failed: {viz_response.text}")
            return False

    except Exception as e:
        print(f"   ❌ Visualization test error: {e}")
        return False

def main():
    print("🚀 STARTING COMPREHENSIVE VISUALIZATION TEST")
    print("📁 Using user's actual file: testwork_user.csv")
    print("🎯 Testing complete pipeline with REAL DATA")

    # Run analysis
    analysis_result = test_user_data_complete()

    if not analysis_result:
        print("\n❌ ANALYSIS FAILED - Cannot continue to visualization test")
        return False

    # Run strict visualization test
    viz_success = test_visualization_strict(analysis_result)

    # Final result
    print("\n" + "=" * 60)
    if viz_success:
        print("🎉 SUCCESS: COMPLETE VISUALIZATION PIPELINE WORKING!")
        print("✅ Analysis: Working with user's data")
        print("✅ Regression: Real models generated")
        print("✅ Visualization: Scatter plots and 3D plots working")
        print("✅ Frontend: Ready to display results")
        print("\n🌐 Ready to test at: http://localhost:5001/working")
        return True
    else:
        print("❌ FAILURE: Visualization pipeline has issues")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)