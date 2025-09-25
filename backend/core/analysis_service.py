"""
Analysis Service - Refactored core analysis orchestration
Coordinates different analysis modules and provides a clean interface
"""

from typing import Any, Dict, Optional
import pandas as pd
from ..services.ganglioside_processor_fixed import GangliosideProcessorFixed
from ..services.regression_analyzer import RegressionAnalyzer
from ..services.visualization_service import VisualizationService


class AnalysisService:
    """
    Central analysis service that orchestrates all analysis components
    """

    def __init__(self):
        """Initialize all analysis components"""
        self.ganglioside_processor = GangliosideProcessorFixed()
        self.regression_analyzer = RegressionAnalyzer()
        self.visualization_service = VisualizationService()

        print("🚀 Analysis Service 초기화 완료")

    def update_settings(
        self,
        outlier_threshold: Optional[float] = None,
        r2_threshold: Optional[float] = None,
        rt_tolerance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update analysis settings across all components"""

        # Update ganglioside processor settings
        self.ganglioside_processor.update_settings(
            outlier_threshold=outlier_threshold,
            r2_threshold=r2_threshold,
            rt_tolerance=rt_tolerance
        )

        # Update regression analyzer settings
        if outlier_threshold is not None:
            self.regression_analyzer.outlier_threshold = outlier_threshold
        if r2_threshold is not None:
            self.regression_analyzer.r2_threshold = r2_threshold

        return self.get_current_settings()

    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings from all components"""
        return {
            "ganglioside_processor": self.ganglioside_processor.get_settings(),
            "regression_analyzer": {
                "outlier_threshold": self.regression_analyzer.outlier_threshold,
                "r2_threshold": self.regression_analyzer.r2_threshold,
            }
        }

    def analyze_data(
        self,
        df: pd.DataFrame,
        data_type: str = "Porcine",
        include_advanced_regression: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive data analysis

        Args:
            df: Input dataframe with compound data
            data_type: Type of data analysis (e.g., "Porcine")
            include_advanced_regression: Whether to include advanced regression analysis

        Returns:
            Comprehensive analysis results
        """

        try:
            print(f"🧬 분석 서비스 시작: {len(df)}개 화합물 분석")

            # Primary analysis with fixed ganglioside processor
            primary_results = self.ganglioside_processor.process_data(df, data_type)

            # Enhanced regression analysis if requested and we have valid data
            enhanced_regression = None
            if include_advanced_regression and len(primary_results.get("rule1_results", {}).get("valid_compounds", [])) >= 2:
                try:
                    print("🔬 고급 회귀분석 수행 중...")
                    enhanced_regression = self._perform_enhanced_regression_analysis(
                        primary_results["rule1_results"]["valid_compounds"]
                    )
                except Exception as e:
                    print(f"⚠️ 고급 회귀분석 실패: {str(e)}")

            # Compile comprehensive results
            comprehensive_results = {
                "primary_analysis": primary_results,
                "enhanced_regression": enhanced_regression,
                "analysis_metadata": {
                    "total_compounds_analyzed": len(df),
                    "data_type": data_type,
                    "settings_used": self.get_current_settings(),
                    "analysis_timestamp": pd.Timestamp.now().isoformat(),
                    "includes_advanced_regression": enhanced_regression is not None
                },
                "quality_assessment": self._assess_overall_quality(primary_results, enhanced_regression)
            }

            print("✅ 종합 분석 완료")
            return comprehensive_results

        except Exception as e:
            print(f"❌ 분석 서비스 오류: {str(e)}")
            return self._create_error_result(df, str(e))

    def _perform_enhanced_regression_analysis(self, valid_compounds: list) -> Dict[str, Any]:
        """Perform enhanced regression analysis on valid compounds"""

        if len(valid_compounds) < 2:
            return {"error": "Insufficient data for enhanced regression"}

        # Convert to arrays for regression analysis
        import numpy as np

        log_p_values = []
        rt_values = []
        compound_names = []

        for compound in valid_compounds:
            if "Log P" in compound and "RT" in compound:
                log_p_values.append(compound["Log P"])
                rt_values.append(compound["RT"])
                compound_names.append(compound.get("Name", f"Compound_{len(compound_names)}"))

        if len(log_p_values) < 2:
            return {"error": "Insufficient valid Log P - RT pairs for regression"}

        x_data = np.array(log_p_values)
        y_data = np.array(rt_values)

        # Perform comprehensive regression analysis
        regression_results = self.regression_analyzer.perform_comprehensive_regression(
            x_data, y_data, compound_names
        )

        return {
            "regression_analysis": regression_results,
            "data_summary": {
                "n_compounds": len(valid_compounds),
                "log_p_range": [float(np.min(x_data)), float(np.max(x_data))],
                "rt_range": [float(np.min(y_data)), float(np.max(y_data))],
                "compounds_analyzed": compound_names
            }
        }

    def _assess_overall_quality(
        self,
        primary_results: Dict[str, Any],
        enhanced_regression: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess overall analysis quality"""

        # Get primary analysis quality
        primary_quality = primary_results.get("analysis_quality", {})

        # Assess enhanced regression quality if available
        regression_quality = "Not performed"
        if enhanced_regression and not enhanced_regression.get("error"):
            regression_analysis = enhanced_regression.get("regression_analysis", {})
            if "model_quality" in regression_analysis:
                regression_quality = regression_analysis["model_quality"].get("grade", "Unknown")

        # Overall assessment
        primary_success_rate = primary_results.get("statistics", {}).get("success_rate", 0)

        if primary_success_rate >= 80 and regression_quality in ["Excellent", "Good"]:
            overall_grade = "Excellent"
            confidence = "Very High"
        elif primary_success_rate >= 60:
            overall_grade = "Good"
            confidence = "High"
        elif primary_success_rate >= 40:
            overall_grade = "Fair"
            confidence = "Medium"
        else:
            overall_grade = "Poor"
            confidence = "Low"

        return {
            "overall_grade": overall_grade,
            "confidence_level": confidence,
            "primary_analysis_quality": primary_quality.get("quality", "Unknown"),
            "regression_analysis_quality": regression_quality,
            "success_rate": primary_success_rate,
            "recommendations": self._generate_overall_recommendations(
                primary_results, enhanced_regression, overall_grade
            )
        }

    def _generate_overall_recommendations(
        self,
        primary_results: Dict[str, Any],
        enhanced_regression: Optional[Dict[str, Any]],
        overall_grade: str
    ) -> list:
        """Generate overall recommendations"""

        recommendations = []

        # Primary analysis recommendations
        if primary_results.get("analysis_quality", {}).get("recommendations"):
            recommendations.extend(primary_results["analysis_quality"]["recommendations"])

        # Regression analysis recommendations
        if enhanced_regression and not enhanced_regression.get("error"):
            regression_analysis = enhanced_regression.get("regression_analysis", {})
            if "model_quality" in regression_analysis:
                reg_recommendations = regression_analysis["model_quality"].get("recommendations", [])
                recommendations.extend(reg_recommendations)

        # Overall recommendations based on grade
        if overall_grade == "Poor":
            recommendations.append("Consider reviewing data quality and collection methods")
            recommendations.append("Check if analysis parameters need adjustment")
        elif overall_grade == "Fair":
            recommendations.append("Results are acceptable but could be improved")
        elif overall_grade == "Excellent":
            recommendations.append("Analysis quality is excellent - results are highly reliable")

        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)

        return unique_recommendations[:5]  # Limit to top 5 recommendations

    def _create_error_result(self, df: pd.DataFrame, error_message: str) -> Dict[str, Any]:
        """Create error result structure"""

        return {
            "primary_analysis": {
                "statistics": {
                    "total_compounds": len(df),
                    "valid_compounds": 0,
                    "outliers": len(df),
                    "success_rate": 0.0
                },
                "error": True,
                "error_message": error_message
            },
            "enhanced_regression": {"error": "Primary analysis failed"},
            "analysis_metadata": {
                "total_compounds_analyzed": len(df),
                "error_occurred": True,
                "error_message": error_message,
                "analysis_timestamp": pd.Timestamp.now().isoformat()
            },
            "quality_assessment": {
                "overall_grade": "Error",
                "confidence_level": "None",
                "recommendations": [f"Fix analysis error: {error_message}"]
            }
        }