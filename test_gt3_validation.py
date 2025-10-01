"""
Test GT3 Validation - Verifying True Positives
Validates that GT3(36:1;O2) and GT3(38:1;O2) are correctly identified as VALID compounds
"""

import pandas as pd
import sys
sys.path.insert(0, '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression')

from backend.services.ganglioside_processor_modular import GangliosideProcessorModular


def create_gt3_test_data():
    """
    Create test dataset including the GT3 examples provided by user

    User specification:
    - GT3(36:1;O2), Log P: 2.8, RT: 9.599   → TRUE POSITIVE
    - GT3(38:1;O2), Log P: 3.88, RT: 11.126 → TRUE POSITIVE

    These should BOTH be valid because:
    1. Same prefix (GT3 = trisialoganglioside)
    2. Different carbon chains (36 vs 38) - EXPECTED variation
    3. RT increases with carbon chain - EXPECTED chemistry
    4. Log P increases with carbon chain - EXPECTED chemistry
    5. Multiple regression captures this relationship
    """
    data = {
        'Name': [
            # User-specified GT3 compounds (MUST be valid)
            'GT3(36:1;O2)',
            'GT3(38:1;O2)',

            # Additional GT3 compounds for regression
            'GT3(34:1;O2)',  # Shorter chain
            'GT3(40:1;O2)',  # Longer chain

            # Other compounds for comparison
            'GD1a(36:1;O2)',
            'GM1a(36:1;O2)',
            'GM3(36:1;O2)',
            'GD3(36:1;O2)',
            'GT1b(36:1;O2)',
        ],
        'RT': [
            # GT3 series - RT increases with carbon chain
            9.599,   # GT3(36:1;O2) - User specified
            11.126,  # GT3(38:1;O2) - User specified
            8.2,     # GT3(34:1;O2) - Shorter chain = lower RT
            12.5,    # GT3(40:1;O2) - Longer chain = higher RT

            # Other compounds
            9.572,   # GD1a
            10.452,  # GM1a
            10.606,  # GM3
            10.126,  # GD3
            8.701,   # GT1b
        ],
        'Volume': [
            1000000, 800000, 600000, 1200000,  # GT3 series
            1000000, 500000, 2000000, 800000, 1200000  # Others
        ],
        'Log P': [
            # GT3 series - Log P increases with carbon chain
            2.8,     # GT3(36:1;O2) - User specified
            3.88,    # GT3(38:1;O2) - User specified
            1.5,     # GT3(34:1;O2) - Shorter chain = lower Log P
            5.0,     # GT3(40:1;O2) - Longer chain = higher Log P

            # Other compounds
            1.53,    # GD1a
            4.00,    # GM1a
            7.74,    # GM3
            5.27,    # GD3
            -0.94,   # GT1b
        ],
        'Anchor': [
            # GT3 series - mix of anchors
            'T', 'T', 'T', 'F',  # 3 anchors for regression

            # Others
            'T', 'F', 'F', 'T', 'T'
        ]
    }
    return pd.DataFrame(data)


