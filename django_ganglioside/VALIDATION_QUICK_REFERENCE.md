# CSV Validation Quick Reference

## Import & Use
```python
from apps.analysis.utils import validate_csv_file

result = validate_csv_file(uploaded_file)
if result['is_valid']:
    # Process file
else:
    # Handle errors
```

## Validation Checks
| Check | What It Does | Error/Warning |
|-------|--------------|---------------|
| **MIME Type** | Ensures file is CSV (text/csv, text/plain, etc.) | ❌ Error |
| **File Size** | Enforces 50MB limit, rejects empty files | ❌ Error |
| **CSV Injection** | Blocks cells starting with =, +, -, @ | ❌ Error |
| **Required Columns** | Checks for Name, RT, Volume, Log P, Anchor | ❌ Error |
| **Data Types** | Validates numeric fields (RT, Volume, Log P) | ❌ Error |
| **Anchor Values** | Warns on non-standard T/F/TRUE/FALSE values | ⚠️ Warning |

## Return Value
```python
{
    'is_valid': bool,
    'errors': ['error1', 'error2'],
    'warnings': ['warning1'],
    'metadata': {
        'mime_type': 'text/csv',
        'file_size_mb': 0.05,
        'row_count': 10,
        'headers': ['Name', 'RT', 'Volume', 'Log P', 'Anchor']
    }
}
```

## Example CSV (VALID)
```csv
Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),9.572,1000000,1.53,T
GM1(36:1;O2),10.452,500000,4.00,F
GT1(36:1;O2),8.701,1200000,-0.94,T
```

## Common Errors

### "CSV injection detected"
**Cause**: Cell starts with =, +, -, or @
**Fix**: Excel formula safety - add single quote prefix: `'=value`

### "Missing required columns"
**Cause**: Name, RT, Volume, Log P, or Anchor missing
**Fix**: Ensure exact column names (case-sensitive)

### "Invalid numeric value"
**Cause**: RT/Volume/Log P contains non-numeric data
**Fix**: Use valid numbers, scientific notation OK (1e6)

### "File size exceeds maximum"
**Cause**: File larger than 50MB
**Fix**: Split into multiple files or request limit increase

## Test Coverage
```bash
# Run tests
docker-compose exec django pytest apps/analysis/tests/test_csv_validation.py -v

# Run specific test
docker-compose exec django pytest \
  apps/analysis/tests/test_csv_validation.py::CSVValidationTestCase::test_validate_csv_injection_detection
```

## Configuration (in utils.py)
```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
CSV_INJECTION_CHARS = {'=', '+', '-', '@'}
REQUIRED_COLUMNS = {'Name', 'RT', 'Volume', 'Log P', 'Anchor'}
NUMERIC_COLUMNS = {'RT', 'Volume', 'Log P'}
```

## Security Notes
- ✅ CSV injection protection (formula attacks)
- ✅ MIME type validation
- ✅ File size DoS protection
- ❌ Doesn't validate data content (application logic)
- ❌ Doesn't prevent SQL injection (Django ORM handles)

## Files
| File | Purpose |
|------|---------|
| `apps/analysis/utils.py` | Validation functions |
| `apps/analysis/serializers.py` | DRF integration |
| `apps/analysis/tests/test_csv_validation.py` | 30+ tests |
| `CSV_VALIDATION_GUIDE.md` | Full documentation |
| `examples_validation.py` | 11 interactive examples |

## Run Examples
```bash
cd django_ganglioside
python manage.py shell < apps/analysis/examples_validation.py
```

## API Usage
```bash
# POST to create analysis session (validation automatic)
curl -X POST /api/analysis/sessions/ \
  -H "Authorization: Bearer <token>" \
  -F "name=My Analysis" \
  -F "uploaded_file=@data.csv"

# Response on validation error: 400 Bad Request
# Response on success: 201 Created
```

## Key Functions
```python
validate_csv_file(uploaded_file)              # Main entry point
validate_mime_type(uploaded_file)             # Check MIME type
validate_file_size(uploaded_file)             # Check size
validate_csv_structure(uploaded_file)         # Check format
validate_csv_data(uploaded_file)              # Check data
validate_required_columns(headers)            # Check columns
get_validation_summary(validation_result)     # User-friendly summary
```

## Valid Data Examples
```csv
# Negative Log P
GT1(36:1;O2),8.701,1200000,-0.94,T

# Scientific notation
GD1(36:1;O2),9.572,1.0e6,1.53,T

# Extra columns (OK)
Name,RT,Volume,Log P,Anchor,Notes
GD1(36:1;O2),9.572,1000000,1.53,T,Test sample

# Special characters in names (OK if not at cell start)
GD1+dHex(36:1;O2),9.572,1000000,1.53,T
GM3+OAc(18:1;O2),10.452,500000,4.00,F
```

## Disabled Features (Not Implemented)
- Custom column mapping (use exact names)
- Case-insensitive columns (case-sensitive)
- CSV preview before upload
- Batch partial import
- Compressed file support
- Custom injection character sets

## Performance
- 50KB CSV: ~50-100ms validation
- 1MB CSV: ~500-1000ms validation
- File reading: Single pass + partial reads
- No caching or external calls

## Debug Logging
```python
# Enable in Django settings
LOGGING = {
    'loggers': {
        'apps.analysis': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}
```

## Troubleshoot
```bash
# Check file manually
file -b --mime-type your_file.csv
csvstat your_file.csv
head -5 your_file.csv

# Test validation in shell
python manage.py shell
>>> from apps.analysis.utils import validate_csv_file
>>> result = validate_csv_file(file)
>>> result['is_valid']
```

## Links
- Full Guide: `CSV_VALIDATION_GUIDE.md`
- Implementation: `VALIDATION_IMPLEMENTATION_SUMMARY.md`
- Code: `apps/analysis/utils.py`
- Tests: `apps/analysis/tests/test_csv_validation.py`
- Examples: `apps/analysis/examples_validation.py`
