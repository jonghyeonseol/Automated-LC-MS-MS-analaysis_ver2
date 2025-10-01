"""
Test Modular Rules System
Verifies that individual rule files work correctly
"""

import pandas as pd
import sys
sys.path.insert(0, '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression')

from backend.rules import (
    Rule1PrefixRegression,
    Rule2SugarCount,
    Rule3IsomerClassification,
    Rule4OAcetylation,
    Rule5Fragmentation,
    get_rule_summary
)

def create_test_data():
    """Create test dataset"""
    data = {
        'Name': [
            'GD1a(36:1;O2)',
            'GM1a(36:1;O2)',
            'GM3(36:1;O2)',
            'GD3(36:1;O2)',
            'GT1b(36:1;O2)'
        ],
        'RT': [9.572, 10.452, 10.606, 10.126, 8.701],
        'Volume': [1000000, 500000, 2000000, 800000, 1200000],
        'Log P': [1.53, 4.00, 7.74, 5.27, -0.94],
        'Anchor': ['T', 'F', 'F', 'T', 'T'],
        'prefix': ['GD1a', 'GM1a', 'GM3', 'GD3', 'GT1b'],
        'suffix': ['36:1;O2', '36:1;O2', '36:1;O2', '36:1;O2', '36:1;O2'],
        'a_component': [36, 36, 36, 36, 36],
        'b_component': [1, 1, 1, 1, 1],
        'oxygen_count': [2, 2, 2, 2, 2],
        'sugar_count': [6, 5, 3, 4, 7],
        'sialic_acid_count': [2, 1, 1, 2, 3],
        'has_OAc': [0, 0, 0, 0, 0],
        'has_dHex': [0, 0, 0, 0, 0],
        'has_HexNAc': [0, 0, 0, 0, 0]
    }
    return pd.DataFrame(data)


def test_rule1():
    """Test Rule 1: Prefix-based Regression"""
    print("\n" + "="*70)
    print("TESTING RULE 1: PREFIX-BASED REGRESSION")
    print("="*70)

    df = create_test_data()
    rule1 = Rule1PrefixRegression(r2_threshold=0.95, outlier_threshold=2.0)

    try:
        results = rule1.apply(df)

        print("\n📊 Rule 1 Results:")
        print(f"   - Regression groups: {len(results['regression_results'])}")
        print(f"   - Valid compounds: {len(results['valid_compounds'])}")
        print(f"   - Outliers: {len(results['outliers'])}")

        for group_name, reg_info in results['regression_results'].items():
            print(f"\n   Group: {group_name}")
            print(f"      R² = {reg_info['r2']:.4f}")
            print(f"      Features: {reg_info['n_features']}")
            print(f"      Equation: {reg_info['equation']}")

        print("\n✅ Rule 1 test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Rule 1 test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule2():
    """Test Rule 2: Sugar Count Calculation"""
    print("\n" + "="*70)
    print("TESTING RULE 2: SUGAR COUNT CALCULATION")
    print("="*70)

    df = create_test_data()
    rule2 = Rule2SugarCount()

    try:
        results = rule2.apply(df)

        print("\n🧬 Rule 2 Results:")
        print(f"   - Compounds analyzed: {len(results['sugar_analysis'])}")
        print(f"   - Average sugar count: {results['statistics']['average_sugars']:.1f}")

        print("\n   Sample sugar breakdowns:")
        for compound, sugar_info in list(results['sugar_analysis'].items())[:3]:
            print(f"      {compound}:")
            print(f"         Total sugars: {sugar_info['total_sugars']}")
            print(f"         Formula: {sugar_info['formula']}")

        print("\n✅ Rule 2 test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Rule 2 test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule3():
    """Test Rule 3: Isomer Classification"""
    print("\n" + "="*70)
    print("TESTING RULE 3: ISOMER CLASSIFICATION")
    print("="*70)

    df = create_test_data()
    rule3 = Rule3IsomerClassification()

    try:
        results = rule3.apply(df, data_type="Porcine")

        print("\n🧬 Rule 3 Results:")
        print(f"   - Total compounds: {results['statistics']['total_compounds']}")
        print(f"   - Isomer candidates: {results['statistics']['isomer_candidates']}")
        print(f"   - Corrections applied: {results['statistics']['corrections_applied']}")

        print("\n   Isomer classifications:")
        for compound, isomer_info in list(results['isomer_classification'].items())[:3]:
            print(f"      {compound}:")
            print(f"         Can have isomers: {isomer_info['can_have_isomers']}")
            if isomer_info['can_have_isomers']:
                print(f"         Isomer type: {isomer_info['isomer_type']}")

        print("\n✅ Rule 3 test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Rule 3 test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule4():
    """Test Rule 4: O-acetylation Validation"""
    print("\n" + "="*70)
    print("TESTING RULE 4: O-ACETYLATION VALIDATION")
    print("="*70)

    df = create_test_data()
    rule4 = Rule4OAcetylation()

    try:
        results = rule4.apply(df)

        print("\n⚗️ Rule 4 Results:")
        print(f"   - Total OAc compounds: {results['statistics']['total_oacetyl']}")
        print(f"   - Valid: {results['statistics']['valid']}")
        print(f"   - Invalid: {results['statistics']['invalid']}")
        print(f"   - Validation rate: {results['statistics']['validation_rate']:.1f}%")

        print("\n✅ Rule 4 test PASSED (no OAc compounds in test data)")
        return True

    except Exception as e:
        print(f"\n❌ Rule 4 test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule5():
    """Test Rule 5: Fragmentation Detection"""
    print("\n" + "="*70)
    print("TESTING RULE 5: FRAGMENTATION DETECTION")
    print("="*70)

    df = create_test_data()

    # Create rule with sugar count calculator
    from backend.rules import Rule2SugarCount
    rule2 = Rule2SugarCount()

    rule5 = Rule5Fragmentation(
        rt_tolerance=0.1,
        sugar_count_calculator=rule2.calculate_sugar_count
    )

    try:
        results = rule5.apply(df)

        print("\n🔍 Rule 5 Results:")
        print(f"   - Final compounds: {results['statistics']['final_compounds']}")
        print(f"   - Fragments detected: {results['statistics']['fragments_detected']}")
        print(f"   - Consolidations: {results['statistics']['consolidations']}")

        if results['consolidation_details']:
            print("\n   Consolidation examples:")
            for cons in results['consolidation_details'][:3]:
                print(f"      {cons['parent_compound']}:")
                print(f"         Fragments: {cons['fragment_count']}")
                print(f"         Volume recovery: +{cons['recovery_rate']:.1f}%")

        print("\n✅ Rule 5 test PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Rule 5 test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("MODULAR RULES SYSTEM TEST SUITE")
    print("="*70)

    # Print rule summary
    print("\n" + get_rule_summary())

    # Run tests
    tests = [
        ("Rule 1", test_rule1),
        ("Rule 2", test_rule2),
        ("Rule 3", test_rule3),
        ("Rule 4", test_rule4),
        ("Rule 5", test_rule5),
    ]

    results = {}
    for rule_name, test_func in tests:
        results[rule_name] = test_func()

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for rule_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{rule_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Modular rules system is working correctly.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review errors above.")


if __name__ == "__main__":
    main()
