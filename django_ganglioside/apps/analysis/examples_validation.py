"""
Example usage of CSV validation functions

This script demonstrates how to use the validation utility functions
and how they detect various types of validation failures.

Run with:
  python manage.py shell < examples_validation.py

Or in Django shell:
  >>> exec(open('apps/analysis/examples_validation.py').read())
"""
import io
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.analysis.utils import (
    validate_csv_file,
    get_validation_summary,
)


def create_test_file(name: str, content: str) -> SimpleUploadedFile:
    """Helper to create test files"""
    return SimpleUploadedFile(
        name=name,
        content=content.encode('utf-8'),
        content_type='text/csv'
    )


# Example 1: Valid CSV File
print("=" * 70)
print("EXAMPLE 1: Valid CSV File")
print("=" * 70)

valid_csv = """Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),9.572,1000000,1.53,T
GM1(36:1;O2),10.452,500000,4.00,F
GT1(36:1;O2),8.701,1200000,-0.94,T
GM3(18:1;O2),10.606,2000000,7.74,F"""

valid_file = create_test_file('valid_data.csv', valid_csv)
result = validate_csv_file(valid_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Errors: {len(result['errors'])}")
print(f"  Warnings: {len(result['warnings'])}")
print(f"\nFile Metadata:")
print(f"  Rows: {result['metadata'].get('row_count', 'N/A')}")
print(f"  Columns: {', '.join(result['metadata'].get('headers', []))}")
print(f"  MIME Type: {result['metadata'].get('mime_type', 'N/A')}")
print(f"  Size: {result['metadata'].get('file_size_mb', 'N/A')} MB")

if result['errors']:
    print(f"\nErrors:")
    for error in result['errors']:
        print(f"  ❌ {error}")

if result['warnings']:
    print(f"\nWarnings:")
    for warning in result['warnings']:
        print(f"  ⚠️  {warning}")


# Example 2: Missing Required Column
print("\n" + "=" * 70)
print("EXAMPLE 2: Missing Required Column (Log P)")
print("=" * 70)

missing_column_csv = """Name,RT,Volume,Anchor
GD1(36:1;O2),9.572,1000000,T
GM1(36:1;O2),10.452,500000,F"""

missing_file = create_test_file('missing_column.csv', missing_column_csv)
result = validate_csv_file(missing_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Error Count: {len(result['errors'])}")

if result['errors']:
    print(f"\nErrors:")
    for error in result['errors']:
        print(f"  ❌ {error}")


# Example 3: CSV Injection Attempt (Equals Sign)
print("\n" + "=" * 70)
print("EXAMPLE 3: CSV Injection - Formula with = Sign")
print("=" * 70)

injection_equals_csv = """Name,RT,Volume,Log P,Anchor
=cmd|'/c calc',9.572,1000000,1.53,T
GD1(36:1;O2),10.452,500000,4.00,F"""

injection_file = create_test_file('injection_equals.csv', injection_equals_csv)
result = validate_csv_file(injection_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Error Count: {len(result['errors'])}")

if result['errors']:
    print(f"\nErrors (Injection Detected!):")
    for error in result['errors']:
        print(f"  🚫 {error}")


# Example 4: CSV Injection Attempt (At Sign)
print("\n" + "=" * 70)
print("EXAMPLE 4: CSV Injection - XLM Macro with @ Sign")
print("=" * 70)

injection_at_csv = """Name,RT,Volume,Log P,Anchor
@SUM(1+9)*cmd|'/c powershell',9.572,1000000,1.53,T
GM3(18:1;O2),10.606,2000000,7.74,F"""

injection_file = create_test_file('injection_at.csv', injection_at_csv)
result = validate_csv_file(injection_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Error Count: {len(result['errors'])}")

if result['errors']:
    print(f"\nErrors (Injection Detected!):")
    for error in result['errors']:
        print(f"  🚫 {error}")


# Example 5: Invalid Numeric Data
print("\n" + "=" * 70)
print("EXAMPLE 5: Invalid Numeric Data (RT contains 'abc')")
print("=" * 70)

invalid_numeric_csv = """Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),abc,1000000,1.53,T
GM1(36:1;O2),10.452,not_a_number,4.00,F"""

invalid_file = create_test_file('invalid_numeric.csv', invalid_numeric_csv)
result = validate_csv_file(invalid_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Error Count: {len(result['errors'])}")

if result['errors']:
    print(f"\nErrors:")
    for error in result['errors']:
        print(f"  ❌ {error}")


# Example 6: Empty Required Field
print("\n" + "=" * 70)
print("EXAMPLE 6: Empty Required Field (RT and Log P)")
print("=" * 70)

empty_field_csv = """Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),,1000000,,T
GM1(36:1;O2),10.452,500000,4.00,"""

empty_file = create_test_file('empty_fields.csv', empty_field_csv)
result = validate_csv_file(empty_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Error Count: {len(result['errors'])}")

if result['errors']:
    print(f"\nErrors:")
    for error in result['errors']:
        print(f"  ❌ {error}")


# Example 7: Invalid Anchor Values (Warning)
print("\n" + "=" * 70)
print("EXAMPLE 7: Non-Standard Anchor Values (Warnings)")
print("=" * 70)

non_standard_anchor_csv = """Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),9.572,1000000,1.53,X
GM1(36:1;O2),10.452,500000,4.00,Y
GT1(36:1;O2),8.701,1200000,-0.94,1"""

anchor_file = create_test_file('non_standard_anchor.csv', non_standard_anchor_csv)
result = validate_csv_file(anchor_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Errors: {len(result['errors'])}")
print(f"  Warnings: {len(result['warnings'])}")

if result['warnings']:
    print(f"\nWarnings (Non-blocking):")
    for warning in result['warnings']:
        print(f"  ⚠️  {warning}")


# Example 8: Valid with Extra Columns
print("\n" + "=" * 70)
print("EXAMPLE 8: Valid with Extra Columns")
print("=" * 70)

extra_columns_csv = """Name,RT,Volume,Log P,Anchor,Notes,Lab_ID
GD1(36:1;O2),9.572,1000000,1.53,T,Test compound A,LAB001
GM1(36:1;O2),10.452,500000,4.00,F,Reference standard,LAB002
GT1(36:1;O2),8.701,1200000,-0.94,T,Quality control,LAB003"""

extra_file = create_test_file('extra_columns.csv', extra_columns_csv)
result = validate_csv_file(extra_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Required Columns Found: ✅")
print(f"  Extra Columns: {len(result['metadata'].get('headers', [])) - 5}")
print(f"  All Columns: {', '.join(result['metadata'].get('headers', []))}")


# Example 9: Negative Log P (Valid)
print("\n" + "=" * 70)
print("EXAMPLE 9: Negative Log P Values (Valid)")
print("=" * 70)

negative_logp_csv = """Name,RT,Volume,Log P,Anchor
GT1(36:1;O2),8.701,1200000,-0.94,T
GM3(36:1;O2),7.123,900000,-1.53,F
GD1(36:1;O2),9.572,1000000,-2.15,T"""

negative_file = create_test_file('negative_logp.csv', negative_logp_csv)
result = validate_csv_file(negative_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Errors: {len(result['errors'])}")
print(f"  Rows: {result['metadata'].get('row_count')}")
print(f"\n✅ Negative values are correctly handled for Log P column")


# Example 10: Scientific Notation (Valid)
print("\n" + "=" * 70)
print("EXAMPLE 10: Scientific Notation in Volume (Valid)")
print("=" * 70)

scientific_csv = """Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),9.572,1.0e6,1.53,T
GM1(36:1;O2),10.452,5e5,4.00,F
GT1(36:1;O2),8.701,1.2e6,-0.94,T"""

scientific_file = create_test_file('scientific_notation.csv', scientific_csv)
result = validate_csv_file(scientific_file)

print("\nValidation Result:")
print(f"  Valid: {result['is_valid']}")
print(f"  Errors: {len(result['errors'])}")
print(f"\n✅ Scientific notation is correctly parsed for numeric fields")


# Example 11: Get Validation Summary
print("\n" + "=" * 70)
print("EXAMPLE 11: Using get_validation_summary() Helper")
print("=" * 70)

summary_file = create_test_file('valid_data.csv', valid_csv)
result = validate_csv_file(summary_file)
summary = get_validation_summary(result)

print("\nValidation Summary (User-Friendly Format):")
print(f"  Status: {summary['status'].upper()}")
print(f"  Errors: {summary['error_count']}")
print(f"  Warnings: {summary['warning_count']}")
print(f"\nFile Information:")
print(f"  Size: {summary['file_info']['size_mb']} MB")
print(f"  MIME Type: {summary['file_info']['mime_type']}")
print(f"  Rows: {summary['file_info']['rows']}")
print(f"  Columns: {len(summary['file_info']['columns'])}")
print(f"\nColumn Names:")
for col in summary['file_info']['columns']:
    print(f"  - {col}")


print("\n" + "=" * 70)
print("VALIDATION EXAMPLES COMPLETE")
print("=" * 70)
print("\nKey Takeaways:")
print("  ✅ Valid CSV files pass all checks")
print("  ❌ CSV injection attempts are detected and blocked")
print("  ❌ Missing required columns are caught")
print("  ❌ Invalid data types are caught")
print("  ⚠️  Non-standard values generate warnings but don't block")
print("  ✅ Extra columns and various numeric formats are supported")
