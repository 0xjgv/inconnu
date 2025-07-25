#!/usr/bin/env python3
"""
Financial Services Data Anonymization Example

This example demonstrates how to use Inconnu for processing financial data
including transaction logs, customer communications, loan applications, and
fraud reports while maintaining PCI DSS compliance and regulatory requirements.

Use Cases:
- Transaction logs and audit trails
- Customer complaint emails
- Loan and credit applications
- Fraud investigation reports
- Bank statements
- Wire transfer records
"""

import re

from inconnu import Inconnu, NERComponent

# Initialize Inconnu
inconnu = Inconnu()

print("=" * 60)
print("Financial Services Data Processing with Inconnu")
print("=" * 60)

# Example 1: Transaction Log Processing
print("\n1. TRANSACTION LOG ANONYMIZATION")
print("-" * 30)

transaction_log = """
TRANSACTION LOG - March 28, 2024

Trans ID: TXN-2024-03-28-001
Timestamp: 2024-03-28 09:15:32 UTC
Customer: John Michael Smith
Account: ****1234 (Checking)
SSN: XXX-XX-6789
Email: john.smith@email.com
Phone: +1 (555) 123-4567

Transaction Type: Wire Transfer
Amount: $25,000.00 USD
Destination:
  Beneficiary: Maria Garcia Rodriguez
  Bank: Banco Nacional de Mexico
  SWIFT: BNMXMXMM
  IBAN: MX12 3456 7890 1234 5678 90
  Reference: Invoice INV-2024-0892

Fee: $45.00
Status: COMPLETED
IP Address: 192.168.1.100
Device: iPhone 14 Pro (iOS 17.3)

Authorized by: Sarah Johnson (Relationship Manager)
Branch: Downtown San Francisco (ID: SF-001)
Contact: sjohnson@megabank.com
"""

# Basic anonymization for audit logs
redacted_log = inconnu.redact(transaction_log)
print("Anonymized Transaction Log:")
print(redacted_log[:600] + "...")

# Example 2: Customer Complaint Email
print("\n\n2. CUSTOMER COMPLAINT PROCESSING")
print("-" * 30)

complaint_email = """
From: angry.customer@gmail.com
To: support@megabank.com
Subject: Fraudulent Charges on Credit Card
Date: March 25, 2024

Dear MegaBank,

I am writing to report unauthorized transactions on my credit card ending in 4532.
My name is Robert Chen, and my account number is 1234-5678-9012-4532.

On March 23, 2024, I noticed the following suspicious charges:
1. $2,500 at "Luxury Electronics" in Miami, FL (I live in Seattle, WA)
2. $1,200 at "Designer Boutique" in Miami, FL
3. $800 cash advance at ATM location 12345 in Miami Beach

I have not traveled to Florida. My card was in my possession at my home address:
789 Pine Street, Apt 45, Seattle, WA 98101.

Please investigate immediately. You can reach me at:
- Phone: (206) 555-9876
- Alt Phone: (206) 555-4321
- Work: Microsoft Corporation, Building 42

I've already filed a police report (Case #2024-12345) with Officer James Wilson.

My mother, Linda Chen (425-555-1111), is an authorized user and can verify she
hasn't made these charges either.

Sincerely,
Robert Chen
Customer Since: 2015
Last 4 SSN: 5678
DOB: 05/15/1985
"""

# Pseudonymize for investigation while maintaining traceability
complaint_redacted, complaint_map = inconnu.pseudonymize(complaint_email)
print("Pseudonymized Complaint (for investigation):")
print(complaint_redacted[:500] + "...")

print("\nKey Entity Mappings:")
financial_entities = {
    k: v
    for k, v in complaint_map.items()
    if any(label in k for label in ["MONEY", "DATE", "GPE"])
}
for key, value in list(financial_entities.items())[:5]:
    print(f"  {key}: {value}")

# Example 3: Loan Application with Financial Details
print("\n\n3. LOAN APPLICATION PROCESSING")
print("-" * 30)

loan_application = """
MORTGAGE LOAN APPLICATION
Application ID: ML-2024-SF-0892
Date: March 28, 2024

APPLICANT INFORMATION
Primary Applicant: Jennifer Martinez
SSN: 123-45-6789
DOB: July 15, 1982
Current Address: 456 Oak Avenue, San Francisco, CA 94110
Phone: (415) 555-2345
Email: j.martinez@techcompany.com
Employer: TechCorp Inc.
Position: Senior Software Engineer
Annual Income: $185,000

Co-Applicant: Michael Martinez
SSN: 987-65-4321
DOB: March 22, 1980
Employer: StartupXYZ
Annual Income: $125,000

LOAN DETAILS
Purchase Price: $1,500,000
Down Payment: $300,000 (20%)
Loan Amount: $1,200,000
Interest Rate: 6.75% (30-year fixed)

ASSETS
Checking (Wells Fargo ****5678): $85,000
Savings (Chase ****9012): $250,000
401k (Fidelity): $450,000
RSUs (TechCorp): $320,000 (vesting over 4 years)
Crypto (Coinbase): $75,000 BTC

LIABILITIES
Auto Loan (Toyota Financial): $25,000 remaining
Student Loans: $0 (paid off)
Credit Cards: $3,500 total balance

REFERENCES
Current Landlord: David Wong - (415) 555-8888
Personal: Dr. Sarah Kim - (650) 555-3333
"""

# Anonymize for training ML models
training_data = inconnu.redact(loan_application)
print("Anonymized Loan Application (for ML training):")
print(training_data[:600] + "...")

