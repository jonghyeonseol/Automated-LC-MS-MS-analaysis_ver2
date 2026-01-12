"""
Bayesian Ridge Regression for RT Prediction with Uncertainty Quantification

This module provides Bayesian Ridge regression for retention time (RT) prediction
with full uncertainty quantification, including per-prediction confidence intervals.

Key advantages over standard Ridge/RidgeCV:
- Automatic regularization learning (no alpha grid search needed)
- Per-prediction uncertainty estimates (standard deviation for each prediction)
- More robust to small sample sizes (Bayesian shrinkage)
- Interpretable confidence intervals (95%, 99%)

The Bayesian Ridge model places Gamma priors on the precision parameters:
- alpha: Precision of the noise (inverse of noise variance)
- lambda: Precision of the weights (inverse of weight variance)

These are learned from data, providing automatic regularization that adapts
to the complexity of each prefix group.

Author: LC-MS/MS Analysis Platform
Version: 3.0
"""

import numpy as np
from sklearn.linear_model import BayesianRidge
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_squared_error
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """
    Container for predictions with uncertainty quantification.

    Attributes:
        point_estimate: Mean prediction values (most likely RT)
        std_deviation: Standard deviation per prediction (uncertainty measure)
        ci_lower_95: 95% confidence interval lower bound
        ci_upper_95: 95% confidence interval upper bound
        ci_lower_99: 99% confidence interval lower bound
        ci_upper_99: 99% confidence interval upper bound

    The confidence intervals are computed as:
        CI_95 = point_estimate +/- 1.96 * std_deviation
        CI_99 = point_estimate +/- 2.576 * std_deviation

    Interpretation:
        - 95% CI: We expect the true RT to fall within this range 95% of the time
        - 99% CI: More conservative range for high-confidence decisions
        - Large std_deviation indicates uncertain predictions (e.g., extrapolation)
    """
    point_estimate: np.ndarray
    std_deviation: np.ndarray
    ci_lower_95: np.ndarray
    ci_upper_95: np.ndarray
    ci_lower_99: np.ndarray
    ci_upper_99: np.ndarray

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            'point_estimate': self.point_estimate.tolist(),
            'std_deviation': self.std_deviation.tolist(),
            'ci_lower_95': self.ci_lower_95.tolist(),
            'ci_upper_95': self.ci_upper_95.tolist(),
            'ci_lower_99': self.ci_lower_99.tolist(),
            'ci_upper_99': self.ci_upper_99.tolist(),
        }

    def get_prediction_for_index(self, idx: int) -> Dict[str, float]:
        """Get prediction details for a single compound by index."""
        return {
            'point_estimate': float(self.point_estimate[idx]),
            'std_deviation': float(self.std_deviation[idx]),
            'ci_lower_95': float(self.ci_lower_95[idx]),
            'ci_upper_95': float(self.ci_upper_95[idx]),
            'ci_lower_99': float(self.ci_lower_99[idx]),
            'ci_upper_99': float(self.ci_upper_99[idx]),
        }

    @property
    def mean_uncertainty(self) -> float:
        """Average prediction uncertainty across all compounds."""
        return float(np.mean(self.std_deviation))

    @property
    def max_uncertainty(self) -> float:
        """Maximum prediction uncertainty (worst case)."""
        return float(np.max(self.std_deviation))


