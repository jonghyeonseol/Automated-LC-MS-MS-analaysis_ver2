"""
Comprehensive Input Validation for Ganglioside Analysis

This module addresses critical data handling vulnerabilities:
- C2: NaN propagation prevention
- C3: Explicit row dropping with user notification
- C8: Robust anchor boolean parsing
- H4: Case-insensitive column normalization
- H5: Duplicate compound detection
- H8: Physical bounds validation
- H9: Reserved column name protection

All validation results are explicitly returned for API transparency.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Complete validation result with transparency about all operations."""

    is_valid: bool
    df: Optional[pd.DataFrame]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # Transparency metrics
    rows_received: int = 0
    rows_after_validation: int = 0
    rows_dropped: int = 0
    dropped_row_details: List[Dict[str, Any]] = field(default_factory=list)

    # Column normalization tracking
    columns_renamed: Dict[str, str] = field(default_factory=dict)
    columns_original: List[str] = field(default_factory=list)

    # Data quality metrics
    nan_counts_by_column: Dict[str, int] = field(default_factory=dict)
    duplicate_names: List[str] = field(default_factory=list)
    out_of_bounds_values: Dict[str, List[Tuple[int, Any]]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'statistics': {
                'rows_received': self.rows_received,
                'rows_after_validation': self.rows_after_validation,
                'rows_dropped': self.rows_dropped,
                'drop_rate_percent': round(
                    self.rows_dropped / self.rows_received * 100, 2
                ) if self.rows_received > 0 else 0
            },
            'dropped_rows': self.dropped_row_details[:10],  # Limit to first 10
            'columns_renamed': self.columns_renamed,
            'nan_counts': self.nan_counts_by_column,
            'duplicate_names': self.duplicate_names[:10],  # Limit display
            'out_of_bounds': {
                col: [(idx, val) for idx, val in values[:5]]
                for col, values in self.out_of_bounds_values.items()
            }
        }


