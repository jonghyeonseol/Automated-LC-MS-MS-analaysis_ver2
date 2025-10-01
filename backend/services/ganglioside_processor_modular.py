"""
Ganglioside Data Processor - Modular Rules Version
Uses separated rule modules for maintainable analysis
"""

import sys
import os
from typing import Any, Dict, List
import numpy as np
import pandas as pd

# Import modular rules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from rules import (
    Rule1PrefixRegression,
    Rule2SugarCount,
    Rule3IsomerClassification,
    Rule4OAcetylation,
    Rule5Fragmentation
)
from utils.ganglioside_categorizer import GangliosideCategorizer


class GangliosideProcessorModular:
    """
    Ganglioside Analysis Processor using Modular Rules

    Key Design Principles:
    1. Carbon chain variation (e.g., 36:1 vs 38:1) within same prefix is EXPECTED
    2. Multiple regression accounts for carbon chain effects via a_component
    3. Outliers are determined by residuals, not by having different carbon chains
    4. Realistic thresholds based on LC-MS data variability

    Example:
    - GT3(36:1;O2), Log P: 2.8, RT: 9.599  ✅ Valid
    - GT3(38:1;O2), Log P: 3.88, RT: 11.126 ✅ Valid
    Both are valid because:
      - Same prefix (GT3 = trisialo)
      - Different carbon chains (expected variation)
      - RT increases with carbon chain (expected chemistry)
      - Multiple regression captures this relationship
    """

    def __init__(
        self,
        r2_threshold: float = 0.80,      # Realistic for LC-MS data
        outlier_threshold: float = 3.0,  # 3σ for conservative outlier detection
        rt_tolerance: float = 0.1,       # ±6 seconds for co-elution
        use_ridge: bool = True,          # Use Ridge regression
        regularization_alpha: float = 1.0  # Ridge regularization strength
    ):
        """
        Initialize processor with modular rules

        Args:
            r2_threshold: Minimum R² for valid regression (0.80 = 80% variance explained)
            outlier_threshold: Standardized residual threshold (3.0 = 99.7% confidence)
            rt_tolerance: RT window for fragmentation detection (0.1 min)
            use_ridge: Use Ridge regression to prevent overfitting (True recommended)
            regularization_alpha: Ridge regularization strength (1.0 recommended)
                                 Higher values = stronger regularization = less overfitting
        """
        # Initialize individual rules with appropriate thresholds
        self.rule1 = Rule1PrefixRegression(
            r2_threshold=r2_threshold,
            outlier_threshold=outlier_threshold,
            use_ridge=use_ridge,
            regularization_alpha=regularization_alpha
        )
        self.rule2 = Rule2SugarCount()
        self.rule3 = Rule3IsomerClassification()
        self.rule4 = Rule4OAcetylation(min_rt_increase=0.0)
        self.rule5 = Rule5Fragmentation(
            rt_tolerance=rt_tolerance,
            sugar_count_calculator=self.rule2.calculate_sugar_count
        )

        # Categorizer for visualization
        self.categorizer = GangliosideCategorizer()

        # Store settings
        self.r2_threshold = r2_threshold
        self.outlier_threshold = outlier_threshold
        self.rt_tolerance = rt_tolerance
        self.use_ridge = use_ridge
        self.regularization_alpha = regularization_alpha

        print("🧬 Ganglioside Processor (Modular) 초기화 완료")
        print(f"   📊 R² threshold: {r2_threshold} (realistic for LC-MS)")
        print(f"   📊 Outlier threshold: ±{outlier_threshold}σ (conservative)")
        print(f"   📊 RT tolerance: ±{rt_tolerance} min")
        print(f"   📊 Regularization: {'Ridge (α=' + str(regularization_alpha) + ')' if use_ridge else 'None'}")
        print("\n   ✅ Modular rules loaded:")
        print("      - Rule 1: Prefix-based multiple regression")
        print("      - Rule 2: Sugar count calculation")
        print("      - Rule 3: Isomer classification")
        print("      - Rule 4: O-acetylation validation")
        print("      - Rule 5: Fragmentation detection")

    def process_data(self, df: pd.DataFrame, data_type: str = "Porcine") -> Dict[str, Any]:
        """
        Process ganglioside data through all rules

        Args:
            df: DataFrame with columns: Name, RT, Volume, Log P, Anchor
            data_type: Biological source (Porcine/Human/Mouse)

        Returns:
            Comprehensive analysis results from all rules
        """
        print(f"\n🔬 분석 시작: {len(df)}개 화합물, 모드: {data_type}")

        # Step 0: Preprocess data (extract features)
        df_processed = self._preprocess_data(df)
        print(f"✅ 전처리 완료: {len(df_processed)}개 화합물")

        # Step 1: Apply Rule 1 (Regression)
        print("\n📊 규칙 1: 접두사 기반 회귀분석 실행 중...")
        rule1_results = self.rule1.apply(df_processed)

        # Step 2: Apply Rule 2 (Sugar Count)
        print("\n🧬 규칙 2: 당 개수 계산 실행 중...")
        rule2_results = self.rule2.apply(df_processed)

        # Step 3: Apply Rule 3 (Isomers)
        print(f"\n🧬 규칙 3: 이성질체 분류 실행 중 (데이터 타입: {data_type})...")
        rule3_results = self.rule3.apply(df_processed, data_type)

        # Step 4: Apply Rule 4 (OAcetylation)
        print("\n⚗️ 규칙 4: O-acetylation 효과 검증 실행 중...")
        rule4_results = self.rule4.apply(df_processed)

        # Step 5: Apply Rule 5 (Fragmentation)
        # Use valid compounds from Rule 1
        df_valid = pd.DataFrame(rule1_results['valid_compounds'])
        print(f"\n🔍 규칙 5: RT 필터링 및 fragmentation 탐지 실행 중...")
        print(f"   입력: {len(df_valid)}개 유효 화합물 (Rule 1 통과)")
        rule5_results = self.rule5.apply(df_valid)

        # Compile final results
        print("\n📋 최종 결과 통합 중...")
        final_results = self._compile_results(
            df_processed,
            rule1_results,
            rule2_results,
            rule3_results,
            rule4_results,
            rule5_results,
            data_type
        )

        # Add categorization for visualization
        print("\n📊 생성 중: 강글리오시드 카테고리 분석...")
        categorization = self.categorizer.categorize_compounds(df_processed)
        final_results["categorization"] = categorization
        print(f"   ✅ 카테고리 분석 완료: {categorization['statistics']['total_categories']}개 카테고리")

        success_rate = final_results['statistics']['success_rate']
        print(f"\n✅ 분석 완료: {success_rate:.1f}% 성공률")

        return final_results

    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 전처리: 접두사, 접미사 분리 및 다중회귀용 특성 추출
        """
        df = df.copy()

        # Name 컬럼에서 접두사와 접미사 분리
        df["prefix"] = df["Name"].str.extract(r"^([^(]+)")[0]
        df["suffix"] = df["Name"].str.extract(r"\(([^)]+)\)")[0]

        # 접미사에서 a, b, c 성분 추출 (36:1;O2 형태)
        suffix_parts = df["suffix"].str.extract(r"(\d+):(\d+);(\w+)")
        df["a_component"] = pd.to_numeric(suffix_parts[0], errors="coerce")  # 탄소수
        df["b_component"] = pd.to_numeric(suffix_parts[1], errors="coerce")  # 불포화도
        df["c_component"] = suffix_parts[2]  # 산소수 문자열

        # 산소수를 숫자로 변환 (O2 -> 2, O3 -> 3)
        df["oxygen_count"] = df["c_component"].str.extract(r"O(\d+)")[0]
        df["oxygen_count"] = pd.to_numeric(df["oxygen_count"], errors="coerce").fillna(0)

        # 당 개수 계산 (Rule 2 사용)
        df["sugar_count"] = df["prefix"].apply(
            lambda x: self.rule2.calculate_sugar_count(x)["total_sugars"] if pd.notna(x) else 0
        )

        # Sialic acid 개수 (e component)
        df["sialic_acid_count"] = df["prefix"].apply(
            lambda x: self.rule2.calculate_sugar_count(x)["sialic_acids"] if pd.notna(x) else 0
        )

        # 수식 그룹 이진 특성 추출
        df["has_OAc"] = df["prefix"].str.contains(r"\+OAc", na=False).astype(int)
        df["has_2OAc"] = df["prefix"].str.contains(r"\+2OAc", na=False).astype(int)
        df["has_dHex"] = df["prefix"].str.contains(r"\+dHex", na=False).astype(int)
        df["has_HexNAc"] = df["prefix"].str.contains(r"\+HexNAc", na=False).astype(int)
        df["has_NeuAc"] = df["prefix"].str.contains(r"\+NeuAc", na=False).astype(int)
        df["has_NeuGc"] = df["prefix"].str.contains(r"\+NeuGc", na=False).astype(int)

        # 데이터 품질 검증
        invalid_rows = df[df["prefix"].isna() | df["suffix"].isna()].index
        if len(invalid_rows) > 0:
            print(f"⚠️ 형식이 잘못된 {len(invalid_rows)}개 행 발견")
            df = df.drop(invalid_rows)

        print(f"📊 추출된 회귀 특성: Log P, Carbon({df['a_component'].mean():.1f}), "
              f"Unsaturation({df['b_component'].mean():.1f}), "
              f"Sugar({df['sugar_count'].mean():.1f}), "
              f"Modifications({(df['has_OAc'] + df['has_dHex'] + df['has_HexNAc']).sum()})")

        return df

    def _compile_results(
        self,
        df_processed: pd.DataFrame,
        rule1_results: Dict,
        rule2_results: Dict,
        rule3_results: Dict,
        rule4_results: Dict,
        rule5_results: Dict,
        data_type: str
    ) -> Dict[str, Any]:
        """
        Compile results from all rules into final output
        """
        # Get final valid compounds (after fragmentation consolidation)
        final_valid = rule5_results['filtered_compounds']

        # Combine all outliers
        all_outliers = []
        all_outliers.extend(rule1_results['outliers'])
        all_outliers.extend(rule4_results['invalid_oacetyl'])
        all_outliers.extend(rule5_results['fragmentation_candidates'])

        # Remove duplicates (keep first occurrence)
        seen_names = set()
        unique_outliers = []
        for outlier in all_outliers:
            name = outlier['Name']
            if name not in seen_names:
                seen_names.add(name)
                unique_outliers.append(outlier)

        # Calculate statistics
        total_compounds = len(df_processed)
        final_count = len(final_valid)
        outlier_count = len(unique_outliers)
        success_rate = (final_count / total_compounds * 100) if total_compounds > 0 else 0

        # Regression quality summary
        regression_quality = {}
        for group_name, reg_result in rule1_results['regression_results'].items():
            regression_quality[group_name] = {
                "r2": reg_result['r2'],
                "n_features": reg_result['n_features'],
                "equation": reg_result['equation'],
                "n_samples": reg_result['n_samples'],
                "quality_grade": self._grade_regression(reg_result['r2'])
            }

        return {
            "statistics": {
                "total_compounds": total_compounds,
                "valid_compounds": final_count,
                "outliers": outlier_count,
                "success_rate": success_rate,
                "data_type": data_type,
                "regression_summary": {
                    "total_groups": len(rule1_results['regression_results']),
                    "avg_r2": rule1_results['statistics']['avg_r2'],
                    "high_quality_groups": sum(
                        1 for r in rule1_results['regression_results'].values()
                        if r['r2'] >= 0.90
                    )
                }
            },
            "regression_analysis": rule1_results['regression_results'],
            "regression_quality": regression_quality,
            "valid_compounds": final_valid,
            "outliers": unique_outliers,
            "sugar_analysis": rule2_results['sugar_analysis'],
            "isomer_classification": rule3_results['isomer_classification'],
            "oacetylation_analysis": rule4_results['oacetylation_analysis'],
            "fragmentation_analysis": {
                "fragments_detected": len(rule5_results['fragmentation_candidates']),
                "consolidations": rule5_results['consolidation_details'],
                "volume_recovered": rule5_results['statistics']['volume_recovered']
            },
            "rule_statistics": {
                "rule1": rule1_results['statistics'],
                "rule2": rule2_results['statistics'],
                "rule3": rule3_results['statistics'],
                "rule4": rule4_results['statistics'],
                "rule5": rule5_results['statistics']
            }
        }

    def _grade_regression(self, r2: float) -> str:
        """Grade regression quality based on R²"""
        if r2 >= 0.95:
            return "Excellent"
        elif r2 >= 0.85:
            return "Good"
        elif r2 >= 0.70:
            return "Acceptable"
        else:
            return "Poor"

    def update_settings(
        self,
        r2_threshold=None,
        outlier_threshold=None,
        rt_tolerance=None,
        use_ridge=None,
        regularization_alpha=None
    ):
        """Update analysis settings"""
        if r2_threshold is not None:
            self.r2_threshold = r2_threshold
            self.rule1.r2_threshold = r2_threshold

        if outlier_threshold is not None:
            self.outlier_threshold = outlier_threshold
            self.rule1.outlier_threshold = outlier_threshold

        if rt_tolerance is not None:
            self.rt_tolerance = rt_tolerance
            self.rule5.rt_tolerance = rt_tolerance

        if use_ridge is not None:
            self.use_ridge = use_ridge
            self.rule1.use_ridge = use_ridge

        if regularization_alpha is not None:
            self.regularization_alpha = regularization_alpha
            self.rule1.regularization_alpha = regularization_alpha

        reg_str = f"Ridge(α={self.regularization_alpha})" if self.use_ridge else "None"
        print(f"⚙️ 설정 업데이트: R²={self.r2_threshold}, "
              f"Outlier=±{self.outlier_threshold}σ, RT=±{self.rt_tolerance}min, Reg={reg_str}")

    def get_settings(self):
        """Get current settings"""
        return {
            "r2_threshold": self.r2_threshold,
            "outlier_threshold": self.outlier_threshold,
            "rt_tolerance": self.rt_tolerance,
            "use_ridge": self.use_ridge,
            "regularization_alpha": self.regularization_alpha
        }
