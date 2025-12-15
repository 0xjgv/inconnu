"""Tests for data interfaces: ProcessedData and NERComponent.

This module tests the data structures used throughout Inconnu:
- ProcessedData: Container for redaction results
- NERComponent: Configuration for custom NER components

These are unit tests that don't require spaCy models.
"""

import re

import pytest

from inconnu.nlp.interfaces import NERComponent, ProcessedData


# =============================================================================
# ProcessedData Tests
# =============================================================================


class TestProcessedData:
    """Test the ProcessedData dataclass."""

    @pytest.mark.unit
    def test_basic_construction(self):
        """Test basic ProcessedData construction."""
        data = ProcessedData(
            entity_map={"[PERSON_0]": "John Doe"},
            processing_time_ms=10.5,
            redacted_text="Hello [PERSON_0]",
            original_text="Hello John Doe",
            text_length=14,
            timestamp="2024-01-01T12:00:00",
            hashed_id="abc123",
        )

        assert data.entity_map == {"[PERSON_0]": "John Doe"}
        assert data.processing_time_ms == 10.5
        assert data.redacted_text == "Hello [PERSON_0]"
        assert data.original_text == "Hello John Doe"
        assert data.text_length == 14
        assert data.timestamp == "2024-01-01T12:00:00"
        assert data.hashed_id == "abc123"

    @pytest.mark.unit
    def test_entity_positions_default(self):
        """Test that entity_positions defaults to empty dict."""
        data = ProcessedData(
            entity_map={},
            processing_time_ms=0.0,
            redacted_text="",
            original_text="",
            text_length=0,
            timestamp="",
            hashed_id="",
        )

        assert data.entity_positions == {}

    @pytest.mark.unit
    def test_entity_positions_explicit(self):
        """Test setting entity_positions explicitly."""
        data = ProcessedData(
            entity_map={"[PERSON_0]": "John"},
            processing_time_ms=1.0,
            redacted_text="Hello [PERSON_0]",
            original_text="Hello John",
            text_length=10,
            timestamp="2024-01-01",
            hashed_id="xyz",
            entity_positions={"[PERSON_0]": (6, 16)},
        )

        assert data.entity_positions == {"[PERSON_0]": (6, 16)}

    @pytest.mark.unit
    def test_multiple_entities(self):
        """Test ProcessedData with multiple entities."""
        data = ProcessedData(
            entity_map={
                "[PERSON_0]": "John Doe",
                "[GPE_0]": "New York",
                "[DATE_0]": "yesterday",
            },
            processing_time_ms=25.3,
            redacted_text="[PERSON_0] visited [GPE_0] [DATE_0].",
            original_text="John Doe visited New York yesterday.",
            text_length=36,
            timestamp="2024-01-15T10:30:00",
            hashed_id="def456",
            entity_positions={
                "[PERSON_0]": (0, 10),
                "[GPE_0]": (19, 25),
                "[DATE_0]": (26, 34),
            },
        )

        assert len(data.entity_map) == 3
        assert len(data.entity_positions) == 3

    @pytest.mark.unit
    def test_empty_entity_map(self):
        """Test ProcessedData with no entities (text unchanged)."""
        original = "The quick brown fox."
        data = ProcessedData(
            entity_map={},
            processing_time_ms=5.0,
            redacted_text=original,
            original_text=original,
            text_length=len(original),
            timestamp="2024-01-01",
            hashed_id="empty123",
            entity_positions={},
        )

        assert data.redacted_text == data.original_text
        assert len(data.entity_map) == 0

    @pytest.mark.unit
    def test_mutability(self):
        """Test that ProcessedData fields can be modified after creation."""
        data = ProcessedData(
            entity_map={},
            processing_time_ms=0.0,
            redacted_text="",
            original_text="",
            text_length=0,
            timestamp="",
            hashed_id="",
        )

        # Modify fields
        data.entity_map = {"[PERSON_0]": "Test"}
        data.redacted_text = "Hello [PERSON_0]"
        data.entity_positions = {"[PERSON_0]": (6, 16)}

        assert data.entity_map == {"[PERSON_0]": "Test"}
        assert data.redacted_text == "Hello [PERSON_0]"
        assert data.entity_positions == {"[PERSON_0]": (6, 16)}


# =============================================================================
# NERComponent Tests
# =============================================================================


