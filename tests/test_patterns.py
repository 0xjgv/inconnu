"""Test suite for pattern validation and entity detection.

This test suite validates all patterns in the expanded pattern library,
testing both positive matches and negative cases for each pattern type.
"""

import pytest

from inconnu import Inconnu, NERComponent
from inconnu.nlp.patterns import (
    API_KEY_PATTERN_RE,
    BAR_NUMBER_PATTERN_RE,
    BITCOIN_ADDRESS_PATTERN_RE,
    # Legal patterns
    CASE_NUMBER_PATTERN_RE,
    COURSE_CODE_PATTERN_RE,
    # Financial patterns
    CREDIT_CARD_PATTERN_RE,
    DEA_NUMBER_PATTERN_RE,
    ETHEREUM_ADDRESS_PATTERN_RE,
    GPA_PATTERN_RE,
    ICD_CODE_PATTERN_RE,
    LEGAL_CITATION_PATTERN_RE,
    MAC_ADDRESS_PATTERN_RE,
    MRN_PATTERN_RE,
    NPI_PATTERN_RE,
    ROUTING_NUMBER_PATTERN_RE,
    SSN_PATTERN_RE,
    # Education patterns
    STUDENT_ID_PATTERN_RE,
    SWIFT_CODE_PATTERN_RE,
    # Customer support patterns
    UUID_PATTERN_RE,
)
from inconnu.nlp.validators import VALIDATION_REGISTRY


class TestHealthcarePatterns:
    """Test healthcare-specific patterns."""

    def test_ssn_pattern(self):
        """Test SSN pattern matching."""
        # Valid SSNs
        valid_ssns = [
            "123-45-6789",
            "987-65-4321",
            "555-12-3456",
        ]
        for ssn in valid_ssns:
            assert SSN_PATTERN_RE.search(ssn), f"Failed to match valid SSN: {ssn}"

        # Invalid SSNs
        invalid_ssns = [
            "12-345-6789",  # Wrong format
            "123456789",  # No dashes
            "123-45-678",  # Too short
            "abc-de-fghi",  # Letters
        ]
        for ssn in invalid_ssns:
            assert not SSN_PATTERN_RE.search(ssn), (
                f"Incorrectly matched invalid SSN: {ssn}"
            )

    def test_mrn_pattern(self):
        """Test Medical Record Number pattern."""
        valid_mrns = [
            "MRN: 123456",
            "MRN:7890123",
            "1234567890",  # Just numbers
            "MRN 999999",
        ]
        for mrn in valid_mrns:
            assert MRN_PATTERN_RE.search(mrn), f"Failed to match valid MRN: {mrn}"

    def test_npi_pattern(self):
        """Test National Provider Identifier pattern."""
        valid_npis = [
            "1234567890",
            "9876543210",
        ]
        for npi in valid_npis:
            assert NPI_PATTERN_RE.search(npi), f"Failed to match valid NPI: {npi}"

        # Should not match numbers with dashes or too many digits
        assert not NPI_PATTERN_RE.search("123-456-7890")
        assert not NPI_PATTERN_RE.search("12345678901")

    def test_dea_number_pattern(self):
        """Test DEA number pattern."""
        valid_deas = [
            "AB1234567",
            "XY9876543",
            "CD0000001",
        ]
        for dea in valid_deas:
            assert DEA_NUMBER_PATTERN_RE.search(dea), (
                f"Failed to match valid DEA: {dea}"
            )

    def test_icd_code_pattern(self):
        """Test ICD code pattern."""
        valid_codes = [
            "A01",
            "B12.3",
            "Z99.999",
            "M25.50",
        ]
        for code in valid_codes:
            assert ICD_CODE_PATTERN_RE.search(code), (
                f"Failed to match valid ICD: {code}"
            )


