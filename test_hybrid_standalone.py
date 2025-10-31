#!/usr/bin/env python3
"""
Standalone test for hybrid multi-level regression strategy
No Django required - tests core algorithm logic only
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.model_selection import LeaveOneOut


def cross_validate_regression(X, y):
    """Leave-One-Out Cross-Validation"""
    if len(X) < 3:
        return None

    loo = LeaveOneOut()
    predictions = []
    actuals = []

    for train_idx, test_idx in loo.split(X):
        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        model = Ridge(alpha=1.0)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        predictions.append(pred[0])
        actuals.append(y_test[0])

    validation_r2 = r2_score(actuals, predictions)
    return float(validation_r2)


def test_hybrid_multilevel():
    """Test hybrid multi-level strategy with real data"""

    print("=" * 80)
    print("HYBRID MULTI-LEVEL STRATEGY TEST (Standalone)")
    print("=" * 80)
    print()

    # Load test data
    data_path = '/Users/seoljonghyeon/Documents/GitHub/Automated-LC-MS-MS-analaysis_ver2/Regression/data/samples/testwork_user.csv'

    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"❌ Data file not found: {data_path}")
        return

    print(f"📊 Dataset: testwork_user.csv")
    print(f"   Total compounds: {len(df)}")
    print(f"   Anchor compounds (T): {len(df[df['Anchor'] == 'T'])}")
    print(f"   Test compounds (F): {len(df[df['Anchor'] == 'F'])}")
    print()

    # Extract prefix
    df['prefix'] = df['Name'].str.extract(r'^([^(]+)')[0]

    # Count by prefix
    print("📋 Compounds by Prefix:")
    prefix_summary = {}
    for prefix in sorted(df['prefix'].unique()):
        prefix_df = df[df['prefix'] == prefix]
        anchors = len(prefix_df[prefix_df['Anchor'] == 'T'])
        total = len(prefix_df)
        prefix_summary[prefix] = {'total': total, 'anchors': anchors}
        print(f"   {prefix}: {total} total ({anchors} anchors)")
    print()

    # Define prefix families (same as in code)
    PREFIX_FAMILIES = {
        "GD_family": ["GD1", "GD1a", "GD1b", "GD1+HexNAc", "GD1+dHex", "GD3"],
        "GM_family": ["GM1", "GM1+HexNAc", "GM3", "GM3+OAc"],
        "GT_family": ["GT1", "GT1a", "GT1b", "GT3"],
        "GQ_family": ["GQ1", "GQ1a", "GQ1b", "GQ1c", "GQ1+HexNAc"],
        "GP_family": ["GP1", "GP1a"]
    }

    # Create reverse mapping
    prefix_to_family = {}
    for family_name, prefixes in PREFIX_FAMILIES.items():
        for prefix in prefixes:
            prefix_to_family[prefix] = family_name

    # Test decision logic for each prefix
    print("🔬 Testing Decision Tree Logic:")
    print()

    decisions = {}

    for prefix in sorted(prefix_summary.keys()):
        n_anchors = prefix_summary[prefix]['anchors']
        family = prefix_to_family.get(prefix)

        print(f"   {prefix} (n={n_anchors}):")

        # Decision tree simulation
        if n_anchors >= 10:
            # Level 1: Large sample prefix-specific
            prefix_data = df[df['prefix'] == prefix]
            anchors = prefix_data[prefix_data['Anchor'] == 'T']

            X = anchors[['Log P']].values
            y = anchors['RT'].values

            model = Ridge(alpha=1.0)
            model.fit(X, y)

            training_r2 = r2_score(y, model.predict(X))
            validation_r2 = cross_validate_regression(X, y)
            r2_check = validation_r2 if validation_r2 is not None else training_r2

            if r2_check >= 0.75:
                decision = "Level 1: Prefix-specific (threshold=0.75)"
                decisions[prefix] = {'level': 1, 'model': 'prefix', 'r2': r2_check}
                print(f"      ✅ {decision} - R²={r2_check:.3f}")
            else:
                decision = "Level 1 FAILED → trying Level 2"
                print(f"      ⚠️  {decision} - R²={r2_check:.3f} < 0.75")

                # Fall through to Level 2
                if r2_check >= 0.70:
                    decision = "Level 2: Prefix-specific (threshold=0.70)"
                    decisions[prefix] = {'level': 2, 'model': 'prefix', 'r2': r2_check}
                    print(f"      ✅ {decision} - R²={r2_check:.3f}")
                else:
                    decision = "Level 2 FAILED → trying Level 3 (family)"
                    decisions[prefix] = {'level': 3, 'model': 'family', 'family': family}
                    print(f"      ⚠️  {decision}")

        elif n_anchors >= 4:
            # Level 2: Medium sample prefix-specific
            prefix_data = df[df['prefix'] == prefix]
            anchors = prefix_data[prefix_data['Anchor'] == 'T']

            X = anchors[['Log P']].values
            y = anchors['RT'].values

            model = Ridge(alpha=1.0)
            model.fit(X, y)

            training_r2 = r2_score(y, model.predict(X))
            validation_r2 = cross_validate_regression(X, y)
            r2_check = validation_r2 if validation_r2 is not None else training_r2

            if r2_check >= 0.70:
                decision = "Level 2: Prefix-specific (threshold=0.70)"
                decisions[prefix] = {'level': 2, 'model': 'prefix', 'r2': r2_check}
                print(f"      ✅ {decision} - R²={r2_check:.3f}")
            else:
                decision = "Level 2 FAILED → trying Level 3 (family)"
                decisions[prefix] = {'level': 3, 'model': 'family', 'family': family}
                print(f"      ⚠️  {decision}")

        elif n_anchors == 3:
            # Level 3: Family pooling
            decision = "Level 3: Family pooling"
            decisions[prefix] = {'level': 3, 'model': 'family', 'family': family}
            print(f"      🔄 {decision} (family: {family})")

        else:
            # Level 4: Overall fallback
            decision = "Level 4: Overall fallback"
            decisions[prefix] = {'level': 4, 'model': 'overall'}
            print(f"      🔄 {decision}")

    # Test family pooling for GD family
    print("\n🔬 Testing GD Family Pooling:")

    gd_prefixes = ["GD1", "GD1+HexNAc", "GD1+dHex", "GD3"]
    gd_family_df = df[df['prefix'].isin(gd_prefixes)]
    gd_anchors = gd_family_df[gd_family_df['Anchor'] == 'T']

    if len(gd_anchors) >= 10:
        X_gd = gd_anchors[['Log P']].values
        y_gd = gd_anchors['RT'].values

        model_gd = Ridge(alpha=1.0)
        model_gd.fit(X_gd, y_gd)

        training_r2_gd = r2_score(y_gd, model_gd.predict(X_gd))
        validation_r2_gd = cross_validate_regression(X_gd, y_gd)
        r2_gd = validation_r2_gd if validation_r2_gd is not None else training_r2_gd

        print(f"   GD_family:")
        print(f"      Pooled anchors: {len(gd_anchors)}")
        print(f"      Contributing prefixes: {', '.join(gd_prefixes)}")
        print(f"      Training R²: {training_r2_gd:.3f}")
        print(f"      Validation R²: {validation_r2_gd:.3f}" if validation_r2_gd else "      Validation R²: N/A")
        print(f"      R² for threshold: {r2_gd:.3f}")

        if r2_gd >= 0.70:
            print(f"      ✅ GD_family model ACCEPTED (R²={r2_gd:.3f} >= 0.70)")
        else:
            print(f"      ❌ GD_family model REJECTED (R²={r2_gd:.3f} < 0.70)")
    else:
        print(f"   ❌ Insufficient anchors for GD family (n={len(gd_anchors)})")

    # Summary
    print("\n" + "=" * 80)
    print("DECISION SUMMARY")
    print("=" * 80)
    print()

    level_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for prefix, decision in decisions.items():
        level_counts[decision['level']] += 1

    print(f"📊 Level Usage:")
    print(f"   Level 1 (n≥10, threshold=0.75): {level_counts[1]} prefixes")
    print(f"   Level 2 (n≥4, threshold=0.70): {level_counts[2]} prefixes")
    print(f"   Level 3 (family pooling): {level_counts[3]} prefixes")
    print(f"   Level 4 (overall fallback): {level_counts[4]} prefixes")

    # Validate n=3 groups
    print("\n✅ n=3 Group Validation:")
    n3_groups = [p for p, s in prefix_summary.items() if s['anchors'] == 3]

    all_n3_correct = True
    for group in n3_groups:
        if group in decisions:
            level = decisions[group]['level']
            if level >= 3:  # Family or overall
                print(f"   ✅ {group}: Level {level} ({decisions[group]['model']})")
            else:
                print(f"   ❌ {group}: Incorrectly using Level {level}")
                all_n3_correct = False

    # Final assessment
    print("\n" + "=" * 80)
    print("FINAL ASSESSMENT")
    print("=" * 80)
    print()

    success = True

    # Test 1: Multi-level logic
    if level_counts[1] > 0 or level_counts[2] > 0:
        print("✅ Test 1: Prefix-specific levels working")
    else:
        print("⚠️  Test 1: No prefix-specific levels used")

    # Test 2: Family pooling
    if level_counts[3] > 0:
        print("✅ Test 2: Family pooling being used")
    else:
        print("❌ Test 2: Family pooling not being used")
        success = False

    # Test 3: n=3 handling
    if all_n3_correct and len(n3_groups) > 0:
        print("✅ Test 3: All n=3 groups using family/overall models")
    elif len(n3_groups) == 0:
        print("⚠️  Test 3: No n=3 groups in dataset")
    else:
        print("❌ Test 3: Some n=3 groups incorrectly handled")
        success = False

    print()

    if success:
        print("🎉 HYBRID MULTI-LEVEL LOGIC VALIDATED!")
        print("   The decision tree is working as expected.")
    else:
        print("⚠️  SOME ISSUES DETECTED - Review results above")

    print()
    print("=" * 80)


if __name__ == '__main__':
    test_hybrid_multilevel()
