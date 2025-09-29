#!/usr/bin/env python3
"""
Test the categorizer with real user data
"""

import pandas as pd
import sys
import os

# Add the backend path
sys.path.append('backend')
from utils.ganglioside_categorizer import GangliosideCategorizer

def test_with_real_data():
    print("🧪 TESTING CATEGORIZER WITH REAL USER DATA")
    print("=" * 60)

    # Load user data
    try:
        df = pd.read_csv('testwork_user.csv')
        print(f"📁 Loaded {len(df)} compounds from testwork_user.csv")
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return

    # Initialize categorizer
    categorizer = GangliosideCategorizer()

    # Generate full summary
    summary = categorizer.generate_categorization_summary(df)
    print(summary)

    # Test categorization results
    results = categorizer.categorize_compounds(df)

    print("\n" + "=" * 60)
    print("🔍 DETAILED CATEGORY ANALYSIS")
    print("=" * 60)

    for category, info in results['categories'].items():
        category_info = info['info']
        print(f"\n🏷️ {category} - {category_info['name']}")
        print(f"   📊 Count: {info['count']} compounds")
        print(f"   🎨 Color: {category_info['color']}")
        print(f"   📝 Description: {category_info['description']}")

        # Show first few compounds as examples
        examples = info['compounds'][:3]
        if examples:
            print(f"   📋 Examples: {', '.join(examples)}")
            if len(info['compounds']) > 3:
                print(f"   ... and {len(info['compounds']) - 3} more")

    # Test grouped data creation
    print("\n" + "=" * 60)
    print("📊 CREATING GROUPED DATASETS")
    print("=" * 60)

    grouped_data = categorizer.create_category_grouped_data(df)

    for category, group_df in grouped_data.items():
        print(f"\n📊 {category} Category Dataset:")
        print(f"   - Compounds: {len(group_df)}")
        print(f"   - Columns: {list(group_df.columns)}")

        # Show base prefix distribution within this category
        base_prefixes = group_df['Base_Prefix'].value_counts()
        print(f"   - Base Prefixes: {dict(base_prefixes)}")

        # Show modification distribution
        modifications = group_df['Modifications'].value_counts()
        print(f"   - Modifications: {dict(modifications)}")

    # Test color mapping
    print("\n" + "=" * 60)
    print("🎨 COLOR SCHEME")
    print("=" * 60)

    colors = categorizer.get_category_colors()
    for category, color in colors.items():
        if category in results['categories']:
            count = results['categories'][category]['count']
            print(f"🎨 {category}: {color} ({count} compounds)")

    print(f"\n✅ CATEGORIZATION TEST COMPLETED")
    print(f"📊 Ready to integrate with visualization system!")

if __name__ == "__main__":
    test_with_real_data()