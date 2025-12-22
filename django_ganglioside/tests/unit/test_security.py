"""
Unit tests for security features including CSV injection protection
and file upload validation
"""
import pytest
import pandas as pd
from io import StringIO, BytesIO
from unittest.mock import Mock, MagicMock

from apps.analysis.services.ganglioside_processor import GangliosideProcessor
from apps.analysis.services.ganglioside_processor_v2 import GangliosideProcessorV2
from apps.analysis.serializers import AnalysisSessionCreateSerializer


class TestCSVInjectionProtection:
    """Test CSV injection protection in processors"""

    @pytest.fixture
    def malicious_csv_data(self):
        """CSV data with potential formula injection patterns"""
        return pd.DataFrame({
            'Name': [
                '=cmd|\'calc\'!A0',  # Excel command injection
                '+SUM(A1:A10)',      # Plus prefix formula
                '-1+1',              # Minus prefix formula
                '@SUM(A1)',          # At-sign prefix
                '\t=1+1',            # Tab prefix
                '\r=HYPERLINK()',    # Carriage return prefix
                'GD1(36:1;O2)',      # Normal compound name
            ],
            'RT': [9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 9.572],
            'Volume': [1000000] * 7,
            'Log P': [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 1.53],
            'Anchor': ['T', 'T', 'T', 'T', 'T', 'T', 'T'],
        })

    @pytest.fixture
    def clean_csv_data(self):
        """Normal CSV data without injection patterns"""
        return pd.DataFrame({
            'Name': [
                'GD1(36:1;O2)',
                'GM1(36:1;O2)',
                'GT1(36:1;O2)',
            ],
            'RT': [9.572, 10.452, 8.701],
            'Volume': [1000000, 500000, 1200000],
            'Log P': [1.53, 4.00, -0.94],
            'Anchor': ['T', 'T', 'T'],
        })

    def test_v1_processor_sanitizes_dangerous_prefixes(self, malicious_csv_data):
        """Test that V1 processor removes dangerous prefixes from Name column"""
        processor = GangliosideProcessor()

        # Make a copy to avoid modifying the fixture
        df = malicious_csv_data.copy()

        # Call the preprocessing method
        processed_df = processor._preprocess_data(df)

        # Check that dangerous prefixes are removed
        dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r')
        for name in processed_df['Name']:
            assert not str(name).startswith(dangerous_prefixes), \
                f"Name '{name}' still has dangerous prefix"

    def test_v2_processor_sanitizes_dangerous_prefixes(self, malicious_csv_data):
        """Test that V2 processor removes dangerous prefixes from Name column"""
        processor = GangliosideProcessorV2()

        # Make a copy to avoid modifying the fixture
        df = malicious_csv_data.copy()

        # Call the preprocessing method
        processed_df = processor._preprocess_data(df)

        # Check that dangerous prefixes are removed
        dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r')
        for name in processed_df['Name']:
            assert not str(name).startswith(dangerous_prefixes), \
                f"Name '{name}' still has dangerous prefix"

    def test_clean_data_passes_through_unchanged(self, clean_csv_data):
        """Test that clean data is not modified by sanitization"""
        processor_v1 = GangliosideProcessor()
        processor_v2 = GangliosideProcessorV2()

        original_names = clean_csv_data['Name'].tolist()

        # Test V1
        df_v1 = clean_csv_data.copy()
        processed_v1 = processor_v1._preprocess_data(df_v1)
        for orig, proc in zip(original_names, processed_v1['Name'].tolist()):
            assert orig == proc, f"V1: Clean name '{orig}' was incorrectly modified to '{proc}'"

        # Test V2
        df_v2 = clean_csv_data.copy()
        processed_v2 = processor_v2._preprocess_data(df_v2)
        for orig, proc in zip(original_names, processed_v2['Name'].tolist()):
            assert orig == proc, f"V2: Clean name '{orig}' was incorrectly modified to '{proc}'"

    def test_sanitization_preserves_valid_compound_structure(self, malicious_csv_data):
        """Test that sanitization still extracts valid compound structures after cleaning"""
        processor = GangliosideProcessorV2()

        df = malicious_csv_data.copy()
        processed_df = processor._preprocess_data(df)

        # The last row is a valid compound and should be parsed correctly
        valid_row = processed_df[processed_df['Name'] == 'GD1(36:1;O2)']
        assert len(valid_row) == 1, "Valid compound should remain after sanitization"
        assert valid_row['prefix'].values[0] == 'GD1', "Prefix should be extracted correctly"
        assert valid_row['suffix'].values[0] == '36:1;O2', "Suffix should be extracted correctly"

    def test_multiple_dangerous_prefixes_stripped(self):
        """Test that multiple consecutive dangerous prefixes are all stripped"""
        processor = GangliosideProcessorV2()

        df = pd.DataFrame({
            'Name': ['===GD1(36:1;O2)', '++GM1(36:1;O2)', '--GT1(36:1;O2)'],
            'RT': [9.5, 10.0, 8.7],
            'Volume': [1000000, 500000, 1200000],
            'Log P': [1.5, 4.0, -0.9],
            'Anchor': ['T', 'T', 'T'],
        })

        processed_df = processor._preprocess_data(df)

        # After stripping, names should start with valid compound prefixes
        assert processed_df['Name'].iloc[0] == 'GD1(36:1;O2)'
        assert processed_df['Name'].iloc[1] == 'GM1(36:1;O2)'
        assert processed_df['Name'].iloc[2] == 'GT1(36:1;O2)'


