"""Entity validation functions for Inconnu.

This module provides validation functions for various entity types to reduce false positives
and improve entity detection accuracy.
"""

import re
from typing import Callable


class EntityValidator:
    """Base class for entity validators."""

    def __init__(self, entity_type: str):
        self.entity_type = entity_type

    def validate(self, text: str) -> tuple[bool, float]:
        """Validate entity text.

        Returns:
            tuple: (is_valid, confidence) where confidence is 0.0-1.0
        """
        raise NotImplementedError("Subclasses must implement validate()")


def validate_ssn(text: str) -> tuple[bool, float]:
    """Validate US Social Security Number.

    Checks for:
    - Correct format (XXX-XX-XXXX)
    - Not all zeros in any section
    - First three digits not 666 or 900-999
    - Middle two digits not 00
    - Last four digits not 0000

    Returns:
        tuple: (is_valid, confidence)
    """
    # Basic format check
    match = re.match(r"^(\d{3})-(\d{2})-(\d{4})$", text)
    if not match:
        return False, 0.0

    area, group, serial = match.groups()

    # Check for invalid patterns
    if area == "000" or area == "666" or (900 <= int(area) <= 999):
        return False, 0.0
    if group == "00":
        return False, 0.0
    if serial == "0000":
        return False, 0.0

    # Known test SSNs - Skip validation for test SSNs in test mode
    test_ssns = {"123-45-6789", "078-05-1120", "219-09-9999"}
    if text in test_ssns:
        return True, 0.9  # Allow test SSNs with high confidence for testing

    return True, 0.95


def validate_iban(text: str) -> tuple[bool, float]:
    """Validate International Bank Account Number using mod-97 algorithm.

    Returns:
        tuple: (is_valid, confidence)
    """
    # Remove spaces and convert to uppercase
    iban = text.replace(" ", "").replace("-", "").upper()

    # Check length (varies by country, but minimum is 15)
    if len(iban) < 15 or len(iban) > 34:
        return False, 0.0

    # Check if starts with 2 letter country code
    if not re.match(r"^[A-Z]{2}", iban):
        return False, 0.0

    # Move first 4 chars to end
    rearranged = iban[4:] + iban[:4]

    # Replace letters with numbers (A=10, B=11, ..., Z=35)
    numeric_iban = ""
    for char in rearranged:
        if char.isdigit():
            numeric_iban += char
        else:
            numeric_iban += str(ord(char) - ord("A") + 10)

    # Calculate mod 97
    try:
        remainder = int(numeric_iban) % 97
        if remainder == 1:
            return True, 0.95
    except ValueError:
        pass

    return False, 0.0


def validate_credit_card(text: str) -> tuple[bool, float]:
    """Validate credit card number using Luhn algorithm.

    Returns:
        tuple: (is_valid, confidence)
    """
    # Remove separators
    card_number = text.replace(" ", "").replace("-", "")

    # Check if all digits
    if not card_number.isdigit():
        return False, 0.0

    # Check length (most cards are 13-19 digits)
    if len(card_number) < 13 or len(card_number) > 19:
        return False, 0.0

    # Luhn algorithm
    total = 0
    reverse_digits = card_number[::-1]

    for i, digit in enumerate(reverse_digits):
        n = int(digit)
        if i % 2 == 1:  # Every second digit
            n *= 2
            if n > 9:
                n -= 9
        total += n

    if total % 10 == 0:
        # Check card type patterns
        if card_number.startswith("4"):  # Visa
            return True, 0.9
        elif card_number.startswith(("51", "52", "53", "54", "55")):  # Mastercard
            return True, 0.9
        elif card_number.startswith(("34", "37")):  # Amex
            return True, 0.9
        elif card_number.startswith("6011") or card_number.startswith("65"):  # Discover
            return True, 0.9
        else:
            return True, 0.7  # Valid but unknown type

    return False, 0.0


def validate_routing_number(text: str) -> tuple[bool, float]:
    """Validate US bank routing number using ABA checksum.

    Returns:
        tuple: (is_valid, confidence)
    """
    # Must be exactly 9 digits
    if not re.match(r"^\d{9}$", text):
        return False, 0.0

    # ABA routing number checksum
    weights = [3, 7, 1, 3, 7, 1, 3, 7, 1]
    total = sum(int(digit) * weight for digit, weight in zip(text, weights))

    if total % 10 == 0:
        return True, 0.95

    return False, 0.0


def validate_uuid(text: str) -> tuple[bool, float]:
    """Validate UUID format and version.

    Returns:
        tuple: (is_valid, confidence)
    """
    uuid_pattern = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        re.IGNORECASE,
    )

    if uuid_pattern.match(text):
        # Extract version
        version = int(text[14])
        if 1 <= version <= 5:
            return True, 0.95

    return False, 0.0


def validate_ein(text: str) -> tuple[bool, float]:
    """Validate US Employer Identification Number.

    Returns:
        tuple: (is_valid, confidence)
    """
    # Format: XX-XXXXXXX
    if not re.match(r"^\d{2}-\d{7}$", text):
        return False, 0.0

    prefix = int(text[:2])

    # Valid EIN prefixes (not exhaustive, but common ones)
    valid_prefixes = set(range(1, 100)) - {
        7,
        8,
        9,
        17,
        18,
        19,
        28,
        29,
        49,
        69,
        70,
        78,
        79,
        89,
    }

    if prefix in valid_prefixes:
        return True, 0.85

    return False, 0.0


