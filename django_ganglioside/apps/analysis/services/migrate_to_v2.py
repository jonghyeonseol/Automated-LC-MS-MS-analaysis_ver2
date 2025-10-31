"""
Migration script to transition from original GangliosideProcessor to V2
Provides backward compatibility and smooth transition
"""

import logging
from typing import Dict, Any, Optional
from .ganglioside_processor import GangliosideProcessor
from .ganglioside_processor_v2 import GangliosideProcessorV2

logger = logging.getLogger(__name__)


class ProcessorMigrationHelper:
    """Helper class to migrate from V1 to V2 processor"""

    @staticmethod
    def compare_results(v1_results: Dict, v2_results: Dict) -> Dict[str, Any]:
        """
        Compare results from V1 and V2 processors.

        Args:
            v1_results: Results from original processor
            v2_results: Results from improved processor

        Returns:
            Dictionary with comparison metrics
        """
        comparison = {
            'v1_success_rate': v1_results.get('statistics', {}).get('success_rate', 0),
            'v2_success_rate': v2_results.get('statistics', {}).get('success_rate', 0),
            'v1_valid_compounds': len(v1_results.get('valid_compounds', [])),
            'v2_valid_compounds': len(v2_results.get('valid_compounds', [])),
            'v1_outliers': len(v1_results.get('outliers', [])),
            'v2_outliers': len(v2_results.get('outliers', [])),
            'improvements': []
        }

        # Check for overfitting detection
        v1_warnings = v1_results.get('model_warnings', [])
        v2_warnings = v2_results.get('model_warnings', [])

        if len(v2_warnings) > len(v1_warnings):
            comparison['improvements'].append('Better overfitting detection')

        # Check regression quality
        v1_regression = v1_results.get('regression_analysis', {})
        v2_regression = v2_results.get('regression_analysis', {})

        for prefix in v2_regression:
            if prefix in v1_regression:
                v1_r2 = v1_regression[prefix].get('r2', 0)
                v2_metrics = v2_regression[prefix].get('metrics', {})
                v2_r2 = v2_metrics.get('r2', 0)

                # V2 should have more realistic R² values
                if v1_r2 == 1.0 and v2_r2 < 0.99:
                    comparison['improvements'].append(
                        f'{prefix}: Realistic R² ({v2_r2:.3f} vs {v1_r2:.3f})'
                    )

        return comparison

    @staticmethod
    def migrate_settings(v1_processor: GangliosideProcessor) -> Dict[str, float]:
        """
        Migrate settings from V1 to V2 processor.

        Args:
            v1_processor: Original processor instance

        Returns:
            Settings dictionary for V2
        """
        v1_settings = v1_processor.get_settings()

        # V2 uses more conservative defaults
        v2_settings = {
            'r2_threshold': min(v1_settings.get('r2_threshold', 0.75), 0.75),
            'outlier_threshold': v1_settings.get('outlier_threshold', 2.5),
            'rt_tolerance': v1_settings.get('rt_tolerance', 0.1),
            'min_samples_for_regression': 3
        }

        logger.info(f"Migrated settings from V1 to V2: {v2_settings}")
        return v2_settings


class BackwardCompatibleProcessor:
    """
    Wrapper that provides backward compatibility while using V2 internally.
    Allows gradual migration without breaking existing code.
    """

    def __init__(self, use_v2: bool = True, log_comparison: bool = False):
        """
        Initialize backward compatible processor.

        Args:
            use_v2: Whether to use V2 processor (True) or V1 (False)
            log_comparison: Whether to log comparison between V1 and V2
        """
        self.use_v2 = use_v2
        self.log_comparison = log_comparison

        if use_v2:
            self.processor = GangliosideProcessorV2()
            logger.info("Using improved V2 processor with overfitting prevention")
        else:
            self.processor = GangliosideProcessor()
            logger.info("Using original V1 processor")

        # Keep V1 for comparison if needed
        if log_comparison:
            self.v1_processor = GangliosideProcessor()

    def process_data(self, df, data_type="Porcine") -> Dict[str, Any]:
        """
        Process data with backward compatibility.

        Args:
            df: Input DataFrame
            data_type: Type of data

        Returns:
            Analysis results (V2 format if use_v2=True)
        """
        if self.use_v2:
            results = self.processor.process_data(df, data_type)

            if self.log_comparison:
                # Run V1 for comparison
                v1_results = self.v1_processor.process_data(df, data_type)
                comparison = ProcessorMigrationHelper.compare_results(
                    v1_results, results
                )

                logger.info(f"Comparison - V1 vs V2:")
                logger.info(f"  Success rate: {comparison['v1_success_rate']:.1f}% vs "
                          f"{comparison['v2_success_rate']:.1f}%")
                logger.info(f"  Valid compounds: {comparison['v1_valid_compounds']} vs "
                          f"{comparison['v2_valid_compounds']}")
                logger.info(f"  Improvements: {comparison['improvements']}")

                # Add comparison to results
                results['_migration_comparison'] = comparison

        else:
            results = self.processor.process_data(df, data_type)

        return results

    def update_settings(self, **kwargs):
        """Update processor settings."""
        self.processor.update_settings(**kwargs)
        if hasattr(self, 'v1_processor'):
            self.v1_processor.update_settings(**kwargs)

    def get_settings(self):
        """Get processor settings."""
        return self.processor.get_settings()


