"""
Dummy Data Processor - 실제 분석 로직 시뮬레이션
개발 및 테스트용 더미 클래스
"""

import pandas as pd
from typing import Dict, Any


class DummyGangliosideDataProcessor:
    """더미 데이터 프로세서 - 실제 분석 로직 시뮬레이션"""
    
    def __init__(self):
        self.r2_threshold = 0.99
        self.outlier_threshold = 3.0
        self.rt_tolerance = 0.1
        print("🧪 Dummy Ganglioside Data Processor 초기화")
        
    def process_data(self, df: pd.DataFrame, data_type: str = "Porcine") -> Dict[str, Any]:
        """실제 5가지 규칙을 시뮬레이션하는 향상된 분석 (설정 반영)"""
        
        print(f"🔬 더미 분석 실행: threshold={self.outlier_threshold}, r2={self.r2_threshold}, rt={self.rt_tolerance}")
        
        # 데이터 전처리
        df = df.copy()
        df['prefix'] = df['Name'].str.extract(r'^([^(]+)')[0]
        df['suffix'] = df['Name'].str.extract(r'\(([^)]+)\)')[0]
        
        # 규칙 1: 접두사별 회귀분석 시뮬레이션 (R² 임계값 적용)
        regression_results = {}
        valid_compounds = []
        outliers = []
        
        for prefix in df['prefix'].unique():
            if pd.isna(prefix):
                continue
                
            prefix_group = df[df['prefix'] == prefix]
            anchor_compounds = prefix_group[prefix_group['Anchor'] == 'T']
            
            if len(anchor_compounds) >= 1:
                # 가상의 R² 값 생성 (설정된 임계값 주변으로)
                base_r2 = 0.985 + (len(anchor_compounds) * 0.002)
                # 설정된 임계값에 따라 조정
                if self.r2_threshold > 0.99:
                    r2 = min(base_r2 + 0.005, 0.999)  # 높은 임계값일 때 더 높은 R²
                elif self.r2_threshold < 0.95:
                    r2 = max(base_r2 - 0.01, 0.92)   # 낮은 임계값일 때 더 낮은 R²
                else:
                    r2 = base_r2
                
                slope = -0.5 + (hash(prefix) % 100) / 100
                intercept = 8.0 + (hash(prefix) % 50) / 10
                
                # R² 임계값 검사 적용
                if r2 >= self.r2_threshold:
                    regression_results[prefix] = {
                        'slope': slope,
                        'intercept': intercept,
                        'r2': r2,
                        'n_samples': len(prefix_group),
                        'equation': f'RT = {slope:.4f} * Log P + {intercept:.4f}',
                        'p_value': 0.001,
                        'passes_threshold': True
                    }
                    
                    # 표준화 잔차 임계값에 따른 이상치 판별
                    for _, row in prefix_group.iterrows():
                        row_dict = row.to_dict()
                        predicted_rt = slope * row['Log P'] + intercept
                        residual = row['RT'] - predicted_rt
                        
                        row_dict['predicted_rt'] = predicted_rt
                        row_dict['residual'] = residual
                        
                        # 표준화 잔차 계산 (설정된 임계값 사용)
                        std_residual = residual / 0.1
                        row_dict['std_residual'] = std_residual
                        
                        # 설정된 표준화 잔차 임계값으로 이상치 판별
                        if abs(std_residual) >= self.outlier_threshold:
                            row_dict['outlier_reason'] = f'Rule 1: |Std residual| = {abs(std_residual):.2f} >= {self.outlier_threshold}'
                            outliers.append(row_dict)
                        else:
                            valid_compounds.append(row_dict)
                else:
                    # R² 임계값 미달
                    regression_results[prefix] = {
                        'slope': slope,
                        'intercept': intercept,
                        'r2': r2,
                        'n_samples': len(prefix_group),
                        'equation': f'RT = {slope:.4f} * Log P + {intercept:.4f}',
                        'p_value': 0.1,
                        'passes_threshold': False
                    }
                    
                    for _, row in prefix_group.iterrows():
                        row_dict = row.to_dict()
                        row_dict['outlier_reason'] = f'Rule 1: Low R² = {r2:.3f} < {self.r2_threshold}'
                        outliers.append(row_dict)
        
        # 규칙 4: O-acetylation 분석
        oacetyl_compounds = df[df['prefix'].str.contains('OAc', na=False)]
        valid_oacetyl = []
        invalid_oacetyl = []
        
        for _, row in oacetyl_compounds.iterrows():
            row_dict = row.to_dict()
            # 90% 확률로 유효한 OAc 효과 시뮬레이션
            if hash(row['Name']) % 10 < 9:
                row_dict['rt_increase'] = 0.2 + (hash(row['Name']) % 50) / 100
                valid_oacetyl.append(row_dict)
            else:
                row_dict['outlier_reason'] = 'Rule 4: O-acetylation should increase RT'
                invalid_oacetyl.append(row_dict)
        
        # 최종 통계 계산
        total_compounds = len(df)
        anchor_compounds = len(df[df['Anchor'] == 'T'])
        final_valid = len(valid_compounds)
        final_outliers = len(outliers) + len(invalid_oacetyl)
        success_rate = (final_valid / total_compounds) * 100 if total_compounds > 0 else 0
        
        # 설정 영향도 계산
        setting_impact = {
            'outlier_strictness': 'High' if self.outlier_threshold >= 3.0 else 'Medium' if self.outlier_threshold >= 2.0 else 'Low',
            'r2_strictness': 'Very High' if self.r2_threshold >= 0.99 else 'High' if self.r2_threshold >= 0.95 else 'Medium',
            'rt_precision': 'High' if self.rt_tolerance <= 0.1 else 'Medium' if self.rt_tolerance <= 0.2 else 'Low',
            'expected_success_rate': success_rate
        }
        
        print(f"📊 더미 분석 결과: {final_valid}/{total_compounds} 유효 ({success_rate:.1f}%)")
        
        return {
            "statistics": {
                "total_compounds": total_compounds,
                "anchor_compounds": anchor_compounds,
                "valid_compounds": final_valid,
                "outliers": final_outliers,
                "success_rate": success_rate,
                "rule_breakdown": {
                    "rule1_regression": len(valid_compounds),
                    "rule4_oacetylation": len(valid_oacetyl),
                    "rule5_rt_filtering": len(df),
                    "rule1_outliers": len(outliers),
                    "rule4_outliers": len(invalid_oacetyl),
                    "rule5_outliers": 0
                }
            },
            "valid_compounds": valid_compounds,
            "outliers": outliers + invalid_oacetyl,
            "regression_analysis": regression_results,
            "setting_impact": setting_impact,
            "status": f"Dummy Analysis - Thresholds: Outlier={self.outlier_threshold}, R²={self.r2_threshold}, RT=±{self.rt_tolerance}",
            "target_achievement": f"{final_valid}/{total_compounds} compounds identified",
            "analysis_summary": {
                "data_quality": 'High' if success_rate >= 90 else 'Medium' if success_rate >= 70 else 'Low',
                "settings_applied": True
            }
        }


class DummyVisualizationService:
    """더미 시각화 서비스"""
    
    def __init__(self):
        print("📊 Dummy Visualization Service 초기화")
    
    def create_all_plots(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """더미 시각화 생성"""
        return {
            "message": "더미 시각화 기능 준비 중",
            "available_plots": [
                "regression_plots",
                "residual_analysis", 
                "outlier_detection",
                "rt_distribution",
                "success_rate_summary"
            ]
        }