class TestLegalPatterns:
    """Test legal-specific patterns."""

    def test_case_number_pattern(self):
        """Test case number pattern."""
        valid_cases = [
            "2024-CV-123456",
            "2023-CR-9876",
            "2022-FA-1234",
        ]
        for case in valid_cases:
            assert CASE_NUMBER_PATTERN_RE.search(case), (
                f"Failed to match valid case: {case}"
            )

    def test_bar_number_pattern(self):
        """Test bar number pattern."""
        valid_bars = [
            "Bar No. CA-12345",
            "State Bar No: NY123456",
            "Bar No.TX-98765",
        ]
        for bar in valid_bars:
            assert BAR_NUMBER_PATTERN_RE.search(bar), (
                f"Failed to match valid bar: {bar}"
            )

    def test_legal_citation_pattern(self):
        """Test legal citation pattern."""
        valid_citations = [
            "42 U.S.C. § 1983",
            "26 C.F.R. 1.501",
            "15 U.S.C. § 78j(b)",
        ]
        for citation in valid_citations:
            assert LEGAL_CITATION_PATTERN_RE.search(citation), (
                f"Failed to match valid citation: {citation}"
            )


class TestFinancialPatterns:
    """Test financial-specific patterns."""

    def test_credit_card_pattern(self):
        """Test credit card pattern."""
        valid_cards = [
            "1234 5678 9012 3456",
            "1234-5678-9012-3456",
            "1234567890123456",
        ]
        for card in valid_cards:
            assert CREDIT_CARD_PATTERN_RE.search(card), (
                f"Failed to match valid card: {card}"
            )

        # Should not match partial numbers
        assert not CREDIT_CARD_PATTERN_RE.search("1234 5678")

    def test_swift_code_pattern(self):
        """Test SWIFT code pattern."""
        valid_swifts = [
            "BOFAUS3N",  # 8 characters
            "CHASUS33XXX",  # 11 characters
            "DEUTDEFF",
        ]
        for swift in valid_swifts:
            assert SWIFT_CODE_PATTERN_RE.search(swift), (
                f"Failed to match valid SWIFT: {swift}"
            )

    def test_routing_number_pattern(self):
        """Test routing number pattern."""
        valid_routing = [
            "123456789",
            "987654321",
            "111000025",  # Real Federal Reserve routing
        ]
        for routing in valid_routing:
            assert ROUTING_NUMBER_PATTERN_RE.search(routing), (
                f"Failed to match valid routing: {routing}"
            )

        # Should not match with dashes or wrong length
        assert not ROUTING_NUMBER_PATTERN_RE.search("12-3456789")
        assert not ROUTING_NUMBER_PATTERN_RE.search("12345678")

    def test_crypto_addresses(self):
        """Test cryptocurrency address patterns."""
        # Bitcoin addresses
        bitcoin_addresses = [
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",  # Legacy
            "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy",  # P2SH
            "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq",  # Bech32
        ]
        for addr in bitcoin_addresses:
            assert BITCOIN_ADDRESS_PATTERN_RE.search(addr), (
                f"Failed to match Bitcoin: {addr}"
            )

        # Ethereum addresses
        eth_addresses = [
            "0x742d35Cc6634C0532925a3b844Bc9e7595f6bEd1",
            "0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe",
        ]
        for addr in eth_addresses:
            assert ETHEREUM_ADDRESS_PATTERN_RE.search(addr), (
                f"Failed to match Ethereum: {addr}"
            )


class TestEducationPatterns:
    """Test education-specific patterns."""

    def test_student_id_pattern(self):
        """Test student ID pattern."""
        valid_ids = [
            "ABC-1234-5678",
            "XY-2024-9999",
            "STU-0001-0001",
        ]
        for sid in valid_ids:
            assert STUDENT_ID_PATTERN_RE.search(sid), (
                f"Failed to match student ID: {sid}"
            )

    def test_course_code_pattern(self):
        """Test course code pattern."""
        valid_courses = [
            "CS 101",
            "MATH215",
            "BIO 300A",
            "CHEM101L",
        ]
        for course in valid_courses:
            assert COURSE_CODE_PATTERN_RE.search(course), (
                f"Failed to match course: {course}"
            )

    def test_gpa_pattern(self):
        """Test GPA pattern."""
        valid_gpas = [
            "4.0",
            "3.85",
            "2.5/4.0",
            "3.92/4.00",
        ]
        for gpa in valid_gpas:
            assert GPA_PATTERN_RE.search(gpa), f"Failed to match GPA: {gpa}"


