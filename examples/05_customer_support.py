#!/usr/bin/env python3
"""
Customer Support Data Anonymization Example

This example demonstrates how to use Inconnu for processing customer support
interactions including tickets, chat logs, emails, and feedback while
maintaining service quality and protecting customer privacy.

Use Cases:
- Support ticket anonymization
- Live chat transcripts
- Customer email threads
- Product reviews and feedback
- Social media complaints
- Call center transcripts
"""

import asyncio
import re

from inconnu import Inconnu, NERComponent

# Initialize Inconnu
inconnu = Inconnu()

print("=" * 60)
print("Customer Support Data Processing with Inconnu")
print("=" * 60)

# Example 1: Support Ticket
print("\n1. SUPPORT TICKET ANONYMIZATION")
print("-" * 30)

support_ticket = """
SUPPORT TICKET #2024-03-28-1234

Created: March 28, 2024 09:45 AM PST
Priority: HIGH
Category: Account Access

CUSTOMER INFORMATION
Name: Sarah Johnson
Account ID: CUST-789012
Email: sarah.j.2024@gmail.com
Phone: +1 (555) 123-4567
Location: Austin, Texas

ISSUE DESCRIPTION
Customer unable to access account since March 27, 2024. Error message:
"Invalid credentials". Customer states she hasn't changed her password.

Previous tickets: #2024-02-15-5678 (billing issue - resolved)

CONVERSATION HISTORY

[March 28, 2024 09:45 AM]
Customer: I can't log into my account! I've been a customer since 2019 and
this is unacceptable. My username is sjohnson_austin and I need access to
download my invoices for tax purposes.

[March 28, 2024 09:50 AM]
Agent Tom Wilson: I understand your frustration, Sarah. I can see your account
and will help you regain access. Can you verify the last 4 digits of the credit
card on file? It ends in 4532.

[March 28, 2024 09:52 AM]
Customer: Yes, that's correct. My billing address is 123 Oak Street, Austin, TX 78701.

[March 28, 2024 09:55 AM]
Agent Tom Wilson: Thank you for verifying. I've sent a password reset link to
sarah.j.2024@gmail.com. Your temporary password is: Temp2024$Reset

[March 28, 2024 10:00 AM]
Customer: It worked! Thank you Tom. While I have you, my colleague Jennifer Chen
(jen.chen@techcorp.com) also needs access to our business account BIZ-456789.

RESOLUTION
Password reset completed. Added note about business account access request.
Escalated to Business Support team for Jennifer Chen's access.

Agent: Tom Wilson (ID: AGT-1234)
Resolution Time: 15 minutes
Customer Satisfaction: Pending
"""

# Anonymize for quality assurance review
qa_ticket = inconnu.redact(support_ticket)
print("Anonymized Ticket (for QA review):")
print(qa_ticket[:800] + "...")

# Example 2: Live Chat Transcript
print("\n\n2. LIVE CHAT TRANSCRIPT")
print("-" * 30)

chat_transcript = """
LIVE CHAT SESSION
Session ID: CHAT-2024-03-28-5678
Date: March 28, 2024
Duration: 12 minutes

[10:15:32] System: Customer Robert Martinez connected from IP 192.168.1.100
[10:15:35] Agent Lisa: Hello! I'm Lisa. How can I help you today?
[10:15:45] Robert Martinez: Hi Lisa, I'm having issues with my order #ORD-2024-9876
[10:15:52] Agent Lisa: I'd be happy to help with your order. Let me pull that up.
[10:16:10] Agent Lisa: I see your order for the Premium Package ($299) placed on March 25
[10:16:20] Robert Martinez: Yes, but it was supposed to be delivered to my office
[10:16:25] Robert Martinez: 456 Business Plaza, Suite 200, Denver, CO 80202
[10:16:35] Agent Lisa: I see it's currently showing delivery to 789 Home St, Denver
[10:16:45] Robert Martinez: That's my home. My assistant Maria Garcia ordered it
[10:16:50] Robert Martinez: Her email is mgarcia@mycompany.com if you need to verify
[10:17:05] Agent Lisa: I can update the delivery address for you right now
[10:17:15] Robert Martinez: Great! My office phone is (303) 555-8900
[10:17:25] Agent Lisa: Perfect. I've updated the delivery address and added your office phone
[10:17:35] Robert Martinez: Thank you! My boss David Chen will be happy
[10:17:40] Robert Martinez: He's been waiting for this at david.chen@mycompany.com
[10:17:50] Agent Lisa: You're welcome! The package will arrive at your office by March 30
[10:18:00] Robert Martinez: 5 stars! Thanks Lisa!
[10:18:05] Agent Lisa: Thank you for choosing our service! Have a great day!
[10:18:10] System: Customer disconnected. Satisfaction rating: 5/5
"""