class InputValidator:
    """
    Comprehensive input validation with full transparency.

    Addresses all critical data handling vulnerabilities identified in
    the algorithm weakness review.
    """

    # Required columns (case-insensitive matching)
    REQUIRED_COLUMNS = {'name', 'rt', 'volume', 'log p', 'anchor'}

    # Column name normalization mapping
    COLUMN_ALIASES = {
        'name': 'Name',
        'compound': 'Name',
        'compound_name': 'Name',
        'rt': 'RT',
        'retention_time': 'RT',
        'retention time': 'RT',
        'volume': 'Volume',
        'area': 'Volume',
        'peak_area': 'Volume',
        'peak area': 'Volume',
        'log p': 'Log P',
        'logp': 'Log P',
        'log_p': 'Log P',
        'clogp': 'Log P',
        'anchor': 'Anchor',
        'is_anchor': 'Anchor',
        'training': 'Anchor',
    }

    # Reserved column names (will be created during preprocessing)
    RESERVED_COLUMNS = {
        'prefix', 'suffix', 'base_prefix',
        'a_component', 'b_component', 'c_component',
        'is_valid', 'validation_reason', 'confidence_score'
    }

    # Physical bounds for LC-MS data
    PHYSICAL_BOUNDS = {
        'RT': (0.0, 120.0),        # 0-120 minutes (typical LC run)
        'Volume': (0.0, 1e15),      # Non-negative, reasonable upper bound
        'Log P': (-10.0, 20.0),     # Extreme but physically possible range
    }

    # Anchor value mappings (case-insensitive)
    ANCHOR_TRUE_VALUES = {'t', 'true', '1', 'yes', 'y', 'anchor'}
    ANCHOR_FALSE_VALUES = {'f', 'false', '0', 'no', 'n', 'test'}

    def __init__(
        self,
        strict_mode: bool = False,
        allow_duplicates: bool = False,
        custom_bounds: Optional[Dict[str, Tuple[float, float]]] = None
    ):
        """
        Initialize validator.

        Args:
            strict_mode: If True, any warning becomes an error
            allow_duplicates: If True, allow duplicate compound names
            custom_bounds: Override default physical bounds
        """
        self.strict_mode = strict_mode
        self.allow_duplicates = allow_duplicates
        self.bounds = {**self.PHYSICAL_BOUNDS}
        if custom_bounds:
            self.bounds.update(custom_bounds)

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        """
        Perform comprehensive validation on input DataFrame.

        Args:
            df: Input DataFrame from CSV upload

        Returns:
            ValidationResult with detailed information about all operations
        """
        result = ValidationResult(
            is_valid=True,
            df=None,
            rows_received=len(df),
            columns_original=list(df.columns)
        )

        # Make a copy to avoid modifying original
        df = df.copy()

        # Step 1: Sanitize dangerous characters (CSV injection prevention)
        df = self._sanitize_csv_injection(df, result)

        # Step 2: Normalize column names
        df, result = self._normalize_columns(df, result)
        if not result.is_valid:
            return result

        # Step 3: Check for reserved column conflicts
        df, result = self._check_reserved_columns(df, result)

        # Step 4: Validate and convert Anchor column
        df, result = self._validate_anchor_column(df, result)
        if not result.is_valid:
            return result

        # Step 5: Validate numeric columns and detect NaN
        df, result = self._validate_numeric_columns(df, result)
        if not result.is_valid:
            return result

        # Step 6: Validate physical bounds
        df, result = self._validate_physical_bounds(df, result)

        # Step 7: Validate compound name format
        df, result = self._validate_compound_names(df, result)
        if not result.is_valid:
            return result

        # Step 8: Check for duplicate compound names
        df, result = self._check_duplicates(df, result)
        if not result.is_valid:
            return result

        # Step 9: Drop invalid rows with full tracking
        df, result = self._drop_invalid_rows(df, result)

        # Final checks
        if len(df) == 0:
            result.is_valid = False
            result.errors.append("No valid rows remain after validation")
            return result

        # Check minimum anchor count
        anchor_count = df['Anchor'].sum()
        if anchor_count < 3:
            result.warnings.append(
                f"Only {anchor_count} anchor compounds. Minimum 3 required for regression, "
                f"10+ recommended for reliable results."
            )

        # Strict mode: convert warnings to errors
        if self.strict_mode and result.warnings:
            result.errors.extend(result.warnings)
            result.warnings = []
            result.is_valid = False

        result.df = df
        result.rows_after_validation = len(df)
        result.rows_dropped = result.rows_received - result.rows_after_validation

        return result

    def _sanitize_csv_injection(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> pd.DataFrame:
        """Remove CSV injection prefixes from all string columns."""
        dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r', '\n')

        for col in df.columns:
            if df[col].dtype == 'object':
                original = df[col].copy()
                df[col] = df[col].apply(
                    lambda x: str(x).lstrip(''.join(dangerous_prefixes))
                    if isinstance(x, str) else x
                )
                changed = (original != df[col]).sum()
                if changed > 0:
                    result.warnings.append(
                        f"Sanitized {changed} values in '{col}' column "
                        f"(removed formula prefixes)"
                    )

        return df

    def _normalize_columns(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Normalize column names to standard format."""

        # Strip whitespace and remove BOM
        df.columns = df.columns.str.strip()
        df.columns = df.columns.str.replace('\ufeff', '', regex=False)

        # Build rename mapping
        rename_map = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in self.COLUMN_ALIASES:
                standard_name = self.COLUMN_ALIASES[col_lower]
                if col != standard_name:
                    rename_map[col] = standard_name

        # Apply renaming
        if rename_map:
            df = df.rename(columns=rename_map)
            result.columns_renamed = rename_map

        # Check for required columns
        current_cols = set(df.columns)
        required = {'Name', 'RT', 'Volume', 'Log P', 'Anchor'}
        missing = required - current_cols

        if missing:
            result.is_valid = False
            result.errors.append(
                f"Missing required columns: {sorted(missing)}. "
                f"Available columns: {sorted(current_cols)}"
            )

        return df, result

    def _check_reserved_columns(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Check for and handle reserved column name conflicts."""
        conflicts = set(df.columns) & self.RESERVED_COLUMNS

        if conflicts:
            # Rename conflicting columns with suffix
            rename_map = {col: f"{col}_original" for col in conflicts}
            df = df.rename(columns=rename_map)
            result.warnings.append(
                f"Reserved column names renamed: {rename_map}"
            )
            result.columns_renamed.update(rename_map)

        return df, result

    def _validate_anchor_column(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Robustly parse Anchor column to boolean."""

        def parse_anchor(value) -> Optional[bool]:
            """Parse anchor value with comprehensive handling."""
            if pd.isna(value):
                return None

            # Handle boolean
            if isinstance(value, bool):
                return value

            # Handle numeric
            if isinstance(value, (int, float)):
                if value == 1:
                    return True
                elif value == 0:
                    return False
                return None

            # Handle string
            val_str = str(value).strip().lower()
            if val_str in self.ANCHOR_TRUE_VALUES:
                return True
            elif val_str in self.ANCHOR_FALSE_VALUES:
                return False

            return None

        # Parse all anchor values
        parsed = df['Anchor'].apply(parse_anchor)

        # Track invalid values
        invalid_mask = parsed.isna()
        invalid_count = invalid_mask.sum()

        if invalid_count > 0:
            invalid_values = df.loc[invalid_mask, 'Anchor'].unique().tolist()
            result.warnings.append(
                f"{invalid_count} rows have invalid Anchor values: {invalid_values[:5]}. "
                f"Valid values: T/F, True/False, 1/0, Yes/No"
            )

            # Mark rows for dropping
            df.loc[invalid_mask, '_invalid_anchor'] = True

        # Apply parsed values
        df['Anchor'] = parsed.fillna(False).astype(bool)

        return df, result

    def _validate_numeric_columns(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Validate and convert numeric columns, tracking NaN creation."""
        numeric_cols = ['RT', 'Volume', 'Log P']

        for col in numeric_cols:
            if col not in df.columns:
                continue

            # Store original for comparison
            original = df[col].copy()

            # Convert to numeric
            df[col] = pd.to_numeric(df[col], errors='coerce')

            # Track NaN creation
            new_nans = df[col].isna() & ~pd.isna(original)
            nan_count = new_nans.sum()

            if nan_count > 0:
                result.nan_counts_by_column[col] = nan_count

                # Get sample of invalid values
                invalid_values = original[new_nans].head(5).tolist()
                result.warnings.append(
                    f"{nan_count} invalid numeric values in '{col}': {invalid_values}"
                )

                # Mark rows for dropping
                df.loc[new_nans, f'_invalid_{col}'] = True

        # Check total NaN impact
        total_nans = sum(result.nan_counts_by_column.values())
        if total_nans > 0:
            result.warnings.append(
                f"Total {total_nans} values coerced to NaN. "
                f"These rows will be excluded from analysis."
            )

        return df, result

    def _validate_physical_bounds(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Validate numeric values are within physical bounds."""

        for col, (min_val, max_val) in self.bounds.items():
            if col not in df.columns:
                continue

            # Skip NaN values
            valid_mask = ~df[col].isna()

            # Check bounds
            below_min = (df[col] < min_val) & valid_mask
            above_max = (df[col] > max_val) & valid_mask
            out_of_bounds = below_min | above_max

            if out_of_bounds.any():
                oob_count = out_of_bounds.sum()
                oob_values = [
                    (idx, val)
                    for idx, val in df.loc[out_of_bounds, col].items()
                ]
                result.out_of_bounds_values[col] = oob_values

                result.warnings.append(
                    f"{oob_count} values in '{col}' outside bounds "
                    f"[{min_val}, {max_val}]"
                )

                # Mark rows for dropping
                df.loc[out_of_bounds, f'_oob_{col}'] = True

        return df, result

    def _validate_compound_names(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Validate compound name format: PREFIX(a:b;c)."""

        # Pattern: PREFIX + optional modifications + (a:b;c)
        # Examples: GD1(36:1;O2), GM3+OAc(18:1;O2), GD1+dHex+Fuc(38:2;O3)
        pattern = r'^[A-Z][A-Z0-9]*(\+[a-zA-Z0-9]+)*\(\d+:\d+;[A-Za-z0-9]+\)$'

        valid_format = df['Name'].str.match(pattern, na=False)
        invalid_count = (~valid_format).sum()

        if invalid_count > 0:
            invalid_names = df.loc[~valid_format, 'Name'].head(5).tolist()
            result.warnings.append(
                f"{invalid_count} compound names don't match expected format "
                f"PREFIX(a:b;c). Examples: {invalid_names}"
            )

            # Mark rows for dropping
            df.loc[~valid_format, '_invalid_name'] = True

        return df, result

    def _check_duplicates(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Check for duplicate compound names."""

        duplicates = df[df['Name'].duplicated(keep=False)]

        if len(duplicates) > 0:
            dup_names = duplicates['Name'].unique().tolist()
            result.duplicate_names = dup_names

            if not self.allow_duplicates:
                # Keep first occurrence, mark rest for dropping
                dup_mask = df['Name'].duplicated(keep='first')
                df.loc[dup_mask, '_duplicate'] = True

                result.warnings.append(
                    f"{len(dup_names)} duplicate compound names found. "
                    f"Keeping first occurrence: {dup_names[:5]}"
                )
            else:
                result.warnings.append(
                    f"{len(dup_names)} duplicate compound names found "
                    f"(duplicates allowed): {dup_names[:5]}"
                )

        return df, result

    def _drop_invalid_rows(
        self, df: pd.DataFrame, result: ValidationResult
    ) -> Tuple[pd.DataFrame, ValidationResult]:
        """Drop invalid rows with full tracking."""

        # Find all invalid row markers
        invalid_cols = [col for col in df.columns if col.startswith('_')]

        if not invalid_cols:
            return df, result

        # Identify rows to drop
        invalid_mask = df[invalid_cols].any(axis=1)
        rows_to_drop = df[invalid_mask]

        # Record details for each dropped row
        for idx, row in rows_to_drop.iterrows():
            reasons = []
            for col in invalid_cols:
                if pd.notna(row.get(col)) and row.get(col):
                    reason_name = col.replace('_invalid_', '').replace('_oob_', 'out_of_bounds_')
                    reasons.append(reason_name)

            result.dropped_row_details.append({
                'row_index': idx,
                'name': row.get('Name', 'N/A'),
                'reasons': reasons
            })

        # Drop invalid rows and cleanup marker columns
        df = df[~invalid_mask].drop(columns=invalid_cols, errors='ignore')
        df = df.reset_index(drop=True)

        return df, result

    def validate_preprocessing_result(
        self, df: pd.DataFrame
    ) -> Tuple[bool, List[str]]:
        """
        Post-preprocessing validation to catch any remaining issues.

        Call this AFTER preprocessing to ensure no NaN values snuck through.
        """
        errors = []

        # Check for NaN in critical columns
        critical_cols = [
            'Name', 'RT', 'Volume', 'Log P', 'Anchor',
            'prefix', 'suffix', 'a_component', 'b_component'
        ]

        for col in critical_cols:
            if col in df.columns:
                nan_count = df[col].isna().sum()
                if nan_count > 0:
                    errors.append(
                        f"Post-preprocessing: {nan_count} NaN values in '{col}'"
                    )

        # Check for empty prefix/suffix
        if 'prefix' in df.columns:
            empty_prefix = (df['prefix'] == '').sum()
            if empty_prefix > 0:
                errors.append(f"Post-preprocessing: {empty_prefix} empty prefix values")

        return len(errors) == 0, errors


# Convenience function for quick validation
def validate_input(
    df: pd.DataFrame,
    strict_mode: bool = False,
    allow_duplicates: bool = False
) -> ValidationResult:
    """
    Convenience function for validating input DataFrame.

    Args:
        df: Input DataFrame
        strict_mode: If True, warnings become errors
        allow_duplicates: If True, allow duplicate compound names

    Returns:
        ValidationResult with complete validation information
    """
    validator = InputValidator(
        strict_mode=strict_mode,
        allow_duplicates=allow_duplicates
    )
    return validator.validate(df)