def test_gt3_validation():
    """
    Test that GT3 examples are correctly identified as VALID
    """
    print("="*80)
    print("GT3 VALIDATION TEST")
    print("="*80)
    print("\nUser Specification:")
    print("  GT3(36:1;O2), Log P: 2.8, RT: 9.599   → MUST be VALID")
    print("  GT3(38:1;O2), Log P: 3.88, RT: 11.126 → MUST be VALID")
    print("\nRationale:")
    print("  ✓ Same prefix (GT3)")
    print("  ✓ Different carbon chains (36 vs 38) - EXPECTED")
    print("  ✓ RT increases with carbon chain - EXPECTED chemistry")
    print("  ✓ Log P increases with carbon chain - EXPECTED chemistry")
    print("  ✓ Multiple regression accounts for carbon chain variation")
    print("="*80)

    # Create test data
    df = create_gt3_test_data()

    print(f"\n📊 Test Dataset Created:")
    print(f"   Total compounds: {len(df)}")
    print(f"   GT3 compounds: {len(df[df['Name'].str.startswith('GT3')])}")
    print(f"   Anchor compounds: {len(df[df['Anchor'] == 'T'])}")

    # Display GT3 compounds
    print("\n📋 GT3 Compounds in Dataset:")
    gt3_df = df[df['Name'].str.startswith('GT3')].copy()
    for _, row in gt3_df.iterrows():
        print(f"   {row['Name']:20s} | RT: {row['RT']:7.3f} | Log P: {row['Log P']:6.2f} | Anchor: {row['Anchor']}")

    # Initialize processor with realistic settings
    print("\n🔧 Initializing Modular Processor...")
    processor = GangliosideProcessorModular(
        r2_threshold=0.80,      # Realistic for LC-MS
        outlier_threshold=3.0,  # Conservative (3σ)
        rt_tolerance=0.1
    )

    # Process data
    print("\n🧬 Processing data...")
    results = processor.process_data(df, data_type="Porcine")

    # Check GT3 classification
    print("\n" + "="*80)
    print("VALIDATION RESULTS")
    print("="*80)

    valid_names = [c['Name'] for c in results['valid_compounds']]
    outlier_names = [c['Name'] for c in results['outliers']]

    # Check user-specified GT3 compounds
    gt3_36 = 'GT3(36:1;O2)'
    gt3_38 = 'GT3(38:1;O2)'

    gt3_36_status = "✅ VALID" if gt3_36 in valid_names else "❌ OUTLIER (WRONG!)"
    gt3_38_status = "✅ VALID" if gt3_38 in valid_names else "❌ OUTLIER (WRONG!)"

    print(f"\n{gt3_36:20s}: {gt3_36_status}")
    print(f"{gt3_38:20s}: {gt3_38_status}")

    # Display GT3 regression details
    print("\n📊 GT3 Regression Analysis:")
    if 'GT3' in results['regression_analysis']:
        gt3_reg = results['regression_analysis']['GT3']
        print(f"   R² = {gt3_reg['r2']:.4f}")
        print(f"   Features used: {gt3_reg['n_features']}")
        print(f"   Feature names: {', '.join(gt3_reg['feature_names'][:5])}")
        print(f"   Equation: {gt3_reg['equation'][:100]}...")
        print(f"   Samples: {gt3_reg['n_samples']}")
        print(f"   Anchors: {gt3_reg['n_anchors']}")
    else:
        print("   ⚠️ GT3 not found in regression results")
        print("   Available groups:", list(results['regression_analysis'].keys()))

    # Show all GT3 compound classifications
    print("\n📋 All GT3 Classifications:")
    for name in gt3_df['Name']:
        if name in valid_names:
            status = "✅ VALID"
            # Find in valid compounds
            compound = next(c for c in results['valid_compounds'] if c['Name'] == name)
            if 'predicted_rt' in compound:
                print(f"   {name:20s}: {status}")
                print(f"      Actual RT: {compound['RT']:.3f}")
                print(f"      Predicted RT: {compound['predicted_rt']:.3f}")
                print(f"      Residual: {compound.get('residual', 0):.3f}")
        elif name in outlier_names:
            status = "❌ OUTLIER"
            compound = next(c for c in results['outliers'] if c['Name'] == name)
            print(f"   {name:20s}: {status}")
            print(f"      Reason: {compound.get('outlier_reason', 'Unknown')}")
        else:
            print(f"   {name:20s}: ⚠️ NOT CLASSIFIED")

    # Overall statistics
    print("\n📈 Overall Statistics:")
    stats = results['statistics']
    print(f"   Total compounds: {stats['total_compounds']}")
    print(f"   Valid compounds: {stats['valid_compounds']}")
    print(f"   Outliers: {stats['outliers']}")
    print(f"   Success rate: {stats['success_rate']:.1f}%")

    # Test validation
    print("\n" + "="*80)
    print("TEST RESULT")
    print("="*80)

    gt3_36_valid = gt3_36 in valid_names
    gt3_38_valid = gt3_38 in valid_names

    if gt3_36_valid and gt3_38_valid:
        print("\n✅ TEST PASSED!")
        print("   Both GT3(36:1;O2) and GT3(38:1;O2) are correctly identified as VALID.")
        print("\n📝 Explanation:")
        print("   The multiple regression model correctly handles:")
        print("   1. Different carbon chains (a_component feature)")
        print("   2. Relationship: RT = f(Log P, Carbon, Sugar, etc.)")
        print("   3. Expected chemical behavior (longer chain → higher RT, Log P)")
        print("   4. Realistic thresholds (R² ≥ 0.80, outlier ≥ 3σ)")
        return True
    else:
        print("\n❌ TEST FAILED!")
        if not gt3_36_valid:
            print(f"   GT3(36:1;O2) incorrectly flagged as outlier")
        if not gt3_38_valid:
            print(f"   GT3(38:1;O2) incorrectly flagged as outlier")
        print("\n📝 This indicates the regression model or thresholds need adjustment.")
        return False


if __name__ == "__main__":
    success = test_gt3_validation()
    exit(0 if success else 1)
