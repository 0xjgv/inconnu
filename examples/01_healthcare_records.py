#!/usr/bin/env python3
"""
Healthcare Records Anonymization Example

This example demonstrates how to use Inconnu to anonymize sensitive medical data
including patient records, clinical notes, and research data while maintaining
HIPAA compliance and data utility for medical research.

Use Cases:
- Patient admission forms
- Medical consultation notes
- Prescription records
- Clinical trial data
- Medical research datasets
"""

import re

from inconnu import Inconnu, NERComponent

custom_components_generic = [
    NERComponent(
        pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        label="SOCIAL_SECURITY_NUMBER",
        processing_func=None,
    ),
    NERComponent(
        pattern=re.compile(r"\d{2}/\d{2}/\d{4}"),
        processing_func=None,
        label="DATE_OF_BIRTH",
    ),
    NERComponent(
        pattern=re.compile(r"\bMRN:\s*\d{6,10}\b"),
        label="MEDICAL_RECORD_NUMBER",
        processing_func=None,
    ),
]

# Initialize Inconnu with default settings
inconnu = Inconnu(custom_components=custom_components_generic)

print("=" * 60)
print("Healthcare Records Anonymization with Inconnu")
print("=" * 60)

# Example 1: Patient Admission Form
print("\n1. PATIENT ADMISSION FORM")
print("-" * 30)

admission_form = """
PATIENT ADMISSION FORM
Date: March 15, 2024

Patient Name: Sarah Johnson
Date of Birth: July 8, 1985
SSN: 123-45-6789
Address: 742 Evergreen Terrace, Springfield, IL 62701
Phone: (555) 123-4567
Email: sarah.johnson@email.com
Emergency Contact: Michael Johnson (Husband) - (555) 987-6543

Primary Insurance: Blue Cross Blue Shield
Policy Number: BCB123456789
Group Number: GRP456789

Reason for Visit: Severe abdominal pain, fever 102°F
Allergies: Penicillin, Latex
Current Medications: Metformin 500mg, Lisinopril 10mg

Attending Physician: Dr. Emily Chen, MD
"""

# Basic anonymization
print("Original:")
print(admission_form[:200] + "...")

redacted = inconnu.redact(admission_form)
print("\nAnonymized:")
print(redacted[:400] + "...")

# Example 2: Medical Consultation Notes
print("\n\n2. MEDICAL CONSULTATION NOTES")
print("-" * 30)

consultation_notes = """
CONSULTATION NOTES
Patient: Robert Martinez (MRN: 456789)
Date: March 15, 2024
Provider: Dr. James Wilson, Cardiology

Chief Complaint:
Mr. Martinez, a 58-year-old male from Houston, Texas, presents with chest pain
and shortness of breath for the past 3 days.

History of Present Illness:
Patient reports intermittent chest pain, rated 7/10, radiating to left arm.
Associated with exertion. Sister Maria Martinez (contact: 713-555-0123) brought
him to the ER yesterday at 2:30 PM.

Past Medical History:
- Hypertension (diagnosed 2018)
- Type 2 Diabetes (diagnosed 2020)
- Previous MI in January 2022 at Memorial Hermann Hospital

Social History:
Lives with wife Rosa Martinez at 1234 Oak Street, Houston, TX 77001.
Works as an accountant at Johnson & Associates. Non-smoker.

Assessment and Plan:
1. Acute coronary syndrome - Order ECG, troponin levels
2. Continue aspirin 81mg, add clopidogrel 75mg
3. Cardiology consult requested
4. Follow up in 1 week or sooner if symptoms worsen

Electronically signed by: Dr. James Wilson, MD
License #: TX123456
"""

# Pseudonymization with entity mapping for potential de-identification
redacted_notes, entity_map = inconnu.pseudonymize(consultation_notes)
print("Pseudonymized Notes (first 400 chars):")
print(redacted_notes[:400] + "...")

print("\nEntity Mapping (for secure storage):")
for key, value in list(entity_map.items())[:5]:
    print(f"  {key}: {value}")
print(f"  ... and {len(entity_map) - 5} more entities")

# Example 3: Clinical Trial Data with Custom Identifiers
print("\n\n3. CLINICAL TRIAL DATA")
print("-" * 30)

