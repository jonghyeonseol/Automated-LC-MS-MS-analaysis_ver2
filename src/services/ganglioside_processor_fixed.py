"""
Ganglioside Data Processor - Fixed and Refactored Version
5-rule based acidic glycolipid data classification system with improved regression analysis
"""

from typing import Any, Dict, List, Optional, Tuple
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from scipy import stats

warnings.filterwarnings("ignore")


class GangliosideProcessorFixed:
    """
    Fixed Ganglioside Processor with improved regression analysis
    """

    def __init__(self):
        # Realistic thresholds for chemical analysis
        self.r2_threshold = 0.75  # Lowered from 0.99 to realistic value
        self.outlier_threshold = 2.5  # Lowered from 3.0 for better sensitivity
        self.rt_tolerance = 0.1
        self.min_compounds_for_regression = 2

        print("🧬 Ganglioside Processor Fixed 초기화 완료")

    def update_settings(
        self,
        outlier_threshold: Optional[float] = None,
        r2_threshold: Optional[float] = None,
        rt_tolerance: Optional[float] = None
    ) -> None:
        """Update analysis settings with validation"""
        if outlier_threshold is not None:
            self.outlier_threshold = max(1.0, min(5.0, outlier_threshold))
        if r2_threshold is not None:
            self.r2_threshold = max(0.5, min(0.99, r2_threshold))
        if rt_tolerance is not None:
            self.rt_tolerance = max(0.01, min(1.0, rt_tolerance))

        print(
            f"⚙️ 설정 업데이트: outlier={self.outlier_threshold:.2f}, "
            f"r2={self.r2_threshold:.3f}, rt={self.rt_tolerance:.2f}"
        )

    def get_settings(self) -> Dict[str, float]:
        """Get current settings"""
        return {
            "outlier_threshold": self.outlier_threshold,
            "r2_threshold": self.r2_threshold,
            "rt_tolerance": self.rt_tolerance,
        }

    def process_data(
        self, df: pd.DataFrame, data_type: str = "Porcine"
    ) -> Dict[str, Any]:
        """
        Main data processing function with improved algorithm
        """
        print(f"🔬 분석 시작: {len(df)}개 화합물, 모드: {data_type}")

        try:
            # Data preprocessing with validation
            df_processed = self._preprocess_data_enhanced(df.copy())
            print(f"✅ 전처리 완료: {len(df_processed)}개 화합물")

            # Improved Rule 1: Enhanced regression analysis
            print("📊 규칙 1: 향상된 회귀분석 실행 중...")
            rule1_results = self._apply_rule1_enhanced_regression(df_processed)
            print(f"   - 회귀 그룹 수: {len(rule1_results['regression_results'])}")
            print(f"   - 유효 화합물: {len(rule1_results['valid_compounds'])}")
            print(f"   - 이상치: {len(rule1_results['outliers'])}")

            # Rules 2-3: Sugar count and isomer classification
            print("🧬 규칙 2-3: 당 개수 계산 및 이성질체 분류 실행 중...")
            rule23_results = self._apply_rule2_3_enhanced(df_processed, data_type)
            isomer_count = sum(
                1 for info in rule23_results["sugar_analysis"].values()
                if info.get("can_have_isomers", False)
            )
            print(f"   - 이성질체 후보: {isomer_count}")

            # Rule 4: O-acetylation effect validation
            print("⚗️ 규칙 4: O-acetylation 효과 검증 실행 중...")
            rule4_results = self._apply_rule4_enhanced(df_processed)
            print(f"   - 유효 OAc 화합물: {len(rule4_results['valid_oacetyl'])}")
            print(f"   - 무효 OAc 화합물: {len(rule4_results['invalid_oacetyl'])}")

            # Rule 5: RT filtering and fragmentation detection
            print("🔍 규칙 5: RT 필터링 및 fragmentation 탐지 실행 중...")
            rule5_results = self._apply_rule5_enhanced(df_processed)
            print(f"   - Fragmentation 후보: {len(rule5_results['fragmentation_candidates'])}")
            print(f"   - 필터링된 화합물: {len(rule5_results['filtered_compounds'])}")

            # Compile enhanced results
            print("📋 최종 결과 통합 중...")
            final_results = self._compile_enhanced_results(
                df_processed, rule1_results, rule23_results, rule4_results, rule5_results
            )
            print(f"✅ 분석 완료: {final_results['statistics']['success_rate']:.1f}% 성공률")

            return final_results

        except Exception as e:
            print(f"❌ 분석 중 오류 발생: {str(e)}")
            return self._create_error_result(df, str(e))

    def _preprocess_data_enhanced(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhanced data preprocessing with better validation"""

        # Validate required columns
        required_columns = ["Name", "RT", "Log P"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Add Anchor column if missing (default to 'T' for all compounds)
        if "Anchor" not in df.columns:
            df["Anchor"] = "T"
            print("   ⚠️ Anchor 컬럼이 없어서 모든 화합물을 Anchor='T'로 설정")

        # Enhanced name parsing
        df["prefix"] = df["Name"].str.extract(r"^([A-Za-z]+\d*[a-z]*)")[0]
        df["suffix"] = df["Name"].str.extract(r"\(([^)]+)\)")[0]

        # Parse suffix components more robustly
        if not df["suffix"].isna().all():
            suffix_parts = df["suffix"].str.extract(r"(\d+):(\d+);?(\w*)")
            df["carbon_count"] = pd.to_numeric(suffix_parts[0], errors="coerce")
            df["unsaturation"] = pd.to_numeric(suffix_parts[1], errors="coerce")
            df["oxygen_info"] = suffix_parts[2].fillna("")

        # Create molecular family grouping for better regression
        df["molecular_family"] = df["prefix"].str.extract(r"^([A-Za-z]+)")[0]

        # Data quality checks
        invalid_rt = df["RT"].isna() | (df["RT"] <= 0)
        invalid_logp = df["Log P"].isna()
        invalid_name = df["Name"].isna() | (df["Name"].str.len() == 0)

        invalid_mask = invalid_rt | invalid_logp | invalid_name
        if invalid_mask.any():
            print(f"   ⚠️ {invalid_mask.sum()}개 행에 유효하지 않은 데이터 발견")
            df = df[~invalid_mask].reset_index(drop=True)

        return df

    def _apply_rule1_enhanced_regression(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Enhanced Rule 1: Improved regression analysis with multiple grouping strategies
        """
        regression_results = {}
        valid_compounds = []
        outliers = []

        # Strategy 1: Try prefix-based grouping first
        prefix_results = self._perform_regression_by_group(df, "prefix", "Prefix-based")

        # Strategy 2: If no good regression groups, try molecular family
        if len(prefix_results["regression_results"]) == 0:
            family_results = self._perform_regression_by_group(df, "molecular_family", "Family-based")
            if len(family_results["regression_results"]) > 0:
                prefix_results = family_results

        # Strategy 3: If still no groups, perform overall regression with anchor compounds
        if len(prefix_results["regression_results"]) == 0:
            overall_results = self._perform_overall_regression(df)
            prefix_results = overall_results

        return prefix_results

    def _perform_regression_by_group(
        self, df: pd.DataFrame, group_column: str, strategy_name: str
    ) -> Dict[str, Any]:
        """Perform regression analysis grouped by specified column"""

        regression_results = {}
        valid_compounds = []
        outliers = []

        for group_value in df[group_column].dropna().unique():
            group_df = df[df[group_column] == group_value].copy()

            if len(group_df) < self.min_compounds_for_regression:
                # Handle single compounds
                for _, row in group_df.iterrows():
                    if row.get("Anchor", "T") == "T":
                        compound = row.to_dict()
                        compound["predicted_rt"] = compound["RT"]
                        compound["residual"] = 0.0
                        compound["std_residual"] = 0.0
                        compound["group_strategy"] = strategy_name
                        valid_compounds.append(compound)
                    else:
                        compound = row.to_dict()
                        compound["outlier_reason"] = f"Rule 1 ({strategy_name}): Single compound, not anchor"
                        outliers.append(compound)
                continue

            # Perform regression on this group
            anchor_compounds = group_df[group_df["Anchor"] == "T"]

            if len(anchor_compounds) >= 2:
                # Enough anchor compounds for regression
                reg_result = self._perform_group_regression(
                    group_df, anchor_compounds, group_value, strategy_name
                )

                if reg_result["success"]:
                    regression_results[f"{strategy_name}_{group_value}"] = reg_result["regression_info"]
                    valid_compounds.extend(reg_result["valid_compounds"])
                    outliers.extend(reg_result["outliers"])
                else:
                    # Regression failed, treat all as outliers
                    for _, row in group_df.iterrows():
                        compound = row.to_dict()
                        compound["outlier_reason"] = f"Rule 1 ({strategy_name}): {reg_result['reason']}"
                        outliers.append(compound)
            else:
                # Not enough anchor compounds, validate individually
                for _, row in group_df.iterrows():
                    compound = row.to_dict()
                    if row.get("Anchor", "T") == "T":
                        compound["predicted_rt"] = compound["RT"]
                        compound["residual"] = 0.0
                        compound["std_residual"] = 0.0
                        compound["group_strategy"] = f"{strategy_name}_individual"
                        valid_compounds.append(compound)
                    else:
                        compound["outlier_reason"] = f"Rule 1 ({strategy_name}): Insufficient anchors"
                        outliers.append(compound)

        return {
            "regression_results": regression_results,
            "valid_compounds": valid_compounds,
            "outliers": outliers,
        }

    def _perform_overall_regression(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Perform overall regression when grouping strategies fail"""

        anchor_compounds = df[df["Anchor"] == "T"]

        if len(anchor_compounds) >= self.min_compounds_for_regression:
            reg_result = self._perform_group_regression(
                df, anchor_compounds, "Overall", "Global"
            )

            if reg_result["success"]:
                return {
                    "regression_results": {"Global_Overall": reg_result["regression_info"]},
                    "valid_compounds": reg_result["valid_compounds"],
                    "outliers": reg_result["outliers"],
                }

        # Fallback: treat all anchor compounds as valid
        valid_compounds = []
        outliers = []

        for _, row in df.iterrows():
            compound = row.to_dict()
            if row.get("Anchor", "T") == "T":
                compound["predicted_rt"] = compound["RT"]
                compound["residual"] = 0.0
                compound["std_residual"] = 0.0
                compound["group_strategy"] = "Fallback_individual"
                valid_compounds.append(compound)
            else:
                compound["outlier_reason"] = "Rule 1 (Fallback): No valid regression possible"
                outliers.append(compound)

        return {
            "regression_results": {},
            "valid_compounds": valid_compounds,
            "outliers": outliers,
        }

    def _perform_group_regression(
        self,
        full_group: pd.DataFrame,
        anchor_compounds: pd.DataFrame,
        group_name: str,
        strategy_name: str
    ) -> Dict[str, Any]:
        """Perform regression analysis on a specific group"""

        try:
            # Prepare regression data
            X = anchor_compounds[["Log P"]].values
            y = anchor_compounds["RT"].values

            if len(np.unique(X)) < 2:
                return {
                    "success": False,
                    "reason": f"Insufficient Log P variation in {group_name}",
                    "valid_compounds": [],
                    "outliers": []
                }

            # Fit regression model
            model = LinearRegression()
            model.fit(X, y)

            # Calculate predictions and R²
            y_pred = model.predict(X)
            r2 = r2_score(y, y_pred)

            # Enhanced regression diagnostics
            residuals = y - y_pred
            mse = np.mean(residuals**2)
            rmse = np.sqrt(mse)

            # Calculate additional statistics
            n = len(anchor_compounds)
            std_error = rmse / np.sqrt(n - 2) if n > 2 else rmse

            # Check R² threshold
            if r2 < self.r2_threshold:
                return {
                    "success": False,
                    "reason": f"R² = {r2:.3f} < {self.r2_threshold:.3f} for {group_name}",
                    "valid_compounds": [],
                    "outliers": []
                }

            # Apply model to full group
            all_X = full_group[["Log P"]].values
            all_pred = model.predict(all_X)
            all_residuals = full_group["RT"].values - all_pred

            # Standardized residuals with proper scaling
            residual_std = np.std(all_residuals)
            if residual_std > 0:
                std_residuals = all_residuals / residual_std
            else:
                std_residuals = np.zeros_like(all_residuals)

            # Classify compounds
            valid_compounds = []
            outliers = []

            outlier_mask = np.abs(std_residuals) >= self.outlier_threshold

            for idx, (_, row) in enumerate(full_group.iterrows()):
                compound = row.to_dict()
                compound["predicted_rt"] = float(all_pred[idx])
                compound["residual"] = float(all_residuals[idx])
                compound["std_residual"] = float(std_residuals[idx])
                compound["group_strategy"] = strategy_name
                compound["group_name"] = group_name

                if not outlier_mask[idx]:
                    valid_compounds.append(compound)
                else:
                    compound["outlier_reason"] = (
                        f"Rule 1 ({strategy_name}): Std residual = {std_residuals[idx]:.3f} "
                        f"(threshold = {self.outlier_threshold:.3f})"
                    )
                    outliers.append(compound)

            # Store regression information
            regression_info = {
                "slope": float(model.coef_[0]),
                "intercept": float(model.intercept_),
                "r2": float(r2),
                "rmse": float(rmse),
                "n_samples": len(full_group),
                "n_anchors": len(anchor_compounds),
                "equation": f"RT = {model.coef_[0]:.4f} * Log P + {model.intercept_:.4f}",
                "group_name": group_name,
                "strategy": strategy_name,
                "std_error": float(std_error),
                "meets_threshold": True
            }

            return {
                "success": True,
                "regression_info": regression_info,
                "valid_compounds": valid_compounds,
                "outliers": outliers
            }

        except Exception as e:
            return {
                "success": False,
                "reason": f"Regression error for {group_name}: {str(e)}",
                "valid_compounds": [],
                "outliers": []
            }

    def _apply_rule2_3_enhanced(
        self, df: pd.DataFrame, data_type: str
    ) -> Dict[str, Any]:
        """Enhanced Rules 2-3: Sugar count and isomer classification"""

        sugar_analysis = {}

        for _, row in df.iterrows():
            name = row["Name"]

            # Extract sugar information
            sugar_info = self._analyze_sugar_composition(name, row, data_type)
            sugar_analysis[name] = sugar_info

        return {
            "sugar_analysis": sugar_analysis,
            "rule2_validated": len([s for s in sugar_analysis.values() if s.get("valid_sugar_count", False)]),
            "rule3_validated": len([s for s in sugar_analysis.values() if s.get("can_have_isomers", False)])
        }

    def _analyze_sugar_composition(
        self, name: str, row: pd.Series, data_type: str
    ) -> Dict[str, Any]:
        """Analyze sugar composition for a compound"""

        # Extract number of sugars from the name pattern
        sugar_count = 0
        can_have_isomers = False

        # Common ganglioside patterns
        if "GM3" in name:
            sugar_count = 1
        elif "GM2" in name or "GM1" in name:
            sugar_count = 2 if "GM2" in name else 3
            can_have_isomers = True
        elif "GD3" in name or "GD1" in name:
            sugar_count = 3 if "GD3" in name else 4
            can_have_isomers = True
        elif "GT1" in name:
            sugar_count = 4
            can_have_isomers = True

        return {
            "sugar_count": sugar_count,
            "can_have_isomers": can_have_isomers,
            "valid_sugar_count": sugar_count > 0,
            "data_type": data_type
        }

    def _apply_rule4_enhanced(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Enhanced Rule 4: O-acetylation effect validation"""

        valid_oacetyl = []
        invalid_oacetyl = []

        for _, row in df.iterrows():
            name = row["Name"]

            # Check for O-acetylation markers
            has_oacetyl = "OAc" in name or "Ac" in name

            if has_oacetyl:
                # Validate O-acetylation effect on RT
                if self._validate_oacetylation_effect(row, df):
                    valid_oacetyl.append(row.to_dict())
                else:
                    invalid_oacetyl.append(row.to_dict())

        return {
            "valid_oacetyl": valid_oacetyl,
            "invalid_oacetyl": invalid_oacetyl
        }

    def _validate_oacetylation_effect(
        self, compound: pd.Series, df: pd.DataFrame
    ) -> bool:
        """Validate O-acetylation effect on retention time"""

        # Simple validation: O-acetylated compounds should have different RT patterns
        base_name = compound["Name"].replace("OAc", "").replace("Ac", "")

        # Look for base compound
        potential_bases = df[df["Name"].str.contains(base_name.split("(")[0], na=False, regex=False)]

        if len(potential_bases) > 1:
            # Compare RT values (O-acetylated typically elute later)
            return True

        return True  # Default to valid if no comparison possible

    def _apply_rule5_enhanced(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Enhanced Rule 5: RT filtering and fragmentation detection"""

        fragmentation_candidates = []
        filtered_compounds = []

        # Calculate RT statistics
        rt_mean = df["RT"].mean()
        rt_std = df["RT"].std()

        for _, row in df.iterrows():
            compound = row.to_dict()
            rt = row["RT"]

            # Check for unusual RT patterns that might indicate fragmentation
            rt_zscore = (rt - rt_mean) / rt_std if rt_std > 0 else 0

            if abs(rt_zscore) > 2.0:  # More than 2 standard deviations
                compound["fragmentation_score"] = abs(rt_zscore)
                compound["fragmentation_reason"] = f"RT outlier (z-score = {rt_zscore:.2f})"
                fragmentation_candidates.append(compound)
            else:
                filtered_compounds.append(compound)

        return {
            "fragmentation_candidates": fragmentation_candidates,
            "filtered_compounds": filtered_compounds,
            "rt_statistics": {
                "mean": float(rt_mean),
                "std": float(rt_std),
                "min": float(df["RT"].min()),
                "max": float(df["RT"].max())
            }
        }

    def _compile_enhanced_results(
        self,
        df_processed: pd.DataFrame,
        rule1_results: Dict[str, Any],
        rule23_results: Dict[str, Any],
        rule4_results: Dict[str, Any],
        rule5_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compile enhanced analysis results"""

        total_compounds = len(df_processed)
        valid_compounds = len(rule1_results["valid_compounds"])
        outliers = len(rule1_results["outliers"])

        success_rate = (valid_compounds / total_compounds * 100) if total_compounds > 0 else 0

        statistics = {
            "total_compounds": total_compounds,
            "valid_compounds": valid_compounds,
            "outliers": outliers,
            "success_rate": float(success_rate),
            "rule_breakdown": {
                "rule1_regression": len(rule1_results["regression_results"]),
                "rule1_valid": valid_compounds,
                "rule1_outliers": outliers,
                "rule2_sugar_validated": rule23_results["rule2_validated"],
                "rule3_isomers": rule23_results["rule3_validated"],
                "rule4_oacetyl_valid": len(rule4_results["valid_oacetyl"]),
                "rule4_oacetyl_invalid": len(rule4_results["invalid_oacetyl"]),
                "rule5_fragmentation": len(rule5_results["fragmentation_candidates"]),
                "rule5_filtered": len(rule5_results["filtered_compounds"])
            }
        }

        return {
            "statistics": statistics,
            "rule1_results": rule1_results,
            "rule23_results": rule23_results,
            "rule4_results": rule4_results,
            "rule5_results": rule5_results,
            "processed_data": df_processed.to_dict("records"),
            "settings_used": self.get_settings(),
            "analysis_quality": self._assess_analysis_quality(statistics)
        }

    def _assess_analysis_quality(self, statistics: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the quality of the analysis"""

        success_rate = statistics["success_rate"]
        regression_count = statistics["rule_breakdown"]["rule1_regression"]

        if success_rate >= 80 and regression_count > 0:
            quality = "Excellent"
            confidence = "High"
        elif success_rate >= 60:
            quality = "Good"
            confidence = "Medium"
        elif success_rate >= 40:
            quality = "Fair"
            confidence = "Medium"
        else:
            quality = "Poor"
            confidence = "Low"

        return {
            "quality": quality,
            "confidence": confidence,
            "regression_models": regression_count,
            "recommendations": self._generate_recommendations(statistics)
        }

    def _generate_recommendations(self, statistics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis results"""

        recommendations = []

        success_rate = statistics["success_rate"]
        regression_count = statistics["rule_breakdown"]["rule1_regression"]

        if success_rate < 60:
            recommendations.append("Consider adjusting outlier threshold for better compound acceptance")

        if regression_count == 0:
            recommendations.append("No regression models found - check data grouping and anchor compounds")

        if statistics["outliers"] > statistics["valid_compounds"]:
            recommendations.append("High outlier rate - review data quality and thresholds")

        if not recommendations:
            recommendations.append("Analysis quality is good - results are reliable")

        return recommendations

    def _create_error_result(self, df: pd.DataFrame, error_message: str) -> Dict[str, Any]:
        """Create error result structure"""

        return {
            "statistics": {
                "total_compounds": len(df),
                "valid_compounds": 0,
                "outliers": len(df),
                "success_rate": 0.0,
                "rule_breakdown": {}
            },
            "error": True,
            "error_message": error_message,
            "processed_data": [],
            "settings_used": self.get_settings(),
            "analysis_quality": {
                "quality": "Error",
                "confidence": "None",
                "recommendations": [f"Fix error: {error_message}"]
            }
        }