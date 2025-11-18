"""
Utility functions for file validation and CSV processing
"""
import csv
import io
import mimetypes
from typing import Dict, List, Tuple, Any
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError


# MIME types that are acceptable for CSV files
ACCEPTED_MIME_TYPES = {
    'text/csv',
    'text/plain',
    'application/csv',
    'application/vnd.ms-excel',
}

# Characters that indicate CSV injection vulnerability
CSV_INJECTION_CHARS = {'=', '+', '-', '@'}

# Required columns in CSV file
REQUIRED_COLUMNS = {'Name', 'RT', 'Volume', 'Log P', 'Anchor'}

# Numeric columns that must contain valid numbers
NUMERIC_COLUMNS = {'RT', 'Volume', 'Log P'}

# Maximum file size (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB in bytes


def validate_csv_file(uploaded_file) -> Dict[str, Any]:
    """
    Comprehensive CSV file validation with detailed error reporting

    Performs the following validations:
    1. MIME type check (text/csv, application/csv, text/plain)
    2. File size limit (50MB default)
    3. CSV injection detection (cells starting with =, +, -, @)
    4. Required columns check (Name, RT, Volume, Log P, Anchor)
    5. Data type validation (numeric fields)

    Args:
        uploaded_file: Django uploaded file object

    Returns:
        Dict with validation results containing:
        - is_valid: bool
        - errors: List of error messages
        - warnings: List of warning messages
        - metadata: Dict with file metadata

    Raises:
        DRFValidationError: If validation fails
    """
    errors = []
    warnings = []
    metadata = {}

    try:
        # 1. File extension validation
        filename = uploaded_file.name.lower()
        if not filename.endswith('.csv'):
            errors.append(f"Invalid file extension: {filename.split('.')[-1]}. Expected .csv file.")

        # 2. MIME type validation
        mime_type = validate_mime_type(uploaded_file)
        if not mime_type['is_valid']:
            errors.append(mime_type['error'])
        else:
            metadata['mime_type'] = mime_type['detected_type']

        # 3. File size validation
        size_validation = validate_file_size(uploaded_file)
        if not size_validation['is_valid']:
            errors.append(size_validation['error'])
        else:
            metadata['file_size'] = uploaded_file.size
            metadata['file_size_mb'] = round(uploaded_file.size / (1024 * 1024), 2)

        # Stop early if critical errors exist
        if errors:
            raise DRFValidationError({
                'file': errors,
                'detail': 'File validation failed. Please check your file and try again.'
            })

        # Reset file pointer for reading
        uploaded_file.seek(0)

        # 4. CSV format and structure validation
        csv_validation = validate_csv_structure(uploaded_file)
        if not csv_validation['is_valid']:
            errors.extend(csv_validation['errors'])
        else:
            metadata['headers'] = csv_validation['headers']
            metadata['row_count'] = csv_validation['row_count']

        if errors:
            raise DRFValidationError({
                'file': errors,
                'detail': 'CSV structure validation failed.'
            })

        # Reset file pointer again
        uploaded_file.seek(0)

        # 5. Data validation (columns, types, injection)
        data_validation = validate_csv_data(uploaded_file)
        if not data_validation['is_valid']:
            errors.extend(data_validation['errors'])
        if data_validation['warnings']:
            warnings.extend(data_validation['warnings'])

        metadata['data_quality'] = {
            'total_rows': data_validation.get('total_rows', 0),
            'rows_with_issues': data_validation.get('rows_with_issues', []),
        }

        if errors:
            raise DRFValidationError({
                'data': errors,
                'detail': 'CSV data validation failed. Check for injection attempts or invalid data types.'
            })

        return {
            'is_valid': True,
            'errors': [],
            'warnings': warnings,
            'metadata': metadata
        }

    except DRFValidationError:
        raise
    except Exception as e:
        raise DRFValidationError({
            'file': [f'Unexpected error during validation: {str(e)}'],
            'detail': 'An unexpected error occurred while validating the file.'
        })


