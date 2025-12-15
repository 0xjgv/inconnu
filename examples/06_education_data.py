#!/usr/bin/env python3
"""
Education Data Anonymization Example

This example demonstrates how to use Inconnu for processing educational data
including student records, transcripts, parent communications, and research
data while complying with FERPA and protecting student privacy.

Use Cases:
- Student enrollment records
- Academic transcripts
- Parent-teacher communications
- College applications
- Research participant data
- Online learning platforms

This example also demonstrates:
- Enhanced error handling and conflict resolution
- Use of centralized pattern library
- Debug logging for entity conflicts
- Performance monitoring
"""

import logging

from inconnu import Config, Inconnu, NERComponent
from inconnu.nlp.patterns import (
    COURSE_CODE_PATTERN_RE,
    GPA_PATTERN_RE,
    PATTERN_DOMAINS,
    STUDENT_ID_PATTERN_RE,
)

# Configure logging to see debug information
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Initialize Inconnu with education-specific configuration
config = Config(
    log_conflicts=True,  # Enable conflict logging
    debug_mode=True,  # Enable debug mode
    log_performance=True,  # Enable performance logging
)

inconnu = Inconnu(config=config)

print("=" * 60)
print("Education Data Processing with Inconnu")
print("=" * 60)

# Example 1: Student Enrollment Record
print("\n1. STUDENT ENROLLMENT RECORD")
print("-" * 30)

enrollment_record = """
STUDENT ENROLLMENT FORM
School Year: 2024-2025
School: Lincoln High School, Denver, Colorado

STUDENT INFORMATION
Name: Emily Rodriguez
Date of Birth: March 15, 2008
Student ID: LHS-2024-8901
Grade: 10th
Gender: Female
Email: emily.rodriguez.2008@student.lincolnhs.edu

HOME ADDRESS
456 Oak Street, Apt 3B
Denver, CO 80205
Home Phone: (303) 555-1234

PARENT/GUARDIAN INFORMATION
Parent 1: Maria Rodriguez
Relationship: Mother
Occupation: Software Engineer at TechCorp
Work Phone: (303) 555-5678
Cell: (720) 555-9012
Email: maria.rodriguez@email.com

Parent 2: Carlos Rodriguez
Relationship: Father
Occupation: Teacher at Washington Elementary
Cell: (720) 555-3456
Email: carlos.r.teacher@gmail.com

EMERGENCY CONTACTS
1. Ana Martinez (Grandmother): (303) 555-7890
2. Dr. James Wilson (Family Doctor): (303) 555-2345

MEDICAL INFORMATION
Allergies: Peanuts, Shellfish
Medications: Albuterol inhaler for asthma
Doctor: Dr. Sarah Chen, Pediatrics Plus
Insurance: Blue Cross Blue Shield, Policy #BC123456

ACADEMIC INFORMATION
Previous School: Jefferson Middle School
GPA: 3.85
Counselor Assignment: Ms. Jennifer Thompson
Special Programs: Advanced Placement Math, Honor Roll
"""

# Anonymize for statistical reporting
stats_safe = inconnu.redact(enrollment_record)
print("Anonymized Enrollment (for statistics):")
print(stats_safe[:700] + "...")

# Example 2: Academic Transcript
print("\n\n2. ACADEMIC TRANSCRIPT")
print("-" * 30)

transcript = """
OFFICIAL ACADEMIC TRANSCRIPT
Stanford University
Office of the Registrar

Student: Michael Chen
Student ID: 06-123-456
Email: mchen@stanford.edu
Date of Birth: January 20, 2002
Address: 789 Campus Drive, Dorm 5A, Stanford, CA 94305
Phone: (650) 555-8901

Degree: Bachelor of Science in Computer Science
Expected Graduation: June 2024
Cumulative GPA: 3.92/4.00

ACADEMIC RECORD

Fall 2023
CS 106B - Programming Abstractions (Prof. Julie Zelenski) - A
MATH 51 - Linear Algebra (Prof. Robert Kim) - A-
PHIL 150 - Ethics in AI (Prof. Sarah Williams) - A
MUSIC 17N - The Mozart Effect (Prof. David Anderson) - B+
Quarter GPA: 3.83

Winter 2024
CS 221 - Artificial Intelligence (Prof. Andrew Ng) - A
CS 229 - Machine Learning (Prof. Christopher Manning) - A
STATS 116 - Statistical Methods (Prof. Lisa Johnson) - A-
ECON 1 - Principles of Economics (Prof. Mark Thompson) - B+
Quarter GPA: 3.85

HONORS AND AWARDS
- Dean's List: Fall 2023, Winter 2024
- Tau Beta Pi Engineering Honor Society
- Research Assistant - Prof. Jennifer Garcia's NLP Lab

Registrar: Patricia Brown
Date Issued: March 28, 2024
"""