# Pseudonymize for training chat agents
chat_redacted, chat_map = inconnu.pseudonymize(chat_transcript)
print("Pseudonymized Chat (for agent training):")
print(chat_redacted[:600] + "...")

print("\nEntity mappings (sample):")
for key, value in list(chat_map.items())[:5]:
    print(f"  {key}: {value}")

# Example 3: Customer Email Thread
print("\n\n3. EMAIL THREAD PROCESSING")
print("-" * 30)

email_thread = """
Subject: Re: Urgent: Billing Error on Account
Thread ID: EMAIL-2024-03-28-3456

From: angry.customer@email.com (Michael Thompson)
To: support@company.com
Date: March 28, 2024 08:00 AM

This is the THIRD time I'm writing about this! You charged my Visa ending
in 8901 three times for the same subscription! Each charge was $49.99.

My account number is ACC-123456 and I've been a customer since 2018. This
is completely unacceptable. If this isn't resolved TODAY, I'm calling my
bank to dispute all charges and posting on Twitter (@mikethompson_real).

---
From: support@company.com
To: angry.customer@email.com
Date: March 28, 2024 08:30 AM

Dear Michael,

I sincerely apologize for this billing error. I'm Sarah from the Billing
Department and I'll personally ensure this is resolved today.

I can confirm we see the triple charge on your Visa ending 8901. I've:
1. Initiated refunds for the two duplicate charges ($99.98 total)
2. Added a $20 credit to your account for the inconvenience
3. Escalated to our VP of Customer Success, James Wilson

The refunds will appear in 3-5 business days. Reference: REF-2024-7890

---
From: angry.customer@email.com
To: support@company.com
Date: March 28, 2024 09:00 AM

Thank you Sarah. I appreciate the quick response. Please also update my
email to michael.thompson.new@email.com and my phone to (555) 987-6543.

My wife Jennifer (on the same account) should also get notifications at
jennifer.t@email.com.

- Michael Thompson
  123 Main Street, Apt 45
  San Francisco, CA 94105
"""

# Anonymize for customer service metrics
metrics_safe = inconnu.redact(email_thread)
print("Anonymized Email Thread (for metrics):")
print(metrics_safe[:600] + "...")

# Example 4: Product Review Moderation
print("\n\n4. PRODUCT REVIEW MODERATION")
print("-" * 30)

product_reviews = [
    "Great product! John Smith from Seattle here. Worth every penny of the $199 I paid.",
    "Terrible experience. Sarah at ext 5678 was rude. Email me at karen@email.com",
    "5 stars! Delivered to 456 Oak St, Boston. Contact: (617) 555-1234 for questions.",
]

print(f"Processing {len(product_reviews)} product reviews...")
moderated_reviews = inconnu.redact_batch(product_reviews)

for i, (original, moderated) in enumerate(zip(product_reviews, moderated_reviews)):
    print(f"\nReview {i + 1}:")
    print(f"  Original: {original}")
    print(f"  Moderated: {moderated}")

# Example 5: Social Media Complaint
print("\n\n5. SOCIAL MEDIA COMPLAINT")
print("-" * 30)

