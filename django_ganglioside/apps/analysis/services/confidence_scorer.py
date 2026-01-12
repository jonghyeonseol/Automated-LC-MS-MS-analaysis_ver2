"""
Rule 10: Confidence Scorer

Provides probabilistic confidence scoring for compound identifications.
Combines multiple evidence sources to produce an overall confidence level.

Scoring factors:
1. Regression fit quality (R², RMSE)
2. Residual magnitude (distance from expected RT)
3. Bayesian uncertainty (prediction std deviation)
4. Chemical validation results (coefficient signs, RT ordering)
5. Cross-prefix consistency
6. Modification stack validity
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Confidence level classification"""
    HIGH = "high"        # ≥ 0.8
    MEDIUM = "medium"    # 0.6 - 0.8
    LOW = "low"          # 0.4 - 0.6
    VERY_LOW = "very_low"  # < 0.4


# Default scoring weights
DEFAULT_WEIGHTS = {
    'regression_fit': 0.20,       # R² contribution
    'residual': 0.25,             # How close to predicted RT
    'bayesian_uncertainty': 0.20, # Prediction uncertainty
    'chemical_validation': 0.20,  # Chemical rules validation
    'cross_prefix': 0.10,         # Cross-prefix consistency
    'modification_stack': 0.05,   # Modification validation
}


@dataclass
class ConfidenceScore:
    """Confidence score for a single compound"""
    compound_name: str
    overall_score: float
    confidence_level: ConfidenceLevel
    component_scores: Dict[str, float]
    contributing_factors: List[str]
    detracting_factors: List[str]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'compound_name': self.compound_name,
            'overall_score': float(self.overall_score),
            'confidence_level': self.confidence_level.value,
            'component_scores': {
                k: float(v) for k, v in self.component_scores.items()
            },
            'contributing_factors': self.contributing_factors,
            'detracting_factors': self.detracting_factors,
            'warnings': self.warnings,
        }


@dataclass
class ConfidenceAnalysis:
    """Complete confidence scoring analysis"""
    is_valid: bool
    compounds_scored: int
    high_confidence_count: int
    medium_confidence_count: int
    low_confidence_count: int
    very_low_confidence_count: int
    average_score: float
    scores: List[ConfidenceScore]
    statistics: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'is_valid': bool(self.is_valid),
            'compounds_scored': int(self.compounds_scored),
            'high_confidence_count': int(self.high_confidence_count),
            'medium_confidence_count': int(self.medium_confidence_count),
            'low_confidence_count': int(self.low_confidence_count),
            'very_low_confidence_count': int(self.very_low_confidence_count),
            'average_score': float(self.average_score),
            'scores': [s.to_dict() for s in self.scores],
            'statistics': self.statistics,
            'warnings': self.warnings,
        }


