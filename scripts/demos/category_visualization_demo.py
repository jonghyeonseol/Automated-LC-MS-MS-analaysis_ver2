#!/usr/bin/env python3
"""
Demo script showing category-based visualization

NOTE: This demo script is Flask-specific and should be migrated to Django.
The Flask infrastructure has been removed. See django_ganglioside/apps/visualization for Django visualization.
"""

import sys
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Add Django project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../django_ganglioside'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Import from new Django structure
from apps.analysis.services.ganglioside_categorizer import GangliosideCategorizer


def create_category_scatter_plot(df, categorizer):
    """Create a scatter plot colored by ganglioside categories"""

    # Get categorization
    categorization = categorizer.categorize_compounds(df)
    colors = categorizer.get_category_colors()

    # Add category information to dataframe
    df_viz = df.copy()
    df_viz['Category'] = df_viz['Name'].apply(
        lambda x: categorization['compound_mapping'][x]['category']
    )
    df_viz['Base_Prefix'] = df_viz['Name'].apply(
        lambda x: categorization['compound_mapping'][x]['base_prefix']
    )
    df_viz['Modifications'] = df_viz['Name'].apply(
        lambda x: ', '.join(categorization['compound_mapping'][x]['modifications']) or 'None'
    )

    # Create scatter plot
    fig = go.Figure()

    for category, info in categorization['categories'].items():
        category_data = df_viz[df_viz['Category'] == category]

        fig.add_trace(go.Scatter(
            x=category_data['Log P'],
            y=category_data['RT'],
            mode='markers',
            name=f"{category} ({info['count']} compounds)",
            marker=dict(
                color=colors.get(category, '#888888'),
                size=8,
                opacity=0.7,
                line=dict(width=1, color='white')
            ),
            text=category_data['Name'],
            hovertemplate=(
                '<b>%{text}</b><br>' +
                'Log P: %{x:.2f}<br>' +
                'RT: %{y:.2f}<br>' +
                'Category: ' + category + '<br>' +
                '<extra></extra>'
            )
        ))

    fig.update_layout(
        title={
            'text': '🧬 Ganglioside Classification by Category<br>' +
                    '<sub>LC-MS-MS Data Analysis with Automated Categorization</sub>',
            'x': 0.5,
            'font': {'size': 16}
        },
        xaxis_title='Log P (Lipophilicity)',
        yaxis_title='Retention Time (min)',
        width=900,
        height=600,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01
        ),
        margin=dict(r=200)
    )

    return fig


