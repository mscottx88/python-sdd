"""
Test configuration and shared fixtures.

This file is automatically discovered by pytest and provides
configuration and fixtures available to all tests.
"""

import logging
import os
import re
import subprocess
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from psycopg import connect, sql
from psycopg.conninfo import make_conninfo
from psycopg_pool import ConnectionPool

# Load environment variables from .env file before any tests run
load_dotenv()


def _validate_container_name(name: str) -> None:
    """Validate container name contains only safe characters.

    Prevents command injection by ensuring container names only contain
    alphanumeric characters, hyphens, and underscores.
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        raise ValueError(
            f"Invalid container name '{name}'. "
            "Must contain only alphanumeric characters, hyphens, and underscores."
        )


def pytest_configure(config):
    """Register custom markers and verify test environment infrastructure."""
    # Skip Docker checks in CI environments (GitHub Actions, etc.)
    skip_docker_check = os.getenv("SKIP_DOCKER_CHECK", "").lower() in (
        "true",
        "1",
        "yes",
    )

    if not skip_docker_check:
        # Verify Docker Desktop is running
        try:
            result = subprocess.run(  # noqa: S603  # Docker command is hardcoded, no user input
                ["docker", "info"],  # noqa: S607  # Docker is system-installed via PATH
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
        except FileNotFoundError:
            pytest.exit(
                "Docker is not installed or not in PATH.\n"
                "Install Docker Desktop: https://www.docker.com/products/docker-desktop",
                returncode=1,
            )
        except subprocess.CalledProcessError:
            pytest.exit(
                "Docker Desktop is not running.\n"
                "Start Docker Desktop and wait for it to be ready, then retry.",
                returncode=1,
            )
        except subprocess.TimeoutExpired:
            pytest.exit(
                "Docker command timed out. Docker Desktop may be starting up.\n"
                "Wait for Docker Desktop to be fully ready, then retry.",
                returncode=1,
            )

        # Check database container is running
        db_container_name = os.getenv("DB_CONTAINER_NAME", "python-sdd-db-1")
        _validate_container_name(db_container_name)  # Prevent injection attacks

        try:
            result = subprocess.run(  # noqa: S603  # Input validated above
                [  # noqa: S607  # Docker is system-installed via PATH
                    "docker",
                    "ps",
                    "--filter",
                    f"name={db_container_name}",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            if not result.stdout.strip():
                pytest.exit(
                    f"Database container '{db_container_name}' is not running.\n"
                    f"Start the container: docker-compose up -d\n"
                    f"Or check container name matches DB_CONTAINER_NAME env variable.",
                    returncode=1,
                )
        except subprocess.CalledProcessError as e:
            pytest.exit(
                f"Failed to check database container status: {e}\n"
                f"Ensure Docker Desktop is running and try: docker ps",
                returncode=1,
            )

    # Verify database connection (quick connectivity check)
    test_db_host = os.getenv("PGHOST", "localhost")
    test_db_port = os.getenv("PGPORT", "5433")
    try:
        conninfo = make_conninfo(
            host=test_db_host,
            port=int(test_db_port),
            dbname=os.getenv("PGDATABASE", "test_csv_pipeline"),
            user=os.getenv("PGUSER", "test_user"),
            password=os.getenv("PGPASSWORD", "test_password"),
            connect_timeout=5,
        )
        with connect(conninfo) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
    except (OSError, ConnectionError) as e:
        pytest.exit(
            f"Cannot connect to test database at {test_db_host}:{test_db_port}\n"
            f"Error: {e}\n"
            f"Check: docker-compose up -d && docker ps\n"
            f"Verify PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD environment variables.",
            returncode=1,
        )

    if skip_docker_check:
        print("\\n[OK] Test environment verified: CI mode, database connection available")
    else:
        print(
            "\\n[OK] Test environment verified: Docker Desktop running, database container available"
        )

    config.addinivalue_line(
        "markers", "integration: Integration tests requiring database"
    )
    config.addinivalue_line("markers", "contract: Contract tests for external APIs")
    config.addinivalue_line("markers", "unit: Unit tests for individual functions")


# Test database configuration from environment or defaults
TEST_DB_CONFIG = {
    "host": os.getenv("TEST_DB_HOST", "localhost"),
    "port": int(os.getenv("TEST_DB_PORT", "5432")),
    "database": os.getenv("TEST_DB_NAME", "test_csv_pipeline"),
    "user": os.getenv("TEST_DB_USER", "test_user"),
    "password": os.getenv("TEST_DB_PASSWORD", "test_password"),
}


@pytest.fixture(scope="session")
def test_db_config():
    """Provide test database configuration for all tests."""
    return TEST_DB_CONFIG


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def fixtures_dir():
    """Return the integration test fixtures directory."""
    return Path(__file__).parent / "integration" / "fixtures"


# Integration test database fixtures (hoisted from individual test files)


@pytest.fixture
def db_config() -> dict[str, Any]:
    """Database configuration for integration tests from PostgreSQL environment variables.

    Uses PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD environment variables.
    """
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", "5433")),
        "dbname": os.environ.get("PGDATABASE", "test_csv_pipeline"),
        "username": os.environ.get("PGUSER", "test_user"),
        "password": os.environ.get("PGPASSWORD", "test_password"),
        "connection_timeout": 30,
        "command_timeout": None,
        "pool_min_size": 1,
        "pool_max_size": 10,
    }


@pytest.fixture
def test_table_name() -> str:
    """Generate unique test table name to avoid conflicts between parallel tests."""
    timestamp = str(int(time.time() * 1000))
    return f"test_table_{timestamp}"


@pytest.fixture
def create_test_table(db_config: dict[str, Any], test_table_name: str) -> Generator[str]:
    """Create a test table matching valid_1000_rows.csv schema (customer data).

    Schema: customer_id (INT PK), first_name (TEXT), last_name (TEXT),
            email (TEXT), created_at (TIMESTAMP)

    Automatically cleans up table after test completion.
    """
    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            # Create table matching valid_1000_rows.csv schema
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE {} (
                    customer_id INTEGER PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    created_at TIMESTAMP
                )
            """
                ).format(sql.Identifier(test_table_name))
            )
            conn.commit()

        yield test_table_name

        # Cleanup
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(test_table_name))
            )
            conn.commit()
    finally:
        pool.close()