def validate_mime_type(uploaded_file) -> Dict[str, Any]:
    """
    Validate MIME type of uploaded file

    Args:
        uploaded_file: Django uploaded file object

    Returns:
        Dict with:
        - is_valid: bool
        - detected_type: str (detected MIME type)
        - error: str (error message if invalid)
    """
    filename = uploaded_file.name.lower()

    # Guess MIME type from filename
    guessed_type, _ = mimetypes.guess_type(filename)

    # Check if MIME type is acceptable
    if guessed_type and guessed_type in ACCEPTED_MIME_TYPES:
        return {
            'is_valid': True,
            'detected_type': guessed_type,
            'error': None
        }

    # If guessed type is not in accepted list, default to text/plain for .csv files
    if filename.endswith('.csv'):
        return {
            'is_valid': True,
            'detected_type': 'text/csv',
            'error': None
        }

    return {
        'is_valid': False,
        'detected_type': guessed_type or 'unknown',
        'error': f"Invalid MIME type: {guessed_type or 'unknown'}. Expected CSV file (text/csv, text/plain, or application/csv)."
    }


def validate_file_size(uploaded_file) -> Dict[str, Any]:
    """
    Validate file size is within limits

    Args:
        uploaded_file: Django uploaded file object

    Returns:
        Dict with:
        - is_valid: bool
        - error: str (error message if invalid)
    """
    file_size = uploaded_file.size

    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return {
            'is_valid': False,
            'error': f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_mb:.0f}MB)."
        }

    if file_size == 0:
        return {
            'is_valid': False,
            'error': "File is empty. Please upload a non-empty CSV file."
        }

    return {
        'is_valid': True,
        'error': None
    }


def validate_csv_structure(uploaded_file) -> Dict[str, Any]:
    """
    Validate basic CSV structure and required columns

    Args:
        uploaded_file: Django uploaded file object

    Returns:
        Dict with:
        - is_valid: bool
        - headers: List of column names
        - row_count: int
        - errors: List of error messages
    """
    errors = []
    headers = []
    row_count = 0

    try:
        # Decode file and read CSV
        uploaded_file.seek(0)
        content = uploaded_file.read()

        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            return {
                'is_valid': False,
                'headers': [],
                'row_count': 0,
                'errors': ['File must be UTF-8 encoded text.']
            }

        # Parse CSV
        lines = text_content.strip().split('\n')
        if not lines:
            return {
                'is_valid': False,
                'headers': [],
                'row_count': 0,
                'errors': ['File appears to be empty.']
            }

        # Check for CSV content (should have commas or tabs)
        if ',' not in lines[0] and '\t' not in lines[0]:
            return {
                'is_valid': False,
                'headers': [],
                'row_count': 0,
                'errors': ['File does not appear to be a valid CSV format (no delimiters detected).']
            }

        # Parse headers
        reader = csv.DictReader(io.StringIO(text_content))
        headers = reader.fieldnames or []

        if not headers:
            return {
                'is_valid': False,
                'headers': [],
                'row_count': 0,
                'errors': ['CSV file has no headers.']
            }

        # Check for required columns
        header_set = set(h.strip() for h in headers)
        missing_columns = REQUIRED_COLUMNS - header_set

        if missing_columns:
            errors.append(
                f"Missing required columns: {', '.join(sorted(missing_columns))}. "
                f"Expected columns: {', '.join(sorted(REQUIRED_COLUMNS))}"
            )

        # Count rows
        row_count = sum(1 for _ in reader)

        if row_count == 0:
            errors.append('CSV file has headers but no data rows.')

        return {
            'is_valid': len(errors) == 0,
            'headers': headers,
            'row_count': row_count,
            'errors': errors
        }

    except Exception as e:
        return {
            'is_valid': False,
            'headers': [],
            'row_count': 0,
            'errors': [f'Error parsing CSV structure: {str(e)}']
        }


