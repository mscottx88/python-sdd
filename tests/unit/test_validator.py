"""Unit tests for CSV validation functions."""

from pathlib import Path

import pytest

from src.csv_postgres_pipeline.exceptions import ValidationError
from src.csv_postgres_pipeline.models import (
    ColumnInfo,
    CSVFile,
    PipelineConfig,
    TableSchema,
    ValidationStatus,
)
from src.csv_postgres_pipeline.validator import validate_csv_file, validate_csv_schema


class TestValidateCSVFile:
    """Tests for validate_csv_file function."""

    def test_validate_valid_csv_file(self, tmp_path: Path) -> None:
        """Test validation of a valid CSV file."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2,col3\nval1,val2,val3\nval4,val5,val6\n")

        csv_file = CSVFile(file_path=test_file)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["col1", "col2", "col3"]
        assert csv_file.row_count == 2

    def test_validate_csv_strips_whitespace_from_headers(self, tmp_path: Path) -> None:
        """Test that column names have whitespace stripped."""
        test_file = tmp_path / "test.csv"
        test_file.write_text(" col1 , col2 ,col3\nval1,val2,val3\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        assert csv_file.column_names == ["col1", "col2", "col3"]

    def test_validate_csv_empty_file_with_header(self, tmp_path: Path) -> None:
        """Test validation of CSV with header but no data rows."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2,col3\n")

        csv_file = CSVFile(file_path=test_file)
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.column_names == ["col1", "col2", "col3"]
        assert csv_file.row_count == 0

    def test_validate_csv_duplicate_column_names(self, tmp_path: Path) -> None:
        """Test validation fails with duplicate column names."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2,col1\nval1,val2,val3\n")

        csv_file = CSVFile(file_path=test_file)

        with pytest.raises(ValidationError, match="duplicate column names"):
            validate_csv_file(csv_file)

        assert csv_file.validation_status == ValidationStatus.INVALID

    def test_validate_csv_empty_header_row(self, tmp_path: Path) -> None:
        """Test validation fails with empty header row."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("\nval1,val2,val3\n")

        csv_file = CSVFile(file_path=test_file)

        with pytest.raises(ValidationError, match="header row is empty"):
            validate_csv_file(csv_file)

        assert csv_file.validation_status == ValidationStatus.INVALID

    def test_validate_csv_completely_empty_file(self, tmp_path: Path) -> None:
        """Test validation fails with completely empty file."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("")

        csv_file = CSVFile(file_path=test_file)

        with pytest.raises(ValidationError, match="empty"):
            validate_csv_file(csv_file)

        assert csv_file.validation_status == ValidationStatus.INVALID

    def test_validate_csv_nonexistent_file(self, tmp_path: Path) -> None:
        """Test validation fails for nonexistent file."""
        # Create CSVFile with path that will exist initially
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1\n")
        csv_file = CSVFile(file_path=test_file)

        # Remove the file
        test_file.unlink()

        with pytest.raises(ValidationError, match="not found"):
            validate_csv_file(csv_file)

    def test_validate_csv_invalid_encoding(self, tmp_path: Path) -> None:
        """Test validation fails with encoding errors."""
        test_file = tmp_path / "test.csv"
        # Write binary data that's not valid UTF-8
        test_file.write_bytes(b"\xff\xfe\x00\x00")

        csv_file = CSVFile(file_path=test_file, encoding="utf-8")

        with pytest.raises(ValidationError, match="Failed to read"):
            validate_csv_file(csv_file)

        assert csv_file.validation_status == ValidationStatus.INVALID

    def test_validate_csv_custom_delimiter(self, tmp_path: Path) -> None:
        """Test validation with custom delimiter."""
        test_file = tmp_path / "test.tsv"
        test_file.write_text("col1\tcol2\tcol3\nval1\tval2\tval3\n")

        csv_file = CSVFile(file_path=test_file, delimiter="\t")
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.column_names == ["col1", "col2", "col3"]
        assert csv_file.row_count == 1

    def test_validate_csv_updates_validation_status(self, tmp_path: Path) -> None:
        """Test that validation status is updated during validation."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        assert csv_file.validation_status == ValidationStatus.NOT_VALIDATED

        validate_csv_file(csv_file)

        assert csv_file.validation_status == ValidationStatus.VALID  # type: ignore[comparison-overlap]