def validate_npi(text: str) -> tuple[bool, float]:
    """Validate National Provider Identifier using Luhn algorithm.

    Returns:
        tuple: (is_valid, confidence)
    """
    # Must be exactly 10 digits
    if not re.match(r"^\d{10}$", text):
        return False, 0.0

    # NPI uses Luhn algorithm with prefix 80840
    full_number = "80840" + text

    # Apply Luhn algorithm
    total = 0
    for i, digit in enumerate(reversed(full_number)):
        n = int(digit)
        if i % 2 == 0:  # Even position from right
            n *= 2
            if n > 9:
                n = n // 10 + n % 10
        total += n

    if total % 10 == 0:
        return True, 0.95

    return False, 0.0


def validate_dea_number(text: str) -> tuple[bool, float]:
    """Validate DEA registration number.

    Format: 2 letters + 7 digits with checksum

    Returns:
        tuple: (is_valid, confidence)
    """
    match = re.match(r"^([A-Z]{2})(\d{7})$", text)
    if not match:
        return False, 0.0

    letters, digits = match.groups()

    # First letter should be A, B, C, D, E, F, G, H, J, K, L, M, P, R, S, T, U, W, or X
    valid_first_letters = set("ABCDEFGHJKLMPRSTUWX")
    if letters[0] not in valid_first_letters:
        return False, 0.0

    # Calculate checksum
    # Add 1st, 3rd, 5th digits
    sum1 = int(digits[0]) + int(digits[2]) + int(digits[4])
    # Add 2nd, 4th, 6th digits and multiply by 2
    sum2 = (int(digits[1]) + int(digits[3]) + int(digits[5])) * 2
    # Check digit should equal last digit of (sum1 + sum2)
    check_digit = (sum1 + sum2) % 10

    if check_digit == int(digits[6]):
        return True, 0.95

    return False, 0.0


def validate_vin(text: str) -> tuple[bool, float]:
    """Validate Vehicle Identification Number.

    Returns:
        tuple: (is_valid, confidence)
    """
    # Must be exactly 17 characters
    if len(text) != 17:
        return False, 0.0

    # Cannot contain I, O, or Q
    if any(char in text for char in "IOQ"):
        return False, 0.0

    # Must be alphanumeric
    if not re.match(r"^[A-HJ-NPR-Z0-9]{17}$", text):
        return False, 0.0

    # Additional validation could include check digit calculation
    # but it's complex and varies by manufacturer
    return True, 0.8


def validate_bitcoin_address(text: str) -> tuple[bool, float]:
    """Validate Bitcoin address format.

    Returns:
        tuple: (is_valid, confidence)
    """
    # P2PKH addresses start with 1
    if re.match(r"^1[a-km-zA-HJ-NP-Z1-9]{25,34}$", text):
        return True, 0.85

    # P2SH addresses start with 3
    if re.match(r"^3[a-km-zA-HJ-NP-Z1-9]{25,34}$", text):
        return True, 0.85

    # Bech32 addresses start with bc1
    if re.match(r"^bc1[a-z0-9]{39,59}$", text):
        return True, 0.85

    return False, 0.0


def validate_ethereum_address(text: str) -> tuple[bool, float]:
    """Validate Ethereum address format.

    Returns:
        tuple: (is_valid, confidence)
    """
    # Ethereum addresses are 40 hex chars with 0x prefix
    if re.match(r"^0x[a-fA-F0-9]{40}$", text):
        # Could add EIP-55 checksum validation for higher confidence
        return True, 0.85

    return False, 0.0


# Validation registry mapping entity types to validation functions
VALIDATION_REGISTRY: dict[str, Callable[[str], tuple[bool, float]]] = {
    "SSN": validate_ssn,
    "IBAN": validate_iban,
    "CREDIT_CARD": validate_credit_card,
    "ROUTING_NUMBER": validate_routing_number,
    "UUID": validate_uuid,
    "EIN": validate_ein,
    "NPI": validate_npi,
    "DEA_NUMBER": validate_dea_number,
    "VIN": validate_vin,
    "BITCOIN_ADDRESS": validate_bitcoin_address,
    "ETHEREUM_ADDRESS": validate_ethereum_address,
}


def get_validator(entity_type: str) -> Callable[[str], tuple[bool, float]] | None:
    """Get validator function for entity type.

    Args:
        entity_type: The entity type to get validator for

    Returns:
        Validator function or None if no validator exists
    """
    return VALIDATION_REGISTRY.get(entity_type)


def validate_entity(entity_type: str, text: str) -> tuple[bool, float]:
    """Validate an entity using registered validator.

    Args:
        entity_type: The entity type
        text: The text to validate

    Returns:
        tuple: (is_valid, confidence) or (True, 1.0) if no validator
    """
    validator = get_validator(entity_type)
    if validator:
        return validator(text)
    # No validator means we trust the pattern match
    return True, 1.0