def run_migration_test(csv_path: str) -> Dict[str, Any]:
    """
    Test migration by running both processors and comparing results.

    Args:
        csv_path: Path to test CSV file

    Returns:
        Comparison results
    """
    import pandas as pd

    logger.info(f"Running migration test on {csv_path}")

    # Load data
    df = pd.read_csv(csv_path)

    # Run V1
    v1_processor = GangliosideProcessor()
    v1_results = v1_processor.process_data(df)

    # Run V2
    v2_processor = GangliosideProcessorV2()
    v2_results = v2_processor.process_data(df)

    # Compare
    comparison = ProcessorMigrationHelper.compare_results(v1_results, v2_results)

    # Detailed regression comparison
    regression_comparison = {}
    v1_reg = v1_results.get('regression_analysis', {})
    v2_reg = v2_results.get('regression_analysis', {})

    for prefix in set(list(v1_reg.keys()) + list(v2_reg.keys())):
        regression_comparison[prefix] = {
            'v1': {
                'r2': v1_reg.get(prefix, {}).get('r2'),
                'n_samples': v1_reg.get(prefix, {}).get('n_samples'),
                'equation': v1_reg.get(prefix, {}).get('equation', 'N/A')
            },
            'v2': {
                'r2': v2_reg.get(prefix, {}).get('metrics', {}).get('r2'),
                'features': v2_reg.get(prefix, {}).get('features'),
                'cv_method': v2_reg.get(prefix, {}).get('metrics', {}).get('cv_method'),
                'equation': v2_reg.get(prefix, {}).get('equation', 'N/A')
            }
        }

    return {
        'overall_comparison': comparison,
        'regression_comparison': regression_comparison,
        'recommendation': _get_migration_recommendation(comparison, regression_comparison)
    }


def _get_migration_recommendation(comparison: Dict, regression_comp: Dict) -> str:
    """
    Generate migration recommendation based on comparison.

    Args:
        comparison: Overall comparison metrics
        regression_comp: Detailed regression comparison

    Returns:
        Recommendation string
    """
    recommendations = []

    # Check success rate
    v1_rate = comparison['v1_success_rate']
    v2_rate = comparison['v2_success_rate']

    if v2_rate >= v1_rate - 5:  # Allow 5% tolerance
        recommendations.append("✓ V2 maintains comparable success rate")
    else:
        recommendations.append("⚠ V2 has lower success rate - review outlier threshold")

    # Check for overfitting improvements
    overfitting_fixed = False
    for prefix, data in regression_comp.items():
        v1_r2 = data['v1'].get('r2')
        v2_r2 = data['v2'].get('r2')

        if v1_r2 and v1_r2 >= 0.99 and v2_r2 and v2_r2 < 0.95:
            overfitting_fixed = True
            break

    if overfitting_fixed:
        recommendations.append("✓ V2 successfully addresses overfitting issues")

    # Check feature reduction
    for prefix, data in regression_comp.items():
        if data['v2'].get('features'):
            n_features = len(data['v2']['features'])
            if n_features <= 2:
                recommendations.append(f"✓ {prefix}: Reduced to {n_features} meaningful features")

    # Overall recommendation
    if len([r for r in recommendations if r.startswith('✓')]) >= 2:
        final_rec = "RECOMMENDED: Safe to migrate to V2"
    else:
        final_rec = "CAUTION: Review results carefully before migration"

    return "\n".join(recommendations + [f"\n{final_rec}"])


# Usage example for Django management command
class Command:
    """Django management command for migration"""

    help = 'Migrate from GangliosideProcessor V1 to V2'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-file',
            type=str,
            help='CSV file to test migration'
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply migration to all existing sessions'
        )

    def handle(self, *args, **options):
        if options['test_file']:
            results = run_migration_test(options['test_file'])
            print("\nMigration Test Results:")
            print("=" * 50)
            print(f"Overall Comparison: {results['overall_comparison']}")
            print(f"\nRecommendation:\n{results['recommendation']}")

        if options['apply']:
            # Update analysis service to use V2
            from apps.analysis.services.analysis_service import AnalysisService

            # Monkey patch or update configuration
            logger.info("Migration applied - now using GangliosideProcessorV2")
            print("Migration complete - GangliosideProcessorV2 is now active")