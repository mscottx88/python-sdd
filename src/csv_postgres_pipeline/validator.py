"""CSV validation functions."""

import csv

from src.csv_postgres_pipeline.exceptions import ValidationError
from src.csv_postgres_pipeline.models import (
    CSVFile,
    PipelineConfig,
    TableSchema,
    ValidationStatus,
)


def validate_csv_file(csv_file: CSVFile) -> bool:
    """Validate CSV file structure and parse headers.

    Args:
        csv_file: CSVFile instance to validate

    Returns:
        True if file is valid, raises ValidationError otherwise

    Side effects:
        - Updates csv_file.column_names with parsed headers
        - Updates csv_file.validation_status to VALID or INVALID
        - Updates csv_file.row_count with number of data rows

    Raises:
        ValidationError: If file cannot be read or parsed

    Example:
        >>> csv_file = CSVFile(Path("data.csv"))
        >>> if validate_csv_file(csv_file):
        ...     print(f"Valid CSV with columns: {csv_file.column_names}")
    """
    csv_file.validation_status = ValidationStatus.VALIDATING

    try:
        # Verify file is readable
        if not csv_file.file_path.exists():
            csv_file.validation_status = ValidationStatus.INVALID
            raise ValidationError(f"File not found: {csv_file.file_path}")

        # Parse CSV and extract headers
        with open(csv_file.file_path, encoding=csv_file.encoding, newline="") as f:
            reader = csv.reader(f, delimiter=csv_file.delimiter)

            try:
                # Read header row
                if csv_file.has_header:
                    header_row: list[str] = next(reader)
                    csv_file.column_names = [col.strip() for col in header_row]

                    if not csv_file.column_names:
                        csv_file.validation_status = ValidationStatus.INVALID
                        raise ValidationError("CSV header row is empty")

                    if len(csv_file.column_names) != len(set(csv_file.column_names)):
                        csv_file.validation_status = ValidationStatus.INVALID
                        raise ValidationError("CSV has duplicate column names")

                # Count data rows and validate column count consistency
                row_count: int = 0
                expected_column_count = (
                    len(csv_file.column_names) if csv_file.has_header else None
                )

                for row_number, row in enumerate(
                    reader, start=2
                ):  # Start at 2 (after header)
                    row_count += 1

                    # Validate column count consistency
                    if expected_column_count is not None:
                        actual_column_count = len(row)
                        if actual_column_count != expected_column_count:
                            csv_file.validation_status = ValidationStatus.INVALID
                            raise ValidationError(
                                f"Malformed CSV file '{csv_file.file_path.name}': "
                                f"inconsistent column count at line {row_number}. "
                                f"Expected {expected_column_count} columns, "
                                f"found {actual_column_count}"
                            )

                csv_file.row_count = row_count

            except StopIteration as exc:
                # Empty file or only header
                csv_file.row_count = 0
                if csv_file.has_header and not csv_file.column_names:
                    csv_file.validation_status = ValidationStatus.INVALID
                    raise ValidationError("CSV file is empty") from exc

        csv_file.validation_status = ValidationStatus.VALID
        return True

    except (OSError, UnicodeDecodeError) as e:
        csv_file.validation_status = ValidationStatus.INVALID
        raise ValidationError(f"Failed to read CSV file: {e}") from e
    except csv.Error as e:
        csv_file.validation_status = ValidationStatus.INVALID
        raise ValidationError(f"Invalid CSV format: {e}") from e


def validate_csv_schema(
    csv_file: CSVFile, table_schema: TableSchema, config: PipelineConfig
) -> bool:
    """Validate CSV columns match database table schema.

    Args:
        csv_file: CSVFile with parsed column names
        table_schema: Target table schema from database
        config: Pipeline configuration with column matching options

    Returns:
        True if schema matches, raises ValidationError otherwise

    Raises:
        ValidationError: If CSV columns don't match table schema

    Example:
        >>> csv_file = CSVFile(Path("data.csv"))
        >>> validate_csv_file(csv_file)
        >>> schema = get_table_schema(db_config, "target_table")
        >>> pipeline_config = PipelineConfig()
        >>> validate_csv_schema(csv_file, schema, pipeline_config)
        True
    """
    if csv_file.validation_status != ValidationStatus.VALID:
        raise ValidationError(
            "CSV file must be validated before schema validation. "
            "Call validate_csv_file() first."
        )

    if not csv_file.column_names:
        raise ValidationError("CSV has no column names")

    # Use TableSchema's built-in validation with config options
    is_valid: bool
    error_message: str | None
    is_valid, error_message = table_schema.validate_csv_columns(
        csv_file.column_names,
        case_insensitive=config.case_insensitive,
        allow_subset=config.allow_subset,
        ignore_extra=config.ignore_extra,
    )

    if not is_valid:
        csv_file.validation_status = ValidationStatus.INVALID
        raise ValidationError(
            f"CSV schema mismatch for table '{table_schema.table_name}': {error_message}"
        )

    return True
