"""Tests for the EntityRedactor class.

This module tests the EntityRedactor component directly:
- Entity detection and redaction
- Position tracking
- De-anonymization logic
- Error handling
- Custom component handling

Most tests require spaCy models to be loaded.
"""

import logging
import re
from unittest.mock import MagicMock, patch

import pytest

from inconnu import ProcessingError
from inconnu.nlp.entity_redactor import EntityRedactor
from inconnu.nlp.interfaces import NERComponent, ProcessedData


# =============================================================================
# Basic Redaction Tests
# =============================================================================


class TestBasicRedaction:
    """Test basic redaction functionality."""

    @pytest.mark.requires_model
    def test_redact_returns_three_values(self):
        """Test that redact returns (text, entity_map, entity_positions)."""
        redactor = EntityRedactor(language="en")
        text = "John Doe visited New York."

        result = redactor.redact(text=text, deanonymize=True)

        assert len(result) == 3
        redacted_text, entity_map, entity_positions = result
        assert isinstance(redacted_text, str)
        assert isinstance(entity_map, dict)
        assert isinstance(entity_positions, dict)

    @pytest.mark.requires_model
    def test_anonymize_mode(self):
        """Test redaction without de-anonymization (generic placeholders)."""
        redactor = EntityRedactor(language="en")
        text = "John Doe and Jane Smith met."

        redacted_text, entity_map, _ = redactor.redact(text=text, deanonymize=False)

        # Should use generic [PERSON] not [PERSON_0], [PERSON_1]
        assert "[PERSON]" in redacted_text
        assert "[PERSON_0]" not in redacted_text
        # Entity map should be empty in anonymize mode
        assert entity_map == {}

    @pytest.mark.requires_model
    def test_pseudonymize_mode(self):
        """Test redaction with de-anonymization (indexed placeholders)."""
        redactor = EntityRedactor(language="en")
        text = "John Doe and Jane Smith met."

        redacted_text, entity_map, _ = redactor.redact(text=text, deanonymize=True)

        # Should use indexed placeholders
        assert "[PERSON_0]" in redacted_text or "[PERSON_1]" in redacted_text
        # Entity map should have mappings
        assert len(entity_map) > 0

    @pytest.mark.requires_model
    def test_empty_text(self):
        """Test redaction of empty text."""
        redactor = EntityRedactor(language="en")

        redacted_text, entity_map, entity_positions = redactor.redact(
            text="", deanonymize=True
        )

        assert redacted_text == ""
        assert entity_map == {}
        assert entity_positions == {}

    @pytest.mark.requires_model
    def test_no_entities_text(self):
        """Test text with no recognizable entities."""
        redactor = EntityRedactor(language="en")
        text = "The quick brown fox jumps over the lazy dog."

        redacted_text, entity_map, entity_positions = redactor.redact(
            text=text, deanonymize=True
        )

        assert redacted_text == text
        assert entity_map == {}
        assert entity_positions == {}


# =============================================================================
# Position Tracking Tests
# =============================================================================


class TestPositionTracking:
    """Test that entity positions are tracked correctly."""

    @pytest.mark.requires_model
    def test_single_entity_position(self):
        """Test position tracking for a single entity."""
        redactor = EntityRedactor(language="en")
        text = "Hello John Doe!"

        redacted_text, entity_map, entity_positions = redactor.redact(
            text=text, deanonymize=True
        )

        # Find the PERSON placeholder
        person_placeholders = [p for p in entity_map if "PERSON" in p]
        assert len(person_placeholders) >= 1

        placeholder = person_placeholders[0]
        if placeholder in entity_positions:
            start, end = entity_positions[placeholder]
            assert redacted_text[start:end] == placeholder

    @pytest.mark.requires_model
    def test_multiple_entity_positions(self):
        """Test position tracking for multiple entities."""
        redactor = EntityRedactor(language="en")
        text = "John Doe visited New York last summer."

        redacted_text, entity_map, entity_positions = redactor.redact(
            text=text, deanonymize=True
        )

        # Verify all positions are correct
        for placeholder, (start, end) in entity_positions.items():
            actual = redacted_text[start:end]
            assert actual == placeholder, (
                f"Position mismatch: expected '{placeholder}' at {start}:{end}, "
                f"got '{actual}'"
            )

    @pytest.mark.requires_model
    def test_position_offsets_calculated_correctly(self):
        """Test that position offsets account for placeholder length changes."""
        redactor = EntityRedactor(language="en")
        # "John Doe" (8 chars) -> "[PERSON_0]" (10 chars) = +2 offset
        # "New York" (8 chars) -> "[GPE_0]" (7 chars) = -1 offset
        text = "John Doe visited New York."

        redacted_text, _, entity_positions = redactor.redact(
            text=text, deanonymize=True
        )

        # All positions should be valid in the redacted text
        for placeholder, (start, end) in entity_positions.items():
            assert 0 <= start < len(redacted_text)
            assert 0 < end <= len(redacted_text)
            assert start < end


# =============================================================================
# De-anonymization Tests
# =============================================================================


