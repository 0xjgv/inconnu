#!/usr/bin/env python3
"""
Custom Entity Recognition Example

This example demonstrates how to extend Inconnu with custom entity patterns
for industry-specific identifiers, specialized formats, and domain-specific
data types that aren't covered by standard NLP models.

Use Cases:
- Social Security Numbers (SSN)
- Passport numbers
- Vehicle identification (VIN, license plates)
- Medical record numbers (MRN)
- Custom ID formats
- Industry-specific codes
- Cryptocurrency addresses
- API keys and tokens
"""

import re

from inconnu import Inconnu, NERComponent

print("=" * 60)
print("Custom Entity Recognition with Inconnu")
print("=" * 60)

# Example 1: Government ID Patterns
print("\n1. GOVERNMENT IDENTIFIERS")
print("-" * 30)

# Define custom patterns for government IDs
gov_id_components = [
    NERComponent(
        label="SSN", pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), processing_func=None
    ),
    NERComponent(
        label="PASSPORT",
        pattern=re.compile(r"\b[A-Z][0-9]{8}\b"),  # US passport format
        processing_func=None,
    ),
    NERComponent(
        label="DRIVERS_LICENSE",
        pattern=re.compile(r"\b[A-Z]{1,2}\d{6,8}\b"),  # Various state formats
        processing_func=None,
    ),
    NERComponent(
        label="EIN",  # Employer Identification Number
        pattern=re.compile(r"\b\d{2}-\d{7}\b"),
        processing_func=None,
    ),
]

inconnu_gov = Inconnu(custom_components=gov_id_components)

gov_text = """
BACKGROUND CHECK REPORT
Subject: John Michael Smith
SSN: 123-45-6789
Passport: A12345678
Driver's License: CA12345678
Previous Employer: Tech Corp (EIN: 12-3456789)

Verification completed on March 28, 2024 by investigator Sarah Johnson
(Badge #5678). Subject cleared for employment.
"""

redacted_gov = inconnu_gov.redact(gov_text)
print("Redacted government document:")
print(redacted_gov)

# Example 2: Vehicle and Transportation
print("\n\n2. VEHICLE IDENTIFICATION")
print("-" * 30)