@dataclass
class RegressionFitResult:
    """
    Container for comprehensive regression fitting results.

    Attributes:
        success: Whether the regression met quality thresholds
        r2: Coefficient of determination (R-squared)
        adjusted_r2: Adjusted R-squared (penalized for number of features)
        rmse: Root mean squared error
        alpha_learned: Learned noise precision (higher = less noise assumed)
        lambda_learned: Learned weight precision (higher = stronger regularization)
        coefficients: Dictionary mapping feature names to coefficient values
        intercept: Regression intercept term
        training_predictions: PredictionResult for training data
        residuals: Raw residuals (observed - predicted)
        standardized_residuals: Residuals divided by residual standard deviation
        equation: Human-readable regression equation string
        warnings: List of any warnings generated during fitting
        n_samples: Number of samples used for fitting
        n_features: Number of features used
        cv_score: Cross-validation score if available
    """
    success: bool
    r2: float
    adjusted_r2: Optional[float]
    rmse: float
    alpha_learned: float
    lambda_learned: float
    coefficients: Dict[str, float]
    intercept: float
    training_predictions: PredictionResult
    residuals: np.ndarray
    standardized_residuals: np.ndarray
    equation: str
    warnings: List[str]
    n_samples: int
    n_features: int
    cv_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            'success': bool(self.success),
            'r2': float(self.r2),
            'adjusted_r2': float(self.adjusted_r2) if self.adjusted_r2 is not None else None,
            'rmse': float(self.rmse),
            'alpha_learned': float(self.alpha_learned),
            'lambda_learned': float(self.lambda_learned),
            'coefficients': {k: float(v) for k, v in self.coefficients.items()},
            'intercept': float(self.intercept),
            'training_predictions': self.training_predictions.to_dict(),
            'residuals': self.residuals.tolist(),
            'standardized_residuals': self.standardized_residuals.tolist(),
            'equation': self.equation,
            'warnings': self.warnings,
            'n_samples': int(self.n_samples),
            'n_features': int(self.n_features),
            'cv_score': float(self.cv_score) if self.cv_score is not None else None,
        }

    @property
    def is_overfitting_risk(self) -> bool:
        """Check if there's risk of overfitting based on metrics."""
        # Suspiciously high R² with small sample
        if self.r2 > 0.99 and self.n_samples < 10:
            return True
        # Too many features relative to samples
        if self.n_features >= self.n_samples - 2:
            return True
        # Large gap between R² and adjusted R²
        if self.adjusted_r2 is not None:
            if self.r2 - self.adjusted_r2 > 0.1:
                return True
        return False


