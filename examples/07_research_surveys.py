#!/usr/bin/env python3
"""
Research & Survey Data Anonymization Example

This example demonstrates how to use Inconnu for processing research data
including survey responses, interview transcripts, focus group discussions,
and participant information while maintaining research integrity and ethics.

Use Cases:
- Survey response anonymization
- Interview transcript processing
- Focus group discussions
- Longitudinal study data
- Market research data
- Academic research datasets
"""

import re

from inconnu import Inconnu, NERComponent

# Initialize Inconnu
inconnu = Inconnu()

print("=" * 60)
print("Research & Survey Data Processing with Inconnu")
print("=" * 60)

# Example 1: Survey Response Data
print("\n1. SURVEY RESPONSE ANONYMIZATION")
print("-" * 30)

survey_response = """
CUSTOMER SATISFACTION SURVEY
Response ID: RESP-2024-03-28-1234
Timestamp: March 28, 2024 10:45 AM PST

RESPONDENT INFORMATION
Name: Sarah Johnson
Email: sarah.j.marketing@techcorp.com
Company: TechCorp Solutions
Position: Marketing Director
Location: San Francisco, CA
Years of Experience: 12

CONTACT PREFERENCES
Phone: (415) 555-1234
Best time to call: Afternoons 2-5 PM PST
LinkedIn: linkedin.com/in/sarahjohnsonmarketing

SURVEY RESPONSES

Q1: How satisfied are you with our product?
A: Very satisfied. It has helped our team increase productivity by 40%.

Q2: Who in your organization uses our product?
A: Primarily our design team led by Michael Chen (mchen@techcorp.com) and
the development team under Jennifer Wu (jwu@techcorp.com). Our CEO,
David Anderson, also reviews the analytics dashboard weekly.

Q3: What is your annual budget for similar tools?
A: We allocate approximately $125,000 annually for marketing automation tools.

Q4: Would you recommend our product?
A: Yes, I've already recommended it to my colleague Lisa Park at StartupXYZ
(lisa.park@startupxyz.com) and my former manager Robert Kim who now works
at Google (rkim@google.com).

Q5: Additional comments?
A: Your customer success manager, Amanda Torres, has been exceptional. She
helped us integrate with our Salesforce instance (ID: 00D2E000000AbCd).
My assistant James Wilson (ext. 5678) can provide more technical details.

FOLLOW-UP
Willing to participate in case study: Yes
Willing to provide testimonial: Yes
Referral contacts provided: 2
"""

# Anonymize for aggregate analysis
analysis_safe = inconnu.redact(survey_response)
print("Anonymized Survey Response:")
print(analysis_safe[:800] + "...")

# Example 2: Interview Transcript
print("\n\n2. INTERVIEW TRANSCRIPT")
print("-" * 30)

interview_transcript = """
RESEARCH INTERVIEW TRANSCRIPT
Study: Remote Work Impact on Mental Health
Participant ID: INT-2024-045
Date: March 28, 2024
Interviewer: Dr. Emily Chen, Stanford University
Duration: 45 minutes

[00:00] Dr. Chen: Thank you for participating. Can you introduce yourself?

[00:15] Participant: I'm Robert Martinez, I work as a Senior Developer at
CloudTech Inc. I've been working remotely from my home in Austin, Texas
since March 2020. I live at 789 Oak Street with my wife Maria and our
two kids, aged 8 and 10.

[01:30] Dr. Chen: How has remote work affected your work-life balance?

[01:45] Participant: It's been challenging. My manager, Susan Lee, expects
me to be available from 8 AM to 6 PM. Her email is slee@cloudtech.com if
you need to verify. My doctor, Dr. James Park at Austin Medical Center
(512-555-7890), prescribed anxiety medication last year.

[03:20] Dr. Chen: Can you describe a typical workday?

[03:35] Participant: I wake up at 6:30, check emails from our Mumbai team
led by Raj Patel. By 9 AM, I'm in meetings. My colleague Jennifer Brown
(she's at 555-234-5678) and I pair program most afternoons. We use my
personal Zoom account (robert.martinez@gmail.com) when company servers
are slow.

[05:10] Dr. Chen: Have you discussed these challenges with anyone?

[05:25] Participant: Yes, with my therapist Dr. Lisa Anderson at Better
Mind Clinic on Lamar Boulevard. Also with my brother Carlos who works at
Dell (carlos.martinez@dell.com). He's experiencing similar issues.

[07:00] Dr. Chen: What support would help?

[07:15] Participant: Better boundaries. My skip-level manager, VP David
Wilson, suggested a 4-day workweek. His assistant Karen (x4567) sent me
some research about it. My wife works at IBM (maria.m@ibm.com) and they
have better policies.

[End of excerpt]
"""

