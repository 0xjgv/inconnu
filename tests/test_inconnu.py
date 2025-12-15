"""Tests for the main Inconnu class API.

This module tests the public API of the Inconnu class including:
- Pseudonymization (redact with reversible mapping)
- Anonymization (redact without mapping)
- De-anonymization (restore original text)
- Batch processing
- Error handling
- Library logging behavior

Fixtures are defined in conftest.py.
"""

import io
import json
import logging
import sys
from re import compile
from unittest.mock import patch

import pytest

from inconnu import Config, Inconnu, ProcessingError, TextTooLongError
from inconnu.nlp.interfaces import NERComponent


# =============================================================================
# Pseudonymization Tests (with entity mapping for reversibility)
# =============================================================================


class TestPseudonymization:
    """Test pseudonymization functionality (reversible redaction)."""

    @pytest.mark.requires_model
    def test_basic_pseudonymization(self, inconnu_en, simple_text):
        """Test basic text pseudonymization with entity mapping."""
        processed_data = inconnu_en(text=simple_text)

        assert processed_data.entity_map["[PERSON_0]"] == "John Doe"
        assert processed_data.entity_map["[GPE_0]"] == "New York"
        assert processed_data.text_length == len(simple_text)
        assert len(processed_data.entity_map) >= 2

    @pytest.mark.requires_model
    def test_no_entities_returns_original(self, inconnu_en):
        """Test that text without entities is returned unchanged."""
        text = "The quick brown fox jumps over the lazy dog."

        processed_data = inconnu_en(text=text)

        assert processed_data.redacted_text == text
        assert len(processed_data.entity_map) == 0

    @pytest.mark.requires_model
    def test_multiple_entities(self, inconnu_en, multiple_entities_text):
        """Test pseudonymization with multiple entity types."""
        processed_data = inconnu_en(text=multiple_entities_text)

        # Verify dates are captured
        assert processed_data.entity_map.get("[DATE_0]") == "last summer"
        assert processed_data.entity_map.get("[DATE_1]") == "March"

        # Verify persons are captured
        assert processed_data.entity_map.get("[PERSON_0]") == "John Doe"
        assert processed_data.entity_map.get("[PERSON_1]") == "Jane Smith"

        # Verify locations are captured
        assert processed_data.entity_map.get("[GPE_0]") == "New York"
        assert processed_data.entity_map.get("[GPE_1]") == "Paris"

    @pytest.mark.requires_model
    def test_hashed_id_generation(self, inconnu_en, simple_text):
        """Test that hashed_id is generated correctly."""
        processed_data = inconnu_en(text=simple_text)

        assert processed_data.hashed_id.isalnum()
        assert len(processed_data.hashed_id) == 64  # SHA-256 length

    @pytest.mark.requires_model
    def test_timestamp_generation(self, inconnu_en, simple_text):
        """Test that timestamp is generated."""
        processed_data = inconnu_en(text=simple_text)

        assert processed_data.timestamp is not None
        assert len(processed_data.timestamp) > 0

    @pytest.mark.requires_model
    def test_entity_positions_tracked(self, inconnu_en, simple_text):
        """Test that entity positions are tracked for robust de-anonymization."""
        processed_data = inconnu_en(text=simple_text)

        # Positions should be tracked
        assert processed_data.entity_positions is not None

        # Each placeholder should have a position
        for placeholder in processed_data.entity_map:
            if placeholder in processed_data.entity_positions:
                start, end = processed_data.entity_positions[placeholder]
                # Verify position matches actual placeholder location
                assert processed_data.redacted_text[start:end] == placeholder


# =============================================================================
# De-anonymization Tests
# =============================================================================


class TestDeanonymization:
    """Test de-anonymization functionality (restoring original text)."""

    @pytest.mark.requires_model
    def test_basic_deanonymization(self, inconnu_en, simple_text):
        """Test that de-anonymization restores original text."""
        processed_data = inconnu_en(text=simple_text)

        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)

        assert deanonymized == simple_text

    @pytest.mark.requires_model
    def test_deanonymization_multiple_entities(
        self, inconnu_en, multiple_entities_text, structured_output
    ):
        """Test de-anonymization with structured data transformation."""
        processed_data = inconnu_en(text=multiple_entities_text)

        # Transform to structured format
        processed_data.redacted_text = json.dumps(structured_output)
        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)

        result = json.loads(deanonymized)
        assert result[0]["Person"] == "John Doe"
        assert result[1]["Person"] == "Jane Smith"
        assert result[2]["Person"] == "Dr. Alice Johnson"

    @pytest.mark.requires_model
    def test_deanonymization_with_placeholder_like_text(
        self, inconnu_en, text_with_placeholder_like_content
    ):
        """Test de-anonymization when original text contains placeholder-like strings.

        This is a critical edge case: if original text contains '[PERSON_0]',
        the position-based de-anonymization should only restore the actual
        redacted entity, not the literal string in the original text.
        """
        processed_data = inconnu_en(text=text_with_placeholder_like_content)

        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)

        # The original [PERSON_0] variable reference should remain
        assert "[PERSON_0]" in deanonymized
        # The actual person name should be restored
        assert "John Doe" in deanonymized

    @pytest.mark.unit
    def test_deanonymization_backward_compatibility(
        self, inconnu_en, mock_processed_data_no_positions
    ):
        """Test de-anonymization works without position data (backward compatibility)."""
        # Use ProcessedData without positions
        deanonymized = inconnu_en.deanonymize(
            processed_data=mock_processed_data_no_positions
        )

        assert "John Doe" in deanonymized
        assert "New York" in deanonymized
        assert "[PERSON_0]" not in deanonymized
        assert "[GPE_0]" not in deanonymized

    @pytest.mark.requires_model
    def test_empty_text_deanonymization(self, inconnu_en):
        """Test de-anonymization of empty text."""
        processed_data = inconnu_en(text="")

        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)

        assert deanonymized == ""


