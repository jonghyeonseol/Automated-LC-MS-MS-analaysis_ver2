"""
Unit tests for ChemicalValidator class.

Tests validation of analysis results against chromatography principles:
- Sugar-RT relationship (more sugars → lower RT)
- Category ordering (GP < GQ < GT < GD < GM by average RT)
- Coefficient sign validation (a_component +, b_component -, Log P +)
- O-acetylation magnitude validation (0.3-3.0 min shift)
"""

import pytest
import pandas as pd
import numpy as np

from apps.analysis.services.chemical_validation import (
    ChemicalValidator,
    ValidationResult,
    ValidationWarning
)


# Mark all tests in this module as needing Django database
pytestmark = pytest.mark.django_db(transaction=True)


class TestChemicalValidatorInit:
    """Test ChemicalValidator initialization."""

    def test_default_initialization(self):
        """Test default parameter values."""
        validator = ChemicalValidator()
        assert validator.OACETYL_RT_SHIFT_MIN == 0.3
        assert validator.OACETYL_RT_SHIFT_MAX == 3.0

    def test_category_sugar_map(self):
        """Test category to sugar mapping is defined."""
        validator = ChemicalValidator()
        assert 'GM' in validator.CATEGORY_SUGAR_MAP
        assert 'GD' in validator.CATEGORY_SUGAR_MAP
        assert 'GT' in validator.CATEGORY_SUGAR_MAP
        assert 'GQ' in validator.CATEGORY_SUGAR_MAP
        assert 'GP' in validator.CATEGORY_SUGAR_MAP


