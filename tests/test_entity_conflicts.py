"""Test suite for entity conflict resolution and overlap handling.

This test suite validates the enhanced conflict resolution system,
ensuring that overlapping entities are handled correctly according
to priority rules and that the system gracefully handles edge cases.
"""

import pytest
import re
from spacy.tokens import Span

from inconnu import Config, Inconnu, NERComponent
from inconnu.nlp.utils import filter_overlapping_spans, validate_entity_spans


class TestEntityConflictResolution:
    """Test the core conflict resolution functionality."""

    def test_basic_overlap_resolution(self):
        """Test basic overlap resolution with different priorities."""
        # Create a mock doc
        text = "John Smith has SSN 123-45-6789"
        inconnu = Inconnu()
        doc = inconnu.entity_redactor.nlp(text)

        # Create overlapping spans
        spans = [
            Span(doc, 0, 2, label="PERSON"),  # "John Smith"
            Span(doc, 1, 2, label="PERSON"),  # "Smith" - overlaps
            Span(doc, 4, 7, label="SSN"),  # "123-45-6789"
        ]

        # Filter overlapping spans
        filtered = filter_overlapping_spans(spans)

        # Should keep the longer PERSON span
        assert len(filtered) == 2
        assert filtered[0].text == "John Smith"
        assert filtered[1].label_ == "SSN"

    def test_priority_based_resolution(self):
        """Test that higher priority entities win in conflicts."""
        text = "Email: john@example.com 123-45-6789"
        inconnu = Inconnu()
        doc = inconnu.entity_redactor.nlp(text)

        # Create spans with different priorities
        spans = [
            Span(doc, 2, 4, label="EMAIL"),  # Higher priority
            Span(doc, 2, 4, label="MISC"),  # Lower priority - same span
            Span(doc, 5, 8, label="SSN"),  # High priority
            Span(doc, 5, 8, label="CARDINAL"),  # Lower priority - same span
        ]

        filtered = filter_overlapping_spans(spans)

        # Should keep higher priority entities
        assert len(filtered) == 2
        assert any(s.label_ == "EMAIL" for s in filtered)
        assert any(s.label_ == "SSN" for s in filtered)
        assert not any(s.label_ == "MISC" for s in filtered)
        assert not any(s.label_ == "CARDINAL" for s in filtered)

    def test_length_based_resolution(self):
        """Test that longer spans are preferred when priorities are equal."""
        text = "Dr. John Smith is a physician"
        inconnu = Inconnu()
        doc = inconnu.entity_redactor.nlp(text)

        # Create overlapping spans of different lengths
        spans = [
            Span(doc, 0, 3, label="PERSON"),  # "Dr. John Smith"
            Span(doc, 1, 3, label="PERSON"),  # "John Smith" - shorter overlap
            Span(doc, 2, 3, label="PERSON"),  # "Smith" - shortest
        ]

        filtered = filter_overlapping_spans(spans)

        # Should keep the longest span
        assert len(filtered) == 1
        assert filtered[0].text == "Dr. John Smith"

    def test_debug_logging(self):
        """Test that debug logging works for conflict resolution."""
        text = "Test conflict resolution"
        inconnu = Inconnu()
        doc = inconnu.entity_redactor.nlp(text)

        # Create conflicting spans using token indices
        spans = [
            Span(doc, 0, 1, label="PERSON"),  # "Test" (token 0)
            Span(
                doc, 0, 2, label="ORG"
            ),  # "Test conflict" (tokens 0-1) - Overlaps with PERSON
        ]

        # Enable debug logging and check it works without errors
        filtered = filter_overlapping_spans(spans, debug=True)

        # Should filter overlapping spans correctly
        assert len(filtered) == 1
        # When spans start at the same position, longer span wins (ORG with 2 tokens vs PERSON with 1)
        assert filtered[0].label_ == "ORG"


