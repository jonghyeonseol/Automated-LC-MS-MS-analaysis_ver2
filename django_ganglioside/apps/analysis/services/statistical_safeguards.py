"""
Statistical Safeguards for Regression Analysis

This module addresses critical statistical vulnerabilities:
- C1: Sample-size-aware R² thresholds
- C4: Scientifically justified threshold selection
- C6: Extrapolation detection and warning
- C7: Cross-validation meaningfulness assessment
- H1: Multicollinearity detection
- H2: Small-sample outlier detection validity
- H5: Heteroscedasticity testing

The goal is HONEST uncertainty quantification, not pretending
to have confidence that the data doesn't support.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ConfidenceLevel(Enum):
    """Honest confidence levels for regression results."""
    UNRELIABLE = "unreliable"       # n < 5 or n ≤ p
    LOW = "low"                     # 5 ≤ n < 10
    MODERATE = "moderate"           # 10 ≤ n < 20
    HIGH = "high"                   # n ≥ 20
    VALIDATED = "validated"         # External validation passed


@dataclass
class RegressionDiagnostics:
    """Complete diagnostics for a regression model."""

    # Sample size assessment
    n_samples: int
    n_features: int
    degrees_of_freedom: int
    sample_feature_ratio: float
    confidence_level: ConfidenceLevel

    # Threshold assessment
    r2_threshold_used: float
    r2_threshold_recommended: float
    threshold_justification: str

    # Cross-validation assessment
    cv_meaningful: bool
    cv_method: str
    cv_warning: Optional[str] = None

    # Extrapolation assessment
    extrapolation_detected: bool = False
    extrapolation_features: List[str] = field(default_factory=list)
    extrapolation_severity: str = "none"  # none, mild, severe

    # Heteroscedasticity
    heteroscedasticity_tested: bool = False
    heteroscedasticity_detected: bool = False
    heteroscedasticity_p_value: Optional[float] = None

    # Multicollinearity
    max_vif: Optional[float] = None
    vif_warning: Optional[str] = None

    # Outlier detection validity
    outlier_detection_valid: bool = True
    outlier_warning: Optional[str] = None

    # Warnings and recommendations
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sample_assessment': {
                'n_samples': self.n_samples,
                'n_features': self.n_features,
                'degrees_of_freedom': self.degrees_of_freedom,
                'sample_feature_ratio': round(self.sample_feature_ratio, 2),
                'confidence_level': self.confidence_level.value
            },
            'threshold_assessment': {
                'r2_threshold_used': self.r2_threshold_used,
                'r2_threshold_recommended': self.r2_threshold_recommended,
                'justification': self.threshold_justification
            },
            'cv_assessment': {
                'meaningful': self.cv_meaningful,
                'method': self.cv_method,
                'warning': self.cv_warning
            },
            'extrapolation': {
                'detected': self.extrapolation_detected,
                'features': self.extrapolation_features,
                'severity': self.extrapolation_severity
            },
            'heteroscedasticity': {
                'tested': self.heteroscedasticity_tested,
                'detected': self.heteroscedasticity_detected,
                'p_value': self.heteroscedasticity_p_value
            },
            'multicollinearity': {
                'max_vif': self.max_vif,
                'warning': self.vif_warning
            },
            'outlier_detection': {
                'valid': self.outlier_detection_valid,
                'warning': self.outlier_warning
            },
            'warnings': self.warnings,
            'recommendations': self.recommendations
        }


class StatisticalSafeguards:
    """
    Statistical safeguards for honest uncertainty quantification.

    This class provides sample-size-aware thresholds and diagnostics
    to prevent over-confidence in small-sample regression results.
    """

    # Sample size requirements for different confidence levels
    SAMPLE_THRESHOLDS = {
        ConfidenceLevel.UNRELIABLE: (0, 5),     # [0, 5)
        ConfidenceLevel.LOW: (5, 10),           # [5, 10)
        ConfidenceLevel.MODERATE: (10, 20),     # [10, 20)
        ConfidenceLevel.HIGH: (20, float('inf'))  # [20, ∞)
    }

    # Sample-size adjusted R² thresholds
    # Based on: smaller samples need LOWER thresholds (more forgiving)
    # because achieving high R² with small n is easy via overfitting
    R2_THRESHOLDS_BY_CONFIDENCE = {
        ConfidenceLevel.UNRELIABLE: 0.50,  # Low bar, results unreliable anyway
        ConfidenceLevel.LOW: 0.60,         # Slightly higher
        ConfidenceLevel.MODERATE: 0.70,    # Standard threshold
        ConfidenceLevel.HIGH: 0.75,        # Can expect better fit with more data
        ConfidenceLevel.VALIDATED: 0.80    # External validation allows higher bar
    }

    # Cross-validation minimum samples per fold
    MIN_SAMPLES_PER_FOLD = 3

    # VIF threshold for multicollinearity
    VIF_THRESHOLD = 5.0  # Common threshold; 10.0 is more lenient

    # Heteroscedasticity test significance level
    HETEROSCEDASTICITY_ALPHA = 0.05

    def __init__(
        self,
        strict_mode: bool = False,
        custom_thresholds: Optional[Dict[ConfidenceLevel, float]] = None
    ):
        """
        Initialize safeguards.

        Args:
            strict_mode: If True, unreliable results raise errors
            custom_thresholds: Override default R² thresholds
        """
        self.strict_mode = strict_mode
        self.r2_thresholds = {**self.R2_THRESHOLDS_BY_CONFIDENCE}
        if custom_thresholds:
            self.r2_thresholds.update(custom_thresholds)

    def assess_sample_size(
        self,
        n_samples: int,
        n_features: int
    ) -> Tuple[ConfidenceLevel, str]:
        """
        Assess sample size adequacy for regression.

        Returns:
            Tuple of (confidence_level, justification)
        """
        df = n_samples - n_features - 1
        ratio = n_samples / n_features if n_features > 0 else float('inf')

        # Check for exactly determined or underdetermined system
        if n_samples <= n_features:
            return (
                ConfidenceLevel.UNRELIABLE,
                f"System is {'exactly' if n_samples == n_features else 'under'}-determined "
                f"(n={n_samples}, p={n_features}). No degrees of freedom for inference."
            )

        # Check degrees of freedom
        if df <= 0:
            return (
                ConfidenceLevel.UNRELIABLE,
                f"Zero or negative degrees of freedom (df={df}). "
                f"Results are mathematically forced, not statistically meaningful."
            )

        # Assess by sample size
        for level, (min_n, max_n) in self.SAMPLE_THRESHOLDS.items():
            if min_n <= n_samples < max_n:
                return (
                    level,
                    f"n={n_samples} samples with {n_features} features. "
                    f"Sample/feature ratio: {ratio:.1f}. "
                    f"Confidence: {level.value}."
                )

        return (ConfidenceLevel.HIGH, f"n={n_samples}, adequate sample size.")

    def get_r2_threshold(
        self,
        n_samples: int,
        n_features: int,
        requested_threshold: float = 0.70
    ) -> Tuple[float, str]:
        """
        Get sample-size-appropriate R² threshold.

        Args:
            n_samples: Number of samples
            n_features: Number of features
            requested_threshold: User-requested threshold

        Returns:
            Tuple of (adjusted_threshold, justification)
        """
        confidence, _ = self.assess_sample_size(n_samples, n_features)
        recommended = self.r2_thresholds[confidence]

        if confidence == ConfidenceLevel.UNRELIABLE:
            justification = (
                f"Sample size too small for reliable inference. "
                f"Using R²≥{recommended:.2f} but results should not be trusted."
            )
            return (recommended, justification)

        if requested_threshold > recommended:
            justification = (
                f"Requested R²≥{requested_threshold:.2f} is too high for n={n_samples}. "
                f"Using R²≥{recommended:.2f} based on sample size."
            )
            return (recommended, justification)

        if requested_threshold < recommended - 0.15:
            justification = (
                f"Requested R²≥{requested_threshold:.2f} is below recommended "
                f"{recommended:.2f} for n={n_samples}. Using requested threshold."
            )
            return (requested_threshold, justification)

        return (
            requested_threshold,
            f"Using R²≥{requested_threshold:.2f} (recommended: {recommended:.2f})"
        )

    def assess_cv_meaningfulness(
        self,
        n_samples: int,
        n_features: int,
        cv_folds: int = 5
    ) -> Tuple[bool, str, str]:
        """
        Assess whether cross-validation is meaningful.

        Returns:
            Tuple of (is_meaningful, cv_method, warning_if_any)
        """
        samples_per_fold = n_samples / cv_folds

        if n_samples <= n_features:
            return (
                False,
                "none",
                f"CV impossible: n={n_samples} ≤ p={n_features}. "
                f"Each fold would have negative degrees of freedom."
            )

        if n_samples < 5:
            return (
                False,
                "none",
                f"CV not meaningful: n={n_samples} too small. "
                f"Each fold would train on 1-2 samples."
            )

        if samples_per_fold < self.MIN_SAMPLES_PER_FOLD:
            # Use LOOCV but warn about instability
            return (
                True,
                "leave-one-out",
                f"LOOCV used but unstable with n={n_samples}. "
                f"CV estimates have high variance."
            )

        if n_samples < 10:
            return (
                True,
                "leave-one-out",
                f"LOOCV used. Results have limited reliability with n={n_samples}."
            )

        if samples_per_fold < 5:
            adjusted_folds = max(2, n_samples // 5)
            return (
                True,
                f"{adjusted_folds}-fold",
                f"Reduced to {adjusted_folds}-fold CV due to sample size."
            )

        return (True, f"{cv_folds}-fold", None)

    def detect_extrapolation(
        self,
        X_train: np.ndarray,
        X_predict: np.ndarray,
        feature_names: List[str],
        tolerance: float = 0.1
    ) -> Tuple[bool, List[str], str]:
        """
        Detect if predictions are extrapolations beyond training range.

        Args:
            X_train: Training feature matrix (n_train, p)
            X_predict: Prediction feature matrix (n_predict, p)
            feature_names: Names of features
            tolerance: Fraction of range allowed beyond training bounds

        Returns:
            Tuple of (extrapolation_detected, affected_features, severity)
        """
        if X_train.ndim == 1:
            X_train = X_train.reshape(-1, 1)
        if X_predict.ndim == 1:
            X_predict = X_predict.reshape(-1, 1)

        extrapolation_features = []
        max_severity = 0

        for i, name in enumerate(feature_names):
            train_min = X_train[:, i].min()
            train_max = X_train[:, i].max()
            train_range = train_max - train_min

            if train_range == 0:
                continue

            # Calculate allowed bounds
            allowed_min = train_min - tolerance * train_range
            allowed_max = train_max + tolerance * train_range

            pred_min = X_predict[:, i].min()
            pred_max = X_predict[:, i].max()

            if pred_min < allowed_min or pred_max > allowed_max:
                extrapolation_features.append(name)

                # Calculate severity
                if pred_min < allowed_min:
                    severity = (allowed_min - pred_min) / train_range
                    max_severity = max(max_severity, severity)
                if pred_max > allowed_max:
                    severity = (pred_max - allowed_max) / train_range
                    max_severity = max(max_severity, severity)

        if not extrapolation_features:
            return (False, [], "none")

        if max_severity < 0.25:
            return (True, extrapolation_features, "mild")
        elif max_severity < 0.5:
            return (True, extrapolation_features, "moderate")
        else:
            return (True, extrapolation_features, "severe")

    def test_heteroscedasticity(
        self,
        X: np.ndarray,
        residuals: np.ndarray
    ) -> Tuple[bool, Optional[float]]:
        """
        Test for heteroscedasticity using Breusch-Pagan test.

        Returns:
            Tuple of (heteroscedasticity_detected, p_value)
        """
        n = len(residuals)

        if n < 10:
            logger.warning(
                f"Sample size {n} too small for reliable heteroscedasticity test"
            )
            return (False, None)

        try:
            # Breusch-Pagan test
            # H0: homoscedasticity (constant variance)
            # H1: heteroscedasticity (variance depends on X)

            # Square residuals
            residuals_sq = residuals ** 2

            # Regress squared residuals on X
            if X.ndim == 1:
                X = X.reshape(-1, 1)

            # Add constant for regression
            X_const = np.column_stack([np.ones(n), X])

            # OLS for squared residuals
            try:
                beta = np.linalg.lstsq(X_const, residuals_sq, rcond=None)[0]
                fitted = X_const @ beta
                ss_reg = np.sum((fitted - residuals_sq.mean()) ** 2)
                ss_tot = np.sum((residuals_sq - residuals_sq.mean()) ** 2)
                r2 = ss_reg / ss_tot if ss_tot > 0 else 0

                # Test statistic
                lm_stat = n * r2
                p_value = 1 - stats.chi2.cdf(lm_stat, X.shape[1])

                return (p_value < self.HETEROSCEDASTICITY_ALPHA, p_value)

            except np.linalg.LinAlgError:
                return (False, None)

        except Exception as e:
            logger.warning(f"Heteroscedasticity test failed: {e}")
            return (False, None)

    def calculate_vif(self, X: np.ndarray) -> Optional[np.ndarray]:
        """
        Calculate Variance Inflation Factors for multicollinearity detection.

        Returns:
            Array of VIF values for each feature, or None if calculation fails
        """
        if X.ndim == 1 or X.shape[1] < 2:
            return None

        n_features = X.shape[1]
        vifs = np.zeros(n_features)

        try:
            for i in range(n_features):
                # Regress feature i on all other features
                y = X[:, i]
                X_other = np.delete(X, i, axis=1)

                # Add constant
                X_const = np.column_stack([np.ones(len(y)), X_other])

                # Calculate R²
                try:
                    beta = np.linalg.lstsq(X_const, y, rcond=None)[0]
                    y_pred = X_const @ beta
                    ss_res = np.sum((y - y_pred) ** 2)
                    ss_tot = np.sum((y - y.mean()) ** 2)

                    if ss_tot == 0:
                        vifs[i] = float('inf')
                    else:
                        r2 = 1 - ss_res / ss_tot
                        vifs[i] = 1 / (1 - r2) if r2 < 1 else float('inf')

                except np.linalg.LinAlgError:
                    vifs[i] = float('inf')

            return vifs

        except Exception as e:
            logger.warning(f"VIF calculation failed: {e}")
            return None

    def assess_outlier_detection_validity(
        self,
        n_samples: int,
        outlier_threshold: float = 2.5
    ) -> Tuple[bool, Optional[str]]:
        """
        Assess whether outlier detection is statistically valid.

        Returns:
            Tuple of (is_valid, warning_if_invalid)
        """
        if n_samples < 5:
            return (
                False,
                f"n={n_samples} too small for outlier detection. "
                f"Cannot estimate standard deviation reliably."
            )

        if n_samples < 10:
            expected_outliers = n_samples * (1 - stats.norm.cdf(outlier_threshold))
            if expected_outliers < 0.1:
                return (
                    True,
                    f"n={n_samples}: outlier detection may flag legitimate variation. "
                    f"Consider relaxing threshold or adding more samples."
                )

        if n_samples < 20:
            return (
                True,
                f"n={n_samples}: outlier detection has limited power. "
                f"Cannot reliably distinguish outliers from natural variation."
            )

        return (True, None)

    def run_full_diagnostics(
        self,
        X: np.ndarray,
        y: np.ndarray,
        residuals: np.ndarray,
        feature_names: List[str],
        r2_threshold: float = 0.70,
        outlier_threshold: float = 2.5,
        X_predict: Optional[np.ndarray] = None
    ) -> RegressionDiagnostics:
        """
        Run complete diagnostic assessment.

        Args:
            X: Training feature matrix
            y: Target values
            residuals: Model residuals
            feature_names: Names of features
            r2_threshold: User-requested R² threshold
            outlier_threshold: Outlier detection threshold
            X_predict: Optional prediction feature matrix for extrapolation check

        Returns:
            Complete RegressionDiagnostics object
        """
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        n_samples, n_features = X.shape
        df = n_samples - n_features - 1
        ratio = n_samples / n_features if n_features > 0 else float('inf')

        # Sample size assessment
        confidence, confidence_just = self.assess_sample_size(n_samples, n_features)

        # R² threshold
        r2_rec, r2_just = self.get_r2_threshold(n_samples, n_features, r2_threshold)

        # CV meaningfulness
        cv_meaningful, cv_method, cv_warning = self.assess_cv_meaningfulness(
            n_samples, n_features
        )

        # Extrapolation detection
        if X_predict is not None:
            extrap_detected, extrap_features, extrap_severity = self.detect_extrapolation(
                X, X_predict, feature_names
            )
        else:
            extrap_detected, extrap_features, extrap_severity = False, [], "none"

        # Heteroscedasticity
        hetero_detected, hetero_pval = self.test_heteroscedasticity(X, residuals)

        # VIF
        vifs = self.calculate_vif(X)
        max_vif = float(np.max(vifs)) if vifs is not None else None
        vif_warning = None
        if max_vif and max_vif > self.VIF_THRESHOLD:
            vif_warning = f"High multicollinearity detected (max VIF={max_vif:.1f} > {self.VIF_THRESHOLD})"

        # Outlier detection validity
        outlier_valid, outlier_warning = self.assess_outlier_detection_validity(
            n_samples, outlier_threshold
        )

        # Compile warnings
        warnings = []
        recommendations = []

        if confidence == ConfidenceLevel.UNRELIABLE:
            warnings.append(
                f"UNRELIABLE: n={n_samples} is insufficient for {n_features} features. "
                f"Results should not be used for validation decisions."
            )
            recommendations.append(
                f"Add at least {10 - n_samples} more anchor compounds for this prefix."
            )

        if cv_warning:
            warnings.append(f"Cross-validation: {cv_warning}")

        if extrap_detected:
            warnings.append(
                f"Extrapolation ({extrap_severity}): predictions extend beyond training range "
                f"for features: {extrap_features}"
            )
            if extrap_severity in ['moderate', 'severe']:
                recommendations.append(
                    "Add anchor compounds covering the extrapolation range."
                )

        if hetero_detected:
            warnings.append(
                f"Heteroscedasticity detected (p={hetero_pval:.3f}). "
                f"Confidence intervals may be invalid."
            )
            recommendations.append(
                "Consider weighted regression or robust methods."
            )

        if vif_warning:
            warnings.append(vif_warning)
            recommendations.append(
                "Consider removing correlated features or using PCA."
            )

        if outlier_warning:
            warnings.append(f"Outlier detection: {outlier_warning}")

        return RegressionDiagnostics(
            n_samples=n_samples,
            n_features=n_features,
            degrees_of_freedom=df,
            sample_feature_ratio=ratio,
            confidence_level=confidence,
            r2_threshold_used=r2_threshold,
            r2_threshold_recommended=r2_rec,
            threshold_justification=r2_just,
            cv_meaningful=cv_meaningful,
            cv_method=cv_method,
            cv_warning=cv_warning,
            extrapolation_detected=extrap_detected,
            extrapolation_features=extrap_features,
            extrapolation_severity=extrap_severity,
            heteroscedasticity_tested=True,
            heteroscedasticity_detected=hetero_detected,
            heteroscedasticity_p_value=hetero_pval,
            max_vif=max_vif,
            vif_warning=vif_warning,
            outlier_detection_valid=outlier_valid,
            outlier_warning=outlier_warning,
            warnings=warnings,
            recommendations=recommendations
        )


# Convenience functions
def get_adjusted_r2_threshold(
    n_samples: int,
    n_features: int,
    requested: float = 0.70
) -> float:
    """Get sample-size-adjusted R² threshold."""
    safeguards = StatisticalSafeguards()
    threshold, _ = safeguards.get_r2_threshold(n_samples, n_features, requested)
    return threshold


def is_extrapolation(
    X_train: np.ndarray,
    X_predict: np.ndarray,
    feature_names: List[str]
) -> bool:
    """Check if prediction involves extrapolation."""
    safeguards = StatisticalSafeguards()
    detected, _, _ = safeguards.detect_extrapolation(X_train, X_predict, feature_names)
    return detected


def get_confidence_level(n_samples: int, n_features: int) -> str:
    """Get confidence level string for sample size."""
    safeguards = StatisticalSafeguards()
    level, _ = safeguards.assess_sample_size(n_samples, n_features)
    return level.value
