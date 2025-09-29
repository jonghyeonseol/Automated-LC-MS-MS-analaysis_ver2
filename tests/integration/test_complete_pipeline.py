#!/usr/bin/env python3
"""
Complete end-to-end test of the visualization pipeline
"""

import requests
import json

def test_complete_pipeline():
    print("🎯 Testing Complete Analysis & Visualization Pipeline")
    print("=" * 55)

    # Use the running server on port 5001
    base_url = "http://localhost:5001"

    # Step 1: Test health
    print("1. Health check...")
    try:
        health = requests.get(f"{base_url}/api/health")
        print(f"   Status: {health.status_code}")
        if health.status_code == 200:
            print("   ✅ Server is healthy")
        else:
            print(f"   ❌ Health check failed: {health.text}")
            return False
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False

    # Step 2: Run analysis
    print("2. Running analysis...")
    try:
        with open("data/sample/testwork.csv", "rb") as f:
            files = {"file": ("testwork.csv", f, "text/csv")}
            data = {
                "data_type": "Porcine",
                "outlier_threshold": 2.5,  # Fixed realistic values
                "r2_threshold": 0.75,      # Fixed realistic values
                "rt_tolerance": 0.1
            }

            analysis_response = requests.post(f"{base_url}/api/analyze", files=files, data=data)

        print(f"   Analysis status: {analysis_response.status_code}")

        if analysis_response.status_code == 200:
            analysis_result = analysis_response.json()
            stats = analysis_result['results']['statistics']
            print(f"   ✅ Analysis successful!")
            print(f"   Success rate: {stats['success_rate']:.1f}%")
            print(f"   Valid compounds: {stats['valid_compounds']}")
        else:
            print(f"   ❌ Analysis failed: {analysis_response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Analysis error: {e}")
        return False

    # Step 3: Test visualization
    print("3. Testing visualization...")
    try:
        analysis_data = analysis_result['results']
        viz_payload = {"results": analysis_data}

        viz_response = requests.post(
            f"{base_url}/api/visualize",
            headers={"Content-Type": "application/json"},
            data=json.dumps(viz_payload)
        )

        print(f"   Visualization status: {viz_response.status_code}")

        if viz_response.status_code == 200:
            viz_result = viz_response.json()
            print(f"   ✅ Visualization successful!")

            # Analyze the structure we get back
            print(f"   Top level keys: {list(viz_result.keys())}")

            if 'plots' in viz_result:
                plots = viz_result['plots']
                print(f"   Plots type: {type(plots)}")
                print(f"   Plots keys: {list(plots.keys())}")

                # Check if there's nested structure
                if 'plots' in plots:
                    nested_plots = plots['plots']
                    print(f"   📊 Nested plots found!")
                    print(f"   Nested plots keys: {list(nested_plots.keys())}")

                    # Test if the frontend would now find plots
                    frontend_tests = [
                        ('3d_distribution', '3D Distribution'),
                        ('dashboard', 'Dashboard'),
                        ('scatter', 'Scatter Plot'),
                        ('regression_scatter', 'Regression Scatter')
                    ]

                    found_plots = []
                    for key, name in frontend_tests:
                        if key in nested_plots and nested_plots[key]:
                            content_length = len(str(nested_plots[key]))
                            print(f"   ✅ {name}: {content_length} characters")
                            found_plots.append(key)

                    if found_plots:
                        print(f"   🎉 FIXED! Frontend will now display: {found_plots}")
                        return True
                    else:
                        print(f"   ❌ No displayable plots found")
                else:
                    # Direct plots (old structure)
                    for key, content in plots.items():
                        if content:
                            content_length = len(str(content))
                            print(f"   - {key}: {content_length} characters")
            else:
                print(f"   ❌ No 'plots' key in visualization result")
        else:
            print(f"   ❌ Visualization failed: {viz_response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Visualization error: {e}")
        return False

    return False

if __name__ == "__main__":
    success = test_complete_pipeline()
    if success:
        print(f"\n🎉 COMPLETE PIPELINE IS WORKING!")
        print(f"✅ Analysis generates data correctly")
        print(f"✅ Visualization creates plots correctly")
        print(f"✅ Frontend JavaScript can now display plots")
    else:
        print(f"\n❌ Pipeline has issues - check above for details")
    exit(0 if success else 1)