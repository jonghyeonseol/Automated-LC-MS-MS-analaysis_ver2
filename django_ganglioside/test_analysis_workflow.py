#!/usr/bin/env python
"""
Test script to verify complete analysis workflow works correctly
"""
import os
import django
import sys
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from django.core.files import File
from apps.analysis.models import AnalysisSession, AnalysisResult, Compound, RegressionModel
from apps.analysis.services.analysis_service import AnalysisService

User = get_user_model()

def test_complete_workflow():
    """Test the complete analysis workflow"""
    print("=" * 80)
    print("DJANGO GANGLIOSIDE PLATFORM - WORKFLOW TEST")
    print("=" * 80)

    # 1. Get or create test user
    print("\n[1/6] Setting up test user...")
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@example.com', 'is_active': True}
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print("✅ Created test user: test_user")
    else:
        print("✅ Using existing test user: test_user")

    # 2. Create analysis session
    print("\n[2/6] Creating analysis session...")
    csv_path = Path('../data/samples/testwork_user.csv')

    if not csv_path.exists():
        print(f"❌ Test file not found: {csv_path}")
        sys.exit(1)

    with open(csv_path, 'rb') as f:
        session = AnalysisSession.objects.create(
            user=user,
            name="Test Analysis - Workflow Verification",
            data_type='porcine',
            uploaded_file=File(f, name='testwork_user.csv'),
            original_filename='testwork_user.csv',
            file_size=csv_path.stat().st_size,
            r2_threshold=0.75,
            outlier_threshold=2.5,
            rt_tolerance=0.1
        )

    print(f"✅ Created session ID: {session.id}")
    print(f"   - Name: {session.name}")
    print(f"   - File: {session.original_filename}")
    print(f"   - Size: {session.file_size / 1024:.2f} KB")

    # 3. Run analysis
    print("\n[3/6] Running analysis pipeline...")
    print("   This may take 5-10 seconds...")

    try:
        service = AnalysisService()
        result = service.run_analysis(session)

        # Update session status
        session.status = 'completed'
        session.save()

        print("✅ Analysis completed successfully")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # 4. Verify results
    print("\n[4/6] Verifying results...")

    # Refresh from database
    session.refresh_from_db()

    if not hasattr(session, 'result'):
        print("❌ No AnalysisResult found")
        sys.exit(1)

    result = session.result
    print(f"✅ AnalysisResult created: ID {result.id}")
    print(f"   - Total compounds: {result.total_compounds}")
    print(f"   - Valid compounds: {result.valid_compounds}")
    print(f"   - Outliers: {result.outlier_count}")
    print(f"   - Success rate: {result.success_rate:.2f}%")

    # 5. Verify compounds
    print("\n[5/6] Verifying compounds...")
    compounds = Compound.objects.filter(session=session)
    compound_count = compounds.count()

    if compound_count == 0:
        print("❌ No compounds created")
        sys.exit(1)

    print(f"✅ {compound_count} compounds created")

    # Show breakdown by category
    categories = compounds.values_list('category', flat=True).distinct()
    for cat_name in sorted(set(categories)):
        if cat_name:  # Skip None values
            cat_count = compounds.filter(category=cat_name).count()
            valid_count = compounds.filter(category=cat_name, status='valid').count()
            print(f"   - {cat_name}: {cat_count} total, {valid_count} valid")

    # 6. Verify regression models
    print("\n[6/6] Verifying regression models...")
    models = RegressionModel.objects.filter(session=session)
    model_count = models.count()

    if model_count == 0:
        print("⚠️  No regression models created (may be expected for some datasets)")
    else:
        print(f"✅ {model_count} regression models created")
        for model in models:
            print(f"   - {model.prefix_group}: R² = {model.r2:.4f}, "
                  f"{model.n_samples} samples ({model.n_anchors} anchors), type={model.model_type}")

    # Final summary
    print("\n" + "=" * 80)
    print("WORKFLOW TEST SUMMARY")
    print("=" * 80)
    print(f"✅ Session created: ID {session.id}")
    print(f"✅ Analysis status: {session.get_status_display()}")
    print(f"✅ Total compounds: {result.total_compounds}")
    print(f"✅ Valid compounds: {result.valid_compounds}")
    print(f"✅ Outliers detected: {result.outlier_count}")
    print(f"✅ Success rate: {result.success_rate:.2f}%")
    print(f"✅ Regression models: {model_count}")
    print("=" * 80)
    print("\n🎉 ALL TESTS PASSED - System is working correctly!")
    print("\nNext steps:")
    print("1. Start server: python manage.py runserver")
    print(f"2. View results: http://localhost:8000/sessions/{session.id}/results/")
    print("3. API docs: http://localhost:8000/api/docs/")
    print("=" * 80)

    return session

if __name__ == '__main__':
    try:
        session = test_complete_workflow()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
