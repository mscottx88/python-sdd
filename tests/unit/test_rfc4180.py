"""
Unit tests for RFC 4180 CSV compliance.

Tests the system's ability to handle standard CSV edge cases:
- Quoted fields containing commas
- Escaped double quotes within quoted fields
- Embedded newlines within quoted fields
- CR+LF line endings

Reference: https://tools.ietf.org/html/rfc4180
"""

from pathlib import Path

import pytest

from src.csv_postgres_pipeline.models import CSVFile, ValidationStatus
from src.csv_postgres_pipeline.validator import validate_csv_file


class TestRFC4180Compliance:
    """Test RFC 4180 CSV edge cases (FR-014)."""

    def test_quoted_fields_with_commas(self, tmp_path: Path) -> None:
        """Test that fields containing commas are properly handled when quoted."""
        test_file = tmp_path / "test.csv"
        test_file.write_text(
            'col1,col2,col3\n1,"value, with comma",3\n4,"another, comma",6\n'
        )

        csv_file = CSVFile(file_path=test_file)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["col1", "col2", "col3"]
        assert csv_file.row_count == 2

    def test_escaped_quotes_within_quoted_fields(self, tmp_path: Path) -> None:
        """Test that double quotes are properly escaped within quoted fields."""
        test_file = tmp_path / "test.csv"
        test_file.write_text(
            'col1,col2,col3\n1,"value with ""quotes""",3\n4,"more ""escaped"" quotes",6\n'
        )

        csv_file = CSVFile(file_path=test_file)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["col1", "col2", "col3"]
        assert csv_file.row_count == 2

    def test_embedded_newlines_within_quoted_fields(self, tmp_path: Path) -> None:
        """Test that newlines within quoted fields are handled correctly."""
        test_file = tmp_path / "test.csv"
        test_file.write_text(
            'col1,col2,col3\n1,"value with\nembedded newline",3\n4,"another\nmultiline\nvalue",6\n'
        )

        csv_file = CSVFile(file_path=test_file)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["col1", "col2", "col3"]
        # Note: row_count counts logical rows, not physical lines
        assert csv_file.row_count == 2

    def test_crlf_line_endings(self, tmp_path: Path) -> None:
        """Test that CR+LF line endings (Windows style) are handled correctly."""
        test_file = tmp_path / "test.csv"
        # Write in binary mode to preserve CRLF line endings
        test_file.write_bytes(b"col1,col2,col3\r\n1,value1,3\r\n4,value2,6\r\n")

        csv_file = CSVFile(file_path=test_file)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["col1", "col2", "col3"]
        assert csv_file.row_count == 2

    def test_mixed_quoted_and_unquoted_fields(self, tmp_path: Path) -> None:
        """Test that quoted and unquoted fields can coexist in the same row."""
        test_file = tmp_path / "test.csv"
        test_file.write_text(
            'col1,col2,col3\n1,"quoted value",unquoted\n2,unquoted,"quoted"\n'
        )

        csv_file = CSVFile(file_path=test_file)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["col1", "col2", "col3"]
        assert csv_file.row_count == 2

    def test_empty_quoted_fields(self, tmp_path: Path) -> None:
        """Test that empty quoted fields are handled correctly."""
        test_file = tmp_path / "test.csv"
        test_file.write_text('col1,col2,col3\n1,"",3\n4,"",6\n')

        csv_file = CSVFile(file_path=test_file)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["col1", "col2", "col3"]
        assert csv_file.row_count == 2

    def test_rfc4180_fixture_file(self) -> None:
        """Test the RFC 4180 fixture file with multiple edge cases."""
        fixture_path = (
            Path(__file__).parent.parent
            / "integration"
            / "fixtures"
            / "rfc4180_quoted_fields.csv"
        )

        if not fixture_path.exists():
            pytest.skip(f"Fixture file not found: {fixture_path}")

        csv_file = CSVFile(file_path=fixture_path)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["id", "name", "description", "status"]
        assert csv_file.row_count == 5


class TestLineEndings:
    """Tests for CRLF/LF line ending support (FR-014, T049c-T049e).

    Per constitution: Source files must use LF only, but CSV data files
    MUST support both CRLF and LF per RFC 4180.
    """

    def test_csv_mixed_line_endings(self, tmp_path: Path) -> None:
        """Test CSV with mixed CRLF and LF line endings within same file."""
        csv_path = tmp_path / "mixed_endings.csv"

        # Mix CRLF and LF in same file (some tools produce this)
        content = b"name,value\r\nAlice,100\nBob,200\r\nCharlie,300\n"
        csv_path.write_bytes(content)

        csv_file = CSVFile(file_path=csv_path)

        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.row_count == 3  # Should count all 3 data rows

    def test_csv_crlf_only(self, tmp_path: Path) -> None:
        """Test CSV with Windows CRLF line endings only."""
        csv_path = tmp_path / "crlf.csv"

        # All CRLF (Windows style)
        content = b"name,value\r\nAlice,100\r\nBob,200\r\n"
        csv_path.write_bytes(content)

        csv_file = CSVFile(file_path=csv_path)

        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.row_count == 2

    def test_csv_lf_only(self, tmp_path: Path) -> None:
        """Test CSV with Unix LF line endings only."""
        csv_path = tmp_path / "lf.csv"

        # All LF (Unix style)
        content = b"name,value\nAlice,100\nBob,200\n"
        csv_path.write_bytes(content)

        csv_file = CSVFile(file_path=csv_path)

        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.row_count == 2

    def test_csv_embedded_newlines_with_crlf(self, tmp_path: Path) -> None:
        """Test CSV with embedded newlines in quoted fields using CRLF line endings."""
        csv_path = tmp_path / "embedded_crlf.csv"

        # RFC 4180: Quoted fields can contain newlines
        content = (
            b'name,description\r\n"Alice","Line1\r\nLine2"\r\n"Bob","Single line"\r\n'
        )
        csv_path.write_bytes(content)

        csv_file = CSVFile(file_path=csv_path)

        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.row_count == 2
