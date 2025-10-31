"""
Ganglioside Data Processor V2 - Improved version with better regression handling
5-rule based ganglioside data automatic classification system
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from .improved_regression import ImprovedRegressionModel
from .ganglioside_categorizer import GangliosideCategorizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GangliosideProcessorV2:
    """
    Improved Ganglioside Processor with better regression handling and validation.

    Major improvements:
    - Uses ImprovedRegressionModel to prevent overfitting
    - Proper feature selection and cross-validation
    - Comprehensive data validation
    - English-only logging and documentation
    - Better error handling
    """

    def __init__(
        self,
        r2_threshold: float = 0.70,  # Realistic threshold for LC-MS data
        outlier_threshold: float = 2.5,
        rt_tolerance: float = 0.1,
        min_samples_for_regression: int = 3
    ):
        """
        Initialize Ganglioside Processor V2.

        Args:
            r2_threshold: Minimum R² for valid regression (0.70 recommended)
            outlier_threshold: Standardized residual threshold for outliers
            rt_tolerance: RT tolerance for fragmentation detection (minutes)
            min_samples_for_regression: Minimum samples needed for regression
        """
        self.r2_threshold = r2_threshold
        self.outlier_threshold = outlier_threshold
        self.rt_tolerance = rt_tolerance
        self.min_samples_for_regression = min_samples_for_regression

        # Initialize components
        self.categorizer = GangliosideCategorizer()
        self.regression_model = ImprovedRegressionModel(
            min_samples=min_samples_for_regression,
            r2_threshold=r2_threshold
        )

        logger.info(
            "Ganglioside Processor V2 initialized with settings: "
            f"r2={r2_threshold}, outlier={outlier_threshold}, rt={rt_tolerance}"
        )

    def update_settings(
        self,
        outlier_threshold: Optional[float] = None,
        r2_threshold: Optional[float] = None,
        rt_tolerance: Optional[float] = None
    ) -> None:
        """Update analysis settings."""
        if outlier_threshold is not None:
            self.outlier_threshold = outlier_threshold
        if r2_threshold is not None:
            self.r2_threshold = r2_threshold
            self.regression_model.r2_threshold = r2_threshold
        if rt_tolerance is not None:
            self.rt_tolerance = rt_tolerance

        logger.info(
            f"Settings updated: outlier={self.outlier_threshold}, "
            f"r2={self.r2_threshold}, rt={self.rt_tolerance}"
        )

    def get_settings(self) -> Dict[str, float]:
        """Get current settings."""
        return {
            "outlier_threshold": self.outlier_threshold,
            "r2_threshold": self.r2_threshold,
            "rt_tolerance": self.rt_tolerance,
        }

    def validate_input_data(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate input DataFrame structure and content.

        Args:
            df: Input DataFrame

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required columns
        required_columns = ['Name', 'RT', 'Volume', 'Log P', 'Anchor']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")

        # Check data types
        if 'RT' in df.columns and not pd.api.types.is_numeric_dtype(df['RT']):
            errors.append("RT column must be numeric")
        if 'Volume' in df.columns and not pd.api.types.is_numeric_dtype(df['Volume']):
            errors.append("Volume column must be numeric")
        if 'Log P' in df.columns and not pd.api.types.is_numeric_dtype(df['Log P']):
            errors.append("Log P column must be numeric")

        # Check for empty DataFrame
        if len(df) == 0:
            errors.append("DataFrame is empty")

        # Check Anchor column values
        if 'Anchor' in df.columns:
            valid_anchors = df['Anchor'].isin(['T', 'F', True, False])
            if not valid_anchors.all():
                errors.append("Anchor column must contain only 'T' or 'F' values")

        # Check compound name format (basic validation)
        if 'Name' in df.columns:
            # Basic pattern check: should have parentheses
            invalid_names = df[~df['Name'].str.contains(r'\(.*\)', na=False)]
            if not invalid_names.empty:
                errors.append(
                    f"Invalid compound name format in {len(invalid_names)} rows. "
                    "Expected format: PREFIX(a:b;c)"
                )

        return len(errors) == 0, errors

    def process_data(
        self,
        df: pd.DataFrame,
        data_type: str = "Porcine"
    ) -> Dict[str, Any]:
        """
        Main data processing function.
        Applies 5 rules sequentially for data classification.

        Args:
            df: Input DataFrame with compound data
            data_type: Type of data (Porcine, Human, etc.)

        Returns:
            Dictionary with analysis results
        """
        logger.info(f"Starting analysis: {len(df)} compounds, mode: {data_type}")

        # Validate input
        is_valid, validation_errors = self.validate_input_data(df)
        if not is_valid:
            logger.error(f"Input validation failed: {validation_errors}")
            return {
                "success": False,
                "errors": validation_errors,
                "statistics": {"total_compounds": len(df)}
            }

        try:
            # Data preprocessing
            df_processed = self._preprocess_data(df.copy())
            logger.info(f"Preprocessing complete: {len(df_processed)} compounds")

            # Rule 1: Prefix-based regression analysis
            logger.info("Rule 1: Running prefix-based regression analysis...")
            rule1_results = self._apply_rule1_prefix_regression(df_processed)
            logger.info(
                f"  - Regression groups: {len(rule1_results['regression_results'])}, "
                f"Valid compounds: {len(rule1_results['valid_compounds'])}, "
                f"Outliers: {len(rule1_results['outliers'])}"
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

            # Compile final results
            logger.info("Compiling final results...")
            final_results = self._compile_results(
                df_processed, rule1_results, rule23_results, rule4_results, rule5_results
            )

            success_rate = final_results['statistics']['success_rate']
            logger.info(f"Analysis complete: {success_rate:.1f}% success rate")

            return final_results

        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "statistics": {"total_compounds": len(df)}
            }

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Data preprocessing: extract prefix, suffix, and structural components.

        Args:
            df: Input DataFrame

        Returns:
            Processed DataFrame with extracted features
        """
        # Extract prefix and suffix from Name column
        df["prefix"] = df["Name"].str.extract(r"^([^(]+)")[0]
        df["suffix"] = df["Name"].str.extract(r"\(([^)]+)\)")[0]

        # Extract a, b, c components from suffix (36:1;O2 format)
        suffix_parts = df["suffix"].str.extract(r"(\d+):(\d+);(\w+)")
        df["a_component"] = pd.to_numeric(suffix_parts[0], errors="coerce")  # Carbon count
        df["b_component"] = pd.to_numeric(suffix_parts[1], errors="coerce")  # Unsaturation
        df["c_component"] = suffix_parts[2]  # Oxygen component

        # Remove modifications from prefix for base comparison
        df["base_prefix"] = df["prefix"].str.replace(r"\+.*", "", regex=True)

        # Data quality check
        invalid_rows = df[df["prefix"].isna() | df["suffix"].isna()].index
        if len(invalid_rows) > 0:
            logger.warning(f"Found {len(invalid_rows)} rows with invalid format, removing...")
            df = df.drop(invalid_rows)

        # Convert Anchor column to boolean if needed
        if df["Anchor"].dtype == 'object':
            df["Anchor"] = df["Anchor"] == "T"

        return df

    def _apply_rule1_prefix_regression(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Rule 1: Prefix-based regression analysis using improved model.
        Groups by prefix and validates Log P-RT linearity.

        Args:
            df: Preprocessed DataFrame

        Returns:
            Dictionary with regression results and compound classification
        """
        regression_results = {}
        valid_compounds = []
        outliers = []
        model_warnings = []

        # Group by prefix
        for prefix in df["prefix"].unique():
            if pd.isna(prefix):
                continue

            prefix_group = df[df["prefix"] == prefix].copy()
            n_total = len(prefix_group)

            # Check if we have enough samples
            anchor_compounds = prefix_group[prefix_group["Anchor"] == True]
            n_anchors = len(anchor_compounds)

            logger.info(
                f"Processing prefix {prefix}: {n_total} total, {n_anchors} anchors"
            )

            if n_anchors < self.min_samples_for_regression:
                # Insufficient samples for regression
                if n_anchors > 0:
                    # Mark anchors as valid (trusted)
                    for _, row in anchor_compounds.iterrows():
                        compound = row.to_dict()
                        compound["predicted_rt"] = compound["RT"]
                        compound["residual"] = 0.0
                        compound["std_residual"] = 0.0
                        compound["regression_group"] = f"{prefix}_trusted"
                        valid_compounds.append(compound)

                # Mark non-anchors as uncertain
                non_anchors = prefix_group[prefix_group["Anchor"] == False]
                for _, row in non_anchors.iterrows():
                    row_dict = row.to_dict()
                    row_dict["outlier_reason"] = (
                        f"Rule 1: Insufficient anchor compounds ({n_anchors} < "
                        f"{self.min_samples_for_regression}) for regression"
                    )
                    outliers.append(row_dict)

                model_warnings.append(
                    f"{prefix}: Only {n_anchors} anchors, skipped regression"
                )
                continue

            # Fit improved regression model
            regression_result = self.regression_model.fit_regression(
                prefix_group,
                prefix,
                anchor_only=True
            )

            if regression_result['success']:
                # Save regression results
                regression_results[prefix] = {
                    'features': regression_result['features'],
                    'coefficients': regression_result['coefficients'],
                    'equation': regression_result['equation'],
                    'metrics': regression_result['metrics'],
                    'n_samples': n_total,
                    'n_anchors': n_anchors
                }

                # Check for overfitting warning
                if 'warning' in regression_result['metrics']:
                    model_warnings.append(
                        f"{prefix}: {regression_result['metrics']['warning']}"
                    )

                # Classify compounds based on residuals
                predictions = regression_result['predictions']
                std_residuals = regression_result['standardized_residuals']

                for idx, (_, row) in enumerate(prefix_group.iterrows()):
                    row_dict = row.to_dict()
                    row_dict["predicted_rt"] = float(predictions[idx])
                    row_dict["residual"] = float(regression_result['residuals'][idx])
                    row_dict["std_residual"] = float(std_residuals[idx])
                    row_dict["regression_group"] = prefix

                    if abs(std_residuals[idx]) < self.outlier_threshold:
                        valid_compounds.append(row_dict)
                    else:
                        row_dict["outlier_reason"] = (
                            f"Rule 1: Standardized residual = {std_residuals[idx]:.3f} "
                            f"exceeds threshold {self.outlier_threshold}"
                        )
                        outliers.append(row_dict)

            else:
                # Regression failed
                regression_results[prefix] = {
                    'success': False,
                    'reason': regression_result['reason'],
                    'n_samples': n_total,
                    'n_anchors': n_anchors
                }

                model_warnings.append(
                    f"{prefix}: Regression failed - {regression_result['reason']}"
                )

                # Mark all compounds as outliers
                for _, row in prefix_group.iterrows():
                    row_dict = row.to_dict()
                    row_dict["outlier_reason"] = f"Rule 1: {regression_result['reason']}"
                    outliers.append(row_dict)

        return {
            "regression_results": regression_results,
            "valid_compounds": valid_compounds,
            "outliers": outliers,
            "model_warnings": model_warnings
        }

    def _apply_rule2_3_sugar_count(
        self,
        df: pd.DataFrame,
        data_type: str
    ) -> Dict[str, Any]:
        """
        Rule 2-3: Calculate sugar counts and identify isomers.

        Args:
            df: Preprocessed DataFrame
            data_type: Type of data

        Returns:
            Dictionary with sugar analysis results
        """
        sugar_analysis = {}

        for _, row in df.iterrows():
            name = row["Name"]
            prefix = row["base_prefix"]

            # Parse prefix to extract sugar information
            sugar_info = self._parse_sugar_composition(prefix)

            # Check for potential isomers
            can_have_isomers = self._check_isomer_possibility(prefix, sugar_info)

            sugar_analysis[name] = {
                "prefix": prefix,
                "sugar_count": sugar_info.get("total_sugars", 0),
                "sialic_acid_count": sugar_info.get("sialic_acids", 0),
                "can_have_isomers": can_have_isomers,
                "isomer_type": sugar_info.get("isomer_type", ""),
                "data_type": data_type
            }

        return {"sugar_analysis": sugar_analysis}

    def _apply_rule4_oacetylation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Rule 4: Validate O-acetylation effects on retention time.

        Args:
            df: Preprocessed DataFrame

        Returns:
            Dictionary with O-acetylation validation results
        """
        valid_oacetyl = []
        invalid_oacetyl = []

        # Find O-acetylated compounds
        oacetyl_compounds = df[df["prefix"].str.contains(r"\+OAc", na=False)]

        for _, oac_row in oacetyl_compounds.iterrows():
            # Find base compound (without OAc)
            base_name = oac_row["prefix"].replace("+OAc", "")
            base_suffix = oac_row["suffix"]

            # Find matching base compound
            base_compound = df[
                (df["prefix"] == base_name) &
                (df["suffix"] == base_suffix)
            ]

            if not base_compound.empty:
                base_rt = base_compound.iloc[0]["RT"]
                oac_rt = oac_row["RT"]

                # O-acetylation should increase retention time
                if oac_rt > base_rt:
                    valid_oacetyl.append({
                        "compound": oac_row["Name"],
                        "base_compound": base_compound.iloc[0]["Name"],
                        "rt_increase": oac_rt - base_rt,
                        "valid": True
                    })
                else:
                    invalid_oacetyl.append({
                        "compound": oac_row["Name"],
                        "base_compound": base_compound.iloc[0]["Name"],
                        "rt_difference": oac_rt - base_rt,
                        "valid": False,
                        "reason": "O-acetylation did not increase RT"
                    })
            else:
                # No matching base compound found
                invalid_oacetyl.append({
                    "compound": oac_row["Name"],
                    "valid": False,
                    "reason": "No matching base compound found"
                })

        return {
            "valid_oacetyl": valid_oacetyl,
            "invalid_oacetyl": invalid_oacetyl
        }

    def _apply_rule5_rt_filtering(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Rule 5: RT-based filtering and in-source fragmentation detection.

        Args:
            df: Preprocessed DataFrame

        Returns:
            Dictionary with fragmentation detection results
        """
        fragmentation_candidates = []
        filtered_compounds = []
        consolidated_compounds = {}

        # Group by suffix (lipid composition)
        for suffix in df["suffix"].unique():
            if pd.isna(suffix):
                continue

            suffix_group = df[df["suffix"] == suffix].sort_values("RT")

            # Check for compounds within RT tolerance
            for i, row in suffix_group.iterrows():
                rt = row["RT"]
                name = row["Name"]

                # Find other compounds within RT tolerance
                nearby_compounds = suffix_group[
                    (abs(suffix_group["RT"] - rt) <= self.rt_tolerance) &
                    (suffix_group.index != i)
                ]

                if not nearby_compounds.empty:
                    # Potential fragmentation detected
                    # Keep compound with highest sugar count (least fragmented)
                    all_candidates = pd.concat([
                        pd.DataFrame([row]),
                        nearby_compounds
                    ])

                    # Get sugar counts
                    sugar_counts = []
                    for _, cand in all_candidates.iterrows():
                        sugar_info = self._parse_sugar_composition(cand["base_prefix"])
                        sugar_counts.append(sugar_info.get("total_sugars", 0))

                    # Select compound with maximum sugar count
                    max_sugar_idx = np.argmax(sugar_counts)
                    selected = all_candidates.iloc[max_sugar_idx]

                    # Record fragmentation event
                    if len(all_candidates) > 1:
                        fragmentation_candidates.append({
                            "selected": selected["Name"],
                            "fragments": all_candidates["Name"].tolist(),
                            "rt_range": (
                                all_candidates["RT"].min(),
                                all_candidates["RT"].max()
                            ),
                            "consolidated_volume": all_candidates["Volume"].sum()
                        })

                    # Add to filtered list (avoid duplicates)
                    if selected["Name"] not in consolidated_compounds:
                        consolidated_compounds[selected["Name"]] = {
                            **selected.to_dict(),
                            "consolidated": True,
                            "fragment_count": len(all_candidates)
                        }

        # Add compounds that weren't involved in fragmentation
        for _, row in df.iterrows():
            if row["Name"] not in consolidated_compounds:
                filtered_compounds.append(row.to_dict())
            else:
                filtered_compounds.append(consolidated_compounds[row["Name"]])

        return {
            "fragmentation_candidates": fragmentation_candidates,
            "filtered_compounds": filtered_compounds
        }

    def _parse_sugar_composition(self, prefix: str) -> Dict[str, Any]:
        """
        Parse sugar composition from ganglioside prefix.

        Args:
            prefix: Ganglioside prefix (e.g., GD1, GM3, GT1)

        Returns:
            Dictionary with sugar composition details
        """
        # Extract components (G[e][f] format)
        if not prefix or len(prefix) < 2:
            return {}

        # Map for sialic acid count
        sialic_map = {'M': 1, 'D': 2, 'T': 3, 'Q': 4, 'P': 5, 'A': 0}

        try:
            # Extract e (sialic acid indicator)
            e_value = prefix[1] if len(prefix) > 1 else ''
            sialic_acids = sialic_map.get(e_value, 0)

            # Extract f (remaining sugars)
            f_value = int(prefix[2]) if len(prefix) > 2 and prefix[2].isdigit() else 0

            # Calculate total sugars
            total_sugars = sialic_acids + (5 - f_value) if f_value > 0 else sialic_acids

            # Check for known isomer types
            isomer_type = ""
            if prefix in ['GD1', 'GT1', 'GQ1'] and f_value == 1:
                isomer_type = f"{prefix}a/b"

            return {
                "sialic_acids": sialic_acids,
                "total_sugars": total_sugars,
                "isomer_type": isomer_type,
                "e_value": e_value,
                "f_value": f_value
            }

        except Exception as e:
            logger.warning(f"Failed to parse sugar composition for {prefix}: {e}")
            return {}

    def _check_isomer_possibility(
        self,
        prefix: str,
        sugar_info: Dict[str, Any]
    ) -> bool:
        """Check if a compound can have structural isomers."""
        # Known isomer patterns
        isomer_prefixes = ['GD1', 'GT1', 'GQ1']
        f_value = sugar_info.get('f_value', 0)

        return prefix in isomer_prefixes and f_value == 1

    def _compile_results(
        self,
        df: pd.DataFrame,
        rule1_results: Dict[str, Any],
        rule23_results: Dict[str, Any],
        rule4_results: Dict[str, Any],
        rule5_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compile all rule results into final output."""
        # Calculate statistics
        total_compounds = len(df)
        anchor_compounds = len(df[df["Anchor"] == True])
        valid_compounds = len(rule1_results["valid_compounds"])
        outlier_count = len(rule1_results["outliers"])
        success_rate = (valid_compounds / total_compounds * 100) if total_compounds > 0 else 0

        # Categorize compounds
        categorization = self.categorizer.categorize_compounds(df.to_dict('records'))

        return {
            "success": True,
            "statistics": {
                "total_compounds": total_compounds,
                "anchor_compounds": anchor_compounds,
                "valid_compounds": valid_compounds,
                "outlier_count": outlier_count,
                "success_rate": success_rate
            },
            "regression_analysis": rule1_results["regression_results"],
            "model_warnings": rule1_results.get("model_warnings", []),
            "valid_compounds": rule1_results["valid_compounds"],
            "outliers": rule1_results["outliers"],
            "sugar_analysis": rule23_results["sugar_analysis"],
            "oacetylation_analysis": {
                "valid": rule4_results["valid_oacetyl"],
                "invalid": rule4_results["invalid_oacetyl"]
            },
            "rt_filtering_summary": {
                "fragmentation_events": rule5_results["fragmentation_candidates"],
                "filtered_compounds": rule5_results["filtered_compounds"]
            },
            "categorization": categorization
        }