def validate_csv_data(uploaded_file) -> Dict[str, Any]:
    """
    Validate actual CSV data:
    - Check for CSV injection attempts
    - Validate data types of numeric columns
    - Check for required column values

    Args:
        uploaded_file: Django uploaded file object

    Returns:
        Dict with:
        - is_valid: bool
        - errors: List of error messages
        - warnings: List of warning messages
        - total_rows: int
        - rows_with_issues: List of row numbers with issues
    """
    errors = []
    warnings = []
    rows_with_issues = []
    total_rows = 0

    try:
        uploaded_file.seek(0)
        content = uploaded_file.read()
        text_content = content.decode('utf-8')

        reader = csv.DictReader(io.StringIO(text_content))
        headers = reader.fieldnames or []
        header_set = set(h.strip() for h in headers)

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
            total_rows += 1
            row_errors = []

            # Check each cell for CSV injection
            for col_name, cell_value in row.items():
                if cell_value is None:
                    continue

                cell_str = str(cell_value).strip()

                # CSV Injection detection
                if cell_str and cell_str[0] in CSV_INJECTION_CHARS:
                    row_errors.append(
                        f"Column '{col_name}': Potential CSV injection detected "
                        f"(cells cannot start with {', '.join(sorted(CSV_INJECTION_CHARS))})"
                    )

            # Validate numeric columns
            for num_col in NUMERIC_COLUMNS:
                if num_col in header_set:
                    cell_value = row.get(num_col, '').strip()
                    if cell_value:  # Only validate if not empty
                        try:
                            float(cell_value)
                        except ValueError:
                            row_errors.append(
                                f"Column '{num_col}': Invalid numeric value '{cell_value}'. "
                                f"Expected a number."
                            )

            # Check required columns have values
            for req_col in REQUIRED_COLUMNS:
                if req_col in header_set:
                    cell_value = row.get(req_col, '').strip()
                    if not cell_value:
                        row_errors.append(
                            f"Column '{req_col}': Required field is empty."
                        )

            # Validate Anchor column value
            if 'Anchor' in header_set:
                anchor_value = row.get('Anchor', '').strip()
                if anchor_value and anchor_value.upper() not in {'T', 'F', 'TRUE', 'FALSE'}:
                    warnings.append(
                        f"Row {row_num}: Anchor value '{anchor_value}' is not standard. "
                        f"Expected 'T', 'F', 'TRUE', or 'FALSE'."
                    )

            # Collect row errors
            if row_errors:
                rows_with_issues.append({
                    'row_number': row_num,
                    'errors': row_errors
                })
                errors.extend([f"Row {row_num}: {err}" for err in row_errors])

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'total_rows': total_rows,
            'rows_with_issues': rows_with_issues
        }

    except Exception as e:
        return {
            'is_valid': False,
            'errors': [f'Error validating CSV data: {str(e)}'],
            'warnings': [],
            'total_rows': total_rows,
            'rows_with_issues': rows_with_issues
        }


def validate_required_columns(headers: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if all required columns are present

    Args:
        headers: List of column names

    Returns:
        Tuple of (is_valid: bool, missing_columns: List[str])
    """
    header_set = set(h.strip() for h in headers)
    missing_columns = sorted(REQUIRED_COLUMNS - header_set)
    return len(missing_columns) == 0, missing_columns


def get_validation_summary(validation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a user-friendly summary of validation results

    Args:
        validation_result: Result from validate_csv_file()

    Returns:
        Dict with summary information for user
    """
    return {
        'status': 'valid' if validation_result['is_valid'] else 'invalid',
        'valid': validation_result['is_valid'],
        'error_count': len(validation_result['errors']),
        'warning_count': len(validation_result['warnings']),
        'errors': validation_result['errors'],
        'warnings': validation_result['warnings'],
        'file_info': {
            'size_mb': validation_result['metadata'].get('file_size_mb', 0),
            'mime_type': validation_result['metadata'].get('mime_type', 'unknown'),
            'rows': validation_result['metadata'].get('row_count', 0),
            'columns': validation_result['metadata'].get('headers', []),
        }
    }
