"""
Django admin for Analysis models
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import AnalysisSession, AnalysisResult, Compound, RegressionModel


@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'colored_status', 'data_type', 'success_rate_display',
        'duration_display', 'created_at'
    ]
    list_filter = ['status', 'data_type', 'created_at']
    search_fields = ['name', 'user__username', 'original_filename']
    readonly_fields = [
        'created_at', 'updated_at', 'started_at', 'completed_at',
        'celery_task_id', 'file_size'
    ]

    fieldsets = (
        ('Session Info', {
            'fields': ('user', 'name', 'status', 'data_type')
        }),
        ('File Upload', {
            'fields': ('uploaded_file', 'original_filename', 'file_size')
        }),
        ('Analysis Parameters', {
            'fields': ('r2_threshold', 'outlier_threshold', 'rt_tolerance')
        }),
        ('Processing', {
            'fields': ('started_at', 'completed_at', 'error_message', 'celery_task_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def colored_status(self, obj):
        colors = {
            'pending': 'gray',
            'uploading': 'blue',
            'processing': 'orange',
            'completed': 'green',
            'failed': 'red',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'

    def success_rate_display(self, obj):
        if hasattr(obj, 'result'):
            return f"{obj.result.success_rate:.1f}%"
        return "N/A"
    success_rate_display.short_description = 'Success Rate'

    def duration_display(self, obj):
        if obj.duration:
            return f"{obj.duration:.2f}s"
        return "N/A"
    duration_display.short_description = 'Duration'


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'session', 'total_compounds', 'valid_compounds',
        'outlier_count', 'success_rate_percent', 'created_at'
    ]
    list_filter = ['created_at']
    search_fields = ['session__name', 'session__user__username']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Session', {
            'fields': ('session',)
        }),
        ('Statistics', {
            'fields': (
                'total_compounds', 'anchor_compounds', 'valid_compounds',
                'outlier_count', 'success_rate'
            )
        }),
        ('Rule Breakdown', {
            'fields': (
                'rule1_valid', 'rule1_outliers',
                'rule4_valid', 'rule4_invalid',
                'rule5_fragments'
            )
        }),
        ('Detailed Results', {
            'fields': (
                'regression_analysis', 'regression_quality',
                'sugar_analysis', 'oacetylation_analysis',
                'rt_filtering_summary', 'categorization'
            ),
            'classes': ('collapse',)
        }),
    )

    def success_rate_percent(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate_percent.short_description = 'Success Rate'


@admin.register(Compound)
class CompoundAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'session', 'colored_status', 'category', 'rt',
        'log_p', 'is_anchor', 'sugar_count'
    ]
    list_filter = ['status', 'category', 'is_anchor', 'session__data_type']
    search_fields = ['name', 'prefix', 'session__name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('session', 'name', 'status', 'category')
        }),
        ('Original Data', {
            'fields': ('rt', 'volume', 'log_p', 'is_anchor')
        }),
        ('Structural Features', {
            'fields': (
                'prefix', 'suffix',
                'a_component', 'b_component', 'c_component'
            )
        }),
        ('Sugar Analysis', {
            'fields': (
                'sugar_count', 'sialic_acid_count',
                'can_have_isomers', 'isomer_type'
            )
        }),
        ('Modifications', {
            'fields': ('has_oacetylation', 'has_dhex', 'has_hexnac')
        }),
        ('Regression Results', {
            'fields': (
                'regression_group', 'predicted_rt',
                'residual', 'standardized_residual'
            )
        }),
        ('Outlier/Fragment Info', {
            'fields': (
                'outlier_reason', 'reference_compound',
                'merged_compounds', 'fragmentation_sources'
            ),
            'classes': ('collapse',)
        }),
    )

    def colored_status(self, obj):
        colors = {
            'valid': 'green',
            'outlier': 'red',
            'fragment': 'orange',
        }
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'


@admin.register(RegressionModel)
class RegressionModelAdmin(admin.ModelAdmin):
    list_display = [
        'prefix_group', 'session', 'model_type', 'r2_display',
        'n_samples', 'n_anchors', 'created_at'
    ]
    list_filter = ['model_type', 'created_at']
    search_fields = ['prefix_group', 'session__name']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Model Info', {
            'fields': ('session', 'prefix_group', 'model_type')
        }),
        ('Parameters', {
            'fields': (
                'intercept', 'coefficients', 'feature_names',
                'regularization_alpha', 'equation'
            )
        }),
        ('Quality Metrics', {
            'fields': ('r2', 'adjusted_r2', 'rmse', 'durbin_watson')
        }),
        ('Sample Info', {
            'fields': ('n_samples', 'n_anchors')
        }),
    )

    def r2_display(self, obj):
        color = 'green' if obj.r2 >= 0.80 else 'orange' if obj.r2 >= 0.70 else 'red'
        return format_html(
            '<span style="color: {};">{:.4f}</span>',
            color,
            obj.r2
        )
    r2_display.short_description = 'R²'