# Add custom patterns for clinical trial identifiers
custom_components_clinical = [
    NERComponent(
        label="TRIAL_ID", pattern=re.compile(r"\bNCT\d{8}\b"), processing_func=None
    ),
    NERComponent(
        pattern=re.compile(r"\bSUB-\d{4}-[A-Z]{2}\b"),
        processing_func=None,
        label="SUBJECT_ID",
    ),
    NERComponent(
        pattern=re.compile(r"\bSITE-[A-Z]{2}-\d{3}\b"),
        processing_func=None,
        label="SITE_ID",
    ),
]

inconnu_clinical = Inconnu(custom_components=custom_components_clinical)

clinical_trial_data = """
CLINICAL TRIAL: NCT12345678 - Phase III Diabetes Medication Study
Site: SITE-TX-001 (Austin Medical Center)
Principal Investigator: Dr. Lisa Chang, MD, PhD

Subject: SUB-2024-AB
Name: Jennifer Thompson
Age: 45 years
Enrollment Date: January 15, 2024
Contact: jenny.thompson@email.com, (512) 555-0199

Week 4 Assessment:
- HbA1c: 7.2% (baseline: 8.5%)
- Weight: 165 lbs (baseline: 172 lbs)
- Blood Pressure: 128/82 mmHg
- Adverse Events: Mild nausea reported on Day 22

Next Visit: February 12, 2024 at 9:00 AM
Study Coordinator: Maria Rodriguez (maria.rodriguez@austinmed.org)
"""

redacted_trial = inconnu_clinical.redact(clinical_trial_data)
print("Anonymized Clinical Trial Data:")
print(redacted_trial)

# Example 4: Batch Processing Medical Records
print("\n\n4. BATCH PROCESSING MULTIPLE RECORDS")
print("-" * 30)

# Simulate multiple patient discharge summaries
discharge_summaries = [
    "Patient John Smith (DOB: 01/15/1970) discharged on 03/10/2024. Follow up with Dr. Brown.",
    "Maria Garcia (MRN: 789012) stable condition. Discharged to home at 123 Main St, Austin, TX.",
    "David Lee transferred to skilled nursing facility. Contact number: (415) 555-0123.",
]

print("Processing", len(discharge_summaries), "discharge summaries...")
anonymized_summaries = inconnu.redact_batch(discharge_summaries)

for i, (original, anonymized) in enumerate(
    zip(discharge_summaries, anonymized_summaries)
):
    print(f"\nRecord {i + 1}:")
    print(f"  Original: {original}")
    print(f"  Anonymized: {anonymized}")

# Example 5: HIPAA Compliance and Audit Trail
print("\n\n5. HIPAA COMPLIANCE FEATURES")
print("-" * 30)

# Process with full metadata for audit trail
sensitive_record = """
HIV Test Results - CONFIDENTIAL
Patient: Michael Chen, SSN: 987-65-4321
Test Date: March 14, 2024
Result: Positive
Physician: Dr. Sarah Kim
Next Appointment: March 28, 2024
"""

# Use the full processing method to get complete metadata
result = inconnu(text=sensitive_record)
print("Audit Trail Information:")
print(f"  Processing Time: {result.processing_time_ms:.2f}ms")
print(f"  Timestamp: {result.timestamp}")
print(f"  Text Hash: {result.hashed_id[:16]}...")
print(f"  Entities Found: {len(result.entity_map)}")
print(f"  Redacted Text: {result.redacted_text[:50]}...")

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR HEALTHCARE DATA")
print("=" * 60)
print("""
1. HIPAA Compliance:
   - Always use pseudonymization for data that may need de-identification
   - Store entity mappings securely and separately from anonymized data
   - Implement access controls and audit logging

2. Custom Identifiers:
   - Add patterns for MRN, trial IDs, and facility-specific codes
   - Consider regional variations in ID formats

3. Performance Considerations:
   - Use batch processing for large datasets
   - Consider async processing for web applications
   - Monitor processing times for SLA compliance

4. Data Retention:
   - Configure retention policies based on regulations
   - Implement secure deletion of entity mappings
   - Maintain audit trails for compliance

5. Quality Assurance:
   - Validate anonymization completeness
   - Test with diverse data formats
   - Regular updates for new entity types
""")

print("\nExample completed successfully!")
