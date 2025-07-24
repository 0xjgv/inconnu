#!/usr/bin/env python3
"""
HR & Employment Data Anonymization Example

This example demonstrates how to use Inconnu for processing HR and employment
data including resumes, performance reviews, interview notes, and employee
records while ensuring fair hiring practices and privacy compliance.

Use Cases:
- Resume/CV anonymization for bias-free screening
- Employee performance reviews
- Interview feedback forms
- Exit interview transcripts
- Salary and compensation data
- Background check reports
"""

import asyncio
import re

from inconnu import Inconnu, NERComponent

# Initialize Inconnu
inconnu = Inconnu()

print("=" * 60)
print("HR & Employment Data Processing with Inconnu")
print("=" * 60)

# Example 1: Resume Anonymization for Bias-Free Screening
print("\n1. RESUME ANONYMIZATION")
print("-" * 30)

resume = """
CURRICULUM VITAE

Sarah Elizabeth Johnson
Email: sarah.johnson@email.com | Phone: (555) 123-4567
LinkedIn: linkedin.com/in/sarahjohnson | GitHub: github.com/sjohnson
Address: 123 Tech Street, San Francisco, CA 94105

OBJECTIVE
Senior Software Engineer with 8 years of experience seeking a challenging role
at an innovative technology company.

EDUCATION
Master of Science in Computer Science
Stanford University, Stanford, CA
GPA: 3.9/4.0, Graduated: May 2016

Bachelor of Science in Computer Engineering
UC Berkeley, Berkeley, CA
Summa Cum Laude, Graduated: May 2014

EXPERIENCE
Senior Software Engineer
TechCorp Inc., San Francisco, CA
June 2019 - Present
• Led team of 5 engineers in developing microservices architecture
• Reduced system latency by 40% through optimization
• Mentored junior developers including James Chen and Maria Garcia

Software Engineer II
StartupXYZ, Palo Alto, CA
July 2016 - May 2019
• Developed REST APIs serving 1M+ daily active users
• Collaborated with PM Jessica Williams on product roadmap
• Received "Employee of the Year 2018" award from CEO Mike Thompson

SKILLS
Languages: Python, Java, JavaScript, Go
Technologies: AWS, Docker, Kubernetes, PostgreSQL, Redis

REFERENCES
Available upon request
Dr. Robert Kim, Stanford University - rkim@stanford.edu
Lisa Anderson, Former Manager at TechCorp - landerson@techcorp.com
"""

# Anonymize for initial screening
redacted_resume = inconnu.redact(resume)
print("Anonymized Resume (for bias-free screening):")
print(redacted_resume[:800] + "...")

# Example 2: Performance Review with Sensitive Information
print("\n\n2. PERFORMANCE REVIEW")
print("-" * 30)

performance_review = """
ANNUAL PERFORMANCE REVIEW - CONFIDENTIAL
Employee: Michael Rodriguez (ID: EMP-12345)
Department: Engineering
Manager: Jennifer Chen
Review Period: January 1, 2023 - December 31, 2023
Review Date: January 15, 2024

PERFORMANCE SUMMARY
Overall Rating: Exceeds Expectations (4/5)

Michael has demonstrated exceptional technical skills this year. His work on the
Project Atlas with team members David Park and Anna Schmidt resulted in $2.5M
in cost savings.

STRENGTHS:
- Technical expertise in cloud architecture
- Strong collaboration with offshore team in Bangalore, India
- Mentored 3 junior engineers: Tom Wilson, Sarah Ahmed, and Kevin Li

AREAS FOR IMPROVEMENT:
- Time management on Project Beta (delayed by 2 weeks)
- Communication with stakeholder Robert Johnson at ClientCorp

COMPENSATION DISCUSSION:
Current Salary: $145,000
Recommended Increase: 8% ($11,600)
New Salary: $156,600
Stock Options: 1,000 RSUs vesting over 4 years
Bonus: $20,000 (target achieved)

PERSONAL DEVELOPMENT:
- Attending AWS Summit in Las Vegas, May 2024
- Enrolled in Stanford's online ML course
- Leading diversity initiative with HR Director Patricia Williams

360 FEEDBACK SUMMARY:
- "Michael is a joy to work with" - Anna Schmidt
- "Very knowledgeable but sometimes impatient" - Tom Wilson
- "Best architect on the team" - Jennifer Chen

Manager Signature: Jennifer Chen, Engineering Director
Employee Signature: Michael Rodriguez
HR Representative: Patricia Williams (pwilliams@company.com)
"""

# Pseudonymize for HR records
review_redacted, review_map = inconnu.pseudonymize(performance_review)
print("Pseudonymized Performance Review (excerpt):")
print(review_redacted[:600] + "...")

print("\nSample Entity Mappings:")
salary_entities = {k: v for k, v in review_map.items() if "MONEY" in k}
for key, value in list(salary_entities.items())[:3]:
    print(f"  {key}: {value}")

# Example 3: Interview Feedback Form
print("\n\n3. INTERVIEW FEEDBACK")
print("-" * 30)

