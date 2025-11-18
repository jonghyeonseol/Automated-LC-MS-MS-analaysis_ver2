"""
Improved Regression Model for Ganglioside Analysis
Addresses overfitting issues with proper feature selection and validation
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional, List
from sklearn.linear_model import Ridge, RidgeCV, LinearRegression
from sklearn.model_selection import LeaveOneOut, KFold, cross_val_score
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class ImprovedRegressionModel:
    """
    Improved regression model that addresses overfitting issues:
    - Uses minimal, meaningful features
    - Implements cross-validation even for small samples
    - Uses regularization to prevent overfitting
    - Provides realistic R² thresholds
    """

    # Default configuration
    DEFAULT_MIN_SAMPLES = 3
    DEFAULT_MAX_FEATURES_RATIO = 0.3  # Max 30% features relative to samples
    DEFAULT_R2_THRESHOLD = 0.70  # Realistic threshold for LC-MS data
    DEFAULT_ALPHA_VALUES = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0]

    # Feature selection thresholds
    VARIANCE_THRESHOLD = 0.01  # Minimum variance for meaningful features
    CORRELATION_THRESHOLD = 0.95  # Maximum correlation to avoid multicollinearity
    MIN_FEATURES = 1  # Minimum number of features to use

    # Cross-validation configuration
    CV_THRESHOLD_SMALL = 5  # Use LOO CV if n_samples < this
    CV_THRESHOLD_MEDIUM = 10  # Use 3-fold CV if n_samples < this
    CV_FOLDS_SMALL = 3  # Number of folds for small samples
    CV_FOLDS_STANDARD = 5  # Number of folds for standard samples
    RANDOM_STATE = 42  # For reproducibility

    # Regularization
    ALPHA_EXACTLY_DETERMINED = 10.0  # Alpha for exactly determined systems

    # Overfitting detection
    OVERFITTING_R2_THRESHOLD = 0.98  # R² threshold for overfitting warning
    OVERFITTING_SAMPLE_THRESHOLD = 10  # Sample size threshold for overfitting check

    def __init__(
        self,
        min_samples: int = None,
        max_features_ratio: float = None,
        r2_threshold: float = None,
        alpha_values: List[float] = None
    ):
        """
        Initialize improved regression model.

        Args:
            min_samples: Minimum samples required for regression
            max_features_ratio: Maximum ratio of features to samples
            r2_threshold: Minimum R² for valid regression (0.70-0.85 realistic)
            alpha_values: Ridge regression alpha values for CV
        """
        self.min_samples = min_samples if min_samples is not None else self.DEFAULT_MIN_SAMPLES
        self.max_features_ratio = max_features_ratio if max_features_ratio is not None else self.DEFAULT_MAX_FEATURES_RATIO
        self.r2_threshold = r2_threshold if r2_threshold is not None else self.DEFAULT_R2_THRESHOLD
        self.alpha_values = alpha_values if alpha_values is not None else self.DEFAULT_ALPHA_VALUES

    def select_features(
        self,
        df: pd.DataFrame,
        prefix_group: str
    ) -> Tuple[List[str], Dict[str, float]]:
        """
        Select meaningful features based on variance and correlation.

        Args:
            df: DataFrame with compounds
            prefix_group: Prefix group being analyzed

        Returns:
            Tuple of (selected_features, feature_variances)
        """
        # Potential features in order of importance
        potential_features = [
            'Log P',           # Primary predictor
            'a_component',     # Carbon chain length
            'b_component',     # Unsaturation
        ]

        # Calculate variance for each feature
        feature_variances = {}
        selected_features = []

        for feature in potential_features:
            if feature in df.columns:
                variance = df[feature].var()
                feature_variances[feature] = variance

                # Only include features with meaningful variance
                if variance > self.VARIANCE_THRESHOLD:
                    selected_features.append(feature)

        # Check for multicollinearity
        if len(selected_features) >= 2:
            # Remove highly correlated features (keep only one)
            corr_matrix = df[selected_features].corr().abs()
            upper_tri = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )

            # Find features with correlation above threshold
            to_drop = [column for column in upper_tri.columns
                      if any(upper_tri[column] > self.CORRELATION_THRESHOLD)]

            # Keep Log P if it's being dropped (it's usually more meaningful)
            if 'Log P' in to_drop and 'a_component' in selected_features:
                to_drop.remove('Log P')
                to_drop.append('a_component')

            selected_features = [f for f in selected_features if f not in to_drop]

            logger.info(f"Dropped correlated features: {to_drop}")

        # Limit features based on sample size
        n_samples = len(df)
        max_features = max(self.MIN_FEATURES, int(n_samples * self.max_features_ratio))

        if len(selected_features) > max_features:
            # Keep only the most important features
            selected_features = selected_features[:max_features]
            logger.warning(
                f"Limited features from {len(potential_features)} to {max_features} "
                f"due to sample size ({n_samples} samples)"
            )

        # Ensure we have at least one feature
        if not selected_features and 'Log P' in df.columns:
            selected_features = ['Log P']

        logger.info(
            f"Selected features for {prefix_group}: {selected_features} "
            f"(variances: {feature_variances})"
        )

        return selected_features, feature_variances

    def fit_with_validation(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_samples: int
    ) -> Tuple[Any, Dict[str, float]]:
        """
        Fit regression model with appropriate validation strategy.

        Args:
            X: Feature matrix
            y: Target values
            n_samples: Number of samples

        Returns:
            Tuple of (fitted_model, metrics)
        """
        metrics = {}

        if n_samples < self.CV_THRESHOLD_SMALL:
            # Too few samples for cross-validation - use Leave-One-Out
            logger.warning(f"Only {n_samples} samples - using Leave-One-Out CV")

            if n_samples == X.shape[1]:
                # Exactly determined system - use strong regularization
                model = Ridge(alpha=self.ALPHA_EXACTLY_DETERMINED)
                model.fit(X, y)
                y_pred = model.predict(X)
                metrics['cv_method'] = 'none (exactly determined)'
                metrics['warning'] = 'System is exactly determined - results unreliable'

            else:
                # Use LOO cross-validation
                cv = LeaveOneOut()
                model = RidgeCV(alphas=self.alpha_values, cv=cv)
                model.fit(X, y)

                # Calculate LOO predictions for metrics
                y_pred = np.zeros(n_samples)
                for i, (train_idx, test_idx) in enumerate(cv.split(X)):
                    temp_model = Ridge(alpha=model.alpha_)
                    temp_model.fit(X[train_idx], y[train_idx])
                    y_pred[test_idx] = temp_model.predict(X[test_idx])

                metrics['cv_method'] = 'leave-one-out'
                metrics['selected_alpha'] = model.alpha_

        elif n_samples < self.CV_THRESHOLD_MEDIUM:
            # Small sample - use 3-fold CV
            logger.info(f"{n_samples} samples - using {self.CV_FOLDS_SMALL}-fold CV")
            cv = KFold(n_splits=self.CV_FOLDS_SMALL, shuffle=True, random_state=self.RANDOM_STATE)
            model = RidgeCV(alphas=self.alpha_values, cv=cv)
            model.fit(X, y)
            y_pred = model.predict(X)

            metrics['cv_method'] = f'{self.CV_FOLDS_SMALL}-fold'
            metrics['selected_alpha'] = model.alpha_

        else:
            # Adequate samples - use 5-fold CV
            logger.info(f"{n_samples} samples - using {self.CV_FOLDS_STANDARD}-fold CV")
            cv = KFold(n_splits=self.CV_FOLDS_STANDARD, shuffle=True, random_state=self.RANDOM_STATE)
            model = RidgeCV(alphas=self.alpha_values, cv=cv)
            model.fit(X, y)
            y_pred = model.predict(X)

            metrics['cv_method'] = f'{self.CV_FOLDS_STANDARD}-fold'
            metrics['selected_alpha'] = model.alpha_

        # Calculate metrics
        metrics['r2'] = r2_score(y, y_pred)
        metrics['rmse'] = np.sqrt(mean_squared_error(y, y_pred))
        metrics['n_samples'] = n_samples
        metrics['n_features'] = X.shape[1]

        # Adjusted R² (penalizes for number of features)
        if n_samples > X.shape[1] + 1:
            metrics['adjusted_r2'] = 1 - (1 - metrics['r2']) * \
                                     (n_samples - 1) / (n_samples - X.shape[1] - 1)
        else:
            metrics['adjusted_r2'] = None

        # Warning if R² is suspiciously high
        if metrics['r2'] > self.OVERFITTING_R2_THRESHOLD and n_samples < self.OVERFITTING_SAMPLE_THRESHOLD:
            metrics['warning'] = f"R²={metrics['r2']:.3f} with only {n_samples} samples suggests overfitting"
            logger.warning(metrics['warning'])

        return model, metrics

    def fit_regression(
        self,
        df: pd.DataFrame,
        prefix_group: str,
        anchor_only: bool = True
    ) -> Dict[str, Any]:
        """
        Fit improved regression model for a prefix group.

        Args:
            df: DataFrame with compounds for this prefix
            prefix_group: Name of prefix group
            anchor_only: Whether to use only anchor compounds for training

        Returns:
            Dictionary with regression results and metrics
        """
        # Filter to anchor compounds if specified
        if anchor_only:
            train_df = df[df['Anchor'] == 'T'].copy()
        else:
            train_df = df.copy()

        n_samples = len(train_df)

        # Check minimum samples
        if n_samples < self.min_samples:
            return {
                'success': False,
                'reason': f'Insufficient samples ({n_samples} < {self.min_samples})',
                'n_samples': n_samples
            }

        # Select features
        selected_features, feature_variances = self.select_features(train_df, prefix_group)

        if not selected_features:
            return {
                'success': False,
                'reason': 'No features with sufficient variance',
                'feature_variances': feature_variances
            }

        # Prepare data
        X = train_df[selected_features].values
        y = train_df['RT'].values

        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Fit model with validation
        model, metrics = self.fit_with_validation(X_scaled, y, n_samples)

        # Check if model meets threshold
        if metrics['r2'] < self.r2_threshold:
            return {
                'success': False,
                'reason': f"R² ({metrics['r2']:.3f}) below threshold ({self.r2_threshold})",
                'metrics': metrics,
                'features': selected_features
            }

        # Generate predictions for all compounds
        all_X = df[selected_features].values
        all_X_scaled = scaler.transform(all_X)
        predictions = model.predict(all_X_scaled)
        residuals = df['RT'].values - predictions

        # Calculate standardized residuals
        residual_std = np.std(residuals)
        if residual_std > 0:
            standardized_residuals = residuals / residual_std
        else:
            standardized_residuals = np.zeros_like(residuals)

        # Create equation string
        equation_parts = [f"{model.intercept_:.4f}"]
        for i, (feature, coef) in enumerate(zip(selected_features, model.coef_)):
            equation_parts.append(f"{coef:.4f}*{feature}")
        equation = "RT = " + " + ".join(equation_parts)

        return {
            'success': True,
            'prefix_group': prefix_group,
            'model': model,
            'scaler': scaler,
            'features': selected_features,
            'feature_variances': feature_variances,
            'metrics': metrics,
            'equation': equation,
            'coefficients': {
                'intercept': float(model.intercept_),
                'features': {f: float(c) for f, c in zip(selected_features, model.coef_)}
            },
            'predictions': predictions,
            'residuals': residuals,
            'standardized_residuals': standardized_residuals,
            'residual_std': residual_std
        }

    def validate_model(
        self,
        model_result: Dict[str, Any],
        test_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Validate model on test set (non-anchor compounds).

        Args:
            model_result: Result from fit_regression
            test_df: DataFrame with test compounds

        Returns:
            Validation metrics
        """
        if not model_result['success']:
            return {'success': False, 'reason': 'Model fitting failed'}

        model = model_result['model']
        scaler = model_result['scaler']
        features = model_result['features']

        # Prepare test data
        X_test = test_df[features].values
        X_test_scaled = scaler.transform(X_test)
        y_test = test_df['RT'].values

        # Predict
        y_pred = model.predict(X_test_scaled)

        # Calculate metrics
        test_r2 = r2_score(y_test, y_pred)
        test_rmse = np.sqrt(mean_squared_error(y_test, y_pred))

        return {
            'success': True,
            'test_r2': test_r2,
            'test_rmse': test_rmse,
            'n_test_samples': len(test_df),
            'overfit_indicator': model_result['metrics']['r2'] - test_r2
        }