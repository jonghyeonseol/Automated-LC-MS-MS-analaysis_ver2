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
        """모든 시각화 생성 - 2D와 3D 통합"""
        try:
            plots = {}

            # 1. 메인 대시보드
            plots["dashboard"] = self._create_dashboard(results)

            # 2. 통합 시각화 세트 (2D + 3D)
            plots["integrated_visualization"] = self._create_integrated_visualization(results)

            # 3. 회귀분석 산점도 (2D)
            plots["regression_scatter"] = self._create_regression_scatter(results)

            # 4. 3D 분포 시각화
            plots["3d_distribution"] = self._create_3d_distribution_plot(results)

            # 5. 잔차 분석 플롯
            plots["residual_analysis"] = self._create_residual_analysis(results)

            # 6. 이상치 분포 히스토그램
            plots["outlier_histogram"] = self._create_outlier_histogram(results)

            # 7. 접두사별 성공률 바차트
            plots["prefix_success_rate"] = self._create_prefix_success_rate(results)

            # 8. RT-Log P 상관관계 히트맵
            plots["correlation_heatmap"] = self._create_correlation_heatmap(results)

            # 9. 규칙별 분류 결과 파이차트
            plots["rule_breakdown_pie"] = self._create_rule_breakdown_pie(results)

            # 10. 시계열 분석 (RT 분포)
            plots["rt_distribution"] = self._create_rt_distribution(results)

            return {
                "status": "success",
                "message": "통합 시각화 생성 완료",
                "plots": plots,
                "plot_count": len(plots),
                "features": {
                    "has_2d_plots": True,
                    "has_3d_plots": True,
                    "has_integrated_view": True
                }
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

    def _create_integrated_visualization(self, results: Dict[str, Any]) -> str:
        """
        통합 시각화 생성 - 2D 산점도와 3D 분포를 함께 표시
        탭 인터페이스로 전환 가능한 형태
        """
        # 데이터 준비
        valid_compounds = results.get("valid_compounds", [])
        outliers = results.get("outliers", [])
        all_compounds = valid_compounds + outliers

        if not all_compounds:
            return '<div class="no-data">표시할 데이터가 없습니다.</div>'

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

        # HTML 템플릿 생성
        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>통합 시각화 - 2D & 3D 분석</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .tab-container {{
            background-color: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
        }}
        .tab-nav {{
            display: flex;
            justify-content: center;
            padding: 0;
            margin: 0;
            list-style: none;
        }}
        .tab-nav li {{
            margin: 0 5px;
        }}
        .tab-nav button {{
            background: none;
            border: none;
            padding: 15px 30px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            border-radius: 10px 10px 0 0;
            transition: all 0.3s ease;
            color: #6c757d;
        }}
        .tab-nav button.active {{
            background: white;
            color: #495057;
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1);
        }}
        .tab-nav button:hover:not(.active) {{
            background-color: #e9ecef;
            color: #495057;
        }}
        .tab-content {{
            padding: 30px;
            min-height: 600px;
        }}
        .tab-pane {{
            display: none;
        }}
        .tab-pane.active {{
            display: block;
        }}
        .plot-container {{
            width: 100%;
            height: 700px;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            overflow: hidden;
        }}
        .info-panel {{
            background-color: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        .legend {{
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            border: 1px solid #e9ecef;
        }}
        .legend h4 {{
            margin-top: 0;
            color: #495057;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 10px;
        }}
        .legend-color {{
            display: inline-block;
            width: 15px;
            height: 15px;
            border-radius: 3px;
            margin-right: 8px;
            vertical-align: middle;
        }}
        .controls {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .btn {{
            background-color: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin: 0 5px;
            transition: background-color 0.3s;
        }}
        .btn:hover {{
            background-color: #5a67d8;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧬 통합 LC-MS-MS 데이터 시각화</h1>
            <p>2D 산점도와 3D 분포 분석을 동시에 제공하는 인터랙티브 플랫폼</p>
        </div>

        <div class="tab-container">
            <ul class="tab-nav">
                <li><button class="tab-btn active" data-tab="tab-2d">📊 2D 산점도</button></li>
                <li><button class="tab-btn" data-tab="tab-3d">🌌 3D 분포도</button></li>
                <li><button class="tab-btn" data-tab="tab-comparison">🔄 비교 분석</button></li>
                <li><button class="tab-btn" data-tab="tab-stats">📈 통계 정보</button></li>
            </ul>
        </div>

        <div class="tab-content">
            <!-- 2D 산점도 탭 -->
            <div id="tab-2d" class="tab-pane active">
                <div class="info-panel">
                    <strong>📊 2D 산점도 분석:</strong> Retention Time vs Log P 관계를 통한 전통적인 분석 방법입니다.
                    각 점은 화합물을 나타내며, 색상과 모양으로 상태를 구분합니다.
                </div>
                <div class="controls">
                    <button class="btn" onclick="reset2DView()">🔄 시점 초기화</button>
                    <button class="btn" onclick="toggle2DOutliers()">👁️ 이상치 토글</button>
                    <button class="btn" onclick="show2DRegression()">📈 회귀선 표시</button>
                </div>
                <div id="plot-2d" class="plot-container"></div>
                <div class="legend">
                    <h4>범례</h4>
                    <div class="legend-item">
                        <span class="legend-color" style="background-color: #3498db;"></span>
                        Anchor 화합물 (T)
                    </div>
                    <div class="legend-item">
                        <span class="legend-color" style="background-color: #2ecc71;"></span>
                        유효 화합물
                    </div>
                    <div class="legend-item">
                        <span class="legend-color" style="background-color: #e74c3c;"></span>
                        이상치
                    </div>
                </div>
            </div>

            <!-- 3D 분포도 탭 -->
            <div id="tab-3d" class="tab-pane">
                <div class="info-panel">
                    <strong>🌌 3D 분포 분석:</strong> Mass-to-Charge(X), Retention Time(Y), Log P(Z) 3차원 공간에서의
                    화합물 분포를 시각화합니다. 마우스로 회전하여 다양한 각도에서 관찰할 수 있습니다.
                </div>
                <div class="controls">
                    <button class="btn" onclick="reset3DView()">🔄 시점 초기화</button>
                    <button class="btn" onclick="toggle3DOutliers()">👁️ 이상치 토글</button>
                    <button class="btn" onclick="toggle3DRegression()">📈 회귀평면 토글</button>
                </div>
                <div id="plot-3d" class="plot-container"></div>
                <div class="legend">
                    <h4>축 정보</h4>
                    <div class="legend-item">
                        <strong>X축:</strong> Mass-to-Charge (m/z)
                    </div>
                    <div class="legend-item">
                        <strong>Y축:</strong> Retention Time (min)
                    </div>
                    <div class="legend-item">
                        <strong>Z축:</strong> Partition Coefficient (Log P)
                    </div>
                </div>
            </div>

            <!-- 비교 분석 탭 -->
            <div id="tab-comparison" class="tab-pane">
                <div class="info-panel">
                    <strong>🔄 비교 분석:</strong> 2D와 3D 시각화를 동시에 보여주어 상호 비교가 가능합니다.
                    각 플롯에서 선택한 화합물은 다른 플롯에서도 하이라이트됩니다.
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div>
                        <h3 style="text-align: center;">2D 산점도</h3>
                        <div id="plot-2d-comparison" style="height: 400px; border: 1px solid #e9ecef; border-radius: 5px;"></div>
                    </div>
                    <div>
                        <h3 style="text-align: center;">3D 분포도</h3>
                        <div id="plot-3d-comparison" style="height: 400px; border: 1px solid #e9ecef; border-radius: 5px;"></div>
                    </div>
                </div>
            </div>

            <!-- 통계 정보 탭 -->
            <div id="tab-stats" class="tab-pane">
                <div class="info-panel">
                    <strong>📈 통계 정보:</strong> 분석된 데이터의 주요 통계 지표와 분포 특성을 확인할 수 있습니다.
                </div>
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{len(all_compounds)}</div>
                        <div class="stat-label">총 화합물</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #27ae60, #229954);">
                        <div class="stat-number">{len(valid_compounds)}</div>
                        <div class="stat-label">유효 화합물</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #e74c3c, #c0392b);">
                        <div class="stat-number">{len(outliers)}</div>
                        <div class="stat-label">이상치</div>
                    </div>
                    <div class="stat-card" style="background: linear-gradient(135deg, #f39c12, #e67e22);">
                        <div class="stat-number">{len([c for c in all_compounds if c["Anchor"] == "T"])}</div>
                        <div class="stat-label">Anchor 화합물</div>
                    </div>
                </div>
                <div style="margin-top: 30px;">
                    <h3>데이터 범위</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="background-color: #f8f9fa;">
                            <th style="padding: 10px; border: 1px solid #e9ecef;">속성</th>
                            <th style="padding: 10px; border: 1px solid #e9ecef;">최소값</th>
                            <th style="padding: 10px; border: 1px solid #e9ecef;">최대값</th>
                            <th style="padding: 10px; border: 1px solid #e9ecef;">평균</th>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">Mass-to-Charge (m/z)</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{min(mass_to_charge):.1f}</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{max(mass_to_charge):.1f}</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{sum(mass_to_charge)/len(mass_to_charge):.1f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">Retention Time (min)</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{min(retention_times):.2f}</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{max(retention_times):.2f}</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{sum(retention_times)/len(retention_times):.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">Log P</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{min(log_p_values):.2f}</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{max(log_p_values):.2f}</td>
                            <td style="padding: 10px; border: 1px solid #e9ecef;">{sum(log_p_values)/len(log_p_values):.2f}</td>
                        </tr>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 데이터 준비
        const compoundData = {{
            names: {names},
            retention_times: {retention_times},
            log_p_values: {log_p_values},
            mass_to_charge: {mass_to_charge},
            volumes: {volumes},
            anchor_mask: {anchor_mask},
            outlier_mask: {outlier_mask}
        }};

        let showOutliers2D = true;
        let showOutliers3D = true;
        let showRegression2D = false;
        let showRegression3D = false;

        // 탭 전환 기능
        document.addEventListener('DOMContentLoaded', function() {{
            // 탭 버튼 이벤트 리스너
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.addEventListener('click', function() {{
                    const targetTab = this.getAttribute('data-tab');
                    switchTab(targetTab);
                }});
            }});

            // 초기 플롯 생성
            create2DPlot();
            create3DPlot();
            create2DComparisonPlot();
            create3DComparisonPlot();
        }});

        function switchTab(tabId) {{
            // 모든 탭 버튼과 패널 비활성화
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));

            // 선택된 탭 활성화
            document.querySelector(`[data-tab="${{tabId}}"]`).classList.add('active');
            document.getElementById(tabId).classList.add('active');
        }}

        function create2DPlot() {{
            const traces = [];

            // Anchor 화합물
            const anchorIndices = compoundData.anchor_mask.map((isAnchor, idx) => isAnchor && !compoundData.outlier_mask[idx] ? idx : -1).filter(idx => idx >= 0);
            if (anchorIndices.length > 0) {{
                traces.push({{
                    x: anchorIndices.map(i => compoundData.log_p_values[i]),
                    y: anchorIndices.map(i => compoundData.retention_times[i]),
                    mode: 'markers',
                    type: 'scatter',
                    name: 'Anchor (T)',
                    marker: {{
                        color: '#3498db',
                        size: 12,
                        symbol: 'diamond',
                        line: {{ color: 'white', width: 2 }}
                    }},
                    text: anchorIndices.map(i => compoundData.names[i]),
                    hovertemplate: '<b>%{{text}}</b><br>Log P: %{{x}}<br>RT: %{{y}}<extra></extra>'
                }});
            }}

            // 유효 화합물
            const validIndices = compoundData.anchor_mask.map((isAnchor, idx) => !isAnchor && !compoundData.outlier_mask[idx] ? idx : -1).filter(idx => idx >= 0);
            if (validIndices.length > 0) {{
                traces.push({{
                    x: validIndices.map(i => compoundData.log_p_values[i]),
                    y: validIndices.map(i => compoundData.retention_times[i]),
                    mode: 'markers',
                    type: 'scatter',
                    name: 'Valid Compounds',
                    marker: {{
                        color: '#2ecc71',
                        size: 8,
                        line: {{ color: 'white', width: 1 }}
                    }},
                    text: validIndices.map(i => compoundData.names[i]),
                    hovertemplate: '<b>%{{text}}</b><br>Log P: %{{x}}<br>RT: %{{y}}<extra></extra>'
                }});
            }}

            // 이상치
            if (showOutliers2D) {{
                const outlierIndices = compoundData.outlier_mask.map((isOutlier, idx) => isOutlier ? idx : -1).filter(idx => idx >= 0);
                if (outlierIndices.length > 0) {{
                    traces.push({{
                        x: outlierIndices.map(i => compoundData.log_p_values[i]),
                        y: outlierIndices.map(i => compoundData.retention_times[i]),
                        mode: 'markers',
                        type: 'scatter',
                        name: 'Outliers',
                        marker: {{
                            color: '#e74c3c',
                            size: 10,
                            symbol: 'x',
                            line: {{ width: 2 }}
                        }},
                        text: outlierIndices.map(i => compoundData.names[i]),
                        hovertemplate: '<b>%{{text}}</b><br>Log P: %{{x}}<br>RT: %{{y}}<br><b>이상치</b><extra></extra>'
                    }});
                }}
            }}

            const layout = {{
                title: 'Retention Time vs Log P (2D)',
                xaxis: {{ title: 'Log P (Partition Coefficient)' }},
                yaxis: {{ title: 'Retention Time (min)' }},
                hovermode: 'closest',
                showlegend: true,
                legend: {{ x: 0.02, y: 0.98 }}
            }};

            Plotly.newPlot('plot-2d', traces, layout, {{ responsive: true }});
        }}

        function create3DPlot() {{
            const traces = [];

            // Anchor 화합물
            const anchorIndices = compoundData.anchor_mask.map((isAnchor, idx) => isAnchor && !compoundData.outlier_mask[idx] ? idx : -1).filter(idx => idx >= 0);
            if (anchorIndices.length > 0) {{
                traces.push({{
                    x: anchorIndices.map(i => compoundData.mass_to_charge[i]),
                    y: anchorIndices.map(i => compoundData.retention_times[i]),
                    z: anchorIndices.map(i => compoundData.log_p_values[i]),
                    mode: 'markers',
                    type: 'scatter3d',
                    name: 'Anchor (T)',
                    marker: {{
                        color: '#3498db',
                        size: 8,
                        symbol: 'diamond',
                        line: {{ color: 'white', width: 2 }}
                    }},
                    text: anchorIndices.map(i => compoundData.names[i]),
                    hovertemplate: '<b>%{{text}}</b><br>m/z: %{{x:.1f}}<br>RT: %{{y:.3f}}<br>Log P: %{{z:.2f}}<extra></extra>'
                }});
            }}

            // 유효 화합물
            const validIndices = compoundData.anchor_mask.map((isAnchor, idx) => !isAnchor && !compoundData.outlier_mask[idx] ? idx : -1).filter(idx => idx >= 0);
            if (validIndices.length > 0) {{
                traces.push({{
                    x: validIndices.map(i => compoundData.mass_to_charge[i]),
                    y: validIndices.map(i => compoundData.retention_times[i]),
                    z: validIndices.map(i => compoundData.log_p_values[i]),
                    mode: 'markers',
                    type: 'scatter3d',
                    name: 'Valid Compounds',
                    marker: {{
                        color: '#2ecc71',
                        size: 6,
                        line: {{ color: 'white', width: 1 }}
                    }},
                    text: validIndices.map(i => compoundData.names[i]),
                    hovertemplate: '<b>%{{text}}</b><br>m/z: %{{x:.1f}}<br>RT: %{{y:.3f}}<br>Log P: %{{z:.2f}}<extra></extra>'
                }});
            }}

            // 이상치
            if (showOutliers3D) {{
                const outlierIndices = compoundData.outlier_mask.map((isOutlier, idx) => isOutlier ? idx : -1).filter(idx => idx >= 0);
                if (outlierIndices.length > 0) {{
                    traces.push({{
                        x: outlierIndices.map(i => compoundData.mass_to_charge[i]),
                        y: outlierIndices.map(i => compoundData.retention_times[i]),
                        z: outlierIndices.map(i => compoundData.log_p_values[i]),
                        mode: 'markers',
                        type: 'scatter3d',
                        name: 'Outliers',
                        marker: {{
                            color: '#e74c3c',
                            size: 6,
                            symbol: 'x',
                            line: {{ width: 2 }}
                        }},
                        text: outlierIndices.map(i => compoundData.names[i]),
                        hovertemplate: '<b>%{{text}}</b><br>m/z: %{{x:.1f}}<br>RT: %{{y:.3f}}<br>Log P: %{{z:.2f}}<br><b>이상치</b><extra></extra>'
                    }});
                }}
            }}

            const layout = {{
                title: '3D Distribution: m/z vs RT vs Log P',
                scene: {{
                    xaxis: {{ title: 'Mass-to-Charge (m/z)' }},
                    yaxis: {{ title: 'Retention Time (min)' }},
                    zaxis: {{ title: 'Partition Coefficient (Log P)' }},
                    camera: {{
                        eye: {{ x: 1.2, y: 1.2, z: 1.2 }}
                    }}
                }},
                showlegend: true,
                legend: {{ x: 0.02, y: 0.98 }}
            }};

            Plotly.newPlot('plot-3d', traces, layout, {{ responsive: true }});
        }}

        function create2DComparisonPlot() {{
            // 간소화된 2D 플롯
            create2DPlot();
            // 플롯 복사
            setTimeout(() => {{
                const plot2d = document.getElementById('plot-2d');
                if (plot2d && plot2d.data) {{
                    Plotly.newPlot('plot-2d-comparison', plot2d.data, plot2d.layout, {{ responsive: true }});
                }}
            }}, 100);
        }}

        function create3DComparisonPlot() {{
            // 간소화된 3D 플롯
            create3DPlot();
            // 플롯 복사
            setTimeout(() => {{
                const plot3d = document.getElementById('plot-3d');
                if (plot3d && plot3d.data) {{
                    Plotly.newPlot('plot-3d-comparison', plot3d.data, plot3d.layout, {{ responsive: true }});
                }}
            }}, 100);
        }}

        // 컨트롤 함수들
        function reset2DView() {{
            Plotly.relayout('plot-2d', {{
                'xaxis.autorange': true,
                'yaxis.autorange': true
            }});
        }}

        function reset3DView() {{
            Plotly.relayout('plot-3d', {{
                'scene.camera': {{
                    eye: {{ x: 1.2, y: 1.2, z: 1.2 }}
                }}
            }});
        }}

        function toggle2DOutliers() {{
            showOutliers2D = !showOutliers2D;
            create2DPlot();
        }}

        function toggle3DOutliers() {{
            showOutliers3D = !showOutliers3D;
            create3DPlot();
        }}

        function show2DRegression() {{
            showRegression2D = !showRegression2D;
            // 회귀선 구현 (추후 추가 가능)
            create2DPlot();
        }}

        function toggle3DRegression() {{
            showRegression3D = !showRegression3D;
            // 회귀평면 구현 (추후 추가 가능)
            create3DPlot();
        }}

        // 창 크기 변경 시 플롯 리사이즈
        window.addEventListener('resize', function() {{
            ['plot-2d', 'plot-3d', 'plot-2d-comparison', 'plot-3d-comparison'].forEach(id => {{
                const element = document.getElementById(id);
                if (element && element.data) {{
                    Plotly.Plots.resize(element);
                }}
            }});
        }});
    </script>
</body>
</html>
        """

        return html_content

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