class TestTechnologyPatterns:
    """Test technology-specific patterns."""

    def test_uuid_pattern(self):
        """Test UUID pattern."""
        valid_uuids = [
            "123e4567-e89b-12d3-a456-426614174000",
            "550e8400-e29b-41d4-a716-446655440000",
        ]
        for uuid in valid_uuids:
            assert UUID_PATTERN_RE.search(uuid), f"Failed to match UUID: {uuid}"

        # Invalid version
        assert not UUID_PATTERN_RE.search("123e4567-e89b-62d3-a456-426614174000")

    def test_mac_address_pattern(self):
        """Test MAC address pattern."""
        valid_macs = [
            "00:11:22:33:44:55",
            "AA-BB-CC-DD-EE-FF",
            "a1:b2:c3:d4:e5:f6",
        ]
        for mac in valid_macs:
            assert MAC_ADDRESS_PATTERN_RE.search(mac), f"Failed to match MAC: {mac}"

    def test_api_key_pattern(self):
        """Test API key pattern."""
        valid_keys = [
            "api_key=abcdef1234567890abcdef1234567890",
            "apikey: 'xyz123abc456def789ghi012jkl345mno678'",
            'access_token="0123456789abcdef0123456789abcdef"',
        ]
        for key in valid_keys:
            assert API_KEY_PATTERN_RE.search(key), f"Failed to match API key: {key}"


class TestIntegrationWithInconnu:
    """Test pattern integration with Inconnu."""

    def test_custom_pattern_registration(self):
        """Test registering custom patterns with Inconnu."""
        # Create custom components for testing
        custom_components = [
            NERComponent(
                label="STUDENT_ID",
                pattern=STUDENT_ID_PATTERN_RE,
                processing_func=None,
            ),
            NERComponent(
                label="CREDIT_CARD",
                pattern=CREDIT_CARD_PATTERN_RE,
                processing_func=None,
            ),
        ]

        # Initialize Inconnu with custom patterns
        inconnu = Inconnu(custom_components=custom_components)

        # Test detection
        text = "Student ABC-1234-5678 paid with card 1234-5678-9012-3456"
        result = inconnu.redact(text)

        assert "[STUDENT_ID]" in result
        assert "[CREDIT_CARD]" in result

    def test_pattern_priorities(self):
        """Test that pattern priorities work correctly."""
        # This is tested via the entity conflict resolution
        # Higher priority patterns should win in overlaps
        inconnu = Inconnu()

        # Create text with potential overlap
        text = "SSN: 123-45-6789 and employee ID: EMP-12345"
        result = inconnu.redact(text)

        # Both should be detected without conflict
        assert "[SSN]" in result or "123-45-6789" not in result
        assert "[EMPLOYEE_ID]" in result or "EMP-12345" not in result


class TestPatternValidation:
    """Test pattern validation with validators."""

    def test_ssn_validation(self):
        """Test SSN validation function."""
        validator = VALIDATION_REGISTRY.get("SSN")
        if validator:
            # Valid SSNs
            valid, confidence = validator("123-45-6789")
            assert valid and confidence > 0.8

            # Invalid SSNs
            valid, confidence = validator("000-00-0000")
            assert not valid

            valid, confidence = validator("666-12-3456")
            assert not valid

    def test_credit_card_validation(self):
        """Test credit card validation."""
        validator = VALIDATION_REGISTRY.get("CREDIT_CARD")
        if validator:
            # Valid Visa
            valid, confidence = validator("4111111111111111")
            assert valid and confidence > 0.8

            # Invalid checksum
            valid, confidence = validator("4111111111111112")
            assert not valid


class TestPerformance:
    """Test pattern matching performance."""

    def test_pattern_performance(self):
        """Test that pattern matching meets performance requirements."""
        import time

        # Create test text with many entities
        text = " ".join(
            [
                "John Doe SSN: 123-45-6789",
                "Credit Card: 4111-1111-1111-1111",
                "Student ID: ABC-1234-5678",
                "Email: john@example.com",
                "Phone: (555) 123-4567",
            ]
            * 20
        )  # Repeat to create larger text

        inconnu = Inconnu()

        # Measure processing time
        start = time.time()
        result = inconnu.redact(text)
        elapsed = time.time() - start

        # Should process in under 200ms as per requirements
        assert elapsed < 0.2, (
            f"Processing took {elapsed:.3f}s, exceeding 200ms requirement"
        )

        # Verify entities were detected
        assert "[PERSON]" in result
        assert "[EMAIL]" in result
        assert "[PHONE_NUMBER]" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