class TestNERComponent:
    """Test the NERComponent NamedTuple."""

    @pytest.mark.unit
    def test_pattern_only_component(self):
        """Test NERComponent with only a pattern."""
        component = NERComponent(
            label="EMAIL",
            pattern=re.compile(r"\S+@\S+"),
        )

        assert component.label == "EMAIL"
        assert component.pattern is not None
        assert component.processing_func is None
        assert component.before_ner is True  # Default

    @pytest.mark.unit
    def test_function_only_component(self):
        """Test NERComponent with only a processing function."""

        def custom_processor(doc):
            return doc

        component = NERComponent(
            label="CUSTOM",
            processing_func=custom_processor,
        )

        assert component.label == "CUSTOM"
        assert component.pattern is None
        assert component.processing_func is custom_processor
        assert component.before_ner is True

    @pytest.mark.unit
    def test_before_ner_false(self):
        """Test NERComponent that runs after NER."""
        component = NERComponent(
            label="POST_PROCESS",
            processing_func=lambda doc: doc,
            before_ner=False,
        )

        assert component.before_ner is False

    @pytest.mark.unit
    def test_named_tuple_access(self):
        """Test NamedTuple field access."""
        component = NERComponent(
            label="TEST",
            pattern=re.compile(r"\d+"),
            before_ner=True,
        )

        # Access by name
        assert component.label == "TEST"

        # Access by index
        assert component[0] == "TEST"

        # Unpack
        label, func, pattern, before = component
        assert label == "TEST"
        assert func is None
        assert pattern is not None
        assert before is True

    @pytest.mark.unit
    def test_asdict_method(self):
        """Test converting NERComponent to dict."""
        component = NERComponent(
            label="PHONE",
            pattern=re.compile(r"\d{3}-\d{4}"),
        )

        d = component._asdict()

        assert d["label"] == "PHONE"
        assert d["pattern"] is not None
        assert d["processing_func"] is None
        assert d["before_ner"] is True

    @pytest.mark.unit
    def test_immutability(self):
        """Test that NERComponent is immutable (NamedTuple)."""
        component = NERComponent(
            label="TEST",
            pattern=re.compile(r"test"),
        )

        with pytest.raises(AttributeError):
            component.label = "CHANGED"


# =============================================================================
# Integration Tests
# =============================================================================


class TestInterfacesIntegration:
    """Test interfaces work together correctly."""

    @pytest.mark.unit
    def test_processed_data_with_ner_component_labels(self):
        """Test that ProcessedData can store entities from NERComponent labels."""
        # Define components
        components = [
            NERComponent(label="CUSTOM_EMAIL", pattern=re.compile(r"\S+@\S+")),
            NERComponent(label="CUSTOM_PHONE", pattern=re.compile(r"\d{3}-\d{4}")),
        ]

        # Create ProcessedData with those labels
        data = ProcessedData(
            entity_map={
                "[CUSTOM_EMAIL_0]": "test@example.com",
                "[CUSTOM_PHONE_0]": "555-1234",
            },
            processing_time_ms=10.0,
            redacted_text="Contact [CUSTOM_EMAIL_0] or [CUSTOM_PHONE_0]",
            original_text="Contact test@example.com or 555-1234",
            text_length=37,
            timestamp="2024-01-01",
            hashed_id="int123",
            entity_positions={
                "[CUSTOM_EMAIL_0]": (8, 24),
                "[CUSTOM_PHONE_0]": (28, 44),
            },
        )

        # Verify labels match component definitions
        for comp in components:
            placeholder = f"[{comp.label}_0]"
            assert placeholder in data.entity_map
            assert placeholder in data.entity_positions

    @pytest.mark.unit
    def test_position_verification(self):
        """Test that positions correctly map to redacted text."""
        data = ProcessedData(
            entity_map={
                "[PERSON_0]": "Alice",
                "[ORG_0]": "Acme Corp",
            },
            processing_time_ms=5.0,
            redacted_text="[PERSON_0] works at [ORG_0].",
            original_text="Alice works at Acme Corp.",
            text_length=25,
            timestamp="2024-01-01",
            hashed_id="pos123",
            entity_positions={
                "[PERSON_0]": (0, 10),
                "[ORG_0]": (20, 27),
            },
        )

        # Verify positions match
        for placeholder, (start, end) in data.entity_positions.items():
            actual = data.redacted_text[start:end]
            assert actual == placeholder, (
                f"Position mismatch: expected '{placeholder}' at {start}:{end}, "
                f"got '{actual}'"
            )