class TestValidateCSVSchema:
    """Tests for validate_csv_schema function."""

    def test_validate_schema_exact_match(self, tmp_path: Path) -> None:
        """Test schema validation with exact column match."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)
        config = PipelineConfig()

        result = validate_csv_schema(csv_file, schema, config)

        assert result is True

    def test_validate_schema_missing_required_column(self, tmp_path: Path) -> None:
        """Test schema validation fails with missing required column."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1\nval1\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=False, ordinal_position=2
            ),  # Required column
        ]
        schema = TableSchema(table_name="test_table", columns=columns)
        config = PipelineConfig()

        with pytest.raises(ValidationError, match="missing required columns"):
            validate_csv_schema(csv_file, schema, config)

        assert csv_file.validation_status == ValidationStatus.INVALID

    def test_validate_schema_extra_csv_column(self, tmp_path: Path) -> None:
        """Test schema validation fails with extra CSV column."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2,col3\nval1,val2,val3\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)
        config = PipelineConfig()

        with pytest.raises(ValidationError, match="not in table"):
            validate_csv_schema(csv_file, schema, config)

    def test_validate_schema_optional_column_missing(self, tmp_path: Path) -> None:
        """Test schema validation with missing optional column requires allow_subset."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1\nval1\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=False, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),  # Nullable (optional)
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        # Strict mode (default) - should fail
        strict_config = PipelineConfig()
        with pytest.raises(ValidationError, match="missing optional columns"):
            validate_csv_schema(csv_file, schema, strict_config)

        # Reset validation status after failed validation
        csv_file.validation_status = ValidationStatus.VALID

        # With allow_subset - should pass
        subset_config = PipelineConfig(allow_subset=True)
        result = validate_csv_schema(csv_file, schema, subset_config)

        assert result is True

    def test_validate_schema_column_with_default_missing(self, tmp_path: Path) -> None:
        """Test schema validation with missing column that has default requires allow_subset."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1\nval1\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=False, ordinal_position=1
            ),
            ColumnInfo(
                name="col2",
                data_type="integer",
                is_nullable=False,
                ordinal_position=2,
                column_default="0",
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        # Strict mode - should fail even though column has default
        strict_config = PipelineConfig()
        with pytest.raises(ValidationError, match="missing optional columns"):
            validate_csv_schema(csv_file, schema, strict_config)

        # Reset validation status after failed validation
        csv_file.validation_status = ValidationStatus.VALID

        # With allow_subset - should pass (column with default is acceptable to omit)
        subset_config = PipelineConfig(allow_subset=True)
        result = validate_csv_schema(csv_file, schema, subset_config)

        assert result is True

    def test_validate_schema_requires_validated_csv(self, tmp_path: Path) -> None:
        """Test schema validation requires CSV to be validated first."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        # Don't call validate_csv_file

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)
        config = PipelineConfig()

        with pytest.raises(ValidationError, match="must be validated before"):
            validate_csv_schema(csv_file, schema, config)

    def test_validate_schema_requires_column_names(self, tmp_path: Path) -> None:
        """Test schema validation fails if CSV has no column names."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        csv_file.validation_status = ValidationStatus.VALID
        csv_file.column_names = []  # Empty column names

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)
        config = PipelineConfig()

        with pytest.raises(ValidationError, match="no column names"):
            validate_csv_schema(csv_file, schema, config)


class TestConfigurableColumnMatching:
    """Tests for configurable column matching modes in validate_csv_schema."""

    def test_case_insensitive_matching_success(self, tmp_path: Path) -> None:
        """Test case-insensitive column matching allows different case."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("COL1,Col2,col3\nval1,val2,val3\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
            ColumnInfo(
                name="col3", data_type="text", is_nullable=True, ordinal_position=3
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        # Strict mode should fail
        strict_config = PipelineConfig()
        with pytest.raises(ValidationError, match="not in table"):
            validate_csv_schema(csv_file, schema, strict_config)

        # Reset status
        csv_file.validation_status = ValidationStatus.VALID

        # Case-insensitive mode should pass
        case_config = PipelineConfig(case_insensitive=True)
        result = validate_csv_schema(csv_file, schema, case_config)
        assert result is True

    def test_case_insensitive_duplicate_detection(self, tmp_path: Path) -> None:
        """Test case-insensitive mode detects duplicate columns."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,COL1,col2\nval1,val2,val3\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)
        config = PipelineConfig(case_insensitive=True)

        with pytest.raises(ValidationError, match="duplicate columns"):
            validate_csv_schema(csv_file, schema, config)

    def test_allow_subset_with_optional_columns(self, tmp_path: Path) -> None:
        """Test allow_subset permits missing optional columns."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1\nval1\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=False, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
            ColumnInfo(
                name="col3",
                data_type="integer",
                is_nullable=False,
                column_default="0",
                ordinal_position=3,
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)
        config = PipelineConfig(allow_subset=True)

        result = validate_csv_schema(csv_file, schema, config)
        assert result is True

    def test_allow_subset_still_requires_required_columns(self, tmp_path: Path) -> None:
        """Test allow_subset still fails if required columns are missing."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col2\nval2\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=False, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)
        config = PipelineConfig(allow_subset=True)

        with pytest.raises(ValidationError, match="missing required columns"):
            validate_csv_schema(csv_file, schema, config)

    def test_ignore_extra_columns(self, tmp_path: Path) -> None:
        """Test ignore_extra allows CSV to have extra columns."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2,col3,col4\nval1,val2,val3,val4\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        # Strict mode should fail
        strict_config = PipelineConfig()
        with pytest.raises(ValidationError, match="not in table"):
            validate_csv_schema(csv_file, schema, strict_config)

        # Reset status
        csv_file.validation_status = ValidationStatus.VALID

        # Ignore extra mode should pass
        ignore_config = PipelineConfig(ignore_extra=True)
        result = validate_csv_schema(csv_file, schema, ignore_config)
        assert result is True

    def test_combined_case_insensitive_and_subset(self, tmp_path: Path) -> None:
        """Test combining case-insensitive and subset matching."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("COL1\nval1\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=False, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        # Need both flags for this to work
        config = PipelineConfig(case_insensitive=True, allow_subset=True)
        result = validate_csv_schema(csv_file, schema, config)
        assert result is True

    def test_combined_case_insensitive_and_ignore_extra(self, tmp_path: Path) -> None:
        """Test combining case-insensitive and ignore extra columns."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("COL1,Col2,extra_col\nval1,val2,val3\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        config = PipelineConfig(case_insensitive=True, ignore_extra=True)
        result = validate_csv_schema(csv_file, schema, config)
        assert result is True

    def test_combined_subset_and_ignore_extra(self, tmp_path: Path) -> None:
        """Test combining subset and ignore extra columns."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,extra_col\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=False, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        config = PipelineConfig(allow_subset=True, ignore_extra=True)
        result = validate_csv_schema(csv_file, schema, config)
        assert result is True

    def test_all_matching_modes_combined(self, tmp_path: Path) -> None:
        """Test all matching modes enabled together (maximum flexibility)."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("COL1,Extra1,Extra2\nval1,val2,val3\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=False, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
            ColumnInfo(
                name="col3", data_type="text", is_nullable=True, ordinal_position=3
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        # All permissive modes
        config = PipelineConfig(
            case_insensitive=True, allow_subset=True, ignore_extra=True
        )
        result = validate_csv_schema(csv_file, schema, config)
        assert result is True

    def test_strict_mode_default_behavior(self, tmp_path: Path) -> None:
        """Test default strict mode requires exact column match."""
        test_file = tmp_path / "test.csv"
        test_file.write_text("col1,col2\nval1,val2\n")

        csv_file = CSVFile(file_path=test_file)
        validate_csv_file(csv_file)

        columns = [
            ColumnInfo(
                name="col1", data_type="text", is_nullable=True, ordinal_position=1
            ),
            ColumnInfo(
                name="col2", data_type="text", is_nullable=True, ordinal_position=2
            ),
        ]
        schema = TableSchema(table_name="test_table", columns=columns)

        # Default config (strict mode)
        config = PipelineConfig()
        result = validate_csv_schema(csv_file, schema, config)
        assert result is True
        assert config.case_insensitive is False
        assert config.allow_subset is False
        assert config.ignore_extra is False


class TestEncodingSupport:
    """Tests for CSV encoding support (FR-016, T039d)."""

    def test_csv_file_latin1_encoding(self, tmp_path: Path) -> None:
        """Test CSV file with Latin-1 encoding."""
        csv_path = tmp_path / "latin1.csv"
        # Write Latin-1 encoded content with special characters
        content = "name,city\nJosé,São Paulo\nFrançois,Montréal\n"
        csv_path.write_bytes(content.encode("latin-1"))

        csv_file = CSVFile(file_path=csv_path, encoding="latin-1")

        # Validate can read with correct encoding
        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["name", "city"]
        assert csv_file.row_count == 2
        # Verify special characters preserved
        assert "José" in csv_path.read_text(encoding="latin-1")

    def test_csv_file_windows1252_encoding(self, tmp_path: Path) -> None:
        """Test CSV file with Windows-1252 encoding."""
        csv_path = tmp_path / "windows.csv"
        # Windows-1252 specific: smart quotes, em dash
        content = 'text,note\n"Hello—World","Test"\n'
        csv_path.write_bytes(content.encode("windows-1252"))

        csv_file = CSVFile(file_path=csv_path, encoding="windows-1252")

        result = validate_csv_file(csv_file)

        assert result is True
        assert csv_file.validation_status == ValidationStatus.VALID
        assert csv_file.column_names == ["text", "note"]
        assert csv_file.row_count == 1

    def test_csv_file_encoding_mismatch_error(self, tmp_path: Path) -> None:
        """Test behavior when encoding doesn't match file."""
        csv_path = tmp_path / "latin1.csv"
        content = "name,city\nJosé,São Paulo\n"
        csv_path.write_bytes(content.encode("latin-1"))

        # Try to read with wrong encoding - should raise error or mark invalid
        csv_file = CSVFile(file_path=csv_path, encoding="utf-8")

        # Python's csv module may fail or produce garbage for wrong encoding
        # We expect either ValidationError or invalid status
        try:
            result = validate_csv_file(csv_file)
            # If validation doesn't raise, it should mark as invalid or succeed with replacements
            assert (
                result is False or csv_file.validation_status == ValidationStatus.INVALID
            )
        except (UnicodeDecodeError, ValidationError):
            # Expected behavior for encoding mismatch
            pass