class BayesianRTPredictor:
    """
    Bayesian Ridge regression for RT prediction with full uncertainty quantification.

    This class wraps scikit-learn's BayesianRidge model and adds:
    - Automatic feature scaling for numerical stability
    - Comprehensive diagnostics and warnings
    - Easy-to-use prediction uncertainty interface
    - Integration with LC-MS/MS analysis workflow

    Bayesian Ridge Regression Model:
        y = X @ w + intercept + noise

        Where:
        - w ~ N(0, lambda^-1 * I)  [weight prior]
        - noise ~ N(0, alpha^-1)    [noise model]

        The precision parameters alpha and lambda are learned from data
        using evidence maximization (type-II maximum likelihood).

    Example Usage:
        >>> predictor = BayesianRTPredictor(r2_threshold=0.70)
        >>> result = predictor.fit(X_train, y_train, ['Log P', 'a_component'])
        >>> if result.success:
        ...     predictions = predictor.predict_with_uncertainty(X_test)
        ...     print(f"Predicted RT: {predictions.point_estimate[0]:.2f}")
        ...     print(f"95% CI: [{predictions.ci_lower_95[0]:.2f}, {predictions.ci_upper_95[0]:.2f}]")
    """

    def __init__(
        self,
        alpha_1: float = 1e-6,
        alpha_2: float = 1e-6,
        lambda_1: float = 1e-6,
        lambda_2: float = 1e-6,
        r2_threshold: float = 0.70,
        min_samples: int = 3,
        max_iter: int = 300,
        tol: float = 1e-6
    ):
        """
        Initialize Bayesian RT Predictor.

        Args:
            alpha_1: Shape parameter for Gamma prior on noise precision (alpha).
                     Small values (1e-6) give non-informative priors.
            alpha_2: Rate parameter for Gamma prior on noise precision.
            lambda_1: Shape parameter for Gamma prior on weight precision (lambda).
            lambda_2: Rate parameter for Gamma prior on weight precision.
            r2_threshold: Minimum R² for regression to be considered successful.
                          Recommended: 0.70-0.85 for LC-MS data.
            min_samples: Minimum number of samples required for fitting.
            max_iter: Maximum number of iterations for evidence maximization.
            tol: Convergence tolerance for evidence maximization.

        Note:
            Small values for hyperparameters (1e-6) give non-informative priors,
            letting the data determine the regularization strength. This is
            recommended for most use cases.
        """
        self.alpha_1 = alpha_1
        self.alpha_2 = alpha_2
        self.lambda_1 = lambda_1
        self.lambda_2 = lambda_2
        self.r2_threshold = r2_threshold
        self.min_samples = min_samples
        self.max_iter = max_iter
        self.tol = tol

        # Model components (set during fit)
        self.model: Optional[BayesianRidge] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names_: Optional[List[str]] = None
        self._is_fitted: bool = False

        logger.debug(
            f"BayesianRTPredictor initialized: r2_threshold={r2_threshold}, "
            f"min_samples={min_samples}"
        )

    def _create_model(self) -> BayesianRidge:
        """Create a fresh BayesianRidge model instance."""
        return BayesianRidge(
            alpha_1=self.alpha_1,
            alpha_2=self.alpha_2,
            lambda_1=self.lambda_1,
            lambda_2=self.lambda_2,
            compute_score=True,
            fit_intercept=True,
            max_iter=self.max_iter,
            tol=self.tol
        )

    def _create_prediction_result(
        self,
        y_pred: np.ndarray,
        y_std: np.ndarray
    ) -> PredictionResult:
        """Create PredictionResult with confidence intervals."""
        return PredictionResult(
            point_estimate=y_pred,
            std_deviation=y_std,
            ci_lower_95=y_pred - 1.96 * y_std,
            ci_upper_95=y_pred + 1.96 * y_std,
            ci_lower_99=y_pred - 2.576 * y_std,
            ci_upper_99=y_pred + 2.576 * y_std
        )

    def _create_failure_result(self, reason: str) -> RegressionFitResult:
        """Create a failure result with given reason."""
        empty_pred = PredictionResult(
            point_estimate=np.array([]),
            std_deviation=np.array([]),
            ci_lower_95=np.array([]),
            ci_upper_95=np.array([]),
            ci_lower_99=np.array([]),
            ci_upper_99=np.array([])
        )
        return RegressionFitResult(
            success=False,
            r2=0.0,
            adjusted_r2=None,
            rmse=float('inf'),
            alpha_learned=0.0,
            lambda_learned=0.0,
            coefficients={},
            intercept=0.0,
            training_predictions=empty_pred,
            residuals=np.array([]),
            standardized_residuals=np.array([]),
            equation='',
            warnings=[reason],
            n_samples=0,
            n_features=0
        )

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str]
    ) -> RegressionFitResult:
        """
        Fit Bayesian Ridge model with uncertainty quantification.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
               Features should include Log P, and optionally a_component, b_component.
            y: Target RT values of shape (n_samples,).
            feature_names: List of feature names for interpretability.
                           Must match the number of columns in X.

        Returns:
            RegressionFitResult containing:
            - success: Whether R² meets threshold
            - Learned parameters (alpha, lambda, coefficients)
            - Training predictions with uncertainty
            - Diagnostic metrics and warnings

        Raises:
            ValueError: If X and y have incompatible shapes or feature_names mismatch.
        """
        # Input validation
        X = np.asarray(X)
        y = np.asarray(y)

        if X.ndim == 1:
            X = X.reshape(-1, 1)

        n_samples, n_features = X.shape

        if len(y) != n_samples:
            return self._create_failure_result(
                f"Shape mismatch: X has {n_samples} samples, y has {len(y)}"
            )

        if len(feature_names) != n_features:
            return self._create_failure_result(
                f"Feature names count ({len(feature_names)}) doesn't match "
                f"feature count ({n_features})"
            )

        # Check minimum samples
        if n_samples < self.min_samples:
            return self._create_failure_result(
                f"Insufficient samples: {n_samples} < {self.min_samples} minimum"
            )

        self.feature_names_ = feature_names
        warnings = []

        logger.info(
            f"Fitting BayesianRidge: {n_samples} samples, {n_features} features "
            f"({', '.join(feature_names)})"
        )

        # Feature scaling for numerical stability
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Check for zero variance features after scaling
        feature_vars = np.var(X_scaled, axis=0)
        zero_var_features = [
            feature_names[i] for i, v in enumerate(feature_vars)
            if v < 1e-10
        ]
        if zero_var_features:
            warnings.append(
                f"Near-zero variance features detected: {zero_var_features}. "
                "Consider removing these features."
            )

        # Fit Bayesian Ridge model
        self.model = self._create_model()

        try:
            self.model.fit(X_scaled, y)
        except Exception as e:
            logger.error(f"BayesianRidge fitting failed: {e}")
            return self._create_failure_result(f"Model fitting failed: {str(e)}")

        self._is_fitted = True

        # Get predictions with uncertainty for training data
        y_pred, y_std = self.model.predict(X_scaled, return_std=True)

        # Calculate metrics
        residuals = y - y_pred
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        r2 = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0.0
        rmse = np.sqrt(mean_squared_error(y, y_pred))

        # Adjusted R² (penalizes for number of features)
        adjusted_r2 = None
        if n_samples > n_features + 1:
            adjusted_r2 = 1 - (1 - r2) * (n_samples - 1) / (n_samples - n_features - 1)
        else:
            warnings.append(
                "Cannot compute adjusted R²: insufficient degrees of freedom "
                f"({n_samples} samples, {n_features} features)"
            )

        # Standardized residuals
        residual_std = np.std(residuals) if len(residuals) > 1 else 1.0
        if residual_std > 1e-10:
            standardized_residuals = residuals / residual_std
        else:
            standardized_residuals = np.zeros_like(residuals)
            warnings.append("Residual standard deviation is near zero")

        # Build equation string
        equation_parts = [f"{self.model.intercept_:.4f}"]
        coef_dict = {}
        for feat, coef in zip(feature_names, self.model.coef_):
            coef_dict[feat] = float(coef)
            sign = '+' if coef >= 0 else ''
            equation_parts.append(f"{sign}{coef:.4f}*{feat}")
        equation = "RT = " + " ".join(equation_parts)

        # Learned regularization parameters
        alpha_learned = float(self.model.alpha_)  # Noise precision
        lambda_learned = float(self.model.lambda_)  # Weight precision

        # Quality warnings
        if r2 < self.r2_threshold:
            warnings.append(
                f"R² ({r2:.3f}) below threshold ({self.r2_threshold}). "
                "Model may not adequately explain RT variation."
            )

        if r2 > 0.99 and n_samples < 10:
            warnings.append(
                f"Suspiciously high R²={r2:.3f} with only {n_samples} samples. "
                "Possible overfitting - interpret with caution."
            )

        # High regularization indicates limited data information
        if lambda_learned > 100:
            warnings.append(
                f"High weight precision (λ={lambda_learned:.1f}) indicates "
                "strong regularization was needed. Predictions may be conservative."
            )

        # Check for convergence
        if hasattr(self.model, 'n_iter_') and self.model.n_iter_ >= self.max_iter:
            warnings.append(
                f"Model reached maximum iterations ({self.max_iter}). "
                "Consider increasing max_iter for better convergence."
            )

        # Create training prediction result
        training_predictions = self._create_prediction_result(y_pred, y_std)

        # Log summary
        logger.info(
            f"BayesianRidge fit complete: R²={r2:.3f}, RMSE={rmse:.3f}, "
            f"α={alpha_learned:.2f}, λ={lambda_learned:.2f}, "
            f"mean_uncertainty={training_predictions.mean_uncertainty:.3f}"
        )

        if warnings:
            for w in warnings:
                logger.warning(w)

        return RegressionFitResult(
            success=bool(r2 >= self.r2_threshold),
            r2=float(r2),
            adjusted_r2=float(adjusted_r2) if adjusted_r2 is not None else None,
            rmse=float(rmse),
            alpha_learned=alpha_learned,
            lambda_learned=lambda_learned,
            coefficients=coef_dict,
            intercept=float(self.model.intercept_),
            training_predictions=training_predictions,
            residuals=residuals,
            standardized_residuals=standardized_residuals,
            equation=equation,
            warnings=warnings,
            n_samples=n_samples,
            n_features=n_features,
            cv_score=float(self.model.scores_[-1]) if hasattr(self.model, 'scores_') and self.model.scores_ is not None and len(self.model.scores_) > 0 else None
        )

    def predict_with_uncertainty(
        self,
        X: np.ndarray
    ) -> PredictionResult:
        """
        Generate predictions with confidence intervals for new data.

        Args:
            X: Feature matrix for new compounds, shape (n_samples, n_features).
               Must have same features as training data.

        Returns:
            PredictionResult with point estimates and confidence intervals.

        Raises:
            ValueError: If model hasn't been fitted yet.

        Note:
            Prediction uncertainty is typically higher for compounds that are:
            - Far from the training data distribution (extrapolation)
            - In regions with sparse training data
            - Using feature values outside the training range
        """
        if not self._is_fitted:
            raise ValueError(
                "Model must be fitted before prediction. Call fit() first."
            )

        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        # Check feature count matches
        if X.shape[1] != len(self.feature_names_):
            raise ValueError(
                f"Feature count mismatch: expected {len(self.feature_names_)}, "
                f"got {X.shape[1]}"
            )

        # Scale features using training scaler
        X_scaled = self.scaler.transform(X)

        # Get predictions with uncertainty
        y_pred, y_std = self.model.predict(X_scaled, return_std=True)

        logger.debug(
            f"Predicted {len(y_pred)} compounds: "
            f"mean_uncertainty={np.mean(y_std):.3f}"
        )

        return self._create_prediction_result(y_pred, y_std)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Generate point predictions only (no uncertainty).

        Args:
            X: Feature matrix for new compounds.

        Returns:
            Predicted RT values as numpy array.

        Note:
            Use predict_with_uncertainty() when you need confidence intervals.
            This method is provided for compatibility with scikit-learn interface.
        """
        result = self.predict_with_uncertainty(X)
        return result.point_estimate

    def get_model_summary(self) -> Dict[str, Any]:
        """
        Get summary of fitted model for logging/debugging.

        Returns:
            Dictionary with model parameters and diagnostics.
        """
        if not self._is_fitted:
            return {'fitted': False}

        return {
            'fitted': True,
            'features': self.feature_names_,
            'alpha_learned': float(self.model.alpha_),
            'lambda_learned': float(self.model.lambda_),
            'n_iter': self.model.n_iter_,
            'scores': self.model.scores_.tolist() if self.model.scores_ is not None else None,
            'intercept': float(self.model.intercept_),
            'coefficients': dict(zip(self.feature_names_, self.model.coef_.tolist()))
        }

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance based on standardized coefficients.

        Returns:
            Dictionary mapping feature names to importance scores.
            Higher absolute values indicate more important features.

        Note:
            Since features are standardized before fitting, the coefficient
            magnitudes reflect relative importance.
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted first.")

        importance = {}
        for feat, coef in zip(self.feature_names_, self.model.coef_):
            importance[feat] = abs(float(coef))

        # Sort by importance (descending)
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    @property
    def is_fitted(self) -> bool:
        """Check if model has been fitted."""
        return self._is_fitted

    @property
    def feature_names(self) -> Optional[List[str]]:
        """Get feature names if fitted."""
        return self.feature_names_