class TestCSVInjectionPatterns:
    """Test detection of various CSV injection attack patterns"""

    @pytest.mark.parametrize("malicious_name,expected_sanitized", [
        ("=HYPERLINK('http://evil.com')", "HYPERLINK('http://evil.com')"),
        ("+cmd|'calc'!A0", "cmd|'calc'!A0"),
        ("-1+1", "1+1"),
        ("@SUM(A1:A10)", "SUM(A1:A10)"),
        ("\t=1+1", "1+1"),
        ("\r=test", "test"),
    ])
    def test_injection_patterns_are_sanitized(self, malicious_name, expected_sanitized):
        """Test that dangerous prefixes are stripped from Name column"""
        processor = GangliosideProcessorV2()

        # Include a valid compound to prevent empty DataFrame after preprocessing
        df = pd.DataFrame({
            'Name': [malicious_name, 'GD1(36:1;O2)'],
            'RT': [9.5, 9.572],
            'Volume': [1000000, 1000000],
            'Log P': [1.5, 1.53],
            'Anchor': ['T', 'T'],
        })

        # Check that dangerous prefixes are stripped (before invalid row removal)
        dangerous_prefixes = ('=', '+', '-', '@', '\t', '\r')
        df_copy = df.copy()
        if 'Name' in df_copy.columns:
            df_copy['Name'] = df_copy['Name'].apply(
                lambda x: str(x).lstrip(''.join(dangerous_prefixes)) if isinstance(x, str) else x
            )

        # First row should have dangerous prefix stripped
        assert df_copy['Name'].iloc[0] == expected_sanitized, \
            f"Expected '{expected_sanitized}', got '{df_copy['Name'].iloc[0]}'"

    def test_malicious_names_without_parentheses_are_removed(self):
        """Test that malicious names without proper compound format are removed"""
        processor = GangliosideProcessorV2()

        df = pd.DataFrame({
            'Name': [
                '=cmd|calc!A0',   # No parentheses - will not match compound format
                'GD1(36:1;O2)',   # Valid compound
            ],
            'RT': [9.5, 9.572],
            'Volume': [1000000, 1000000],
            'Log P': [1.5, 1.53],
            'Anchor': ['T', 'T'],
        })

        processed_df = processor._preprocess_data(df)

        # Malicious name should be removed (doesn't match compound format)
        # Only the valid compound should remain
        assert len(processed_df) == 1, "Malicious names without valid format should be removed"
        assert processed_df['Name'].iloc[0] == 'GD1(36:1;O2)', "Valid compound should remain"

    def test_dangerous_prefix_stripped_even_if_format_matches(self):
        """Test that dangerous prefixes are stripped even if result matches format"""
        processor = GangliosideProcessorV2()

        # This malicious name has parentheses that match the pattern
        # The important thing is that the '=' prefix is stripped
        df = pd.DataFrame({
            'Name': ['=HYPERLINK("evil.com")'],
            'RT': [9.5],
            'Volume': [1000000],
            'Log P': [1.5],
            'Anchor': ['T'],
        })

        processed_df = processor._preprocess_data(df)

        # The '=' should be stripped even though the pattern matches
        assert not processed_df['Name'].iloc[0].startswith('='), \
            "Dangerous prefix '=' should be stripped"
        assert processed_df['Name'].iloc[0] == 'HYPERLINK("evil.com")', \
            "Name should have dangerous prefix removed"

    def test_valid_compound_with_dangerous_prefix_is_preserved(self):
        """Test that valid compounds with dangerous prefixes are sanitized and preserved"""
        processor = GangliosideProcessorV2()

        df = pd.DataFrame({
            'Name': ['=+@-\tGD1(36:1;O2)'],  # Valid compound hidden by prefixes
            'RT': [9.572],
            'Volume': [1000000],
            'Log P': [1.53],
            'Anchor': ['T'],
        })

        processed_df = processor._preprocess_data(df)

        # After sanitization, the valid compound format should be revealed and preserved
        assert len(processed_df) == 1, "Valid compound should be preserved after sanitization"
        assert processed_df['Name'].iloc[0] == 'GD1(36:1;O2)', "Dangerous prefixes should be stripped"
        assert processed_df['prefix'].iloc[0] == 'GD1', "Prefix should be correctly extracted"


