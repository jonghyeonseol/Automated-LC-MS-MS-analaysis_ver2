"""
Constrained Ridge Regression for RT Prediction

This module provides Ridge regression with chromatography-informed coefficient
sign constraints. It ensures that learned coefficients respect fundamental
chromatography principles, providing scientifically valid predictions.

Chromatography Principles (Reverse-Phase):
    In reverse-phase chromatography, retention time (RT) reflects hydrophobicity:
    - Higher hydrophobicity → Higher retention time

    Expected coefficient signs based on chemical properties:
    - Log P: POSITIVE (higher partition coefficient = more hydrophobic = higher RT)
    - a_component (carbon count): POSITIVE (more carbons = more hydrophobic = higher RT)
    - b_component (double bonds): NEGATIVE (more unsaturation = less hydrophobic = lower RT)
    - sugar_count: NEGATIVE (more sugars = more hydrophilic = lower RT)

Key Features:
    - Enforces chemically valid coefficient signs during optimization
    - Uses SLSQP (Sequential Least Squares Programming) for constrained optimization
    - Reports which constraints were active (binding) after fitting
    - Tracks how many coefficient sign violations were prevented

Author: LC-MS/MS Analysis Platform
Version: 3.0
"""

import numpy as np
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConstrainedRegressionResult:
    """
    Container for constrained regression results.

    Attributes:
        success: Whether optimization succeeded AND R² meets threshold
        r2: Coefficient of determination
        adjusted_r2: Adjusted R² (penalized for features)
        rmse: Root mean squared error
        coefficients: Dictionary mapping feature names to coefficient values
        intercept: Regression intercept term
        equation: Human-readable regression equation
        optimization_converged: Whether the optimizer converged
        optimization_message: Message from optimizer
        optimization_iterations: Number of iterations used
        active_constraints: List of constraints that were active (binding)
        constraint_violations_prevented: Count of violations that were prevented
        unconstrained_coefficients: What coefficients would be without constraints
        warnings: List of any warnings generated

    The active_constraints list shows which coefficients were pushed to
    boundaries by the constraints. This can indicate data quality issues
    or unusual chromatography behavior.
    """
    success: bool
    r2: float
    adjusted_r2: Optional[float]
    rmse: float
    coefficients: Dict[str, float]
    intercept: float
    equation: str
    optimization_converged: bool
    optimization_message: str
    optimization_iterations: int
    active_constraints: List[str]
    constraint_violations_prevented: int
    unconstrained_coefficients: Optional[Dict[str, float]]
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            'success': self.success,
            'r2': self.r2,
            'adjusted_r2': self.adjusted_r2,
            'rmse': self.rmse,
            'coefficients': self.coefficients,
            'intercept': self.intercept,
            'equation': self.equation,
            'optimization_converged': self.optimization_converged,
            'optimization_message': self.optimization_message,
            'optimization_iterations': self.optimization_iterations,
            'active_constraints': self.active_constraints,
            'constraint_violations_prevented': self.constraint_violations_prevented,
            'unconstrained_coefficients': self.unconstrained_coefficients,
            'warnings': self.warnings,
        }

    @property
    def had_constraints_active(self) -> bool:
        """Check if any constraints were active (binding)."""
        return len(self.active_constraints) > 0


