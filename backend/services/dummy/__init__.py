"""
더미 서비스 모듈 초기화
"""

try:
    from .processors import (DummyGangliosideDataProcessor,
                             DummyVisualizationService)
except ImportError as e:
    print(f"Import 오류: {e}")

    # 간단한 더미 클래스 정의
    class DummyGangliosideDataProcessor:
        def __init__(self):
            self.outlier_threshold = 2.0
            self.r2_threshold = 0.90
            self.rt_tolerance = 0.3
            print("🧪 기본 Dummy Ganglioside Data Processor 초기화")

        def update_settings(
            self, outlier_threshold=None, r2_threshold=None, rt_tolerance=None
        ):
            if outlier_threshold is not None:
                self.outlier_threshold = outlier_threshold
            if r2_threshold is not None:
                self.r2_threshold = r2_threshold
            if rt_tolerance is not None:
                self.rt_tolerance = rt_tolerance
            print(f"⚙️ 설정 업데이트: {self.outlier_threshold}, {self.r2_threshold}")

        def get_settings(self):
            return {
                "outlier_threshold": self.outlier_threshold,
                "r2_threshold": self.r2_threshold,
                "rt_tolerance": self.rt_tolerance,
            }

        def process_data(self, df, data_type="Porcine"):
            print("🔬 GT1 특별 처리 더미 분석 실행")

            # 실제 데이터프레임 처리
            if df is not None and not df.empty:
                total = len(df)
                anchor_count = (
                    len(df[df["Anchor"] == "T"]) if "Anchor" in df.columns else 0
                )

                print(f"📊 분석 대상: {total}개 화합물, {anchor_count}개 Anchor")

                # 접두사 추출 (간단 버전)
                if "Name" in df.columns:
                    df_copy = df.copy()
                    df_copy["prefix"] = df_copy["Name"].str.split("(").str[0]

                    # GT1 계열 확인
                    gt1_compounds = df_copy[
                        df_copy["prefix"].str.contains("GT1", na=False)
                    ]
                    if len(gt1_compounds) > 0:
                        print(f"🎯 GT1 계열 발견: {len(gt1_compounds)}개")

                        # GT1(42:2;O2) 특별 확인
                        target_gt1 = gt1_compounds[
                            gt1_compounds["Name"].str.contains(
                                "GT1\\(42:2;O2\\)", na=False
                            )
                        ]
                        if len(target_gt1) > 0:
                            print(
                                f"🎯 GT1(42:2;O2) 특별 발견: {len(target_gt1)}개 - 강제 유효 처리!"
                            )

                # GT1 특별 처리가 적용된 성공률 계산
                base_success = 65  # GT1 처리로 기본 성공률 증가
                if self.r2_threshold <= 0.90:
                    base_success += 15  # R² 관대하면 +15%
                if self.outlier_threshold >= 2.5:
                    base_success += 10  # 이상치 관대하면 +10%

                # GT1 화합물이 있으면 추가 보너스
                if "Name" in df.columns:
                    gt1_count = len(df[df["Name"].str.contains("GT1", na=False)])
                    if gt1_count > 0:
                        gt1_bonus = min(gt1_count * 2, 15)  # GT1 화합물 수에 비례, 최대 15%
                        base_success += gt1_bonus
                        print(f"🎯 GT1 보너스 적용: {gt1_count}개 GT1 화합물로 +{gt1_bonus}% 성공률")

                success_rate = min(base_success, 95)  # 최대 95%
                valid_count = int(total * success_rate / 100)

                print(f"📊 기본 더미 분석 결과: {valid_count}/{total} 유효 ({success_rate:.1f}%)")
                print(f"🎯 Anchor 보존률: {anchor_count}/{anchor_count} (100.0%)")

                # 간단한 유효/이상치 리스트 생성
                valid_compounds = []
                outliers = []

                for i, (_, row) in enumerate(df.iterrows()):
                    row_dict = row.to_dict()

                    # Anchor는 무조건 유효
                    if row.get("Anchor") == "T":
                        row_dict["forced_valid"] = True
                        row_dict["anchor_status"] = "Reference Point"
                        valid_compounds.append(row_dict)
                    elif i < valid_count:
                        valid_compounds.append(row_dict)
                    else:
                        row_dict[
                            "outlier_reason"
                        ] = "Rule 1: Simulated outlier for demo"
                        outliers.append(row_dict)

                return {
                    "statistics": {
                        "total_compounds": total,
                        "anchor_compounds": anchor_count,
                        "anchor_in_valid": anchor_count,
                        "anchor_success_rate": 100.0,
                        "valid_compounds": len(valid_compounds),
                        "outliers": len(outliers),
                        "success_rate": success_rate,
                        "rule_breakdown": {
                            "rule1_regression": len(valid_compounds),
                            "anchor_forced_valid": anchor_count,
                            "rule1_outliers": len(outliers),
                        },
                    },
                    "valid_compounds": valid_compounds,
                    "outliers": outliers,
                    "regression_results": {
                        "GD1": {
                            "r2": 0.95,
                            "slope": -0.5,
                            "intercept": 8.0,
                            "passes_threshold": True,
                        },
                        "GM1": {
                            "r2": 0.92,
                            "slope": -0.4,
                            "intercept": 8.5,
                            "passes_threshold": True,
                        },
                    },
                    "settings_impact": {
                        "outlier_strictness": "Lenient"
                        if self.outlier_threshold >= 2.5
                        else "Moderate",
                        "r2_strictness": "Lenient"
                        if self.r2_threshold <= 0.90
                        else "Strict",
                        "rt_precision": "Relaxed"
                        if self.rt_tolerance >= 0.3
                        else "Tight",
                        "expected_success_rate": success_rate,
                        "anchor_preservation": 100.0,
                    },
                }
            else:
                # 데이터가 없는 경우 기본값
                return {
                    "statistics": {
                        "total_compounds": 0,
                        "anchor_compounds": 0,
                        "valid_compounds": 0,
                        "outliers": 0,
                        "success_rate": 0.0,
                    },
                    "valid_compounds": [],
                    "outliers": [],
                    "regression_results": {},
                }

    class DummyVisualizationService:
        def __init__(self):
            print("📊 기본 Dummy Visualization Service 초기화")

        def create_dashboard(self, results):
            return "<div>기본 더미 시각화</div>"


__all__ = ["DummyGangliosideDataProcessor", "DummyVisualizationService"]
