"""
Analysis models - Core data models for ganglioside analysis
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import TimeStampedModel, SoftDeleteModel

User = get_user_model()


class AnalysisSession(TimeStampedModel, SoftDeleteModel):
    """
    Analysis session - represents a complete analysis run
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('uploading', 'Uploading'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    DATA_TYPE_CHOICES = [
        ('porcine', 'Porcine'),
        ('human', 'Human'),
        ('bovine', 'Bovine'),
        ('mouse', 'Mouse'),
        ('other', 'Other'),
    ]

    # User
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='analysis_sessions'
    )

    # Session info
    name = models.CharField(max_length=255, blank=True, help_text="Optional session name")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    data_type = models.CharField(max_length=50, choices=DATA_TYPE_CHOICES, default='porcine')

    # File upload
    uploaded_file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="File size in bytes")

    # Analysis parameters
    r2_threshold = models.FloatField(
        default=0.75,
        validators=[MinValueValidator(0.5), MaxValueValidator(0.999)],
        help_text="Minimum R² for regression validity"
    )
    outlier_threshold = models.FloatField(
        default=2.5,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        help_text="Standardized residual threshold (sigma)"
    )
    rt_tolerance = models.FloatField(
        default=0.1,
        validators=[MinValueValidator(0.01), MaxValueValidator(0.5)],
        help_text="RT tolerance for fragmentation detection (minutes)"
    )

    # Processing info
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    # Task tracking
    celery_task_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['celery_task_id']),
        ]

    def __str__(self):
        return f"{self.name or f'Session {self.id}'} - {self.get_status_display()}"

    @property
    def duration(self):
        """Calculate analysis duration"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class AnalysisResult(TimeStampedModel):
    """
    Analysis results - stores aggregated analysis output
    """
    session = models.OneToOneField(
        AnalysisSession,
        on_delete=models.CASCADE,
        related_name='result'
    )

    # Statistics
    total_compounds = models.IntegerField(default=0)
    anchor_compounds = models.IntegerField(default=0)
    valid_compounds = models.IntegerField(default=0)
    outlier_count = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0.0)

    # Detailed results (JSON fields)
    regression_analysis = models.JSONField(
        default=dict,
        help_text="Regression models per prefix group"
    )
    regression_quality = models.JSONField(
        default=dict,
        help_text="Quality metrics for each regression"
    )
    sugar_analysis = models.JSONField(
        default=dict,
        help_text="Sugar count and isomer analysis"
    )
    oacetylation_analysis = models.JSONField(
        default=dict,
        help_text="O-acetylation validation results"
    )
    rt_filtering_summary = models.JSONField(
        default=dict,
        help_text="Fragmentation detection summary"
    )
    categorization = models.JSONField(
        default=dict,
        help_text="GM/GD/GT/GQ/GP categorization data"
    )

    # Rule breakdown
    rule1_valid = models.IntegerField(default=0, help_text="Valid after Rule 1")
    rule1_outliers = models.IntegerField(default=0, help_text="Outliers from Rule 1")
    rule4_valid = models.IntegerField(default=0, help_text="Valid OAc compounds")
    rule4_invalid = models.IntegerField(default=0, help_text="Invalid OAc compounds")
    rule5_fragments = models.IntegerField(default=0, help_text="Fragments detected")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Results for {self.session}"


class Compound(TimeStampedModel):
    """
    Individual compound data and classification
    """
    STATUS_CHOICES = [
        ('valid', 'Valid'),
        ('outlier', 'Outlier'),
        ('fragment', 'Fragment'),
    ]

    CATEGORY_CHOICES = [
        ('GM', 'Monosialoganglioside'),
        ('GD', 'Disialoganglioside'),
        ('GT', 'Trisialoganglioside'),
        ('GQ', 'Tetrasialoganglioside'),
        ('GP', 'Pentasialoganglioside'),
        ('UNKNOWN', 'Unknown'),
    ]

    # Relation
    session = models.ForeignKey(
        AnalysisSession,
        on_delete=models.CASCADE,
        related_name='compounds'
    )

    # Original data
    name = models.CharField(max_length=255, db_index=True)
    rt = models.FloatField(help_text="Retention time (minutes)")
    volume = models.FloatField(help_text="Peak volume/area")
    log_p = models.FloatField(help_text="Lipophilicity")
    is_anchor = models.BooleanField(default=False, help_text="Anchor compound for training")

    # Structural features (extracted from name)
    prefix = models.CharField(max_length=50, blank=True, db_index=True)
    suffix = models.CharField(max_length=50, blank=True)
    a_component = models.IntegerField(null=True, blank=True, help_text="Carbon chain length")
    b_component = models.IntegerField(null=True, blank=True, help_text="Unsaturation degree")
    c_component = models.CharField(max_length=10, blank=True, help_text="Oxygen component")

    # Sugar analysis
    sugar_count = models.IntegerField(null=True, blank=True)
    sialic_acid_count = models.IntegerField(null=True, blank=True)
    can_have_isomers = models.BooleanField(default=False)
    isomer_type = models.CharField(max_length=50, blank=True)

    # Modifications
    has_oacetylation = models.BooleanField(default=False)
    has_dhex = models.BooleanField(default=False)
    has_hexnac = models.BooleanField(default=False)

    # Classification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='valid')
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='UNKNOWN')

    # Regression results
    regression_group = models.CharField(max_length=100, blank=True)
    predicted_rt = models.FloatField(null=True, blank=True)
    residual = models.FloatField(null=True, blank=True)
    standardized_residual = models.FloatField(null=True, blank=True)

    # Outlier/Fragment info
    outlier_reason = models.TextField(blank=True)
    reference_compound = models.CharField(max_length=255, blank=True, help_text="Parent for fragments")
    merged_compounds = models.IntegerField(default=1, help_text="Number of merged fragments")
    fragmentation_sources = models.JSONField(default=list, help_text="Names of fragment sources")

    class Meta:
        ordering = ['session', 'name']
        indexes = [
            models.Index(fields=['session', 'status']),
            models.Index(fields=['session', 'category']),
            models.Index(fields=['prefix']),
            models.Index(fields=['is_anchor']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class RegressionModel(TimeStampedModel):
    """
    Stores regression model details for each prefix group
    """
    session = models.ForeignKey(
        AnalysisSession,
        on_delete=models.CASCADE,
        related_name='regression_models'
    )

    # Model identification
    prefix_group = models.CharField(max_length=100, db_index=True)
    model_type = models.CharField(
        max_length=50,
        default='Ridge',
        help_text="Ridge, Linear, or Fallback"
    )

    # Model parameters
    intercept = models.FloatField()
    coefficients = models.JSONField(help_text="Feature coefficients")
    feature_names = models.JSONField(help_text="List of features used")
    regularization_alpha = models.FloatField(null=True, blank=True)

    # Model quality
    r2 = models.FloatField()
    adjusted_r2 = models.FloatField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    durbin_watson = models.FloatField(null=True, blank=True)

    # Sample info
    n_samples = models.IntegerField(help_text="Total compounds in group")
    n_anchors = models.IntegerField(help_text="Anchor compounds used for training")

    # Equation (for display)
    equation = models.TextField()

    class Meta:
        ordering = ['session', 'prefix_group']
        indexes = [
            models.Index(fields=['session', 'prefix_group']),
        ]

    def __str__(self):
        return f"{self.prefix_group} - R²={self.r2:.3f}"