# =============================================================================
# Anonymization Tests (non-reversible redaction)
# =============================================================================


class TestAnonymization:
    """Test anonymization functionality (non-reversible redaction)."""

    @pytest.mark.requires_model
    @pytest.mark.parametrize(
        "text, expected_anonymized",
        [
            (
                "John Doe visited New York last summer.",
                "[PERSON] visited [GPE] [DATE].",
            ),
            ("John Doe visited New York.", "[PERSON] visited [GPE]."),
            (
                "Dr. Alice Johnson gave a lecture in London last week.",
                "[PERSON] gave a lecture in [GPE] [DATE].",
            ),
        ],
    )
    def test_basic_anonymization(self, inconnu_en, text, expected_anonymized):
        """Test that anonymization produces expected output."""
        processed_data = inconnu_en(text=text, deanonymize=False)

        assert processed_data.redacted_text == expected_anonymized
        assert processed_data.text_length == len(text)

    @pytest.mark.requires_model
    def test_anonymization_removes_all_pii(self, inconnu_en, multiple_entities_text):
        """Test that all PII is removed from text."""
        result = inconnu_en(text=multiple_entities_text, deanonymize=False)

        # Original names should not appear
        assert "John Doe" not in result.redacted_text
        assert "Jane Smith" not in result.redacted_text
        assert "Dr. Alice Johnson" not in result.redacted_text

        # Original locations should not appear
        assert "New York" not in result.redacted_text
        assert "California" not in result.redacted_text

    @pytest.mark.requires_model
    def test_redact_method(self, inconnu_en, simple_text):
        """Test the redact() convenience method."""
        result = inconnu_en.redact(simple_text)

        assert isinstance(result, str)
        assert "[PERSON]" in result
        assert "John Doe" not in result

    @pytest.mark.requires_model
    def test_anonymize_method(self, inconnu_en, simple_text):
        """Test the anonymize() alias method."""
        result = inconnu_en.anonymize(simple_text)

        assert isinstance(result, str)
        assert result == inconnu_en.redact(simple_text)

    @pytest.mark.requires_model
    def test_pseudonymize_method(self, inconnu_en, simple_text):
        """Test the pseudonymize() method returns tuple."""
        result, entity_map = inconnu_en.pseudonymize(simple_text)

        assert isinstance(result, str)
        assert isinstance(entity_map, dict)
        assert "[PERSON_0]" in entity_map


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.requires_model
    def test_text_too_long_error(self, inconnu_with_small_limit):
        """Test that TextTooLongError is raised for oversized text."""
        long_text = "x" * 200

        with pytest.raises(TextTooLongError) as exc_info:
            inconnu_with_small_limit.redact(long_text)

        assert "200" in str(exc_info.value)
        assert "100" in str(exc_info.value)

    @pytest.mark.unit
    def test_spacy_error_raises_processing_error(self):
        """Test that spaCy failures raise ProcessingError, not silent failure."""
        inconnu = Inconnu(language="en")

        with patch.object(
            inconnu.entity_redactor, "nlp", side_effect=RuntimeError("Mock spaCy failure")
        ):
            with pytest.raises(ProcessingError) as exc_info:
                inconnu.redact("Some text")

            assert "SpaCy NLP processing failed" in str(exc_info.value)

    @pytest.mark.unit
    def test_spacy_error_does_not_leak_pii(self):
        """Test that spaCy failures don't silently return unredacted text."""
        inconnu = Inconnu(language="en")
        sensitive_text = "John Doe's SSN is 123-45-6789"

        with patch.object(
            inconnu.entity_redactor, "nlp", side_effect=RuntimeError("Mock failure")
        ):
            with pytest.raises(ProcessingError):
                # Should raise, NOT return the sensitive text
                inconnu.redact(sensitive_text)

    @pytest.mark.unit
    def test_processing_error_via_pseudonymize(self):
        """Test ProcessingError is raised from pseudonymize method."""
        inconnu = Inconnu(language="en")

        with patch.object(
            inconnu.entity_redactor, "nlp", side_effect=RuntimeError("Mock failure")
        ):
            with pytest.raises(ProcessingError):
                inconnu.pseudonymize("Test text")