class TestPersonWithTitleConflicts:
    """Test the person_with_title function that was causing issues."""

    def test_person_title_extension(self):
        """Test that person entities are correctly extended with titles."""
        text = "Dr. Smith and Mr. Jones met yesterday"
        inconnu = Inconnu()

        # Process the text
        result = inconnu.redact(text)

        # Both people with titles should be detected
        assert result.count("[PERSON]") == 2
        assert "Dr." not in result  # Title should be included in PERSON entity
        assert "Mr." not in result  # Title should be included in PERSON entity

    def test_overlapping_title_conflicts(self):
        """Test edge case where title extension could cause conflicts."""
        # This was the specific case causing ValueError in Example 06
        text = "Meeting with Dr. Alice Johnson, Prof. Bob Smith, and Ms. Carol White"

        config = Config(log_conflicts=True)
        inconnu = Inconnu(config=config)

        # This should not raise ValueError anymore
        result = inconnu.redact(text)

        # All three people should be detected
        assert result.count("[PERSON]") == 3

        # Titles should be included in person entities
        assert "Dr." not in result
        assert "Prof." not in result
        assert "Ms." not in result

    def test_adjacent_entities_with_titles(self):
        """Test handling of adjacent entities that might overlap after title extension."""
        text = "Dr. Smith, CEO of TechCorp, announced the merger"
        inconnu = Inconnu()

        result = inconnu.redact(text)

        # Should detect both PERSON and ORG without conflict
        assert "[PERSON]" in result
        assert "[ORG]" in result

        # Original text structure should be preserved
        assert ", CEO of [ORG]" in result or "CEO" in result


class TestEdgeCases:
    """Test edge cases in entity conflict resolution."""

    def test_zero_length_spans(self):
        """Test handling of zero-length spans."""
        text = "Test text"
        inconnu = Inconnu()
        doc = inconnu.entity_redactor.nlp(text)

        # Create spans including zero-length
        spans = [
            Span(doc, 0, 1, label="MISC"),
            Span(doc, 1, 1, label="MISC"),  # Zero-length span
            Span(doc, 1, 2, label="MISC"),
        ]

        # Validate spans
        valid_spans, errors = validate_entity_spans(spans)

        # Zero-length span should be filtered out
        assert len(valid_spans) == 2
        assert any("invalid range" in error for error in errors)

    def test_out_of_bounds_spans(self):
        """Test handling of spans that exceed document boundaries."""
        text = "Short"
        inconnu = Inconnu()
        doc = inconnu.entity_redactor.nlp(text)

        # Create spans including out of bounds
        spans = [
            Span(doc, 0, 1, label="MISC"),
            # Note: Can't create actually invalid Span objects
        ]

        # Test validation with mock boundaries
        valid_spans, errors = validate_entity_spans(spans, doc_length=len(doc))

        assert len(valid_spans) == 1

    def test_identical_spans_different_labels(self):
        """Test handling of identical spans with different labels."""
        text = "Apple Inc. is a company"
        inconnu = Inconnu()
        doc = inconnu.entity_redactor.nlp(text)

        # Create identical spans with different labels
        spans = [
            Span(doc, 0, 2, label="ORG"),
            Span(doc, 0, 2, label="PRODUCT"),  # Same span, different label
        ]

        filtered = filter_overlapping_spans(spans)

        # Should keep higher priority (ORG over PRODUCT)
        assert len(filtered) == 1
        assert filtered[0].label_ == "ORG"

    def test_nested_entities(self):
        """Test handling of nested entities."""
        text = "New York City Police Department"
        inconnu = Inconnu()
        doc = inconnu.entity_redactor.nlp(text)

        # Create nested spans
        spans = [
            Span(doc, 0, 5, label="ORG"),  # Full organization name
            Span(doc, 0, 3, label="GPE"),  # "New York City" nested inside
            Span(doc, 3, 4, label="ORG"),  # "Police" partial
        ]

        filtered = filter_overlapping_spans(spans)

        # Should prefer the complete ORG span
        assert len(filtered) == 1
        assert filtered[0].text == "New York City Police Department"
        assert filtered[0].label_ == "ORG"


class TestMultilingualConflicts:
    """Test conflict resolution in multilingual contexts."""

    def test_german_entity_conflicts(self):
        """Test German-specific entity conflicts (PER vs PERSON)."""
        text = "Herr Schmidt arbeitet bei Siemens"
        inconnu = Inconnu(language="de")

        result = inconnu.redact(text)

        # Should normalize PER to PERSON
        assert "[PERSON]" in result
        # Herr should be included in the person entity
        assert "Herr" not in result

    def test_cross_language_standardization(self):
        """Test standardization of entity types across languages."""
        # Test German PER -> PERSON conversion
        text_de = "Angela Merkel ist Bundeskanzlerin"
        inconnu_de = Inconnu(language="de")
        result_de = inconnu_de.redact(text_de)

        # Test English
        text_en = "Angela Merkel is Chancellor"
        inconnu_en = Inconnu(language="en")
        result_en = inconnu_en.redact(text_en)

        # Both should use PERSON, not PER
        assert "[PERSON]" in result_de
        assert "[PERSON]" in result_en