class ConstrainedRTRegression:
    """
    Ridge regression with chromatography-informed coefficient sign constraints.

    This class enforces chemically valid coefficient signs during optimization,
    rather than just warning about violations after fitting. This ensures that
    predictions always respect fundamental chromatography principles.

    Optimization Problem:
        minimize: MSE(y, X @ coef + intercept) + alpha * ||coef||²
        subject to: coef[i] >= 0 for positive-expected features
                    coef[i] <= 0 for negative-expected features

    The optimization uses SLSQP (Sequential Least Squares Programming),
    which is efficient for small to medium-sized problems with constraints.

    Example Usage:
        >>> model = ConstrainedRTRegression(alpha=1.0, enforce_constraints=True)
        >>> result = model.fit(X_train, y_train, ['Log P', 'a_component', 'b_component'])
        >>> if result.success:
        ...     print(f"R² = {result.r2:.3f}")
        ...     print(f"Violations prevented: {result.constraint_violations_prevented}")
        ...     y_pred = model.predict(X_test)
    """

    # Chemical constraints based on reverse-phase chromatography principles
    COEFFICIENT_CONSTRAINTS = {
        'Log P': 'positive',           # Higher Log P = more hydrophobic = higher RT
        'a_component': 'positive',     # More carbons = more hydrophobic = higher RT
        'b_component': 'negative',     # More double bonds = less hydrophobic = lower RT
        'sugar_count': 'negative',     # More sugars = more hydrophilic = lower RT
        'sialic_acids': 'negative',    # More sialic acids = more hydrophilic = lower RT
    }

    # Descriptions for logging
    CONSTRAINT_EXPLANATIONS = {
        'Log P': "Log P coefficient should be positive: higher lipophilicity → higher RT",
        'a_component': "Carbon count coefficient should be positive: longer chains → higher RT",
        'b_component': "Double bond coefficient should be negative: more unsaturation → lower RT",
        'sugar_count': "Sugar count coefficient should be negative: more sugars → lower RT",
        'sialic_acids': "Sialic acid coefficient should be negative: more polar → lower RT",
    }

    def __init__(
        self,
        alpha: float = 1.0,
        enforce_constraints: bool = True,
        r2_threshold: float = 0.70,
        constraint_epsilon: float = 1e-8,
        max_iter: int = 1000,
        ftol: float = 1e-9
    ):
        """
        Initialize constrained regression model.

        Args:
            alpha: Ridge regularization strength. Higher values = stronger
                   regularization = smaller coefficients.
            enforce_constraints: If True, enforce coefficient sign constraints.
                                 If False, fit unconstrained (with warnings).
            r2_threshold: Minimum R² for success flag.
            constraint_epsilon: Small positive value for numerical stability
                               in constraints. Constraints are:
                               coef >= epsilon (for positive)
                               coef <= -epsilon (for negative)
            max_iter: Maximum iterations for SLSQP optimizer.
            ftol: Function tolerance for convergence.
        """
        self.alpha = alpha
        self.enforce_constraints = enforce_constraints
        self.r2_threshold = r2_threshold
        self.constraint_epsilon = constraint_epsilon
        self.max_iter = max_iter
        self.ftol = ftol

        # Model state (set during fit)
        self.coef_: Optional[np.ndarray] = None
        self.intercept_: Optional[float] = None
        self.feature_names_: Optional[List[str]] = None
        self.scaler_: Optional[StandardScaler] = None
        self._is_fitted: bool = False

        logger.debug(
            f"ConstrainedRTRegression initialized: alpha={alpha}, "
            f"enforce_constraints={enforce_constraints}"
        )

    def _build_objective(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_samples: int
    ) -> Callable[[np.ndarray], float]:
        """
        Build the Ridge regression objective function.

        Objective: MSE + (alpha/n_samples) * ||coef||²

        The penalty is scaled by 1/n_samples to make alpha interpretation
        consistent regardless of sample size.
        """
        def ridge_objective(params: np.ndarray) -> float:
            intercept = params[0]
            coef = params[1:]
            predictions = X @ coef + intercept
            mse = np.mean((y - predictions) ** 2)
            penalty = (self.alpha / n_samples) * np.sum(coef ** 2)
            return mse + penalty

        return ridge_objective

    def _build_constraints(
        self,
        feature_names: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Build optimization constraints for coefficient signs.

        Returns list of constraint dictionaries for scipy.optimize.minimize.
        Each constraint is of the form:
            {'type': 'ineq', 'fun': f}  where f(x) >= 0 must hold
        """
        constraints = []

        for idx, feat_name in enumerate(feature_names):
            expected_sign = self.COEFFICIENT_CONSTRAINTS.get(feat_name)

            if expected_sign == 'positive':
                # Constraint: coef[idx] - epsilon >= 0
                # Note: params[0] is intercept, so coefficient is params[idx+1]
                def pos_constraint(params, i=idx):
                    return params[i + 1] - self.constraint_epsilon
                constraints.append({'type': 'ineq', 'fun': pos_constraint})

            elif expected_sign == 'negative':
                # Constraint: -coef[idx] - epsilon >= 0 (i.e., coef[idx] <= -epsilon)
                def neg_constraint(params, i=idx):
                    return -params[i + 1] - self.constraint_epsilon
                constraints.append({'type': 'ineq', 'fun': neg_constraint})

        return constraints

    def _get_initial_params(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_samples: int,
        n_features: int
    ) -> np.ndarray:
        """
        Get initial parameters for optimization using OLS solution.

        Falls back to zeros if OLS fails (e.g., singular matrix).
        """
        try:
            X_with_intercept = np.column_stack([np.ones(n_samples), X])
            initial_params, _, _, _ = np.linalg.lstsq(X_with_intercept, y, rcond=None)
            return initial_params
        except np.linalg.LinAlgError:
            logger.warning("OLS solution failed, starting from zeros")
            return np.zeros(n_features + 1)

    def _fit_unconstrained(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str]
    ) -> Tuple[np.ndarray, float]:
        """
        Fit unconstrained model for comparison.

        Returns:
            Tuple of (coefficients, intercept)
        """
        n_samples = len(y)
        objective = self._build_objective(X, y, n_samples)
        initial_params = self._get_initial_params(X, y, n_samples, len(feature_names))

        result = minimize(
            objective,
            x0=initial_params,
            method='SLSQP',
            options={'maxiter': self.max_iter, 'ftol': self.ftol, 'disp': False}
        )

        return result.x[1:], result.x[0]

    def _identify_active_constraints(
        self,
        constrained_coef: np.ndarray,
        unconstrained_coef: np.ndarray,
        feature_names: List[str]
    ) -> Tuple[List[str], int]:
        """
        Identify which constraints were active (binding) after optimization.

        A constraint is considered active if:
        1. The feature has an expected sign constraint
        2. The unconstrained coefficient would violate it
        3. The constrained coefficient respects it

        Returns:
            Tuple of (active_constraint_descriptions, violation_count)
        """
        active_constraints = []
        violations_prevented = 0

        for idx, feat_name in enumerate(feature_names):
            expected_sign = self.COEFFICIENT_CONSTRAINTS.get(feat_name)
            if expected_sign is None:
                continue

            constrained_val = constrained_coef[idx]
            unconstrained_val = unconstrained_coef[idx]

            if expected_sign == 'positive':
                if unconstrained_val < 0 and constrained_val >= 0:
                    active_constraints.append(
                        f"{feat_name}: constrained to {constrained_val:.4f} "
                        f"(unconstrained would be {unconstrained_val:.4f})"
                    )
                    violations_prevented += 1

            elif expected_sign == 'negative':
                if unconstrained_val > 0 and constrained_val <= 0:
                    active_constraints.append(
                        f"{feat_name}: constrained to {constrained_val:.4f} "
                        f"(unconstrained would be {unconstrained_val:.4f})"
                    )
                    violations_prevented += 1

        return active_constraints, violations_prevented

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str]
    ) -> ConstrainedRegressionResult:
        """
        Fit constrained Ridge regression model.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Target RT values of shape (n_samples,).
            feature_names: List of feature names (must match X columns).

        Returns:
            ConstrainedRegressionResult with fit diagnostics.

        The optimization enforces coefficient sign constraints based on
        chromatography principles. After fitting, you can check:
        - active_constraints: Which constraints were binding
        - constraint_violations_prevented: How many violations were prevented
        - unconstrained_coefficients: What coefficients would be without constraints
        """
        X = np.asarray(X)
        y = np.asarray(y)

        if X.ndim == 1:
            X = X.reshape(-1, 1)

        n_samples, n_features = X.shape
        self.feature_names_ = feature_names
        warnings = []

        logger.info(
            f"Fitting ConstrainedRTRegression: {n_samples} samples, "
            f"{n_features} features, alpha={self.alpha}, "
            f"constraints={'enabled' if self.enforce_constraints else 'disabled'}"
        )

        # Feature scaling
        self.scaler_ = StandardScaler()
        X_scaled = self.scaler_.fit_transform(X)

        # Build objective function
        objective = self._build_objective(X_scaled, y, n_samples)

        # Get initial parameters
        initial_params = self._get_initial_params(X_scaled, y, n_samples, n_features)

        # Build constraints if enforcing
        constraints = []
        if self.enforce_constraints:
            constraints = self._build_constraints(feature_names)
            logger.debug(f"Built {len(constraints)} coefficient sign constraints")

        # Run optimization
        result = minimize(
            objective,
            x0=initial_params,
            method='SLSQP',
            constraints=constraints if constraints else None,
            options={
                'maxiter': self.max_iter,
                'ftol': self.ftol,
                'disp': False
            }
        )

        self.intercept_ = result.x[0]
        self.coef_ = result.x[1:]
        self._is_fitted = True

        # Calculate metrics
        y_pred = X_scaled @ self.coef_ + self.intercept_
        residuals = y - y_pred
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        r2 = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0.0
        rmse = np.sqrt(np.mean(residuals ** 2))

        # Adjusted R²
        adjusted_r2 = None
        if n_samples > n_features + 1:
            adjusted_r2 = 1 - (1 - r2) * (n_samples - 1) / (n_samples - n_features - 1)

        # Fit unconstrained for comparison
        unconstrained_coef = None
        active_constraints = []
        violations_prevented = 0

        if self.enforce_constraints:
            unconstrained_coef_arr, _ = self._fit_unconstrained(
                X_scaled, y, feature_names
            )
            unconstrained_coef = {
                feat: float(c) for feat, c in zip(feature_names, unconstrained_coef_arr)
            }

            active_constraints, violations_prevented = self._identify_active_constraints(
                self.coef_, unconstrained_coef_arr, feature_names
            )

            if active_constraints:
                logger.info(
                    f"Constraints active: {violations_prevented} coefficient sign "
                    f"violation(s) prevented"
                )
                for constraint in active_constraints:
                    logger.info(f"  - {constraint}")

        # Build coefficient dictionary
        coef_dict = {feat: float(c) for feat, c in zip(feature_names, self.coef_)}

        # Build equation string
        equation_parts = [f"{self.intercept_:.4f}"]
        for feat, coef in coef_dict.items():
            sign = '+' if coef >= 0 else ''
            equation_parts.append(f"{sign}{coef:.4f}*{feat}")
        equation = "RT = " + " ".join(equation_parts)

        # Generate warnings
        if not result.success:
            warnings.append(f"Optimization did not converge: {result.message}")

        if r2 < self.r2_threshold:
            warnings.append(
                f"R² ({r2:.3f}) below threshold ({self.r2_threshold})"
            )

        if violations_prevented > 0:
            warnings.append(
                f"{violations_prevented} coefficient sign violation(s) were prevented "
                f"by constraints. This may indicate unusual data or chromatography behavior."
            )

        # Log summary
        logger.info(
            f"ConstrainedRTRegression fit complete: R²={r2:.3f}, RMSE={rmse:.3f}, "
            f"converged={result.success}, violations_prevented={violations_prevented}"
        )

        return ConstrainedRegressionResult(
            success=bool(result.success and r2 >= self.r2_threshold),
            r2=float(r2),
            adjusted_r2=float(adjusted_r2) if adjusted_r2 is not None else None,
            rmse=float(rmse),
            coefficients=coef_dict,
            intercept=float(self.intercept_),
            equation=equation,
            optimization_converged=bool(result.success),
            optimization_message=str(result.message),
            optimization_iterations=int(result.nit) if hasattr(result, 'nit') else 0,
            active_constraints=active_constraints,
            constraint_violations_prevented=violations_prevented,
            unconstrained_coefficients=unconstrained_coef,
            warnings=warnings
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Generate predictions for new data.

        Args:
            X: Feature matrix of shape (n_samples, n_features).

        Returns:
            Predicted RT values as numpy array.

        Raises:
            ValueError: If model hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted before prediction. Call fit() first.")

        X = np.asarray(X)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        X_scaled = self.scaler_.transform(X)
        return X_scaled @ self.coef_ + self.intercept_

    def get_coefficient_validity(self) -> Dict[str, Dict[str, Any]]:
        """
        Get validity assessment for each coefficient.

        Returns dictionary with:
        - expected_sign: What sign chromatography expects
        - actual_sign: Actual sign of fitted coefficient
        - is_valid: Whether coefficient respects chromatography
        - explanation: Why the expected sign is expected
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted first.")

        validity = {}
        for feat, coef in zip(self.feature_names_, self.coef_):
            expected = self.COEFFICIENT_CONSTRAINTS.get(feat)
            actual = 'positive' if coef > 0 else ('negative' if coef < 0 else 'zero')

            if expected is None:
                is_valid = True  # No constraint for this feature
            elif expected == 'positive':
                is_valid = bool(coef >= 0)
            else:  # negative
                is_valid = bool(coef <= 0)

            validity[feat] = {
                'coefficient': float(coef),
                'expected_sign': expected,
                'actual_sign': actual,
                'is_valid': is_valid,
                'explanation': self.CONSTRAINT_EXPLANATIONS.get(feat, '')
            }

        return validity

    @property
    def is_fitted(self) -> bool:
        """Check if model has been fitted."""
        return self._is_fitted

    @property
    def feature_names(self) -> Optional[List[str]]:
        """Get feature names if fitted."""
        return self.feature_names_

    @classmethod
    def get_expected_sign(cls, feature_name: str) -> Optional[str]:
        """
        Get expected coefficient sign for a feature.

        Args:
            feature_name: Name of the feature.

        Returns:
            'positive', 'negative', or None if no constraint defined.
        """
        return cls.COEFFICIENT_CONSTRAINTS.get(feature_name)

    @classmethod
    def get_all_constraints(cls) -> Dict[str, str]:
        """Get all defined coefficient constraints."""
        return cls.COEFFICIENT_CONSTRAINTS.copy()