# Vehicle-related patterns
vehicle_components = [
    NERComponent(
        label="VIN",
        pattern=re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="LICENSE_PLATE",
        pattern=re.compile(r"\b[A-Z]{2,3}[-\s]?\d{3,4}[-\s]?[A-Z0-9]{1,3}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="FLIGHT_NUMBER",
        pattern=re.compile(r"\b[A-Z]{2}\d{3,4}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="CONTAINER_ID",
        pattern=re.compile(r"\b[A-Z]{4}\d{7}\b"),  # Shipping container
        processing_func=None,
    ),
]

inconnu_vehicle = Inconnu(custom_components=vehicle_components)

vehicle_report = """
ACCIDENT REPORT
Date: March 28, 2024
Location: Interstate 5, Seattle, WA

Vehicle 1:
- License Plate: WA 123 ABC
- VIN: 1HGBH41JXMN109186
- Driver: Robert Chen (License: WA567890)

Vehicle 2:
- License Plate: OR-4567-XYZ
- VIN: 2HGFG12688H541234
- Driver: Maria Garcia

Witness arrived on United Airlines flight UA1234 from San Francisco.
Damaged cargo container MSCU1234567 was removed by crane.
"""

redacted_vehicle = inconnu_vehicle.redact(vehicle_report)
print("Redacted vehicle report:")
print(redacted_vehicle)

# Example 3: Medical and Healthcare IDs
print("\n\n3. MEDICAL IDENTIFIERS")
print("-" * 30)

# Medical record patterns
medical_components = [
    NERComponent(
        label="MRN",  # Medical Record Number
        pattern=re.compile(r"\bMRN[:\s]?\d{6,10}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="NPI",  # National Provider Identifier
        pattern=re.compile(r"\b\d{10}\b"),  # Validate checksum in real use
        processing_func=None,
    ),
    NERComponent(
        label="DEA_NUMBER",
        pattern=re.compile(r"\b[A-Z]{2}\d{7}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="ICD_CODE",
        pattern=re.compile(r"\b[A-Z]\d{2}\.?\d{0,3}\b"),
        processing_func=None,
    ),
]

inconnu_medical = Inconnu(custom_components=medical_components)

medical_text = """
PATIENT DISCHARGE SUMMARY
Patient: Jennifer Smith (MRN: 12345678)
Attending Physician: Dr. Michael Brown (NPI: 1234567890, DEA: BM1234567)

Diagnosis:
- Primary: Type 2 Diabetes (ICD: E11.9)
- Secondary: Hypertension (ICD: I10)

Medications prescribed:
- Metformin 500mg BID (Rx# 9876543)
- Lisinopril 10mg QD (Rx# 9876544)

Follow-up with endocrinologist Dr. Sarah Lee (NPI: 0987654321)
"""

redacted_medical = inconnu_medical.redact(medical_text)
print("Redacted medical document:")
print(redacted_medical)

# Example 4: Financial and Crypto
print("\n\n4. FINANCIAL & CRYPTOCURRENCY")
print("-" * 30)

# Financial patterns including crypto
financial_components = [
    NERComponent(
        label="BITCOIN_ADDRESS",
        pattern=re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|bc1[a-z0-9]{39,59}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="ETHEREUM_ADDRESS",
        pattern=re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="CREDIT_CARD",
        pattern=re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="ROUTING_NUMBER", pattern=re.compile(r"\b\d{9}\b"), processing_func=None
    ),
    NERComponent(
        label="SWIFT_CODE",
        pattern=re.compile(r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"),
        processing_func=None,
    ),
]

inconnu_finance = Inconnu(custom_components=financial_components)

finance_text = """
TRANSACTION INVESTIGATION REPORT

Suspicious activity detected:
1. Wire transfer from account 123456789 (routing: 021000021) to
   Bitcoin address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
   Amount: $50,000

2. Ethereum transaction from wallet 0x742d35Cc6634C0532925a3b844Bc9e7595f6E123
   to unknown address. Gas fees paid with card 4532 1234 5678 9012.

3. International transfer via SWIFT CHASUS33 to account in Switzerland.

Investigating officer: Agent Smith (Badge #007)
"""

redacted_finance = inconnu_finance.redact(finance_text)
print("Redacted financial report:")
print(redacted_finance)

# Example 5: Technology and Security
print("\n\n5. TECHNOLOGY IDENTIFIERS")
print("-" * 30)

# Tech and security patterns
tech_components = [
    NERComponent(
        label="API_KEY",
        pattern=re.compile(r"\b[A-Za-z0-9]{32,}\b"),  # Generic API key pattern
        processing_func=None,
    ),
    NERComponent(
        label="MAC_ADDRESS",
        pattern=re.compile(r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="UUID",
        pattern=re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
        ),
        processing_func=None,
    ),
    NERComponent(
        label="JWT_TOKEN",
        pattern=re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
        processing_func=None,
    ),
]

inconnu_tech = Inconnu(custom_components=tech_components)

tech_log = """
SECURITY INCIDENT LOG
Timestamp: 2024-03-28T10:15:30Z

Unauthorized access attempt detected:
- Source IP: 192.168.1.100
- MAC Address: 00:1B:44:11:3A:B7
- Device UUID: 550e8400-e29b-41d4-a716-446655440000
- Attempted API key: sk_live_4eC39HqLyjWDarjtT1zdp7dc
- Invalid JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c

User: john.doe@company.com attempting to access restricted resource.
"""

redacted_tech = inconnu_tech.redact(tech_log)
print("Redacted security log:")
print(redacted_tech)

# Example 6: Custom Validation Functions
print("\n\n6. CUSTOM VALIDATION FUNCTIONS")
print("-" * 30)


def validate_and_process_ssn(doc):
    """Custom function to validate and process SSN patterns"""
    from spacy.tokens import Span

    # Pattern for SSN with validation
    ssn_pattern = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")

    new_ents = []
    for match in ssn_pattern.finditer(doc.text):
        # Additional validation (e.g., check if not 000, 666, or 900-999)
        area = match.group(1)
        if area not in ["000", "666"] and not (900 <= int(area) <= 999):
            start, end = match.span()
            span = doc.char_span(start, end)
            if span:
                span = Span(doc, span.start, span.end, label="SSN_VALIDATED")
                new_ents.append(span)

    # Merge with existing entities
    doc.ents = list(doc.ents) + new_ents
    return doc


# Create component with validation function
validated_components = [
    NERComponent(
        label="SSN_VALIDATED",
        pattern=None,  # Pattern handled by function
        processing_func=validate_and_process_ssn,
    ),
    NERComponent(
        label="PHONE_US",
        pattern=re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"
        ),
        processing_func=None,
    ),
]

inconnu_validated = Inconnu(custom_components=validated_components)

validated_text = """
Valid SSN: 123-45-6789
Invalid SSN: 000-12-3456 (should not be redacted)
Invalid SSN: 666-12-3456 (should not be redacted)
Invalid SSN: 901-12-3456 (should not be redacted)

Phone numbers:
- US Format: (555) 123-4567
- International: +1-555-234-5678
- Simple: 555.345.6789
"""

redacted_validated = inconnu_validated.redact(validated_text)
print("Validation-aware redaction:")
print(redacted_validated)

# Example 7: Combining Multiple Custom Patterns
print("\n\n7. COMPREHENSIVE CUSTOM ENTITY SET")
print("-" * 30)

# Combine all patterns for comprehensive coverage
all_components = (
    gov_id_components
    + vehicle_components
    + medical_components
    + financial_components
    + tech_components
)

inconnu_comprehensive = Inconnu(custom_components=all_components)

comprehensive_text = """
CONFIDENTIAL INVESTIGATION REPORT
Case #2024-INV-1234

Subject: Data Breach Investigation
Date: March 28, 2024

Subject Information:
- Name: John Doe
- SSN: 456-78-9012
- Passport: B87654321
- Driver's License: NY12345678

Financial Impact:
- Compromised credit card: 4111 1111 1111 1111
- Bitcoin wallet accessed: 3FKj3v2KLbJ9hVKiYmP3v7oLwRmKm6XXX4
- Estimated loss: $250,000

Technical Details:
- Breach via API key: ak_live_abcdef123456789012345678901234567890
- Server MAC: AA:BB:CC:DD:EE:FF
- Session UUID: 123e4567-e89b-12d3-a456-426614174000

Medical records accessed:
- Patient MRN: 87654321
- Provider NPI: 9876543210

Vehicle used in physical breach:
- License plate: CA 7SAM123
- VIN: 1HGCM82633A123456

This report is classified. Distribution limited to authorized personnel.
"""

final_redacted = inconnu_comprehensive.redact(comprehensive_text)
print("Fully redacted comprehensive report:")
print(final_redacted)

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR CUSTOM ENTITIES")
print("=" * 60)
print("""
1. PATTERN DESIGN:
   - Be specific to avoid false positives
   - Test patterns thoroughly
   - Consider regional variations
   - Use anchors and boundaries

2. VALIDATION:
   - Add checksum validation for IDs
   - Verify format constraints
   - Use processing functions for complex logic
   - Filter out test/invalid patterns

3. PERFORMANCE:
   - Compile regex patterns once
   - Order patterns by frequency
   - Combine similar patterns
   - Limit pattern complexity

4. INDUSTRY SPECIFIC:
   - Healthcare: MRN, NPI, DEA, ICD codes
   - Finance: Account numbers, routing, crypto
   - Government: SSN, passport, licenses
   - Technology: API keys, MACs, UUIDs

5. MAINTENANCE:
   - Document pattern purposes
   - Version control patterns
   - Test with real-world data
   - Update for new formats

Common Patterns Reference:
- SSN: \\b\\d{3}-\\d{2}-\\d{4}\\b
- Credit Card: \\b(?:\\d[ -]*?){13,19}\\b
- Email: Already included in base Inconnu
- Phone: Already included with international support
- UUID: \\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\\b
""")

print("\nExample completed successfully!")