# Pseudonymize for research while maintaining structure
transcript_redacted, transcript_map = inconnu.pseudonymize(transcript)
print("Pseudonymized Transcript (excerpt):")
print(transcript_redacted[:600] + "...")

print("\nSample mappings (courses and professors):")
academic_entities = {
    k: v for k, v in transcript_map.items() if "PERSON" in k or "ORG" in k
}
for key, value in list(academic_entities.items())[:5]:
    print(f"  {key}: {value}")

# Example 3: Parent-Teacher Communication
print("\n\n3. PARENT-TEACHER EMAIL")
print("-" * 30)

parent_email = """
From: jennifer.smith@email.com
To: mr.wilson@lincolnelementary.edu
Subject: Re: Tommy's Progress - Reading Concerns
Date: March 28, 2024

Dear Mr. Wilson,

Thank you for reaching out about Tommy Smith's reading progress. As his mother,
I share your concerns about his performance in the recent assessment.

Tommy (Student ID: LE-2024-5678) has mentioned that he's been struggling with
the new reading program. At home (123 Maple Street, Denver, CO 80210), we've
been working with him every evening, but progress has been slow.

I spoke with his pediatrician, Dr. Michael Brown at Children's Hospital
(303-555-4567), who suggested we might want to have him evaluated for dyslexia.
His older sister Sarah (now at Harvard) had similar challenges at his age.

Would it be possible to meet next week? I'm available any day after 3:30 PM.
You can reach me at (720) 555-8901 or my work number (303) 555-6789.

My husband David (david.smith@lawfirm.com) would also like to attend if
possible. He's particularly concerned since his brother James had undiagnosed
learning disabilities that affected his education.

Thank you for your dedication to Tommy's education.

Best regards,
Jennifer Smith

P.S. Tommy's tutor, Maria Garcia (tutoring@learningcenter.com), mentioned
she could provide her assessment notes if helpful.
"""

# Anonymize for teacher training materials
training_email = inconnu.redact(parent_email)
print("Anonymized Parent Email (for training):")
print(training_email[:600] + "...")

# Example 4: College Application Essay
print("\n\n4. COLLEGE APPLICATION")
print("-" * 30)

college_app = """
COMMON APPLICATION ESSAY
Applicant: Jessica Martinez
Email: jmartinez2006@email.com
Phone: (512) 555-3456
High School: Austin Preparatory Academy

Prompt: Describe a challenge you've overcome.

When my father, Roberto Martinez, lost his job at Dell Technologies in 2022,
our family faced financial hardship. As the eldest of three children, I knew
I had to step up. My mother, Ana Martinez, works as a nurse at St. David's
Medical Center, but her income alone wasn't enough.

I started tutoring other students at Austin Prep in math and science, charging
$25/hour. My first client was Johnny Chen, whose mother found me through our
church, St. Mary's Catholic Church on Guadalupe Street. Soon, I was tutoring
five students, including Sarah Williams and Michael Brown.

This experience taught me resilience. Despite working 15 hours/week, I maintained
my 4.0 GPA and position as president of the National Honor Society. My counselor,
Mrs. Patricia Johnson (pjohnson@austinprep.edu), nominated me for the National
Merit Scholarship.

My siblings, Carlos (age 14) and Sofia (age 12), now help me with organizing
my tutoring materials. We live at 789 Riverside Drive, Austin, TX 78704, where
I've converted our garage into a study space.

This challenge ultimately strengthened our family and taught me the value of
hard work. It's why I'm applying for need-based financial aid (Family AGI: $65,000).

References:
- Principal Thomas Anderson: tanderson@austinprep.edu
- Math Teacher Dr. Lisa Wang: lwang@austinprep.edu
"""

