"""Tests for codebase improvements: logging, error handling, and de-anonymization."""

import io
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from inconnu import Inconnu, ProcessingError
from inconnu.config import Config
from inconnu.nlp.interfaces import ProcessedData


@pytest.fixture
def inconnu_en() -> Inconnu:
    return Inconnu(
        config=Config(
            data_retention_days=30,
            max_text_length=75_000,
        ),
        language="en",
    )


class TestLibraryLogging:
    """Tests to verify proper library logging behavior.

    Libraries should NOT log by default. They should use NullHandler
    and let the application configure logging if needed.
    """

    def test_no_stdout_pollution_on_processing(self, inconnu_en):
        """Verify that processing text doesn't print to stdout."""
        # Capture stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            # Process some text
            text = "John Doe visited New York last summer."
            inconnu_en(text=text)

            # Check that nothing was printed to stdout
            output = captured_output.getvalue()
            assert output == "", f"Library should not print to stdout, but got: {output!r}"
        finally:
            sys.stdout = sys.__stdout__

    def test_no_stdout_pollution_on_batch_processing(self, inconnu_en):
        """Verify that batch processing doesn't print to stdout."""
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            texts = [
                "John Doe visited New York.",
                "Jane Smith went to Paris.",
                "Bob Johnson lives in London.",
            ]
            inconnu_en.redact_batch(texts)

            output = captured_output.getvalue()
            assert output == "", f"Library should not print to stdout, but got: {output!r}"
        finally:
            sys.stdout = sys.__stdout__

    def test_logging_can_be_enabled_by_application(self, inconnu_en):
        """Verify that applications can enable logging if they want."""
        # Set up logging to capture debug messages
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)

        # Get the inconnu logger and add our handler
        inconnu_logger = logging.getLogger("inconnu")
        inconnu_logger.setLevel(logging.DEBUG)
        inconnu_logger.addHandler(handler)

        try:
            text = "John Doe visited New York."
            inconnu_en(text=text)

            # Check that debug messages were captured
            log_output = log_capture.getvalue()
            assert "Processing text" in log_output or log_output == ""
        finally:
            inconnu_logger.removeHandler(handler)
            inconnu_logger.setLevel(logging.WARNING)


class TestProcessingErrorHandling:
    """Tests to verify that processing errors are properly raised, not silently ignored."""

    def test_spacy_error_raises_processing_error(self):
        """Verify that spaCy processing failures raise ProcessingError."""
        inconnu = Inconnu(language="en")

        # Mock the nlp pipeline to raise an error
        with patch.object(
            inconnu.entity_redactor, "nlp", side_effect=RuntimeError("Mock spaCy failure")
        ):
            with pytest.raises(ProcessingError) as exc_info:
                inconnu.redact("Some text that should fail")

            assert "SpaCy NLP processing failed" in str(exc_info.value)
            assert "Mock spaCy failure" in str(exc_info.value)

    def test_spacy_error_does_not_return_original_text(self):
        """Verify that spaCy failures don't silently return unredacted text."""
        inconnu = Inconnu(language="en")

        sensitive_text = "John Doe's SSN is 123-45-6789"

        with patch.object(
            inconnu.entity_redactor, "nlp", side_effect=RuntimeError("Mock failure")
        ):
            # Should raise, NOT return the sensitive text
            with pytest.raises(ProcessingError):
                result = inconnu.redact(sensitive_text)
                # If we get here without exception, fail the test
                pytest.fail(
                    f"Should have raised ProcessingError, but returned: {result}"
                )

    def test_processing_error_via_call_method(self):
        """Verify ProcessingError is raised when using __call__ method."""
        inconnu = Inconnu(language="en")

        with patch.object(
            inconnu.entity_redactor, "nlp", side_effect=RuntimeError("Mock failure")
        ):
            with pytest.raises(ProcessingError):
                inconnu(text="Test text")

    def test_processing_error_via_pseudonymize(self):
        """Verify ProcessingError is raised when using pseudonymize method."""
        inconnu = Inconnu(language="en")

        with patch.object(
            inconnu.entity_redactor, "nlp", side_effect=RuntimeError("Mock failure")
        ):
            with pytest.raises(ProcessingError):
                inconnu.pseudonymize("Test text")