# Pseudonymize for qualitative analysis
transcript_redacted, transcript_map = inconnu.pseudonymize(interview_transcript)
print("Pseudonymized Interview Transcript:")
print(transcript_redacted[:800] + "...")

print("\nEntity mappings (sample):")
for key, value in list(transcript_map.items())[:5]:
    print(f"  {key}: {value}")

# Example 3: Focus Group Discussion
print("\n\n3. FOCUS GROUP DISCUSSION")
print("-" * 30)

focus_group = """
FOCUS GROUP TRANSCRIPT
Topic: Consumer Preferences for Sustainable Products
Date: March 28, 2024
Moderator: Market Research Inc.
Location: Seattle Conference Center, Room 205

PARTICIPANTS:
1. Jessica Wong - Teacher, age 34, Bellevue (jessica.w.teacher@email.com)
2. Michael Thompson - Engineer at Boeing, age 45 (mthompson@boeing.com)
3. Sarah Ahmed - Small business owner, age 28 (sarah@greencafe.com)
4. David Lee - Retired, age 67, lives at Sunrise Senior Living
5. Emma Rodriguez - Student at UW, age 22 (emma.r@uw.edu)

[Moderator]: What influences your purchasing decisions?

[Jessica]: Price is important. As a teacher at Lincoln Elementary making
$65,000/year, I have to budget carefully. My husband Tom works at Microsoft
(tom.wong@microsoft.com) but we still watch spending.

[Michael]: Quality matters more. I learned this from my father, Robert
Thompson, who ran Thompson's Hardware on Pike Street for 30 years.

[Sarah]: For my café at 456 Green Street, I prioritize local suppliers.
I work with Johnson Farms (contact: Bill Johnson at 206-555-8901).

[David]: At my age, convenience is key. My daughter Lisa (425-555-2345)
helps me order online. My social security and pension from Boeing total
about $4,500/month.

[Emma]: Environmental impact! My environmental science professor, Dr. Kumar
(rkumar@uw.edu), taught us about carbon footprints. I shop at the co-op
on 45th Street where my roommate Katie Chen works.

[Michael]: Speaking of environment, my wife Jennifer is on the city council
(jthompson@seattle.gov). She mentioned new regulations coming.

[Group Discussion continues...]
"""

# Anonymize for market research report
market_safe = inconnu.redact(focus_group)
print("Anonymized Focus Group (excerpt):")
print(market_safe[:700] + "...")

# Example 4: Longitudinal Study Data
print("\n\n4. LONGITUDINAL STUDY DATA")
print("-" * 30)

longitudinal_data = """
LONGITUDINAL HEALTH STUDY - 5 YEAR FOLLOW-UP
Participant Code: LS-2019-0892
Original ID: John David Miller
Current Contact: (312) 555-6789
Email: jdmiller1979@email.com

BASELINE (2019):
- Age: 40
- Weight: 185 lbs
- Address: 123 Michigan Ave, Chicago, IL 60601
- Employer: First National Bank
- Spouse: Mary Miller (mary.miller@email.com)
- Primary Care: Dr. Susan Kim, Northwestern Medicine

YEAR 1 (2020):
- Weight: 190 lbs
- Job change: Now at JPMorgan Chase
- Moved to: 456 Lake Shore Dr, Chicago, IL 60611
- Started therapy with Dr. Michael Brown (Anxiety)

YEAR 3 (2022):
- Weight: 175 lbs
- Divorced from Mary Miller
- New partner: Sarah Johnson
- Relocated: 789 North Ave, Apt 23, Chicago, IL 60610
- Children visit weekends: Emma (12) and James (10)

YEAR 5 (2024):
- Weight: 170 lbs
- Married to Sarah Johnson-Miller
- Combined income: $275,000
- New physician: Dr. Robert Chen at Rush Medical
- Medications: Lisinopril 10mg, Metformin 500mg

Emergency Contact Update:
Brother - Thomas Miller: (847) 555-4321
Ex-spouse - Mary Wilson (remarried): (312) 555-8765
"""

# Full anonymization for publication
publication_data = inconnu.redact(longitudinal_data)
print("Anonymized Longitudinal Data:")
print(publication_data[:600] + "...")