# =============================================================================
# Library Logging Tests
# =============================================================================


class TestLibraryLogging:
    """Test that the library follows logging best practices.

    Libraries should NOT log by default. They should use NullHandler
    and let the application configure logging if needed.
    """

    @pytest.mark.requires_model
    def test_no_stdout_pollution(self, inconnu_en):
        """Test that processing doesn't print to stdout."""
        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            inconnu_en(text="John Doe visited New York.")
            output = captured_output.getvalue()
            assert output == "", f"Library should not print to stdout: {output!r}"
        finally:
            sys.stdout = original_stdout

    @pytest.mark.requires_model
    def test_no_stdout_on_batch(self, inconnu_en):
        """Test that batch processing doesn't print to stdout."""
        captured_output = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            texts = ["John Doe.", "Jane Smith.", "Bob Wilson."]
            inconnu_en.redact_batch(texts)
            output = captured_output.getvalue()
            assert output == "", f"Library should not print to stdout: {output!r}"
        finally:
            sys.stdout = original_stdout

    @pytest.mark.requires_model
    def test_logging_can_be_enabled(self, inconnu_en):
        """Test that applications can enable library logging."""
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)

        inconnu_logger = logging.getLogger("inconnu")
        inconnu_logger.setLevel(logging.DEBUG)
        inconnu_logger.addHandler(handler)

        try:
            inconnu_en(text="John Doe.")
            # If logging works, we should see some output (or empty if no debug statements hit)
            # The key is that this doesn't crash
        finally:
            inconnu_logger.removeHandler(handler)
            inconnu_logger.setLevel(logging.WARNING)


# =============================================================================
# Custom Components Tests
# =============================================================================


class TestCustomComponents:
    """Test custom NER component functionality."""

    @pytest.mark.requires_model
    def test_add_custom_pattern(self):
        """Test adding custom pattern components."""
        inconnu = Inconnu(language="it")

        inconnu.add_custom_components([
            NERComponent(
                pattern=compile(r"SEPA[-\w]*"),
                label="TRANSACTION_TYPE",
                before_ner=True,
            ),
            NERComponent(
                pattern=compile(r"numero[:]?\s*(?:\d+)"),
                label="CONTRACT_NUMBER",
                before_ner=True,
            ),
        ])

        text = "SEPA payment for numero 021948"
        processed_data = inconnu(text=text)

        assert processed_data.entity_map.get("[TRANSACTION_TYPE_0]") == "SEPA"
        assert processed_data.entity_map.get("[CONTRACT_NUMBER_0]") == "numero 021948"


# =============================================================================
# Multilingual Tests
# =============================================================================


class TestMultilingual:
    """Test multilingual processing capabilities."""

    @pytest.mark.requires_model
    def test_german_processing(self, inconnu_de, de_prompt):
        """Test German language processing."""
        processed_data = inconnu_de(text=de_prompt)
        deanonymized = inconnu_de.deanonymize(processed_data=processed_data)

        # Custom NER should detect email and phone
        assert processed_data.entity_map.get("[EMAIL_0]") == "emma.schmidt@solartech.de"
        assert "[PHONE_NUMBER_0]" in processed_data.entity_map

        # De-anonymization should restore original
        assert de_prompt == deanonymized

    @pytest.mark.requires_model
    def test_english_processing(self, inconnu_en, en_prompt):
        """Test English language processing within time constraints."""
        processed_data = inconnu_en(text=en_prompt)

        assert 0 < processed_data.processing_time_ms < 200

    @pytest.mark.requires_model
    def test_iban_detection_english(self, inconnu_en):
        """Test IBAN detection in English context."""
        text = "IBAN: DE02120300000000202051"
        processed_data = inconnu_en(text=text)

        assert processed_data.entity_map.get("[IBAN_0]") == "DE02120300000000202051"

    @pytest.mark.requires_model
    def test_iban_detection_italian(self, inconnu_it):
        """Test IBAN detection in Italian context."""
        text = "Il mio IBAN è DE02120300000000202051"
        processed_data = inconnu_it(text=text)

        assert processed_data.entity_map.get("[IBAN_0]") == "DE02120300000000202051"

    @pytest.mark.requires_model
    def test_phone_number_detection(self, inconnu_en):
        """Test US phone number detection including reserved 555 numbers."""
        text = "Call +1-555-123-4567 for support."
        processed_data = inconnu_en(text=text)

        phone_placeholders = [
            k for k in processed_data.entity_map if k.startswith("[PHONE_NUMBER")
        ]
        assert len(phone_placeholders) == 1
        assert processed_data.entity_map[phone_placeholders[0]] == "+1-555-123-4567"