class ConfidenceScorer:
    """
    Calculates probabilistic confidence scores for compound identifications.

    This class implements Rule 10 of the analysis pipeline, combining
    evidence from multiple sources to produce an overall confidence level
    for each identified compound.

    Attributes:
        weights: Dictionary of scoring component weights
        high_threshold: Minimum score for HIGH confidence (default: 0.8)
        medium_threshold: Minimum score for MEDIUM confidence (default: 0.6)
        low_threshold: Minimum score for LOW confidence (default: 0.4)
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        high_threshold: float = 0.8,
        medium_threshold: float = 0.6,
        low_threshold: float = 0.4,
    ):
        """
        Initialize the ConfidenceScorer.

        Args:
            weights: Custom weights for scoring components (must sum to 1.0)
            high_threshold: Minimum score for HIGH confidence
            medium_threshold: Minimum score for MEDIUM confidence
            low_threshold: Minimum score for LOW confidence
        """
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.low_threshold = low_threshold

        # Normalize weights to sum to 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.001:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}

    def _classify_confidence(self, score: float) -> ConfidenceLevel:
        """
        Classify a score into a confidence level.

        Args:
            score: Overall confidence score (0-1)

        Returns:
            ConfidenceLevel enum value
        """
        if score >= self.high_threshold:
            return ConfidenceLevel.HIGH
        elif score >= self.medium_threshold:
            return ConfidenceLevel.MEDIUM
        elif score >= self.low_threshold:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _score_regression_fit(
        self,
        r2: Optional[float],
        rmse: Optional[float],
        n_samples: Optional[int],
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score based on regression fit quality.

        Args:
            r2: R-squared value
            rmse: Root mean square error
            n_samples: Number of samples in regression

        Returns:
            Tuple of (score, contributing_factors, detracting_factors)
        """
        contributing = []
        detracting = []

        if r2 is None:
            return 0.5, [], ["Regression fit data unavailable"]

        score = 0.0

        # R² contribution (0-0.7)
        if r2 >= 0.95:
            score += 0.7
            contributing.append(f"Excellent R² ({r2:.3f})")
        elif r2 >= 0.85:
            score += 0.6
            contributing.append(f"Good R² ({r2:.3f})")
        elif r2 >= 0.75:
            score += 0.5
            contributing.append(f"Acceptable R² ({r2:.3f})")
        else:
            score += max(0, r2 * 0.5)
            detracting.append(f"Low R² ({r2:.3f})")

        # Sample size consideration (0-0.3)
        if n_samples is not None:
            if n_samples >= 10:
                score += 0.3
                contributing.append(f"Sufficient sample size (n={n_samples})")
            elif n_samples >= 5:
                score += 0.2
            else:
                score += 0.1
                detracting.append(f"Small sample size (n={n_samples})")

        return min(1.0, score), contributing, detracting

    def _score_residual(
        self,
        residual: Optional[float],
        std_residual: Optional[float],
        predicted_rt: Optional[float],
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score based on residual magnitude.

        Args:
            residual: Raw residual (actual - predicted)
            std_residual: Standardized residual
            predicted_rt: Predicted retention time

        Returns:
            Tuple of (score, contributing_factors, detracting_factors)
        """
        contributing = []
        detracting = []

        if std_residual is None and residual is None:
            return 0.5, [], ["Residual data unavailable"]

        # Use standardized residual if available
        if std_residual is not None:
            abs_std = abs(std_residual)
            if abs_std < 1.0:
                score = 1.0 - (abs_std * 0.2)
                contributing.append(f"Low residual ({std_residual:.2f}σ)")
            elif abs_std < 2.0:
                score = 0.8 - ((abs_std - 1.0) * 0.3)
                contributing.append(f"Moderate residual ({std_residual:.2f}σ)")
            elif abs_std < 2.5:
                score = 0.5 - ((abs_std - 2.0) * 0.4)
                detracting.append(f"High residual ({std_residual:.2f}σ)")
            else:
                score = 0.1
                detracting.append(f"Outlier residual ({std_residual:.2f}σ)")
        else:
            # Fallback to raw residual if standardized not available
            abs_res = abs(residual) if residual else 0
            if abs_res < 0.1:
                score = 1.0
                contributing.append(f"Very low RT error ({residual:.3f} min)")
            elif abs_res < 0.3:
                score = 0.8
                contributing.append(f"Low RT error ({residual:.3f} min)")
            elif abs_res < 0.5:
                score = 0.5
                detracting.append(f"Moderate RT error ({residual:.3f} min)")
            else:
                score = max(0.1, 1.0 - abs_res)
                detracting.append(f"High RT error ({residual:.3f} min)")

        return max(0, min(1, score)), contributing, detracting

    def _score_bayesian_uncertainty(
        self,
        std_dev: Optional[float],
        predicted_rt: Optional[float],
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score based on Bayesian prediction uncertainty.

        Args:
            std_dev: Standard deviation of prediction
            predicted_rt: Predicted retention time

        Returns:
            Tuple of (score, contributing_factors, detracting_factors)
        """
        contributing = []
        detracting = []

        if std_dev is None:
            return 0.5, [], ["Bayesian uncertainty unavailable"]

        # Relative uncertainty (as percentage of predicted RT)
        if predicted_rt and predicted_rt > 0:
            rel_uncertainty = std_dev / predicted_rt
        else:
            rel_uncertainty = std_dev / 10.0  # Assume RT ~10 min

        if rel_uncertainty < 0.02:
            score = 1.0
            contributing.append(f"Very low uncertainty ({std_dev:.3f} min)")
        elif rel_uncertainty < 0.05:
            score = 0.85
            contributing.append(f"Low uncertainty ({std_dev:.3f} min)")
        elif rel_uncertainty < 0.10:
            score = 0.7
            contributing.append(f"Moderate uncertainty ({std_dev:.3f} min)")
        elif rel_uncertainty < 0.20:
            score = 0.5
            detracting.append(f"High uncertainty ({std_dev:.3f} min)")
        else:
            score = 0.3
            detracting.append(f"Very high uncertainty ({std_dev:.3f} min)")

        return score, contributing, detracting

    def _score_chemical_validation(
        self,
        validation_results: Optional[Dict[str, Any]],
        compound_name: str,
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score based on chemical validation results.

        Args:
            validation_results: Results from chemical validation
            compound_name: Name of compound being scored

        Returns:
            Tuple of (score, contributing_factors, detracting_factors)
        """
        contributing = []
        detracting = []

        if not validation_results:
            return 0.5, [], ["Chemical validation unavailable"]

        score = 1.0
        penalty = 0.0

        # Check coefficient sign validity
        coef_validity = validation_results.get('coefficient_validity', {})
        for feature, valid in coef_validity.items():
            if not valid:
                penalty += 0.15
                detracting.append(f"Coefficient sign violation: {feature}")

        # Check O-acetylation validation
        oacetyl = validation_results.get('oacetylation', {})
        if oacetyl.get('is_invalid'):
            penalty += 0.2
            detracting.append("O-acetylation RT validation failed")

        # Check category ordering
        category_valid = validation_results.get('category_ordering_valid', True)
        if not category_valid:
            penalty += 0.15
            detracting.append("Category RT ordering violation")

        if penalty == 0:
            contributing.append("All chemical validations passed")

        score = max(0.1, score - penalty)
        return score, contributing, detracting

    def _score_cross_prefix(
        self,
        cross_prefix_results: Optional[Dict[str, Any]],
        compound_name: str,
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score based on cross-prefix consistency.

        Args:
            cross_prefix_results: Results from cross-prefix validation
            compound_name: Name of compound being scored

        Returns:
            Tuple of (score, contributing_factors, detracting_factors)
        """
        contributing = []
        detracting = []

        if not cross_prefix_results:
            return 0.5, [], ["Cross-prefix validation unavailable"]

        is_valid = cross_prefix_results.get('is_valid', True)
        violations = cross_prefix_results.get('category_violations', [])

        # Check if this compound is involved in violations
        compound_in_violation = any(
            v.get('compound_a') == compound_name or
            v.get('compound_b') == compound_name
            for v in violations
        )

        if compound_in_violation:
            score = 0.4
            detracting.append("Involved in cross-prefix RT violation")
        elif not is_valid:
            score = 0.7
            detracting.append("Cross-prefix validation has violations")
        else:
            score = 1.0
            contributing.append("Cross-prefix consistency maintained")

        return score, contributing, detracting

    def _score_modification_stack(
        self,
        modification_results: Optional[Dict[str, Any]],
        compound_name: str,
    ) -> Tuple[float, List[str], List[str]]:
        """
        Score based on modification stack validation.

        Args:
            modification_results: Results from modification validation
            compound_name: Name of compound being scored

        Returns:
            Tuple of (score, contributing_factors, detracting_factors)
        """
        contributing = []
        detracting = []

        if not modification_results:
            return 0.5, [], ["Modification validation unavailable"]

        violations = modification_results.get('rt_ordering_violations', [])

        # Check if this compound has violations
        compound_violations = [
            v for v in violations
            if v.get('compound') == compound_name
        ]

        if compound_violations:
            error_violations = [
                v for v in compound_violations
                if v.get('severity', 'error') != 'info'
            ]
            if error_violations:
                score = 0.3
                detracting.append("Modification RT ordering violation")
            else:
                score = 0.7
                detracting.append("Modification RT magnitude unusual")
        else:
            score = 1.0
            contributing.append("Modification stack valid")

        return score, contributing, detracting

    def score_compound(
        self,
        compound_name: str,
        regression_data: Optional[Dict[str, Any]] = None,
        residual_data: Optional[Dict[str, Any]] = None,
        bayesian_data: Optional[Dict[str, Any]] = None,
        chemical_validation: Optional[Dict[str, Any]] = None,
        cross_prefix_results: Optional[Dict[str, Any]] = None,
        modification_results: Optional[Dict[str, Any]] = None,
    ) -> ConfidenceScore:
        """
        Calculate confidence score for a single compound.

        Args:
            compound_name: Name of the compound
            regression_data: Regression fit information (r2, rmse, n_samples)
            residual_data: Residual information (residual, std_residual, predicted_rt)
            bayesian_data: Bayesian uncertainty (std_dev, predicted_rt)
            chemical_validation: Chemical validation results
            cross_prefix_results: Cross-prefix validation results
            modification_results: Modification validation results

        Returns:
            ConfidenceScore for the compound
        """
        component_scores = {}
        all_contributing = []
        all_detracting = []
        warnings = []

        # Score each component
        reg_data = regression_data or {}
        reg_score, reg_contrib, reg_detract = self._score_regression_fit(
            reg_data.get('r2'),
            reg_data.get('rmse'),
            reg_data.get('n_samples'),
        )
        component_scores['regression_fit'] = reg_score
        all_contributing.extend(reg_contrib)
        all_detracting.extend(reg_detract)

        res_data = residual_data or {}
        res_score, res_contrib, res_detract = self._score_residual(
            res_data.get('residual'),
            res_data.get('std_residual'),
            res_data.get('predicted_rt'),
        )
        component_scores['residual'] = res_score
        all_contributing.extend(res_contrib)
        all_detracting.extend(res_detract)

        bay_data = bayesian_data or {}
        bay_score, bay_contrib, bay_detract = self._score_bayesian_uncertainty(
            bay_data.get('std_dev'),
            bay_data.get('predicted_rt'),
        )
        component_scores['bayesian_uncertainty'] = bay_score
        all_contributing.extend(bay_contrib)
        all_detracting.extend(bay_detract)

        chem_score, chem_contrib, chem_detract = self._score_chemical_validation(
            chemical_validation,
            compound_name,
        )
        component_scores['chemical_validation'] = chem_score
        all_contributing.extend(chem_contrib)
        all_detracting.extend(chem_detract)

        cp_score, cp_contrib, cp_detract = self._score_cross_prefix(
            cross_prefix_results,
            compound_name,
        )
        component_scores['cross_prefix'] = cp_score
        all_contributing.extend(cp_contrib)
        all_detracting.extend(cp_detract)

        mod_score, mod_contrib, mod_detract = self._score_modification_stack(
            modification_results,
            compound_name,
        )
        component_scores['modification_stack'] = mod_score
        all_contributing.extend(mod_contrib)
        all_detracting.extend(mod_detract)

        # Calculate weighted overall score
        overall_score = sum(
            component_scores.get(k, 0.5) * v
            for k, v in self.weights.items()
        )

        # Classify confidence level
        confidence_level = self._classify_confidence(overall_score)

        return ConfidenceScore(
            compound_name=compound_name,
            overall_score=overall_score,
            confidence_level=confidence_level,
            component_scores=component_scores,
            contributing_factors=all_contributing,
            detracting_factors=all_detracting,
            warnings=warnings,
        )

    def score_all_compounds(
        self,
        df: pd.DataFrame,
        regression_results: Optional[Dict[str, Any]] = None,
        bayesian_results: Optional[Dict[str, Any]] = None,
        chemical_validation: Optional[Dict[str, Any]] = None,
        cross_prefix_results: Optional[Dict[str, Any]] = None,
        modification_results: Optional[Dict[str, Any]] = None,
    ) -> ConfidenceAnalysis:
        """
        Calculate confidence scores for all compounds in a DataFrame.

        Args:
            df: DataFrame with compound data
            regression_results: Regression results by prefix
            bayesian_results: Bayesian regression results
            chemical_validation: Chemical validation results
            cross_prefix_results: Cross-prefix validation results
            modification_results: Modification validation results

        Returns:
            ConfidenceAnalysis with all scores
        """
        if 'Name' not in df.columns:
            return ConfidenceAnalysis(
                is_valid=False,
                compounds_scored=0,
                high_confidence_count=0,
                medium_confidence_count=0,
                low_confidence_count=0,
                very_low_confidence_count=0,
                average_score=0.0,
                scores=[],
                warnings=["DataFrame missing 'Name' column"],
            )

        if df.empty:
            return ConfidenceAnalysis(
                is_valid=True,
                compounds_scored=0,
                high_confidence_count=0,
                medium_confidence_count=0,
                low_confidence_count=0,
                very_low_confidence_count=0,
                average_score=0.0,
                scores=[],
                statistics={},
            )

        scores = []
        high_count = 0
        medium_count = 0
        low_count = 0
        very_low_count = 0

        # Build lookup for compound-specific data
        residual_lookup = self._build_residual_lookup(df, regression_results)
        bayesian_lookup = self._build_bayesian_lookup(bayesian_results)

        for _, row in df.iterrows():
            compound_name = row['Name']

            # Get compound-specific data
            residual_data = residual_lookup.get(compound_name, {})
            bayesian_data = bayesian_lookup.get(compound_name, {})

            # Get regression data (from prefix group)
            reg_data = self._get_regression_data(
                compound_name, row.get('prefix'), regression_results
            )

            score = self.score_compound(
                compound_name=compound_name,
                regression_data=reg_data,
                residual_data=residual_data,
                bayesian_data=bayesian_data,
                chemical_validation=chemical_validation,
                cross_prefix_results=cross_prefix_results,
                modification_results=modification_results,
            )
            scores.append(score)

            # Count confidence levels
            if score.confidence_level == ConfidenceLevel.HIGH:
                high_count += 1
            elif score.confidence_level == ConfidenceLevel.MEDIUM:
                medium_count += 1
            elif score.confidence_level == ConfidenceLevel.LOW:
                low_count += 1
            else:
                very_low_count += 1

        # Calculate statistics
        all_scores = [s.overall_score for s in scores]
        avg_score = float(np.mean(all_scores)) if all_scores else 0.0

        statistics = {
            'total_compounds': len(scores),
            'average_score': avg_score,
            'min_score': float(min(all_scores)) if all_scores else 0.0,
            'max_score': float(max(all_scores)) if all_scores else 0.0,
            'std_score': float(np.std(all_scores)) if all_scores else 0.0,
            'high_confidence_rate': high_count / len(scores) if scores else 0.0,
            'medium_confidence_rate': medium_count / len(scores) if scores else 0.0,
            'low_confidence_rate': low_count / len(scores) if scores else 0.0,
            'very_low_confidence_rate': very_low_count / len(scores) if scores else 0.0,
        }

        # Determine validity (majority should be medium or higher)
        acceptable_count = high_count + medium_count
        is_valid = acceptable_count >= len(scores) * 0.5 if scores else True

        return ConfidenceAnalysis(
            is_valid=is_valid,
            compounds_scored=len(scores),
            high_confidence_count=high_count,
            medium_confidence_count=medium_count,
            low_confidence_count=low_count,
            very_low_confidence_count=very_low_count,
            average_score=avg_score,
            scores=scores,
            statistics=statistics,
        )

    def _build_residual_lookup(
        self,
        df: pd.DataFrame,
        regression_results: Optional[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """Build lookup for residual data by compound name."""
        lookup = {}

        # Check if residual columns exist in DataFrame
        if 'residual' in df.columns:
            for _, row in df.iterrows():
                lookup[row['Name']] = {
                    'residual': row.get('residual'),
                    'std_residual': row.get('std_residual'),
                    'predicted_rt': row.get('predicted_rt'),
                }

        # Also check regression_results for outlier information
        if regression_results:
            for prefix_data in regression_results.get('prefix_results', {}).values():
                if not isinstance(prefix_data, dict):
                    continue
                for outlier in prefix_data.get('outliers', []):
                    if isinstance(outlier, dict):
                        name = outlier.get('name', outlier.get('compound'))
                        if name and name not in lookup:
                            lookup[name] = {
                                'residual': outlier.get('residual'),
                                'std_residual': outlier.get('std_residual'),
                            }

        return lookup

    def _build_bayesian_lookup(
        self,
        bayesian_results: Optional[Dict[str, Any]],
    ) -> Dict[str, Dict[str, Any]]:
        """Build lookup for Bayesian uncertainty by compound name."""
        lookup = {}

        if not bayesian_results:
            return lookup

        # Handle training predictions
        training = bayesian_results.get('training_predictions', {})
        if isinstance(training, dict):
            names = training.get('names', [])
            std_devs = training.get('std_deviation', [])
            point_estimates = training.get('point_estimate', [])

            for i, name in enumerate(names):
                lookup[name] = {
                    'std_dev': std_devs[i] if i < len(std_devs) else None,
                    'predicted_rt': point_estimates[i] if i < len(point_estimates) else None,
                }

        return lookup

    def _get_regression_data(
        self,
        compound_name: str,
        prefix: Optional[str],
        regression_results: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Get regression data for a compound from its prefix group."""
        if not regression_results or not prefix:
            return {}

        prefix_results = regression_results.get('prefix_results', {})
        prefix_data = prefix_results.get(prefix, {})

        if not isinstance(prefix_data, dict):
            return {}

        return {
            'r2': prefix_data.get('r2'),
            'rmse': prefix_data.get('rmse'),
            'n_samples': prefix_data.get('n_samples'),
        }

    def get_confidence_thresholds(self) -> Dict[str, float]:
        """Get current confidence thresholds."""
        return {
            'high': self.high_threshold,
            'medium': self.medium_threshold,
            'low': self.low_threshold,
        }

    def get_weights(self) -> Dict[str, float]:
        """Get current scoring weights."""
        return self.weights.copy()