class TestDeanonymization:
    """Test the deanonymize method."""

    @pytest.mark.requires_model
    def test_basic_deanonymize(self):
        """Test basic de-anonymization restores original text."""
        redactor = EntityRedactor(language="en")
        original = "John Doe visited New York."

        redacted_text, entity_map, entity_positions = redactor.redact(
            text=original, deanonymize=True
        )

        processed_data = ProcessedData(
            entity_map=entity_map,
            processing_time_ms=0.0,
            redacted_text=redacted_text,
            original_text=original,
            text_length=len(original),
            timestamp="",
            hashed_id="",
            entity_positions=entity_positions,
        )

        restored = redactor.deanonymize(processed_data=processed_data)
        assert restored == original

    @pytest.mark.requires_model
    def test_deanonymize_with_positions(self):
        """Test position-based de-anonymization."""
        redactor = EntityRedactor(language="en")
        original = "Alice and Bob met in Paris."

        redacted_text, entity_map, entity_positions = redactor.redact(
            text=original, deanonymize=True
        )

        processed_data = ProcessedData(
            entity_map=entity_map,
            processing_time_ms=0.0,
            redacted_text=redacted_text,
            original_text=original,
            text_length=len(original),
            timestamp="",
            hashed_id="",
            entity_positions=entity_positions,
        )

        restored = redactor.deanonymize(processed_data=processed_data)
        assert restored == original

    @pytest.mark.unit
    def test_deanonymize_without_positions_fallback(self):
        """Test fallback to string replacement when no positions."""
        redactor = EntityRedactor(language="en")

        # Create ProcessedData without positions
        processed_data = ProcessedData(
            entity_map={
                "[PERSON_0]": "John Doe",
                "[GPE_0]": "New York",
            },
            processing_time_ms=0.0,
            redacted_text="[PERSON_0] visited [GPE_0].",
            original_text="John Doe visited New York.",
            text_length=26,
            timestamp="",
            hashed_id="",
            entity_positions={},  # Empty - use fallback
        )

        restored = redactor.deanonymize(processed_data=processed_data)

        assert "John Doe" in restored
        assert "New York" in restored
        assert "[PERSON_0]" not in restored
        assert "[GPE_0]" not in restored

    @pytest.mark.unit
    def test_deanonymize_position_mismatch_warning(self, caplog):
        """Test warning when position doesn't match expected placeholder."""
        redactor = EntityRedactor(language="en")

        # Create ProcessedData with incorrect positions
        processed_data = ProcessedData(
            entity_map={"[PERSON_0]": "John"},
            processing_time_ms=0.0,
            redacted_text="Modified: [PERSON_0] here",
            original_text="",
            text_length=0,
            timestamp="",
            hashed_id="",
            entity_positions={"[PERSON_0]": (0, 10)},  # Wrong position
        )

        with caplog.at_level(logging.WARNING):
            restored = redactor.deanonymize(processed_data=processed_data)

        # Should still restore via fallback
        assert "John" in restored
        # Should log a warning
        assert "Position mismatch" in caplog.text or "[PERSON_0]" not in restored


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling in EntityRedactor."""

    @pytest.mark.unit
    def test_nlp_failure_raises_processing_error(self):
        """Test that NLP failures raise ProcessingError."""
        redactor = EntityRedactor(language="en")

        with patch.object(
            redactor, "nlp", side_effect=RuntimeError("NLP failed")
        ):
            with pytest.raises(ProcessingError) as exc_info:
                redactor.redact(text="Test text", deanonymize=True)

            assert "SpaCy NLP processing failed" in str(exc_info.value)
            assert "NLP failed" in str(exc_info.value)

    @pytest.mark.unit
    def test_nlp_failure_preserves_original_error(self):
        """Test that original error is preserved in ProcessingError."""
        redactor = EntityRedactor(language="en")
        original_error = ValueError("Original error message")

        with patch.object(redactor, "nlp", side_effect=original_error):
            with pytest.raises(ProcessingError) as exc_info:
                redactor.redact(text="Test", deanonymize=True)

            assert exc_info.value.original_error is original_error


# =============================================================================
# Custom Component Tests
# =============================================================================


class TestCustomComponents:
    """Test custom NER component functionality."""

    @pytest.mark.requires_model
    def test_add_pattern_component(self):
        """Test adding a pattern-based custom component."""
        redactor = EntityRedactor(language="en")

        redactor.add_custom_components([
            NERComponent(
                label="CUSTOM_ID",
                pattern=re.compile(r"ID-\d{5}"),
                before_ner=True,
            )
        ])

        text = "Reference: ID-12345"
        redacted_text, entity_map, _ = redactor.redact(text=text, deanonymize=True)

        assert "[CUSTOM_ID_0]" in redacted_text
        assert entity_map.get("[CUSTOM_ID_0]") == "ID-12345"

    @pytest.mark.requires_model
    def test_component_before_ner(self):
        """Test component that runs before NER."""
        redactor = EntityRedactor(language="en")

        # Component that runs before NER
        redactor.add_custom_components([
            NERComponent(
                label="BEFORE_NER",
                pattern=re.compile(r"BEFORE-\w+"),
                before_ner=True,
            )
        ])

        text = "Code: BEFORE-TEST"
        redacted_text, entity_map, _ = redactor.redact(text=text, deanonymize=True)

        assert "[BEFORE_NER_0]" in redacted_text


# =============================================================================
# Singleton Tests
# =============================================================================


class TestSingleton:
    """Test EntityRedactor singleton behavior."""

    @pytest.mark.requires_model
    def test_same_language_returns_same_instance(self):
        """Test that same language returns same instance."""
        redactor1 = EntityRedactor(language="en")
        redactor2 = EntityRedactor(language="en")

        # Should be the same instance (singleton per language)
        assert redactor1 is redactor2

    @pytest.mark.requires_model
    def test_different_languages_different_instances(self):
        """Test that different languages create different instances."""
        redactor_en = EntityRedactor(language="en")
        redactor_de = EntityRedactor(language="de")

        # Should be different instances
        assert redactor_en is not redactor_de
        assert redactor_en.nlp is not redactor_de.nlp
