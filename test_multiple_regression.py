"""
Test Multiple Regression Implementation
Tests the refactored multiple regression with functional features
"""

import pandas as pd
import sys
sys.path.insert(0, '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression')

from backend.services.ganglioside_processor import GangliosideProcessor
from backend.core.analysis_service import AnalysisService

def test_multiple_regression():
    """Test the multiple regression implementation"""

    print("="*80)
    print("MULTIPLE REGRESSION TEST")
    print("="*80)

    # Load sample data
    print("\n📂 Loading sample data...")
    df = pd.read_csv('data/sample/testwork.csv')
    print(f"✅ Loaded {len(df)} compounds")
    print(f"   Columns: {list(df.columns)}")

    # Initialize processor
    print("\n🔧 Initializing GangliosideProcessor...")
    processor = GangliosideProcessor()

    # Process data
    print("\n🧬 Processing data with multiple regression...")
    results = processor.process_data(df, data_type="Porcine")

    # Display regression results
    print("\n" + "="*80)
    print("REGRESSION RESULTS")
    print("="*80)

    if "regression_analysis" in results:
        for group_name, reg_result in results["regression_analysis"].items():
            print(f"\n📊 Group: {group_name}")
            print(f"   R² = {reg_result.get('r2', 0):.4f}")
            print(f"   Features: {reg_result.get('n_features', 1)}")

            if "feature_names" in reg_result:
                print(f"   Feature Names: {', '.join(reg_result['feature_names'])}")

            if "coefficients" in reg_result:
                print(f"   Coefficients:")
                for feat, coef in reg_result['coefficients'].items():
                    print(f"      {feat:20s}: {coef:8.4f}")

            print(f"   Equation: {reg_result.get('equation', 'N/A')}")

    # Test with AnalysisService
    print("\n" + "="*80)
    print("TESTING ANALYSIS SERVICE")
    print("="*80)

    print("\n🔧 Initializing AnalysisService...")
    service = AnalysisService()

    print("\n🧬 Running comprehensive analysis...")
    comprehensive_results = service.analyze_data(df, data_type="Porcine", include_advanced_regression=True)

    if "enhanced_regression" in comprehensive_results and comprehensive_results["enhanced_regression"]:
        enhanced = comprehensive_results["enhanced_regression"]
        if "regression_analysis" in enhanced:
            reg_analysis = enhanced["regression_analysis"]

            print(f"\n📊 Enhanced Regression Analysis:")
            if "basic_regression" in reg_analysis:
                basic = reg_analysis["basic_regression"]
                print(f"   R² = {basic.get('r2', 0):.4f}")
                print(f"   Adjusted R² = {basic.get('adjusted_r2', 0):.4f}")
                print(f"   Features: {basic.get('n_features', 1)}")
                print(f"   Equation: {basic.get('equation', 'N/A')}")

                if "coefficient_details" in basic:
                    print(f"\n   📈 Coefficient Details:")
                    for feat, details in basic['coefficient_details'].items():
                        sig = "***" if details.get('significant', False) else ""
                        print(f"      {feat:20s}: {details['coefficient']:8.4f} (p={details['p_value']:.4f}) {sig}")

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    stats = results.get("statistics", {})
    print(f"\n✅ Total Compounds: {stats.get('total_compounds', 0)}")
    print(f"✅ Valid Compounds: {stats.get('valid_compounds', 0)}")
    print(f"✅ Success Rate: {stats.get('success_rate', 0):.1f}%")

    if "regression_summary" in stats:
        reg_summary = stats["regression_summary"]
        print(f"\n📊 Regression Summary:")
        print(f"   Total Groups: {reg_summary.get('total_groups', 0)}")
        print(f"   Average R²: {reg_summary.get('avg_r2', 0):.4f}")
        print(f"   High Quality Groups (R²≥0.99): {reg_summary.get('high_quality_groups', 0)}")

    print("\n" + "="*80)
    print("✅ MULTIPLE REGRESSION TEST COMPLETED")
    print("="*80)

if __name__ == "__main__":
    test_multiple_regression()
