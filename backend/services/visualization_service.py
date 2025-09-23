"""
Visualization Service - 시각화 생성 서비스
Plotly 기반 인터랙티브 차트 및 분석 결과 시각화
"""

from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from backend.utils.data_structures import VisualizationData, calculate_mass_to_charge


class VisualizationService:
    def __init__(self):
        self.color_palette = {
            "valid": "#2ecc71",  # Green
            "outlier": "#e74c3c",  # Red
            "anchor": "#3498db",  # Blue
            "regression": "#9b59b6",  # Purple
            "background": "#ecf0f1",  # Light gray
            "grid": "#bdc3c7",  # Gray
        }

        print("📊 Visualization Service 초기화 완료")

    def create_all_plots(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """모든 시각화 생성"""
        try:
            plots = {}

            # 1. 메인 대시보드
            plots["dashboard"] = self._create_dashboard(results)

            # 2. 회귀분석 산점도
            plots["regression_scatter"] = self._create_regression_scatter(results)

            # 3. 잔차 분석 플롯
            plots["residual_analysis"] = self._create_residual_analysis(results)

            # 4. 이상치 분포 히스토그램
            plots["outlier_histogram"] = self._create_outlier_histogram(results)

            # 5. 접두사별 성공률 바차트
            plots["prefix_success_rate"] = self._create_prefix_success_rate(results)

            # 6. RT-Log P 상관관계 히트맵
            plots["correlation_heatmap"] = self._create_correlation_heatmap(results)

            # 7. 규칙별 분류 결과 파이차트
            plots["rule_breakdown_pie"] = self._create_rule_breakdown_pie(results)

            # 8. 시계열 분석 (RT 분포)
            plots["rt_distribution"] = self._create_rt_distribution(results)

            # 9. 3D 분포 시각화 (새로운 기능)
            plots["3d_distribution"] = self._create_3d_distribution_plot(results)

            return {
                "status": "success",
                "message": "시각화 생성 완료",
                "plots": plots,
                "plot_count": len(plots),
            }

        except Exception as e:
            print(f"Visualization error: {str(e)}")
            return {"status": "error", "message": f"시각화 생성 중 오류: {str(e)}", "plots": {}}

    def _create_dashboard(self, results: Dict[str, Any]) -> str:
        """메인 대시보드 생성"""
        stats = results["statistics"]

        # 서브플롯 생성 (2x2 그리드)
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=["전체 통계", "규칙별 분석", "회귀분석 품질", "RT 분포"],
            specs=[
                [{"type": "indicator"}, {"type": "bar"}],
                [{"type": "scatter"}, {"type": "histogram"}],
            ],
        )

        # 1. 성공률 게이지
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=stats["success_rate"],
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "성공률 (%)"},
                delta={"reference": 80},
                gauge={
                    "axis": {"range": [None, 100]},
                    "bar": {"color": self.color_palette["valid"]},
                    "steps": [
                        {"range": [0, 50], "color": "lightgray"},
                        {"range": [50, 80], "color": "gray"},
                    ],
                    "threshold": {
                        "line": {"color": "red", "width": 4},
                        "thickness": 0.75,
                        "value": 90,
                    },
                },
            ),
            row=1,
            col=1,
        )

        # 2. 규칙별 분석 바차트
        rule_names = ["Rule 1", "Rule 4", "Rule 5"]
        rule_values = [
            stats["rule_breakdown"]["rule1_regression"],
            stats["rule_breakdown"]["rule4_oacetylation"],
            stats["rule_breakdown"]["rule5_rt_filtering"],
        ]

        fig.add_trace(
            go.Bar(
                x=rule_names,
                y=rule_values,
                marker_color=[
                    self.color_palette["valid"],
                    self.color_palette["anchor"],
                    self.color_palette["regression"],
                ],
                name="유효 화합물",
            ),
            row=1,
            col=2,
        )

        # 3. 회귀분석 R² 산점도
        if results.get("regression_quality"):
            prefixes = list(results["regression_quality"].keys())
            r2_values = [results["regression_quality"][p]["r2"] for p in prefixes]

            fig.add_trace(
                go.Scatter(
                    x=prefixes,
                    y=r2_values,
                    mode="markers+lines",
                    marker=dict(
                        size=10,
                        color=r2_values,
                        colorscale="Viridis",
                        showscale=True,
                        colorbar=dict(title="R²"),
                    ),
                    name="회귀 품질",
                ),
                row=2,
                col=1,
            )

        # 4. RT 분포 히스토그램
        all_compounds = results.get("valid_compounds", []) + results.get("outliers", [])
        rt_values = [c["RT"] for c in all_compounds if "RT" in c]

        if rt_values:
            fig.add_trace(
                go.Histogram(
                    x=rt_values,
                    nbinsx=20,
                    marker_color=self.color_palette["background"],
                    name="RT 분포",
                ),
                row=2,
                col=2,
            )

        # 레이아웃 설정
        fig.update_layout(
            title_text="🧬 Ganglioside Analysis Dashboard",
            showlegend=False,
            height=800,
            font=dict(size=12),
        )

        return fig.to_html(include_plotlyjs="cdn", div_id="dashboard")

    def _create_regression_scatter(self, results: Dict[str, Any]) -> str:
        """회귀분석 산점도 생성"""
        fig = go.Figure()

        # 유효 화합물과 이상치 분리
        valid_compounds = results.get("valid_compounds", [])
        outliers = results.get("outliers", [])

        # 유효 화합물 플롯
        if valid_compounds:
            valid_df = pd.DataFrame(valid_compounds)

            # Anchor 구분
            anchor_mask = valid_df["Anchor"] == "T"

            # Anchor 화합물
            fig.add_trace(
                go.Scatter(
                    x=valid_df[anchor_mask]["Log P"],
                    y=valid_df[anchor_mask]["RT"],
                    mode="markers",
                    marker=dict(
                        size=12,
                        color=self.color_palette["anchor"],
                        symbol="diamond",
                        line=dict(width=2, color="white"),
                    ),
                    name="Anchor (T)",
                    text=valid_df[anchor_mask]["Name"],
                    hovertemplate="<b>%{text}</b><br>Log P: %{x}<br>RT: %{y}<extra></extra>",
                )
            )

            # 일반 유효 화합물
            fig.add_trace(
                go.Scatter(
                    x=valid_df[~anchor_mask]["Log P"],
                    y=valid_df[~anchor_mask]["RT"],
                    mode="markers",
                    marker=dict(
                        size=10,
                        color=self.color_palette["valid"],
                        line=dict(width=1, color="white"),
                    ),
                    name="Valid",
                    text=valid_df[~anchor_mask]["Name"],
                    hovertemplate="<b>%{text}</b><br>Log P: %{x}<br>RT: %{y}<extra></extra>",
                )
            )

        # 이상치 플롯
        if outliers:
            outlier_df = pd.DataFrame(outliers)
            fig.add_trace(
                go.Scatter(
                    x=outlier_df["Log P"],
                    y=outlier_df["RT"],
                    mode="markers",
                    marker=dict(
                        size=10,
                        color=self.color_palette["outlier"],
                        symbol="x",
                        line=dict(width=2),
                    ),
                    name="Outliers",
                    text=outlier_df["Name"],
                    hovertemplate="<b>%{text}</b><br>Log P: %{x}<br>RT: %{y}<br>Reason: %{customdata}<extra></extra>",
                    customdata=outlier_df.get(
                        "outlier_reason", ["Unknown"] * len(outlier_df)
                    ),
                )
            )

        # 회귀선 추가
        regression_analysis = results.get("regression_analysis", {})
        for prefix, reg_data in regression_analysis.items():
            slope = reg_data["slope"]
            intercept = reg_data["intercept"]
            r2 = reg_data["r2"]

            # Log P 범위 계산
            all_log_p = []
            if valid_compounds:
                all_log_p.extend([c["Log P"] for c in valid_compounds])
            if outliers:
                all_log_p.extend([c["Log P"] for c in outliers])

            if all_log_p:
                x_range = np.linspace(min(all_log_p), max(all_log_p), 100)
                y_pred = slope * x_range + intercept

                fig.add_trace(
                    go.Scatter(
                        x=x_range,
                        y=y_pred,
                        mode="lines",
                        line=dict(dash="dash", width=2),
                        name=f"{prefix} (R²={r2:.3f})",
                        showlegend=True,
                    )
                )

        fig.update_layout(
            title="Log P vs Retention Time Regression Analysis",
            xaxis_title="Log P (Partition Coefficient)",
            yaxis_title="Retention Time (min)",
            hovermode="closest",
            height=600,
            template="plotly_white",
        )

        return fig.to_html(include_plotlyjs="cdn", div_id="regression_scatter")

    def _create_residual_analysis(self, results: Dict[str, Any]) -> str:
        """잔차 분석 플롯 생성"""
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=["잔차 vs 예측값", "표준화 잔차", "Q-Q Plot", "잔차 히스토그램"],
            specs=[
                [{"type": "scatter"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "histogram"}],
            ],
        )

        # 잔차 데이터 수집
        valid_compounds = results.get("valid_compounds", [])
        if valid_compounds:
            residuals = [
                c.get("residual", 0) for c in valid_compounds if "residual" in c
            ]
            std_residuals = [
                c.get("std_residual", 0) for c in valid_compounds if "std_residual" in c
            ]
            predicted_rt = [
                c.get("predicted_rt", c.get("RT", 0)) for c in valid_compounds
            ]

            # 1. 잔차 vs 예측값
            fig.add_trace(
                go.Scatter(
                    x=predicted_rt,
                    y=residuals,
                    mode="markers",
                    marker=dict(color=self.color_palette["valid"]),
                    name="Residuals",
                ),
                row=1,
                col=1,
            )

            # 2. 표준화 잔차
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(std_residuals))),
                    y=std_residuals,
                    mode="markers",
                    marker=dict(color=self.color_palette["anchor"]),
                    name="Std Residuals",
                ),
                row=1,
                col=2,
            )

            # 임계값 라인 추가 (±3)
            fig.add_hline(y=3, line_dash="dash", line_color="red", row=1, col=2)
            fig.add_hline(y=-3, line_dash="dash", line_color="red", row=1, col=2)

            # 3. Q-Q Plot (정규성 검정)
            if len(residuals) > 3:
                from scipy import stats as scipy_stats

                (osm, osr), (slope, intercept, r) = scipy_stats.probplot(
                    residuals, dist="norm"
                )

                fig.add_trace(
                    go.Scatter(
                        x=osm,
                        y=osr,
                        mode="markers",
                        marker=dict(color=self.color_palette["regression"]),
                        name="Q-Q Plot",
                    ),
                    row=2,
                    col=1,
                )

                # 이론적 라인 추가
                fig.add_trace(
                    go.Scatter(
                        x=osm,
                        y=slope * osm + intercept,
                        mode="lines",
                        line=dict(color="red", dash="dash"),
                        name="Theoretical Line",
                    ),
                    row=2,
                    col=1,
                )

            # 4. 잔차 히스토그램
            fig.add_trace(
                go.Histogram(
                    x=residuals,
                    nbinsx=15,
                    marker_color=self.color_palette["background"],
                    name="Residual Distribution",
                ),
                row=2,
                col=2,
            )

        fig.update_layout(title_text="Residual Analysis", showlegend=False, height=800)

        return fig.to_html(include_plotlyjs="cdn", div_id="residual_analysis")

    def _create_outlier_histogram(self, results: Dict[str, Any]) -> str:
        """이상치 분포 히스토그램 생성"""
        fig = go.Figure()

        outliers = results.get("outliers", [])
        if outliers:
            # 이상치 사유별 분류
            outlier_reasons = {}
            for outlier in outliers:
                reason = outlier.get("outlier_reason", "Unknown")
                # 규칙별로 분류
                if "Rule 1" in reason:
                    category = "Rule 1: 회귀분석"
                elif "Rule 4" in reason:
                    category = "Rule 4: O-acetylation"
                elif "Rule 5" in reason:
                    category = "Rule 5: RT 필터링"
                else:
                    category = "Other"

                if category not in outlier_reasons:
                    outlier_reasons[category] = 0
                outlier_reasons[category] += 1

            # 바차트 생성
            categories = list(outlier_reasons.keys())
            counts = list(outlier_reasons.values())
            colors = [self.color_palette["outlier"]] * len(categories)

            fig.add_trace(
                go.Bar(
                    x=categories,
                    y=counts,
                    marker_color=colors,
                    text=counts,
                    textposition="auto",
                    name="Outlier Count",
                )
            )

        fig.update_layout(
            title="Outlier Distribution by Rules",
            xaxis_title="Outlier Category",
            yaxis_title="Count",
            height=400,
            template="plotly_white",
        )

        return fig.to_html(include_plotlyjs="cdn", div_id="outlier_histogram")

    def _create_prefix_success_rate(self, results: Dict[str, Any]) -> str:
        """접두사별 성공률 바차트 생성"""
        fig = go.Figure()

        # 접두사별 통계 계산
        prefix_stats = {}
        all_compounds = results.get("valid_compounds", []) + results.get("outliers", [])

        for compound in all_compounds:
            name = compound.get("Name", "")
            if "(" in name:
                prefix = name.split("(")[0]
                if prefix not in prefix_stats:
                    prefix_stats[prefix] = {"total": 0, "valid": 0}
                prefix_stats[prefix]["total"] += 1

                # 유효 화합물인지 확인
                if compound in results.get("valid_compounds", []):
                    prefix_stats[prefix]["valid"] += 1

        # 성공률 계산
        prefixes = []
        success_rates = []
        total_counts = []

        for prefix, stats in prefix_stats.items():
            if stats["total"] > 0:
                prefixes.append(prefix)
                success_rate = (stats["valid"] / stats["total"]) * 100
                success_rates.append(success_rate)
                total_counts.append(stats["total"])

        # 색상 매핑 (성공률에 따라)
        colors = []
        for rate in success_rates:
            if rate >= 90:
                colors.append(self.color_palette["valid"])
            elif rate >= 70:
                colors.append(self.color_palette["anchor"])
            else:
                colors.append(self.color_palette["outlier"])

        fig.add_trace(
            go.Bar(
                x=prefixes,
                y=success_rates,
                marker_color=colors,
                text=[
                    f"{rate:.1f}%<br>({count})"
                    for rate, count in zip(success_rates, total_counts)
                ],
                textposition="auto",
                name="Success Rate",
            )
        )

        fig.update_layout(
            title="Success Rate by Ganglioside Prefix",
            xaxis_title="Ganglioside Prefix",
            yaxis_title="Success Rate (%)",
            height=500,
            template="plotly_white",
        )

        return fig.to_html(include_plotlyjs="cdn", div_id="prefix_success_rate")

    def _create_correlation_heatmap(self, results: Dict[str, Any]) -> str:
        """RT-Log P 상관관계 히트맵 생성"""
        fig = go.Figure()

        all_compounds = results.get("valid_compounds", []) + results.get("outliers", [])
        if all_compounds:
            # 접두사별 그룹화
            prefix_data = {}
            for compound in all_compounds:
                name = compound.get("Name", "")
                if "(" in name:
                    prefix = name.split("(")[0]
                    if prefix not in prefix_data:
                        prefix_data[prefix] = {"rt": [], "log_p": []}
                    prefix_data[prefix]["rt"].append(compound.get("RT", 0))
                    prefix_data[prefix]["log_p"].append(compound.get("Log P", 0))

            # 상관계수 계산
            prefixes = list(prefix_data.keys())
            correlation_matrix = np.zeros((len(prefixes), len(prefixes)))

            for i, prefix1 in enumerate(prefixes):
                for j, prefix2 in enumerate(prefixes):
                    if i == j:
                        correlation_matrix[i][j] = 1.0
                    else:
                        # 교차 상관계수 계산 (단순화)
                        data1 = prefix_data[prefix1]
                        data2 = prefix_data[prefix2]
                        if len(data1["rt"]) > 1 and len(data2["rt"]) > 1:
                            corr = np.corrcoef(data1["rt"], data1["log_p"])[0, 1]
                            if np.isnan(corr):
                                corr = 0
                            correlation_matrix[i][j] = abs(corr)
                        else:
                            correlation_matrix[i][j] = 0

            fig.add_trace(
                go.Heatmap(
                    z=correlation_matrix,
                    x=prefixes,
                    y=prefixes,
                    colorscale="RdYlBu_r",
                    text=correlation_matrix,
                    texttemplate="%{text:.2f}",
                    textfont={"size": 10},
                    colorbar=dict(title="Correlation"),
                )
            )

        fig.update_layout(
            title="RT-Log P Correlation Heatmap by Prefix",
            height=600,
            template="plotly_white",
        )

        return fig.to_html(include_plotlyjs="cdn", div_id="correlation_heatmap")

    def _create_rule_breakdown_pie(self, results: Dict[str, Any]) -> str:
        """규칙별 분류 결과 파이차트 생성"""
        fig = go.Figure()

        stats = results["statistics"]
        rule_breakdown = stats["rule_breakdown"]

        # 데이터 준비
        labels = [
            "Rule 1 Valid",
            "Rule 4 Valid",
            "Rule 5 Valid",
            "Rule 1 Outliers",
            "Rule 4 Outliers",
            "Rule 5 Outliers",
        ]
        values = [
            rule_breakdown["rule1_regression"],
            rule_breakdown["rule4_oacetylation"],
            rule_breakdown["rule5_rt_filtering"],
            rule_breakdown["rule1_outliers"],
            rule_breakdown["rule4_outliers"],
            rule_breakdown["rule5_outliers"],
        ]

        colors = [
            self.color_palette["valid"],
            self.color_palette["anchor"],
            self.color_palette["regression"],
            self.color_palette["outlier"],
            "#ff7675",
            "#fd79a8",
        ]

        fig.add_trace(
            go.Pie(
                labels=labels,
                values=values,
                marker_colors=colors,
                textinfo="label+percent+value",
                textposition="auto",
            )
        )

        fig.update_layout(title="Rule-based Classification Results", height=500)

        return fig.to_html(include_plotlyjs="cdn", div_id="rule_breakdown_pie")

    def _create_rt_distribution(self, results: Dict[str, Any]) -> str:
        """RT 분포 분석 생성"""
        fig = go.Figure()

        # 유효 화합물과 이상치 RT 분포
        valid_compounds = results.get("valid_compounds", [])
        outliers = results.get("outliers", [])

        if valid_compounds:
            valid_rt = [c["RT"] for c in valid_compounds]
            fig.add_trace(
                go.Histogram(
                    x=valid_rt,
                    name="Valid Compounds",
                    opacity=0.7,
                    marker_color=self.color_palette["valid"],
                    nbinsx=20,
                )
            )

        if outliers:
            outlier_rt = [c["RT"] for c in outliers]
            fig.add_trace(
                go.Histogram(
                    x=outlier_rt,
                    name="Outliers",
                    opacity=0.7,
                    marker_color=self.color_palette["outlier"],
                    nbinsx=20,
                )
            )

        fig.update_layout(
            title="Retention Time Distribution",
            xaxis_title="Retention Time (min)",
            yaxis_title="Count",
            barmode="overlay",
            height=400,
            template="plotly_white",
        )

        return fig.to_html(include_plotlyjs="cdn", div_id="rt_distribution")

    def _create_3d_distribution_plot(self, results: Dict[str, Any]) -> str:
        """
        3D 분포 시각화 생성 - Mass-to-Charge(X) vs Retention Time(Y) vs Log P(Z)
        데이터의 분포를 3차원으로 표현하여 패턴 분석
        """
        fig = go.Figure()

        # 유효 화합물과 이상치 데이터 분리
        valid_compounds = results.get("valid_compounds", [])
        outliers = results.get("outliers", [])

        # 유효 화합물 3D 산점도
        if valid_compounds:
            # 데이터 준비
            names = [c["Name"] for c in valid_compounds]
            retention_times = [c["RT"] for c in valid_compounds]
            log_p_values = [c["Log P"] for c in valid_compounds]
            volumes = [c["Volume"] for c in valid_compounds]

            # Mass-to-charge 계산
            mass_to_charge = [calculate_mass_to_charge(name) for name in names]

            # Anchor 상태 확인
            anchor_mask = [c["Anchor"] == "T" for c in valid_compounds]

            # 접두사별 색상 매핑
            prefixes = [name.split("(")[0] if "(" in name else name for name in names]
            unique_prefixes = list(set(prefixes))
            color_map = {prefix: i for i, prefix in enumerate(unique_prefixes)}
            colors = [color_map[prefix] for prefix in prefixes]

            # Volume에 따른 크기 조정 (정규화)
            min_vol, max_vol = min(volumes), max(volumes)
            if max_vol > min_vol:
                normalized_sizes = [(v - min_vol) / (max_vol - min_vol) * 20 + 5 for v in volumes]
            else:
                normalized_sizes = [10] * len(volumes)

            # Anchor 화합물 (다이아몬드 마커)
            anchor_indices = [i for i, is_anchor in enumerate(anchor_mask) if is_anchor]
            if anchor_indices:
                fig.add_trace(go.Scatter3d(
                    x=[mass_to_charge[i] for i in anchor_indices],
                    y=[retention_times[i] for i in anchor_indices],
                    z=[log_p_values[i] for i in anchor_indices],
                    mode='markers',
                    marker=dict(
                        size=[normalized_sizes[i] for i in anchor_indices],
                        color=self.color_palette["anchor"],
                        symbol='diamond',
                        line=dict(width=2, color='white'),
                        opacity=0.9
                    ),
                    name='Anchor Compounds (T)',
                    text=[f"<b>{names[i]}</b><br>m/z: {mass_to_charge[i]:.1f}<br>RT: {retention_times[i]:.3f}<br>Log P: {log_p_values[i]:.2f}<br>Volume: {volumes[i]:,}" for i in anchor_indices],
                    hovertemplate='%{text}<extra></extra>'
                ))

            # 일반 유효 화합물 (구형 마커)
            non_anchor_indices = [i for i, is_anchor in enumerate(anchor_mask) if not is_anchor]
            if non_anchor_indices:
                fig.add_trace(go.Scatter3d(
                    x=[mass_to_charge[i] for i in non_anchor_indices],
                    y=[retention_times[i] for i in non_anchor_indices],
                    z=[log_p_values[i] for i in non_anchor_indices],
                    mode='markers',
                    marker=dict(
                        size=[normalized_sizes[i] for i in non_anchor_indices],
                        color=[colors[i] for i in non_anchor_indices],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="Ganglioside Type", x=1.1),
                        line=dict(width=1, color='white'),
                        opacity=0.8
                    ),
                    name='Valid Compounds',
                    text=[f"<b>{names[i]}</b><br>m/z: {mass_to_charge[i]:.1f}<br>RT: {retention_times[i]:.3f}<br>Log P: {log_p_values[i]:.2f}<br>Volume: {volumes[i]:,}" for i in non_anchor_indices],
                    hovertemplate='%{text}<extra></extra>'
                ))

        # 이상치 3D 산점도
        if outliers:
            outlier_names = [c["Name"] for c in outliers]
            outlier_rt = [c["RT"] for c in outliers]
            outlier_log_p = [c["Log P"] for c in outliers]
            outlier_volumes = [c["Volume"] for c in outliers]
            outlier_reasons = [c.get("outlier_reason", "Unknown") for c in outliers]

            # Mass-to-charge 계산
            outlier_mz = [calculate_mass_to_charge(name) for name in outlier_names]

            # Volume에 따른 크기 조정
            if outlier_volumes:
                min_vol, max_vol = min(outlier_volumes), max(outlier_volumes)
                if max_vol > min_vol:
                    outlier_sizes = [(v - min_vol) / (max_vol - min_vol) * 15 + 5 for v in outlier_volumes]
                else:
                    outlier_sizes = [8] * len(outlier_volumes)

                fig.add_trace(go.Scatter3d(
                    x=outlier_mz,
                    y=outlier_rt,
                    z=outlier_log_p,
                    mode='markers',
                    marker=dict(
                        size=outlier_sizes,
                        color=self.color_palette["outlier"],
                        symbol='x',
                        line=dict(width=2),
                        opacity=0.7
                    ),
                    name='Outliers',
                    text=[f"<b>{name}</b><br>m/z: {mz:.1f}<br>RT: {rt:.3f}<br>Log P: {lp:.2f}<br>Volume: {vol:,}<br>Reason: {reason}"
                          for name, mz, rt, lp, vol, reason in zip(outlier_names, outlier_mz, outlier_rt, outlier_log_p, outlier_volumes, outlier_reasons)],
                    hovertemplate='%{text}<extra></extra>'
                ))

        # 3D 회귀 평면 추가 (선택적)
        if results.get("regression_analysis"):
            self._add_3d_regression_planes(fig, results, valid_compounds)

        # 레이아웃 설정
        fig.update_layout(
            title=dict(
                text="3D Distribution: Mass-to-Charge vs Retention Time vs Log P",
                x=0.5,
                font=dict(size=16)
            ),
            scene=dict(
                xaxis_title="Mass-to-Charge (m/z)",
                yaxis_title="Retention Time (min)",
                zaxis_title="Partition Coefficient (Log P)",
                camera=dict(
                    eye=dict(x=1.2, y=1.2, z=1.2)
                ),
                aspectmode='cube'
            ),
            width=900,
            height=700,
            margin=dict(l=0, r=0, t=50, b=0),
            legend=dict(
                x=0.02,
                y=0.98,
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(0,0,0,0.2)',
                borderwidth=1
            ),
            hovermode='closest'
        )

        return fig.to_html(include_plotlyjs="cdn", div_id="3d_distribution")

    def _add_3d_regression_planes(self, fig: go.Figure, results: Dict[str, Any], valid_compounds: list):
        """
        3D 회귀 평면 추가 (선택적 기능)
        각 접두사 그룹별로 RT-LogP 관계를 나타내는 평면 표시
        """
        regression_analysis = results.get("regression_analysis", {})

        for prefix, reg_data in regression_analysis.items():
            if reg_data["r2"] < 0.95:  # R²가 낮은 경우 평면 생략
                continue

            # 해당 접두사의 화합물들 필터링
            prefix_compounds = [c for c in valid_compounds if c["Name"].startswith(prefix)]
            if len(prefix_compounds) < 3:
                continue

            # Log P 범위 설정
            log_p_values = [c["Log P"] for c in prefix_compounds]
            log_p_min, log_p_max = min(log_p_values), max(log_p_values)

            # 평면을 위한 격자 생성
            log_p_grid = np.linspace(log_p_min, log_p_max, 10)

            # Mass-to-charge 추정 (해당 접두사의 평균값 사용)
            mz_values = [calculate_mass_to_charge(c["Name"]) for c in prefix_compounds]
            avg_mz = np.mean(mz_values)
            mz_grid = np.full_like(log_p_grid, avg_mz)

            # 회귀선에 따른 RT 계산
            slope = reg_data["slope"]
            intercept = reg_data["intercept"]
            rt_grid = slope * log_p_grid + intercept

            # 평면 추가 (선 형태로 단순화)
            fig.add_trace(go.Scatter3d(
                x=mz_grid,
                y=rt_grid,
                z=log_p_grid,
                mode='lines',
                line=dict(
                    color=self.color_palette["regression"],
                    width=4,
                    dash='dash'
                ),
                name=f'{prefix} Regression (R²={reg_data["r2"]:.3f})',
                showlegend=True,
                hovertemplate=f'<b>{prefix}</b><br>Predicted RT: %{{y:.3f}}<br>Log P: %{{z:.2f}}<extra></extra>'
            ))

    def create_visualization_data(self, results: Dict[str, Any]) -> VisualizationData:
        """
        분석 결과를 VisualizationData 구조체로 변환
        외부에서 사용할 수 있는 구조화된 3D 데이터 제공
        """
        valid_compounds = results.get("valid_compounds", [])
        outliers = results.get("outliers", [])
        all_compounds = valid_compounds + outliers

        if not all_compounds:
            return VisualizationData(
                x_data=[], y_data=[], z_data=[], labels=[], colors=[], sizes=[],
                anchor_mask=[], title="Empty Dataset"
            )

        # 데이터 추출
        names = [c["Name"] for c in all_compounds]
        retention_times = [c["RT"] for c in all_compounds]
        log_p_values = [c["Log P"] for c in all_compounds]
        volumes = [c["Volume"] for c in all_compounds]

        # Mass-to-charge 계산
        mass_to_charge = [calculate_mass_to_charge(name) for name in names]

        # 상태별 마스크
        anchor_mask = [c["Anchor"] == "T" for c in all_compounds]
        outlier_mask = [c in outliers for c in all_compounds]

        # 색상 및 크기 설정
        colors = []
        sizes = []
        for i, compound in enumerate(all_compounds):
            if outlier_mask[i]:
                colors.append(self.color_palette["outlier"])
                sizes.append(8)
            elif anchor_mask[i]:
                colors.append(self.color_palette["anchor"])
                sizes.append(12)
            else:
                colors.append(self.color_palette["valid"])
                sizes.append(10)

        # 접두사별 그룹 매핑
        prefix_groups = {}
        for i, name in enumerate(names):
            prefix = name.split("(")[0] if "(" in name else name
            if prefix not in prefix_groups:
                prefix_groups[prefix] = []
            prefix_groups[prefix].append(i)

        return VisualizationData(
            x_data=mass_to_charge,
            y_data=retention_times,
            z_data=log_p_values,
            labels=names,
            colors=colors,
            sizes=sizes,
            anchor_mask=anchor_mask,
            outlier_mask=outlier_mask,
            prefix_groups=prefix_groups,
            title="LC-MS-MS Ganglioside Analysis Results"
        )
