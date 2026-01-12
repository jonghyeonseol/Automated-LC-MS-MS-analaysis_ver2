"""
GangliosideProcessorV3 - 10-Rule Analysis Pipeline

Extends V2 with three additional validation rules:
- Rule 8: Modification Stack Validation
- Rule 9: Cross-Prefix Consistency Validation
- Rule 10: Confidence Scoring

This processor implements a comprehensive analysis pipeline that combines
regression analysis, chemical validation, and confidence scoring for
LC-MS/MS ganglioside identification.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .ganglioside_processor_v2 import GangliosideProcessorV2
from .modification_validator import ModificationStackValidator
from .cross_prefix_validator import CrossPrefixValidator
from .confidence_scorer import ConfidenceScorer
from .input_validator import InputValidator, ValidationResult
from .statistical_safeguards import StatisticalSafeguards, ConfidenceLevel

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Complete result from V3 processing pipeline."""
    success: bool
    statistics: Dict[str, Any]
    regression_analysis: Dict[str, Any]
    model_warnings: List[str]
    valid_compounds: List[Dict[str, Any]]
    outliers: List[Dict[str, Any]]
    sugar_analysis: Dict[str, Any]
    oacetylation_analysis: Dict[str, Any]
    rt_filtering_summary: Dict[str, Any]
    categorization: Dict[str, Any]
    chemical_validation: Dict[str, Any]
    chemical_warnings: List[Dict[str, Any]]
    modification_validation: Dict[str, Any]
    cross_prefix_validation: Dict[str, Any]
    confidence_analysis: Dict[str, Any]
    errors: Optional[List[str]] = None
    # Phase 2: Scientific credibility enhancements
    input_validation: Optional[Dict[str, Any]] = None
    regression_diagnostics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            'success': self.success,
            'statistics': self.statistics,
            'regression_analysis': self.regression_analysis,
            'model_warnings': self.model_warnings,
            'valid_compounds': self.valid_compounds,
            'outliers': self.outliers,
            'sugar_analysis': self.sugar_analysis,
            'oacetylation_analysis': self.oacetylation_analysis,
            'rt_filtering_summary': self.rt_filtering_summary,
            'categorization': self.categorization,
            'chemical_validation': self.chemical_validation,
            'chemical_warnings': self.chemical_warnings,
            'modification_validation': self.modification_validation,
            'cross_prefix_validation': self.cross_prefix_validation,
            'confidence_analysis': self.confidence_analysis,
        }
        if self.errors:
            result['errors'] = self.errors
        # Phase 2: Scientific credibility enhancements
        if self.input_validation:
            result['input_validation'] = self.input_validation
        if self.regression_diagnostics:
            result['regression_diagnostics'] = self.regression_diagnostics
        return result


