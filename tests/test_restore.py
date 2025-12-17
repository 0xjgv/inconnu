"""Test suite for restore/deanonymize functionality.

Tests cover:
- Basic restoration (round-trip pseudonymize → restore)
- Hallucination detection (unmatched tokens)
- Batch processing
- Edge cases (punctuation, unicode, empty inputs)
"""

import logging

import pytest


class TestRestoreBasic:
    """Basic restore functionality tests."""

    def test_round_trip_single_entity(self, inconnu_en):
        """Verify pseudonymize → restore returns original text."""
        original = "John Doe visited New York."

        redacted, entity_map = inconnu_en.pseudonymize(original)
        restored = inconnu_en.restore(redacted, entity_map)

        assert restored == original

    def test_round_trip_multiple_entities(self, inconnu_en):
        """Verify round-trip with multiple entity types."""
        original = "Dr. Alice Johnson from Texas gave a lecture in London last week."

        redacted, entity_map = inconnu_en.pseudonymize(original)
        restored = inconnu_en.restore(redacted, entity_map)

        assert restored == original

    def test_restore_empty_entity_map(self, inconnu_en):
        """Restore with empty entity_map returns text unchanged."""
        text = "Hello [PERSON_0], how are you?"

        result = inconnu_en.restore(text, {})

        assert result == text

    def test_restore_no_tokens_in_text(self, inconnu_en):
        """Text without tokens returns unchanged."""
        text = "Hello world, no tokens here."
        entity_map = {"[PERSON_0]": "John"}

        result = inconnu_en.restore(text, entity_map)

        assert result == text

    @pytest.mark.parametrize(
        "text,entity_map,expected",
        [
            # Basic replacement
            ("[PERSON_0] called.", {"[PERSON_0]": "John"}, "John called."),
            # Multiple same-type tokens
            (
                "[PERSON_0] met [PERSON_1].",
                {"[PERSON_0]": "Alice", "[PERSON_1]": "Bob"},
                "Alice met Bob.",
            ),
            # Mixed entity types
            (
                "[PERSON_0] from [GPE_0] emailed [EMAIL_0].",
                {
                    "[PERSON_0]": "Jane",
                    "[GPE_0]": "NYC",
                    "[EMAIL_0]": "jane@example.com",
                },
                "Jane from NYC emailed jane@example.com.",
            ),
            # Repeated tokens (same person mentioned twice)
            (
                "[PERSON_0] said [PERSON_0] is busy.",
                {"[PERSON_0]": "Alice"},
                "Alice said Alice is busy.",
            ),
        ],
        ids=[
            "basic_single",
            "multiple_same_type",
            "mixed_types",
            "repeated_tokens",
        ],
    )
    def test_restore_parameterized(self, inconnu_en, text, entity_map, expected):
        """Parameterized restore tests for various scenarios."""
        result = inconnu_en.restore(text, entity_map)
        assert result == expected


class TestRestoreHallucinationDetection:
    """Tests for unmatched token (hallucination) detection."""

    def test_warns_on_single_unmatched_token(self, inconnu_en, caplog):
        """Warning logged for single hallucinated token."""
        text = "Hello [PERSON_0], your friend [PERSON_99] called."
        entity_map = {"[PERSON_0]": "John Doe"}

        with caplog.at_level(logging.WARNING):
            result = inconnu_en.restore(text, entity_map)

        assert result == "Hello John Doe, your friend [PERSON_99] called."
        assert "Unmatched tokens" in caplog.text
        assert "[PERSON_99]" in caplog.text

    def test_warns_on_multiple_unmatched_tokens(self, inconnu_en, caplog):
        """Warning includes all unmatched tokens."""
        text = "[PERSON_0] knows [PERSON_5] and [GPE_10]."
        entity_map = {"[PERSON_0]": "Alice"}

        with caplog.at_level(logging.WARNING):
            inconnu_en.restore(text, entity_map)

        assert "[PERSON_5]" in caplog.text
        assert "[GPE_10]" in caplog.text

    def test_no_warning_when_all_matched(self, inconnu_en, caplog):
        """No warning when all tokens have mappings."""
        text = "Hello [PERSON_0] from [GPE_0]."
        entity_map = {"[PERSON_0]": "John Doe", "[GPE_0]": "New York"}

        with caplog.at_level(logging.WARNING):
            result = inconnu_en.restore(text, entity_map)

        assert result == "Hello John Doe from New York."
        assert "Unmatched tokens" not in caplog.text

    def test_warn_unmatched_disabled(self, inconnu_en, caplog):
        """Warning can be disabled via parameter."""
        text = "Hello [PERSON_99]."
        entity_map = {}

        with caplog.at_level(logging.WARNING):
            result = inconnu_en.entity_redactor.restore(
                text, entity_map, warn_unmatched=False
            )

        assert result == "Hello [PERSON_99]."
        assert "Unmatched tokens" not in caplog.text

    def test_no_warning_for_non_token_brackets(self, inconnu_en, caplog):
        """Brackets that don't match token pattern don't trigger warning."""
        text = "Use [option1] or [option2] for config."
        entity_map = {}

        with caplog.at_level(logging.WARNING):
            result = inconnu_en.restore(text, entity_map)

        assert result == text
        assert "Unmatched tokens" not in caplog.text