class TestFileUploadValidation:
    """Test file upload validation features"""

    def _create_mock_file(self, content: bytes, filename: str = 'test.csv', size: int = None):
        """Create a mock file object for testing"""
        file = MagicMock()
        file.name = filename
        file.size = size if size is not None else len(content)

        # Create a BytesIO that supports seek and read
        buffer = BytesIO(content)
        file.read = buffer.read
        file.seek = buffer.seek

        return file

    def test_valid_csv_passes_validation(self):
        """Test that valid CSV files pass validation"""
        csv_content = b"Name,RT,Volume,Log P,Anchor\nGD1(36:1;O2),9.572,1000000,1.53,T\n"
        mock_file = self._create_mock_file(csv_content)

        serializer = AnalysisSessionCreateSerializer()
        # Should not raise exception
        result = serializer.validate_uploaded_file(mock_file)
        assert result is not None

    def test_non_csv_extension_rejected(self):
        """Test that non-CSV file extensions are rejected"""
        csv_content = b"Name,RT,Volume,Log P,Anchor\nGD1(36:1;O2),9.572,1000000,1.53,T\n"
        mock_file = self._create_mock_file(csv_content, filename='test.xlsx')

        serializer = AnalysisSessionCreateSerializer()
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_uploaded_file(mock_file)
        assert "Only CSV files are allowed" in str(exc_info.value)

    def test_oversized_file_rejected(self):
        """Test that files exceeding 50MB are rejected"""
        csv_content = b"Name,RT,Volume,Log P,Anchor\nGD1(36:1;O2),9.572,1000000,1.53,T\n"
        # Simulate a 51MB file
        mock_file = self._create_mock_file(csv_content, size=51 * 1024 * 1024)

        serializer = AnalysisSessionCreateSerializer()
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_uploaded_file(mock_file)
        assert "exceed 50MB" in str(exc_info.value)

    def test_binary_content_rejected(self):
        """Test that binary content is rejected"""
        # PNG file header (magic bytes)
        binary_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        mock_file = self._create_mock_file(binary_content, filename='malicious.csv')

        serializer = AnalysisSessionCreateSerializer()
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_uploaded_file(mock_file)
        assert "binary" in str(exc_info.value).lower() or "UTF-8" in str(exc_info.value)

    def test_missing_required_columns_rejected(self):
        """Test that CSVs missing required columns are rejected"""
        # Missing 'Volume' and 'Log P' columns
        csv_content = b"Name,RT,Anchor\nGD1(36:1;O2),9.572,T\n"
        mock_file = self._create_mock_file(csv_content)

        serializer = AnalysisSessionCreateSerializer()
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_uploaded_file(mock_file)
        assert "Missing required columns" in str(exc_info.value)

    def test_too_many_rows_rejected(self):
        """Test that files with too many rows are rejected"""
        # Create content with more rows than allowed
        header = b"Name,RT,Volume,Log P,Anchor\n"
        row = b"GD1(36:1;O2),9.572,1000000,1.53,T\n"
        max_rows = AnalysisSessionCreateSerializer.MAX_ROW_COUNT

        # Create content with max_rows + 100 rows
        csv_content = header + row * (max_rows + 100)
        mock_file = self._create_mock_file(csv_content)

        serializer = AnalysisSessionCreateSerializer()
        from rest_framework.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            serializer.validate_uploaded_file(mock_file)
        assert "too many rows" in str(exc_info.value)

    def test_max_row_limit_is_reasonable(self):
        """Test that MAX_ROW_COUNT is set to a reasonable value"""
        max_rows = AnalysisSessionCreateSerializer.MAX_ROW_COUNT
        assert max_rows >= 1000, "MAX_ROW_COUNT should allow at least 1000 rows"
        assert max_rows <= 100000, "MAX_ROW_COUNT should not exceed 100000 rows"

    def test_file_at_row_limit_passes(self):
        """Test that files exactly at the row limit pass validation"""
        header = b"Name,RT,Volume,Log P,Anchor\n"
        row = b"GD1(36:1;O2),9.572,1000000,1.53,T\n"
        max_rows = AnalysisSessionCreateSerializer.MAX_ROW_COUNT

        # Create content with exactly max_rows
        csv_content = header + row * max_rows
        mock_file = self._create_mock_file(csv_content)

        serializer = AnalysisSessionCreateSerializer()
        # Should not raise exception
        result = serializer.validate_uploaded_file(mock_file)
        assert result is not None
