"""
Rule 9: Cross-Prefix Consistency Validator

Validates consistency of RT predictions and patterns across different
prefix groups (GM, GD, GT, GQ, GP) with the same lipid composition.

Key validations:
1. Same lipid suffix should follow expected RT ordering across prefixes
2. Regression parameters should be consistent across related prefixes
3. Identify shared outliers appearing in multiple prefix groups
4. Validate that category RT ordering is preserved for matched pairs
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)


# Expected RT ordering by category (more sugars = lower RT)
# GP (5 sialic) < GQ (4) < GT (3) < GD (2) < GM (1)
CATEGORY_ORDER = ['GP', 'GQ', 'GT', 'GD', 'GM']
CATEGORY_RANK = {cat: i for i, cat in enumerate(CATEGORY_ORDER)}

# Sialic acid count by category prefix
SIALIC_ACID_COUNT = {
    'GP': 5,  # Pentasialo
    'GQ': 4,  # Tetrasialo
    'GT': 3,  # Trisialo
    'GD': 2,  # Disialo
    'GM': 1,  # Monosialo
}


@dataclass
class CrossPrefixWarning:
    """Container for a cross-prefix validation warning"""
    rule: str = "Rule 9: Cross-Prefix Consistency"
    severity: str = 'warning'  # 'info', 'warning', 'error'
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'rule': self.rule,
            'severity': self.severity,
            'message': self.message,
            'details': self.details,
        }


@dataclass
class PrefixPairComparison:
    """Comparison result for a pair of compounds with different prefixes"""
    compound_a: str
    compound_b: str
    prefix_a: str
    prefix_b: str
    suffix: str  # Shared lipid composition
    rt_a: float
    rt_b: float
    expected_order: str  # e.g., "GM > GD" (GM should have higher RT)
    actual_order: str
    is_valid: bool
    rt_difference: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'compound_a': self.compound_a,
            'compound_b': self.compound_b,
            'prefix_a': self.prefix_a,
            'prefix_b': self.prefix_b,
            'suffix': self.suffix,
            'rt_a': float(self.rt_a),
            'rt_b': float(self.rt_b),
            'expected_order': self.expected_order,
            'actual_order': self.actual_order,
            'is_valid': bool(self.is_valid),
            'rt_difference': float(self.rt_difference),
        }


@dataclass
class RegressionConsistency:
    """Consistency analysis of regression parameters across prefixes"""
    parameter: str  # e.g., "Log P coefficient"
    values: Dict[str, float]  # prefix -> value
    mean: float
    std: float
    cv: float  # Coefficient of variation
    is_consistent: bool
    outlier_prefixes: List[str]  # Prefixes with outlier values

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'parameter': self.parameter,
            'values': {k: float(v) for k, v in self.values.items()},
            'mean': float(self.mean),
            'std': float(self.std),
            'cv': float(self.cv),
            'is_consistent': bool(self.is_consistent),
            'outlier_prefixes': self.outlier_prefixes,
        }


@dataclass
class CrossPrefixAnalysis:
    """Complete cross-prefix consistency analysis results"""
    is_valid: bool
    total_comparisons: int
    valid_comparisons: int
    invalid_comparisons: int
    pair_comparisons: List[PrefixPairComparison]
    regression_consistency: List[RegressionConsistency]
    shared_outliers: List[Dict[str, Any]]
    category_violations: List[Dict[str, Any]]
    warnings: List[CrossPrefixWarning] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'is_valid': bool(self.is_valid),
            'total_comparisons': int(self.total_comparisons),
            'valid_comparisons': int(self.valid_comparisons),
            'invalid_comparisons': int(self.invalid_comparisons),
            'pair_comparisons': [p.to_dict() for p in self.pair_comparisons],
            'regression_consistency': [r.to_dict() for r in self.regression_consistency],
            'shared_outliers': self.shared_outliers,
            'category_violations': self.category_violations,
            'warnings': [w.to_dict() for w in self.warnings],
            'statistics': self.statistics,
        }


class CrossPrefixValidator:
    """
    Validates cross-prefix consistency in ganglioside analysis.

    This validator implements Rule 9 of the analysis pipeline:
    1. Check RT ordering for same-suffix compounds across prefixes
    2. Validate regression parameter consistency
    3. Identify shared outliers across prefix groups
    4. Track overall consistency statistics

    Attributes:
        rt_tolerance: Tolerance for RT comparisons (default: 0.1 min)
        cv_threshold: Max coefficient of variation for consistency (default: 0.5)
        min_pairs_for_analysis: Minimum pairs needed for analysis (default: 3)
    """

    def __init__(
        self,
        rt_tolerance: float = 0.1,
        cv_threshold: float = 0.5,
        min_pairs_for_analysis: int = 3,
    ):
        """
        Initialize the CrossPrefixValidator.

        Args:
            rt_tolerance: RT tolerance for comparisons (minutes)
            cv_threshold: Max CV for regression parameter consistency
            min_pairs_for_analysis: Min pairs needed for cross-prefix analysis
        """
        self.rt_tolerance = rt_tolerance
        self.cv_threshold = cv_threshold
        self.min_pairs_for_analysis = min_pairs_for_analysis

    def _extract_category(self, prefix: str) -> str:
        """
        Extract category (GM, GD, GT, GQ, GP) from prefix.

        Args:
            prefix: Full prefix (e.g., "GD1a", "GM3")

        Returns:
            Category code (e.g., "GD", "GM")
        """
        # Remove modifications first
        clean_prefix = prefix.split('+')[0]
        # Extract first two characters
        if len(clean_prefix) >= 2:
            return clean_prefix[:2].upper()
        return clean_prefix.upper()

    def _extract_suffix(self, compound_name: str) -> str:
        """
        Extract lipid composition suffix from compound name.

        Args:
            compound_name: Full compound name

        Returns:
            Suffix (e.g., "36:1;O2")
        """
        import re
        match = re.search(r'\(([^)]+)\)$', compound_name)
        return match.group(1) if match else ""

    def _compare_pair(
        self,
        compound_a: str,
        compound_b: str,
        prefix_a: str,
        prefix_b: str,
        rt_a: float,
        rt_b: float,
        suffix: str,
    ) -> PrefixPairComparison:
        """
        Compare a pair of compounds with different prefixes.

        Args:
            compound_a, compound_b: Compound names
            prefix_a, prefix_b: Prefix parts
            rt_a, rt_b: Retention times
            suffix: Shared lipid composition

        Returns:
            PrefixPairComparison result
        """
        cat_a = self._extract_category(prefix_a)
        cat_b = self._extract_category(prefix_b)

        rank_a = CATEGORY_RANK.get(cat_a, -1)
        rank_b = CATEGORY_RANK.get(cat_b, -1)

        # Determine expected order
        # Higher rank = fewer sugars = higher RT (more hydrophobic)
        if rank_a > rank_b:
            expected_order = f"{cat_a} > {cat_b}"
            expected_rt_relation = rt_a > rt_b
        elif rank_a < rank_b:
            expected_order = f"{cat_a} < {cat_b}"
            expected_rt_relation = rt_a < rt_b
        else:
            expected_order = f"{cat_a} = {cat_b}"
            expected_rt_relation = True  # Same category, no ordering constraint

        # Determine actual order
        rt_diff = rt_a - rt_b
        if abs(rt_diff) < self.rt_tolerance:
            actual_order = f"{cat_a} ~ {cat_b}"
            is_valid = True  # Within tolerance
        elif rt_a > rt_b:
            actual_order = f"{cat_a} > {cat_b}"
            is_valid = expected_rt_relation or abs(rt_diff) < self.rt_tolerance
        else:
            actual_order = f"{cat_a} < {cat_b}"
            is_valid = expected_rt_relation or abs(rt_diff) < self.rt_tolerance

        return PrefixPairComparison(
            compound_a=compound_a,
            compound_b=compound_b,
            prefix_a=prefix_a,
            prefix_b=prefix_b,
            suffix=suffix,
            rt_a=rt_a,
            rt_b=rt_b,
            expected_order=expected_order,
            actual_order=actual_order,
            is_valid=is_valid,
            rt_difference=rt_diff,
        )

    def _find_suffix_groups(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, List[Tuple[str, str, float]]]:
        """
        Group compounds by lipid suffix.

        Args:
            df: DataFrame with Name, prefix, and RT columns

        Returns:
            Dictionary mapping suffix to list of (name, prefix, RT) tuples
        """
        groups: Dict[str, List[Tuple[str, str, float]]] = {}

        for _, row in df.iterrows():
            suffix = self._extract_suffix(row['Name'])
            if not suffix:
                continue

            prefix = row.get('prefix', row.get('base_prefix', ''))
            rt = row['RT']

            if suffix not in groups:
                groups[suffix] = []
            groups[suffix].append((row['Name'], prefix, rt))

        return groups

    def _analyze_pair_ordering(
        self,
        df: pd.DataFrame,
    ) -> Tuple[List[PrefixPairComparison], List[Dict[str, Any]]]:
        """
        Analyze RT ordering for pairs with same suffix but different prefixes.

        Args:
            df: DataFrame with compound data

        Returns:
            Tuple of (pair comparisons, category violations)
        """
        comparisons = []
        violations = []

        suffix_groups = self._find_suffix_groups(df)

        for suffix, compounds in suffix_groups.items():
            if len(compounds) < 2:
                continue

            # Compare all pairs within the same suffix group
            for i in range(len(compounds)):
                for j in range(i + 1, len(compounds)):
                    name_a, prefix_a, rt_a = compounds[i]
                    name_b, prefix_b, rt_b = compounds[j]

                    cat_a = self._extract_category(prefix_a)
                    cat_b = self._extract_category(prefix_b)

                    # Only compare different categories
                    if cat_a == cat_b:
                        continue

                    comparison = self._compare_pair(
                        name_a, name_b, prefix_a, prefix_b, rt_a, rt_b, suffix
                    )
                    comparisons.append(comparison)

                    if not comparison.is_valid:
                        violations.append({
                            'suffix': suffix,
                            'compound_a': name_a,
                            'compound_b': name_b,
                            'expected': comparison.expected_order,
                            'actual': comparison.actual_order,
                            'rt_difference': float(comparison.rt_difference),
                        })

        return comparisons, violations

    def _analyze_regression_consistency(
        self,
        regression_results: Optional[Dict[str, Any]],
    ) -> List[RegressionConsistency]:
        """
        Analyze consistency of regression parameters across prefixes.

        Args:
            regression_results: Dictionary with regression results per prefix

        Returns:
            List of RegressionConsistency objects
        """
        if not regression_results:
            return []

        consistencies = []

        # Collect parameters by name across prefixes
        params: Dict[str, Dict[str, float]] = {}

        for prefix, result in regression_results.items():
            if not isinstance(result, dict):
                continue

            coefficients = result.get('coefficients', {})
            for param, value in coefficients.items():
                if param not in params:
                    params[param] = {}
                params[param][prefix] = float(value)

        # Analyze each parameter's consistency
        for param, values in params.items():
            if len(values) < 2:
                continue

            values_array = np.array(list(values.values()))
            mean = float(np.mean(values_array))
            std = float(np.std(values_array))
            cv = abs(std / mean) if abs(mean) > 1e-10 else 0.0

            is_consistent = cv <= self.cv_threshold

            # Find outliers using z-score
            outlier_prefixes = []
            if std > 1e-10:
                z_scores = np.abs((values_array - mean) / std)
                for prefix, z in zip(values.keys(), z_scores):
                    if z > 2.0:  # 2 standard deviations
                        outlier_prefixes.append(prefix)

            consistencies.append(RegressionConsistency(
                parameter=param,
                values=values,
                mean=mean,
                std=std,
                cv=cv,
                is_consistent=is_consistent,
                outlier_prefixes=outlier_prefixes,
            ))

        return consistencies

    def _find_shared_outliers(
        self,
        rule1_results: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Find outliers that appear in multiple prefix groups.

        Args:
            rule1_results: Dictionary with Rule 1 regression results

        Returns:
            List of shared outlier information
        """
        if not rule1_results:
            return []

        # Collect outliers by suffix
        outliers_by_suffix: Dict[str, List[Dict[str, Any]]] = {}

        prefix_results = rule1_results.get('prefix_results', {})
        for prefix, result in prefix_results.items():
            if not isinstance(result, dict):
                continue

            outliers = result.get('outliers', [])
            for outlier in outliers:
                if not isinstance(outlier, dict):
                    continue

                name = outlier.get('name', outlier.get('compound', ''))
                suffix = self._extract_suffix(name)
                if not suffix:
                    continue

                if suffix not in outliers_by_suffix:
                    outliers_by_suffix[suffix] = []
                outliers_by_suffix[suffix].append({
                    'name': name,
                    'prefix': prefix,
                    'reason': outlier.get('reason', 'outlier'),
                })

        # Find suffixes with outliers in multiple prefixes
        shared = []
        for suffix, outliers in outliers_by_suffix.items():
            prefixes = set(o['prefix'] for o in outliers)
            if len(prefixes) >= 2:
                shared.append({
                    'suffix': suffix,
                    'prefixes': list(prefixes),
                    'outliers': outliers,
                    'count': len(outliers),
                })

        return shared

    def _calculate_statistics(
        self,
        comparisons: List[PrefixPairComparison],
        violations: List[Dict[str, Any]],
        consistencies: List[RegressionConsistency],
        shared_outliers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate summary statistics.

        Args:
            comparisons: List of pair comparisons
            violations: List of violations
            consistencies: List of regression consistencies
            shared_outliers: List of shared outliers

        Returns:
            Dictionary of statistics
        """
        total = len(comparisons)
        valid = sum(1 for c in comparisons if c.is_valid)
        invalid = total - valid

        # Consistency rate
        consistent_params = sum(1 for c in consistencies if c.is_consistent)
        total_params = len(consistencies)

        return {
            'total_comparisons': int(total),
            'valid_comparisons': int(valid),
            'invalid_comparisons': int(invalid),
            'validity_rate': float(valid / total) if total > 0 else 1.0,
            'consistent_parameters': int(consistent_params),
            'total_parameters': int(total_params),
            'consistency_rate': float(consistent_params / total_params) if total_params > 0 else 1.0,
            'shared_outlier_groups': len(shared_outliers),
            'total_shared_outliers': sum(s['count'] for s in shared_outliers),
        }

    def validate(
        self,
        df: pd.DataFrame,
        regression_results: Optional[Dict[str, Any]] = None,
        rule1_results: Optional[Dict[str, Any]] = None,
    ) -> CrossPrefixAnalysis:
        """
        Perform complete cross-prefix consistency validation.

        Args:
            df: DataFrame with Name, prefix, and RT columns
            regression_results: Optional regression results for consistency check
            rule1_results: Optional Rule 1 results for shared outlier detection

        Returns:
            CrossPrefixAnalysis with complete results
        """
        warnings: List[CrossPrefixWarning] = []

        # Handle empty DataFrame
        if df.empty:
            return CrossPrefixAnalysis(
                is_valid=True,
                total_comparisons=0,
                valid_comparisons=0,
                invalid_comparisons=0,
                pair_comparisons=[],
                regression_consistency=[],
                shared_outliers=[],
                category_violations=[],
                warnings=[],
                statistics={
                    'total_comparisons': 0,
                    'valid_comparisons': 0,
                    'invalid_comparisons': 0,
                    'validity_rate': 1.0,
                    'consistent_parameters': 0,
                    'total_parameters': 0,
                    'consistency_rate': 1.0,
                    'shared_outlier_groups': 0,
                    'total_shared_outliers': 0,
                },
            )

        # Check required columns
        if 'Name' not in df.columns or 'RT' not in df.columns:
            return CrossPrefixAnalysis(
                is_valid=False,
                total_comparisons=0,
                valid_comparisons=0,
                invalid_comparisons=0,
                pair_comparisons=[],
                regression_consistency=[],
                shared_outliers=[],
                category_violations=[],
                warnings=[CrossPrefixWarning(
                    severity='error',
                    message="DataFrame missing required 'Name' or 'RT' columns",
                )],
            )

        # Ensure prefix column exists
        if 'prefix' not in df.columns and 'base_prefix' not in df.columns:
            # Try to extract from Name
            df = df.copy()
            df['prefix'] = df['Name'].str.extract(r'^([^(+]+)')[0]

        # Analyze pair ordering
        comparisons, violations = self._analyze_pair_ordering(df)

        # Analyze regression consistency
        consistencies = self._analyze_regression_consistency(regression_results)

        # Find shared outliers
        shared_outliers = self._find_shared_outliers(rule1_results)

        # Generate warnings
        for violation in violations:
            warnings.append(CrossPrefixWarning(
                severity='warning',
                message=f"RT ordering violation: {violation['compound_a']} vs {violation['compound_b']}",
                details=violation,
            ))

        for consistency in consistencies:
            if not consistency.is_consistent:
                warnings.append(CrossPrefixWarning(
                    severity='info',
                    message=f"Regression parameter '{consistency.parameter}' shows high variability (CV={consistency.cv:.2f})",
                    details=consistency.to_dict(),
                ))

        for shared in shared_outliers:
            warnings.append(CrossPrefixWarning(
                severity='info',
                message=f"Shared outlier pattern in suffix '{shared['suffix']}' across {len(shared['prefixes'])} prefixes",
                details=shared,
            ))

        # Calculate statistics
        statistics = self._calculate_statistics(
            comparisons, violations, consistencies, shared_outliers
        )

        # Determine overall validity
        is_valid = len(violations) == 0

        return CrossPrefixAnalysis(
            is_valid=is_valid,
            total_comparisons=len(comparisons),
            valid_comparisons=statistics['valid_comparisons'],
            invalid_comparisons=statistics['invalid_comparisons'],
            pair_comparisons=comparisons,
            regression_consistency=consistencies,
            shared_outliers=shared_outliers,
            category_violations=violations,
            warnings=warnings,
            statistics=statistics,
        )

    def get_category_info(self, category: str) -> Dict[str, Any]:
        """
        Get information about a specific category.

        Args:
            category: Category code (e.g., 'GM', 'GD')

        Returns:
            Dictionary with category information
        """
        return {
            'category': category,
            'sialic_acid_count': SIALIC_ACID_COUNT.get(category, 0),
            'rank': CATEGORY_RANK.get(category, -1),
            'expected_rt_order': CATEGORY_ORDER.index(category) if category in CATEGORY_ORDER else -1,
        }

    def get_expected_ordering(self) -> List[Dict[str, Any]]:
        """
        Get expected RT ordering information.

        Returns:
            List of categories in expected RT order (ascending)
        """
        return [
            {
                'category': cat,
                'sialic_acid_count': SIALIC_ACID_COUNT[cat],
                'expected_rt': f"lowest" if i == 0 else f"higher than {CATEGORY_ORDER[i-1]}",
            }
            for i, cat in enumerate(CATEGORY_ORDER)
        ]
