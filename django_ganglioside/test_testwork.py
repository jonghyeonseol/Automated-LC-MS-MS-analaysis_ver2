#!/usr/bin/env python
"""
Test script for testwork.csv analysis
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

print("=" * 80)
print("TESTWORK.CSV ANALYSIS TEST")
print("=" * 80)

# Get admin user (already created)
try:
    user = User.objects.get(username='admin')
    print(f"\n✅ Using admin user: {user.username}")
except User.DoesNotExist:
    print("\n❌ Admin user not found. Creating...")
    user = User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print(f"✅ Created admin user: {user.username}")

# Create analysis session
print("\n[1/5] Creating analysis session with testwork.csv...")
csv_path = Path('../data/sample/testwork.csv')

if not csv_path.exists():
    print(f"❌ Test file not found: {csv_path}")
    sys.exit(1)

with open(csv_path, 'rb') as f:
    session = AnalysisSession.objects.create(
        user=user,
        name="Testwork.csv - Production Test",
        data_type='porcine',
        uploaded_file=File(f, name='testwork.csv'),
        original_filename='testwork.csv',
        file_size=csv_path.stat().st_size,
        r2_threshold=0.75,
        outlier_threshold=2.5,
        rt_tolerance=0.1
    )

print(f"✅ Session created: ID {session.id}")
print(f"   - File: {session.original_filename}")
print(f"   - Size: {session.file_size / 1024:.2f} KB")

# Run analysis
print("\n[2/5] Running analysis...")
print("   This will execute the complete 5-rule pipeline...")

try:
    from django.utils import timezone

    session.status = 'processing'
    session.started_at = timezone.now()
    session.save()

    service = AnalysisService()
    result = service.run_analysis(session)

    session.status = 'completed'
    session.completed_at = timezone.now()
    session.save()

    print("✅ Analysis completed successfully")

    duration = (session.completed_at - session.started_at).total_seconds()
    print(f"   - Duration: {duration:.2f} seconds")

except Exception as e:
    print(f"❌ Analysis failed: {e}")
    session.status = 'failed'
    session.error_message = str(e)
    session.save()
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify results
print("\n[3/5] Verifying results...")
session.refresh_from_db()

if not hasattr(session, 'result'):
    print("❌ No AnalysisResult found")
    sys.exit(1)

result = session.result
print(f"✅ Analysis results:")
print(f"   - Total compounds: {result.total_compounds}")
print(f"   - Anchor compounds: {result.anchor_compounds}")
print(f"   - Valid compounds: {result.valid_compounds}")
print(f"   - Outliers: {result.outlier_count}")
print(f"   - Success rate: {result.success_rate:.2f}%")

# Verify compounds
print("\n[4/5] Analyzing compound distribution...")
compounds = Compound.objects.filter(session=session)
total_compounds = compounds.count()

if total_compounds == 0:
    print("❌ No compounds created")
    sys.exit(1)

print(f"✅ {total_compounds} compounds processed")

# Category breakdown
categories = compounds.values_list('category', flat=True).distinct()
print("\n   Category Distribution:")
for cat_name in sorted(set(categories)):
    if cat_name:
        cat_total = compounds.filter(category=cat_name).count()
        cat_valid = compounds.filter(category=cat_name, status='valid').count()
        cat_outlier = compounds.filter(category=cat_name, status='outlier').count()
        print(f"   - {cat_name:3s}: {cat_total:3d} total | {cat_valid:3d} valid | {cat_outlier:3d} outliers")

# Status breakdown
print("\n   Status Distribution:")
statuses = compounds.values_list('status', flat=True).distinct()
for status_name in sorted(set(statuses)):
    if status_name:
        count = compounds.filter(status=status_name).count()
        pct = (count / total_compounds) * 100
        print(f"   - {status_name:15s}: {count:3d} ({pct:5.1f}%)")

# Verify regression models
print("\n[5/5] Analyzing regression models...")
models = RegressionModel.objects.filter(session=session)
model_count = models.count()

if model_count == 0:
    print("⚠️  No regression models created")
else:
    print(f"✅ {model_count} regression models created\n")

    # Sort by R² descending
    models_sorted = models.order_by('-r2')

    print("   Model Quality Metrics:")
    print(f"   {'Prefix':<15} {'R²':>8} {'RMSE':>8} {'Samples':>8} {'Anchors':>8} {'Type':<10}")
    print("   " + "-" * 70)

    for model in models_sorted:
        rmse_str = f"{model.rmse:.4f}" if model.rmse else "N/A"
        print(f"   {model.prefix_group:<15} {model.r2:>8.4f} {rmse_str:>8} "
              f"{model.n_samples:>8} {model.n_anchors:>8} {model.model_type:<10}")

    # Calculate statistics
    avg_r2 = sum(m.r2 for m in models) / len(models)
    min_r2 = min(m.r2 for m in models)
    max_r2 = max(m.r2 for m in models)

    print("\n   Model Statistics:")
    print(f"   - Average R²: {avg_r2:.4f}")
    print(f"   - Min R²: {min_r2:.4f}")
    print(f"   - Max R²: {max_r2:.4f}")

    # Quality assessment
    excellent = sum(1 for m in models if m.r2 >= 0.95)
    good = sum(1 for m in models if 0.90 <= m.r2 < 0.95)
    acceptable = sum(1 for m in models if 0.75 <= m.r2 < 0.90)
    poor = sum(1 for m in models if m.r2 < 0.75)

    print(f"\n   Quality Distribution:")
    print(f"   - Excellent (R² ≥ 0.95): {excellent}")
    print(f"   - Good (0.90 ≤ R² < 0.95): {good}")
    print(f"   - Acceptable (0.75 ≤ R² < 0.90): {acceptable}")
    print(f"   - Poor (R² < 0.75): {poor}")

# Final summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"✅ Session ID: {session.id}")
print(f"✅ File: {session.original_filename}")
print(f"✅ Status: {session.get_status_display()}")
print(f"✅ Duration: {duration:.2f} seconds")
print(f"✅ Total compounds: {result.total_compounds}")
print(f"✅ Valid: {result.valid_compounds} ({result.success_rate:.2f}%)")
print(f"✅ Outliers: {result.outlier_count}")
print(f"✅ Regression models: {model_count}")
print(f"✅ Average R²: {avg_r2:.4f}")
print("=" * 80)

print("\n🎉 TEST COMPLETED SUCCESSFULLY!")
print("\n📊 View results in web UI:")
print(f"   http://localhost:8000/sessions/{session.id}/results/")
print("\n📋 View session detail:")
print(f"   http://localhost:8000/sessions/{session.id}/")
print("\n🔍 View in admin panel:")
print(f"   http://localhost:8000/admin/analysis/analysissession/{session.id}/change/")
print("=" * 80)
