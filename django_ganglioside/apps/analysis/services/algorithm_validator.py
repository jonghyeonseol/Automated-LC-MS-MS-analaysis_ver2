"""
Algorithm Validation Module
Validates the 5-rule algorithm performance using MS/MS verified anchor compounds
Provides cross-validation, performance metrics, and learning capabilities
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from sklearn.model_selection import KFold, LeaveOneOut
from sklearn.metrics import (
    r2_score, mean_squared_error, mean_absolute_error,
    accuracy_score, precision_score, recall_score, f1_score
)
import logging

from .ganglioside_processor_v2 import GangliosideProcessorV2

logger = logging.getLogger(__name__)


@dataclass
class ValidationMetrics:
    """Container for validation metrics"""
    # Regression metrics
    r2_train: float
    r2_test: float
    rmse_train: float
    rmse_test: float
    mae_train: float
    mae_test: float

    # Classification metrics (valid vs outlier)
    accuracy: float
    precision: float
    recall: float
    f1: float

    # Confusion matrix
    true_positives: int  # Correctly identified valid compounds
    false_positives: int  # Valid compounds marked as outliers
    true_negatives: int  # Correctly identified outliers
    false_negatives: int  # Outliers marked as valid

    # Sample sizes
    n_train: int
    n_test: int
    n_anchors_train: int
    n_anchors_test: int

    # Additional info
    overfitting_score: float  # r2_train - r2_test (high = overfitting)
    generalization_ratio: float  # r2_test / r2_train (close to 1 = good)


class AlgorithmValidator:
    """
    Validates ganglioside analysis algorithm performance

    Features:
    - Cross-validation with multiple folds
    - Leave-one-out validation for small datasets
    - Train/test split validation
    - Performance metrics calculation
    - Overfitting detection
    - Anchor compound learning effectiveness
    """

    def __init__(self, processor: GangliosideProcessorV2 = None):
        self.processor = processor or GangliosideProcessorV2()
        self.validation_results = []

    def validate_with_kfold(
        self,
        df: pd.DataFrame,
        n_splits: int = 5,
        data_type: str = 'Porcine',
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        K-Fold cross-validation

        Args:
            df: DataFrame with compounds (must have 'Anchor' column)
            n_splits: Number of folds
            data_type: Data type for analysis
            random_state: Random seed

        Returns:
            Validation results with metrics per fold
        """
        logger.info(f"Starting {n_splits}-fold cross-validation on {len(df)} compounds")

        # Separate anchors and non-anchors
        anchors = df[df['Anchor'] == 'T'].copy()
        non_anchors = df[df['Anchor'] == 'F'].copy()

        if len(anchors) < n_splits:
            logger.warning(
                f"Only {len(anchors)} anchors, using Leave-One-Out instead of {n_splits}-fold"
            )
            return self.validate_leave_one_out(df, data_type)

        kfold = KFold(n_splits=n_splits, shuffle=True, random_state=random_state)
        fold_results = []

        for fold_idx, (train_idx, test_idx) in enumerate(kfold.split(anchors), 1):
            logger.info(f"Processing fold {fold_idx}/{n_splits}")

            # Split anchors into train/test
            anchors_train = anchors.iloc[train_idx].copy()
            anchors_test = anchors.iloc[test_idx].copy()

            # Create training set (train anchors + all non-anchors marked as test)
            train_df = pd.concat([anchors_train, non_anchors]).reset_index(drop=True)

            # Create test set (test anchors only for validation)
            test_df = anchors_test.copy()

            # Run analysis on training set
            train_results = self.processor.process_data(train_df, data_type=data_type)

            # Validate on test set
            metrics = self._calculate_fold_metrics(
                train_df=train_df,
                test_df=test_df,
                train_results=train_results,
                fold_idx=fold_idx
            )

            fold_results.append({
                'fold': fold_idx,
                'metrics': metrics,
                'train_size': len(train_df),
                'test_size': len(test_df),
                'n_anchors_train': len(anchors_train),
                'n_anchors_test': len(anchors_test)
            })

        # Aggregate results
        return self._aggregate_fold_results(fold_results, n_splits)

    def validate_leave_one_out(
        self,
        df: pd.DataFrame,
        data_type: str = 'Porcine'
    ) -> Dict[str, Any]:
        """
        Leave-One-Out cross-validation
        Each anchor compound is tested individually

        Best for small datasets with few anchor compounds
        """
        anchors = df[df['Anchor'] == 'T'].copy()
        non_anchors = df[df['Anchor'] == 'F'].copy()

        n_anchors = len(anchors)
        logger.info(f"Starting Leave-One-Out validation on {n_anchors} anchor compounds")

        if n_anchors < 2:
            raise ValueError("Need at least 2 anchor compounds for LOO validation")

        loo_results = []
        predictions = []
        actuals = []

        for idx in range(n_anchors):
            # Leave one out
            test_anchor = anchors.iloc[[idx]].copy()
            train_anchors = anchors.drop(anchors.index[idx]).copy()

            # Training set
            train_df = pd.concat([train_anchors, non_anchors]).reset_index(drop=True)

            # Run analysis
            train_results = self.processor.process_data(train_df, data_type=data_type)

            # Predict test anchor
            test_compound_name = test_anchor.iloc[0]['Name']
            test_rt = test_anchor.iloc[0]['RT']
            test_log_p = test_anchor.iloc[0]['Log P']

            # Find regression model for this compound's prefix
            prefix = self.processor._preprocess_data(test_anchor).iloc[0]['prefix']

            predicted_rt = None
            if prefix in train_results.get('regression_analysis', {}):
                model_info = train_results['regression_analysis'][prefix]
                slope = model_info.get('slope', 0)
                intercept = model_info.get('intercept', 0)
                predicted_rt = slope * test_log_p + intercept

            if predicted_rt is not None:
                predictions.append(predicted_rt)
                actuals.append(test_rt)
                residual = test_rt - predicted_rt

                loo_results.append({
                    'compound': test_compound_name,
                    'actual_rt': test_rt,
                    'predicted_rt': predicted_rt,
                    'residual': residual,
                    'abs_error': abs(residual),
                    'squared_error': residual ** 2
                })

        if not predictions:
            return {'error': 'No predictions could be made'}

        # Calculate LOO metrics
        predictions = np.array(predictions)
        actuals = np.array(actuals)

        return {
            'method': 'Leave-One-Out',
            'n_compounds': n_anchors,
            'metrics': {
                'r2': r2_score(actuals, predictions),
                'rmse': np.sqrt(mean_squared_error(actuals, predictions)),
                'mae': mean_absolute_error(actuals, predictions),
                'max_error': np.max(np.abs(actuals - predictions)),
                'mean_residual': np.mean(actuals - predictions),
                'std_residual': np.std(actuals - predictions)
            },
            'predictions': loo_results,
            'summary': {
                'best_prediction': min(loo_results, key=lambda x: x['abs_error']),
                'worst_prediction': max(loo_results, key=lambda x: x['abs_error'])
            }
        }

    def validate_train_test_split(
        self,
        df: pd.DataFrame,
        test_size: float = 0.2,
        data_type: str = 'Porcine',
        random_state: int = 42
    ) -> Dict[str, Any]:
        """
        Single train/test split validation

        Args:
            df: Full dataset
            test_size: Fraction of anchors to use for testing (0.0-1.0)
            data_type: Data type
            random_state: Random seed
        """
        anchors = df[df['Anchor'] == 'T'].copy()
        non_anchors = df[df['Anchor'] == 'F'].copy()

        n_test = max(1, int(len(anchors) * test_size))

        # Random split
        np.random.seed(random_state)
        test_indices = np.random.choice(anchors.index, size=n_test, replace=False)

        anchors_test = anchors.loc[test_indices].copy()
        anchors_train = anchors.drop(test_indices).copy()

        # Create datasets
        train_df = pd.concat([anchors_train, non_anchors]).reset_index(drop=True)
        test_df = anchors_test.copy()

        # Run analysis
        train_results = self.processor.process_data(train_df, data_type=data_type)

        # Validate
        metrics = self._calculate_fold_metrics(
            train_df=train_df,
            test_df=test_df,
            train_results=train_results,
            fold_idx=1
        )

        return {
            'method': 'Train/Test Split',
            'test_size': test_size,
            'n_train': len(train_df),
            'n_test': len(test_df),
            'n_anchors_train': len(anchors_train),
            'n_anchors_test': len(anchors_test),
            'metrics': metrics,
            'train_results': train_results
        }

    def _calculate_fold_metrics(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        train_results: Dict[str, Any],
        fold_idx: int
    ) -> ValidationMetrics:
        """Calculate validation metrics for a single fold"""

        # Training metrics
        train_compounds = train_results.get('valid_compounds', [])
        train_anchors = [c for c in train_compounds if c.get('Anchor') == 'T']

        if train_anchors:
            train_actuals = [c['RT'] for c in train_anchors]
            train_predictions = [c.get('predicted_rt', c['RT']) for c in train_anchors]
            r2_train = r2_score(train_actuals, train_predictions)
            rmse_train = np.sqrt(mean_squared_error(train_actuals, train_predictions))
            mae_train = mean_absolute_error(train_actuals, train_predictions)
        else:
            r2_train = rmse_train = mae_train = 0.0

        # Test metrics - predict on held-out test set
        test_actuals = []
        test_predictions = []

        for _, test_row in test_df.iterrows():
            test_rt = test_row['RT']
            test_log_p = test_row['Log P']
            prefix = self.processor._preprocess_data(
                pd.DataFrame([test_row])
            ).iloc[0]['prefix']

            if prefix in train_results.get('regression_analysis', {}):
                model_info = train_results['regression_analysis'][prefix]

                # Get coefficients
                if 'coefficients' in model_info:
                    # Multiple regression
                    intercept = model_info.get('intercept', 0)
                    # For now, use simple Log P prediction
                    slope = model_info.get('slope', model_info['coefficients'].get('Log P', 0))
                    predicted_rt = slope * test_log_p + intercept
                else:
                    # Simple regression
                    slope = model_info.get('slope', 0)
                    intercept = model_info.get('intercept', 0)
                    predicted_rt = slope * test_log_p + intercept

                test_actuals.append(test_rt)
                test_predictions.append(predicted_rt)

        if test_actuals:
            r2_test = r2_score(test_actuals, test_predictions)
            rmse_test = np.sqrt(mean_squared_error(test_actuals, test_predictions))
            mae_test = mean_absolute_error(test_actuals, test_predictions)
        else:
            r2_test = rmse_test = mae_test = 0.0

        # Classification metrics (valid vs outlier detection)
        total_compounds = len(train_results.get('valid_compounds', [])) + len(train_results.get('outliers', []))
        true_positives = len(train_results.get('valid_compounds', []))
        false_positives = len([o for o in train_results.get('outliers', []) if o.get('Anchor') == 'T'])

        accuracy = true_positives / total_compounds if total_compounds > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        # Overfitting detection
        overfitting_score = r2_train - r2_test
        generalization_ratio = r2_test / r2_train if r2_train > 0 else 0

        return ValidationMetrics(
            r2_train=r2_train,
            r2_test=r2_test,
            rmse_train=rmse_train,
            rmse_test=rmse_test,
            mae_train=mae_train,
            mae_test=mae_test,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1=f1,
            true_positives=true_positives,
            false_positives=false_positives,
            true_negatives=0,  # Need ground truth for this
            false_negatives=0,
            n_train=len(train_df),
            n_test=len(test_df),
            n_anchors_train=len(train_df[train_df['Anchor'] == 'T']),
            n_anchors_test=len(test_df[test_df['Anchor'] == 'T']),
            overfitting_score=overfitting_score,
            generalization_ratio=generalization_ratio
        )

    def _aggregate_fold_results(self, fold_results: List[Dict], n_splits: int) -> Dict[str, Any]:
        """Aggregate metrics across all folds"""

        # Extract metrics from each fold
        r2_train_scores = [f['metrics'].r2_train for f in fold_results]
        r2_test_scores = [f['metrics'].r2_test for f in fold_results]
        rmse_test_scores = [f['metrics'].rmse_test for f in fold_results]
        mae_test_scores = [f['metrics'].mae_test for f in fold_results]
        overfitting_scores = [f['metrics'].overfitting_score for f in fold_results]

        return {
            'method': f'{n_splits}-Fold Cross-Validation',
            'n_folds': n_splits,
            'aggregated_metrics': {
                'mean_r2_train': np.mean(r2_train_scores),
                'mean_r2_test': np.mean(r2_test_scores),
                'std_r2_test': np.std(r2_test_scores),
                'mean_rmse_test': np.mean(rmse_test_scores),
                'std_rmse_test': np.std(rmse_test_scores),
                'mean_mae_test': np.mean(mae_test_scores),
                'mean_overfitting_score': np.mean(overfitting_scores),
                'max_overfitting_score': np.max(overfitting_scores),
            },
            'per_fold_results': fold_results,
            'interpretation': self._interpret_results(
                np.mean(r2_test_scores),
                np.std(r2_test_scores),
                np.mean(overfitting_scores)
            )
        }

    def _interpret_results(self, mean_r2: float, std_r2: float, mean_overfitting: float) -> Dict[str, str]:
        """Provide human-readable interpretation of results"""

        interpretation = {}

        # R² interpretation
        if mean_r2 >= 0.90:
            interpretation['r2_quality'] = 'Excellent - Model explains >90% of variance'
        elif mean_r2 >= 0.75:
            interpretation['r2_quality'] = 'Good - Model has strong predictive power'
        elif mean_r2 >= 0.50:
            interpretation['r2_quality'] = 'Moderate - Model has some predictive power'
        else:
            interpretation['r2_quality'] = 'Poor - Model has weak predictive power'

        # Consistency interpretation
        if std_r2 < 0.05:
            interpretation['consistency'] = 'Very consistent across folds'
        elif std_r2 < 0.10:
            interpretation['consistency'] = 'Reasonably consistent'
        else:
            interpretation['consistency'] = 'High variance - results depend on data split'

        # Overfitting interpretation
        if mean_overfitting < 0.05:
            interpretation['overfitting'] = 'No significant overfitting detected'
        elif mean_overfitting < 0.15:
            interpretation['overfitting'] = 'Mild overfitting - monitor with more data'
        else:
            interpretation['overfitting'] = 'Significant overfitting - model memorizing training data'

        # Overall recommendation
        if mean_r2 >= 0.75 and mean_overfitting < 0.10:
            interpretation['recommendation'] = 'Algorithm performs well - ready for production use'
        elif mean_r2 >= 0.50:
            interpretation['recommendation'] = 'Algorithm has potential - consider tuning parameters'
        else:
            interpretation['recommendation'] = 'Algorithm needs improvement - review feature engineering'

        return interpretation
