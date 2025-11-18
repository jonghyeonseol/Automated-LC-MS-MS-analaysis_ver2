"""
Regression Analyzer - 고급 회귀분석 전용 모듈
OLS 회귀분석, 잔차분석, Durbin-Watson 테스트, Cook's Distance 등
"""

import logging
import warnings
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)


class RegressionAnalyzer:
    def __init__(self) -> None:
        self.r2_threshold: float = 0.99
        self.outlier_threshold: float = 3.0
        self.confidence_level: float = 0.95

        print("📈 Regression Analyzer 초기화 완료")

    def perform_comprehensive_regression(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        compound_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        종합적인 회귀분석 수행

        Args:
            x_data: 독립변수 (Log P)
            y_data: 종속변수 (RT)
            compound_names: 화합물 이름 리스트

        Returns:
            종합 회귀분석 결과
        """

        if len(x_data) < 3:
            return self._minimal_regression_result(x_data, y_data)

        try:
            # 1. 기본 OLS 회귀분석
            basic_regression = self._perform_ols_regression(x_data, y_data)

            # 2. 잔차 진단
            residual_diagnostics = self._comprehensive_residual_analysis(
                basic_regression["residuals"], basic_regression["predicted_values"]
            )

            # 3. 영향력 진단 (Cook's Distance, Leverage, DFFITS)
            influence_diagnostics = self._influence_diagnostics(
                x_data, y_data, basic_regression
            )

            # 4. 고급 이상치 탐지
            outlier_analysis = self._advanced_outlier_detection(
                x_data, y_data, basic_regression, compound_names
            )

            # 5. 모델 가정 검정
            assumption_tests = self._test_regression_assumptions(
                basic_regression["residuals"],
                basic_regression["predicted_values"],
                x_data,
            )

            # 6. 예측 구간 계산
            prediction_intervals = self._calculate_prediction_intervals(
                x_data, y_data, basic_regression
            )

            # 7. 모델 품질 평가
            model_quality = self._evaluate_model_quality(
                basic_regression, residual_diagnostics, assumption_tests
            )

            return {
                "basic_regression": basic_regression,
                "residual_diagnostics": residual_diagnostics,
                "influence_diagnostics": influence_diagnostics,
                "outlier_analysis": outlier_analysis,
                "assumption_tests": assumption_tests,
                "prediction_intervals": prediction_intervals,
                "model_quality": model_quality,
                "analysis_summary": self._generate_analysis_summary(
                    basic_regression, model_quality, outlier_analysis
                ),
            }

        except (ValueError, np.linalg.LinAlgError) as e:
            # Numerical errors in regression calculation
            logger.error(f"Regression numerical error: {e}")
            print(f"Regression numerical error: {str(e)}")
            return self._error_regression_result(f"Numerical error: {str(e)}")
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected regression analysis error: {e}")
            print(f"Regression analysis error: {str(e)}")
            return self._error_regression_result(f"Unexpected error: {str(e)}")

    def _perform_ols_regression(
        self, x_data: np.ndarray, y_data: np.ndarray
    ) -> Dict[str, Any]:
        """기본 OLS 회귀분석 수행"""

        n = len(x_data)

        # 설계 행렬 생성 (절편 포함)
        X = np.column_stack([np.ones(n), x_data])

        # OLS 추정
        try:
            # 정규방정식: β = (X'X)^(-1)X'y
            XTX_inv = np.linalg.inv(X.T @ X)
            beta = XTX_inv @ X.T @ y_data
        except np.linalg.LinAlgError:
            # 특이행렬인 경우 최소제곱법 사용
            beta, _, _, _ = np.linalg.lstsq(X, y_data, rcond=None)

        intercept, slope = beta[0], beta[1]

        # 예측값 및 잔차 계산
        y_pred = X @ beta
        residuals = y_data - y_pred

        # 통계량 계산
        ss_total = np.sum((y_data - np.mean(y_data)) ** 2)
        ss_residual = np.sum(residuals**2)
        ss_regression = ss_total - ss_residual

        r2 = ss_regression / ss_total if ss_total > 0 else 0
        adjusted_r2 = (
            1 - (ss_residual / (n - 2)) / (ss_total / (n - 1)) if n > 2 else r2
        )

        # 표준오차 계산
        mse = ss_residual / (n - 2) if n > 2 else 0
        se_slope = np.sqrt(mse * XTX_inv[1, 1]) if mse > 0 else 0
        se_intercept = np.sqrt(mse * XTX_inv[0, 0]) if mse > 0 else 0

        # t-통계량 및 p-값
        t_slope = slope / se_slope if se_slope > 0 else 0
        t_intercept = intercept / se_intercept if se_intercept > 0 else 0

        df = n - 2
        p_slope = 2 * (1 - stats.t.cdf(abs(t_slope), df)) if df > 0 else 0.5
        p_intercept = 2 * (1 - stats.t.cdf(abs(t_intercept), df)) if df > 0 else 0.5

        # F-통계량
        f_statistic = (
            (ss_regression / 1) / (ss_residual / df)
            if df > 0 and ss_residual > 0
            else 0
        )
        f_p_value = 1 - stats.f.cdf(f_statistic, 1, df) if df > 0 else 0.5

        return {
            "slope": float(slope),
            "intercept": float(intercept),
            "r2": float(r2),
            "adjusted_r2": float(adjusted_r2),
            "mse": float(mse),
            "rmse": float(np.sqrt(mse)),
            "se_slope": float(se_slope),
            "se_intercept": float(se_intercept),
            "t_slope": float(t_slope),
            "t_intercept": float(t_intercept),
            "p_slope": float(p_slope),
            "p_intercept": float(p_intercept),
            "f_statistic": float(f_statistic),
            "f_p_value": float(f_p_value),
            "predicted_values": y_pred.tolist(),
            "residuals": residuals.tolist(),
            "standardized_residuals": (residuals / np.std(residuals)).tolist()
            if np.std(residuals) > 0
            else residuals.tolist(),
            "n_observations": n,
            "degrees_freedom": df,
            "equation": f"RT = {slope:.4f} * Log_P + {intercept:.4f}",
        }

    def _comprehensive_residual_analysis(
        self, residuals: List[float], predicted_values: List[float]
    ) -> Dict[str, Any]:
        """종합적인 잔차 분석"""

        residuals = np.array(residuals)
        predicted_values = np.array(predicted_values)

        # 1. Durbin-Watson 검정 (자기상관)
        dw_statistic = self._durbin_watson_test(residuals)

        # 2. Breusch-Pagan 검정 (등분산성)
        bp_test = self._breusch_pagan_test(residuals, predicted_values)

        # 3. Shapiro-Wilk 검정 (정규성)
        shapiro_test = self._shapiro_wilk_test(residuals)

        # 4. 잔차 통계
        residual_stats = {
            "mean": float(np.mean(residuals)),
            "std": float(np.std(residuals)),
            "min": float(np.min(residuals)),
            "max": float(np.max(residuals)),
            "range": float(np.max(residuals) - np.min(residuals)),
            "skewness": float(stats.skew(residuals)),
            "kurtosis": float(stats.kurtosis(residuals)),
        }

        return {
            "durbin_watson": dw_statistic,
            "breusch_pagan": bp_test,
            "shapiro_wilk": shapiro_test,
            "residual_statistics": residual_stats,
            "autocorrelation_detected": dw_statistic["is_problematic"],
            "heteroscedasticity_detected": bp_test["is_heteroscedastic"],
            "non_normality_detected": not shapiro_test["is_normal"],
        }

    def _durbin_watson_test(self, residuals: np.ndarray) -> Dict[str, Any]:
        """Durbin-Watson 검정 (1차 자기상관 검정)"""

        n = len(residuals)
        if n < 2:
            return {
                "statistic": 2.0,
                "interpretation": "데이터 부족",
                "is_problematic": False,
            }

        # DW 통계량 계산
        diff_residuals = np.diff(residuals)
        dw_stat = np.sum(diff_residuals**2) / np.sum(residuals**2)

        # 해석 (간략화된 기준)
        if dw_stat < 1.5:
            interpretation = "양의 자기상관 의심"
            is_problematic = True
        elif dw_stat > 2.5:
            interpretation = "음의 자기상관 의심"
            is_problematic = True
        else:
            interpretation = "자기상관 없음"
            is_problematic = False

        return {
            "statistic": float(dw_stat),
            "interpretation": interpretation,
            "is_problematic": is_problematic,
            "critical_range": [1.5, 2.5],
        }

    def _breusch_pagan_test(
        self, residuals: np.ndarray, predicted_values: np.ndarray
    ) -> Dict[str, Any]:
        """Breusch-Pagan 검정 (등분산성 검정)"""

        n = len(residuals)
        if n < 3:
            return {"is_heteroscedastic": False, "p_value": 0.5, "test_statistic": 0.0}

        # 잔차 제곱과 예측값의 상관계수
        squared_residuals = residuals**2

        try:
            correlation, p_value = stats.pearsonr(squared_residuals, predicted_values)

            # LM 통계량 (간략화)
            lm_stat = n * correlation**2

            # 임계값 설정 (간략화)
            is_heteroscedastic = abs(correlation) > 0.3 or p_value < 0.05

            return {
                "correlation": float(correlation),
                "p_value": float(p_value),
                "lm_statistic": float(lm_stat),
                "is_heteroscedastic": is_heteroscedastic,
                "interpretation": "이분산성 발견" if is_heteroscedastic else "등분산성 가정 만족",
            }
        except (ValueError, RuntimeError, TypeError) as e:
            logger.warning(f"Breusch-Pagan test failed: {e}")
            return {"is_heteroscedastic": False, "p_value": 0.5, "test_statistic": 0.0}

    def _shapiro_wilk_test(self, residuals: np.ndarray) -> Dict[str, Any]:
        """Shapiro-Wilk 검정 (정규성 검정)"""

        n = len(residuals)
        if n < 3:
            return {"is_normal": True, "p_value": 0.5, "statistic": 1.0}

        try:
            statistic, p_value = stats.shapiro(residuals)
            is_normal = p_value > 0.05

            return {
                "statistic": float(statistic),
                "p_value": float(p_value),
                "is_normal": is_normal,
                "interpretation": "정규성 만족" if is_normal else "정규성 위반",
            }
        except (ValueError, RuntimeError, TypeError) as e:
            logger.warning(f"Shapiro-Wilk test failed: {e}")
            return {"is_normal": True, "p_value": 0.5, "statistic": 1.0}

    def _influence_diagnostics(
        self, x_data: np.ndarray, y_data: np.ndarray, regression_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """영향력 진단 (Cook's Distance, Leverage, DFFITS)"""

        n = len(x_data)
        p = 2  # 파라미터 개수 (절편 + 기울기)

        # 설계 행렬
        X = np.column_stack([np.ones(n), x_data])

        try:
            # Hat matrix (H = X(X'X)^(-1)X')
            XTX_inv = np.linalg.inv(X.T @ X)
            H = X @ XTX_inv @ X.T
            leverage = np.diag(H)

            # 잔차
            residuals = np.array(regression_result["residuals"])
            mse = regression_result["mse"]

            # Cook's Distance
            standardized_residuals = residuals / np.sqrt(mse * (1 - leverage))
            cooks_distance = (standardized_residuals**2 / p) * (
                leverage / (1 - leverage)
            )

            # DFFITS
            dffits = standardized_residuals * np.sqrt(leverage / (1 - leverage))

            # 임계값
            leverage_threshold = 2 * p / n
            cooks_threshold = 4 / (n - p)
            dffits_threshold = 2 * np.sqrt(p / n)

            # 영향력 있는 관측치 탐지
            high_leverage = leverage > leverage_threshold
            high_cooks = cooks_distance > cooks_threshold
            high_dffits = np.abs(dffits) > dffits_threshold

            influential = high_leverage | high_cooks | high_dffits

            return {
                "leverage": leverage.tolist(),
                "cooks_distance": cooks_distance.tolist(),
                "dffits": dffits.tolist(),
                "thresholds": {
                    "leverage": float(leverage_threshold),
                    "cooks_distance": float(cooks_threshold),
                    "dffits": float(dffits_threshold),
                },
                "influential_points": {
                    "high_leverage": np.where(high_leverage)[0].tolist(),
                    "high_cooks": np.where(high_cooks)[0].tolist(),
                    "high_dffits": np.where(high_dffits)[0].tolist(),
                    "any_influential": np.where(influential)[0].tolist(),
                },
                "influence_summary": {
                    "n_high_leverage": int(np.sum(high_leverage)),
                    "n_high_cooks": int(np.sum(high_cooks)),
                    "n_high_dffits": int(np.sum(high_dffits)),
                    "n_influential": int(np.sum(influential)),
                },
            }

        except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as e:
            # Numerical errors in influence diagnostics calculation
            logger.error(f"Influence diagnostics numerical error: {e}")
            print(f"Influence diagnostics numerical error: {str(e)}")
            return self._default_influence_result(n)
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected influence diagnostics error: {e}")
            print(f"Influence diagnostics error: {str(e)}")
            return self._default_influence_result(n)

    def _advanced_outlier_detection(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        regression_result: Dict[str, Any],
        compound_names: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """고급 이상치 탐지"""

        n = len(x_data)
        residuals = np.array(regression_result["residuals"])
        std_residuals = np.array(regression_result["standardized_residuals"])

        # 1. 표준화 잔차 기반 이상치 (±3 기준)
        std_outliers = np.abs(std_residuals) >= self.outlier_threshold

        # 2. IQR 기반 이상치
        q1, q3 = np.percentile(residuals, [25, 75])
        iqr = q3 - q1
        iqr_outliers = (residuals < q1 - 1.5 * iqr) | (residuals > q3 + 1.5 * iqr)

        # 3. Modified Z-score (MAD 기반)
        mad = np.median(np.abs(residuals - np.median(residuals)))
        modified_z_scores = (
            0.6745 * (residuals - np.median(residuals)) / mad
            if mad > 0
            else np.zeros_like(residuals)
        )
        mad_outliers = np.abs(modified_z_scores) > 3.5

        # 4. 통합 이상치 판별
        combined_outliers = std_outliers | iqr_outliers | mad_outliers

        # 이상치 상세 정보
        outlier_details = []
        for i in range(n):
            if combined_outliers[i]:
                outlier_info = {
                    "index": int(i),
                    "name": compound_names[i]
                    if compound_names and i < len(compound_names)
                    else f"Point_{i}",
                    "x_value": float(x_data[i]),
                    "y_value": float(y_data[i]),
                    "residual": float(residuals[i]),
                    "std_residual": float(std_residuals[i]),
                    "modified_z_score": float(modified_z_scores[i]),
                    "outlier_methods": [],
                }

                if std_outliers[i]:
                    outlier_info["outlier_methods"].append("Standardized Residual")
                if iqr_outliers[i]:
                    outlier_info["outlier_methods"].append("IQR Method")
                if mad_outliers[i]:
                    outlier_info["outlier_methods"].append("MAD Method")

                outlier_details.append(outlier_info)

        return {
            "outlier_indices": np.where(combined_outliers)[0].tolist(),
            "outlier_details": outlier_details,
            "outlier_summary": {
                "n_std_outliers": int(np.sum(std_outliers)),
                "n_iqr_outliers": int(np.sum(iqr_outliers)),
                "n_mad_outliers": int(np.sum(mad_outliers)),
                "n_total_outliers": int(np.sum(combined_outliers)),
                "outlier_percentage": float(np.sum(combined_outliers) / n * 100),
            },
            "thresholds": {
                "standardized_residual": self.outlier_threshold,
                "iqr_multiplier": 1.5,
                "mad_threshold": 3.5,
            },
        }

    def _test_regression_assumptions(
        self, residuals: List[float], predicted_values: List[float], x_data: np.ndarray
    ) -> Dict[str, Any]:
        """회귀분석 가정 검정"""

        residuals = np.array(residuals)
        predicted_values = np.array(predicted_values)

        assumptions = {}

        # 1. 선형성 (잔차 vs 예측값의 패턴)
        linearity_corr = (
            np.corrcoef(predicted_values, residuals)[0, 1] if len(residuals) > 1 else 0
        )
        assumptions["linearity"] = {
            "correlation": float(linearity_corr),
            "is_satisfied": abs(linearity_corr) < 0.1,
            "interpretation": "선형성 만족" if abs(linearity_corr) < 0.1 else "선형성 의심",
        }

        # 2. 독립성 (Durbin-Watson)
        dw_result = self._durbin_watson_test(residuals)
        assumptions["independence"] = {
            "durbin_watson": dw_result["statistic"],
            "is_satisfied": not dw_result["is_problematic"],
            "interpretation": dw_result["interpretation"],
        }

        # 3. 등분산성 (Breusch-Pagan)
        bp_result = self._breusch_pagan_test(residuals, predicted_values)
        assumptions["homoscedasticity"] = {
            "is_satisfied": not bp_result["is_heteroscedastic"],
            "test_result": bp_result,
            "interpretation": bp_result["interpretation"],
        }

        # 4. 정규성 (Shapiro-Wilk)
        sw_result = self._shapiro_wilk_test(residuals)
        assumptions["normality"] = {
            "is_satisfied": sw_result["is_normal"],
            "test_result": sw_result,
            "interpretation": sw_result["interpretation"],
        }

        # 종합 평가
        all_satisfied = all(
            [
                assumptions["linearity"]["is_satisfied"],
                assumptions["independence"]["is_satisfied"],
                assumptions["homoscedasticity"]["is_satisfied"],
                assumptions["normality"]["is_satisfied"],
            ]
        )

        assumptions["overall_assessment"] = {
            "all_assumptions_met": all_satisfied,
            "violated_assumptions": [
                name
                for name, test in assumptions.items()
                if isinstance(test, dict) and not test.get("is_satisfied", True)
            ],
        }

        return assumptions

    def _calculate_prediction_intervals(
        self, x_data: np.ndarray, y_data: np.ndarray, regression_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """예측 구간 계산"""

        n = len(x_data)
        if n < 3:
            return {"confidence_intervals": [], "prediction_intervals": []}

        slope = regression_result["slope"]
        intercept = regression_result["intercept"]
        mse = regression_result["mse"]

        # t 임계값
        alpha = 1 - self.confidence_level
        t_critical = stats.t.ppf(1 - alpha / 2, n - 2)

        # 설계 행렬
        X = np.column_stack([np.ones(n), x_data])

        try:
            XTX_inv = np.linalg.inv(X.T @ X)

            confidence_intervals = []
            prediction_intervals = []

            for i, x_val in enumerate(x_data):
                # 예측값
                y_pred = slope * x_val + intercept

                # 표준오차
                x_vector = np.array([1, x_val])
                se_pred = np.sqrt(mse * x_vector.T @ XTX_inv @ x_vector)
                se_forecast = np.sqrt(mse * (1 + x_vector.T @ XTX_inv @ x_vector))

                # 신뢰구간 (평균 예측)
                ci_lower = y_pred - t_critical * se_pred
                ci_upper = y_pred + t_critical * se_pred

                # 예측구간 (개별 예측)
                pi_lower = y_pred - t_critical * se_forecast
                pi_upper = y_pred + t_critical * se_forecast

                confidence_intervals.append(
                    {
                        "x": float(x_val),
                        "predicted": float(y_pred),
                        "lower": float(ci_lower),
                        "upper": float(ci_upper),
                    }
                )

                prediction_intervals.append(
                    {
                        "x": float(x_val),
                        "predicted": float(y_pred),
                        "lower": float(pi_lower),
                        "upper": float(pi_upper),
                    }
                )

            return {
                "confidence_level": self.confidence_level,
                "confidence_intervals": confidence_intervals,
                "prediction_intervals": prediction_intervals,
            }

        except (ValueError, np.linalg.LinAlgError, ZeroDivisionError) as e:
            # Numerical errors in prediction interval calculation
            logger.error(f"Prediction interval numerical error: {e}")
            print(f"Prediction interval numerical error: {str(e)}")
            return {"confidence_intervals": [], "prediction_intervals": []}
        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected prediction interval error: {e}")
            print(f"Prediction interval calculation error: {str(e)}")
            return {"confidence_intervals": [], "prediction_intervals": []}

    def _evaluate_model_quality(
        self,
        basic_regression: Dict[str, Any],
        residual_diagnostics: Dict[str, Any],
        assumption_tests: Dict[str, Any],
    ) -> Dict[str, Any]:
        """모델 품질 종합 평가"""

        r2 = basic_regression["r2"]
        adjusted_r2 = basic_regression["adjusted_r2"]
        f_p_value = basic_regression["f_p_value"]

        # 품질 점수 계산 (0-100)
        quality_scores = {}

        # 1. 설명력 점수 (R² 기반)
        quality_scores["explanatory_power"] = min(r2 * 100, 100)

        # 2. 통계적 유의성 점수
        quality_scores["statistical_significance"] = (
            100 if f_p_value < 0.05 else 50 if f_p_value < 0.1 else 0
        )

        # 3. 가정 만족도 점수
        assumptions_met = sum(
            [
                assumption_tests["linearity"]["is_satisfied"],
                assumption_tests["independence"]["is_satisfied"],
                assumption_tests["homoscedasticity"]["is_satisfied"],
                assumption_tests["normality"]["is_satisfied"],
            ]
        )
        quality_scores["assumption_compliance"] = (assumptions_met / 4) * 100

        # 4. 잔차 품질 점수
        residual_quality = 100
        if residual_diagnostics["autocorrelation_detected"]:
            residual_quality -= 30
        if residual_diagnostics["heteroscedasticity_detected"]:
            residual_quality -= 25
        if residual_diagnostics["non_normality_detected"]:
            residual_quality -= 20
        quality_scores["residual_quality"] = max(residual_quality, 0)

        # 종합 점수
        overall_score = np.mean(list(quality_scores.values()))

        # 등급 판정
        if overall_score >= 90:
            grade = "Excellent"
            reliability = "Very High"
        elif overall_score >= 80:
            grade = "Good"
            reliability = "High"
        elif overall_score >= 70:
            grade = "Acceptable"
            reliability = "Medium"
        elif overall_score >= 60:
            grade = "Poor"
            reliability = "Low"
        else:
            grade = "Unacceptable"
            reliability = "Very Low"

        return {
            "overall_score": float(overall_score),
            "grade": grade,
            "reliability": reliability,
            "quality_scores": {k: float(v) for k, v in quality_scores.items()},
            "meets_threshold": r2 >= self.r2_threshold,
            "recommendations": self._generate_recommendations(
                basic_regression, residual_diagnostics, assumption_tests
            ),
        }

    def _generate_recommendations(
        self,
        basic_regression: Dict[str, Any],
        residual_diagnostics: Dict[str, Any],
        assumption_tests: Dict[str, Any],
    ) -> List[str]:
        """개선 권장사항 생성"""

        recommendations = []

        # R² 기반 권장사항
        r2 = basic_regression["r2"]
        if r2 < 0.5:
            recommendations.append("설명력이 낮습니다. 추가 변수나 비선형 모델을 고려해보세요.")
        elif r2 < self.r2_threshold:
            recommendations.append("설명력을 높이기 위해 이상치 제거나 변수 변환을 검토해보세요.")

        # 가정 위반 기반 권장사항
        if not assumption_tests["linearity"]["is_satisfied"]:
            recommendations.append("선형성 가정이 위반됩니다. 비선형 회귀나 변수 변환을 고려해보세요.")

        if not assumption_tests["independence"]["is_satisfied"]:
            recommendations.append("독립성 가정이 위반됩니다. 시계열 모델이나 일반화 선형모델을 고려해보세요.")

        if not assumption_tests["homoscedasticity"]["is_satisfied"]:
            recommendations.append("등분산성 가정이 위반됩니다. 가중최소제곱법이나 로버스트 회귀를 고려해보세요.")

        if not assumption_tests["normality"]["is_satisfied"]:
            recommendations.append("정규성 가정이 위반됩니다. 비모수적 방법이나 변수 변환을 고려해보세요.")

        # 이상치 관련 권장사항
        if residual_diagnostics.get("outlier_detected", False):
            recommendations.append("이상치가 탐지되었습니다. 데이터 품질을 확인하고 이상치 제거를 검토해보세요.")

        if not recommendations:
            recommendations.append("회귀모델이 양호한 품질을 보입니다. 현재 설정을 유지하세요.")

        return recommendations

    def _generate_analysis_summary(
        self,
        basic_regression: Dict[str, Any],
        model_quality: Dict[str, Any],
        outlier_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """분석 요약 생성"""

        return {
            "model_equation": basic_regression["equation"],
            "r_squared": basic_regression["r2"],
            "adjusted_r_squared": basic_regression["adjusted_r2"],
            "p_value": basic_regression["f_p_value"],
            "sample_size": basic_regression["n_observations"],
            "quality_grade": model_quality["grade"],
            "overall_score": model_quality["overall_score"],
            "outliers_detected": outlier_analysis["outlier_summary"][
                "n_total_outliers"
            ],
            "outlier_percentage": outlier_analysis["outlier_summary"][
                "outlier_percentage"
            ],
            "meets_quality_threshold": model_quality["meets_threshold"],
            "key_recommendations": model_quality["recommendations"][:3],  # 상위 3개 권장사항
        }

    def _minimal_regression_result(
        self, x_data: np.ndarray, y_data: np.ndarray
    ) -> Dict[str, Any]:
        """최소 데이터를 위한 간단한 회귀 결과"""

        if len(x_data) == 0:
            return self._empty_regression_result()

        basic_regression = self._perform_ols_regression(x_data, y_data)

        return {
            "basic_regression": basic_regression,
            "model_quality": {
                "overall_score": 50.0,
                "grade": "Insufficient Data",
                "reliability": "Low",
                "meets_threshold": False,
            },
            "analysis_summary": {
                "model_equation": basic_regression["equation"],
                "r_squared": basic_regression["r2"],
                "sample_size": len(x_data),
                "key_recommendations": ["더 많은 데이터가 필요합니다."],
            },
        }

    def _empty_regression_result(self) -> Dict[str, Any]:
        """빈 데이터를 위한 기본 결과"""

        return {
            "basic_regression": {"equation": "RT = 0.0000 * Log_P + 0.0000", "r2": 0.0},
            "model_quality": {
                "overall_score": 0.0,
                "grade": "No Data",
                "reliability": "None",
            },
            "analysis_summary": {"key_recommendations": ["데이터를 제공해주세요."]},
        }

    def _error_regression_result(self, error_message: str) -> Dict[str, Any]:
        """오류 발생 시 결과"""

        return {
            "error": True,
            "error_message": error_message,
            "basic_regression": {"equation": "Error in calculation", "r2": 0.0},
            "model_quality": {
                "overall_score": 0.0,
                "grade": "Error",
                "reliability": "None",
            },
            "analysis_summary": {"key_recommendations": ["분석 중 오류가 발생했습니다."]},
        }

    def _default_influence_result(self, n: int) -> Dict[str, Any]:
        """영향력 진단 기본 결과"""

        return {
            "leverage": [0.0] * n,
            "cooks_distance": [0.0] * n,
            "dffits": [0.0] * n,
            "influential_points": {"any_influential": []},
            "influence_summary": {"n_influential": 0},
        }
