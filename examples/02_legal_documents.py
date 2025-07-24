#!/usr/bin/env python3
"""
Legal Documents Redaction Example

This example demonstrates how to use Inconnu for redacting sensitive information
from legal documents including court cases, contracts, witness statements, and
legal correspondence while maintaining document integrity and legal compliance.

Use Cases:
- Court case documents
- Contracts and agreements
- Witness statements
- Legal correspondence
- Discovery documents
- Public records requests
"""

import re

from inconnu import Inconnu, NERComponent

# Initialize Inconnu
inconnu = Inconnu()

print("=" * 60)
print("Legal Document Redaction with Inconnu")
print("=" * 60)

# Example 1: Court Case Document
print("\n1. COURT CASE DOCUMENT")
print("-" * 30)

court_document = """
IN THE DISTRICT COURT OF TRAVIS COUNTY, TEXAS
CASE NO. 2024-CV-1234

PLAINTIFF: Jennifer Martinez
Address: 456 Oak Street, Austin, TX 78701
Phone: (512) 555-0123
Email: j.martinez@email.com

v.

DEFENDANT: TechCorp Industries, LLC
Represented by: David Johnson, Esq.
Johnson & Associates Law Firm
789 Congress Avenue, Suite 200, Austin, TX 78701
Bar No: TX-12345

COMPLAINT FOR WRONGFUL TERMINATION

1. Plaintiff Jennifer Martinez was employed by Defendant from January 15, 2020
   until her termination on December 10, 2023.

2. On November 28, 2023, Plaintiff reported sexual harassment by her supervisor,
   Michael Thompson, to HR Director Sarah Williams via email to hr@techcorp.com.

3. Plaintiff's colleague, Robert Chen (r.chen@techcorp.com), witnessed multiple
   incidents of harassment occurring at the Austin office located at
   1234 Technology Drive, Austin, TX 78750.

4. Following her complaint, Plaintiff was terminated on December 10, 2023,
   allegedly for "performance issues" despite receiving excellent reviews from
   her previous supervisor, Lisa Anderson.

WHEREFORE, Plaintiff demands judgment against Defendant for damages exceeding
$500,000, including back pay, front pay, and punitive damages.

Submitted this 15th day of March, 2024.

/s/ Amanda Rodriguez
Amanda Rodriguez, Esq.
State Bar No: TX-67890
Rodriguez Legal Services
321 Main Street, Austin, TX 78701
(512) 555-0456
arodriguez@rodriguezlaw.com
"""

# Anonymize for public records
redacted_court = inconnu.redact(court_document)
print("Redacted for Public Release (excerpt):")
print(redacted_court[:600] + "...")

# Example 2: Contract with Confidential Terms
print("\n\n2. CONFIDENTIAL CONTRACT")
print("-" * 30)

contract = """
NON-DISCLOSURE AGREEMENT

This Agreement is entered into as of April 1, 2024, between:

DISCLOSING PARTY: Innovative Solutions Inc.
CEO: Thomas Anderson
Address: 100 Innovation Way, San Francisco, CA 94105
Tax ID: 12-3456789
Contact: legal@innovativesolutions.com

RECEIVING PARTY: John David Smith
SSN: 555-12-3456
Address: 789 Market Street, Apt 45B, San Francisco, CA 94103
Phone: (415) 555-7890
Email: jdsmith.consulting@gmail.com

WHEREAS, Disclosing Party possesses certain confidential information relating to
Project Quantum (internal code: QTM-2024-789) with an estimated value of
$2.5 million in R&D investment;

WHEREAS, Receiving Party desires access to such information for the purpose of
evaluating potential consulting services;

NOW THEREFORE, the parties agree:

1. CONFIDENTIAL INFORMATION includes all technical specifications, financial
   projections showing expected revenue of $10-15 million by Q4 2025, and
   customer lists including contacts at Apple Inc. (Tim Cook's direct line:
   408-555-0001) and Google LLC (Sundar Pichai's assistant: 650-555-0002).

2. TERM: This Agreement shall remain in effect until December 31, 2026.

3. PENALTIES: Breach of this agreement may result in liquidated damages of
   $1,000,000 plus attorney fees.

Signed:
Thomas Anderson (Apr 1, 2024)
John David Smith (Apr 1, 2024)

Witnessed by: Maria Garcia, Notary Public, Commission #SF-123456
"""

# Pseudonymize with mapping for internal use
redacted_contract, contract_map = inconnu.pseudonymize(contract)
print("Pseudonymized Contract (first 500 chars):")
print(redacted_contract[:500] + "...")

print("\nEntity Map Sample (5 entries):")
for key, value in list(contract_map.items())[:5]:
    print(f"  {key}: {value}")

# Example 3: Witness Statement with Sensitive Details
print("\n\n3. WITNESS STATEMENT")
print("-" * 30)

