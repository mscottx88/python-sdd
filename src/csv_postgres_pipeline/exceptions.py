"""Custom exception classes for csv_postgres_pipeline."""


class CSVPipelineError(Exception):
    """Base exception for all CSV pipeline errors."""


class ValidationError(CSVPipelineError):
    """Raised when CSV validation fails."""


class DatabaseError(CSVPipelineError):
    """Raised when database operations fail."""


class FileProcessingError(CSVPipelineError):
    """Raised when file processing fails."""


class ConfigurationError(CSVPipelineError):
    """Raised when configuration is invalid."""
