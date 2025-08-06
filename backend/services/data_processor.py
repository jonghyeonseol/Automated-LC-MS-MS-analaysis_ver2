"""
Ganglioside Data Processor - 핵심 분석 로직
5가지 규칙 기반 산성 당지질 데이터 자동 분류 시스템
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import re


class GangliosideDataProcessor:
    def __init__(self):
        self.r2_threshold = 0.99
        self.outlier_threshold = 3.0
        self.rt_tolerance = 0.1
        
    def process_data(self, df: pd.DataFrame, data_type: str = "Porcine") -> Dict[str, Any]:
        """
        메인 데이터 처리 함수
        5가지 규칙을 순차적으로 적용하여 데이터 분류
        """
        
        # 데이터 전처리
        df_processed = self._preprocess_data(df.copy())
        
        # 규칙 1: 접두사 기반 회귀분석
        rule1_results = self._apply_rule1_prefix_regression(df_processed)
        
        # 규칙 2-3: 당 개수 계산 및 이성질체 분류
        rule23_results = self._apply_rule2_3_sugar_count(df_processed, data_type)
        
        # 규칙 4: O-acetylation 효과 검증
        rule4_results = self._apply_rule4_oacetylation(df_processed)
        
        # 규칙 5: RT 범위 기반 필터링 및 in-source fragmentation 탐지
        rule5_results = self._apply_rule5_rt_filtering(df_processed)
        
        # 통합 결과 생성
        final_results = self._compile_results(df_processed, rule1_results, rule23_results, rule4_results, rule5_results)
        
        return final_results
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 전처리: 접두사, 접미사 분리"""
        
        # Name 컬럼에서 접두사와 접미사 분리
        df['prefix'] = df['Name'].str.extract(r'^([^(]+)')[0]
        df['suffix'] = df['Name'].str.extract(r'\(([^)]+)\)')[0]
        
        # 접미사에서 a, b, c 성분 추출 (36:1;O2 형태)
        suffix_parts = df['suffix'].str.extract(r'(\d+):(\d+);(\w+)')
        df['a_component'] = suffix_parts[0].astype(float)  # 탄소수
        df['b_component'] = suffix_parts[1].astype(float)  # 불포화도
        df['c_component'] = suffix_parts[2]  # 산소수
        
        return df
    
    def _apply_rule1_prefix_regression(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        규칙 1: 접두사 기반 회귀분석
        동일 접두사 그룹에서 Log P-RT 선형성 검증 (R² ≥ 0.99)
        """
        
        regression_results = {}
        valid_compounds = []
        outliers = []
        
        # 접두사별 그룹화
        for prefix in df['prefix'].unique():
            if pd.isna(prefix):
                continue
                
            prefix_group = df[df['prefix'] == prefix].copy()
            
            if len(prefix_group) < 3:  # 최소 3개 데이터 포인트 필요
                continue
            
            # Anchor='T'인 화합물을 회귀 기준점으로 설정
            anchor_compounds = prefix_group[prefix_group['Anchor'] == 'T']
            
            if len(anchor_compounds) >= 2:
                # 회귀분석 수행
                X = anchor_compounds[['Log P']].values
                y = anchor_compounds['RT'].values
                
                model = LinearRegression()
                model.fit(X, y)
                
                # 예측값 계산
                y_pred = model.predict(X)
                r2 = r2_score(y, y_pred)
                
                # R² ≥ 0.99 조건 확인
                if r2 >= self.r2_threshold:
                    # 전체 그룹에 모델 적용
                    all_pred = model.predict(prefix_group[['Log P']].values)
                    residuals = prefix_group['RT'].values - all_pred
                    
                    # 표준화 잔차 계산
                    std_residuals = residuals / np.std(residuals)
                    
                    # 이상치 판별 (|표준화 잔차| >= 3)
                    outlier_mask = np.abs(std_residuals) >= self.outlier_threshold
                    
                    # 결과 저장
                    regression_results[prefix] = {
                        'slope': model.coef_[0],
                        'intercept': model.intercept_,
                        'r2': r2,
                        'n_samples': len(prefix_group),
                        'equation': f'RT = {model.coef_[0]:.4f} * Log P + {model.intercept_:.4f}'
                    }
                    
                    # 유효 화합물과 이상치 분류
                    for idx, (_, row) in enumerate(prefix_group.iterrows()):
                        if not outlier_mask[idx]:
                            valid_compounds.append(row.to_dict())
                        else:
                            outlier_info = row.to_dict()
                            outlier_info['outlier_reason'] = f'Rule 1: Standardized residual = {std_residuals[idx]:.3f}'
                            outliers.append(outlier_info)
        
        return {
            'regression_results': regression_results,
            'valid_compounds': valid_compounds,
            'outliers': outliers
        }
    
    def _apply_rule2_3_sugar_count(self, df: pd.DataFrame, data_type: str) -> Dict[str, Any]:
        """
        규칙 2-3: 당 개수 계산 및 구조 이성질체 분류
        """
        
        sugar_analysis = {}
        isomer_corrections = []
        
        for _, row in df.iterrows():
            prefix = row['prefix']
            if pd.isna(prefix):
                continue
            
            # 당 개수 계산
            sugar_count = self._calculate_sugar_count(prefix)
            
            # 이성질체 분류 (f값이 1인 경우만)
            isomer_type = self._classify_isomer(prefix, data_type)
            
            sugar_analysis[row['Name']] = {
                'prefix': prefix,
                'sugar_count': sugar_count,
                'isomer_type': isomer_type,
                'can_have_isomers': sugar_count['f'] == 1
            }
        
        return {
            'sugar_analysis': sugar_analysis,
            'isomer_corrections': isomer_corrections
        }
    
    def _calculate_sugar_count(self, prefix: str) -> Dict[str, int]:
        """
        규칙 2-3: 접두사 기반 당 개수 계산
        예: GM1 -> G(0) + M(1) + 1 = 2, GD1 -> G(0) + D(2) + 1 = 3
        """
        
        if len(prefix) < 3:
            return {'d': 0, 'e': 0, 'f': 0, 'total': 0}
        
        # 첫 3글자 추출
        d, e, f = prefix[0], prefix[1], prefix[2]
        
        # 규칙 2: e 문자에 따른 당 개수
        e_mapping = {'A': 0, 'M': 1, 'D': 2, 'T': 3, 'Q': 4, 'P': 5}
        e_count = e_mapping.get(e, 0)
        
        # 규칙 3: f 숫자에 따른 당 개수 (5 - f)
        try:
            f_num = int(f)
            f_count = 5 - f_num
        except (ValueError, TypeError):
            f_count = 0
        
        # 총 당 개수
        total_sugar = e_count + f_count
        
        # 추가 수식 그룹 확인 (+dHex, +HexNAc)
        additional = 0
        if '+dHex' in prefix:
            additional += 1
        if '+HexNAc' in prefix:
            additional += 1
        
        return {
            'd': d,
            'e': e_count,
            'f': f_num if f.isdigit() else 0,
            'additional': additional,
            'total': total_sugar + additional
        }
    
    def _classify_isomer(self, prefix: str, data_type: str) -> str:
        """
        구조 이성질체 분류
        """
        
        # GD1 이성질체 처리
        if prefix.startswith('GD1'):
            if '+dHex' in prefix:
                return 'GD1b'  # GD1+dHex는 GD1b로 분류
            elif '+HexNAc' in prefix:
                return 'GD1a'  # GD1+HexNAc는 GD1a로 분류
            else:
                return 'GD1'  # RT 기반으로 a/b 구분 필요
        
        # GQ1 이성질체 처리
        elif prefix.startswith('GQ1'):
            if data_type == "Porcine":
                return 'GQ1bα'  # Porcine에서는 GQ1b를 GQ1bα로 분류
            else:
                return 'GQ1'  # RT 기반으로 b/c 구분 필요
        
        return prefix
    
    def _apply_rule4_oacetylation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        규칙 4: O-acetylation 효과 검증
        OAc 그룹이 있는 경우 RT가 증가해야 함
        """
        
        oacetylation_results = {}
        valid_oacetyl_compounds = []
        invalid_oacetyl_compounds = []
        
        # OAc가 포함된 화합물들 분석
        oacetyl_compounds = df[df['prefix'].str.contains('OAc', na=False)]
        
        for _, oacetyl_row in oacetyl_compounds.iterrows():
            # 기본 화합물 (OAc 없는 버전) 찾기
            base_prefix = oacetyl_row['prefix'].replace('+OAc', '').replace('+2OAc', '')
            base_compounds = df[(df['prefix'] == base_prefix) & 
                              (df['suffix'] == oacetyl_row['suffix'])]
            
            if len(base_compounds) > 0:
                base_rt = base_compounds['RT'].iloc[0]
                oacetyl_rt = oacetyl_row['RT']
                
                # Rule 4: OAc가 있으면 RT가 증가해야 함
                if oacetyl_rt > base_rt:
                    valid_oacetyl_compounds.append(oacetyl_row.to_dict())
                    oacetylation_results[oacetyl_row['Name']] = {
                        'base_rt': base_rt,
                        'oacetyl_rt': oacetyl_rt,
                        'rt_increase': oacetyl_rt - base_rt,
                        'is_valid': True
                    }
                else:
                    invalid_oacetyl_compounds.append(oacetyl_row.to_dict())
                    oacetylation_results[oacetyl_row['Name']] = {
                        'base_rt': base_rt,
                        'oacetyl_rt': oacetyl_rt,
                        'rt_increase': oacetyl_rt - base_rt,
                        'is_valid': False,
                        'outlier_reason': 'Rule 4: O-acetylation should increase RT'
                    }
        
        return {
            'oacetylation_analysis': oacetylation_results,
            'valid_oacetyl': valid_oacetyl_compounds,
            'invalid_oacetyl': invalid_oacetyl_compounds
        }
    
    def _apply_rule5_rt_filtering(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        규칙 5: RT 범위 기반 필터링 및 in-source fragmentation 탐지
        동일 접미사 그룹 내에서 ±0.1분 범위 이상치 제거
        """
        
        rt_filtering_results = {}
        fragmentation_candidates = []
        filtered_compounds = []
        
        # 접미사별 그룹화
        for suffix in df['suffix'].unique():
            if pd.isna(suffix):
                continue
                
            suffix_group = df[df['suffix'] == suffix].copy()
            
            if len(suffix_group) <= 1:
                continue
            
            # RT 기반으로 정렬
            suffix_group = suffix_group.sort_values('RT')
            
            # RT 범위 내 그룹 식별 (±0.1분)
            rt_groups = []
            current_group = [suffix_group.iloc[0]]
            
            for i in range(1, len(suffix_group)):
                current_rt = suffix_group.iloc[i]['RT']
                reference_rt = current_group[0]['RT']
                
                if abs(current_rt - reference_rt) <= self.rt_tolerance:
                    current_group.append(suffix_group.iloc[i])
                else:
                    rt_groups.append(current_group)
                    current_group = [suffix_group.iloc[i]]
            
            if current_group:
                rt_groups.append(current_group)
            
            # 각 RT 그룹에서 가장 당 개수가 많은 화합물만 유지
            for group in rt_groups:
                if len(group) > 1:
                    # 당 개수 계산
                    sugar_counts = []
                    for compound in group:
                        sugar_info = self._calculate_sugar_count(compound['prefix'])
                        sugar_counts.append((compound, sugar_info['total']))
                    
                    # 당 개수가 가장 많은 화합물 선택 (Log P가 가장 낮음)
                    sugar_counts.sort(key=lambda x: (-x[1], x[0]['Log P']))  # 당 개수 내림차순, Log P 오름차순
                    
                    # 첫 번째는 유효, 나머지는 fragmentation 후보
                    valid_compound = sugar_counts[0][0]
                    filtered_compounds.append(valid_compound.to_dict())
                    
                    # Volume 통합 (규칙5에 따라)
                    total_volume = sum(compound['Volume'] for compound, _ in sugar_counts)
                    valid_compound_dict = valid_compound.to_dict()
                    valid_compound_dict['Volume'] = total_volume
                    valid_compound_dict['merged_compounds'] = len(sugar_counts)
                    
                    for compound, _ in sugar_counts[1:]:
                        fragmentation_info = compound.to_dict()
                        fragmentation_info['outlier_reason'] = 'Rule 5: In-source fragmentation candidate'
                        fragmentation_info['reference_compound'] = valid_compound['Name']
                        fragmentation_candidates.append(fragmentation_info)
                else:
                    # 단일 화합물은 그대로 유지
                    filtered_compounds.append(group[0].to_dict())
        
        return {
            'rt_filtering_results': rt_filtering_results,
            'filtered_compounds': filtered_compounds,
            'fragmentation_candidates': fragmentation_candidates
        }
    
    def _enhance_outlier_detection(self, df: pd.DataFrame, rule1_results: Dict, 
                                  rule4_results: Dict, rule5_results: Dict) -> Dict[str, List]:
        """
        이상치 탐지 정교화
        여러 규칙의 결과를 종합하여 최종 이상치 판별
        """
        
        all_outliers = []
        all_valid_compounds = []
        
        # Rule 1 이상치
        all_outliers.extend(rule1_results.get('outliers', []))
        
        # Rule 4 이상치 (O-acetylation 위반)
        all_outliers.extend(rule4_results.get('invalid_oacetyl', []))
        
        # Rule 5 이상치 (fragmentation 후보)
        all_outliers.extend(rule5_results.get('fragmentation_candidates', []))
        
        # 유효 화합물들 수집
        all_valid_compounds.extend(rule1_results.get('valid_compounds', []))
        all_valid_compounds.extend(rule4_results.get('valid_oacetyl', []))
        all_valid_compounds.extend(rule5_results.get('filtered_compounds', []))
        
        # 중복 제거 (Name 기준)
        seen_names = set()
        unique_outliers = []
        for outlier in all_outliers:
            if outlier['Name'] not in seen_names:
                seen_names.add(outlier['Name'])
                unique_outliers.append(outlier)
        
        seen_names = set()
        unique_valid = []
        for valid in all_valid_compounds:
            if valid['Name'] not in seen_names:
                seen_names.add(valid['Name'])
                unique_valid.append(valid)
        
        return {
            'final_outliers': unique_outliers,
            'final_valid_compounds': unique_valid
        }
    
    def _compile_results(self, df: pd.DataFrame, rule1_results: Dict, rule23_results: Dict, 
                        rule4_results: Dict, rule5_results: Dict) -> Dict[str, Any]:
        """최종 결과 통합"""
        
        # 이상치 탐지 정교화
        enhanced_outliers = self._enhance_outlier_detection(df, rule1_results, rule4_results, rule5_results)
        
        total_compounds = len(df)
        anchor_compounds = len(df[df['Anchor'] == 'T'])
        valid_compounds = len(enhanced_outliers['final_valid_compounds'])
        outlier_count = len(enhanced_outliers['final_outliers'])
        
        # 통계 정보
        statistics = {
            'total_compounds': total_compounds,
            'anchor_compounds': anchor_compounds,
            'valid_compounds': valid_compounds,
            'outliers': outlier_count,
            'success_rate': (valid_compounds / total_compounds) * 100 if total_compounds > 0 else 0,
            'rule_breakdown': {
                'rule1_regression': len(rule1_results.get('valid_compounds', [])),
                'rule4_oacetylation': len(rule4_results.get('valid_oacetyl', [])),
                'rule5_rt_filtering': len(rule5_results.get('filtered_compounds', [])),
                'rule1_outliers': len(rule1_results.get('outliers', [])),
                'rule4_outliers': len(rule4_results.get('invalid_oacetyl', [])),
                'rule5_outliers': len(rule5_results.get('fragmentation_candidates', []))
            }
        }
        
        return {
            'statistics': statistics,
            'regression_analysis': rule1_results['regression_results'],
            'valid_compounds': enhanced_outliers['final_valid_compounds'],
            'outliers': enhanced_outliers['final_outliers'],
            'sugar_analysis': rule23_results['sugar_analysis'],
            'oacetylation_analysis': rule4_results.get('oacetylation_analysis', {}),
            'rt_filtering_summary': {
                'fragmentation_detected': len(rule5_results.get('fragmentation_candidates', [])),
                'volume_merged': sum(1 for c in rule5_results.get('filtered_compounds', []) 
                                   if c.get('merged_compounds', 1) > 1)
            },
            'status': 'Complete analysis - All Rules 1-5 active',
            'target_achievement': f"{valid_compounds}/133 compounds identified",
            'detailed_breakdown': {
                'by_rule': statistics['rule_breakdown'],
                'quality_metrics': {
                    'regression_quality': len([r for r in rule1_results['regression_results'].values() 
                                             if r.get('r2', 0) >= self.r2_threshold]),
                    'oacetylation_compliance': len(rule4_results.get('valid_oacetyl', [])),
                    'fragmentation_filtered': len(rule5_results.get('fragmentation_candidates', []))
                }
            }
        }