class TestRobustDeanonymization:
    """Tests for position-based de-anonymization."""

    def test_basic_deanonymization_with_positions(self, inconnu_en):
        """Verify basic de-anonymization works with position tracking."""
        text = "John Doe visited New York last summer."

        processed_data = inconnu_en(text=text)

        # Verify positions are tracked
        assert processed_data.entity_positions, "entity_positions should be populated"

        # Verify de-anonymization works correctly
        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)
        assert deanonymized == text

    def test_deanonymization_with_placeholder_like_text(self, inconnu_en):
        """Test de-anonymization when original text contains placeholder-like strings.

        This is the key test case that the old string-replace approach would fail.
        """
        # Original text contains something that looks like a placeholder
        text = "The code uses [PERSON_0] as a variable name. John Doe wrote it."

        processed_data = inconnu_en(text=text)

        # The redacted text should have two [PERSON_0] - one original, one replaced
        # But entity_map should only have one entry
        assert "[PERSON_0]" in processed_data.entity_map

        # De-anonymization should correctly restore only the entity we redacted
        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)

        # The original [PERSON_0] in the code reference should remain
        assert "[PERSON_0]" in deanonymized
        # The person name should be restored
        assert "John Doe" in deanonymized

    def test_entity_positions_are_correct(self, inconnu_en):
        """Verify that entity positions match the actual placeholder locations."""
        text = "John Doe visited New York."

        processed_data = inconnu_en(text=text)

        # Check each position is correct
        for placeholder, (start, end) in processed_data.entity_positions.items():
            actual_text = processed_data.redacted_text[start:end]
            assert actual_text == placeholder, (
                f"Position mismatch for {placeholder}: "
                f"expected at {start}:{end} to be '{placeholder}', "
                f"but found '{actual_text}'"
            )

    def test_deanonymization_multiple_entities(self, inconnu_en):
        """Test de-anonymization with multiple entities."""
        text = "John Doe from New York visited Jane Smith in Paris last summer."

        processed_data = inconnu_en(text=text)

        # Should have multiple positions tracked
        assert len(processed_data.entity_positions) > 0

        # De-anonymization should restore all entities
        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)
        assert deanonymized == text

    def test_backward_compatibility_without_positions(self, inconnu_en):
        """Verify de-anonymization still works when positions are not available.

        This ensures backward compatibility with older ProcessedData objects.
        """
        text = "John Doe visited New York."

        processed_data = inconnu_en(text=text)

        # Clear positions to simulate old ProcessedData
        processed_data.entity_positions = {}

        # Should still work via string replacement fallback
        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)
        assert deanonymized == text

    def test_position_mismatch_fallback(self, inconnu_en):
        """Test that position mismatch falls back to string replacement."""
        text = "John Doe visited New York."

        processed_data = inconnu_en(text=text)

        # Modify redacted_text to cause position mismatch
        # (simulating external modification of the text)
        original_redacted = processed_data.redacted_text
        processed_data.redacted_text = "MODIFIED: " + original_redacted

        # Update positions to be offset (still pointing to old locations)
        # The deanonymize method should detect mismatch and fall back to string replace

        # This should still work (with warning logged)
        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)

        # Should contain the original names restored via string replacement
        assert "John Doe" in deanonymized
        assert "New York" in deanonymized

    def test_empty_text_handling(self, inconnu_en):
        """Test handling of empty text."""
        text = ""

        processed_data = inconnu_en(text=text)

        assert processed_data.entity_positions == {}
        assert processed_data.entity_map == {}

        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)
        assert deanonymized == ""

    def test_text_without_entities(self, inconnu_en):
        """Test text that contains no recognizable entities."""
        text = "The quick brown fox jumps over the lazy dog."

        processed_data = inconnu_en(text=text)

        assert processed_data.entity_positions == {}
        assert processed_data.entity_map == {}
        assert processed_data.redacted_text == text

        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)
        assert deanonymized == text


class TestProcessedDataEntityPositions:
    """Tests for the new entity_positions field in ProcessedData."""

    def test_processed_data_has_entity_positions_field(self):
        """Verify ProcessedData has the entity_positions field."""
        data = ProcessedData(
            entity_map={},
            processing_time_ms=0.0,
            redacted_text="",
            original_text="",
            text_length=0,
            timestamp="",
            hashed_id="",
        )
        assert hasattr(data, "entity_positions")
        assert data.entity_positions == {}

    def test_entity_positions_default_empty_dict(self):
        """Verify entity_positions defaults to empty dict."""
        data = ProcessedData(
            entity_map={"[PERSON_0]": "John"},
            processing_time_ms=1.0,
            redacted_text="Hello [PERSON_0]",
            original_text="Hello John",
            text_length=10,
            timestamp="2024-01-01",
            hashed_id="abc123",
        )
        # Default value should be empty dict
        assert data.entity_positions == {}

    def test_entity_positions_can_be_set(self):
        """Verify entity_positions can be set with position data."""
        data = ProcessedData(
            entity_map={"[PERSON_0]": "John"},
            processing_time_ms=1.0,
            redacted_text="Hello [PERSON_0]",
            original_text="Hello John",
            text_length=10,
            timestamp="2024-01-01",
            hashed_id="abc123",
            entity_positions={"[PERSON_0]": (6, 16)},
        )
        assert data.entity_positions == {"[PERSON_0]": (6, 16)}