social_media_post = """
TWITTER/X COMPLAINT ALERT
Platform: Twitter/X
Handle: @angrycustomer123
Followers: 5,234
Post Time: March 28, 2024 11:30 AM

Original Tweet:
"@YourCompany Your service is TERRIBLE! I'm Jane Williams (customer #789012)
and I've been waiting 3 DAYS for someone to call me back at 555-234-5678!
My order (ORD-2024-1111) to 789 Pine Ave, Chicago, IL is still missing!
CC: @BetterBusinessBureau @ConsumerReports"

Replies:
- @supporthelper: "Jane, DMing you now! -Mike from Support"
- @randomuser456: "I had the same issue! Email susan.lee@email.com for CEO office"
- @angrycustomer123: "Finally got help from agent Tom Wilson. He found my package!"

Internal Notes:
- High priority due to follower count and mentions
- Customer previously complained on Facebook (fb.com/janewilliams.chicago)
- Resolved by Agent Tom Wilson (emp ID: TW-5678)
- Package was delivered to wrong address: 789 Pine Court (not Ave)
"""

# Anonymize for social media team training
training_post = inconnu.redact(social_media_post)
print("Anonymized Social Media Post:")
print(training_post)

# Example 6: Async Processing of Multiple Channels
print("\n\n6. MULTI-CHANNEL ASYNC PROCESSING")
print("-" * 30)

# Simulate different support channels
support_channels = [
    "Phone: Customer David Lee called from 415-555-7890 about billing",
    "Chat: Emma Wilson needs password reset for emma@techcorp.com",
    "Email: Ticket from Carlos Garcia (carlos.g@email.com) about refund",
    "Social: Twitter user @johnsmith2024 complaining about Austin store",
]


async def process_support_channels():
    """Process multiple support channels asynchronously"""
    results = await inconnu.redact_batch_async(support_channels)
    return results


print("Processing multiple support channels...")
anonymized_channels = asyncio.run(process_support_channels())

for channel, anonymized in zip(support_channels, anonymized_channels):
    print(f"\n{channel[:15]}... → {anonymized}")

# Example 7: Custom Support Entities
print("\n\n7. CUSTOM SUPPORT ENTITIES")
print("-" * 30)

# Add patterns for support-specific data
support_components = [
    NERComponent(
        label="TICKET_ID",
        pattern=re.compile(r"\b(?:TICKET|TKT|#)\s*\d{4}-\d{2}-\d{2}-\d{4}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="ORDER_ID",
        pattern=re.compile(r"\bORD-\d{4}-\d{4,6}\b"),
        processing_func=None,
    ),
    NERComponent(
        label="CUSTOMER_ID",
        pattern=re.compile(r"\b(?:CUST|ACC)-\d{6}\b"),
        processing_func=None,
    ),
]

inconnu_support = Inconnu(custom_components=support_components)

support_note = """
Customer Follow-up Required
TICKET #2024-03-28-9999 | Customer CUST-456789

Order ORD-2024-5555 delayed. Contact Jennifer Brown at 555-0123 before 5 PM.
Previous tickets: #2024-03-15-1111, #2024-03-20-2222
Manager escalation: David Wilson (david.wilson@company.com)
"""

redacted_note = inconnu_support.redact(support_note)
print("Support Note with Custom Entities:")
print(redacted_note)

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR CUSTOMER SUPPORT DATA")
print("=" * 60)
print("""
1. PRIVACY PROTECTION:
   - Remove customer PII from public-facing systems
   - Anonymize data before sharing with third parties
   - Use pseudonymization for internal quality reviews

2. CHANNEL-SPECIFIC:
   - Email: Preserve thread context while removing PII
   - Chat: Maintain conversation flow
   - Social: Protect both customer and company reputation

3. COMPLIANCE:
   - Follow GDPR/CCPA for data requests
   - Implement retention policies per channel
   - Enable right-to-be-forgotten compliance

4. QUALITY ASSURANCE:
   - Anonymize for agent training materials
   - Enable performance metrics without PII
   - Support customer satisfaction analysis

5. OPERATIONAL EFFICIENCY:
   - Use async processing for real-time channels
   - Batch process historical data
   - Integrate with ticketing systems
""")

print("\nExample completed successfully!")
