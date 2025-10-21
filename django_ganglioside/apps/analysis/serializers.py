"""
Django REST Framework serializers for analysis app
"""
from rest_framework import serializers
from .models import AnalysisSession, Compound, AnalysisResult, RegressionModel


class RegressionModelSerializer(serializers.ModelSerializer):
    """Serializer for RegressionModel"""

    class Meta:
        model = RegressionModel
        fields = [
            'id', 'prefix_group', 'model_type', 'intercept', 'coefficients',
            'feature_names', 'regularization_alpha', 'r2', 'adjusted_r2',
            'rmse', 'durbin_watson', 'n_samples', 'n_anchors', 'equation',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CompoundSerializer(serializers.ModelSerializer):
    """Serializer for Compound - detailed view"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Compound
        fields = [
            'id', 'name', 'rt', 'volume', 'log_p', 'is_anchor',
            'prefix', 'suffix', 'a_component', 'b_component', 'c_component',
            'sugar_count', 'sialic_acid_count', 'can_have_isomers', 'isomer_type',
            'has_oacetylation', 'has_dhex', 'has_hexnac',
            'status', 'status_display', 'category', 'category_display',
            'regression_group', 'predicted_rt', 'residual', 'standardized_residual',
            'outlier_reason', 'reference_compound', 'merged_compounds',
            'fragmentation_sources', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CompoundListSerializer(serializers.ModelSerializer):
    """Serializer for Compound - list view (minimal fields)"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Compound
        fields = [
            'id', 'name', 'rt', 'volume', 'status', 'status_display',
            'category', 'category_display', 'predicted_rt', 'residual'
        ]


class AnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisResult"""

    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'total_compounds', 'anchor_compounds', 'valid_compounds',
            'outlier_count', 'success_rate', 'regression_analysis',
            'regression_quality', 'sugar_analysis', 'oacetylation_analysis',
            'rt_filtering_summary', 'categorization', 'rule1_valid',
            'rule1_outliers', 'rule4_valid', 'rule4_invalid', 'rule5_fragments',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AnalysisSessionSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisSession - detailed view with results"""

    result = AnalysisResultSerializer(read_only=True)
    compounds = CompoundListSerializer(many=True, read_only=True)
    regression_models = RegressionModelSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    duration_seconds = serializers.FloatField(source='duration', read_only=True)

    class Meta:
        model = AnalysisSession
        fields = [
            'id', 'user', 'name', 'status', 'status_display',
            'data_type', 'data_type_display', 'uploaded_file', 'original_filename',
            'file_size', 'r2_threshold', 'outlier_threshold', 'rt_tolerance',
            'started_at', 'completed_at', 'duration_seconds', 'error_message',
            'celery_task_id', 'created_at', 'updated_at',
            'result', 'compounds', 'regression_models'
        ]
        read_only_fields = [
            'id', 'user', 'status', 'started_at', 'completed_at',
            'error_message', 'celery_task_id', 'created_at', 'updated_at'
        ]


class AnalysisSessionListSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisSession - list view (minimal fields)"""

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    duration_seconds = serializers.FloatField(source='duration', read_only=True)

    # Include basic statistics from result
    total_compounds = serializers.IntegerField(source='result.total_compounds', read_only=True)
    success_rate = serializers.FloatField(source='result.success_rate', read_only=True)

    class Meta:
        model = AnalysisSession
        fields = [
            'id', 'name', 'status', 'status_display', 'data_type', 'data_type_display',
            'original_filename', 'file_size', 'created_at', 'completed_at',
            'duration_seconds', 'total_compounds', 'success_rate'
        ]


class AnalysisSessionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new AnalysisSession"""

    uploaded_file = serializers.FileField()

    class Meta:
        model = AnalysisSession
        fields = [
            'name', 'data_type', 'uploaded_file', 'r2_threshold',
            'outlier_threshold', 'rt_tolerance'
        ]

    def validate_uploaded_file(self, value):
        """Validate uploaded file is a CSV"""
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are allowed.")

        # Check file size (max 50MB)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 50MB.")

        return value

    def create(self, validated_data):
        """Create analysis session with file metadata"""
        uploaded_file = validated_data.get('uploaded_file')
        validated_data['original_filename'] = uploaded_file.name
        validated_data['file_size'] = uploaded_file.size
        validated_data['user'] = self.context['request'].user

        return super().create(validated_data)
