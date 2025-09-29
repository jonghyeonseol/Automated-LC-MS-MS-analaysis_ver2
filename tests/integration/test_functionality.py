#!/usr/bin/env python3
"""
Test script to verify API functionality
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5001"

def test_health():
    """Test health endpoint"""
    print("🔌 Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data['status']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_analysis():
    """Test analysis endpoint with sample file"""
    print("🚀 Testing analysis endpoint...")
    try:
        # Read sample CSV file
        with open("data/sample/testwork.csv", "rb") as f:
            files = {"file": ("testwork.csv", f, "text/csv")}
            data = {
                "data_type": "Porcine",
                "outlier_threshold": 3.0,
                "r2_threshold": 0.99,
                "rt_tolerance": 0.1
            }

            response = requests.post(f"{BASE_URL}/api/analyze", files=files, data=data)

        if response.status_code == 200:
            result = response.json()
            if "error" in result:
                print(f"❌ Analysis error: {result['error']}")
                return False
            else:
                stats = result['results']['statistics']
                print(f"✅ Analysis completed! Success rate: {stats['success_rate']:.1f}%")
                print(f"   Valid compounds: {stats['valid_compounds']}, Outliers: {stats['outliers']}")
                return result['results']
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Analysis test error: {e}")
        return False

def test_visualization(results):
    """Test visualization endpoint"""
    print("📊 Testing visualization endpoint...")
    try:
        payload = {"results": results}
        response = requests.post(
            f"{BASE_URL}/api/visualize",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )

        if response.status_code == 200:
            result = response.json()
            if "error" in result:
                print(f"❌ Visualization error: {result['error']}")
                return False
            else:
                print("✅ Visualization generated successfully!")
                return True
        else:
            print(f"❌ Visualization failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Visualization test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🧬 Starting LC-MS-MS API functionality tests...\n")

    # Test 1: Health check
    if not test_health():
        print("\n❌ Health check failed - aborting tests")
        sys.exit(1)

    print()

    # Test 2: Analysis
    results = test_analysis()
    if not results:
        print("\n❌ Analysis test failed - aborting remaining tests")
        sys.exit(1)

    print()

    # Test 3: Visualization
    if not test_visualization(results):
        print("\n❌ Visualization test failed")
        sys.exit(1)

    print("\n✅ All API tests passed! The functionality is working correctly.")

if __name__ == "__main__":
    main()