# Example 5: Custom Research Patterns
print("\n\n5. RESEARCH-SPECIFIC ENTITIES")
print("-" * 30)

# Add patterns for research-specific identifiers
research_components = [
    NERComponent(
        label="PARTICIPANT_ID",
        pattern=re.compile(r"\b(?:RESP|INT|LS|P)-\d{4}-\d{3,4}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="STUDY_ID",
        pattern=re.compile(r"\b(?:IRB|STUDY)[-#]\d{4}-[A-Z]{2,3}-\d{3}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="LIKERT_SCALE",
        pattern=re.compile(
            r"\b[1-5]\s*(?:=|:)\s*(?:Strongly\s+)?(?:Disagree|Neutral|Agree)\b"
        ),
        processing_func=None,
    ),
]

inconnu_research = Inconnu(custom_components=research_components)

research_note = """
RESEARCH FIELD NOTES
Study ID: STUDY-2024-PSY-001
IRB Approval: IRB#2024-03-156

Participant P-2024-078 (Jennifer Martinez) showed strong emotional response
when discussing her experience. Contact at jmartinez@email.com or 555-0123.

Survey responses:
- Question 1: 5 = Strongly Agree
- Question 2: 2 = Disagree
- Question 3: 4 = Agree

Follow-up interview scheduled with participant INT-2024-045 (Robert Kim)
who mentioned similar experiences. His therapist Dr. Anderson (800-555-HELP)
confirmed participation approval.

Note: Participant RESP-2024-234 withdrew citing privacy concerns about
employer TechCorp finding out about mental health treatment.
"""

research_redacted = inconnu_research.redact(research_note)
print("Redacted Research Notes:")
print(research_redacted)

# Example 6: Market Research Data
print("\n\n6. MARKET RESEARCH DATA")
print("-" * 30)

market_research = """
CONSUMER BEHAVIOR STUDY
Brand Perception Analysis - Luxury Automotive Segment
Research Firm: Global Insights LLC
Date: March 2024

RESPONDENT PROFILE #MR-2024-1567
Name: Christopher Williams
Age: 52
Income: $450,000+
Occupation: Partner at Wilson, Smith & Associates Law Firm
Email: cwilliams@wsalaw.com
Phone: (212) 555-8900
Address: 45 Park Avenue, Penthouse A, New York, NY 10016

Current Vehicles:
- 2023 Mercedes S-Class ($142,000)
- 2022 Porsche 911 Turbo ($185,000)
- Wife's car: 2024 Range Rover ($125,000)

PURCHASE HISTORY:
Dealership: Manhattan Luxury Motors
Salesperson: James Chen (jchen@manhattanluxury.com)
Relationship Manager: Victoria Adams (direct: 212-555-0011)

BRAND ASSOCIATIONS:
"My colleague David Park at Goldman Sachs drives a Bentley. My neighbor
Tom Anderson (CEO of TechStart) swears by his Lamborghini. But I prefer
German engineering - reminds me of my time working in Munich with Klaus
Mueller at BMW headquarters."

DECISION INFLUENCERS:
- Wife: Elisabeth Williams (former model, now runs charity foundation)
- Business Partner: Robert Smith (rsmith@wsalaw.com)
- Golf buddy: Senator Michael Johnson (not his real name, obviously)

LIFESTYLE NOTES:
- Member: The Harvard Club, National Golf Club
- Second home: The Hamptons (123 Ocean Drive)
- Yacht: "Liberty" moored at Chelsea Piers
"""

# Anonymize for competitive analysis
competitive_safe = inconnu.redact(market_research)
print("Anonymized Market Research:")
print(competitive_safe[:700] + "...")

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR RESEARCH DATA")
print("=" * 60)
print("""
1. ETHICAL CONSIDERATIONS:
   - Obtain informed consent
   - Protect vulnerable populations
   - Follow IRB/ethics committee guidelines

2. DATA INTEGRITY:
   - Preserve research validity
   - Maintain response patterns
   - Enable statistical analysis

3. PARTICIPANT PROTECTION:
   - Remove all direct identifiers
   - Watch for indirect identification
   - Protect sensitive responses

4. LONGITUDINAL STUDIES:
   - Consistent anonymization across time
   - Maintain participant tracking
   - Secure linkage mechanisms

5. PUBLICATION READY:
   - Meet journal requirements
   - Support replication studies
   - Enable data sharing
""")

print("\nExample completed successfully!")