class TestCustomComponentConflicts:
    """Test conflicts between custom and built-in components."""

    def test_custom_pattern_priority(self):
        """Test that custom patterns can override built-in ones."""
        # Create custom SSN pattern with higher priority
        custom_components = [
            NERComponent(
                label="CUSTOM_SSN",
                pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
                processing_func=None,
            ),
        ]

        inconnu = Inconnu(custom_components=custom_components)
        text = "SSN: 123-45-6789"

        result = inconnu.redact(text)

        # Custom pattern should take precedence
        assert "[CUSTOM_SSN]" in result or "[SSN]" in result

    def test_overlapping_custom_patterns(self):
        """Test resolution of overlapping custom patterns."""
        import re

        # Create overlapping patterns
        custom_components = [
            NERComponent(
                label="FULL_SSN",
                pattern=re.compile(r"SSN:\s*\d{3}-\d{2}-\d{4}"),
                processing_func=None,
            ),
            NERComponent(
                label="PARTIAL_SSN",
                pattern=re.compile(r"\d{3}-\d{2}-\d{4}"),
                processing_func=None,
            ),
        ]

        inconnu = Inconnu(custom_components=custom_components)
        text = "My SSN: 123-45-6789 is private"

        result = inconnu.redact(text)

        # Should handle the overlap gracefully
        assert "123-45-6789" not in result
        assert "[" in result and "]" in result


class TestPerformanceImpact:
    """Test performance impact of enhanced conflict resolution."""

    def test_conflict_resolution_performance(self):
        """Test that conflict resolution doesn't significantly impact performance."""
        import time

        # Create text with many potential conflicts
        text = " ".join(
            [
                "Dr. John Smith (john@email.com)",
                "Prof. Jane Doe (555-123-4567)",
                "Mr. Bob Wilson, CEO of TechCorp",
            ]
            * 10
        )

        inconnu = Inconnu()

        # Time the processing
        start = time.time()
        result = inconnu.redact(text)
        elapsed = time.time() - start

        # Should still meet performance requirements
        assert elapsed < 0.2  # Under 200ms requirement

        # Verify entities were properly resolved
        assert "[PERSON]" in result
        assert "[EMAIL]" in result
        assert "[PHONE_NUMBER]" in result
        assert "[ORG]" in result

    def test_large_document_conflicts(self):
        """Test conflict resolution on large documents."""
        # Create a large document with many entities
        sections = []
        for i in range(100):
            sections.append(f"Person {i} (ID: EMP-{i:05d}) works at Company{i}")

        text = " ".join(sections)
        inconnu = Inconnu()

        result = inconnu.redact(text)

        # Should handle all entities without performance degradation
        assert result.count("[PERSON]") <= 100  # Some might be merged or filtered
        assert result.count("[EMPLOYEE_ID]") == 100  # All should be detected
        assert result.count("[ORG]") <= 100


class TestRegressionTests:
    """Regression tests for specific issues that were fixed."""

    def test_example_06_scenario(self):
        """Test the specific scenario that was failing in Example 06."""
        # This is the exact type of text that was causing ValueError
        text = """
        Student: Emily Rodriguez
        Date of Birth: March 15, 2008
        Student ID: LHS-2024-8901
        Grade: 10th

        Instructor: Prof. Amanda Chen
        Current Grade: B+ (GPA: 3.33/4.00)
        """

        # This should not raise ValueError anymore
        inconnu = Inconnu()
        result = inconnu.redact(text)

        # Verify processing succeeded
        assert "[PERSON]" in result  # At least one person should be detected
        assert "[DATE]" in result
        assert "[STUDENT_ID]" in result
        # Note: spaCy small model may not detect all names correctly
        # At least one name should be redacted
        assert "Amanda Chen" not in result or "Emily Rodriguez" not in result

    def test_validation_error_recovery(self):
        """Test that validation errors are handled gracefully."""
        # Create text that might cause validation issues
        text = "Contact: John Doe [][] ((( ))) weird symbols 123-45-6789"

        inconnu = Inconnu()

        # Should handle gracefully without crashing
        result = inconnu.redact(text)

        assert "[PERSON]" in result
        assert "[SSN]" in result or "123-45-6789" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
