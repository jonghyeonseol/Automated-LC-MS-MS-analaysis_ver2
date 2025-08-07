"""
개선된 Ganglioside 분석 더미 프로세서
- GD1a/GD1b 자동 분류 기준 적용
- GD1+HexNAc 등 복합 접두사 그룹화 개선
- 위음성 감소를 위한 관대한 임계값 적용
- Anchor 데이터포인트 강제 참값 분류
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List


class DummyGangliosideDataProcessor:
    """개선된 Ganglioside 분석 더미 클래스 (위음성 감소)"""
    
    def __init__(self):
        # 기본 설정값 (더 관대한 기준으로 설정)
        self.outlier_threshold = 2.0  # 표준화 잔차 임계값 (기본값 더 관대하게)
        self.r2_threshold = 0.90      # R² 임계값 (기본값 더 낮게)
        self.rt_tolerance = 0.3       # RT 허용 오차 (기본값 더 크게)
        print("🧪 Dummy Ganglioside Data Processor 초기화 (개선된 버전)")
        
    def update_settings(self, outlier_threshold=None, r2_threshold=None, rt_tolerance=None):
        """분석 설정 업데이트"""
        if outlier_threshold is not None:
            self.outlier_threshold = outlier_threshold
        if r2_threshold is not None:
            self.r2_threshold = r2_threshold
        if rt_tolerance is not None:
            self.rt_tolerance = rt_tolerance
        print(f"⚙️ 설정 업데이트: 이상치={self.outlier_threshold}, R²={self.r2_threshold}, RT={self.rt_tolerance}")
        
    def get_settings(self):
        """현재 분석 설정 반환"""
        return {
            'outlier_threshold': self.outlier_threshold,
            'r2_threshold': self.r2_threshold,
            'rt_tolerance': self.rt_tolerance
        }
        
    def extract_ganglioside_prefix(self, name: str) -> str:
        """개선된 ganglioside 접두사 추출"""
        # GD1+HexNAc, GM1+HexNAc 등의 복합 접두사 먼저 확인
        if '+HexNAc' in name:
            base_prefix = name.split('+HexNAc')[0]
            return f"{base_prefix}+HexNAc"
        
        # 정확한 ganglioside 타입 추출 (GD1a, GD1b 등 구분)
        ganglioside_types = ['GD1a', 'GD1b', 'GM1a', 'GM1b', 'GM2', 'GM3', 'GD2', 'GD3', 'GT1a', 'GT1b', 'GT1c']
        for gtype in ganglioside_types:
            if name.startswith(gtype):
                return gtype
        
        # 일반적인 접두사 추출 (괄호 앞까지)
        return name.split('(')[0] if '(' in name else name

    def process_data(self, df: pd.DataFrame, data_type: str = "Porcine") -> Dict[str, Any]:
        """개선된 5가지 규칙 시뮬레이션 (위음성 감소)"""
        
        print(f"🔬 개선된 더미 분석 실행: 이상치={self.outlier_threshold}, R²={self.r2_threshold}, RT={self.rt_tolerance}")
        
        # 데이터 전처리 - 개선된 접두사 추출
        df = df.copy()
        df['prefix'] = df['Name'].apply(self.extract_ganglioside_prefix)
        df['suffix'] = df['Name'].str.extract(r'\(([^)]+)\)')[0]
        
        print(f"📊 접두사 그룹 분석: {df['prefix'].value_counts().to_dict()}")
        
        # 결과 저장용 리스트
        valid_compounds = []
        outliers = []
        regression_results = {}
        
        # 1단계: GD1a/GD1b 자동 분류 (강제 유효)
        auto_valid_types = ['GD1a', 'GD1b']
        for gtype in auto_valid_types:
            gtype_compounds = df[df['prefix'] == gtype]
            if len(gtype_compounds) > 0:
                print(f"✅ {gtype} 자동 분류: {len(gtype_compounds)}개 화합물 강제 유효 처리")
                for _, row in gtype_compounds.iterrows():
                    row_dict = row.to_dict()
                    row_dict['auto_classification'] = f'Rule: {gtype} auto-valid'
                    row_dict['forced_valid'] = True
                    valid_compounds.append(row_dict)
        
        # 2단계: Anchor 데이터포인트 강제 유효 분류
        anchor_data = df[df['Anchor'] == 'T']
        print(f"🎯 Anchor 데이터포인트 {len(anchor_data)}개를 참값으로 강제 분류")
        
        # 3단계: 접두사별 회귀분석 (개선된 관대한 기준)
        for prefix in df['prefix'].unique():
            if pd.isna(prefix):
                continue
                
            prefix_group = df[df['prefix'] == prefix]
            anchor_compounds = prefix_group[prefix_group['Anchor'] == 'T']
            
            # 자동 분류된 그룹은 건너뛰기
            if prefix in auto_valid_types:
                print(f"⏭️  {prefix}: 자동 분류 완료로 건너뛰기")
                continue
            
            # 최소 요구사항 완화 (Anchor 1개 이상 또는 총 화합물 2개 이상)
            if len(anchor_compounds) >= 1 or len(prefix_group) >= 2:
                print(f"📊 {prefix} 그룹: {len(anchor_compounds)}개 Anchor, {len(prefix_group)}개 총 화합물")
                
                # 개선된 R² 계산 (위음성 감소를 위한 관대한 기준)
                base_r2 = 0.88 + (len(anchor_compounds) * 0.015)  # 기본 R² 상향 조정
                
                # 특별한 접두사 그룹에 대한 보너스
                if '+HexNAc' in prefix:
                    base_r2 += 0.04  # HexNAc 그룹은 더 높은 신뢰도
                    print(f"  🧪 {prefix}: HexNAc 그룹 보너스 R² (+0.04) 적용")
                
                # 설정된 임계값에 따른 조정 (더 관대하게)
                if self.r2_threshold > 0.99:
                    r2 = min(base_r2 + 0.02, 0.999)
                elif self.r2_threshold < 0.90:
                    r2 = max(base_r2, 0.85)  # 최소 기준 보장
                else:
                    r2 = base_r2
                
                # 회귀분석 파라미터
                slope = -0.4 + (hash(prefix) % 80) / 100  # 기울기 변동 줄임
                intercept = 8.5 + (hash(prefix) % 40) / 10  # 절편 변동 줄임
                
                # 관대한 R² 임계값 적용
                effective_threshold = max(self.r2_threshold - 0.03, 0.82)  # 임계값을 더 완화
                
                if r2 >= effective_threshold:
                    # R² 임계값 통과
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
                    
                    print(f"  ✅ {prefix} 회귀분석 통과: R² = {r2:.3f} >= {effective_threshold:.3f}")
                    
                    # 각 화합물 처리
                    for _, row in prefix_group.iterrows():
                        row_dict = row.to_dict()
                        predicted_rt = slope * row['Log P'] + intercept
                        residual = row['RT'] - predicted_rt
                        
                        row_dict['predicted_rt'] = predicted_rt
                        row_dict['residual'] = residual
                        
                        # 관대한 표준화 잔차 계산
                        std_residual = residual / 0.2  # 표준편차를 더 크게 설정
                        row_dict['std_residual'] = std_residual
                        
                        # Anchor는 무조건 유효
                        if row['Anchor'] == 'T':
                            row_dict['anchor_status'] = 'Reference Point'
                            row_dict['forced_valid'] = True
                            valid_compounds.append(row_dict)
                            print(f"    🎯 {row['Name']}: Anchor로 강제 유효")
                        else:
                            # 일반 화합물에 관대한 이상치 검사
                            effective_outlier_threshold = self.outlier_threshold + 0.7  # 매우 관대한 임계값
                            if abs(std_residual) >= effective_outlier_threshold:
                                row_dict['outlier_reason'] = f'Rule 1: |Std residual| = {abs(std_residual):.2f} >= {effective_outlier_threshold:.2f}'
                                outliers.append(row_dict)
                                print(f"    ❌ {row['Name']}: 이상치 (잔차 = {abs(std_residual):.2f})")
                            else:
                                valid_compounds.append(row_dict)
                                print(f"    ✅ {row['Name']}: 유효 (잔차 = {abs(std_residual):.2f})")
                
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
                    
                    print(f"  ⚠️ {prefix} R² 미달: {r2:.3f} < {effective_threshold:.3f}, 하지만 Anchor는 유효 처리")
                    
                    for _, row in prefix_group.iterrows():
                        row_dict = row.to_dict()
                        
                        if row['Anchor'] == 'T':
                            # Anchor는 R² 관계없이 유효
                            row_dict['anchor_status'] = 'Reference Point (Low R²)'
                            row_dict['forced_valid'] = True
                            valid_compounds.append(row_dict)
                            print(f"    🎯 {row['Name']}: Anchor로 강제 유효 (낮은 R² 무시)")
                        else:
                            # 일반 화합물은 R² 미달로 이상치
                            row_dict['outlier_reason'] = f'Rule 1: Low R² = {r2:.3f} < {effective_threshold:.3f}'
                            outliers.append(row_dict)
                            print(f"    ❌ {row['Name']}: R² 미달로 이상치")
        
        # 4단계: O-acetylation 분석 (기존 로직 유지)
        oacetyl_compounds = df[df['prefix'].str.contains('OAc', na=False)]
        valid_oacetyl = []
        invalid_oacetyl = []
        
        for _, row in oacetyl_compounds.iterrows():
            row_dict = row.to_dict()
            # 95% 확률로 유효한 OAc 효과 시뮬레이션 (더 관대하게)
            if hash(row['Name']) % 20 < 19:  # 95% 확률
                row_dict['rt_increase'] = 0.15 + (hash(row['Name']) % 40) / 100
                valid_oacetyl.append(row_dict)
                print(f"  ✅ {row['Name']}: O-acetylation 유효")
            else:
                row_dict['outlier_reason'] = 'Rule 4: O-acetylation should increase RT'
                invalid_oacetyl.append(row_dict)
                print(f"  ❌ {row['Name']}: O-acetylation 무효")
        
        # 최종 통계 계산
        total_compounds = len(df)
        anchor_compounds = len(df[df['Anchor'] == 'T'])
        final_valid = len(valid_compounds)
        final_outliers = len(outliers) + len(invalid_oacetyl)
        success_rate = (final_valid / total_compounds) * 100 if total_compounds > 0 else 0
        
        # Anchor 보존률 확인
        anchor_in_valid = len([c for c in valid_compounds if c.get('Anchor') == 'T'])
        anchor_success_rate = (anchor_in_valid / anchor_compounds) * 100 if anchor_compounds > 0 else 0
        
        print(f"📊 개선된 분석 결과: {final_valid}/{total_compounds} 유효 ({success_rate:.1f}%)")
        print(f"🎯 Anchor 보존률: {anchor_in_valid}/{anchor_compounds} ({anchor_success_rate:.1f}%)")
        print(f"📈 위음성 감소 효과: 관대한 임계값 적용으로 더 많은 유효 화합물 식별")
        
        return {
            "statistics": {
                "total_compounds": total_compounds,
                "anchor_compounds": anchor_compounds,
                "anchor_in_valid": anchor_in_valid,
                "anchor_success_rate": anchor_success_rate,
                "valid_compounds": final_valid,
                "outliers": final_outliers,
                "success_rate": success_rate,
                "false_negative_reduction": "Applied lenient thresholds",
                "rule_breakdown": {
                    "rule1_regression": len(valid_compounds),
                    "rule4_oacetylation": len(valid_oacetyl),
                    "auto_classification": len([c for c in valid_compounds if c.get('auto_classification')]),
                    "anchor_forced_valid": anchor_in_valid,
                    "rule1_outliers": len(outliers),
                    "rule4_outliers": len(invalid_oacetyl),
                }
            },
            "valid_compounds": valid_compounds,
            "outliers": outliers + invalid_oacetyl,
            "regression_results": regression_results,
            "settings_impact": {
                'outlier_strictness': 'Lenient' if self.outlier_threshold >= 2.5 else 'Moderate',
                'r2_strictness': 'Lenient' if self.r2_threshold <= 0.90 else 'Strict',
                'rt_precision': 'Relaxed' if self.rt_tolerance >= 0.3 else 'Tight',
                'expected_success_rate': success_rate,
                'anchor_preservation': anchor_success_rate
            }
        }


class DummyVisualizationService:
    """더미 시각화 서비스 (변경사항 없음)"""
    
    def __init__(self):
        print("📊 Dummy Visualization Service 초기화")
    
    def create_dashboard(self, results: Dict[str, Any]) -> str:
        return "<div>더미 시각화 대시보드</div>"


class DummyRegressionAnalyzer:
    """더미 회귀분석기 (변경사항 없음)"""
    
    def __init__(self):
        print("🔬 Dummy Regression Analyzer 초기화")
    
    def analyze_regression(self, data: pd.DataFrame) -> Dict[str, Any]:
        return {"r2": 0.95, "slope": -0.5, "intercept": 8.0}
