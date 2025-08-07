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
    
    def update_settings(self, outlier_threshold=None, r2_threshold=None, rt_tolerance=None):
        """분석 설정 업데이트"""
        if outlier_threshold is not None:
            self.outlier_threshold = outlier_threshold
        if r2_threshold is not None:
            self.r2_threshold = r2_threshold
        if rt_tolerance is not None:
            self.rt_tolerance = rt_tolerance
        print(f"⚙️ 더미 설정 업데이트: outlier={self.outlier_threshold}, r2={self.r2_threshold}, rt={self.rt_tolerance}")
    
    def get_settings(self):
        """현재 설정 반환"""
        return {
            'outlier_threshold': self.outlier_threshold,
            'r2_threshold': self.r2_threshold,
            'rt_tolerance': self.rt_tolerance
        }
        
    def process_data(self, df: pd.DataFrame, data_type: str = "Porcine") -> Dict[str, Any]:
        """실제 5가지 규칙을 시뮬레이션하는 향상된 분석 (설정 반영)"""
        
        print(f"🔬 더미 분석 실행: threshold={self.outlier_threshold}, r2={self.r2_threshold}, rt={self.rt_tolerance}")
        
        # 데이터 전처리 - 개선된 접두사 추출
        df = df.copy()
        
        # 복합 접두사 처리 (GD1+HexNAc, GM1+HexNAc 등)
        def extract_ganglioside_prefix(name):
            # GD1+HexNAc, GM1+HexNAc 등의 복합 접두사 먼저 확인
            if '+HexNAc' in name:
                base_prefix = name.split('+HexNAc')[0]
                return f"{base_prefix}+HexNAc"
            # 기본 ganglioside 접두사 (GD1a, GD1b, GM1a, GM3, GD3, GT1b 등)
            elif any(gtype in name for gtype in ['GD1a', 'GD1b', 'GM1a', 'GM1b', 'GM2', 'GM3', 'GD2', 'GD3', 'GT1a', 'GT1b', 'GT1c']):
                # 정확한 ganglioside 타입 추출
                for gtype in ['GD1a', 'GD1b', 'GM1a', 'GM1b', 'GM2', 'GM3', 'GD2', 'GD3', 'GT1a', 'GT1b', 'GT1c']:
                    if name.startswith(gtype):
                        return gtype
            # 일반적인 접두사 추출 (괄호 앞까지)
            else:
                return name.split('(')[0] if '(' in name else name
            return name.split('(')[0] if '(' in name else name
        
        df['prefix'] = df['Name'].apply(extract_ganglioside_prefix)
        df['suffix'] = df['Name'].str.extract(r'\(([^)]+)\)')[0]
        
        print(f"📊 접두사 그룹 분석: {df['prefix'].value_counts().to_dict()}")
        
        # 특별 규칙: GD1a/GD1b 자동 분류
        auto_valid_types = ['GD1a', 'GD1b']
        auto_valid_compounds = []
        
        for gtype in auto_valid_types:
            gtype_compounds = df[df['prefix'] == gtype]
            if len(gtype_compounds) > 0:
                print(f"✅ {gtype} 자동 분류: {len(gtype_compounds)}개 화합물")
                for _, row in gtype_compounds.iterrows():
                    row_dict = row.to_dict()
                    row_dict['auto_classification'] = f'Rule: {gtype} auto-valid'
                    row_dict['forced_valid'] = True
                    auto_valid_compounds.append(row_dict)
        
        # 규칙 1: 접두사별 회귀분석 시뮬레이션 (개선된 R² 임계값 적용)
        regression_results = {}
        valid_compounds = []
        outliers = []
        
        # 먼저 자동 분류된 화합물들을 valid_compounds에 추가
        valid_compounds.extend(auto_valid_compounds)
        print(f"🎯 자동 분류 완료: {len(auto_valid_compounds)}개")
        
        # 먼저 모든 Anchor 데이터포인트를 참값(유효)으로 분류
        anchor_data = df[df['Anchor'] == 'T']
        print(f"🎯 Anchor 데이터포인트 {len(anchor_data)}개를 참값으로 분류")
        
        for prefix in df['prefix'].unique():
            if pd.isna(prefix):
                continue
                
            prefix_group = df[df['prefix'] == prefix]
            anchor_compounds = prefix_group[prefix_group['Anchor'] == 'T']
            
            # 자동 분류된 그룹은 건너뛰기 (이미 처리됨)
            if prefix in auto_valid_types:
                print(f"⏭️  {prefix}: 자동 분류로 건너뛰기")
                continue
            
            if len(anchor_compounds) >= 1 or len(prefix_group) >= 2:  # 최소 요구사항 완화
                print(f"📊 {prefix} 그룹: {len(anchor_compounds)}개 Anchor, {len(prefix_group)}개 총 화합물")
                
                # 개선된 R² 계산 - 위음성 감소를 위해 더 관대한 기준
                base_r2 = 0.92 + (len(anchor_compounds) * 0.01)  # 기본 R² 상향
                
                # 특별한 접두사 그룹에 대한 보너스 R²
                if '+HexNAc' in prefix:
                    base_r2 += 0.03  # HexNAc 그룹은 더 높은 신뢰도
                    print(f"  🧪 {prefix}: HexNAc 그룹 보너스 R² 적용")
                
                # 설정된 임계값에 따라 조정 - 더 관대하게
                if self.r2_threshold > 0.99:
                    r2 = min(base_r2 + 0.01, 0.999)  # 높은 임계값일 때
                elif self.r2_threshold < 0.95:
                    r2 = max(base_r2, 0.88)   # 낮은 임계값일 때도 합리적 수준 유지
                else:
                    r2 = base_r2
                
                slope = -0.5 + (hash(prefix) % 100) / 100
                intercept = 8.0 + (hash(prefix) % 50) / 10
                
                # 더 관대한 R² 임계값 검사 적용
                effective_threshold = max(self.r2_threshold - 0.02, 0.85)  # 임계값을 약간 완화
                
                if r2 >= effective_threshold:
                # 개선된 R² 계산 - 위음성 감소를 위해 더 관대한 기준
                base_r2 = 0.92 + (len(anchor_compounds) * 0.01)  # 기본 R² 상향
                
                # 특별한 접두사 그룹에 대한 보너스 R²
                if '+HexNAc' in prefix:
                    base_r2 += 0.03  # HexNAc 그룹은 더 높은 신뢰도
                    print(f"  🧪 {prefix}: HexNAc 그룹 보너스 R² 적용")
                
                # 설정된 임계값에 따라 조정 - 더 관대하게
                if self.r2_threshold > 0.99:
                    r2 = min(base_r2 + 0.01, 0.999)  # 높은 임계값일 때
                elif self.r2_threshold < 0.95:
                    r2 = max(base_r2, 0.88)   # 낮은 임계값일 때도 합리적 수준 유지
                else:
                    r2 = base_r2
                
                slope = -0.5 + (hash(prefix) % 100) / 100
                intercept = 8.0 + (hash(prefix) % 50) / 10
                
                # 더 관대한 R² 임계값 검사 적용
                effective_threshold = max(self.r2_threshold - 0.02, 0.85)  # 임계값을 약간 완화
                
                if r2 >= effective_threshold:
                    regression_results[prefix] = {
                        'slope': slope,
                        'intercept': intercept,
                        'r2': r2,
                        'n_samples': len(prefix_group),
                        'anchor_count': len(anchor_compounds),
                        'equation': f'RT = {slope:.4f} * Log P + {intercept:.4f}',
                        'p_value': 0.001,
                        'passes_threshold': True,
                        'effective_threshold': effective_threshold
                    }
                    
                    # 각 화합물 처리 (Anchor 우선 처리)
                    for _, row in prefix_group.iterrows():
                        row_dict = row.to_dict()
                        predicted_rt = slope * row['Log P'] + intercept
                        residual = row['RT'] - predicted_rt
                        
                        row_dict['predicted_rt'] = predicted_rt
                        row_dict['residual'] = residual
                        
                        # 표준화 잔차 계산 - 더 관대한 기준
                        std_residual = residual / 0.15  # 표준편차를 더 크게 설정하여 관대하게
                        row_dict['std_residual'] = std_residual
                        
                        # ⭐ Anchor 데이터포인트는 항상 유효로 분류 (참값 강제)
                        if row['Anchor'] == 'T':
                            row_dict['anchor_status'] = 'Reference Point'
                            row_dict['forced_valid'] = True
                            valid_compounds.append(row_dict)
                            print(f"  ✅ {row['Name']}: Anchor로 강제 유효 처리")
                        else:
                            # 일반 화합물에 더 관대한 이상치 검사 적용
                            effective_outlier_threshold = self.outlier_threshold + 0.5  # 관대한 임계값
                            if abs(std_residual) >= effective_outlier_threshold:
                                row_dict['outlier_reason'] = f'Rule 1: |Std residual| = {abs(std_residual):.2f} >= {effective_outlier_threshold}'
                                outliers.append(row_dict)
                            else:
                                valid_compounds.append(row_dict)
                                print(f"  ✅ {row['Name']}: 유효 화합물로 분류 (관대한 기준)")
                                
                else:
                    # R² 임계값 미달이지만 Anchor는 여전히 처리
                    regression_results[prefix] = {
                        'slope': slope,
                        'intercept': intercept,
                        'r2': r2,
                        'n_samples': len(prefix_group),
                        'anchor_count': len(anchor_compounds),
                        'equation': f'RT = {slope:.4f} * Log P + {intercept:.4f}',
                        'p_value': 0.1,
                        'passes_threshold': False,
                        'effective_threshold': effective_threshold
                    }
                    
                    print(f"  ⚠️ {prefix} 그룹: R² = {r2:.3f} < {effective_threshold:.3f}, 하지만 Anchor는 유효 처리")
                    
                    for _, row in prefix_group.iterrows():
                        row_dict = row.to_dict()
                        
                        # ⭐ Anchor는 R² 임계값과 관계없이 항상 유효로 분류
                        if row['Anchor'] == 'T':
                            row_dict['anchor_status'] = 'Reference Point (Low R²)'
                            row_dict['forced_valid'] = True
                            # Anchor는 R² 낮아도 유효하므로 valid_compounds에 추가
                            valid_compounds.append(row_dict)
                            print(f"  ✅ {row['Name']}: Anchor로 강제 유효 처리 (낮은 R² 무시)")
                        else:
                            # 일반 화합물은 R² 임계값 미달로 이상치 처리
                            row_dict['outlier_reason'] = f'Rule 1: Low R² = {r2:.3f} < {effective_threshold:.3f}'
                            outliers.append(row_dict)
                    for _, row in prefix_group.iterrows():
                        row_dict = row.to_dict()
                        predicted_rt = slope * row['Log P'] + intercept
                        residual = row['RT'] - predicted_rt
                        
                        row_dict['predicted_rt'] = predicted_rt
                        row_dict['residual'] = residual
                        
                        # 표준화 잔차 계산
                        std_residual = residual / 0.1
                        row_dict['std_residual'] = std_residual
                        
                        # ⭐ Anchor 데이터포인트는 항상 유효로 분류 (참값 강제)
                        if row['Anchor'] == 'T':
                            row_dict['anchor_status'] = 'Reference Point'
                            row_dict['forced_valid'] = True
                            valid_compounds.append(row_dict)
                            print(f"  ✅ {row['Name']}: Anchor로 강제 유효 처리")
                        else:
                            # 일반 화합물만 이상치 검사 적용
                            if abs(std_residual) >= self.outlier_threshold:
                                row_dict['outlier_reason'] = f'Rule 1: |Std residual| = {abs(std_residual):.2f} >= {self.outlier_threshold}'
                                outliers.append(row_dict)
                            else:
                                valid_compounds.append(row_dict)
                else:
                    # R² 임계값 미달이지만 Anchor는 여전히 처리
                    regression_results[prefix] = {
                        'slope': slope,
                        'intercept': intercept,
                        'r2': r2,
                        'n_samples': len(prefix_group),
                        'anchor_count': len(anchor_compounds),
                        'equation': f'RT = {slope:.4f} * Log P + {intercept:.4f}',
                        'p_value': 0.1,
                        'passes_threshold': False
                    }
                    
                    print(f"  ⚠️ {prefix} 그룹: R² = {r2:.3f} < {self.r2_threshold}, 하지만 Anchor는 유효 처리")
                    
                    for _, row in prefix_group.iterrows():
                        row_dict = row.to_dict()
                        
                        # ⭐ Anchor는 R² 임계값과 관계없이 항상 유효로 분류
                        if row['Anchor'] == 'T':
                            row_dict['anchor_status'] = 'Reference Point (Low R²)'
                            row_dict['forced_valid'] = True
                            # Anchor는 R² 낮아도 유효하므로 valid_compounds에 추가
                            valid_compounds.append(row_dict)
                            print(f"  ✅ {row['Name']}: Anchor로 강제 유효 처리 (낮은 R² 무시)")
                        else:
                            # 일반 화합물은 R² 임계값 미달로 이상치 처리
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
        
        # Anchor 통계 확인
        anchor_in_valid = len([c for c in valid_compounds if c.get('Anchor') == 'T'])
        anchor_success_rate = (anchor_in_valid / anchor_compounds) * 100 if anchor_compounds > 0 else 0
        
        # 설정 영향도 계산
        setting_impact = {
            'outlier_strictness': 'High' if self.outlier_threshold >= 3.0 else 'Medium' if self.outlier_threshold >= 2.0 else 'Low',
            'r2_strictness': 'Very High' if self.r2_threshold >= 0.99 else 'High' if self.r2_threshold >= 0.95 else 'Medium',
            'rt_precision': 'High' if self.rt_tolerance <= 0.1 else 'Medium' if self.rt_tolerance <= 0.2 else 'Low',
            'expected_success_rate': success_rate,
            'anchor_preservation': anchor_success_rate
        }
        
        print(f"📊 더미 분석 결과: {final_valid}/{total_compounds} 유효 ({success_rate:.1f}%)")
        print(f"🎯 Anchor 보존률: {anchor_in_valid}/{anchor_compounds} ({anchor_success_rate:.1f}%) - 모든 Anchor는 참값으로 처리되어야 함")
        
        return {
            "statistics": {
                "total_compounds": total_compounds,
                "anchor_compounds": anchor_compounds,
                "anchor_in_valid": anchor_in_valid,
                "anchor_success_rate": anchor_success_rate,
                "valid_compounds": final_valid,
                "outliers": final_outliers,
                "success_rate": success_rate,
                "rule_breakdown": {
                    "rule1_regression": len(valid_compounds),
                    "rule4_oacetylation": len(valid_oacetyl),
                    "rule5_rt_filtering": len(df),
                    "rule1_outliers": len(outliers),
                    "rule4_outliers": len(invalid_oacetyl),
                    "rule5_outliers": 0,
                    "anchor_forced_valid": anchor_in_valid
                },
                "anchor_analysis": {
                    "total_anchors": anchor_compounds,
                    "valid_anchors": anchor_in_valid,
                    "preservation_rate": anchor_success_rate,
                    "note": "All Anchors should be classified as valid (reference points)"
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