class GangliosideProcessorV3(GangliosideProcessorV2):
    """
    Enhanced Ganglioside Processor with 10-rule validation pipeline.

    Extends V2 with:
    - Rule 8: Modification Stack Validation
    - Rule 9: Cross-Prefix Consistency Validation
    - Rule 10: Confidence Scoring

    The confidence scoring integrates results from all previous rules
    to provide a probabilistic assessment of compound identification.
    """

    def __init__(
        self,
        r2_threshold: float = 0.70,
        outlier_threshold: float = 2.5,
        rt_tolerance: float = 0.1,
        min_samples_for_regression: int = 3,
        confidence_threshold: float = 0.7,
        confidence_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize Ganglioside Processor V3.

        Args:
            r2_threshold: Minimum R² for valid regression (0.70 recommended)
            outlier_threshold: Standardized residual threshold for outliers
            rt_tolerance: RT tolerance for fragmentation detection (minutes)
            min_samples_for_regression: Minimum samples needed for regression
            confidence_threshold: Minimum confidence score for valid compounds
            confidence_weights: Custom weights for confidence components
        """
        # Initialize V2 components
        super().__init__(
            r2_threshold=r2_threshold,
            outlier_threshold=outlier_threshold,
            rt_tolerance=rt_tolerance,
            min_samples_for_regression=min_samples_for_regression
        )

        # V3 specific settings
        self.confidence_threshold = confidence_threshold

        # Initialize V3 validators
        self.modification_validator = ModificationStackValidator(
            rt_tolerance=rt_tolerance
        )
        self.cross_prefix_validator = CrossPrefixValidator()
        self.confidence_scorer = ConfidenceScorer(
            weights=confidence_weights
        )

        # Phase 2: Scientific credibility components
        self.input_validator = InputValidator()
        self.statistical_safeguards = StatisticalSafeguards()

        logger.info(
            f"Ganglioside Processor V3 initialized with 10-rule pipeline, "
            f"confidence_threshold={confidence_threshold}, "
            f"scientific_safeguards=enabled"
        )

    def update_settings(
        self,
        outlier_threshold: Optional[float] = None,
        r2_threshold: Optional[float] = None,
        rt_tolerance: Optional[float] = None,
        confidence_threshold: Optional[float] = None
    ) -> None:
        """Update analysis settings."""
        super().update_settings(
            outlier_threshold=outlier_threshold,
            r2_threshold=r2_threshold,
            rt_tolerance=rt_tolerance
        )

        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
            self.confidence_scorer.threshold = confidence_threshold

        if rt_tolerance is not None:
            self.modification_validator.rt_tolerance = rt_tolerance

        logger.info(
            f"V3 settings updated: confidence_threshold={self.confidence_threshold}"
        )

    def get_settings(self) -> Dict[str, float]:
        """Get current settings including V3 parameters."""
        settings = super().get_settings()
        settings['confidence_threshold'] = self.confidence_threshold
        return settings

    def process_data(
        self,
        df: pd.DataFrame,
        data_type: str = "Porcine"
    ) -> Dict[str, Any]:
        """
        Main data processing function with 10-rule pipeline.

        Applies all rules sequentially:
        - Rules 1-7: Inherited from V2
        - Rule 8: Modification Stack Validation
        - Rule 9: Cross-Prefix Consistency Validation
        - Rule 10: Confidence Scoring

        Args:
            df: Input DataFrame with compound data
            data_type: Type of data (Porcine, Human, etc.)

        Returns:
            Dictionary with complete analysis results
        """
        logger.info(f"V3 Analysis starting: {len(df)} compounds, mode: {data_type}")

        # Phase 2: Comprehensive input validation with transparency
        validation_result = self.input_validator.validate(df)
        input_validation_dict = {
            'is_valid': validation_result.is_valid,
            'rows_received': validation_result.rows_received,
            'rows_after_validation': validation_result.rows_after_validation,
            'rows_dropped': validation_result.rows_dropped,
            'dropped_row_details': validation_result.dropped_row_details,
            'columns_renamed': validation_result.columns_renamed,
            'nan_counts_by_column': validation_result.nan_counts_by_column,
            'duplicate_names': validation_result.duplicate_names,
            'out_of_bounds_values': validation_result.out_of_bounds_values,
            'warnings': validation_result.warnings,
            'errors': validation_result.errors,
        }

        if not validation_result.is_valid:
            logger.error(f"Input validation failed: {validation_result.errors}")
            return ProcessingResult(
                success=False,
                statistics={'total_compounds': len(df)},
                regression_analysis={},
                model_warnings=[],
                valid_compounds=[],
                outliers=[],
                sugar_analysis={},
                oacetylation_analysis={},
                rt_filtering_summary={},
                categorization={},
                chemical_validation={},
                chemical_warnings=[],
                modification_validation={},
                cross_prefix_validation={},
                confidence_analysis={},
                errors=validation_result.errors,
                input_validation=input_validation_dict
            ).to_dict()

        # Use validated DataFrame (with rows dropped transparently)
        df_validated = validation_result.df
        if validation_result.rows_dropped > 0:
            logger.warning(
                f"Input validation dropped {validation_result.rows_dropped} rows. "
                f"Details available in input_validation.dropped_row_details"
            )

        try:
            # Data preprocessing (now uses validated DataFrame)
            df_processed = self._preprocess_data(df_validated.copy())
            logger.info(f"Preprocessing complete: {len(df_processed)} compounds")

            # Rule 1: Prefix-based regression analysis
            logger.info("Rule 1: Running prefix-based regression analysis...")
            rule1_results = self._apply_rule1_prefix_regression(df_processed)
            logger.info(
                f"  - Regression groups: {len(rule1_results['regression_results'])}, "
                f"Valid compounds: {len(rule1_results['valid_compounds'])}, "
                f"Outliers: {len(rule1_results['outliers'])}"
            )

            # Phase 2: Run statistical diagnostics on regression results
            logger.info("Running statistical diagnostics on regression results...")
            regression_diagnostics = self._compute_regression_diagnostics(
                df_processed, rule1_results
            )

            # Rule 2-3: Sugar count calculation and isomer classification
            logger.info("Rule 2-3: Calculating sugar counts and identifying isomers...")
            rule23_results = self._apply_rule2_3_sugar_count(df_processed, data_type)
            isomer_count = sum(
                1 for info in rule23_results["sugar_analysis"].values()
                if info["can_have_isomers"]
            )
            logger.info(f"  - Isomer candidates: {isomer_count}")

            # Rule 4: O-acetylation effect validation
            logger.info("Rule 4: Validating O-acetylation effects...")
            rule4_results = self._apply_rule4_oacetylation(df_processed)
            logger.info(
                f"  - Valid OAc compounds: {len(rule4_results['valid_oacetyl'])}, "
                f"Invalid OAc compounds: {len(rule4_results['invalid_oacetyl'])}"
            )

            # Rule 5: RT-based filtering and in-source fragmentation detection
            logger.info("Rule 5: Detecting fragmentation and filtering...")
            rule5_results = self._apply_rule5_rt_filtering(df_processed)
            logger.info(
                f"  - Fragmentation candidates: {len(rule5_results['fragmentation_candidates'])}, "
                f"Filtered compounds: {len(rule5_results['filtered_compounds'])}"
            )

            # Rule 6: Sugar-RT relationship validation
            logger.info("Rule 6: Validating sugar-RT relationship...")
            rule6_results = self._apply_rule6_sugar_rt_validation(df_processed)

            # Rule 7: Category ordering validation
            logger.info("Rule 7: Validating category RT ordering...")
            rule7_results = self._apply_rule7_category_ordering(df_processed)

            # Rule 8: Modification Stack Validation (NEW in V3)
            logger.info("Rule 8: Validating modification stacks...")
            rule8_results = self._apply_rule8_modification_validation(df_processed)
            logger.info(
                f"  - Analyzed modifications: {rule8_results.get('statistics', {}).get('total_compounds', 0)}, "
                f"Warnings: {rule8_results.get('statistics', {}).get('total_warnings', 0)}"
            )

            # Rule 9: Cross-Prefix Consistency Validation (NEW in V3)
            logger.info("Rule 9: Validating cross-prefix consistency...")
            rule9_results = self._apply_rule9_cross_prefix_validation(
                df_processed, rule1_results
            )
            logger.info(
                f"  - Comparisons: {rule9_results.get('total_comparisons', 0)}, "
                f"Valid: {rule9_results.get('is_valid', False)}"
            )

            # Rule 10: Confidence Scoring (NEW in V3)
            logger.info("Rule 10: Computing confidence scores...")
            rule10_results = self._apply_rule10_confidence_scoring(
                df_processed,
                rule1_results,
                rule6_results,
                rule7_results,
                rule8_results,
                rule9_results
            )
            logger.info(
                f"  - Average confidence: {rule10_results.get('average_score', 0):.3f}, "
                f"High confidence: {rule10_results.get('high_confidence_count', 0)}"
            )

            # Compile final results
            logger.info("Compiling final V3 results...")
            final_results = self._compile_results_v3(
                df_processed,
                rule1_results,
                rule23_results,
                rule4_results,
                rule5_results,
                rule6_results,
                rule7_results,
                rule8_results,
                rule9_results,
                rule10_results,
                input_validation=input_validation_dict,
                regression_diagnostics=regression_diagnostics
            )

            success_rate = final_results['statistics']['success_rate']
            avg_confidence = final_results['confidence_analysis'].get('average_score', 0)
            logger.info(
                f"V3 Analysis complete: {success_rate:.1f}% success rate, "
                f"{avg_confidence:.3f} average confidence"
            )

            return final_results

        except Exception as e:
            logger.error(f"V3 Analysis failed: {str(e)}", exc_info=True)
            return ProcessingResult(
                success=False,
                statistics={'total_compounds': len(df)},
                regression_analysis={},
                model_warnings=[],
                valid_compounds=[],
                outliers=[],
                sugar_analysis={},
                oacetylation_analysis={},
                rt_filtering_summary={},
                categorization={},
                chemical_validation={},
                chemical_warnings=[],
                modification_validation={},
                cross_prefix_validation={},
                confidence_analysis={},
                errors=[str(e)],
                input_validation=input_validation_dict
            ).to_dict()

    def _apply_rule8_modification_validation(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Rule 8: Validate modification stacks.

        Validates:
        - Combinatorial completeness of modifications
        - RT ordering for modification pairs
        - Modification impact consistency

        Args:
            df: Preprocessed DataFrame

        Returns:
            Dictionary with modification validation results
        """
        result = self.modification_validator.validate(df)
        return result.to_dict()

    def _apply_rule9_cross_prefix_validation(
        self,
        df: pd.DataFrame,
        regression_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rule 9: Validate cross-prefix consistency.

        Validates:
        - RT ordering across categories (GP < GQ < GT < GD < GM)
        - Regression parameter consistency
        - Shared outlier detection

        Args:
            df: Preprocessed DataFrame
            regression_results: Results from Rule 1

        Returns:
            Dictionary with cross-prefix validation results
        """
        result = self.cross_prefix_validator.validate(
            df,
            regression_results.get('regression_results', {})
        )
        return result.to_dict()

    def _apply_rule10_confidence_scoring(
        self,
        df: pd.DataFrame,
        rule1_results: Dict[str, Any],
        rule6_results: Dict[str, Any],
        rule7_results: Dict[str, Any],
        rule8_results: Dict[str, Any],
        rule9_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rule 10: Compute compound confidence scores.

        Combines evidence from all rules:
        - Regression fit quality (R²)
        - Residual magnitude
        - Bayesian uncertainty (if available)
        - Chemical validation results
        - Cross-prefix consistency
        - Modification stack validation

        Args:
            df: Preprocessed DataFrame
            rule1_results: Regression analysis results
            rule6_results: Sugar-RT validation results
            rule7_results: Category ordering results
            rule8_results: Modification validation results
            rule9_results: Cross-prefix validation results

        Returns:
            Dictionary with confidence scores for all compounds
        """
        # Combine chemical validation results (rules 6 and 7)
        combined_chemical_validation = {
            'sugar_rt_validation': rule6_results,
            'category_ordering': rule7_results
        }

        result = self.confidence_scorer.score_all_compounds(
            df=df,
            regression_results=rule1_results,
            chemical_validation=combined_chemical_validation,
            cross_prefix_results=rule9_results,
            modification_results=rule8_results
        )
        return result.to_dict()

    def _compute_regression_diagnostics(
        self,
        df: pd.DataFrame,
        rule1_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute statistical diagnostics for each regression group.

        Uses StatisticalSafeguards to assess:
        - Sample size adequacy
        - R² threshold appropriateness
        - Cross-validation meaningfulness
        - Extrapolation risk
        - Heteroscedasticity
        - Multicollinearity
        - Outlier detection validity

        Args:
            df: Processed DataFrame with compound data
            rule1_results: Results from Rule 1 regression analysis

        Returns:
            Dictionary with diagnostics per prefix group and overall summary
        """
        regression_results = rule1_results.get('regression_results', {})

        if not regression_results:
            return {
                'diagnostics_available': False,
                'reason': 'No regression results to analyze',
                'prefix_diagnostics': {},
                'overall_summary': {}
            }

        prefix_diagnostics = {}
        all_warnings = []
        all_recommendations = []
        confidence_levels = []

        for prefix, reg_info in regression_results.items():
            # Skip failed regressions
            if isinstance(reg_info, dict) and reg_info.get('success') is False:
                prefix_diagnostics[prefix] = {
                    'diagnostics_available': False,
                    'reason': reg_info.get('reason', 'Regression failed')
                }
                continue

            # Extract features used in regression
            features = reg_info.get('features', ['Log P'])
            n_samples = reg_info.get('n_samples', 0)
            n_anchors = reg_info.get('n_anchors', 0)

            # Get anchor compounds for this prefix
            prefix_df = df[df['prefix'] == prefix].copy()
            anchor_df = prefix_df[prefix_df['Anchor'] == 'T'].copy()

            if len(anchor_df) < 3:
                prefix_diagnostics[prefix] = {
                    'diagnostics_available': False,
                    'reason': f'Insufficient anchor compounds ({len(anchor_df)} < 3)'
                }
                continue

            try:
                # Prepare X (features) and y (target)
                available_features = [f for f in features if f in anchor_df.columns]
                if not available_features:
                    available_features = ['Log P']

                X = anchor_df[available_features].values
                y = anchor_df['RT'].values

                # Get predictions and compute residuals
                if 'predicted_rt' in prefix_df.columns:
                    anchor_pred = anchor_df['predicted_rt'].values
                    residuals = y - anchor_pred
                else:
                    # Fallback: compute simple residuals from mean
                    residuals = y - np.mean(y)

                # Prepare X_predict for extrapolation check (all compounds, not just anchors)
                X_predict = prefix_df[available_features].values

                # Run full diagnostics
                diagnostics = self.statistical_safeguards.run_full_diagnostics(
                    X=X,
                    y=y,
                    residuals=residuals,
                    feature_names=available_features,
                    r2_threshold=self.r2_threshold,
                    outlier_threshold=self.outlier_threshold,
                    X_predict=X_predict
                )

                # Store diagnostics for this prefix
                prefix_diagnostics[prefix] = diagnostics.to_dict()

                # Collect for overall summary
                all_warnings.extend([
                    f"[{prefix}] {w}" for w in diagnostics.warnings
                ])
                all_recommendations.extend([
                    f"[{prefix}] {r}" for r in diagnostics.recommendations
                ])
                confidence_levels.append(diagnostics.confidence_level)

            except Exception as e:
                logger.warning(f"Diagnostics failed for prefix {prefix}: {e}")
                prefix_diagnostics[prefix] = {
                    'diagnostics_available': False,
                    'reason': f'Diagnostics computation failed: {str(e)}'
                }

        # Compute overall summary
        if confidence_levels:
            # Determine overall confidence (worst case)
            confidence_order = [
                ConfidenceLevel.UNRELIABLE,
                ConfidenceLevel.LOW,
                ConfidenceLevel.MODERATE,
                ConfidenceLevel.HIGH,
                ConfidenceLevel.VALIDATED
            ]
            min_confidence = min(
                confidence_levels,
                key=lambda c: confidence_order.index(c)
            )

            overall_summary = {
                'total_prefix_groups': len(regression_results),
                'groups_with_diagnostics': len([
                    p for p in prefix_diagnostics.values()
                    if isinstance(p, dict) and p.get('diagnostics_available', True)
                ]),
                'overall_confidence': min_confidence.value,
                'total_warnings': len(all_warnings),
                'total_recommendations': len(all_recommendations),
                'critical_issues': [
                    w for w in all_warnings if 'UNRELIABLE' in w or 'critical' in w.lower()
                ]
            }
        else:
            overall_summary = {
                'total_prefix_groups': len(regression_results),
                'groups_with_diagnostics': 0,
                'overall_confidence': 'unknown',
                'total_warnings': 0,
                'total_recommendations': 0,
                'critical_issues': []
            }

        return {
            'diagnostics_available': True,
            'prefix_diagnostics': prefix_diagnostics,
            'overall_summary': overall_summary,
            'all_warnings': all_warnings,
            'all_recommendations': all_recommendations
        }

    def _compile_results_v3(
        self,
        df: pd.DataFrame,
        rule1_results: Dict[str, Any],
        rule23_results: Dict[str, Any],
        rule4_results: Dict[str, Any],
        rule5_results: Dict[str, Any],
        rule6_results: Dict[str, Any],
        rule7_results: Dict[str, Any],
        rule8_results: Dict[str, Any],
        rule9_results: Dict[str, Any],
        rule10_results: Dict[str, Any],
        input_validation: Optional[Dict[str, Any]] = None,
        regression_diagnostics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Compile all rule results into final V3 output.

        Args:
            df: Processed DataFrame
            rule1_results: Regression analysis
            rule23_results: Sugar count and isomer analysis
            rule4_results: O-acetylation validation
            rule5_results: RT filtering and fragmentation
            rule6_results: Sugar-RT validation
            rule7_results: Category ordering validation
            rule8_results: Modification validation
            rule9_results: Cross-prefix validation
            rule10_results: Confidence scoring
            input_validation: Input validation results (Phase 2)
            regression_diagnostics: Statistical diagnostics for regression (Phase 2)

        Returns:
            Complete analysis results dictionary
        """
        # Calculate base statistics
        total_compounds = len(df)
        anchor_compounds = len(df[df["Anchor"] == True])
        valid_compounds = len(rule1_results["valid_compounds"])
        outlier_count = len(rule1_results["outliers"])
        success_rate = (valid_compounds / total_compounds * 100) if total_compounds > 0 else 0

        # Categorize compounds
        categorization = self.categorizer.categorize_compounds(df)

        # Compile chemical validation results
        chemical_validation = {
            'sugar_rt_validation': rule6_results,
            'category_ordering': rule7_results
        }

        # Collect all warnings
        chemical_warnings = []
        for validation_name, validation_result in chemical_validation.items():
            if validation_result and 'warnings' in validation_result:
                for warning in validation_result['warnings']:
                    chemical_warnings.append({
                        'validation': validation_name,
                        **warning
                    })

        # Add modification warnings
        if 'warnings' in rule8_results:
            for warning in rule8_results['warnings']:
                chemical_warnings.append({
                    'validation': 'modification_stack',
                    **warning
                })

        # Add cross-prefix warnings
        if 'warnings' in rule9_results:
            for warning in rule9_results['warnings']:
                chemical_warnings.append({
                    'validation': 'cross_prefix',
                    **warning
                })

        # Enhanced statistics with V3 metrics
        statistics = {
            "total_compounds": total_compounds,
            "anchor_compounds": anchor_compounds,
            "valid_compounds": valid_compounds,
            "outlier_count": outlier_count,
            "success_rate": success_rate,
            # V3 specific metrics
            "average_confidence": rule10_results.get('average_score', 0),
            "high_confidence_count": rule10_results.get('high_confidence_count', 0),
            "low_confidence_count": rule10_results.get('low_confidence_count', 0),
            "modification_warnings": rule8_results.get('statistics', {}).get('total_warnings', 0),
            "cross_prefix_valid": rule9_results.get('is_valid', False),
            "pipeline_version": "V3"
        }

        return ProcessingResult(
            success=True,
            statistics=statistics,
            regression_analysis=rule1_results["regression_results"],
            model_warnings=rule1_results.get("model_warnings", []),
            valid_compounds=rule1_results["valid_compounds"],
            outliers=rule1_results["outliers"],
            sugar_analysis=rule23_results["sugar_analysis"],
            oacetylation_analysis={
                "valid": rule4_results["valid_oacetyl"],
                "invalid": rule4_results["invalid_oacetyl"],
                "magnitude_validation": rule4_results.get("magnitude_validation", {})
            },
            rt_filtering_summary={
                "fragmentation_events": rule5_results["fragmentation_candidates"],
                "filtered_compounds": rule5_results["filtered_compounds"]
            },
            categorization=categorization,
            chemical_validation=chemical_validation,
            chemical_warnings=chemical_warnings,
            modification_validation=rule8_results,
            cross_prefix_validation=rule9_results,
            confidence_analysis=rule10_results,
            # Phase 2: Scientific credibility enhancements
            input_validation=input_validation,
            regression_diagnostics=regression_diagnostics
        ).to_dict()

    def get_compound_confidence(
        self,
        compound_name: str,
        df: pd.DataFrame,
        full_results: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed confidence information for a specific compound.

        Args:
            compound_name: Name of the compound to query
            df: DataFrame containing the compound
            full_results: Pre-computed full results (optional)

        Returns:
            Confidence details for the compound or None if not found
        """
        if full_results is None:
            # Run full analysis if results not provided
            full_results = self.process_data(df)

        confidence_analysis = full_results.get('confidence_analysis', {})
        scores = confidence_analysis.get('scores', [])

        for score in scores:
            if score.get('compound_name') == compound_name:
                return score

        return None

    def filter_by_confidence(
        self,
        df: pd.DataFrame,
        min_confidence: Optional[float] = None,
        full_results: Optional[Dict[str, Any]] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Filter compounds by confidence score.

        Args:
            df: DataFrame with compounds
            min_confidence: Minimum confidence threshold (uses instance default if None)
            full_results: Pre-computed full results (optional)

        Returns:
            Tuple of (high_confidence_df, low_confidence_df)
        """
        if min_confidence is None:
            min_confidence = self.confidence_threshold

        if full_results is None:
            full_results = self.process_data(df)

        confidence_analysis = full_results.get('confidence_analysis', {})
        scores = confidence_analysis.get('scores', [])

        high_confidence_names = []
        low_confidence_names = []

        for score in scores:
            if score.get('overall_score', 0) >= min_confidence:
                high_confidence_names.append(score.get('compound_name'))
            else:
                low_confidence_names.append(score.get('compound_name'))

        high_df = df[df['Name'].isin(high_confidence_names)]
        low_df = df[df['Name'].isin(low_confidence_names)]

        return high_df, low_df

    def get_validation_summary(
        self,
        full_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get a summary of all validation results.

        Args:
            full_results: Complete results from process_data()

        Returns:
            Summary dictionary with validation status for each rule
        """
        statistics = full_results.get('statistics', {})
        confidence_analysis = full_results.get('confidence_analysis', {})

        return {
            'pipeline_version': 'V3',
            'overall_success': full_results.get('success', False),
            'total_compounds': statistics.get('total_compounds', 0),
            'validation_summary': {
                'rule1_regression': {
                    'valid_compounds': statistics.get('valid_compounds', 0),
                    'outliers': statistics.get('outlier_count', 0)
                },
                'rule2_3_sugar': {
                    'analyzed': len(full_results.get('sugar_analysis', {}))
                },
                'rule4_oacetylation': {
                    'valid': len(full_results.get('oacetylation_analysis', {}).get('valid', [])),
                    'invalid': len(full_results.get('oacetylation_analysis', {}).get('invalid', []))
                },
                'rule5_fragmentation': {
                    'events': len(full_results.get('rt_filtering_summary', {}).get('fragmentation_events', []))
                },
                'rule6_sugar_rt': {
                    'is_valid': full_results.get('chemical_validation', {}).get('sugar_rt_validation', {}).get('is_valid', False)
                },
                'rule7_category_order': {
                    'is_valid': full_results.get('chemical_validation', {}).get('category_ordering', {}).get('is_valid', False)
                },
                'rule8_modification': {
                    'is_valid': full_results.get('modification_validation', {}).get('is_valid', False),
                    'warnings': full_results.get('modification_validation', {}).get('statistics', {}).get('total_warnings', 0)
                },
                'rule9_cross_prefix': {
                    'is_valid': full_results.get('cross_prefix_validation', {}).get('is_valid', False),
                    'comparisons': full_results.get('cross_prefix_validation', {}).get('total_comparisons', 0)
                },
                'rule10_confidence': {
                    'average_score': confidence_analysis.get('average_score', 0),
                    'high_confidence': confidence_analysis.get('high_confidence_count', 0),
                    'low_confidence': confidence_analysis.get('low_confidence_count', 0)
                }
            },
            'chemical_warnings_count': len(full_results.get('chemical_warnings', []))
        }