witness_statement = """
WITNESS STATEMENT
Case: State v. Marcus Johnson
Case No: 2024-CR-5678
Date: March 20, 2024

I, Elena Rodriguez, residing at 234 Pine Street, Denver, CO 80203, hereby state:

1. On February 15, 2024, at approximately 10:30 PM, I was walking my dog near
   the intersection of Colfax Avenue and Broadway Street in Denver.

2. I witnessed Marcus Johnson (whom I recognize as my neighbor from apartment 4B)
   arguing with another man I later learned was James Wilson from unit 6A.

3. I heard Mr. Wilson say "You owe me $5,000 for the drugs I gave you last month."
   Mr. Johnson responded "I already paid your partner Carlos at 303-555-9876."

4. The argument escalated and Mr. Wilson pulled out what appeared to be a knife.
   Mr. Johnson defended himself by pushing Mr. Wilson, who fell and hit his head.

5. I immediately called 911 from my cell phone (720-555-3456) and rendered aid
   to Mr. Wilson until paramedics arrived.

6. Officer Patricia Chen (Badge #1234) took my initial statement at the scene.

7. I am willing to testify in court. You can reach me at elena.r@email.com or
   my work number (303) 555-7890 at Denver General Hospital where I work as a
   nurse in the ER department under Dr. Michael Brown.

Signed: Elena Rodriguez
Date: March 20, 2024
Witnessed by: Det. Robert Kim, Denver PD, Badge #5678
"""

# Redact for case summary
redacted_statement = inconnu.redact(witness_statement)
print("Redacted Witness Statement:")
print(redacted_statement)

# Example 4: Batch Processing Legal Discovery Documents
print("\n\n4. BATCH DISCOVERY DOCUMENT PROCESSING")
print("-" * 30)

discovery_emails = [
    "From: CEO@company.com - 'John, the insider trading at $45/share needs to stop'",
    "To: CFO Jane Smith - 'Wire $2M to account CH1234567890 in Zurich by Friday'",
    "Meeting notes: Board member Alice Chen discussed merger with Bob Wilson of CompetitorCorp",
]

print(f"Processing {len(discovery_emails)} discovery documents...")
redacted_discovery = inconnu.redact_batch(discovery_emails)

for i, (original, redacted) in enumerate(zip(discovery_emails, redacted_discovery)):
    print(f"\nDocument {i + 1}:")
    print(f"  Original: {original}")
    print(f"  Redacted: {redacted}")

# Example 5: Custom Legal Entity Patterns
print("\n\n5. CUSTOM LEGAL ENTITIES")
print("-" * 30)

# Add patterns for legal-specific identifiers
legal_components = [
    NERComponent(
        pattern=re.compile(r"\b\d{4}-[A-Z]{2}-\d{4,6}\b"),
        processing_func=None,
        label="CASE_NUMBER",
    ),
    NERComponent(
        pattern=re.compile(r"\b(?:Bar No\.|State Bar No:?)\s*[A-Z]{2}-?\d{5,6}\b"),
        processing_func=None,
        label="BAR_NUMBER",
    ),
    NERComponent(
        pattern=re.compile(
            r"\b\d+\s+U\.S\.C\.\s+§\s*\d+\b|\b\d+\s+C\.F\.R\.\s+§\s*\d+\.\d+\b"
        ),
        processing_func=None,
        label="STATUTE",
    ),
]

inconnu_legal = Inconnu(custom_components=legal_components)

legal_memo = """
MEMORANDUM
RE: Violation of 18 U.S.C. § 1341 (Mail Fraud)
Case No: 2024-CR-98765

Attorney Sarah Mitchell (Bar No. TX-54321) has identified potential violations of
15 U.S.C. § 78j (Securities Exchange Act) by defendant Mark Thompson. Previous
similar case (2023-CV-11111) resulted in penalties under 26 C.F.R. § 1.6662-4.

Recommend filing motion citing precedent from case 2022-CR-33333.
"""

redacted_memo = inconnu_legal.redact(legal_memo)
print("Legal Memo with Custom Entity Detection:")
print(redacted_memo)

# Best Practices for Legal Documents
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR LEGAL DOCUMENT REDACTION")
print("=" * 60)
print("""
1. COMPLIANCE REQUIREMENTS:
   - Follow jurisdiction-specific redaction rules
   - Maintain privilege for attorney-client communications
   - Preserve document authenticity and chain of custody

2. ENTITY DETECTION:
   - Add patterns for case numbers, bar numbers, docket numbers
   - Include financial account patterns
   - Detect legal citations and statute references

3. REDACTION LEVELS:
   - Public release: Full anonymization
   - Court filing: Partial redaction per rules
   - Internal review: Pseudonymization with mapping

4. AUDIT REQUIREMENTS:
   - Log all redaction activities
   - Maintain original documents securely
   - Track who performed redactions and when

5. QUALITY CONTROL:
   - Manual review of redacted documents
   - Verify all PII is properly redacted
   - Ensure legal context remains clear
""")

print("\nExample completed successfully!")
