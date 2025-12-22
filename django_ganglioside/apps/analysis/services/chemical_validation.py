"""
Chemical Validation Module

Validates analysis results against fundamental chromatography principles:
- Reverse-phase chromatography: RT reflects hydrophobicity
- More carbons (a_component) -> higher hydrophobicity -> higher RT
- More double bonds (b_component) -> lower hydrophobicity -> lower RT
- More sugars/glycans -> lower hydrophobicity -> lower RT
- O-acetylation -> higher hydrophobicity -> higher RT
- Log P (partition coefficient) -> reflects hydrophobicity -> positive correlation with RT
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from scipy import stats
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationWarning:
    """Container for a single validation warning"""
    rule: str
    severity: str  # 'info', 'warning', 'error'
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Container for validation results"""
    is_valid: bool
    warnings: List[ValidationWarning] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'is_valid': self.is_valid,
            'warnings': [
                {
                    'rule': w.rule,
                    'severity': w.severity,
                    'message': w.message,
                    'details': w.details
                }
                for w in self.warnings
            ],
            'statistics': self.statistics
        }


class ChemicalValidator:
    """
    Validates analysis results against chromatography principles.

    Chromatography Principles (Reverse-Phase):
    - Higher hydrophobicity -> Higher retention time (RT)

    Hydrophobicity Factors:
    - More carbons (a_component): +hydrophobicity -> +RT
    - More double bonds (b_component): -hydrophobicity -> -RT
    - More sugars/glycans: -hydrophobicity -> -RT
    - O-acetylation (+OAc): +hydrophobicity -> +RT
    - Log P: Composite measure of hydrophobicity

    Expected coefficient signs in regression:
    - a_component: POSITIVE (more carbons = higher RT)
    - b_component: NEGATIVE (more double bonds = lower RT)
    - sugar_count: NEGATIVE (more sugars = lower RT)
    - Log P: POSITIVE (higher Log P = higher RT)
    """

    # Expected sugar counts by category (sialic acid content)
    CATEGORY_SUGAR_MAP = {
        'GM': {'sialic_acids': 1, 'typical_total_sugars': (3, 5)},
        'GD': {'sialic_acids': 2, 'typical_total_sugars': (5, 6)},
        'GT': {'sialic_acids': 3, 'typical_total_sugars': (6, 7)},
        'GQ': {'sialic_acids': 4, 'typical_total_sugars': (7, 8)},
        'GP': {'sialic_acids': 5, 'typical_total_sugars': (8, 9)},
    }

    # Expected RT ordering (more sugars = lower RT)
    CATEGORY_RT_ORDER = ['GP', 'GQ', 'GT', 'GD', 'GM']  # Expected: ascending RT

    # O-acetylation RT shift bounds (minutes)
    OACETYL_RT_SHIFT_MIN = 0.3
    OACETYL_RT_SHIFT_MAX = 3.0

    def __init__(self):
        logger.info("ChemicalValidator initialized")

    def validate_sugar_rt_relationship(
        self,
        df: pd.DataFrame,
        sugar_count_column: str = 'sugar_count',
        rt_column: str = 'RT',
        suffix_column: str = 'suffix'
    ) -> ValidationResult:
        """
        Validate that sugar count inversely correlates with RT.

        Within compounds having the SAME lipid composition (suffix like 36:1;O2),
        higher sugar count should correlate with lower RT.

        Args:
            df: DataFrame with compound data
            sugar_count_column: Column name for sugar count
            rt_column: Column name for retention time
            suffix_column: Column name for lipid composition (for grouping)

        Returns:
            ValidationResult with warnings for violations
        """
        logger.info("Validating sugar-RT relationship...")

        warnings = []
        statistics = {
            'total_lipid_groups': 0,
            'valid_groups': 0,
            'violation_groups': 0,
            'insufficient_data_groups': 0,
            'correlations': {}
        }

        if sugar_count_column not in df.columns:
            return ValidationResult(
                is_valid=True,
                warnings=[ValidationWarning(
                    rule='sugar_rt_relationship',
                    severity='info',
                    message=f"Column '{sugar_count_column}' not found, skipping validation"
                )],
                statistics=statistics
            )

        # Group by lipid composition (suffix)
        for suffix, group in df.groupby(suffix_column):
            statistics['total_lipid_groups'] += 1

            # Need at least 3 compounds with different sugar counts
            unique_sugars = group[sugar_count_column].nunique()
            if len(group) < 3 or unique_sugars < 2:
                statistics['insufficient_data_groups'] += 1
                continue

            # Calculate correlation between sugar count and RT
            try:
                correlation, p_value = stats.pearsonr(
                    group[sugar_count_column],
                    group[rt_column]
                )
            except Exception as e:
                logger.warning(f"Could not calculate correlation for suffix {suffix}: {e}")
                continue

            statistics['correlations'][suffix] = {
                'correlation': float(correlation),
                'p_value': float(p_value),
                'n_compounds': len(group)
            }

            # Expected: NEGATIVE correlation (more sugars = lower RT)
            if correlation > 0.3 and p_value < 0.1:  # Significant positive correlation = WRONG
                statistics['violation_groups'] += 1
                warnings.append(ValidationWarning(
                    rule='sugar_rt_relationship',
                    severity='warning',
                    message=f"Lipid group '{suffix}': positive correlation between sugar count and RT",
                    details={
                        'suffix': suffix,
                        'correlation': round(correlation, 3),
                        'p_value': round(p_value, 4),
                        'n_compounds': len(group),
                        'expected': 'negative correlation',
                        'explanation': 'More sugars should decrease RT (increase hydrophilicity)'
                    }
                ))
            else:
                statistics['valid_groups'] += 1

        is_valid = len(warnings) == 0

        logger.info(
            f"Sugar-RT validation complete: {statistics['valid_groups']} valid, "
            f"{statistics['violation_groups']} violations, "
            f"{statistics['insufficient_data_groups']} insufficient data"
        )

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            statistics=statistics
        )

    def validate_category_ordering(
        self,
        df: pd.DataFrame,
        category_column: str = 'category',
        rt_column: str = 'RT'
    ) -> ValidationResult:
        """
        Validate that average RT follows expected category ordering.

        Expected ordering (by average RT, ascending):
        GP (most sugars) < GQ < GT < GD < GM (fewest sugars)

        This reflects: more sugars = more hydrophilic = lower RT

        Args:
            df: DataFrame with compound data
            category_column: Column name for ganglioside category
            rt_column: Column name for retention time

        Returns:
            ValidationResult with warnings for violations
        """
        logger.info("Validating category RT ordering...")

        warnings = []
        statistics = {
            'category_avg_rt': {},
            'expected_order': self.CATEGORY_RT_ORDER,
            'actual_order': [],
            'order_violations': []
        }

        if category_column not in df.columns:
            # Try to extract category from prefix
            if 'prefix' in df.columns:
                df = df.copy()
                df[category_column] = df['prefix'].str[:2]
            else:
                return ValidationResult(
                    is_valid=True,
                    warnings=[ValidationWarning(
                        rule='category_ordering',
                        severity='info',
                        message=f"Column '{category_column}' not found, skipping validation"
                    )],
                    statistics=statistics
                )

        # Calculate average RT per category
        category_avg = df.groupby(category_column)[rt_column].mean()
        statistics['category_avg_rt'] = category_avg.to_dict()

        # Get categories present in data, sorted by average RT
        present_categories = [cat for cat in self.CATEGORY_RT_ORDER if cat in category_avg.index]
        actual_order = sorted(present_categories, key=lambda x: category_avg[x])
        statistics['actual_order'] = actual_order

        # Check for violations
        for i in range(len(present_categories) - 1):
            expected_lower = present_categories[i]
            expected_higher = present_categories[i + 1]

            if expected_lower in category_avg.index and expected_higher in category_avg.index:
                if category_avg[expected_lower] > category_avg[expected_higher]:
                    violation = {
                        'lower_category': expected_lower,
                        'higher_category': expected_higher,
                        'lower_avg_rt': round(category_avg[expected_lower], 3),
                        'higher_avg_rt': round(category_avg[expected_higher], 3)
                    }
                    statistics['order_violations'].append(violation)

                    warnings.append(ValidationWarning(
                        rule='category_ordering',
                        severity='warning',
                        message=(
                            f"Category ordering violation: {expected_lower} (avg RT={violation['lower_avg_rt']:.2f}) "
                            f"should have lower RT than {expected_higher} (avg RT={violation['higher_avg_rt']:.2f})"
                        ),
                        details={
                            **violation,
                            'explanation': (
                                f"{expected_lower} has more sugars than {expected_higher}, "
                                f"so should be more hydrophilic and elute earlier"
                            )
                        }
                    ))

        is_valid = len(warnings) == 0

        logger.info(
            f"Category ordering validation complete: "
            f"{len(statistics['order_violations'])} violations found"
        )

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            statistics=statistics
        )

    def validate_coefficient_signs(
        self,
        regression_result: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate that regression coefficients have chemically expected signs.

        Expected signs:
        - a_component (carbon count): POSITIVE (more carbons = higher RT)
        - b_component (double bonds): NEGATIVE (more double bonds = lower RT)
        - sugar_count: NEGATIVE (more sugars = lower RT)
        - Log P: POSITIVE (higher hydrophobicity = higher RT)

        Args:
            regression_result: Regression result dictionary with coefficients

        Returns:
            ValidationResult with warnings for violations
        """
        logger.info("Validating coefficient signs...")

        warnings = []
        statistics = {
            'coefficients_checked': {},
            'sign_violations': []
        }

        # Expected coefficient signs
        expected_signs = {
            'a_component': 'positive',
            'Log P': 'positive',
            'b_component': 'negative',
            'sugar_count': 'negative',
        }

        # Get coefficients from result
        coefficients = regression_result.get('coefficients', {})
        if isinstance(coefficients, dict) and 'features' in coefficients:
            coefficients = coefficients['features']

        for feature, expected_sign in expected_signs.items():
            if feature in coefficients:
                coef_value = coefficients[feature]
                statistics['coefficients_checked'][feature] = {
                    'value': round(float(coef_value), 4),
                    'expected_sign': expected_sign
                }

                # Check sign
                is_positive = coef_value > 0
                expected_positive = expected_sign == 'positive'

                if is_positive != expected_positive:
                    violation = {
                        'feature': feature,
                        'coefficient': round(float(coef_value), 4),
                        'expected_sign': expected_sign,
                        'actual_sign': 'positive' if is_positive else 'negative'
                    }
                    statistics['sign_violations'].append(violation)

                    # Determine explanation based on feature
                    explanations = {
                        'a_component': 'More carbons should increase hydrophobicity and RT',
                        'b_component': 'More double bonds should decrease hydrophobicity and RT',
                        'sugar_count': 'More sugars should decrease hydrophobicity and RT',
                        'Log P': 'Higher Log P indicates higher hydrophobicity, should increase RT'
                    }

                    warnings.append(ValidationWarning(
                        rule='coefficient_signs',
                        severity='warning',
                        message=(
                            f"Coefficient sign violation: {feature} is {violation['actual_sign']} "
                            f"(expected {expected_sign})"
                        ),
                        details={
                            **violation,
                            'explanation': explanations.get(feature, '')
                        }
                    ))

        is_valid = len(warnings) == 0

        logger.info(
            f"Coefficient sign validation complete: "
            f"{len(statistics['sign_violations'])} violations found"
        )

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            statistics=statistics
        )

    def validate_oacetylation_magnitude(
        self,
        oacetyl_pairs: List[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate that O-acetylation RT shifts are within expected range.

        O-acetylation increases hydrophobicity, so:
        - RT(compound+OAc) > RT(compound_base) [already validated by Rule 4]
        - RT shift should typically be 0.3-3.0 minutes

        Args:
            oacetyl_pairs: List of dictionaries with 'oacetyl_rt', 'base_rt' keys

        Returns:
            ValidationResult with warnings for unusual shifts
        """
        logger.info("Validating O-acetylation RT shift magnitudes...")

        warnings = []
        statistics = {
            'total_pairs': len(oacetyl_pairs),
            'valid_shifts': 0,
            'unusual_shifts': 0,
            'shift_values': []
        }

        for pair in oacetyl_pairs:
            oacetyl_rt = pair.get('oacetyl_rt') or pair.get('RT')
            base_rt = pair.get('base_rt') or pair.get('base_RT')

            if oacetyl_rt is None or base_rt is None:
                continue

            rt_shift = oacetyl_rt - base_rt
            statistics['shift_values'].append(round(float(rt_shift), 3))

            if rt_shift < self.OACETYL_RT_SHIFT_MIN:
                statistics['unusual_shifts'] += 1
                warnings.append(ValidationWarning(
                    rule='oacetylation_magnitude',
                    severity='warning',
                    message=f"O-acetylation RT shift too small: {rt_shift:.2f} min",
                    details={
                        'oacetyl_name': pair.get('oacetyl_name', 'unknown'),
                        'base_name': pair.get('base_name', 'unknown'),
                        'rt_shift': round(float(rt_shift), 3),
                        'expected_range': f"{self.OACETYL_RT_SHIFT_MIN}-{self.OACETYL_RT_SHIFT_MAX} min",
                        'explanation': 'Very small RT shift may indicate incorrect peak assignment'
                    }
                ))
            elif rt_shift > self.OACETYL_RT_SHIFT_MAX:
                statistics['unusual_shifts'] += 1
                warnings.append(ValidationWarning(
                    rule='oacetylation_magnitude',
                    severity='warning',
                    message=f"O-acetylation RT shift unusually large: {rt_shift:.2f} min",
                    details={
                        'oacetyl_name': pair.get('oacetyl_name', 'unknown'),
                        'base_name': pair.get('base_name', 'unknown'),
                        'rt_shift': round(float(rt_shift), 3),
                        'expected_range': f"{self.OACETYL_RT_SHIFT_MIN}-{self.OACETYL_RT_SHIFT_MAX} min",
                        'explanation': 'Very large RT shift may indicate different compounds or co-elution'
                    }
                ))
            else:
                statistics['valid_shifts'] += 1

        # Calculate shift statistics
        if statistics['shift_values']:
            statistics['mean_shift'] = round(float(np.mean(statistics['shift_values'])), 3)
            statistics['std_shift'] = round(float(np.std(statistics['shift_values'])), 3)

        is_valid = len(warnings) == 0

        logger.info(
            f"O-acetylation magnitude validation complete: "
            f"{statistics['valid_shifts']} valid, {statistics['unusual_shifts']} unusual"
        )

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            statistics=statistics
        )

    def validate_all(
        self,
        df: pd.DataFrame,
        regression_results: Optional[Dict[str, Any]] = None,
        oacetyl_pairs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, ValidationResult]:
        """
        Run all chemical validations.

        Args:
            df: DataFrame with compound data
            regression_results: Optional regression results with coefficients
            oacetyl_pairs: Optional list of O-acetylation compound pairs

        Returns:
            Dictionary mapping validation name to ValidationResult
        """
        logger.info("Running all chemical validations...")

        results = {}

        # Sugar-RT relationship validation
        results['sugar_rt_validation'] = self.validate_sugar_rt_relationship(df)

        # Category ordering validation
        results['category_ordering'] = self.validate_category_ordering(df)

        # Coefficient sign validation (if regression results provided)
        if regression_results:
            results['coefficient_signs'] = self.validate_coefficient_signs(regression_results)

        # O-acetylation magnitude validation (if pairs provided)
        if oacetyl_pairs:
            results['oacetylation_magnitude'] = self.validate_oacetylation_magnitude(oacetyl_pairs)

        # Summarize
        total_warnings = sum(len(r.warnings) for r in results.values())
        logger.info(f"All chemical validations complete: {total_warnings} total warnings")

        return results

    def to_dict(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Convert validation results to dictionary for JSON serialization"""
        return {
            name: result.to_dict()
            for name, result in results.items()
        }
