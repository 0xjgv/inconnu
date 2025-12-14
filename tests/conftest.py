"""Shared test fixtures and configuration for the Inconnu test suite.

This module provides:
- Pytest markers for categorizing tests
- Language-specific Inconnu instance fixtures
- Mock fixtures for unit testing without spaCy models
- Test data fixtures
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inconnu import Config, Inconnu
from inconnu.nlp.interfaces import ProcessedData

# =============================================================================
# Test Data Paths
# =============================================================================

MOCKS_PATH = Path("tests/mocks")


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_model: mark test as requiring a spaCy model"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )


# =============================================================================
# Text Data Fixtures
# =============================================================================


@pytest.fixture
def de_prompt() -> str:
    """German prompt fixture for testing German language processing."""
    with Path(MOCKS_PATH / "de_prompt.txt").open("r") as file:
        return file.read()


@pytest.fixture
def en_prompt() -> str:
    """English prompt fixture for testing English language processing."""
    with Path(MOCKS_PATH / "en_prompt.txt").open("r", encoding="utf-8") as file:
        return file.read()


@pytest.fixture
def simple_text() -> str:
    """Simple English text with common entities."""
    return "John Doe visited New York last summer."


@pytest.fixture
def multiple_entities_text() -> str:
    """Text with multiple entity types for comprehensive testing."""
    return (
        "John Doe from New York visited Paris last summer. "
        "Jane Smith from California attended a conference in Tokyo in March. "
        "Dr. Alice Johnson from Texas gave a lecture in London last week."
    )


@pytest.fixture
def text_with_pii() -> str:
    """Text containing various PII types."""
    return (
        "Contact John Doe at john.doe@example.com or call +1-555-123-4567. "
        "His SSN is 123-45-6789 and IBAN is DE89370400440532013000."
    )


@pytest.fixture
def text_with_placeholder_like_content() -> str:
    """Text that contains placeholder-like strings (edge case for de-anonymization)."""
    return "The code uses [PERSON_0] as a variable name. John Doe wrote it."


@pytest.fixture
def structured_output() -> list[dict[str, str]]:
    """Expected structured output for multiple_entities_text fixture."""
    return [
        {
            "Person": "[PERSON_0]",
            "Origin": "[GPE_0]",
            "Event": "Visit",
            "Location": "[GPE_1]",
            "Date": "[DATE_0]",
        },
        {
            "Person": "[PERSON_1]",
            "Origin": "[GPE_2]",
            "Event": "Conference Attendance",
            "Location": "[GPE_3]",
            "Date": "[DATE_1]",
        },
        {
            "Person": "[PERSON_2]",
            "Origin": "[GPE_4]",
            "Event": "Lecture",
            "Location": "[GPE_5]",
            "Date": "[DATE_2]",
        },
    ]


# =============================================================================
# Inconnu Instance Fixtures (require spaCy models)
# =============================================================================


@pytest.fixture
def inconnu_en() -> Inconnu:
    """English Inconnu instance with default configuration."""
    return Inconnu(
        config=Config(
            data_retention_days=30,
            max_text_length=75_000,
        ),
        language="en",
    )


@pytest.fixture
def inconnu_de() -> Inconnu:
    """German Inconnu instance with default configuration."""
    return Inconnu(
        config=Config(
            data_retention_days=30,
            max_text_length=10_000,
        ),
        language="de",
    )


@pytest.fixture
def inconnu_it() -> Inconnu:
    """Italian Inconnu instance with default configuration."""
    return Inconnu(
        config=Config(
            data_retention_days=30,
            max_text_length=10_000,
        ),
        language="it",
    )


@pytest.fixture
def inconnu_with_small_limit() -> Inconnu:
    """Inconnu instance with small text length limit for error testing."""
    return Inconnu(
        config=Config(
            data_retention_days=30,
            max_text_length=100,
        ),
        language="en",
    )


# =============================================================================
# Mock Fixtures for Unit Testing
# =============================================================================


@pytest.fixture
def mock_processed_data() -> ProcessedData:
    """Pre-built ProcessedData for testing de-anonymization logic."""
    return ProcessedData(
        entity_map={
            "[PERSON_0]": "John Doe",
            "[GPE_0]": "New York",
            "[DATE_0]": "last summer",
        },
        processing_time_ms=10.5,
        redacted_text="[PERSON_0] visited [GPE_0] [DATE_0].",
        original_text="John Doe visited New York last summer.",
        text_length=39,
        timestamp="2024-01-01T12:00:00",
        hashed_id="abc123def456",
        entity_positions={
            "[PERSON_0]": (0, 10),
            "[GPE_0]": (19, 25),
            "[DATE_0]": (26, 34),
        },
    )


@pytest.fixture
def mock_processed_data_no_positions() -> ProcessedData:
    """ProcessedData without positions for backward compatibility testing."""
    return ProcessedData(
        entity_map={
            "[PERSON_0]": "John Doe",
            "[GPE_0]": "New York",
        },
        processing_time_ms=10.5,
        redacted_text="[PERSON_0] visited [GPE_0].",
        original_text="John Doe visited New York.",
        text_length=26,
        timestamp="2024-01-01T12:00:00",
        hashed_id="abc123def456",
        entity_positions={},  # Empty - simulates old ProcessedData
    )


@pytest.fixture
def mock_nlp():
    """Mock spaCy NLP pipeline for unit testing without loading models."""
    mock = MagicMock()
    mock.return_value.ents = []
    return mock


# =============================================================================
# Config Fixtures
# =============================================================================


@pytest.fixture
def default_config() -> Config:
    """Default configuration for testing."""
    return Config(
        data_retention_days=30,
        max_text_length=75_000,
    )


@pytest.fixture
def strict_config() -> Config:
    """Strict configuration with error logging enabled."""
    return Config(
        data_retention_days=30,
        max_text_length=75_000,
        error_mode="strict",
        log_errors=True,
    )