# Example 4: Fraud Investigation Report
print("\n\n4. FRAUD INVESTIGATION REPORT")
print("-" * 30)

# Add custom financial patterns
financial_components = [
    NERComponent(
        label="CREDIT_CARD",
        pattern=re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="SWIFT_CODE",
        pattern=re.compile(r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"),
        processing_func=None,
    ),
    NERComponent(
        label="CRYPTO_WALLET",
        pattern=re.compile(r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="ROUTING_NUMBER", pattern=re.compile(r"\b\d{9}\b"), processing_func=None
    ),
]

inconnu_financial = Inconnu(custom_components=financial_components)

fraud_report = """
FRAUD INVESTIGATION REPORT
Case ID: FRD-2024-0156
Investigator: Senior Analyst Lisa Thompson

SUMMARY
Suspected money laundering scheme involving multiple accounts and cryptocurrency.

INVOLVED PARTIES
1. Primary Suspect: Alexander Volkov
   - SSN: 456-78-9012
   - Address: 123 Luxury Tower, Miami, FL 33131
   - Accounts: Chase ****8901, BofA ****2345
   - Known Associates: Ivan Petrov, Natasha Romanova

2. Shell Company: GlobalTech Solutions LLC
   - EIN: 12-3456789
   - Registered Agent: Maria Fernandez
   - Bank: First National, Routing: 123456789
   - Account: 9876543210

SUSPICIOUS ACTIVITIES
- March 1: Wire transfer $500,000 from Volkov to GlobalTech
- March 5: GlobalTech purchased BTC worth $480,000
- March 6: BTC sent to wallet bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
- March 8: Similar amount appeared in Swiss account CH93 0076 2011 6238 5295 7

EVIDENCE
- IP logs show access from 185.220.101.45 (TOR exit node)
- Phone intercepts mention "package arriving Thursday"
- Emails between volkov@protonmail.com and darkmoney@tutanota.com

RECOMMENDATION
Freeze all accounts immediately. Contact FBI Financial Crimes at (202) 555-0123.
Coordinate with Interpol contact: Agent James Bond (+44 20 7946 0000)
"""

redacted_fraud = inconnu_financial.redact(fraud_report)
print("Redacted Fraud Report (for compliance filing):")
print(redacted_fraud)

# Example 5: Batch Processing Bank Statements
print("\n\n5. BATCH BANK STATEMENT PROCESSING")
print("-" * 30)

bank_statements = [
    "Statement for John Doe, Account ****5678: Opening $10,234.56, Closing $8,123.45",
    "Maria Garcia transferred $5,000 to Carlos Rodriguez on March 15, 2024",
    "ATM withdrawal $500 by James Smith at 123 Main St, Card ****9012",
]

print(f"Processing {len(bank_statements)} bank statements...")
anonymized_statements = inconnu.redact_batch(bank_statements)

for i, (original, anonymized) in enumerate(zip(bank_statements, anonymized_statements)):
    print(f"\nStatement {i + 1}:")
    print(f"  Original: {original}")
    print(f"  Anonymized: {anonymized}")

# Example 6: Wire Transfer with International Details
print("\n\n6. INTERNATIONAL WIRE TRANSFER")
print("-" * 30)

wire_transfer = """
WIRE TRANSFER CONFIRMATION
Reference: WT-2024-03-28-789012

SENDER INFORMATION
Name: TechCorp International Ltd
Account: 1234567890
Address: 100 Tech Plaza, San Francisco, CA 94105
Contact: CFO Michael Chen - mchen@techcorp.com
Phone: +1 415-555-0100

BENEFICIARY INFORMATION
Name: Software Consulting GmbH
Bank: Deutsche Bank AG
SWIFT/BIC: DEUTDEFF
IBAN: DE89 3704 0044 0532 0130 00
Address: Taunusanlage 12, 60325 Frankfurt, Germany
Contact: Hans Mueller - hmueller@softwareconsulting.de

TRANSACTION DETAILS
Amount: $150,000.00 USD
Purpose: Software development services Q1 2024
Exchange Rate: 1 USD = 0.92 EUR
Beneficiary receives: €138,000.00
Fees: $75.00 (shared)

COMPLIANCE
- OFAC screening: PASSED
- AML check: VERIFIED
- Approved by: Sarah Johnson, Compliance Officer
- Timestamp: 2024-03-28 14:30:00 PST
"""

# Process for audit trail
result = inconnu(text=wire_transfer)
print("Wire Transfer Processing Summary:")
print(f"  Entities found: {len(result.entity_map)}")
print(f"  Processing time: {result.processing_time_ms:.2f}ms")
print(f"  Anonymized preview: {result.redacted_text[:200]}...")

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR FINANCIAL DATA")
print("=" * 60)
print("""
1. PCI DSS COMPLIANCE:
   - Never log full credit card numbers
   - Mask account numbers appropriately
   - Implement strong access controls

2. REGULATORY REQUIREMENTS:
   - Maintain audit trails for 7 years
   - Enable transaction reconstruction
   - Support SAR filing requirements

3. CUSTOM PATTERNS:
   - Add SWIFT/BIC code detection
   - Include cryptocurrency addresses
   - Detect routing and account numbers

4. DATA RETENTION:
   - Follow regional requirements (GDPR, CCPA)
   - Implement secure deletion
   - Maintain investigation capabilities

5. FRAUD PREVENTION:
   - Preserve patterns for ML models
   - Enable anomaly detection
   - Support real-time processing
""")

print("\nExample completed successfully!")
