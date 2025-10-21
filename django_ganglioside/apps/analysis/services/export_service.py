"""
Export Service - Export analysis results to various formats
"""
import csv
import io
from django.http import HttpResponse
import pandas as pd

from ..models import AnalysisSession


class ExportService:
    """
    Service for exporting analysis results
    """

    def export_session(self, session: AnalysisSession, export_format: str = 'csv'):
        """
        Export session results

        Args:
            session: AnalysisSession instance
            export_format: 'csv', 'json', or 'excel'

        Returns:
            HttpResponse with file download
        """
        if export_format == 'csv':
            return self._export_csv(session)
        elif export_format == 'json':
            return self._export_json(session)
        elif export_format == 'excel':
            return self._export_excel(session)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")

    def _export_csv(self, session: AnalysisSession) -> HttpResponse:
        """Export compounds as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="analysis_{session.id}_compounds.csv"'

        writer = csv.writer(response)

        # Header
        writer.writerow([
            'Name', 'RT', 'Volume', 'Log P', 'Anchor', 'Status', 'Category',
            'Predicted RT', 'Residual', 'Standardized Residual', 'Outlier Reason'
        ])

        # Data
        for compound in session.compounds.all():
            writer.writerow([
                compound.name,
                compound.rt,
                compound.volume,
                compound.log_p,
                'T' if compound.is_anchor else 'F',
                compound.get_status_display(),
                compound.get_category_display(),
                compound.predicted_rt,
                compound.residual,
                compound.standardized_residual,
                compound.outlier_reason
            ])

        return response

    def _export_json(self, session: AnalysisSession) -> HttpResponse:
        """Export session as JSON"""
        from ..serializers import AnalysisSessionSerializer

        response = HttpResponse(content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="analysis_{session.id}.json"'

        serializer = AnalysisSessionSerializer(session)
        response.write(str(serializer.data))

        return response

    def _export_excel(self, session: AnalysisSession) -> HttpResponse:
        """Export compounds as Excel"""
        # Create DataFrame
        compounds_data = []
        for compound in session.compounds.all():
            compounds_data.append({
                'Name': compound.name,
                'RT': compound.rt,
                'Volume': compound.volume,
                'Log P': compound.log_p,
                'Anchor': 'T' if compound.is_anchor else 'F',
                'Status': compound.get_status_display(),
                'Category': compound.get_category_display(),
                'Predicted RT': compound.predicted_rt,
                'Residual': compound.residual,
                'Standardized Residual': compound.standardized_residual,
                'Outlier Reason': compound.outlier_reason
            })

        df = pd.DataFrame(compounds_data)

        # Write to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Compounds', index=False)

        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="analysis_{session.id}_compounds.xlsx"'

        return response