class TestSugarRTValidation:
    """Test sugar count vs RT relationship validation."""

    @pytest.fixture
    def validator(self):
        return ChemicalValidator()

    @pytest.fixture
    def valid_sugar_rt_data(self):
        """Data where more sugars = lower RT (correct)."""
        return pd.DataFrame({
            'Name': ['GM3(36:1;O2)', 'GD1(36:1;O2)', 'GT1(36:1;O2)'],
            'RT': [10.5, 9.5, 8.5],  # Lower RT with more sugars
            'suffix': ['36:1;O2', '36:1;O2', '36:1;O2'],
            'sugar_count': [3, 6, 7]  # More sugars
        })

    @pytest.fixture
    def invalid_sugar_rt_data(self):
        """Data where more sugars = higher RT (incorrect) with enough points for significance."""
        return pd.DataFrame({
            'Name': ['GM3(36:1;O2)', 'GM1(36:1;O2)', 'GD1(36:1;O2)',
                     'GD3(36:1;O2)', 'GT1(36:1;O2)', 'GQ1(36:1;O2)'],
            'RT': [7.0, 8.0, 9.0, 10.0, 11.0, 12.0],  # Higher RT with more sugars (WRONG)
            'suffix': ['36:1;O2', '36:1;O2', '36:1;O2', '36:1;O2', '36:1;O2', '36:1;O2'],
            'sugar_count': [3, 5, 6, 5, 7, 8]  # More sugars -> higher RT (WRONG direction)
        })

    def test_valid_sugar_rt_relationship(self, validator, valid_sugar_rt_data):
        """Test that valid sugar-RT relationship passes."""
        result = validator.validate_sugar_rt_relationship(
            valid_sugar_rt_data,
            sugar_count_column='sugar_count',
            rt_column='RT',
            suffix_column='suffix'
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_invalid_sugar_rt_relationship(self, validator, invalid_sugar_rt_data):
        """Test that invalid sugar-RT relationship generates warnings."""
        result = validator.validate_sugar_rt_relationship(
            invalid_sugar_rt_data,
            sugar_count_column='sugar_count',
            rt_column='RT',
            suffix_column='suffix'
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert len(result.warnings) > 0
        assert any('positive' in w.message.lower() or 'sugar' in w.message.lower()
                   for w in result.warnings)

    def test_empty_dataframe(self, validator):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame(columns=['Name', 'RT', 'suffix', 'sugar_count'])
        result = validator.validate_sugar_rt_relationship(
            empty_df,
            sugar_count_column='sugar_count',
            rt_column='RT'
        )

        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_missing_sugar_column(self, validator):
        """Test handling when sugar_count column is missing."""
        df = pd.DataFrame({
            'Name': ['GM1(36:1;O2)'],
            'RT': [10.0],
            'suffix': ['36:1;O2']
        })
        result = validator.validate_sugar_rt_relationship(df)

        # Should pass with info warning about missing column
        assert result.is_valid is True
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == 'info'


class TestCategoryOrderingValidation:
    """Test cross-category RT ordering validation."""

    @pytest.fixture
    def validator(self):
        return ChemicalValidator()

    @pytest.fixture
    def valid_category_ordering_data(self):
        """Data with correct RT ordering: GP < GQ < GT < GD < GM."""
        return pd.DataFrame({
            'Name': ['GM3(36:1;O2)', 'GD1(36:1;O2)', 'GT1(36:1;O2)',
                     'GQ1(36:1;O2)', 'GP1(36:1;O2)'],
            'RT': [10.5, 9.5, 8.5, 7.5, 6.5],  # Correct: GM > GD > GT > GQ > GP
            'category': ['GM', 'GD', 'GT', 'GQ', 'GP']
        })

    @pytest.fixture
    def invalid_category_ordering_data(self):
        """Data with incorrect RT ordering."""
        return pd.DataFrame({
            'Name': ['GM3(36:1;O2)', 'GD1(36:1;O2)', 'GT1(36:1;O2)'],
            'RT': [6.5, 9.5, 10.5],  # WRONG: GM < GD < GT (should be opposite)
            'category': ['GM', 'GD', 'GT']
        })

    def test_valid_category_ordering(self, validator, valid_category_ordering_data):
        """Test that valid category ordering passes."""
        result = validator.validate_category_ordering(
            valid_category_ordering_data,
            rt_column='RT',
            category_column='category'
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_invalid_category_ordering(self, validator, invalid_category_ordering_data):
        """Test that invalid category ordering generates warnings."""
        result = validator.validate_category_ordering(
            invalid_category_ordering_data,
            rt_column='RT',
            category_column='category'
        )

        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert len(result.warnings) > 0

    def test_single_category(self, validator):
        """Test handling of single category (no ordering to validate)."""
        single_cat_df = pd.DataFrame({
            'Name': ['GM1(36:1;O2)', 'GM3(36:1;O2)'],
            'RT': [10.0, 11.0],
            'category': ['GM', 'GM']
        })
        result = validator.validate_category_ordering(
            single_cat_df,
            rt_column='RT',
            category_column='category'
        )

        # Single category = no ordering to validate = valid
        assert result.is_valid is True


class TestCoefficientSignValidation:
    """Test regression coefficient sign validation."""

    @pytest.fixture
    def validator(self):
        return ChemicalValidator()

    def test_valid_coefficient_signs(self, validator):
        """Test that correct coefficient signs pass."""
        # Correct signs: a_component +, b_component -, Log P +
        regression_result = {
            'coefficients': {
                'features': {
                    'a_component': 0.5,   # Positive (correct)
                    'b_component': -0.3,  # Negative (correct)
                    'Log P': 0.8          # Positive (correct)
                }
            }
        }

        result = validator.validate_coefficient_signs(regression_result)

        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_invalid_a_component_sign(self, validator):
        """Test that negative a_component generates warning."""
        regression_result = {
            'coefficients': {
                'features': {
                    'a_component': -0.5,  # WRONG: should be positive
                    'Log P': 0.8
                }
            }
        }

        result = validator.validate_coefficient_signs(regression_result)

        assert result.is_valid is False
        assert len(result.warnings) == 1
        assert 'a_component' in result.warnings[0].message

    def test_invalid_b_component_sign(self, validator):
        """Test that positive b_component generates warning."""
        regression_result = {
            'coefficients': {
                'features': {
                    'b_component': 0.3,   # WRONG: should be negative
                    'Log P': 0.8
                }
            }
        }

        result = validator.validate_coefficient_signs(regression_result)

        assert result.is_valid is False
        assert len(result.warnings) == 1
        assert 'b_component' in result.warnings[0].message

    def test_invalid_log_p_sign(self, validator):
        """Test that negative Log P generates warning."""
        regression_result = {
            'coefficients': {
                'features': {
                    'Log P': -0.8  # WRONG: should be positive
                }
            }
        }

        result = validator.validate_coefficient_signs(regression_result)

        assert result.is_valid is False
        assert len(result.warnings) == 1
        assert 'Log P' in result.warnings[0].message

    def test_multiple_invalid_signs(self, validator):
        """Test multiple coefficient sign violations."""
        regression_result = {
            'coefficients': {
                'features': {
                    'a_component': -0.5,  # WRONG
                    'b_component': 0.3,   # WRONG
                    'Log P': -0.8         # WRONG
                }
            }
        }

        result = validator.validate_coefficient_signs(regression_result)

        assert result.is_valid is False
        assert len(result.warnings) == 3

    def test_missing_coefficients(self, validator):
        """Test handling of missing coefficient structure."""
        # No coefficients key
        result1 = validator.validate_coefficient_signs({})
        assert result1.is_valid is True  # Nothing to validate

        # Empty features
        result2 = validator.validate_coefficient_signs({
            'coefficients': {'features': {}}
        })
        assert result2.is_valid is True


class TestOAcetylationMagnitudeValidation:
    """Test O-acetylation RT shift magnitude validation."""

    @pytest.fixture
    def validator(self):
        return ChemicalValidator()

    def test_valid_magnitude(self, validator):
        """Test that RT shift within range passes."""
        pairs = [
            {
                'oacetyl_name': 'GM3+OAc(36:1;O2)',
                'base_name': 'GM3(36:1;O2)',
                'oacetyl_rt': 11.0,
                'base_rt': 10.0  # Shift = 1.0 min (within 0.3-3.0)
            }
        ]

        result = validator.validate_oacetylation_magnitude(pairs)

        assert result.is_valid is True
        assert len(result.warnings) == 0
        assert result.statistics['valid_shifts'] == 1
        assert result.statistics['unusual_shifts'] == 0

    def test_shift_too_small(self, validator):
        """Test that RT shift < 0.3 min generates warning."""
        pairs = [
            {
                'oacetyl_name': 'GM3+OAc(36:1;O2)',
                'base_name': 'GM3(36:1;O2)',
                'oacetyl_rt': 10.1,
                'base_rt': 10.0  # Shift = 0.1 min (too small)
            }
        ]

        result = validator.validate_oacetylation_magnitude(pairs)

        assert result.is_valid is False
        assert len(result.warnings) == 1
        assert 'small' in result.warnings[0].message.lower()

    def test_shift_too_large(self, validator):
        """Test that RT shift > 3.0 min generates warning."""
        pairs = [
            {
                'oacetyl_name': 'GM3+OAc(36:1;O2)',
                'base_name': 'GM3(36:1;O2)',
                'oacetyl_rt': 15.0,
                'base_rt': 10.0  # Shift = 5.0 min (too large)
            }
        ]

        result = validator.validate_oacetylation_magnitude(pairs)

        assert result.is_valid is False
        assert len(result.warnings) == 1
        assert 'large' in result.warnings[0].message.lower()

    def test_multiple_pairs(self, validator):
        """Test validation with multiple pairs."""
        pairs = [
            {
                'oacetyl_name': 'GM3+OAc(36:1;O2)',
                'base_name': 'GM3(36:1;O2)',
                'oacetyl_rt': 11.0,
                'base_rt': 10.0  # Valid: 1.0 min
            },
            {
                'oacetyl_name': 'GD1+OAc(36:1;O2)',
                'base_name': 'GD1(36:1;O2)',
                'oacetyl_rt': 9.1,
                'base_rt': 9.0  # Invalid: 0.1 min (too small)
            },
            {
                'oacetyl_name': 'GT1+OAc(36:1;O2)',
                'base_name': 'GT1(36:1;O2)',
                'oacetyl_rt': 12.0,
                'base_rt': 8.0  # Invalid: 4.0 min (too large)
            }
        ]

        result = validator.validate_oacetylation_magnitude(pairs)

        assert result.is_valid is False
        assert len(result.warnings) == 2
        assert result.statistics['valid_shifts'] == 1
        assert result.statistics['unusual_shifts'] == 2

    def test_empty_pairs(self, validator):
        """Test handling of empty pairs list."""
        result = validator.validate_oacetylation_magnitude([])

        assert result.is_valid is True
        assert len(result.warnings) == 0

    def test_statistics_calculation(self, validator):
        """Test that statistics are correctly calculated."""
        pairs = [
            {'oacetyl_rt': 11.0, 'base_rt': 10.0},  # 1.0
            {'oacetyl_rt': 11.5, 'base_rt': 10.0},  # 1.5
            {'oacetyl_rt': 12.0, 'base_rt': 10.0},  # 2.0
        ]

        result = validator.validate_oacetylation_magnitude(pairs)

        assert 'mean_shift' in result.statistics
        assert 'std_shift' in result.statistics
        assert result.statistics['mean_shift'] == pytest.approx(1.5, rel=0.01)
        assert len(result.statistics['shift_values']) == 3


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        warnings = [
            ValidationWarning(
                rule='test_rule',
                severity='warning',
                message='Test warning',
                details={'key': 'value'}
            )
        ]

        result = ValidationResult(
            is_valid=False,
            warnings=warnings,
            statistics={'count': 1}
        )

        d = result.to_dict()

        assert d['is_valid'] is False
        assert len(d['warnings']) == 1
        assert d['warnings'][0]['rule'] == 'test_rule'
        assert d['statistics']['count'] == 1


class TestValidationWarning:
    """Test ValidationWarning dataclass."""

    def test_attributes(self):
        """Test ValidationWarning attributes."""
        warning = ValidationWarning(
            rule='coefficient_sign',
            severity='warning',
            message='a_component coefficient is negative',
            details={'coefficient': -0.5}
        )

        assert warning.rule == 'coefficient_sign'
        assert warning.severity == 'warning'
        assert warning.message == 'a_component coefficient is negative'
        assert warning.details['coefficient'] == -0.5


class TestValidateAll:
    """Test validate_all method."""

    @pytest.fixture
    def validator(self):
        return ChemicalValidator()

    def test_validate_all_basic(self, validator):
        """Test running all validations."""
        df = pd.DataFrame({
            'Name': ['GM1(36:1;O2)', 'GD1(36:1;O2)'],
            'RT': [10.0, 9.0],
            'category': ['GM', 'GD'],
            'sugar_count': [5, 6],
            'suffix': ['36:1;O2', '36:1;O2']
        })

        results = validator.validate_all(df)

        assert 'sugar_rt_validation' in results
        assert 'category_ordering' in results
        assert isinstance(results['sugar_rt_validation'], ValidationResult)
        assert isinstance(results['category_ordering'], ValidationResult)

    def test_validate_all_with_regression(self, validator):
        """Test validate_all with regression results."""
        df = pd.DataFrame({
            'Name': ['GM1(36:1;O2)'],
            'RT': [10.0],
            'category': ['GM'],
            'suffix': ['36:1;O2']
        })

        regression_result = {
            'coefficients': {
                'features': {'Log P': 0.5}
            }
        }

        results = validator.validate_all(df, regression_results=regression_result)

        assert 'coefficient_signs' in results
        assert results['coefficient_signs'].is_valid is True

    def test_validate_all_with_oacetyl_pairs(self, validator):
        """Test validate_all with O-acetylation pairs."""
        df = pd.DataFrame({
            'Name': ['GM1(36:1;O2)'],
            'RT': [10.0],
            'category': ['GM'],
            'suffix': ['36:1;O2']
        })

        oacetyl_pairs = [
            {'oacetyl_rt': 11.0, 'base_rt': 10.0}
        ]

        results = validator.validate_all(df, oacetyl_pairs=oacetyl_pairs)

        assert 'oacetylation_magnitude' in results
        assert results['oacetylation_magnitude'].is_valid is True
