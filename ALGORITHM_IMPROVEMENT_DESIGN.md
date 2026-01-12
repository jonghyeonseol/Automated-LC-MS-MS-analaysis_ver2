# Algorithm Improvement Design Document

**LC-MS/MS Ganglioside Analysis Platform - Algorithm Evolution v3.0**

| Field | Value |
|-------|-------|
| **Document Version** | 1.0 |
| **Created** | December 29, 2025 |
| **Status** | Draft - Ready for Review |
| **Scope** | 5-Rule → 10-Rule Pipeline Enhancement |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current System Analysis](#2-current-system-analysis)
3. [Improvement Objectives](#3-improvement-objectives)
4. [Phase 1: Regression Model Enhancement](#4-phase-1-regression-model-enhancement)
5. [Phase 2: New Validation Rules](#5-phase-2-new-validation-rules)
6. [Phase 3: Integration Architecture](#6-phase-3-integration-architecture)
7. [API Changes](#7-api-changes)
8. [Testing Strategy](#8-testing-strategy)
9. [Migration Plan](#9-migration-plan)
10. [Risk Assessment](#10-risk-assessment)

---

## 1. Executive Summary

### 1.1 Background

The LC-MS/MS Ganglioside Analysis Platform currently uses a 7-rule sequential algorithm for compound identification and validation. This document proposes expanding to a 10-rule system with enhanced prediction quality, scientific validity enforcement, and extensibility for general glycolipid analysis.

### 1.2 Key Improvements

| Category | Current State | Proposed State |
|----------|---------------|----------------|
| **Regression Model** | RidgeCV with point estimates | Bayesian Ridge with confidence intervals |
| **Coefficient Constraints** | Post-hoc warning only | Constrained optimization (enforced) |
| **Classification** | Binary (valid/outlier) | Probabilistic confidence scoring |
| **Cross-Validation** | Within-prefix only | Cross-prefix consistency checks |
| **Modification Handling** | O-Acetylation only | Full modification stack validation |
| **Rule Count** | 7 rules | 10 rules |

### 1.3 Expected Outcomes

- **+30-50% reduction** in false positives through confidence scoring
- **Per-prediction uncertainty** enabling risk-aware decision making
- **Chemically valid** predictions guaranteed via constrained optimization
- **Extensible architecture** ready for ceramides, sphingomyelins, etc.

---

## 2. Current System Analysis

### 2.1 Existing Rule Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CURRENT 7-RULE PIPELINE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────┐   ┌───────────┐   ┌─────────┐   ┌─────────────────┐  │
│  │ Rule 1  │──▶│ Rule 2-3  │──▶│ Rule 4  │──▶│     Rule 5      │  │
│  │ Regress │   │  Sugar &  │   │ O-Acet  │   │  Fragmentation  │  │
│  │ RidgeCV │   │  Isomers  │   │ Valid.  │   │    Detection    │  │
│  └─────────┘   └───────────┘   └─────────┘   └─────────────────┘  │
│       │                                              │              │
│       ▼                                              ▼              │
│  ┌─────────┐                                   ┌─────────┐         │
│  │ Rule 6  │                                   │ Rule 7  │         │
│  │Sugar-RT │◀──────────────────────────────────│Category │         │
│  │ Valid.  │                                   │ Order   │         │
│  └─────────┘                                   └─────────┘         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Current File Structure

```
django_ganglioside/apps/analysis/services/
├── ganglioside_processor_v2.py    # Main orchestrator (861 lines)
├── improved_regression.py          # RidgeCV implementation (424 lines)
├── chemical_validation.py          # Rules 6-7 validation (528 lines)
├── ganglioside_categorizer.py      # GM/GD/GT/GQ/GP classification
├── analysis_service.py             # High-level API
└── export_service.py               # Results export
```

### 2.3 Identified Gaps

| Gap ID | Description | Impact |
|--------|-------------|--------|
| G-001 | No prediction uncertainty | Can't distinguish reliable vs uncertain predictions |
| G-002 | Post-hoc coefficient warnings | Chemically invalid coefficients in production |
| G-003 | Binary classification | No nuance between "borderline" and "clear" outliers |
| G-004 | Single-prefix validation | Missing cross-category consistency checks |
| G-005 | Limited modification support | Only OAc validated, not dHex, Hex, etc. |

---

## 3. Improvement Objectives

### 3.1 Primary Objectives

| ID | Objective | Success Metric |
|----|-----------|----------------|
| O-001 | Prediction uncertainty quantification | 95% CI available for all predictions |
| O-002 | Chemically valid coefficients | 0 coefficient sign violations |
| O-003 | Probabilistic classification | Confidence score 0-1 for all compounds |
| O-004 | Cross-prefix validation | Category ordering validated globally |
| O-005 | Modification stack validation | All stackable mods validated |

### 3.2 Design Principles

1. **Accuracy First**: Accept complexity if it improves identification accuracy
2. **Scientific Validity**: All predictions must follow chromatography principles
3. **Extensibility**: Architecture must support general glycolipids
4. **Backward Compatibility**: Existing API contracts preserved

---

## 4. Phase 1: Regression Model Enhancement

### 4.1 Bayesian Ridge Implementation

#### 4.1.1 Rationale

| Aspect | RidgeCV (Current) | BayesianRidge (Proposed) |
|--------|-------------------|--------------------------|
| Regularization | Fixed alpha grid search | Automatic learning from data |
| Uncertainty | None | Per-prediction σ |
| Small samples | Prone to overfitting | Robust via Bayesian inference |
| Confidence intervals | Not available | 95%/99% CI automatic |

#### 4.1.2 Technical Specification

**File**: `django_ganglioside/apps/analysis/services/bayesian_regression.py`

```python
from sklearn.linear_model import BayesianRidge
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional, List
from sklearn.preprocessing import StandardScaler

@dataclass
class PredictionResult:
    """Container for predictions with uncertainty quantification"""
    point_estimate: np.ndarray      # Mean prediction
    std_deviation: np.ndarray       # Standard deviation per prediction
    ci_lower_95: np.ndarray         # 95% confidence interval lower bound
    ci_upper_95: np.ndarray         # 95% confidence interval upper bound
    ci_lower_99: np.ndarray         # 99% confidence interval lower bound
    ci_upper_99: np.ndarray         # 99% confidence interval upper bound

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'point_estimate': self.point_estimate.tolist(),
            'std_deviation': self.std_deviation.tolist(),
            'ci_lower_95': self.ci_lower_95.tolist(),
            'ci_upper_95': self.ci_upper_95.tolist(),
            'ci_lower_99': self.ci_lower_99.tolist(),
            'ci_upper_99': self.ci_upper_99.tolist(),
        }


@dataclass
class RegressionFitResult:
    """Container for regression fitting results"""
    success: bool
    r2: float
    adjusted_r2: Optional[float]
    alpha_learned: float            # Noise precision (learned)
    lambda_learned: float           # Weight precision (learned)
    coefficients: Dict[str, float]
    intercept: float
    training_predictions: PredictionResult
    residuals: np.ndarray
    standardized_residuals: np.ndarray
    equation: str
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary"""
        return {
            'success': self.success,
            'r2': self.r2,
            'adjusted_r2': self.adjusted_r2,
            'alpha_learned': self.alpha_learned,
            'lambda_learned': self.lambda_learned,
            'coefficients': self.coefficients,
            'intercept': self.intercept,
            'training_predictions': self.training_predictions.to_dict(),
            'residuals': self.residuals.tolist(),
            'standardized_residuals': self.standardized_residuals.tolist(),
            'equation': self.equation,
            'warnings': self.warnings,
        }


class BayesianRTPredictor:
    """
    Bayesian Ridge regression for RT prediction with full uncertainty quantification.

    Advantages over RidgeCV:
    - Automatic regularization learning (no alpha grid search)
    - Per-prediction uncertainty estimates (σ for each prediction)
    - More robust to small sample sizes (Bayesian shrinkage)
    - Interpretable confidence intervals (95%, 99%)

    The Bayesian Ridge model places Gamma priors on the precision parameters:
    - α (alpha): Precision of the noise
    - λ (lambda): Precision of the weights

    These are learned from data, providing automatic regularization that adapts
    to the complexity of each prefix group.
    """

    def __init__(
        self,
        alpha_1: float = 1e-6,      # Shape parameter for Gamma prior on α
        alpha_2: float = 1e-6,      # Rate parameter for Gamma prior on α
        lambda_1: float = 1e-6,     # Shape parameter for Gamma prior on λ
        lambda_2: float = 1e-6,     # Rate parameter for Gamma prior on λ
        r2_threshold: float = 0.70,
        min_samples: int = 3
    ):
        """
        Initialize Bayesian RT Predictor.

        Args:
            alpha_1, alpha_2: Hyperparameters for noise precision prior
            lambda_1, lambda_2: Hyperparameters for weight precision prior
            r2_threshold: Minimum R² for valid regression
            min_samples: Minimum samples required

        Note:
            Small values (1e-6) for hyperparameters give non-informative priors,
            letting the data determine the regularization strength.
        """
        self.model = BayesianRidge(
            alpha_1=alpha_1,
            alpha_2=alpha_2,
            lambda_1=lambda_1,
            lambda_2=lambda_2,
            compute_score=True,
            fit_intercept=True,
            max_iter=300,
            tol=1e-6
        )
        self.r2_threshold = r2_threshold
        self.min_samples = min_samples
        self.scaler: Optional[StandardScaler] = None
        self.feature_names_: Optional[List[str]] = None
        self._is_fitted = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str]
    ) -> RegressionFitResult:
        """
        Fit Bayesian Ridge model with uncertainty quantification.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target RT values (n_samples,)
            feature_names: Names of features for interpretability

        Returns:
            RegressionFitResult with full diagnostics
        """
        warnings = []
        n_samples, n_features = X.shape
        self.feature_names_ = feature_names

        # Validate inputs
        if n_samples < self.min_samples:
            return RegressionFitResult(
                success=False,
                r2=0.0,
                adjusted_r2=None,
                alpha_learned=0.0,
                lambda_learned=0.0,
                coefficients={},
                intercept=0.0,
                training_predictions=PredictionResult(
                    np.array([]), np.array([]), np.array([]),
                    np.array([]), np.array([]), np.array([])
                ),
                residuals=np.array([]),
                standardized_residuals=np.array([]),
                equation='',
                warnings=[f'Insufficient samples: {n_samples} < {self.min_samples}']
            )

        # Feature scaling for numerical stability
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # Fit Bayesian Ridge
        self.model.fit(X_scaled, y)
        self._is_fitted = True

        # Get predictions with uncertainty
        y_pred, y_std = self.model.predict(X_scaled, return_std=True)

        # Calculate metrics
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0.0

        # Adjusted R² (penalizes for number of features)
        if n_samples > n_features + 1:
            adjusted_r2 = 1 - (1 - r2) * (n_samples - 1) / (n_samples - n_features - 1)
        else:
            adjusted_r2 = None
            warnings.append('Cannot compute adjusted R²: insufficient degrees of freedom')

        # Residual analysis
        residuals = y - y_pred
        residual_std = np.std(residuals) if len(residuals) > 1 else 1.0
        standardized_residuals = residuals / residual_std if residual_std > 1e-10 else residuals

        # Build equation string
        equation_parts = [f'{self.model.intercept_:.4f}']
        coef_dict = {}
        for feat, coef in zip(feature_names, self.model.coef_):
            coef_dict[feat] = float(coef)
            sign = '+' if coef >= 0 else ''
            equation_parts.append(f'{sign}{coef:.4f}*{feat}')
        equation = 'RT = ' + ' '.join(equation_parts)

        # Quality warnings
        if r2 < self.r2_threshold:
            warnings.append(f'R² ({r2:.3f}) below threshold ({self.r2_threshold})')

        if r2 > 0.99 and n_samples < 10:
            warnings.append(f'Suspiciously high R²={r2:.3f} with only {n_samples} samples - possible overfitting')

        # Learned regularization info
        alpha_learned = float(self.model.alpha_)  # Noise precision
        lambda_learned = float(self.model.lambda_)  # Weight precision

        # High regularization indicates limited data
        if lambda_learned > 100:
            warnings.append(f'High weight precision (λ={lambda_learned:.1f}) indicates strong regularization')

        return RegressionFitResult(
            success=r2 >= self.r2_threshold,
            r2=float(r2),
            adjusted_r2=float(adjusted_r2) if adjusted_r2 is not None else None,
            alpha_learned=alpha_learned,
            lambda_learned=lambda_learned,
            coefficients=coef_dict,
            intercept=float(self.model.intercept_),
            training_predictions=PredictionResult(
                point_estimate=y_pred,
                std_deviation=y_std,
                ci_lower_95=y_pred - 1.96 * y_std,
                ci_upper_95=y_pred + 1.96 * y_std,
                ci_lower_99=y_pred - 2.576 * y_std,
                ci_upper_99=y_pred + 2.576 * y_std
            ),
            residuals=residuals,
            standardized_residuals=standardized_residuals,
            equation=equation,
            warnings=warnings
        )

    def predict_with_uncertainty(
        self,
        X: np.ndarray
    ) -> PredictionResult:
        """
        Generate predictions with confidence intervals for new data.

        Args:
            X: Feature matrix for new compounds

        Returns:
            PredictionResult with uncertainty quantification
        """
        if not self._is_fitted:
            raise ValueError('Model must be fitted before prediction')

        X_scaled = self.scaler.transform(X)
        y_pred, y_std = self.model.predict(X_scaled, return_std=True)

        return PredictionResult(
            point_estimate=y_pred,
            std_deviation=y_std,
            ci_lower_95=y_pred - 1.96 * y_std,
            ci_upper_95=y_pred + 1.96 * y_std,
            ci_lower_99=y_pred - 2.576 * y_std,
            ci_upper_99=y_pred + 2.576 * y_std
        )

    def get_model_summary(self) -> Dict[str, Any]:
        """Get summary of fitted model for logging/debugging."""
        if not self._is_fitted:
            return {'fitted': False}

        return {
            'fitted': True,
            'features': self.feature_names_,
            'alpha_learned': self.model.alpha_,
            'lambda_learned': self.model.lambda_,
            'n_iter': self.model.n_iter_,
            'score': self.model.scores_[-1] if self.model.scores_ else None
        }
```

### 4.2 Constrained Optimization

#### 4.2.1 Rationale

Chromatography principles dictate specific relationships between compound properties and retention time:

| Feature | Expected Sign | Chemical Reason |
|---------|---------------|-----------------|
| Log P | POSITIVE (+) | Higher lipophilicity → longer retention |
| a_component | POSITIVE (+) | More carbons → higher hydrophobicity |
| b_component | NEGATIVE (-) | More double bonds → lower hydrophobicity |
| sugar_count | NEGATIVE (-) | More sugars → more hydrophilic |

Current system warns about violations but doesn't prevent them. Constrained optimization guarantees valid coefficients.

#### 4.2.2 Technical Specification

**File**: `django_ganglioside/apps/analysis/services/constrained_regression.py`

```python
import numpy as np
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConstrainedRegressionResult:
    """Container for constrained regression results"""
    success: bool
    r2: float
    coefficients: Dict[str, float]
    intercept: float
    optimization_converged: bool
    optimization_message: str
    active_constraints: List[str]
    constraint_violations_prevented: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'r2': self.r2,
            'coefficients': self.coefficients,
            'intercept': self.intercept,
            'optimization_converged': self.optimization_converged,
            'optimization_message': self.optimization_message,
            'active_constraints': self.active_constraints,
            'constraint_violations_prevented': self.constraint_violations_prevented
        }


class ConstrainedRTRegression:
    """
    Ridge regression with chromatography-informed coefficient sign constraints.

    Uses constrained optimization to ENFORCE chemically valid coefficients,
    rather than just warning about violations after fitting.

    Optimization Problem:
        minimize: MSE(y, X @ coef + intercept) + alpha * ||coef||²
        subject to: coef[i] >= 0 for positive-expected features
                    coef[i] <= 0 for negative-expected features

    Chromatography Principles (Reverse-Phase):
    - Higher hydrophobicity → Higher retention time (RT)
    - Log P: Composite hydrophobicity measure → POSITIVE coefficient
    - Carbon count (a_component): More carbons → more hydrophobic → POSITIVE
    - Double bonds (b_component): More unsaturation → less hydrophobic → NEGATIVE
    - Sugar count: More sugars → more hydrophilic → NEGATIVE
    """

    # Chemical constraints based on reverse-phase chromatography
    COEFFICIENT_CONSTRAINTS = {
        'Log P': 'positive',
        'a_component': 'positive',
        'b_component': 'negative',
        'sugar_count': 'negative',
    }

    def __init__(
        self,
        alpha: float = 1.0,
        enforce_constraints: bool = True,
        r2_threshold: float = 0.70,
        constraint_epsilon: float = 1e-8
    ):
        """
        Initialize constrained regression.

        Args:
            alpha: Ridge regularization strength
            enforce_constraints: Whether to enforce sign constraints
            r2_threshold: Minimum R² for success
            constraint_epsilon: Small value for numerical stability in constraints
        """
        self.alpha = alpha
        self.enforce_constraints = enforce_constraints
        self.r2_threshold = r2_threshold
        self.constraint_epsilon = constraint_epsilon
        self.coef_: Optional[np.ndarray] = None
        self.intercept_: Optional[float] = None
        self.feature_names_: Optional[List[str]] = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str]
    ) -> ConstrainedRegressionResult:
        """
        Fit regression with coefficient sign constraints.

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target values (n_samples,)
            feature_names: Feature names for constraint lookup

        Returns:
            ConstrainedRegressionResult with fit diagnostics
        """
        self.feature_names_ = feature_names
        n_samples, n_features = X.shape

        # Define objective function: Ridge loss
        def ridge_loss(params: np.ndarray) -> float:
            intercept = params[0]
            coef = params[1:]
            pred = X @ coef + intercept
            mse = np.mean((y - pred) ** 2)
            penalty = self.alpha * np.sum(coef ** 2) / n_samples
            return mse + penalty

        # Build sign constraints
        constraints = []
        if self.enforce_constraints:
            for idx, feat_name in enumerate(feature_names):
                expected_sign = self.COEFFICIENT_CONSTRAINTS.get(feat_name)
                if expected_sign == 'positive':
                    # coef[idx] >= epsilon
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda p, i=idx: p[i + 1] - self.constraint_epsilon
                    })
                elif expected_sign == 'negative':
                    # -coef[idx] >= epsilon  (i.e., coef[idx] <= -epsilon)
                    constraints.append({
                        'type': 'ineq',
                        'fun': lambda p, i=idx: -p[i + 1] - self.constraint_epsilon
                    })

        # Compute OLS solution as starting point
        X_with_intercept = np.column_stack([np.ones(n_samples), X])
        try:
            initial_params = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            initial_params = np.zeros(n_features + 1)

        # Run constrained optimization
        result = minimize(
            ridge_loss,
            x0=initial_params,
            method='SLSQP',
            constraints=constraints if constraints else None,
            options={
                'maxiter': 1000,
                'ftol': 1e-9,
                'disp': False
            }
        )

        self.intercept_ = result.x[0]
        self.coef_ = result.x[1:]

        # Calculate R²
        y_pred = X @ self.coef_ + self.intercept_
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 1e-10 else 0.0

        # Identify active constraints (coefficients pushed to boundary)
        active_constraints = []
        violations_prevented = 0

        # Compare with unconstrained solution to see what was prevented
        if self.enforce_constraints:
            # Fit unconstrained for comparison
            unconstrained_result = minimize(
                ridge_loss,
                x0=initial_params,
                method='SLSQP',
                options={'maxiter': 1000, 'ftol': 1e-9}
            )
            unconstrained_coef = unconstrained_result.x[1:]

            for idx, feat_name in enumerate(feature_names):
                expected_sign = self.COEFFICIENT_CONSTRAINTS.get(feat_name)
                constrained_val = self.coef_[idx]
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

        coef_dict = {feat: float(c) for feat, c in zip(feature_names, self.coef_)}

        logger.info(
            f"Constrained regression: R²={r2:.3f}, "
            f"violations prevented={violations_prevented}, "
            f"converged={result.success}"
        )

        return ConstrainedRegressionResult(
            success=result.success and r2 >= self.r2_threshold,
            r2=float(r2),
            coefficients=coef_dict,
            intercept=float(self.intercept_),
            optimization_converged=result.success,
            optimization_message=result.message,
            active_constraints=active_constraints,
            constraint_violations_prevented=violations_prevented
        )

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate predictions for new data."""
        if self.coef_ is None:
            raise ValueError('Model must be fitted before prediction')
        return X @ self.coef_ + self.intercept_
```

---

## 5. Phase 2: New Validation Rules

### 5.1 Rule 8: Modification Stack Validation

#### 5.1.1 Purpose

Validate that compound modification combinations follow expected patterns. If base compound A exists with single modifications A+mod1 and A+mod2, then combination A+mod1+mod2 should likely exist (combinatorial expectation).

#### 5.1.2 Technical Specification

**File**: `django_ganglioside/apps/analysis/services/modification_validator.py`

```python
import re
from typing import Dict, List, Set, Any, Tuple
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class ModificationParsed:
    """Parsed modification information from compound name"""
    base: str                    # Base compound (e.g., 'GD1')
    suffix: str                  # Lipid tail (e.g., '36:1;O2')
    modifications: Tuple[str, ...] # Sorted tuple of mods (e.g., ('+OAc', '+dHex'))
    full_name: str               # Original compound name


@dataclass
class ModificationWarning:
    """Warning for modification pattern violation"""
    warning_type: str
    message: str
    details: Dict[str, Any]


@dataclass
class ModificationAnalysis:
    """Container for modification analysis results"""
    valid_combinations: List[Dict[str, Any]]
    missing_expected: List[Dict[str, Any]]
    rt_ordering_violations: List[Dict[str, Any]]
    warnings: List[ModificationWarning]
    statistics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'valid_combinations': self.valid_combinations,
            'missing_expected': self.missing_expected,
            'rt_ordering_violations': self.rt_ordering_violations,
            'warnings': [
                {'type': w.warning_type, 'message': w.message, 'details': w.details}
                for w in self.warnings
            ],
            'statistics': self.statistics
        }


class ModificationStackValidator:
    """
    Rule 8: Validate modification stacking patterns.

    Validates:
    1. Combinatorial completeness - if A+mod1 and A+mod2 exist, A+mod1+mod2 should exist
    2. RT ordering - modifications should increase/decrease RT consistently
    3. Stack depth - unusual modification stacks flagged

    Known Stackable Modifications:
    - +OAc (O-acetylation): +RT (increases hydrophobicity)
    - +dHex (deoxyhexose): +RT (less hydroxyl groups)
    - +Hex (hexose): -RT (adds sugar, more hydrophilic)
    - +NeuAc (sialic acid): -RT (adds charged sugar)
    - +Fuc (fucose): slight +RT (deoxy sugar)
    """

    # Known modifications and their expected RT effects
    MODIFICATION_RT_EFFECTS = {
        '+OAc': {'direction': 'increase', 'typical_shift': (0.3, 3.0)},
        '+dHex': {'direction': 'increase', 'typical_shift': (0.2, 2.0)},
        '+Hex': {'direction': 'decrease', 'typical_shift': (-2.0, -0.2)},
        '+NeuAc': {'direction': 'decrease', 'typical_shift': (-3.0, -0.3)},
        '+Fuc': {'direction': 'increase', 'typical_shift': (0.1, 1.5)},
    }

    # Maximum reasonable modification stack depth
    MAX_STACK_DEPTH = 4

    def __init__(
        self,
        rt_tolerance: float = 0.5,
        require_combinatorial_completeness: bool = False
    ):
        """
        Initialize modification validator.

        Args:
            rt_tolerance: Tolerance for RT ordering validation
            require_combinatorial_completeness: If True, flag missing combinations
        """
        self.rt_tolerance = rt_tolerance
        self.require_combinatorial_completeness = require_combinatorial_completeness

    def parse_modifications(self, name: str) -> ModificationParsed:
        """
        Parse compound name to extract base, suffix, and modifications.

        Examples:
            'GD1+OAc+dHex(36:1;O2)' → base='GD1', suffix='36:1;O2', mods=('+OAc', '+dHex')
            'GM3(34:1;O2)' → base='GM3', suffix='34:1;O2', mods=()
        """
        # Extract suffix (content within parentheses)
        suffix_match = re.search(r'\(([^)]+)\)', name)
        suffix = suffix_match.group(1) if suffix_match else ''

        # Remove suffix for modification parsing
        name_no_suffix = re.sub(r'\([^)]+\)', '', name)

        # Find all modifications (pattern: +Word)
        modifications = tuple(sorted(re.findall(r'(\+\w+)', name_no_suffix)))

        # Base is what remains after removing modifications
        base = re.sub(r'\+\w+', '', name_no_suffix).strip()

        return ModificationParsed(
            base=base,
            suffix=suffix,
            modifications=modifications,
            full_name=name
        )

    def validate(self, df: pd.DataFrame) -> ModificationAnalysis:
        """
        Validate modification patterns across all compounds.

        Args:
            df: DataFrame with 'Name' and 'RT' columns

        Returns:
            ModificationAnalysis with validation results
        """
        logger.info("Rule 8: Validating modification stacking patterns...")

        # Parse all compounds
        parsed_data = []
        for _, row in df.iterrows():
            parsed = self.parse_modifications(row['Name'])
            parsed_data.append({
                'name': row['Name'],
                'rt': row['RT'],
                'base': parsed.base,
                'suffix': parsed.suffix,
                'mods': parsed.modifications,
                'n_mods': len(parsed.modifications)
            })

        parsed_df = pd.DataFrame(parsed_data)

        valid_combinations = []
        missing_expected = []
        rt_violations = []
        warnings = []

        # Group by base compound + suffix
        for (base, suffix), group in parsed_df.groupby(['base', 'suffix']):
            if len(group) < 2:
                continue

            # Get all modification sets present
            mod_sets = {row['mods']: row for _, row in group.iterrows()}

            # Check combinatorial completeness
            if self.require_combinatorial_completeness:
                individual_mods = set()
                for mods in mod_sets.keys():
                    individual_mods.update(mods)

                # For each pair of individual mods, check if combination exists
                mod_list = sorted(individual_mods)
                for i, mod1 in enumerate(mod_list):
                    if (mod1,) not in mod_sets:
                        continue
                    for mod2 in mod_list[i+1:]:
                        if (mod2,) not in mod_sets:
                            continue

                        expected_combo = tuple(sorted([mod1, mod2]))
                        if expected_combo not in mod_sets:
                            missing_expected.append({
                                'base': base,
                                'suffix': suffix,
                                'expected': expected_combo,
                                'present': [(mod1,), (mod2,)]
                            })

            # Validate RT ordering for modifications
            base_row = mod_sets.get((), None)
            if base_row is not None:
                base_rt = base_row['rt']

                for mods, row in mod_sets.items():
                    if len(mods) == 0:
                        continue

                    mod_rt = row['rt']

                    # Check each modification's expected effect
                    for mod in mods:
                        effect = self.MODIFICATION_RT_EFFECTS.get(mod)
                        if effect is None:
                            continue

                        direction = effect['direction']
                        min_shift, max_shift = effect['typical_shift']
                        actual_shift = mod_rt - base_rt

                        if direction == 'increase' and actual_shift < min_shift - self.rt_tolerance:
                            rt_violations.append({
                                'compound': row['name'],
                                'modification': mod,
                                'expected_direction': 'increase',
                                'actual_shift': round(actual_shift, 3),
                                'expected_range': (min_shift, max_shift)
                            })
                        elif direction == 'decrease' and actual_shift > max_shift + self.rt_tolerance:
                            rt_violations.append({
                                'compound': row['name'],
                                'modification': mod,
                                'expected_direction': 'decrease',
                                'actual_shift': round(actual_shift, 3),
                                'expected_range': (min_shift, max_shift)
                            })

                valid_combinations.append({
                    'base': base,
                    'suffix': suffix,
                    'modifications': mods,
                    'rt': round(mod_rt, 3)
                })

        # Check for unusual stack depths
        deep_stacks = parsed_df[parsed_df['n_mods'] > self.MAX_STACK_DEPTH]
        for _, row in deep_stacks.iterrows():
            warnings.append(ModificationWarning(
                warning_type='deep_stack',
                message=f"Unusual modification depth: {row['n_mods']} modifications",
                details={'compound': row['name'], 'modifications': row['mods']}
            ))

        # Convert RT violations to warnings
        for violation in rt_violations:
            warnings.append(ModificationWarning(
                warning_type='rt_ordering',
                message=f"Modification {violation['modification']} RT shift unexpected",
                details=violation
            ))

        statistics = {
            'total_compounds': len(parsed_df),
            'compounds_with_mods': int((parsed_df['n_mods'] > 0).sum()),
            'unique_modifications': len(set(m for mods in parsed_df['mods'] for m in mods)),
            'valid_combinations': len(valid_combinations),
            'missing_expected': len(missing_expected),
            'rt_violations': len(rt_violations)
        }

        logger.info(
            f"Rule 8 complete: {statistics['valid_combinations']} valid, "
            f"{len(warnings)} warnings"
        )

        return ModificationAnalysis(
            valid_combinations=valid_combinations,
            missing_expected=missing_expected,
            rt_ordering_violations=rt_violations,
            warnings=warnings,
            statistics=statistics
        )
```

### 5.2 Rule 9: Cross-Prefix Consistency Validation

**File**: `django_ganglioside/apps/analysis/services/cross_prefix_validator.py`

(Full implementation as shown in brainstorming - approximately 200 lines)

### 5.3 Rule 10: Confidence Scoring System

**File**: `django_ganglioside/apps/analysis/services/confidence_scorer.py`

(Full implementation as shown in brainstorming - approximately 300 lines)

---

## 6. Phase 3: Integration Architecture

### 6.1 Updated Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROPOSED 10-RULE PIPELINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUT: CSV with Name, RT, Volume, Log P, Anchor                           │
│    │                                                                        │
│    ▼                                                                        │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │ RULE 1: Bayesian Ridge Regression (with constraints)             │     │
│  │ • Log P-based RT prediction                                       │     │
│  │ • Automatic regularization (α, λ learned)                         │     │
│  │ • 95%/99% confidence intervals                                    │     │
│  │ • Chemically constrained coefficients                             │     │
│  └───────────────────────────────────────────────────────────────────┘     │
│    │                                                                        │
│    ▼                                                                        │
│  ┌───────────┐   ┌───────────┐   ┌───────────────────┐                    │
│  │ RULE 2-3  │──▶│  RULE 4   │──▶│      RULE 5       │                    │
│  │ Sugar &   │   │ O-Acetyl  │   │  Fragmentation    │                    │
│  │ Isomers   │   │ Validate  │   │   Detection       │                    │
│  └───────────┘   └───────────┘   └───────────────────┘                    │
│    │                                    │                                   │
│    ▼                                    ▼                                   │
│  ┌───────────┐   ┌───────────┐   ┌───────────────────┐                    │
│  │ RULE 6    │   │  RULE 7   │   │     RULE 8        │ [NEW]              │
│  │ Sugar-RT  │◀─▶│ Category  │◀─▶│  Modification     │                    │
│  │ Correlate │   │ Ordering  │   │  Stack Valid.     │                    │
│  └───────────┘   └───────────┘   └───────────────────┘                    │
│                        │                                                    │
│                        ▼                                                    │
│                  ┌───────────────────┐                                      │
│                  │     RULE 9        │ [NEW]                               │
│                  │  Cross-Prefix     │                                      │
│                  │  Consistency      │                                      │
│                  └───────────────────┘                                      │
│                        │                                                    │
│                        ▼                                                    │
│                  ┌───────────────────┐                                      │
│                  │     RULE 10       │ [NEW]                               │
│                  │   Confidence      │                                      │
│                  │    Scoring        │                                      │
│                  └───────────────────┘                                      │
│                        │                                                    │
│                        ▼                                                    │
│  OUTPUT: Compounds with confidence scores, CIs, validation flags           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Updated File Structure

```
django_ganglioside/apps/analysis/services/
├── __init__.py
├── ganglioside_processor_v3.py    # NEW: Updated orchestrator
├── bayesian_regression.py          # NEW: Bayesian RT predictor
├── constrained_regression.py       # NEW: Sign-constrained regression
├── modification_validator.py       # NEW: Rule 8
├── cross_prefix_validator.py       # NEW: Rule 9
├── confidence_scorer.py            # NEW: Rule 10
├── chemical_validation.py          # EXISTING: Rules 6-7
├── ganglioside_categorizer.py      # EXISTING
├── analysis_service.py             # UPDATED: Use v3 processor
├── export_service.py               # UPDATED: Export confidence scores
│
├── legacy/                         # DEPRECATED (keep for rollback)
│   ├── improved_regression.py
│   └── ganglioside_processor_v2.py
```

### 6.3 Processor V3 Orchestration

```python
# File: django_ganglioside/apps/analysis/services/ganglioside_processor_v3.py

class GangliosideProcessorV3:
    """
    Version 3 processor with enhanced prediction and validation.

    Changes from V2:
    - Bayesian Ridge regression with uncertainty
    - Constrained coefficient optimization
    - Rules 8-10 for comprehensive validation
    - Probabilistic confidence scoring
    """

    def __init__(self, config: ProcessorConfig = None):
        self.config = config or ProcessorConfig()

        # Initialize components
        self.bayesian_predictor = BayesianRTPredictor(
            r2_threshold=self.config.r2_threshold
        )
        self.constrained_regression = ConstrainedRTRegression(
            alpha=self.config.ridge_alpha,
            enforce_constraints=self.config.enforce_constraints
        )
        self.chemical_validator = ChemicalValidator()
        self.modification_validator = ModificationStackValidator()
        self.cross_prefix_validator = CrossPrefixValidator()
        self.confidence_scorer = ConfidenceScorer()
        self.categorizer = GangliosideCategorizer()

    def process_data(self, df: pd.DataFrame, data_type: str = "Porcine") -> Dict[str, Any]:
        """
        Process data through all 10 rules.
        """
        # ... preprocessing ...

        # Rule 1: Bayesian regression with constraints
        rule1_results = self._apply_rule1_bayesian_regression(df_processed)

        # Rules 2-5: Existing rules
        rule23_results = self._apply_rule2_3_sugar_count(df_processed, data_type)
        rule4_results = self._apply_rule4_oacetylation(df_processed)
        rule5_results = self._apply_rule5_rt_filtering(df_processed)

        # Rules 6-7: Chemical validation
        rule6_results = self._apply_rule6_sugar_rt_validation(df_processed)
        rule7_results = self._apply_rule7_category_ordering(df_processed)

        # Rule 8: Modification stacking (NEW)
        rule8_results = self._apply_rule8_modification_validation(df_processed)

        # Rule 9: Cross-prefix consistency (NEW)
        rule9_results = self._apply_rule9_cross_prefix_validation(df_processed)

        # Rule 10: Confidence scoring (NEW)
        rule10_results = self._apply_rule10_confidence_scoring(
            df_processed, rule1_results, rule6_results, rule7_results,
            rule8_results, rule9_results
        )

        return self._compile_results(...)
```

---

## 7. API Changes

### 7.1 New Response Fields

```json
{
  "success": true,
  "statistics": {
    "total_compounds": 150,
    "high_confidence": 120,
    "medium_confidence": 22,
    "low_confidence": 5,
    "uncertain": 3
  },
  "compounds": [
    {
      "name": "GD1(36:1;O2)",
      "rt_observed": 9.572,
      "rt_predicted": 9.58,
      "prediction_uncertainty": {
        "std_deviation": 0.15,
        "ci_95_lower": 9.29,
        "ci_95_upper": 9.87,
        "ci_99_lower": 9.19,
        "ci_99_upper": 9.97
      },
      "confidence": {
        "score": 0.92,
        "classification": "high",
        "components": {
          "regression_fit": 0.95,
          "chemical_consistency": 0.90,
          "cross_validation": 0.88,
          "data_quality": 0.85
        },
        "flags": []
      },
      "validation_status": {
        "rule1_passed": true,
        "rule4_oacetyl_valid": null,
        "rule8_mod_valid": true,
        "rule9_cross_prefix_valid": true
      }
    }
  ],
  "regression_analysis": {
    "GD1": {
      "r2": 0.85,
      "alpha_learned": 2.5,
      "lambda_learned": 15.3,
      "coefficients": {
        "Log P": 0.45,
        "a_component": 0.12
      },
      "constraints_active": [],
      "uncertainty_model": "bayesian_ridge"
    }
  },
  "validation_summary": {
    "rule8_mod_warnings": 2,
    "rule9_cross_prefix_violations": 1,
    "chemical_warnings": []
  }
}
```

### 7.2 New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analysis/analyze/v3/` | POST | Use v3 processor with new rules |
| `/api/analysis/confidence/{compound}/` | GET | Get detailed confidence breakdown |
| `/api/analysis/validation-report/` | GET | Get comprehensive validation report |

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/unit/test_bayesian_regression.py

class TestBayesianRTPredictor:
    def test_fit_returns_uncertainty(self):
        """Verify predictions include confidence intervals"""
        predictor = BayesianRTPredictor()
        result = predictor.fit(X_train, y_train, feature_names)

        assert result.training_predictions.std_deviation is not None
        assert len(result.training_predictions.ci_lower_95) == len(y_train)

    def test_small_sample_regularization(self):
        """Verify strong regularization for small samples"""
        predictor = BayesianRTPredictor()
        result = predictor.fit(X_small, y_small, feature_names)  # n=4

        # Lambda should be high (strong regularization)
        assert result.lambda_learned > 10.0

    def test_uncertainty_increases_with_extrapolation(self):
        """Verify uncertainty is higher for extrapolated points"""
        predictor = BayesianRTPredictor()
        predictor.fit(X_train, y_train, feature_names)

        # Point within training range
        pred_in = predictor.predict_with_uncertainty(X_in_range)
        # Point outside training range
        pred_out = predictor.predict_with_uncertainty(X_extrapolated)

        assert pred_out.std_deviation > pred_in.std_deviation


class TestConstrainedRegression:
    def test_positive_constraint_enforced(self):
        """Verify Log P coefficient is forced positive"""
        model = ConstrainedRTRegression(enforce_constraints=True)
        result = model.fit(X, y, ['Log P'])

        assert result.coefficients['Log P'] >= 0

    def test_negative_constraint_enforced(self):
        """Verify b_component coefficient is forced negative"""
        model = ConstrainedRTRegression(enforce_constraints=True)
        result = model.fit(X, y, ['b_component'])

        assert result.coefficients['b_component'] <= 0

    def test_violations_prevented_count(self):
        """Verify we track how many violations were prevented"""
        model = ConstrainedRTRegression(enforce_constraints=True)
        result = model.fit(X_bad_data, y_bad_data, feature_names)

        # Should report prevented violations
        assert result.constraint_violations_prevented >= 0


class TestConfidenceScorer:
    def test_high_residual_lowers_score(self):
        """Verify large residuals reduce confidence"""
        scorer = ConfidenceScorer()

        compound_good = {'std_residual': 0.5}
        compound_bad = {'std_residual': 3.0}

        score_good = scorer._regression_score(compound_good, {}, [])
        score_bad = scorer._regression_score(compound_bad, {}, [])

        assert score_good > score_bad

    def test_classification_thresholds(self):
        """Verify classification follows defined thresholds"""
        scorer = ConfidenceScorer()

        assert scorer.THRESHOLDS['high'] == 0.80
        assert scorer.THRESHOLDS['medium'] == 0.60
        assert scorer.THRESHOLDS['low'] == 0.40
```

### 8.2 Integration Tests

```python
# tests/integration/test_processor_v3.py

class TestProcessorV3Integration:
    def test_full_pipeline_with_sample_data(self):
        """End-to-end test with sample ganglioside data"""
        processor = GangliosideProcessorV3()
        results = processor.process_data(sample_df)

        assert results['success'] is True
        assert 'confidence' in results['compounds'][0]
        assert 'prediction_uncertainty' in results['compounds'][0]

    def test_backward_compatibility(self):
        """Verify v3 output contains all v2 fields"""
        v2_processor = GangliosideProcessorV2()
        v3_processor = GangliosideProcessorV3()

        v2_results = v2_processor.process_data(sample_df)
        v3_results = v3_processor.process_data(sample_df)

        # All v2 keys should exist in v3
        for key in v2_results.keys():
            assert key in v3_results
```

---

## 9. Migration Plan

### 9.1 Phase Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1** | Week 1-2 | Bayesian Ridge + Constrained Regression |
| **Phase 2** | Week 3-4 | Rules 8-10 implementation |
| **Phase 3** | Week 5 | Integration + API updates |
| **Phase 4** | Week 6 | Testing + Documentation |

### 9.2 Rollback Strategy

1. Keep `ganglioside_processor_v2.py` in `legacy/` folder
2. Add feature flag: `USE_V3_PROCESSOR = True/False`
3. API version parameter: `/api/analysis/analyze/?version=v2`

### 9.3 Data Migration

No database schema changes required. All enhancements are processing-side only.

---

## 10. Risk Assessment

### 10.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Constrained optimization doesn't converge | Low | Medium | Fallback to unconstrained with warning |
| Confidence scores too conservative | Medium | Low | Tune thresholds with real data |
| Performance regression | Low | Medium | Benchmark before/after |
| Bayesian Ridge slower than RidgeCV | Medium | Low | Profile and optimize if needed |

### 10.2 Scientific Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Constraints too strict for edge cases | Medium | Medium | Allow override per compound class |
| Confidence scoring unfairly penalizes valid compounds | Low | High | Extensive validation with expert review |
| Cross-prefix validation fails for unusual samples | Low | Low | Make Rule 9 optional/configurable |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **RT** | Retention Time - time compound elutes from chromatography column |
| **Log P** | Partition coefficient - measure of lipophilicity |
| **Bayesian Ridge** | Regression with Bayesian inference for regularization |
| **Confidence Interval** | Range within which true value is expected |
| **Constrained Optimization** | Optimization with boundary conditions |

---

## Appendix B: References

1. scikit-learn BayesianRidge documentation
2. LC-MS/MS ganglioside analysis methodologies
3. Reverse-phase chromatography principles

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-29 | Claude + User | Initial draft from brainstorming |