interview_feedback = """
INTERVIEW FEEDBACK FORM
Position: Senior Data Scientist
Interview Date: March 25, 2024
Interviewer: Dr. Amanda Wong (awong@techcompany.com)

CANDIDATE INFORMATION
Name: Rajesh Patel
Email: rajesh.patel@email.com
Phone: +1 (408) 555-9876
Current Company: DataCorp Solutions, Mumbai, India
LinkedIn: linkedin.com/in/rajeshpatel
Referred by: Priya Sharma (employee ID: 7890)

INTERVIEW ASSESSMENT

Technical Skills (Score: 9/10)
- Excellent knowledge of ML algorithms
- Solved the clustering problem in 15 minutes
- Previous work at Google Brain mentioned by reference Dr. Liu

Communication (Score: 8/10)
- Clear explanation of past projects
- Good questions about our work with Stanford Medical Center
- Slight accent but easily understandable

Culture Fit (Score: 9/10)
- Values align with company mission
- Excited about mentoring junior team members
- Positive feedback from lunch with team members John Smith and Emily Davis

COMPENSATION EXPECTATIONS
- Current: $180,000 + equity at DataCorp
- Expecting: $200,000-220,000 + equity
- Willing to relocate from Mumbai to San Francisco

RECOMMENDATION: STRONG HIRE
- Extend offer at $210,000 + 5,000 ISOs
- Assign buddy: Senior DS Maria Gonzalez
- Start date: May 1, 2024 (after H1B transfer)

Next Steps: Reference check with Dr. Liu at (650) 555-1234
"""

# Anonymize for DEI reporting
dei_safe_feedback = inconnu.redact(interview_feedback)
print("Anonymized Interview Feedback (for DEI analysis):")
print(dei_safe_feedback[:500] + "...")

# Example 4: Batch Processing Exit Interviews
print("\n\n4. BATCH EXIT INTERVIEW PROCESSING")
print("-" * 30)

exit_interviews = [
    "Sarah quit because her manager Bob was micromanaging. Moving to Apple for $250k.",
    "John from accounting left due to no promotion in 3 years. Lisa got promoted instead.",
    "Emma Thompson leaving for family reasons. Moving to Austin. Great employee.",
]


async def process_exit_interviews():
    """Async processing of multiple exit interviews"""
    results = await inconnu.redact_batch_async(exit_interviews)
    return results


# Run async batch processing
print("Processing exit interviews asynchronously...")
anonymized_exits = asyncio.run(process_exit_interviews())

for i, (original, anonymized) in enumerate(zip(exit_interviews, anonymized_exits)):
    print(f"\nExit Interview {i + 1}:")
    print(f"  Original: {original}")
    print(f"  Anonymized: {anonymized}")

# Example 5: Custom HR Entity Patterns
print("\n\n5. CUSTOM HR ENTITIES")
print("-" * 30)

# Add patterns for HR-specific identifiers
hr_components = [
    NERComponent(
        label="EMPLOYEE_ID", pattern=re.compile(r"\bEMP-\d{5}\b"), processing_func=None
    ),
    NERComponent(
        label="SALARY",
        pattern=re.compile(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?[kK]?"),
        processing_func=None,
    ),
    NERComponent(
        label="DEPARTMENT",
        pattern=re.compile(r"\b(?:Engineering|Sales|Marketing|HR|Finance|Legal)\b"),
        processing_func=None,
    ),
]

inconnu_hr = Inconnu(custom_components=hr_components)

hr_memo = """
INTERNAL MEMO - COMPENSATION ADJUSTMENT
TO: HR Director Susan Martinez
FROM: CFO David Chen

Employee Michael Brown (EMP-45678) in Engineering will receive a salary adjustment
from $125k to $140k effective April 1. This brings him in line with market rates
for Senior Engineers in the Bay Area.

Additionally, approve relocation package of $25,000 for new hire Jennifer Liu
(EMP-45679) moving from our Seattle office to join the Marketing team.

Finance has budgeted for these changes in Q2.
"""

redacted_memo = inconnu_hr.redact(hr_memo)
print("HR Memo with Custom Entities:")
print(redacted_memo)

# Example 6: Background Check Report
print("\n\n6. BACKGROUND CHECK REDACTION")
print("-" * 30)

background_check = """
BACKGROUND CHECK REPORT
Candidate: Robert James Wilson
SSN: 555-12-3456
DOB: March 15, 1985
Driver's License: CA-D1234567

CRIMINAL HISTORY: Clear
- No records found in California, Texas, or New York

EMPLOYMENT VERIFICATION:
1. TechCorp (2019-2023): Verified
   - Position: Senior Developer
   - Supervisor: Amanda Chen (415-555-0123)
   - Reason for leaving: Better opportunity

2. StartupABC (2016-2019): Verified
   - Position: Software Engineer
   - Reference: John Smith (john.smith@startupabc.com)
   - Eligible for rehire: Yes

EDUCATION VERIFICATION:
- MS Computer Science, Stanford University (2014): Verified
- BS Computer Science, UC Berkeley (2012): Verified

CREDIT CHECK:
- Score: 780 (Excellent)
- No bankruptcies or liens
- Mortgage: $450,000 with Wells Fargo

SOCIAL MEDIA SCAN:
- LinkedIn: Professional content only
- Twitter: @rwilson_dev - technology focused
- No concerning content found

Prepared by: SecureCheck Inc.
Date: March 28, 2024
"""

# Full anonymization for compliance
compliant_check = inconnu.redact(background_check)
print("Fully Anonymized Background Check:")
print(compliant_check[:600] + "...")

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR HR DATA PROCESSING")
print("=" * 60)
print("""
1. BIAS PREVENTION:
   - Remove names, photos, age indicators for initial screening
   - Anonymize education institutions to prevent bias
   - Redact location information that might indicate ethnicity

2. COMPLIANCE:
   - Follow EEOC guidelines for fair hiring
   - Comply with GDPR for EU candidates
   - Respect right to be forgotten requests

3. DATA RETENTION:
   - Set appropriate retention periods for different data types
   - Anonymize data after retention period
   - Maintain audit logs for compliance

4. CUSTOM ENTITIES:
   - Add patterns for employee IDs, departments
   - Detect salary and compensation mentions
   - Include industry-specific identifiers

5. ACCESS CONTROL:
   - Use pseudonymization for internal processing
   - Full anonymization for analytics and reporting
   - Restrict access to entity mappings
""")

print("\nExample completed successfully!")
