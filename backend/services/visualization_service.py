"""
Visualization Service - 시각화 생성 서비스
Plotly 기반 인터랙티브 차트 및 분석 결과 시각화
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import json


class VisualizationService:
    def __init__(self):
        self.color_palette = {
            'valid': '#2ecc71',      # Green
            'outlier': '#e74c3c',    # Red
            'anchor': '#3498db',     # Blue
            'regression': '#9b59b6', # Purple
            'background': '#ecf0f1', # Light gray
            'grid': '#bdc3c7'        # Gray
        }
        
        print("📊 Visualization Service 초기화 완료")
    
    def create_all_plots(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """모든 시각화 생성"""
        try:
            plots = {}
            
            # 1. 메인 대시보드
            plots['dashboard'] = self._create_dashboard(results)
            
            # 2. 회귀분석 산점도
            plots['regression_scatter'] = self._create_regression_scatter(results)
            
            # 3. 잔차 분석 플롯
            plots['residual_analysis'] = self._create_residual_analysis(results)
            
            # 4. 이상치 분포 히스토그램
            plots['outlier_histogram'] = self._create_outlier_histogram(results)
            
            # 5. 접두사별 성공률 바차트
            plots['prefix_success_rate'] = self._create_prefix_success_rate(results)
            
            # 6. RT-Log P 상관관계 히트맵
            plots['correlation_heatmap'] = self._create_correlation_heatmap(results)
            
            # 7. 규칙별 분류 결과 파이차트
            plots['rule_breakdown_pie'] = self._create_rule_breakdown_pie(results)
            
            # 8. 시계열 분석 (RT 분포)
            plots['rt_distribution'] = self._create_rt_distribution(results)
            
            return {
                'status': 'success',
                'message': '시각화 생성 완료',
                'plots': plots,
                'plot_count': len(plots)
            }
            
        except Exception as e:
            print(f"Visualization error: {str(e)}")
            return {
                'status': 'error',
                'message': f'시각화 생성 중 오류: {str(e)}',
                'plots': {}
            }
    
    def _create_dashboard(self, results: Dict[str, Any]) -> str:
        """메인 대시보드 생성"""
        stats = results['statistics']
        
        # 서브플롯 생성 (2x2 그리드)
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['전체 통계', '규칙별 분석', '회귀분석 품질', 'RT 분포'],
            specs=[[{"type": "indicator"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "histogram"}]]
        )
        
        # 1. 성공률 게이지
        fig.add_trace(
            go.Indicator(
                mode="gauge+number+delta",
                value=stats['success_rate'],
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "성공률 (%)"},
                delta={'reference': 80},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': self.color_palette['valid']},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ),
            row=1, col=1
        )
        
        # 2. 규칙별 분석 바차트
        rule_names = ['Rule 1', 'Rule 4', 'Rule 5']
        rule_values = [
            stats['rule_breakdown']['rule1_regression'],
            stats['rule_breakdown']['rule4_oacetylation'],
            stats['rule_breakdown']['rule5_rt_filtering']
        ]
        
        fig.add_trace(
            go.Bar(
                x=rule_names,
                y=rule_values,
                marker_color=[self.color_palette['valid'], self.color_palette['anchor'], self.color_palette['regression']],
                name="유효 화합물"
            ),
            row=1, col=2
        )
        
        # 3. 회귀분석 R² 산점도
        if results.get('regression_quality'):
            prefixes = list(results['regression_quality'].keys())
            r2_values = [results['regression_quality'][p]['r2'] for p in prefixes]
            
            fig.add_trace(
                go.Scatter(
                    x=prefixes,
                    y=r2_values,
                    mode='markers+lines',
                    marker=dict(
                        size=10,
                        color=r2_values,
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title="R²")
                    ),
                    name="회귀 품질"
                ),
                row=2, col=1
            )
        
        # 4. RT 분포 히스토그램
        all_compounds = results.get('valid_compounds', []) + results.get('outliers', [])
        rt_values = [c['RT'] for c in all_compounds if 'RT' in c]
        
        if rt_values:
            fig.add_trace(
                go.Histogram(
                    x=rt_values,
                    nbinsx=20,
                    marker_color=self.color_palette['background'],
                    name="RT 분포"
                ),
                row=2, col=2
            )
        
        # 레이아웃 설정
        fig.update_layout(
            title_text="🧬 Ganglioside Analysis Dashboard",
            showlegend=False,
            height=800,
            font=dict(size=12)
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="dashboard")
    
    def _create_regression_scatter(self, results: Dict[str, Any]) -> str:
        """회귀분석 산점도 생성"""
        fig = go.Figure()
        
        # 유효 화합물과 이상치 분리
        valid_compounds = results.get('valid_compounds', [])
        outliers = results.get('outliers', [])
        
        # 유효 화합물 플롯
        if valid_compounds:
            valid_df = pd.DataFrame(valid_compounds)
            
            # Anchor 구분
            anchor_mask = valid_df['Anchor'] == 'T'
            
            # Anchor 화합물
            fig.add_trace(go.Scatter(
                x=valid_df[anchor_mask]['Log P'],
                y=valid_df[anchor_mask]['RT'],
                mode='markers',
                marker=dict(
                    size=12,
                    color=self.color_palette['anchor'],
                    symbol='diamond',
                    line=dict(width=2, color='white')
                ),
                name='Anchor (T)',
                text=valid_df[anchor_mask]['Name'],
                hovertemplate='<b>%{text}</b><br>Log P: %{x}<br>RT: %{y}<extra></extra>'
            ))
            
            # 일반 유효 화합물
            fig.add_trace(go.Scatter(
                x=valid_df[~anchor_mask]['Log P'],
                y=valid_df[~anchor_mask]['RT'],
                mode='markers',
                marker=dict(
                    size=10,
                    color=self.color_palette['valid'],
                    line=dict(width=1, color='white')
                ),
                name='Valid',
                text=valid_df[~anchor_mask]['Name'],
                hovertemplate='<b>%{text}</b><br>Log P: %{x}<br>RT: %{y}<extra></extra>'
            ))
        
        # 이상치 플롯
        if outliers:
            outlier_df = pd.DataFrame(outliers)
            fig.add_trace(go.Scatter(
                x=outlier_df['Log P'],
                y=outlier_df['RT'],
                mode='markers',
                marker=dict(
                    size=10,
                    color=self.color_palette['outlier'],
                    symbol='x',
                    line=dict(width=2)
                ),
                name='Outliers',
                text=outlier_df['Name'],
                hovertemplate='<b>%{text}</b><br>Log P: %{x}<br>RT: %{y}<br>Reason: %{customdata}<extra></extra>',
                customdata=outlier_df.get('outlier_reason', ['Unknown'] * len(outlier_df))
            ))
        
        # 회귀선 추가
        regression_analysis = results.get('regression_analysis', {})
        for prefix, reg_data in regression_analysis.items():
            slope = reg_data['slope']
            intercept = reg_data['intercept']
            r2 = reg_data['r2']
            
            # Log P 범위 계산
            all_log_p = []
            if valid_compounds:
                all_log_p.extend([c['Log P'] for c in valid_compounds])
            if outliers:
                all_log_p.extend([c['Log P'] for c in outliers])
            
            if all_log_p:
                x_range = np.linspace(min(all_log_p), max(all_log_p), 100)
                y_pred = slope * x_range + intercept
                
                fig.add_trace(go.Scatter(
                    x=x_range,
                    y=y_pred,
                    mode='lines',
                    line=dict(dash='dash', width=2),
                    name=f'{prefix} (R²={r2:.3f})',
                    showlegend=True
                ))
        
        fig.update_layout(
            title='Log P vs Retention Time Regression Analysis',
            xaxis_title='Log P (Partition Coefficient)',
            yaxis_title='Retention Time (min)',
            hovermode='closest',
            height=600,
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="regression_scatter")
    
    def _create_residual_analysis(self, results: Dict[str, Any]) -> str:
        """잔차 분석 플롯 생성"""
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['잔차 vs 예측값', '표준화 잔차', 'Q-Q Plot', '잔차 히스토그램'],
            specs=[[{"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "scatter"}, {"type": "histogram"}]]
        )
        
        # 잔차 데이터 수집
        valid_compounds = results.get('valid_compounds', [])
        if valid_compounds:
            residuals = [c.get('residual', 0) for c in valid_compounds if 'residual' in c]
            std_residuals = [c.get('std_residual', 0) for c in valid_compounds if 'std_residual' in c]
            predicted_rt = [c.get('predicted_rt', c.get('RT', 0)) for c in valid_compounds]
            
            # 1. 잔차 vs 예측값
            fig.add_trace(
                go.Scatter(
                    x=predicted_rt,
                    y=residuals,
                    mode='markers',
                    marker=dict(color=self.color_palette['valid']),
                    name='Residuals'
                ),
                row=1, col=1
            )
            
            # 2. 표준화 잔차
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(std_residuals))),
                    y=std_residuals,
                    mode='markers',
                    marker=dict(color=self.color_palette['anchor']),
                    name='Std Residuals'
                ),
                row=1, col=2
            )
            
            # 임계값 라인 추가 (±3)
            fig.add_hline(y=3, line_dash="dash", line_color="red", row=1, col=2)
            fig.add_hline(y=-3, line_dash="dash", line_color="red", row=1, col=2)
            
            # 3. Q-Q Plot (정규성 검정)
            if len(residuals) > 3:
                from scipy import stats as scipy_stats
                (osm, osr), (slope, intercept, r) = scipy_stats.probplot(residuals, dist="norm")
                
                fig.add_trace(
                    go.Scatter(
                        x=osm,
                        y=osr,
                        mode='markers',
                        marker=dict(color=self.color_palette['regression']),
                        name='Q-Q Plot'
                    ),
                    row=2, col=1
                )
                
                # 이론적 라인 추가
                fig.add_trace(
                    go.Scatter(
                        x=osm,
                        y=slope * osm + intercept,
                        mode='lines',
                        line=dict(color='red', dash='dash'),
                        name='Theoretical Line'
                    ),
                    row=2, col=1
                )
            
            # 4. 잔차 히스토그램
            fig.add_trace(
                go.Histogram(
                    x=residuals,
                    nbinsx=15,
                    marker_color=self.color_palette['background'],
                    name='Residual Distribution'
                ),
                row=2, col=2
            )
        
        fig.update_layout(
            title_text="Residual Analysis",
            showlegend=False,
            height=800
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="residual_analysis")
    
    def _create_outlier_histogram(self, results: Dict[str, Any]) -> str:
        """이상치 분포 히스토그램 생성"""
        fig = go.Figure()
        
        outliers = results.get('outliers', [])
        if outliers:
            # 이상치 사유별 분류
            outlier_reasons = {}
            for outlier in outliers:
                reason = outlier.get('outlier_reason', 'Unknown')
                # 규칙별로 분류
                if 'Rule 1' in reason:
                    category = 'Rule 1: 회귀분석'
                elif 'Rule 4' in reason:
                    category = 'Rule 4: O-acetylation'
                elif 'Rule 5' in reason:
                    category = 'Rule 5: RT 필터링'
                else:
                    category = 'Other'
                
                if category not in outlier_reasons:
                    outlier_reasons[category] = 0
                outlier_reasons[category] += 1
            
            # 바차트 생성
            categories = list(outlier_reasons.keys())
            counts = list(outlier_reasons.values())
            colors = [self.color_palette['outlier']] * len(categories)
            
            fig.add_trace(go.Bar(
                x=categories,
                y=counts,
                marker_color=colors,
                text=counts,
                textposition='auto',
                name='Outlier Count'
            ))
        
        fig.update_layout(
            title='Outlier Distribution by Rules',
            xaxis_title='Outlier Category',
            yaxis_title='Count',
            height=400,
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="outlier_histogram")
    
    def _create_prefix_success_rate(self, results: Dict[str, Any]) -> str:
        """접두사별 성공률 바차트 생성"""
        fig = go.Figure()
        
        # 접두사별 통계 계산
        prefix_stats = {}
        all_compounds = results.get('valid_compounds', []) + results.get('outliers', [])
        
        for compound in all_compounds:
            name = compound.get('Name', '')
            if '(' in name:
                prefix = name.split('(')[0]
                if prefix not in prefix_stats:
                    prefix_stats[prefix] = {'total': 0, 'valid': 0}
                prefix_stats[prefix]['total'] += 1
                
                # 유효 화합물인지 확인
                if compound in results.get('valid_compounds', []):
                    prefix_stats[prefix]['valid'] += 1
        
        # 성공률 계산
        prefixes = []
        success_rates = []
        total_counts = []
        
        for prefix, stats in prefix_stats.items():
            if stats['total'] > 0:
                prefixes.append(prefix)
                success_rate = (stats['valid'] / stats['total']) * 100
                success_rates.append(success_rate)
                total_counts.append(stats['total'])
        
        # 색상 매핑 (성공률에 따라)
        colors = []
        for rate in success_rates:
            if rate >= 90:
                colors.append(self.color_palette['valid'])
            elif rate >= 70:
                colors.append(self.color_palette['anchor'])
            else:
                colors.append(self.color_palette['outlier'])
        
        fig.add_trace(go.Bar(
            x=prefixes,
            y=success_rates,
            marker_color=colors,
            text=[f'{rate:.1f}%<br>({count})' for rate, count in zip(success_rates, total_counts)],
            textposition='auto',
            name='Success Rate'
        ))
        
        fig.update_layout(
            title='Success Rate by Ganglioside Prefix',
            xaxis_title='Ganglioside Prefix',
            yaxis_title='Success Rate (%)',
            height=500,
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="prefix_success_rate")
    
    def _create_correlation_heatmap(self, results: Dict[str, Any]) -> str:
        """RT-Log P 상관관계 히트맵 생성"""
        fig = go.Figure()
        
        all_compounds = results.get('valid_compounds', []) + results.get('outliers', [])
        if all_compounds:
            # 접두사별 그룹화
            prefix_data = {}
            for compound in all_compounds:
                name = compound.get('Name', '')
                if '(' in name:
                    prefix = name.split('(')[0]
                    if prefix not in prefix_data:
                        prefix_data[prefix] = {'rt': [], 'log_p': []}
                    prefix_data[prefix]['rt'].append(compound.get('RT', 0))
                    prefix_data[prefix]['log_p'].append(compound.get('Log P', 0))
            
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
                        if len(data1['rt']) > 1 and len(data2['rt']) > 1:
                            corr = np.corrcoef(data1['rt'], data1['log_p'])[0, 1]
                            if np.isnan(corr):
                                corr = 0
                            correlation_matrix[i][j] = abs(corr)
                        else:
                            correlation_matrix[i][j] = 0
            
            fig.add_trace(go.Heatmap(
                z=correlation_matrix,
                x=prefixes,
                y=prefixes,
                colorscale='RdYlBu_r',
                text=correlation_matrix,
                texttemplate='%{text:.2f}',
                textfont={"size": 10},
                colorbar=dict(title="Correlation")
            ))
        
        fig.update_layout(
            title='RT-Log P Correlation Heatmap by Prefix',
            height=600,
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="correlation_heatmap")
    
    def _create_rule_breakdown_pie(self, results: Dict[str, Any]) -> str:
        """규칙별 분류 결과 파이차트 생성"""
        fig = go.Figure()
        
        stats = results['statistics']
        rule_breakdown = stats['rule_breakdown']
        
        # 데이터 준비
        labels = ['Rule 1 Valid', 'Rule 4 Valid', 'Rule 5 Valid', 
                 'Rule 1 Outliers', 'Rule 4 Outliers', 'Rule 5 Outliers']
        values = [
            rule_breakdown['rule1_regression'],
            rule_breakdown['rule4_oacetylation'], 
            rule_breakdown['rule5_rt_filtering'],
            rule_breakdown['rule1_outliers'],
            rule_breakdown['rule4_outliers'],
            rule_breakdown['rule5_outliers']
        ]
        
        colors = [
            self.color_palette['valid'], self.color_palette['anchor'], self.color_palette['regression'],
            self.color_palette['outlier'], '#ff7675', '#fd79a8'
        ]
        
        fig.add_trace(go.Pie(
            labels=labels,
            values=values,
            marker_colors=colors,
            textinfo='label+percent+value',
            textposition='auto'
        ))
        
        fig.update_layout(
            title='Rule-based Classification Results',
            height=500
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="rule_breakdown_pie")
    
    def _create_rt_distribution(self, results: Dict[str, Any]) -> str:
        """RT 분포 분석 생성"""
        fig = go.Figure()
        
        # 유효 화합물과 이상치 RT 분포
        valid_compounds = results.get('valid_compounds', [])
        outliers = results.get('outliers', [])
        
        if valid_compounds:
            valid_rt = [c['RT'] for c in valid_compounds]
            fig.add_trace(go.Histogram(
                x=valid_rt,
                name='Valid Compounds',
                opacity=0.7,
                marker_color=self.color_palette['valid'],
                nbinsx=20
            ))
        
        if outliers:
            outlier_rt = [c['RT'] for c in outliers]
            fig.add_trace(go.Histogram(
                x=outlier_rt,
                name='Outliers',
                opacity=0.7,
                marker_color=self.color_palette['outlier'],
                nbinsx=20
            ))
        
        fig.update_layout(
            title='Retention Time Distribution',
            xaxis_title='Retention Time (min)',
            yaxis_title='Count',
            barmode='overlay',
            height=400,
            template='plotly_white'
        )
        
        return fig.to_html(include_plotlyjs='cdn', div_id="rt_distribution")