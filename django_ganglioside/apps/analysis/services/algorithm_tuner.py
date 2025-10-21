"""
Algorithm Auto-Tuner with ALCOA++ Compliance
Iteratively improves ganglioside analysis algorithm to achieve R² ≥ 0.90

Features:
- Automatic detection and separation of modified compounds
- Feature reduction to prevent overfitting
- Ridge regularization tuning
- Prefix group pooling
- Full ALCOA++ audit trail for each iteration
- Validation after each tuning step

Usage:
    tuner = AlgorithmTuner()
    best_config = tuner.tune_iteratively(df, target_r2=0.90, max_iterations=5)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import re
import logging
import json
from pathlib import Path
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class TuningConfig:
    """Configuration for a single tuning iteration"""
    version: str  # e.g., "v1.1_separated"
    description: str
    separate_modified: bool = False
    features: List[str] = None  # Default to all features
    use_ridge: bool = False
    ridge_alpha: float = 1.0
    pool_prefixes: bool = False
    prefix_mapping: Dict[str, str] = None

    def __post_init__(self):
        if self.features is None:
            # Default: all 9 features
            self.features = [
                "Log P", "a_component", "b_component", "c_component",
                "sugar_count", "oacetylation", "is_modified", "chain_length", "unsaturation"
            ]
        if self.prefix_mapping is None:
            self.prefix_mapping = {}


@dataclass
class TuningResult:
    """Results from a single tuning iteration"""
    version: str
    timestamp: str
    config: TuningConfig
    validation_results: Dict[str, Any]
    r2_loo: float
    r2_kfold: float
    rmse_loo: float
    overfitting_score: float
    success: bool
    trace_location: str
    checksum: str
    notes: str = ""


class AlgorithmTuner:
    """
    Auto-tunes ganglioside analysis algorithm to achieve target R² performance

    Implements 4 tuning strategies:
    1. Separate modified compounds (target R² ≥ 0.85)
    2. Reduce features (target R² ≥ 0.88, overfitting < 0.15)
    3. Ridge regularization (target R² ≥ 0.90, overfitting < 0.10)
    4. Pool prefix groups (target R² ≥ 0.90)
    """

    def __init__(self, trace_dir: str = "trace/algorithm_versions"):
        self.trace_dir = Path(trace_dir)
        self.tuning_history: List[TuningResult] = []
        self.best_config: Optional[TuningConfig] = None
        self.best_r2: float = 0.0

    def tune_iteratively(
        self,
        df: pd.DataFrame,
        target_r2: float = 0.90,
        max_iterations: int = 5,
        data_type: str = 'Porcine'
    ) -> Tuple[TuningConfig, TuningResult]:
        """
        Iteratively tune algorithm until target R² is achieved

        Args:
            df: Dataset with anchor compounds
            target_r2: Target R² score (default 0.90)
            max_iterations: Maximum tuning iterations
            data_type: Data type for analysis

        Returns:
            (best_config, best_result) tuple
        """
        logger.info(f"Starting auto-tuning with target R² = {target_r2}")
        logger.info(f"Dataset: {len(df)} compounds ({len(df[df['Anchor']=='T'])} anchors)")

        # Baseline performance (already validated)
        print("\n" + "="*80)
        print("ALGORITHM AUTO-TUNING")
        print("="*80)
        print(f"Target: R² ≥ {target_r2}")
        print(f"Max Iterations: {max_iterations}")
        print(f"Dataset: {len(df)} compounds, {len(df[df['Anchor']=='T'])} anchors")
        print("")

        # Iteration 1: Separate modified compounds
        result1 = self._iteration1_separate_modified(df, data_type)
        self.tuning_history.append(result1)
        self._print_result(1, result1, target_r2)

        if result1.r2_kfold >= target_r2 and result1.overfitting_score < 0.10:
            return result1.config, result1

        # Iteration 2: Reduce features
        result2 = self._iteration2_reduce_features(df, data_type, result1.config)
        self.tuning_history.append(result2)
        self._print_result(2, result2, target_r2)

        if result2.r2_kfold >= target_r2 and result2.overfitting_score < 0.10:
            return result2.config, result2

        # Iteration 3: Ridge regularization
        result3 = self._iteration3_ridge_regularization(df, data_type, result2.config)
        self.tuning_history.append(result3)
        self._print_result(3, result3, target_r2)

        if result3.r2_kfold >= target_r2 and result3.overfitting_score < 0.10:
            return result3.config, result3

        # Iteration 4: Pool prefixes
        if max_iterations >= 4:
            result4 = self._iteration4_pool_prefixes(df, data_type, result3.config)
            self.tuning_history.append(result4)
            self._print_result(4, result4, target_r2)

            if result4.r2_kfold >= target_r2 and result4.overfitting_score < 0.10:
                return result4.config, result4

        # Return best result even if target not met
        best_result = max(self.tuning_history, key=lambda x: x.r2_kfold)
        self.best_config = best_result.config
        self.best_r2 = best_result.r2_kfold

        print("\n" + "="*80)
        print("TUNING COMPLETE")
        print("="*80)
        if best_result.r2_kfold >= target_r2:
            print(f"✅ SUCCESS: Achieved R² = {best_result.r2_kfold:.4f} (≥ {target_r2})")
        else:
            print(f"⚠️  PARTIAL: Best R² = {best_result.r2_kfold:.4f} (target: {target_r2})")
        print(f"Best configuration: {best_result.version}")
        print("")

        return best_result.config, best_result

    def _iteration1_separate_modified(
        self,
        df: pd.DataFrame,
        data_type: str
    ) -> TuningResult:
        """
        Iteration 1: Separate modified vs unmodified compounds

        Modified compounds (+HexNAc, +dHex, +OAc) have different Log P characteristics
        """
        config = TuningConfig(
            version="v1.1_separated",
            description="Separate modified (+HexNAc, +dHex, +OAc) from base gangliosides",
            separate_modified=True,
            features=["Log P"]  # Start simple
        )

        # Run validation with this config
        validation_results = self._validate_with_config(df, config, data_type)

        # Extract metrics
        r2_loo = validation_results['loo']['metrics']['r2']
        r2_kfold = validation_results['kfold']['aggregated_metrics']['mean_r2_test']
        rmse_loo = validation_results['loo']['metrics']['rmse']
        overfitting = validation_results['kfold']['aggregated_metrics']['mean_overfitting_score']

        # Archive version
        trace_location = self._archive_version(config, validation_results)
        checksum = self._calculate_checksum(config)

        return TuningResult(
            version=config.version,
            timestamp=datetime.now().isoformat(),
            config=config,
            validation_results=validation_results,
            r2_loo=r2_loo,
            r2_kfold=r2_kfold,
            rmse_loo=rmse_loo,
            overfitting_score=overfitting,
            success=(r2_kfold >= 0.85),
            trace_location=trace_location,
            checksum=checksum,
            notes="Separated modified compounds into distinct regression models"
        )

    def _iteration2_reduce_features(
        self,
        df: pd.DataFrame,
        data_type: str,
        prev_config: TuningConfig
    ) -> TuningResult:
        """
        Iteration 2: Reduce features to prevent overfitting

        From 9 features → 2 features (Log P + carbon chain)
        """
        config = TuningConfig(
            version="v1.2_reduced_features",
            description="Reduce features from 9 to 2 (Log P + a_component) to reduce overfitting",
            separate_modified=prev_config.separate_modified,
            features=["Log P", "a_component"]  # Just 2 features
        )

        validation_results = self._validate_with_config(df, config, data_type)

        r2_loo = validation_results['loo']['metrics']['r2']
        r2_kfold = validation_results['kfold']['aggregated_metrics']['mean_r2_test']
        rmse_loo = validation_results['loo']['metrics']['rmse']
        overfitting = validation_results['kfold']['aggregated_metrics']['mean_overfitting_score']

        trace_location = self._archive_version(config, validation_results)
        checksum = self._calculate_checksum(config)

        return TuningResult(
            version=config.version,
            timestamp=datetime.now().isoformat(),
            config=config,
            validation_results=validation_results,
            r2_loo=r2_loo,
            r2_kfold=r2_kfold,
            rmse_loo=rmse_loo,
            overfitting_score=overfitting,
            success=(r2_kfold >= 0.88 and overfitting < 0.15),
            trace_location=trace_location,
            checksum=checksum,
            notes="Reduced features to prevent overfitting"
        )

    def _iteration3_ridge_regularization(
        self,
        df: pd.DataFrame,
        data_type: str,
        prev_config: TuningConfig
    ) -> TuningResult:
        """
        Iteration 3: Add Ridge regularization (L2 penalty)

        Replace LinearRegression → Ridge(alpha=1.0)
        """
        config = TuningConfig(
            version="v1.3_ridge",
            description="Add Ridge regularization (alpha=1.0) to further reduce overfitting",
            separate_modified=prev_config.separate_modified,
            features=prev_config.features,
            use_ridge=True,
            ridge_alpha=1.0
        )

        validation_results = self._validate_with_config(df, config, data_type)

        r2_loo = validation_results['loo']['metrics']['r2']
        r2_kfold = validation_results['kfold']['aggregated_metrics']['mean_r2_test']
        rmse_loo = validation_results['loo']['metrics']['rmse']
        overfitting = validation_results['kfold']['aggregated_metrics']['mean_overfitting_score']

        trace_location = self._archive_version(config, validation_results)
        checksum = self._calculate_checksum(config)

        return TuningResult(
            version=config.version,
            timestamp=datetime.now().isoformat(),
            config=config,
            validation_results=validation_results,
            r2_loo=r2_loo,
            r2_kfold=r2_kfold,
            rmse_loo=rmse_loo,
            overfitting_score=overfitting,
            success=(r2_kfold >= 0.90 and overfitting < 0.10),
            trace_location=trace_location,
            checksum=checksum,
            notes="Added Ridge regularization with alpha=1.0"
        )

    def _iteration4_pool_prefixes(
        self,
        df: pd.DataFrame,
        data_type: str,
        prev_config: TuningConfig
    ) -> TuningResult:
        """
        Iteration 4: Pool related prefix groups to increase sample size

        GM1, GM2, GM3 → GM*
        GD1, GD2, GD3 → GD*
        """
        config = TuningConfig(
            version="v1.4_pooled",
            description="Pool related prefix groups (GM1/GM2/GM3 → GM*) to increase sample size",
            separate_modified=prev_config.separate_modified,
            features=prev_config.features,
            use_ridge=prev_config.use_ridge,
            ridge_alpha=prev_config.ridge_alpha,
            pool_prefixes=True,
            prefix_mapping={
                'GM1': 'GM', 'GM2': 'GM', 'GM3': 'GM',
                'GD1': 'GD', 'GD2': 'GD', 'GD3': 'GD',
                'GT1': 'GT', 'GT2': 'GT', 'GT3': 'GT',
                'GQ1': 'GQ', 'GQ2': 'GQ',
                'GP1': 'GP'
            }
        )

        validation_results = self._validate_with_config(df, config, data_type)

        r2_loo = validation_results['loo']['metrics']['r2']
        r2_kfold = validation_results['kfold']['aggregated_metrics']['mean_r2_test']
        rmse_loo = validation_results['loo']['metrics']['rmse']
        overfitting = validation_results['kfold']['aggregated_metrics']['mean_overfitting_score']

        trace_location = self._archive_version(config, validation_results)
        checksum = self._calculate_checksum(config)

        return TuningResult(
            version=config.version,
            timestamp=datetime.now().isoformat(),
            config=config,
            validation_results=validation_results,
            r2_loo=r2_loo,
            r2_kfold=r2_kfold,
            rmse_loo=rmse_loo,
            overfitting_score=overfitting,
            success=(r2_kfold >= 0.90 and overfitting < 0.10),
            trace_location=trace_location,
            checksum=checksum,
            notes="Pooled related prefix groups to increase sample size per model"
        )

    def _validate_with_config(
        self,
        df: pd.DataFrame,
        config: TuningConfig,
        data_type: str
    ) -> Dict[str, Any]:
        """
        Run validation with a specific configuration

        Returns both LOO and K-Fold results
        """
        from .algorithm_validator import AlgorithmValidator
        from .ganglioside_processor_tuned import GangliosideProcessorTuned

        # Create tuned processor with this config
        processor = GangliosideProcessorTuned(config)
        validator = AlgorithmValidator(processor)

        # Run both validations
        loo_results = validator.validate_leave_one_out(df, data_type)
        kfold_results = validator.validate_with_kfold(df, n_splits=5, data_type=data_type)

        return {
            'loo': loo_results,
            'kfold': kfold_results
        }

    def _archive_version(
        self,
        config: TuningConfig,
        validation_results: Dict[str, Any]
    ) -> str:
        """
        Archive this version in trace/ folder with ALCOA++ compliance
        """
        version_dir = self.trace_dir / config.version
        version_dir.mkdir(parents=True, exist_ok=True)

        # Save configuration
        with open(version_dir / "config.json", 'w') as f:
            json.dump(asdict(config), f, indent=2, default=str)

        # Save validation results
        with open(version_dir / "validation_results.json", 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)

        # Save metadata
        metadata = {
            "version": config.version,
            "timestamp": datetime.now().isoformat(),
            "description": config.description,
            "target_r2": 0.90,
            "achieved_r2_loo": validation_results['loo']['metrics']['r2'],
            "achieved_r2_kfold": validation_results['kfold']['aggregated_metrics']['mean_r2_test']
        }
        with open(version_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)

        return str(version_dir)

    def _calculate_checksum(self, config: TuningConfig) -> str:
        """Calculate SHA-256 checksum of configuration"""
        config_str = json.dumps(asdict(config), sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def _print_result(self, iteration: int, result: TuningResult, target_r2: float):
        """Pretty print iteration results"""
        print(f"Iteration {iteration}: {result.version}")
        print(f"  Description: {result.description}")
        print(f"  R² (LOO):    {result.r2_loo:.4f}")
        print(f"  R² (K-Fold): {result.r2_kfold:.4f} (target: {target_r2})")
        print(f"  RMSE (LOO):  {result.rmse_loo:.4f}")
        print(f"  Overfitting: {result.overfitting_score:.4f} (target: < 0.10)")

        if result.success:
            print(f"  Status:      ✅ SUCCESS - Target achieved!")
        else:
            print(f"  Status:      ⏭️  Continue to next iteration")
        print(f"  Trace:       {result.trace_location}")
        print("")

    def save_tuning_history(self, output_file: str = "trace/tuning_history.json"):
        """Save complete tuning history to file"""
        history_data = {
            "tuning_session": {
                "timestamp": datetime.now().isoformat(),
                "iterations": len(self.tuning_history),
                "best_r2": self.best_r2,
                "best_version": self.best_config.version if self.best_config else None
            },
            "results": [asdict(r) for r in self.tuning_history]
        }

        with open(output_file, 'w') as f:
            json.dump(history_data, f, indent=2, default=str)

        print(f"Tuning history saved to: {output_file}")