class TestRestoreEdgeCases:
    """Edge case tests for restore functionality."""

    def test_unicode_in_original_text(self, inconnu_en):
        """Handles unicode characters in original values."""
        text = "[PERSON_0] lives in [GPE_0]."
        entity_map = {"[PERSON_0]": "José García", "[GPE_0]": "São Paulo"}

        result = inconnu_en.restore(text, entity_map)

        assert result == "José García lives in São Paulo."

    def test_punctuation_adjacent_to_tokens(self, inconnu_en):
        """Handles punctuation directly adjacent to tokens."""
        text = '"[PERSON_0]," said [PERSON_1]. "[GPE_0]!"'
        entity_map = {
            "[PERSON_0]": "Hello",
            "[PERSON_1]": "Alice",
            "[GPE_0]": "NYC",
        }

        result = inconnu_en.restore(text, entity_map)

        assert result == '"Hello," said Alice. "NYC!"'

    def test_newlines_preserved(self, inconnu_en):
        """Newlines in text are preserved during restore."""
        text = "[PERSON_0]\nlives in\n[GPE_0]"
        entity_map = {"[PERSON_0]": "John", "[GPE_0]": "NYC"}

        result = inconnu_en.restore(text, entity_map)

        assert result == "John\nlives in\nNYC"

    def test_empty_text(self, inconnu_en):
        """Empty text returns empty string."""
        result = inconnu_en.restore("", {"[PERSON_0]": "John"})
        assert result == ""

    def test_whitespace_only_text(self, inconnu_en):
        """Whitespace-only text returns unchanged."""
        result = inconnu_en.restore("   \n\t  ", {})
        assert result == "   \n\t  "

    def test_special_regex_chars_in_original(self, inconnu_en):
        """Original values with regex special chars handled correctly."""
        text = "[PERSON_0] asked about [EMAIL_0]"
        entity_map = {
            "[PERSON_0]": "John (Jr.)",
            "[EMAIL_0]": "test+special@example.com",
        }

        result = inconnu_en.restore(text, entity_map)

        assert result == "John (Jr.) asked about test+special@example.com"


class TestRestoreBatch:
    """Tests for batch restore functionality."""

    def test_batch_basic(self, inconnu_en):
        """Basic batch restoration."""
        items = [
            ("[PERSON_0] visited [GPE_0].", {"[PERSON_0]": "John", "[GPE_0]": "NYC"}),
            ("Hello [PERSON_0]!", {"[PERSON_0]": "Jane"}),
        ]

        results = inconnu_en.restore_batch(items)

        assert results == ["John visited NYC.", "Hello Jane!"]

    def test_batch_empty_list(self, inconnu_en):
        """Batch with empty list returns empty list."""
        results = inconnu_en.restore_batch([])
        assert results == []

    def test_batch_single_item(self, inconnu_en):
        """Batch with single item works correctly."""
        items = [("[PERSON_0].", {"[PERSON_0]": "Test"})]

        results = inconnu_en.restore_batch(items)

        assert results == ["Test."]

    def test_batch_large(self, inconnu_en):
        """Batch handles large number of items."""
        items = [
            (f"[PERSON_0] number {i}.", {"[PERSON_0]": f"Person{i}"})
            for i in range(100)
        ]

        results = inconnu_en.restore_batch(items)

        assert len(results) == 100
        assert results[0] == "Person0 number 0."
        assert results[99] == "Person99 number 99."

    def test_batch_with_chunk_size(self, inconnu_en):
        """Batch respects custom chunk_size."""
        items = [
            (f"[PERSON_0] item {i}.", {"[PERSON_0]": f"Name{i}"}) for i in range(10)
        ]

        results = inconnu_en.restore_batch(items, chunk_size=3)

        assert len(results) == 10

    def test_batch_independent_entity_maps(self, inconnu_en):
        """Each item uses its own entity_map independently."""
        items = [
            ("[PERSON_0] is here.", {"[PERSON_0]": "Alice"}),
            ("[PERSON_0] is there.", {"[PERSON_0]": "Bob"}),
        ]

        results = inconnu_en.restore_batch(items)

        assert results == ["Alice is here.", "Bob is there."]

    @pytest.mark.asyncio
    async def test_batch_async(self, inconnu_en):
        """Async batch restoration."""
        items = [
            ("[PERSON_0] called.", {"[PERSON_0]": "Alice"}),
            ("[PERSON_0] replied.", {"[PERSON_0]": "Bob"}),
        ]

        results = await inconnu_en.restore_batch_async(items)

        assert results == ["Alice called.", "Bob replied."]

    @pytest.mark.asyncio
    async def test_batch_async_empty(self, inconnu_en):
        """Async batch with empty list."""
        results = await inconnu_en.restore_batch_async([])
        assert results == []


class TestDeanonymize:
    """Tests for deanonymize() convenience wrapper."""

    def test_deanonymize_basic(self, inconnu_en):
        """Deanonymize with ProcessedData works correctly."""
        original = "John Doe visited New York last summer."

        processed_data = inconnu_en(text=original)
        restored = inconnu_en.deanonymize(processed_data=processed_data)

        assert restored == original

    def test_deanonymize_with_modified_redacted_text(self, inconnu_en):
        """Deanonymize works when redacted_text is modified (LLM response)."""
        original = "John Doe from New York visited Paris."

        processed_data = inconnu_en(text=original)

        # Simulate LLM modifying the structure but keeping tokens
        # We manually construct the redacted text to simulate an LLM summarization
        # e.g. "Summary: [PERSON_0] traveled from [GPE_0]."

        # Note: We need to know which token maps to which entity to construct this reliably in a test
        # Since the token indices are deterministic but depend on the order of extraction,
        # we can just use the entity map to find the tokens.

        person_token = next(
            k for k, v in processed_data.entity_map.items() if "John Doe" in v
        )
        gpe_token = next(
            k for k, v in processed_data.entity_map.items() if "New York" in v
        )

        processed_data.redacted_text = (
            f"Summary: {person_token} traveled from {gpe_token}."
        )

        restored = inconnu_en.deanonymize(processed_data=processed_data)

        assert "John Doe" in restored
        assert "New York" in restored
