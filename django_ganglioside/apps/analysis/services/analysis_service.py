"""
Analysis Service - Orchestrates ganglioside analysis with Django models

This service bridges the existing GangliosideProcessor with Django ORM,
handling CSV upload → analysis → database persistence workflow.
"""
import pandas as pd
import numpy as np
from django.db import transaction
from django.core.files.storage import default_storage
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime

from ..models import AnalysisSession, AnalysisResult, Compound, RegressionModel
from .ganglioside_processor import GangliosideProcessor


def convert_to_json_serializable(obj):
    """
    Recursively convert NumPy types to Python native types for JSON serialization

    Args:
        obj: Object to convert (dict, list, or value)

    Returns:
        JSON-serializable object
    """
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif pd.isna(obj):
        return None
    else:
        return obj


class AnalysisService:
    """
    Service class for running ganglioside analysis and persisting results
    """

    def __init__(self):
        self.processor = GangliosideProcessor()
        self.channel_layer = get_channel_layer()

    def _send_progress(self, session_id: int, message: str, percentage: int, current_step: str = ''):
        """
        Send progress update via WebSocket

        Args:
            session_id: Analysis session ID
            message: Progress message
            percentage: Progress percentage (0-100)
            current_step: Current step name
        """
        if self.channel_layer:
            room_group_name = f'analysis_{session_id}'
            try:
                async_to_sync(self.channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'analysis_progress',
                        'message': message,
                        'percentage': percentage,
                        'current_step': current_step,
                        'timestamp': datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                # Log error but don't fail analysis
                print(f"WebSocket progress update failed: {e}")

    def _send_complete(self, session_id: int, message: str, success: bool = True, results_url: str = ''):
        """
        Send completion notification via WebSocket

        Args:
            session_id: Analysis session ID
            message: Completion message
            success: Whether analysis succeeded
            results_url: URL to view results
        """
        if self.channel_layer:
            room_group_name = f'analysis_{session_id}'
            try:
                async_to_sync(self.channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'analysis_complete',
                        'message': message,
                        'success': success,
                        'results_url': results_url,
                        'timestamp': datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                print(f"WebSocket completion update failed: {e}")

    def _send_error(self, session_id: int, message: str, error: str = ''):
        """
        Send error notification via WebSocket

        Args:
            session_id: Analysis session ID
            message: Error message
            error: Error details
        """
        if self.channel_layer:
            room_group_name = f'analysis_{session_id}'
            try:
                async_to_sync(self.channel_layer.group_send)(
                    room_group_name,
                    {
                        'type': 'analysis_error',
                        'message': message,
                        'error': error,
                        'timestamp': datetime.now().isoformat(),
                    }
                )
            except Exception as e:
                print(f"WebSocket error update failed: {e}")

    def run_analysis(self, session: AnalysisSession) -> AnalysisResult:
        """
        Main entry point: Run complete analysis pipeline

        Args:
            session: AnalysisSession instance with uploaded CSV file

        Returns:
            AnalysisResult: Saved result object

        Raises:
            ValueError: If CSV is invalid or analysis fails
        """
        session_id = session.id

        try:
            # Send initial progress
            self._send_progress(session_id, "Loading CSV file...", 5, "Loading")

            # Load CSV from uploaded file
            df = self._load_csv_from_session(session)

            self._send_progress(session_id, "Configuring analysis parameters...", 10, "Configuration")

            # Update processor settings from session
            self.processor.update_settings(
                r2_threshold=session.r2_threshold,
                outlier_threshold=session.outlier_threshold,
                rt_tolerance=session.rt_tolerance
            )

            # Send progress for each rule
            self._send_progress(session_id, "Preprocessing data...", 15, "Preprocessing")

            self._send_progress(session_id, "Running Rule 1: Prefix-based regression...", 25, "Rule 1")

            # Run analysis using existing processor
            results = self.processor.process_data(df, data_type=session.data_type)

            self._send_progress(session_id, "Analysis complete. Saving results...", 80, "Saving")

            # Persist results to database
            with transaction.atomic():
                analysis_result = self._save_results(session, results, df)

            self._send_progress(session_id, "Results saved successfully.", 95, "Complete")

            # Send completion notification
            results_url = f"/analysis/sessions/{session_id}/"
            self._send_complete(
                session_id,
                "Analysis completed successfully!",
                success=True,
                results_url=results_url
            )

            return analysis_result

        except Exception as e:
            # Send error notification
            self._send_error(
                session_id,
                "Analysis failed",
                error=str(e)
            )
            raise

    def _load_csv_from_session(self, session: AnalysisSession) -> pd.DataFrame:
        """
        Load CSV file from AnalysisSession

        Args:
            session: AnalysisSession with uploaded_file

        Returns:
            pd.DataFrame: Loaded data

        Raises:
            ValueError: If file cannot be read or required columns missing
        """
        file_path = session.uploaded_file.path

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Failed to read CSV: {str(e)}")

        # Validate required columns
        required_columns = ['Name', 'RT', 'Volume', 'Log P', 'Anchor']
        missing_columns = set(required_columns) - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"CSV missing required columns: {', '.join(missing_columns)}"
            )

        return df

    def _save_results(
        self,
        session: AnalysisSession,
        results: dict,
        original_df: pd.DataFrame
    ) -> AnalysisResult:
        """
        Save analysis results to database

        Args:
            session: AnalysisSession instance
            results: Dictionary from GangliosideProcessor.process_data()
            original_df: Original input DataFrame

        Returns:
            AnalysisResult: Saved result object
        """
        # Convert all results to JSON-serializable format
        results = convert_to_json_serializable(results)

        # Create AnalysisResult
        analysis_result = AnalysisResult.objects.create(
            session=session,
            total_compounds=results.get('statistics', {}).get('total_compounds', 0),
            anchor_compounds=results.get('statistics', {}).get('anchor_compounds', 0),
            valid_compounds=len(results.get('valid_compounds', [])),
            outlier_count=len(results.get('outliers', [])),
            success_rate=results.get('statistics', {}).get('success_rate', 0.0),
            regression_analysis=results.get('regression_analysis', {}),
            regression_quality=results.get('regression_quality', {}),
            sugar_analysis=results.get('sugar_analysis', {}),
            oacetylation_analysis=results.get('oacetylation_analysis', {}),
            rt_filtering_summary=results.get('rt_filtering_summary', {}),
            categorization=results.get('categorization', {}),
            rule1_valid=len(results.get('valid_compounds', [])),
            rule1_outliers=len(results.get('outliers', [])),
            rule4_valid=results.get('oacetylation_analysis', {}).get('valid_count', 0),
            rule4_invalid=results.get('oacetylation_analysis', {}).get('invalid_count', 0),
            rule5_fragments=results.get('rt_filtering_summary', {}).get('total_fragments_merged', 0)
        )

        # Save compounds
        self._save_compounds(session, results, original_df)

        # Save regression models
        self._save_regression_models(session, results)

        return analysis_result

    def _save_compounds(
        self,
        session: AnalysisSession,
        results: dict,
        original_df: pd.DataFrame
    ):
        """
        Save individual compound data to database

        Args:
            session: AnalysisSession instance
            results: Analysis results dictionary
            original_df: Original input DataFrame
        """
        compounds_to_create = []

        # Process valid compounds
        for compound_data in results.get('valid_compounds', []):
            compound = self._create_compound_from_dict(session, compound_data, 'valid')
            compounds_to_create.append(compound)

        # Process outliers
        for outlier_data in results.get('outliers', []):
            compound = self._create_compound_from_dict(session, outlier_data, 'outlier')
            compounds_to_create.append(compound)

        # Bulk create for efficiency
        Compound.objects.bulk_create(compounds_to_create, batch_size=500)

    def _create_compound_from_dict(
        self,
        session: AnalysisSession,
        data: dict,
        compound_status: str
    ) -> Compound:
        """
        Create Compound model instance from dictionary

        Args:
            session: AnalysisSession instance
            data: Compound data dictionary
            compound_status: 'valid', 'outlier', or 'fragment'

        Returns:
            Compound: Model instance (not saved)
        """
        # Determine category from prefix
        prefix = data.get('prefix', '')
        category = self._get_category_from_prefix(prefix)

        return Compound(
            session=session,
            name=data.get('Name', ''),
            rt=data.get('RT', 0.0),
            volume=data.get('Volume', 0.0),
            log_p=data.get('Log P', 0.0),
            is_anchor=data.get('Anchor', 'F') == 'T',
            prefix=prefix,
            suffix=data.get('suffix', ''),
            a_component=data.get('a_component'),
            b_component=data.get('b_component'),
            c_component=data.get('c_component', ''),
            sugar_count=data.get('sugar_count'),
            sialic_acid_count=data.get('sialic_acid_count'),
            can_have_isomers=data.get('can_have_isomers', False),
            isomer_type=data.get('isomer_type', ''),
            has_oacetylation='+OAc' in data.get('Name', ''),
            has_dhex='+dHex' in data.get('Name', ''),
            has_hexnac='+HexNAc' in data.get('Name', ''),
            status=compound_status,
            category=category,
            regression_group=data.get('regression_group', ''),
            predicted_rt=data.get('Predicted_RT'),
            residual=data.get('Residual'),
            standardized_residual=data.get('Standardized_Residual'),
            outlier_reason=data.get('outlier_reason', ''),
            reference_compound=data.get('reference_compound', ''),
            merged_compounds=data.get('merged_compounds', 1),
            fragmentation_sources=data.get('fragmentation_sources', [])
        )

    def _get_category_from_prefix(self, prefix: str) -> str:
        """
        Determine ganglioside category from prefix

        Args:
            prefix: Compound prefix (e.g., 'GD1', 'GM3')

        Returns:
            str: Category code ('GM', 'GD', 'GT', 'GQ', 'GP', 'UNKNOWN')
        """
        if not prefix:
            return 'UNKNOWN'

        # Extract category letter (second character after 'G')
        if len(prefix) >= 2:
            category_letter = prefix[1]
            category_map = {
                'M': 'GM',
                'D': 'GD',
                'T': 'GT',
                'Q': 'GQ',
                'P': 'GP'
            }
            return category_map.get(category_letter, 'UNKNOWN')

        return 'UNKNOWN'

    def _save_regression_models(self, session: AnalysisSession, results: dict):
        """
        Save regression model details to database

        Args:
            session: AnalysisSession instance
            results: Analysis results dictionary
        """
        models_to_create = []

        regression_analysis = results.get('regression_analysis', {})
        regression_quality = results.get('regression_quality', {})

        for prefix_group, model_data in regression_analysis.items():
            quality_data = regression_quality.get(prefix_group, {})

            # Extract coefficients and feature names
            coefficients = model_data.get('coefficients', {})
            feature_names = list(coefficients.keys())

            # Build equation string
            equation = self._build_equation_string(
                model_data.get('intercept', 0.0),
                coefficients
            )

            regression_model = RegressionModel(
                session=session,
                prefix_group=prefix_group,
                model_type=model_data.get('model_type', 'Ridge'),
                intercept=model_data.get('intercept', 0.0),
                coefficients=coefficients,
                feature_names=feature_names,
                regularization_alpha=model_data.get('alpha', 1.0),
                r2=quality_data.get('r2', 0.0),
                adjusted_r2=quality_data.get('adjusted_r2'),
                rmse=quality_data.get('rmse'),
                durbin_watson=quality_data.get('durbin_watson'),
                n_samples=model_data.get('n_samples', 0),
                n_anchors=model_data.get('n_anchors', 0),
                equation=equation
            )
            models_to_create.append(regression_model)

        # Bulk create
        RegressionModel.objects.bulk_create(models_to_create, batch_size=100)

    def _build_equation_string(self, intercept: float, coefficients: dict) -> str:
        """
        Build human-readable regression equation

        Args:
            intercept: Model intercept
            coefficients: Dictionary of {feature: coefficient}

        Returns:
            str: Equation string (e.g., "RT = 5.2 + 0.3*LogP + 0.1*a_component")
        """
        parts = [f"{intercept:.4f}"]

        for feature, coef in coefficients.items():
            sign = "+" if coef >= 0 else "-"
            parts.append(f"{sign} {abs(coef):.4f}*{feature}")

        return f"RT = {' '.join(parts)}"
