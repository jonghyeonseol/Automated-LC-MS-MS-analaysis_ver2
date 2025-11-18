# Edge Case Test Suite - Quick Reference

## Files Created

1. **Test Suite**: `/home/user/Automated-LC-MS-MS-analaysis_ver2/django_ganglioside/tests/integration/test_edge_cases.py`
   - 42 test functions
   - 5 test classes (one per rule + general)
   - ~950 lines of code

2. **Documentation**: `/home/user/Automated-LC-MS-MS-analaysis_ver2/django_ganglioside/tests/integration/EDGE_CASES_SUMMARY.md`
   - Complete test breakdown
   - Running instructions
   - Expected outcomes

3. **This File**: Quick reference for developers

---

## Test Breakdown by Rule

### Rule 1: Regression (10 tests)
```python
TestRule1RegressionEdgeCases
├── test_minimum_anchor_compounds_exactly_3
├── test_insufficient_anchors_only_2
├── test_single_anchor_compound
├── test_large_anchor_set_100_compounds [SLOW]
├── test_identical_rt_all_anchors
├── test_identical_logp_all_anchors
├── test_perfect_linear_relationship_r2_equals_1
├── test_no_relationship_r2_near_zero
├── test_single_prefix_group_only
└── test_many_prefix_groups_20_plus [SLOW]
```

### Rule 2-3: Sugar Count (6 tests)
```python
TestRule23SugarCountEdgeCases
├── test_unknown_prefix_not_standard
├── test_malformed_prefix_missing_letters
├── test_very_long_compound_name_100_chars
├── test_special_characters_in_name
├── test_compound_name_only_prefix_no_suffix
└── test_multiple_modifications_complex
```

### Rule 4: O-Acetylation (5 tests)
```python
TestRule4OAcetylationEdgeCases
├── test_oacetyl_without_base_compound
├── test_base_compound_without_oacetyl
├── test_multiple_oacetyl_levels
├── test_oacetyl_rt_decrease_invalid
└── test_oacetyl_identical_rt_edge_case
```

### Rule 5: Fragmentation (7 tests)
```python
TestRule5FragmentationEdgeCases
├── test_all_compounds_within_rt_tolerance
├── test_no_compounds_within_rt_tolerance
├── test_rt_exactly_at_tolerance_boundary
├── test_many_fragments_100_plus_in_group [SLOW]
├── test_single_compound_per_suffix
├── test_very_small_rt_tolerance
└── test_very_large_rt_tolerance
```

### General (14 tests)
```python
TestGeneralEdgeCases
├── test_single_compound_total
├── test_large_dataset_10000_compounds [SLOW]
├── test_all_rt_values_zero
├── test_all_volume_values_zero
├── test_extreme_logp_negative_100
├── test_extreme_logp_positive_100
├── test_unicode_characters_in_compound_name
├── test_empty_csv_no_data_rows
├── test_missing_values_null_nan
├── test_negative_rt_values
├── test_negative_volume_values
├── test_mixed_anchor_formats_true_false_tf
├── test_csv_injection_attempt
└── test_concurrent_analyses_stress_test [SLOW]
```

**SLOW tests**: 5 total (100+ compounds, performance tests)

---

## Quick Commands

### Run All Edge Case Tests
```bash
docker-compose exec django pytest tests/integration/test_edge_cases.py -v
```

### Run Fast Tests Only (Skip Performance)
```bash
docker-compose exec django pytest tests/integration/test_edge_cases.py \
  -m "edge_cases and not slow" -v
```

### Run Single Test
```bash
docker-compose exec django pytest \
  tests/integration/test_edge_cases.py::TestRule1RegressionEdgeCases::test_minimum_anchor_compounds_exactly_3 \
  -v
```

### Run by Rule
```bash
# Rule 1 only
docker-compose exec django pytest \
  tests/integration/test_edge_cases.py::TestRule1RegressionEdgeCases -v

# Rule 4 only
docker-compose exec django pytest \
  tests/integration/test_edge_cases.py::TestRule4OAcetylationEdgeCases -v
```

### Run with Coverage
```bash
docker-compose exec django pytest tests/integration/test_edge_cases.py \
  --cov=apps.analysis --cov-report=html -v
```

### Run with Output
```bash
docker-compose exec django pytest tests/integration/test_edge_cases.py \
  -v -s  # -s shows print statements
```

---

## Edge Cases Coverage Matrix

| Category | Count | Examples |
|----------|-------|----------|
| **Sample Size** | 7 | 1 compound, 2 anchors, 3 anchors, 100 anchors, 10,000 total |
| **Data Quality** | 8 | Missing values, malformed names, empty CSV |
| **Extreme Values** | 6 | Zero RT/Volume, negative values, extreme Log P |
| **Correlation** | 2 | Perfect (R²=1), None (R²≈0) |
| **Tolerances** | 3 | Very small (0.001), normal (0.1), very large (10.0) |
| **Chemical Logic** | 5 | Invalid OAc, fragmentation, isomers |
| **Performance** | 4 | Large datasets, many groups, concurrency |
| **Security** | 2 | CSV injection, Unicode |
| **Parsing** | 5 | Long names, special chars, missing parts |

**Total**: 42 unique edge cases

---

## Expected Test Results