# Full anonymization for admissions committee diversity reports
diversity_safe = inconnu.redact(college_app)
print("Anonymized Application Essay:")
print(diversity_safe[:700] + "...")

# Example 5: Online Learning Platform Data
print("\n\n5. ONLINE LEARNING PLATFORM")
print("-" * 30)

# Use centralized patterns from the pattern library
# These are already included when we enabled the education domain
# But we can add them explicitly as custom components to show priority
edu_components = [
    NERComponent(
        label="STUDENT_ID",
        pattern=STUDENT_ID_PATTERN_RE,  # From centralized patterns
        processing_func=None,
    ),
    NERComponent(
        label="COURSE_CODE",
        pattern=COURSE_CODE_PATTERN_RE,  # From centralized patterns
        processing_func=None,
    ),
    NERComponent(
        label="GPA",
        pattern=GPA_PATTERN_RE,  # From centralized patterns
        processing_func=None,
    ),
]

# Create new instance with custom components and error handling demo
try:
    inconnu_edu = Inconnu(custom_components=edu_components)
    print("Successfully initialized Inconnu with education patterns")
except Exception as e:
    print(f"Error initializing Inconnu: {e}")
    # Fallback to basic instance
    inconnu_edu = inconnu

platform_data = """
STUDENT ANALYTICS REPORT
Platform: EduLearn Pro
Generated: March 28, 2024

Student: Robert Kim (RK-2024-7890)
Email: robert.kim@university.edu
Course: CS 101 - Introduction to Programming
Instructor: Prof. Amanda Chen
Current Grade: B+ (GPA: 3.33/4.00)

Activity Log:
- March 25, 9:45 PM: Logged in from IP 192.168.1.50 (San Francisco, CA)
- Completed Assignment 5: "Loops and Functions"
- Time spent: 2 hours 15 minutes
- Collaborated with: Jennifer Liu (JL-2024-6789), David Park (DP-2024-5678)

Discussion Forum Posts:
"Can someone help with problem 3? - Robert Kim (650-555-1234)"
Reply from TA Sarah Johnson: "Check your loop condition, Robert!"

Parent Access Log:
- Mrs. Susan Kim (parent@email.com) viewed progress report on March 27
- Phone contact: (650) 555-5678

Performance Metrics:
- Assignment Average: 85%
- Quiz Average: 78%
- Participation: 92%
- Predicted Final Grade: B (3.0/4.0)
"""

# Demonstrate error handling and conflict resolution
try:
    platform_redacted = inconnu_edu.redact(platform_data)
    print("Anonymized Platform Data:")
    print(platform_redacted)

    # Show performance stats if available
    stats = inconnu_edu.get_performance_stats()
    print(f"\nPerformance stats: {stats}")
except Exception as e:
    print(f"Error processing platform data: {e}")
    print("Attempting graceful recovery...")
    # Try with basic anonymization
    platform_redacted = inconnu.redact(platform_data)
    print("Recovered with basic anonymization:")
    print(platform_redacted[:400] + "...")

# Example 6: Research Study Participant Data with Entity Conflict Demo
print("\n\n6. EDUCATIONAL RESEARCH DATA (WITH CONFLICT RESOLUTION DEMO)")
print("-" * 30)

