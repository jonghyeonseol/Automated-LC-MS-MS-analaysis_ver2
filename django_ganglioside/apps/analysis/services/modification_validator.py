"""
Rule 8: Modification Stack Validator

Validates modification stacking patterns in ganglioside compounds:
1. Parses modification chains from compound names
2. Validates combinatorial completeness (if A and B exist, A+B should exist)
3. Validates RT ordering (stacked modifications should increase RT predictably)
4. Tracks modification frequencies and identifies patterns

Modifications include: OAc (O-acetylation), dHex (deoxyhexose), Fuc (fucose),
NeuAc (sialic acid), Hex (hexose), etc.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# Known modifications and their expected RT effects
MODIFICATION_RT_EFFECTS = {
    'OAc': 'positive',      # O-acetylation increases hydrophobicity
    'dHex': 'positive',     # Deoxyhexose (e.g., fucose) increases RT
    'Fuc': 'positive',      # Fucose increases RT
    'Hex': 'negative',      # Hexose (polar) decreases RT
    'NeuAc': 'negative',    # Sialic acid (polar) decreases RT
    'NeuGc': 'negative',    # N-glycolylneuraminic acid decreases RT
    'Ac': 'positive',       # Acetylation increases RT
    'SO3': 'negative',      # Sulfation (polar) decreases RT
}

# Default expected RT shift range per modification (minutes)
MODIFICATION_RT_RANGES = {
    'OAc': (0.05, 0.5),     # 0.05 to 0.5 min increase
    'dHex': (0.03, 0.4),
    'Fuc': (0.03, 0.4),
    'Hex': (-0.4, -0.03),
    'NeuAc': (-0.5, -0.05),
    'NeuGc': (-0.5, -0.05),
    'Ac': (0.02, 0.3),
    'SO3': (-0.4, -0.02),
}


@dataclass
class ModificationParsed:
    """Parsed modification information from a compound name"""
    compound_name: str
    base_prefix: str  # Prefix without modifications (e.g., GD1 from GD1+OAc)
    modifications: List[str]  # List of modifications in order
    modification_stack: str  # Full modification string (e.g., "+OAc+dHex")
    suffix: str  # Lipid composition (e.g., "36:1;O2")

    @property
    def has_modifications(self) -> bool:
        """Check if compound has any modifications"""
        return len(self.modifications) > 0

    @property
    def modification_count(self) -> int:
        """Number of modifications"""
        return len(self.modifications)

    @property
    def modification_set(self) -> Set[str]:
        """Set of unique modifications"""
        return set(self.modifications)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'compound_name': self.compound_name,
            'base_prefix': self.base_prefix,
            'modifications': self.modifications,
            'modification_stack': self.modification_stack,
            'suffix': self.suffix,
            'has_modifications': self.has_modifications,
            'modification_count': self.modification_count,
        }


@dataclass
class ModificationWarning:
    """Container for a modification validation warning"""
    rule: str = "Rule 8: Modification Stack"
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
class ModificationAnalysis:
    """Complete modification analysis results"""
    is_valid: bool
    compounds_analyzed: int
    compounds_with_modifications: int
    modification_frequency: Dict[str, int]  # Count of each modification
    stack_patterns: Dict[str, int]  # Count of each modification combination
    missing_combinations: List[Dict[str, Any]]  # Expected but missing combinations
    rt_ordering_violations: List[Dict[str, Any]]  # RT ordering problems
    warnings: List[ModificationWarning] = field(default_factory=list)
    parsed_compounds: List[ModificationParsed] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'is_valid': bool(self.is_valid),
            'compounds_analyzed': int(self.compounds_analyzed),
            'compounds_with_modifications': int(self.compounds_with_modifications),
            'modification_frequency': {
                k: int(v) for k, v in self.modification_frequency.items()
            },
            'stack_patterns': {
                k: int(v) for k, v in self.stack_patterns.items()
            },
            'missing_combinations': self.missing_combinations,
            'rt_ordering_violations': self.rt_ordering_violations,
            'warnings': [w.to_dict() for w in self.warnings],
            'statistics': self.statistics,
        }


class ModificationStackValidator:
    """
    Validates modification stacking patterns in ganglioside compounds.

    This validator implements Rule 8 of the analysis pipeline:
    1. Parse modifications from compound names
    2. Check combinatorial completeness (suggest missing combinations)
    3. Validate RT ordering (stacked modifications should increase RT)
    4. Track patterns and provide analysis statistics

    Attributes:
        rt_tolerance: Tolerance for RT comparisons (default: 0.02 min)
        min_samples_for_completeness: Minimum compounds to suggest completeness
        known_modifications: Set of recognized modification patterns
    """

    def __init__(
        self,
        rt_tolerance: float = 0.02,
        min_samples_for_completeness: int = 3,
        known_modifications: Optional[Set[str]] = None,
    ):
        """
        Initialize the ModificationStackValidator.

        Args:
            rt_tolerance: RT tolerance for comparison (minutes)
            min_samples_for_completeness: Min compounds to suggest missing combos
            known_modifications: Set of known modification patterns
        """
        self.rt_tolerance = rt_tolerance
        self.min_samples_for_completeness = min_samples_for_completeness
        self.known_modifications = known_modifications or set(MODIFICATION_RT_EFFECTS.keys())

        # Compile regex pattern for modification parsing
        mod_pattern = '|'.join(re.escape(m) for m in self.known_modifications)
        self._modification_pattern = re.compile(rf'\+({mod_pattern})')

    def parse_modifications(self, compound_name: str) -> ModificationParsed:
        """
        Parse modifications from a compound name.

        Compound name format: PREFIX[+MOD1][+MOD2]...(suffix)
        Example: GD1+OAc+dHex(36:1;O2)

        Args:
            compound_name: Full compound name

        Returns:
            ModificationParsed object with parsed components
        """
        # Extract suffix (lipid composition in parentheses)
        suffix_match = re.search(r'\(([^)]+)\)$', compound_name)
        suffix = suffix_match.group(1) if suffix_match else ""

        # Get the prefix part (everything before the parentheses)
        prefix_part = compound_name[:suffix_match.start()] if suffix_match else compound_name

        # Find all modifications
        modifications = self._modification_pattern.findall(prefix_part)

        # Extract base prefix (without modifications)
        base_prefix = self._modification_pattern.sub('', prefix_part)

        # Build modification stack string
        modification_stack = ''.join(f'+{m}' for m in modifications)

        return ModificationParsed(
            compound_name=compound_name,
            base_prefix=base_prefix,
            modifications=modifications,
            modification_stack=modification_stack,
            suffix=suffix,
        )

    def _find_missing_combinations(
        self,
        parsed_compounds: List[ModificationParsed],
    ) -> List[Dict[str, Any]]:
        """
        Find missing modification combinations.

        If compounds with modifications A and B exist separately,
        a compound with A+B should also exist for completeness.

        Args:
            parsed_compounds: List of parsed compound information

        Returns:
            List of missing combination details
        """
        missing = []

        # Group by base_prefix + suffix (same core compound)
        compound_groups: Dict[str, List[ModificationParsed]] = {}
        for parsed in parsed_compounds:
            key = f"{parsed.base_prefix}_{parsed.suffix}"
            if key not in compound_groups:
                compound_groups[key] = []
            compound_groups[key].append(parsed)

        # Check each group for completeness
        for key, group in compound_groups.items():
            if len(group) < self.min_samples_for_completeness:
                continue

            # Collect all single modifications in this group
            single_mods: Set[str] = set()
            observed_stacks: Set[Tuple[str, ...]] = set()

            for parsed in group:
                observed_stacks.add(tuple(sorted(parsed.modifications)))
                if parsed.modification_count == 1:
                    single_mods.add(parsed.modifications[0])

            # Check for missing pairwise combinations
            single_list = sorted(single_mods)
            for i, mod_a in enumerate(single_list):
                for mod_b in single_list[i+1:]:
                    combo = tuple(sorted([mod_a, mod_b]))
                    if combo not in observed_stacks:
                        base_prefix, suffix = key.split('_', 1)
                        missing.append({
                            'base_prefix': base_prefix,
                            'suffix': suffix,
                            'missing_combination': list(combo),
                            'existing_singles': [mod_a, mod_b],
                            'suggestion': f"{base_prefix}+{'+'.join(combo)}({suffix})",
                        })

        return missing

    def _validate_rt_ordering(
        self,
        df: pd.DataFrame,
        parsed_compounds: List[ModificationParsed],
    ) -> List[Dict[str, Any]]:
        """
        Validate RT ordering for modification stacks.

        For each modification type, check if the RT change matches
        the expected direction (positive/negative effect).

        Args:
            df: DataFrame with RT column
            parsed_compounds: List of parsed compound information

        Returns:
            List of RT ordering violations
        """
        violations = []

        # Create lookup for compound RT
        rt_lookup = dict(zip(df['Name'], df['RT']))

        # Group by base compound (prefix + suffix)
        compound_groups: Dict[str, List[Tuple[ModificationParsed, float]]] = {}
        for parsed in parsed_compounds:
            if parsed.compound_name in rt_lookup:
                key = f"{parsed.base_prefix}_{parsed.suffix}"
                if key not in compound_groups:
                    compound_groups[key] = []
                compound_groups[key].append((parsed, rt_lookup[parsed.compound_name]))

        # Check RT ordering within each group
        for key, group in compound_groups.items():
            # Find base compound (no modifications)
            base_compounds = [(p, rt) for p, rt in group if not p.has_modifications]
            if not base_compounds:
                continue

            base_rt = base_compounds[0][1]

            # Check each modified compound
            for parsed, rt in group:
                if not parsed.has_modifications:
                    continue

                rt_diff = rt - base_rt

                # For each modification, check expected effect
                for mod in parsed.modifications:
                    expected_effect = MODIFICATION_RT_EFFECTS.get(mod, 'unknown')
                    expected_range = MODIFICATION_RT_RANGES.get(mod)

                    if expected_effect == 'positive' and rt_diff < -self.rt_tolerance:
                        violations.append({
                            'compound': parsed.compound_name,
                            'base_compound': base_compounds[0][0].compound_name,
                            'modification': mod,
                            'expected_effect': 'positive (increase RT)',
                            'actual_rt_diff': float(rt_diff),
                            'violation': 'RT decreased when it should increase',
                        })
                    elif expected_effect == 'negative' and rt_diff > self.rt_tolerance:
                        violations.append({
                            'compound': parsed.compound_name,
                            'base_compound': base_compounds[0][0].compound_name,
                            'modification': mod,
                            'expected_effect': 'negative (decrease RT)',
                            'actual_rt_diff': float(rt_diff),
                            'violation': 'RT increased when it should decrease',
                        })

                    # Check magnitude if we have expected range
                    if expected_range and expected_effect != 'unknown':
                        min_shift, max_shift = expected_range
                        if not (min_shift - self.rt_tolerance <= rt_diff <= max_shift + self.rt_tolerance):
                            if (expected_effect == 'positive' and rt_diff > 0) or \
                               (expected_effect == 'negative' and rt_diff < 0):
                                # Correct direction but unexpected magnitude
                                violations.append({
                                    'compound': parsed.compound_name,
                                    'base_compound': base_compounds[0][0].compound_name,
                                    'modification': mod,
                                    'expected_range': list(expected_range),
                                    'actual_rt_diff': float(rt_diff),
                                    'violation': 'RT shift magnitude outside expected range',
                                    'severity': 'info',  # Less severe than wrong direction
                                })

        return violations

    def _calculate_statistics(
        self,
        parsed_compounds: List[ModificationParsed],
        missing_combinations: List[Dict[str, Any]],
        rt_violations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate summary statistics for the analysis.

        Args:
            parsed_compounds: List of parsed compounds
            missing_combinations: List of missing combinations
            rt_violations: List of RT ordering violations

        Returns:
            Dictionary of statistics
        """
        total = len(parsed_compounds)
        with_mods = sum(1 for p in parsed_compounds if p.has_modifications)

        # Calculate average modifications per modified compound
        mod_counts = [p.modification_count for p in parsed_compounds if p.has_modifications]
        avg_mods = float(np.mean(mod_counts)) if mod_counts else 0.0
        max_mods = max(mod_counts) if mod_counts else 0

        # Count error vs info violations
        errors = sum(1 for v in rt_violations if v.get('severity', 'error') == 'error')
        infos = len(rt_violations) - errors

        return {
            'total_compounds': int(total),
            'compounds_with_modifications': int(with_mods),
            'modification_rate': float(with_mods / total) if total > 0 else 0.0,
            'average_modifications_per_modified': float(avg_mods),
            'max_modification_stack': int(max_mods),
            'missing_combinations_count': len(missing_combinations),
            'rt_violations_count': len(rt_violations),
            'rt_violations_errors': errors,
            'rt_violations_info': infos,
            'completeness_score': 1.0 - (len(missing_combinations) / max(1, with_mods)),
            'ordering_score': 1.0 - (errors / max(1, with_mods)),
        }

    def validate(self, df: pd.DataFrame) -> ModificationAnalysis:
        """
        Perform complete modification stack validation.

        Args:
            df: DataFrame with 'Name' and 'RT' columns

        Returns:
            ModificationAnalysis with complete results
        """
        if 'Name' not in df.columns:
            return ModificationAnalysis(
                is_valid=False,
                compounds_analyzed=0,
                compounds_with_modifications=0,
                modification_frequency={},
                stack_patterns={},
                missing_combinations=[],
                rt_ordering_violations=[],
                warnings=[ModificationWarning(
                    severity='error',
                    message="DataFrame missing required 'Name' column",
                )],
            )

        # Parse all compounds
        parsed_compounds = [
            self.parse_modifications(name)
            for name in df['Name'].dropna()
        ]

        # Calculate modification frequency
        modification_frequency: Dict[str, int] = {}
        for parsed in parsed_compounds:
            for mod in parsed.modifications:
                modification_frequency[mod] = modification_frequency.get(mod, 0) + 1

        # Calculate stack pattern frequency
        stack_patterns: Dict[str, int] = {}
        for parsed in parsed_compounds:
            if parsed.modification_stack:
                stack_patterns[parsed.modification_stack] = \
                    stack_patterns.get(parsed.modification_stack, 0) + 1

        # Find missing combinations
        missing_combinations = self._find_missing_combinations(parsed_compounds)

        # Validate RT ordering
        rt_violations = []
        if 'RT' in df.columns:
            rt_violations = self._validate_rt_ordering(df, parsed_compounds)
        else:
            rt_violations = []

        # Generate warnings
        warnings: List[ModificationWarning] = []

        # Warning for each missing combination
        for missing in missing_combinations:
            warnings.append(ModificationWarning(
                severity='info',
                message=f"Missing modification combination: {missing['suggestion']}",
                details=missing,
            ))

        # Warning for each RT violation
        for violation in rt_violations:
            severity = violation.get('severity', 'warning')
            warnings.append(ModificationWarning(
                severity=severity,
                message=f"RT ordering violation for {violation['compound']}: {violation['violation']}",
                details=violation,
            ))

        # Calculate statistics
        statistics = self._calculate_statistics(
            parsed_compounds, missing_combinations, rt_violations
        )

        # Determine overall validity (only errors affect validity)
        error_violations = [v for v in rt_violations if v.get('severity', 'error') != 'info']
        is_valid = len(error_violations) == 0

        compounds_with_mods = sum(1 for p in parsed_compounds if p.has_modifications)

        return ModificationAnalysis(
            is_valid=is_valid,
            compounds_analyzed=len(parsed_compounds),
            compounds_with_modifications=compounds_with_mods,
            modification_frequency=modification_frequency,
            stack_patterns=stack_patterns,
            missing_combinations=missing_combinations,
            rt_ordering_violations=rt_violations,
            warnings=warnings,
            parsed_compounds=parsed_compounds,
            statistics=statistics,
        )

    def get_modification_info(self, modification: str) -> Dict[str, Any]:
        """
        Get information about a specific modification.

        Args:
            modification: Modification code (e.g., 'OAc', 'dHex')

        Returns:
            Dictionary with modification information
        """
        return {
            'name': modification,
            'known': modification in self.known_modifications,
            'expected_rt_effect': MODIFICATION_RT_EFFECTS.get(modification, 'unknown'),
            'expected_rt_range': MODIFICATION_RT_RANGES.get(modification),
        }

    def get_all_modifications(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all known modifications.

        Returns:
            Dictionary mapping modification codes to their info
        """
        return {
            mod: self.get_modification_info(mod)
            for mod in self.known_modifications
        }