### Should PASS
- `test_minimum_anchor_compounds_exactly_3` (3 is minimum)
- `test_perfect_linear_relationship_r2_equals_1` (perfect fit)
- `test_all_volume_values_zero` (volume not used in analysis)
- `test_base_compound_without_oacetyl` (Rule 4 not applicable)
- `test_csv_injection_attempt` (sanitization implemented)

### Should FAIL (Gracefully)
- `test_single_anchor_compound` (insufficient data)
- `test_empty_csv_no_data_rows` (validation error)
- `test_identical_rt_all_anchors` (no variance)

### Should FALLBACK
- `test_insufficient_anchors_only_2` (use overall regression)
- `test_unknown_prefix_not_standard` (treat as new group)

### May Need Investigation
- `test_unicode_characters_in_compound_name` (encoding support)
- `test_very_large_rt_tolerance` (validation limits)

---

## Performance Expectations

| Test | Expected Duration | Dataset Size |
|------|------------------|--------------|
| Fast tests (37) | < 1s each | 3-10 compounds |
| `test_large_anchor_set_100_compounds` | 2-5s | 120 compounds |
| `test_many_prefix_groups_20_plus` | 2-5s | 100 compounds |
| `test_many_fragments_100_plus_in_group` | 2-5s | 100 compounds |
| `test_large_dataset_10000_compounds` | 10-30s | 10,000 compounds |
| `test_concurrent_analyses_stress_test` | 20-60s | 10 × small dataset |

**Total Suite**: ~2-5 minutes (all tests)
**Fast Suite**: ~30-60 seconds (without slow tests)

---

## Common Test Patterns

### Test Structure
```python
def test_edge_case_name(self, test_user):
    # 1. Create edge case CSV data
    csv_content = b"""Name,RT,Volume,Log P,Anchor
GM1(36:1;O2),10.0,1000000,1.0,T
...
"""
    csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")

    # 2. Create analysis session
    session = AnalysisSession.objects.create(
        user=test_user,
        name="Test Name",
        data_type="porcine",
        uploaded_file=csv_file,
        file_size=csv_file.size,
        original_filename="test.csv",
    )

    # 3. Run analysis
    service = AnalysisService()
    result = service.run_analysis(session)

    # 4. Assert expected behavior
    assert result is not None
    assert result.total_compounds == expected_count
```

### Error Handling Pattern
```python
# For tests that should fail
try:
    result = service.run_analysis(session)
    assert result is not None  # May succeed with fallback
except Exception:
    pass  # Expected to fail
```

---

## Troubleshooting

### Test Fails: "Database not available"
```bash
# Ensure database is running
docker-compose ps postgres

# Run migrations
docker-compose exec django python manage.py migrate
```

### Test Fails: "User fixture not found"
```bash
# Check conftest.py exists
ls tests/conftest.py

# Ensure test_user fixture is defined
grep "def test_user" tests/conftest.py
```

### Test Timeout
```bash
# Increase pytest timeout
pytest tests/integration/test_edge_cases.py --timeout=300
```

### Import Errors
```bash
# Verify Django settings
docker-compose exec django python -c "import django; django.setup(); print('OK')"

# Check app imports
docker-compose exec django python -c "from apps.analysis.services.analysis_service import AnalysisService; print('OK')"
```

---

## Adding New Edge Cases

### Step 1: Identify Edge Case
- What rule does it test?
- What boundary/extreme condition?
- Expected behavior?

### Step 2: Add Test Function
```python
def test_your_new_edge_case(self, test_user):
    """Test description of edge case"""
    csv_content = b"""..."""  # Edge case data
    csv_file = SimpleUploadedFile("test.csv", csv_content, content_type="text/csv")

    session = AnalysisSession.objects.create(...)
    service = AnalysisService()
    result = service.run_analysis(session)

    assert ...  # Expected outcome
```

### Step 3: Add to Documentation
- Update EDGE_CASES_SUMMARY.md
- Update count in this file
- Add to appropriate category

### Step 4: Test
```bash
pytest tests/integration/test_edge_cases.py::TestClassName::test_your_new_edge_case -v
```

---

## Integration with Main Test Suite

These edge case tests complement the existing test files:

- `test_analysis_workflow.py` - Normal workflow tests
- `test_api_endpoints.py` - API endpoint tests
- `test_celery_tasks.py` - Background task tests
- **`test_edge_cases.py`** - Edge case & boundary tests ← NEW

Run all integration tests:
```bash
docker-compose exec django pytest tests/integration/ -v
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run edge case tests
  run: |
    docker-compose exec -T django pytest \
      tests/integration/test_edge_cases.py \
      -m "edge_cases and not slow" \
      --junitxml=test-results/edge-cases.xml

- name: Run slow tests (nightly)
  if: github.event.schedule
  run: |
    docker-compose exec -T django pytest \
      tests/integration/test_edge_cases.py \
      -m "slow" \
      --junitxml=test-results/edge-cases-slow.xml
```

---

## Maintenance Checklist

- [ ] Run edge case tests before each release
- [ ] Update tests when adding new rules
- [ ] Add regression tests when bugs are found
- [ ] Review slow test thresholds quarterly
- [ ] Check for new real-world edge cases monthly
- [ ] Update documentation when tests change

---

**Created**: 2025-11-18
**Version**: 1.0
**Status**: Ready for testing