# This example deliberately creates potential entity conflicts to show
# how the enhanced conflict resolution handles them
research_data = """
EDUCATIONAL RESEARCH STUDY
Title: Impact of Socioeconomic Factors on STEM Performance
IRB Approval: #2024-EDU-123

PARTICIPANT: Study ID 2024-P-045

Demographics:
- Name: Maria Gonzalez
- Age: 16
- School: Jefferson High School, Los Angeles, CA
- Grade: 11th
- Ethnicity: Hispanic/Latina
- Household Income: $45,000-55,000
- Parent Education: Mother - Associate's Degree, Father - High School

Contact:
- Email: participant045@study.edu (anonymized)
- Actual: maria.g.2007@email.com
- Parent Contact: Rosa Gonzalez (323) 555-9876

Pre-Test Scores:
- Math: 78/100
- Science: 82/100
- Reading: 85/100

Intervention: 8-week after-school STEM program
Location: UCLA Campus, Engineering Building Room 201
Instructor: Graduate Student James Wong

Post-Test Scores:
- Math: 89/100 (+11 points)
- Science: 91/100 (+9 points)
- Reading: 87/100 (+2 points)

Qualitative Notes:
"Maria showed significant improvement. Her mother mentioned that her uncle,
Dr. Carlos Mendez (an engineer at SpaceX), has been mentoring her." - J. Wong

Follow-up: Schedule 6-month assessment. Contact via parent's phone.
"""

# Anonymize for publication with error handling
try:
    # Enable debug logging to see conflict resolution
    if config.debug_mode:
        print("\n[DEBUG] Processing research data with potential entity conflicts...")

    publication_ready = inconnu.redact(research_data)
    print("\nAnonymized Research Data (for publication):")
    print(publication_ready[:600] + "...")

    # Demonstrate validation of results
    if "[PERSON]" in publication_ready and "[STUDENT_ID]" in publication_ready:
        print("\n✓ Successfully anonymized person names and student IDs")
    if "[PHONE_NUMBER]" in publication_ready:
        print("✓ Successfully anonymized phone numbers")
    if "[EMAIL]" in publication_ready:
        print("✓ Successfully anonymized email addresses")

except Exception as e:
    print(f"\nError during anonymization: {e}")
    print("This demonstrates the enhanced error handling in action.")

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR EDUCATION DATA")
print("=" * 60)
print("""
1. FERPA COMPLIANCE:
   - Protect student education records
   - Obtain consent for data sharing
   - Limit access to need-to-know basis

2. AGE-APPROPRIATE PRIVACY:
   - Extra protection for K-12 students
   - Parental consent requirements
   - Careful handling of minor's data

3. RESEARCH ETHICS:
   - IRB approval for studies
   - De-identification for publication
   - Secure storage of consent forms

4. DATA MINIMIZATION:
   - Collect only necessary information
   - Regular data purging policies
   - Avoid sensitive demographic data when possible

5. ACADEMIC INTEGRITY:
   - Protect test questions and answers
   - Anonymize peer review feedback
   - Secure grade and assessment data
""")

# Additional Examples Demonstrating New Features
print("\n\n7. DEMONSTRATING NEW FEATURES")
print("-" * 30)

# Demonstrate processing large documents
print("\n7a. Processing Large Text")
large_text = enrollment_record * 10  # Simulate large document
result = inconnu.redact(large_text)
print(f"Processed {len(large_text)} chars successfully")
print(f"Result preview: {result[:200]}...")

# Demonstrate batch processing with progress
print("\n7b. Batch Processing Multiple Documents")
documents = [
    "Student John Doe (ID: ABC-1234-5678) scored 3.85 GPA",
    "Dr. Smith teaches CS 101 in Room 205",
    "Contact parent at (555) 123-4567 or parent@email.com",
    "Invalid document with [[ bad formatting ]]",
]

try:
    batch_results = inconnu.redact_batch(documents, chunk_size=2)
    print("Batch processing results:")
    for i, result in enumerate(batch_results):
        print(f"  Doc {i + 1}: {result}")
except Exception as e:
    print(f"Batch processing error: {e}")

# Demonstrate pattern inspection
print("\n7c. Available Education Patterns")
supported = inconnu.get_supported_patterns()
education_patterns = [
    p for p in supported if PATTERN_DOMAINS.get(p) == "education"
]
print(f"Education-specific patterns: {', '.join(education_patterns)}")

print("\n" + "=" * 60)
print("Example completed successfully!")
print("This example demonstrated:")
print("- Enhanced error handling and recovery")
print("- Entity conflict resolution with debug logging")
print("- Use of centralized pattern library")
print("- Streaming and batch processing")
print("- Performance monitoring")
print("- Pattern inspection and configuration")
print("=" * 60)