def create_category_distribution_charts(df, categorizer):
    """Create distribution charts for categories"""

    categorization = categorizer.categorize_compounds(df)
    colors = categorizer.get_category_colors()

    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            '📊 Category Distribution',
            '🏷️ Base Prefix Distribution',
            '⚗️ Modification Types',
            '📈 Category vs Success Rate'
        ),
        specs=[[{"type": "pie"}, {"type": "bar"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )

    # 1. Category pie chart
    categories = list(categorization['categories'].keys())
    counts = [categorization['categories'][cat]['count'] for cat in categories]
    category_colors = [colors.get(cat, '#888888') for cat in categories]

    fig.add_trace(
        go.Pie(
            labels=[f"{cat}\n({count} compounds)" for cat, count in zip(categories, counts)],
            values=counts,
            marker_colors=category_colors,
            textinfo='label+percent',
            textposition='inside'
        ),
        row=1, col=1
    )

    # 2. Base prefix bar chart
    base_prefixes = list(categorization['base_prefixes'].keys())
    base_counts = list(categorization['base_prefixes'].values())

    fig.add_trace(
        go.Bar(
            x=base_prefixes,
            y=base_counts,
            marker_color='lightblue',
            name='Base Prefixes'
        ),
        row=1, col=2
    )

    # 3. Modifications bar chart
    modifications = list(categorization['modifications'].keys())
    mod_counts = list(categorization['modifications'].values())

    fig.add_trace(
        go.Bar(
            x=modifications,
            y=mod_counts,
            marker_color='lightgreen',
            name='Modifications'
        ),
        row=2, col=1
    )

    # 4. Category compound counts
    fig.add_trace(
        go.Bar(
            x=categories,
            y=counts,
            marker_color=category_colors,
            name='Category Counts'
        ),
        row=2, col=2
    )

    fig.update_layout(
        title={
            'text': '📊 Ganglioside Categorization Analysis Dashboard',
            'x': 0.5,
            'font': {'size': 16}
        },
        height=800,
        width=1200,
        showlegend=False
    )

    return fig


def create_category_3d_plot(df, categorizer):
    """Create 3D plot showing RT vs Log P vs Volume by category"""

    # Get categorization
    categorization = categorizer.categorize_compounds(df)
    colors = categorizer.get_category_colors()

    # Add category information
    df_viz = df.copy()
    df_viz['Category'] = df_viz['Name'].apply(
        lambda x: categorization['compound_mapping'][x]['category']
    )

    fig = go.Figure()

    for category, info in categorization['categories'].items():
        category_data = df_viz[df_viz['Category'] == category]

        fig.add_trace(go.Scatter3d(
            x=category_data['Log P'],
            y=category_data['RT'],
            z=category_data['Volume'],
            mode='markers',
            name=f"{category} ({info['count']})",
            marker=dict(
                color=colors.get(category, '#888888'),
                size=5,
                opacity=0.8
            ),
            text=category_data['Name'],
            hovertemplate=(
                '<b>%{text}</b><br>' +
                'Log P: %{x:.2f}<br>' +
                'RT: %{y:.2f}<br>' +
                'Volume: %{z:,.0f}<br>' +
                'Category: ' + category + '<br>' +
                '<extra></extra>'
            )
        ))

    fig.update_layout(
        title={
            'text': '🎯 3D Ganglioside Distribution by Category<br><sub>RT vs Log P vs Volume</sub>',
            'x': 0.5,
            'font': {'size': 16}
        },
        scene=dict(
            xaxis_title='Log P (Lipophilicity)',
            yaxis_title='Retention Time (min)',
            zaxis_title='Volume (Intensity)'
        ),
        width=900,
        height=700
    )

    return fig


def main():
    print("🎨 GANGLIOSIDE CATEGORIZATION VISUALIZATION DEMO")
    print("=" * 60)

    # Load data
    df = pd.read_csv('data/samples/testwork_user.csv')
    print(f"📁 Loaded {len(df)} compounds")

    # Initialize categorizer
    categorizer = GangliosideCategorizer()

    # Generate categorization summary
    summary = categorizer.generate_categorization_summary(df)
    print(summary)

    # Create visualizations
    print("\n🎨 Creating category-based visualizations...")

    # 1. Category scatter plot
    scatter_fig = create_category_scatter_plot(df, categorizer)
    scatter_fig.write_html('category_scatter_plot.html')
    print("✅ Category scatter plot saved to: category_scatter_plot.html")

    # 2. Distribution dashboard
    dashboard_fig = create_category_distribution_charts(df, categorizer)
    dashboard_fig.write_html('category_dashboard.html')
    print("✅ Category dashboard saved to: category_dashboard.html")

    # 3. 3D category plot
    plot_3d_fig = create_category_3d_plot(df, categorizer)
    plot_3d_fig.write_html('category_3d_plot.html')
    print("✅ Category 3D plot saved to: category_3d_plot.html")

    print("\n🎉 VISUALIZATION DEMO COMPLETE!")
    print("📊 Created 3 category-based visualizations:")
    print("   1. Category scatter plot (RT vs Log P)")
    print("   2. Category analysis dashboard")
    print("   3. 3D category distribution plot")
    print("\n🌐 Open the HTML files in your browser to view the interactive plots!")


if __name__ == "__main__":
    main()
