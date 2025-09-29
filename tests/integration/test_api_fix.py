#!/usr/bin/env python3
"""
Test the API with fixed regression
"""

import requests
import json

def test_analysis_api():
    print("🧪 Testing Fixed Analysis API")
    print("=" * 30)

    # Test health
    print("1. Health check...")
    health = requests.get("http://localhost:5001/api/health")
    print(f"   Status: {health.status_code}")

    # Test analysis with real file
    print("2. Analysis test...")
    with open("data/sample/testwork.csv", "rb") as f:
        files = {"file": ("testwork.csv", f, "text/csv")}
        data = {
            "data_type": "Porcine",
            "outlier_threshold": 2.5,  # Use fixed values
            "r2_threshold": 0.75,      # Use fixed values
            "rt_tolerance": 0.1
        }

        response = requests.post("http://localhost:5001/api/analyze", files=files, data=data)

    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        stats = result['results']['statistics']
        print(f"   ✅ Analysis successful!")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"   Valid compounds: {stats['valid_compounds']}")
        print(f"   Outliers: {stats['outliers']}")

        if stats['success_rate'] > 50:
            print(f"   🎉 REGRESSION ANALYSIS IS WORKING!")
            return True
    else:
        print(f"   ❌ Analysis failed: {response.text}")

    return False

if __name__ == "__main__":
    success = test_analysis_api()
    exit(0 if success else 1)