"""
Regression Analyzer - 회귀분석 전용 모듈
OLS 회귀분석, 잔차분석, Durbin-Watson 테스트
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from scipy import stats
import statsmodels.api as sm


class RegressionAnalyzer:
    def __init__(self):
        self.r2_threshold = 0.99
        self.outlier_threshold = 3.0
        
    def perform_ols_regression(self, x_data: np.ndarray, y_data: np.ndarray, 
                              add_constant: bool = True) -> Dict[str, Any]:
        """
        OLS (Ordinary Least Squares) 회귀분석 수행
        
        Args:
            x_data: 독립변수 (Log P)
            y_data: 종속변수 (RT)
            add_constant: 절편 포함 여부
            
        Returns:
            회귀분석 결과 딕셔너리
        """
        
        if add_constant:
            X = sm.add_constant(x_data)
        else:
            X = x_data
            
        # OLS 모델 피팅
        model = sm.OLS(y_data, X).fit()
        
        # 예측값 및 잔차 계산
        y_pred = model.predict(X)
        residuals = y_data - y_pred
        
        # 표준화 잔차
        standardized_residuals = residuals / np.std(residuals)
        
        # 회귀분석 통계
        results = {
            'slope': model.params[1] if add_constant else model.params[0],
            'intercept': model.params[0] if add_constant else 0,
            'r2': model.rsquared,
            'adj_r2': model.rsquared_adj,
            'f_statistic': model.fvalue,
            'f_pvalue': model.f_pvalue,
            'aic': model.aic,
            'bic': model.bic,
            'residuals': residuals,
            'standardized_residuals': standardized_residuals,
            'predicted_values': y_pred,
            'n_observations': len(y_data),
            'equation': f'RT = {model.params[1]:.4f} * Log_P + {model.params[0]:.4f}' if add_constant else f'RT = {model.params[0]:.4f} * Log_P'
        }
        
        return results
    
    def durbin_watson_test(self, residuals: np.ndarray) -> Dict[str, Any]:
        """
        Durbin-Watson 테스트 수행
        1차 자기상관 검정
        """
        
        n = len(residuals)
        dw_statistic = np.sum(np.diff(residuals)**2) / np.sum(residuals**2)
        
        # 임계값 판정 (간략화된 버전)
        # 실제로는 테이블을 참조해야 하지만, 일반적인 기준 사용
        if dw_statistic < 1.5:
            autocorr_result = "양의 자기상관 의심"
        elif dw_statistic > 2.5:
            autocorr_result = "음의 자기상관 의심"
        else:
            autocorr_result = "자기상관 없음"
        
        return {
            'dw_statistic': dw_statistic,
            'interpretation': autocorr_result,
            'is_valid': 1.5 <= dw_statistic <= 2.5
        }
    
    def detect_outliers(self, standardized_residuals: np.ndarray, 
                       threshold: float = 3.0) -> Dict[str, Any]:
        """
        이상치 탐지 (표준화 잔차 기반)
        """
        
        outlier_indices = np.where(np.abs(standardized_residuals) >= threshold)[0]
        outlier_values = standardized_residuals[outlier_indices]
        
        return {
            'outlier_indices': outlier_indices.tolist(),
            'outlier_values': outlier_values.tolist(),
            'n_outliers': len(outlier_indices),
            'outlier_percentage': (len(outlier_indices) / len(standardized_residuals)) * 100
        }
    
    def regression_diagnostics(self, x_data: np.ndarray, y_data: np.ndarray) -> Dict[str, Any]:
        """
        종합적인 회귀진단 수행
        """
        
        # 기본 회귀분석
        regression_result = self.perform_ols_regression(x_data, y_data)
        
        # Durbin-Watson 테스트
        dw_result = self.durbin_watson_test(regression_result['residuals'])
        
        # 이상치 탐지
        outlier_result = self.detect_outliers(regression_result['standardized_residuals'])
        
        # 정규성 검정 (Shapiro-Wilk)
        shapiro_stat, shapiro_pvalue = stats.shapiro(regression_result['residuals'])
        
        # 등분산성 검정 (Breusch-Pagan)
        # 간단한 버전: 잔차와 예측값의 상관관계
        bp_corr, bp_pvalue = stats.pearsonr(
            np.abs(regression_result['residuals']), 
            regression_result['predicted_values']
        )
        
        return {
            'regression': regression_result,
            'durbin_watson': dw_result,
            'outliers': outlier_result,
            'normality_test': {
                'shapiro_stat': shapiro_stat,
                'shapiro_pvalue': shapiro_pvalue,
                'is_normal': shapiro_pvalue > 0.05
            },
            'homoscedasticity_test': {
                'bp_correlation': bp_corr,
                'bp_pvalue': bp_pvalue,
                'is_homoscedastic': abs(bp_corr) < 0.3
            },
            'model_validity': {
                'r2_acceptable': regression_result['r2'] >= self.r2_threshold,
                'no_autocorrelation': dw_result['is_valid'],
                'residuals_normal': shapiro_pvalue > 0.05,
                'variance_constant': abs(bp_corr) < 0.3
            }
        }
    
    def group_regression_analysis(self, df: pd.DataFrame, 
                                group_column: str = 'prefix') -> Dict[str, Any]:
        """
        그룹별 회귀분석 수행
        접두사별로 개별 회귀분석 실행
        """
        
        group_results = {}
        
        for group_name, group_data in df.groupby(group_column):
            if len(group_data) < 3:  # 최소 3개 데이터 포인트
                continue
                
            # Anchor='T'인 데이터만 사용 (고신뢰도 기준점)
            anchor_data = group_data[group_data['Anchor'] == 'T']
            
            if len(anchor_data) < 2:
                continue
            
            x = anchor_data['Log P'].values
            y = anchor_data['RT'].values
            
            # 회귀진단 수행
            diagnostics = self.regression_diagnostics(x, y)
            
            # 전체 그룹 데이터에 모델 적용
            if diagnostics['model_validity']['r2_acceptable']:
                all_x = group_data['Log P'].values
                all_y = group_data['RT'].values
                
                full_regression = self.perform_ols_regression(all_x, all_y)
                
                group_results[group_name] = {
                    'anchor_analysis': diagnostics,
                    'full_group_analysis': full_regression,
                    'n_anchor': len(anchor_data),
                    'n_total': len(group_data),
                    'is_valid_model': diagnostics['model_validity']['r2_acceptable']
                }
        
    def advanced_outlier_detection(self, x_data: np.ndarray, y_data: np.ndarray, 
                                  compound_names: List[str] = None) -> Dict[str, Any]:
        """
        고급 이상치 탐지 - 여러 방법 통합
        """
        
        # 기본 회귀분석
        regression_result = self.perform_ols_regression(x_data, y_data)
        standardized_residuals = regression_result['standardized_residuals']
        
        # 1. 표준화 잔차 기반 이상치 (기존 방법)
        std_outliers = np.abs(standardized_residuals) >= self.outlier_threshold
        
        # 2. Cook's Distance 계산
        n = len(y_data)
        p = 2  # 독립변수 개수 + 1 (절편 포함)
        
        # 레버리지 계산
        X = np.column_stack([np.ones(n), x_data])
        H = X @ np.linalg.inv(X.T @ X) @ X.T
        leverage = np.diag(H)
        
        # Cook's Distance
        residuals = regression_result['residuals']
        mse = np.sum(residuals**2) / (n - p)
        cooks_distance = (residuals**2 / (p * mse)) * (leverage / (1 - leverage)**2)
        
        # Cook's Distance 이상치 (일반적으로 4/(n-p) 임계값 사용)
        cooks_threshold = 4 / (n - p)
        cooks_outliers = cooks_distance >= cooks_threshold
        
        # 3. DFFITS 계산
        dffits = standardized_residuals * np.sqrt(leverage / (1 - leverage))
        dffits_threshold = 2 * np.sqrt(p / n)
        dffits_outliers = np.abs(dffits) >= dffits_threshold
        
        # 4. 통합 이상치 판별
        combined_outliers = std_outliers | cooks_outliers | dffits_outliers
        
        # 결과 정리
        outlier_details = []
        for i, is_outlier in enumerate(combined_outliers):
            if is_outlier:
                outlier_info = {
                    'index': i,
                    'name': compound_names[i] if compound_names else f"Compound_{i}",
                    'standardized_residual': standardized_residuals[i],
                    'cooks_distance': cooks_distance[i],
                    'dffits': dffits[i],
                    'leverage': leverage[i],
                    'outlier_reasons': []
                }
                
                if std_outliers[i]:
                    outlier_info['outlier_reasons'].append('High standardized residual')
                if cooks_outliers[i]:
                    outlier_info['outlier_reasons'].append('High Cook\'s distance')
                if dffits_outliers[i]:
                    outlier_info['outlier_reasons'].append('High DFFITS')
                
                outlier_details.append(outlier_info)
        
        return {
            'regression_result': regression_result,
            'outlier_indices': np.where(combined_outliers)[0].tolist(),
            'outlier_details': outlier_details,
            'diagnostics': {
                'cooks_distance': cooks_distance.tolist(),
                'leverage': leverage.tolist(),
                'dffits': dffits.tolist(),
                'thresholds': {
                    'standardized_residual': self.outlier_threshold,
                    'cooks_distance': cooks_threshold,
                    'dffits': dffits_threshold
                }
            },
            'outlier_summary': {
                'std_residual_outliers': np.sum(std_outliers),
                'cooks_distance_outliers': np.sum(cooks_outliers),
                'dffits_outliers': np.sum(dffits_outliers),
                'total_outliers': np.sum(combined_outliers)
            }
        }
    
    def predict_retention_time(self, log_p_values: np.ndarray, 
                              slope: float, intercept: float) -> np.ndarray:
        """
        Log P 값으로부터 머무름 시간 예측
        """
        return slope * log_p_values + intercept
    
    def calculate_prediction_intervals(self, x_data: np.ndarray, y_data: np.ndarray,
                                     new_x: np.ndarray, confidence: float = 0.95) -> Dict[str, np.ndarray]:
        """
        예측 구간 계산
        """
        
        # OLS 모델 피팅
        X = sm.add_constant(x_data)
        model = sm.OLS(y_data, X).fit()
        
        # 새로운 X 값에 대한 예측
        new_X = sm.add_constant(new_x)
        predictions = model.get_prediction(new_X)
        
        # 신뢰구간과 예측구간
        conf_int = predictions.conf_int(alpha=1-confidence)
        pred_int = predictions.conf_int(alpha=1-confidence, obs=True)
        
        return {
            'predicted': predictions.predicted_mean,
            'conf_lower': conf_int[:, 0],
            'conf_upper': conf_int[:, 1],
            'pred_lower': pred_int[:, 0],
            'pred_upper': pred_int[:, 1]
        }
    
    def robust_regression_analysis(self, df: pd.DataFrame, group_column: str = 'prefix') -> Dict[str, Any]:
        """
        강건한 회귀분석 - 이상치에 강인한 분석
        """
        
        group_results = {}
        
        for group_name, group_data in df.groupby(group_column):
            if len(group_data) < 3:
                continue
                
            # Anchor='T'인 데이터로 초기 모델 구축
            anchor_data = group_data[group_data['Anchor'] == 'T']
            
            if len(anchor_data) < 2:
                continue
            
            x = anchor_data['Log P'].values
            y = anchor_data['RT'].values
            compound_names = anchor_data['Name'].tolist()
            
            # 고급 이상치 탐지
            advanced_analysis = self.advanced_outlier_detection(x, y, compound_names)
            
            # 이상치 제거 후 재분석
            outlier_indices = advanced_analysis['outlier_indices']
            clean_x = np.delete(x, outlier_indices)
            clean_y = np.delete(y, outlier_indices)
            
            if len(clean_x) >= 2:
                clean_regression = self.perform_ols_regression(clean_x, clean_y)
                
                # 전체 그룹 데이터에 정리된 모델 적용
                all_x = group_data['Log P'].values
                all_y = group_data['RT'].values
                
                # 예측 및 잔차 계산
                all_pred = clean_regression['slope'] * all_x + clean_regression['intercept']
                all_residuals = all_y - all_pred
                all_std_residuals = all_residuals / np.std(all_residuals)
                
                group_results[group_name] = {
                    'initial_analysis': advanced_analysis,
                    'cleaned_regression': clean_regression,
                    'full_group_predictions': {
                        'predicted_rt': all_pred.tolist(),
                        'residuals': all_residuals.tolist(),
                        'standardized_residuals': all_std_residuals.tolist()
                    },
                    'model_quality': {
                        'initial_r2': advanced_analysis['regression_result']['r2'],
                        'cleaned_r2': clean_regression['r2'],
                        'improvement': clean_regression['r2'] - advanced_analysis['regression_result']['r2']
                    },
                    'n_anchor': len(anchor_data),
                    'n_total': len(group_data),
                    'n_outliers_removed': len(outlier_indices),
                    'is_reliable_model': clean_regression['r2'] >= self.r2_threshold
                }
            else:
                group_results[group_name] = {
                    'initial_analysis': advanced_analysis,
                    'error': 'Insufficient data after outlier removal',
                    'n_anchor': len(anchor_data),
                    'is_reliable_model': False
                }
        
        return group_results