@pytest.fixture
def create_typed_test_table(
    db_config: dict[str, Any], test_table_name: str
) -> Generator[str]:
    """Create a test table with typed columns for error handling tests.

    Schema: id (INT PK), name (TEXT), age (INT), salary (NUMERIC(10,2))

    Used for testing type mismatch errors. Automatically cleans up after test.
    """
    conninfo = make_conninfo(
        host=db_config["host"],
        port=db_config["port"],
        dbname=db_config["dbname"],
        user=db_config["username"],
        password=db_config["password"],
    )
    pool = ConnectionPool(conninfo, min_size=1, max_size=2)
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            # Create table with typed columns for type mismatch testing
            cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE {} (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        age INTEGER NOT NULL,
                        salary NUMERIC(10, 2)
                    )
                    """
                ).format(sql.Identifier(test_table_name))
            )
            conn.commit()

        yield test_table_name
    finally:
        # Cleanup
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(test_table_name))
            )
            conn.commit()
        pool.close()


@pytest.fixture(autouse=True)
def setup_test_logger():
    """Setup logger for tests to work with caplog.

    This fixture removes the default stderr handler that interferes with caplog,
    allowing pytest's caplog fixture to properly capture log records.
    """
    logger = logging.getLogger("csv_postgres_pipeline")
    # Clear any existing handlers
    logger.handlers.clear()
    # Set level but don't add handlers - let caplog handle it
    logger.setLevel(logging.DEBUG)
    logger.propagate = True  # Allow propagation to root logger for caplog

    yield

    # Cleanup after test
    logger.handlers.clear()
    logger.propagate = False
