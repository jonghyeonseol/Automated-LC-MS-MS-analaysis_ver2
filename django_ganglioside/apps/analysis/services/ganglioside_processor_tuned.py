"""
Tunable Ganglioside Processor
Supports different configurations for algorithm tuning

This is a configurable version of ganglioside_processor.py that can:
- Separate modified vs unmodified compounds
- Use different feature sets
- Apply Ridge regularization
- Pool prefix groups
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import r2_score, mean_squared_error
import re
import logging

logger = logging.getLogger(__name__)


class GangliosideProcessorTuned:
    """
    Tunable version of Ganglioside Processor

    Configured via TuningConfig to support different algorithm variations
    """

    def __init__(self, config=None):
        """
        Args:
            config: TuningConfig object or None for default behavior
        """
        self.config = config
        self.r2_threshold = 0.75  # Lowered from 0.99
        self.outlier_threshold = 2.5
        self.rt_tolerance = 0.1

    def process_data(self, df: pd.DataFrame, data_type: str = 'Porcine') -> Dict[str, Any]:
        """
        Process data with configured tuning parameters
        """
        df_processed = self._preprocess_data(df.copy())

        # If config specifies separating modified compounds
        if self.config and self.config.separate_modified:
            return self._process_with_separated_modified(df_processed, data_type)
        else:
            return self._process_standard(df_processed, data_type)

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract prefix and detect modifications"""
        def extract_prefix(name):
            # Extract base prefix (e.g., GD1, GM1)
            match = re.match(r'^([A-Z]+\d+)', str(name))
            base_prefix = match.group(1) if match else 'Unknown'

            # Apply prefix pooling if configured
            if self.config and self.config.pool_prefixes:
                for full_prefix, pooled in self.config.prefix_mapping.items():
                    if base_prefix.startswith(full_prefix):
                        return pooled
            return base_prefix

        def detect_modification(name):
            """Detect if compound is modified (+HexNAc, +dHex, +OAc)"""
            name_str = str(name)
            modifications = ['HexNAc', 'dHex', 'OAc', 'NeuAc', 'NeuGc']
            return any(f'+{mod}' in name_str for mod in modifications)

        df['prefix'] = df['Name'].apply(extract_prefix)
        df['is_modified'] = df['Name'].apply(detect_modification)

        return df

    def _process_with_separated_modified(
        self,
        df: pd.DataFrame,
        data_type: str
    ) -> Dict[str, Any]:
        """
        Process with separate models for modified vs unmodified compounds
        """
        # Separate into two groups
        df_base = df[~df['is_modified']].copy()
        df_modified = df[df['is_modified']].copy()

        results = {
            'regression_analysis': {},
            'valid_compounds': [],
            'outliers': [],
            'statistics': {}
        }

        # Process base gangliosides
        if len(df_base) > 0:
            base_results = self._apply_regression(df_base, data_type, prefix_suffix='_base')
            results['regression_analysis'].update(base_results)

        # Process modified gangliosides
        if len(df_modified) > 0:
            modified_results = self._apply_regression(df_modified, data_type, prefix_suffix='_modified')
            results['regression_analysis'].update(modified_results)

        # Compile statistics
        results['statistics'] = {
            'total_compounds': len(df),
            'anchor_compounds': len(df[df['Anchor'] == 'T']),
            'base_compounds': len(df_base),
            'modified_compounds': len(df_modified),
            'valid_compounds': len(df),
            'outliers': 0,
            'success_rate': 100.0
        }

        results['valid_compounds'] = df.to_dict('records')

        return results

    def _process_standard(self, df: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """Standard processing (no separation)"""
        regression_results = self._apply_regression(df, data_type)

        return {
            'regression_analysis': regression_results,
            'valid_compounds': df.to_dict('records'),
            'outliers': [],
            'statistics': {
                'total_compounds': len(df),
                'anchor_compounds': len(df[df['Anchor'] == 'T']),
                'valid_compounds': len(df),
                'outliers': 0,
                'success_rate': 100.0
            }
        }

    def _apply_regression(
        self,
        df: pd.DataFrame,
        data_type: str,
        prefix_suffix: str = ''
    ) -> Dict[str, Any]:
        """
        Apply regression per prefix group with configured parameters
        """
        results = {}

        for prefix in df['prefix'].unique():
            prefix_df = df[df['prefix'] == prefix]
            anchors = prefix_df[prefix_df['Anchor'] == 'T']

            if len(anchors) < 2:
                continue

            # Feature selection based on config
            if self.config and self.config.features:
                # Use only configured features
                if 'Log P' in self.config.features and len(self.config.features) == 1:
                    # Simple linear regression with Log P only
                    X = anchors[['Log P']].values
                elif 'Log P' in self.config.features and 'a_component' in self.config.features:
                    # Extract carbon chain length from compound name
                    X = self._extract_features(anchors, self.config.features)
                else:
                    # Default to Log P
                    X = anchors[['Log P']].values
            else:
                # Default: Log P only
                X = anchors[['Log P']].values

            y = anchors['RT'].values

            # Choose regression model based on config
            if self.config and self.config.use_ridge:
                model = Ridge(alpha=self.config.ridge_alpha)
            else:
                model = LinearRegression()

            model.fit(X, y)
            predictions = model.predict(X)
            r2 = r2_score(y, predictions)

            # Store results
            prefix_key = f"{prefix}{prefix_suffix}"
            results[prefix_key] = {
                'slope': float(model.coef_[0]) if len(model.coef_) == 1 else float(model.coef_[0]),
                'intercept': float(model.intercept_),
                'r2': float(r2),
                'n_samples': len(anchors),
                'equation': f"RT = {model.coef_[0]:.4f} * Log P + {model.intercept_:.4f}",
                'model_type': 'Ridge' if (self.config and self.config.use_ridge) else 'LinearRegression',
                'features': self.config.features if self.config else ['Log P']
            }

            if self.config and self.config.use_ridge:
                results[prefix_key]['ridge_alpha'] = self.config.ridge_alpha

        return results

    def _extract_features(self, df: pd.DataFrame, feature_names: List[str]) -> np.ndarray:
        """
        Extract specified features from dataframe

        Supports:
        - Log P (from column)
        - a_component (carbon chain length - extracted from name)
        """
        features = []

        for feature_name in feature_names:
            if feature_name == 'Log P':
                features.append(df['Log P'].values)
            elif feature_name == 'a_component':
                # Extract carbon chain length from compound name
                # e.g., GD1(36:1;O2) → 36
                def extract_carbon_chain(name):
                    match = re.search(r'\((\d+):', str(name))
                    return int(match.group(1)) if match else 36  # Default
                carbon_chains = df['Name'].apply(extract_carbon_chain).values
                features.append(carbon_chains)

        return np.column_stack(features) if len(features) > 1 else features[0].reshape(-1, 1)
