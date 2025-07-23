#!/usr/bin/env python3
"""
Batch Processing & Performance Optimization Example

This example demonstrates how to use Inconnu for high-volume data processing,
including CSV files, database exports, streaming data, and performance
optimization techniques for production environments.

Use Cases:
- Processing CSV files with customer data
- Bulk email anonymization
- Database export processing
- Log file anonymization
- Large document collections
- Real-time stream processing
"""

import asyncio
import csv
import time
from io import StringIO

from inconnu import Inconnu

# Initialize Inconnu
inconnu = Inconnu()

print("=" * 60)
print("Batch Processing & Performance with Inconnu")
print("=" * 60)

# Example 1: CSV File Processing
print("\n1. CSV FILE PROCESSING")
print("-" * 30)

# Simulate a CSV file with customer data
csv_data = """Name,Email,Phone,Address,SSN,Account_Balance
John Smith,john.smith@email.com,(555) 123-4567,123 Main St Seattle WA,123-45-6789,$125500.00
Maria Garcia,mgarcia@company.com,555-234-5678,456 Oak Ave Portland OR,987-65-4321,$87250.50
Robert Chen,r.chen@techcorp.com,+1-415-555-9012,789 Market St San Francisco CA,555-12-3456,$245000.00
Sarah Johnson,sjohnson2024@gmail.com,(206) 555-3456,321 Pine St Apt 4B Seattle WA,111-22-3333,$52750.25
Michael Brown,mbrown@startup.io,503-555-7890,654 River Rd Portland OR,444-55-6666,$198500.00
Jennifer Lee,jenny.lee@email.com,415-555-2345,987 Hill St San Francisco CA,777-88-9999,$76000.00
David Wilson,d.wilson@bigcorp.com,(206) 555-6789,246 Lake View Seattle WA,222-33-4444,$342000.50
Lisa Anderson,landerson@university.edu,503-555-4321,135 College Way Portland OR,888-99-0000,$93500.75
"""

# Process CSV data
csv_file = StringIO(csv_data)
reader = csv.DictReader(csv_file)

print("Processing customer CSV file...")
start_time = time.time()

anonymized_rows = []
for row in reader:
    # Concatenate fields that need processing
    full_text = f"{row['Name']} | {row['Email']} | {row['Phone']} | {row['Address']} | {row['SSN']} | {row['Account_Balance']}"

    # Anonymize the concatenated text
    anonymized = inconnu.redact(full_text)

    # Split back into fields
    parts = anonymized.split(" | ")
    anonymized_row = {
        "Name": parts[0],
        "Email": parts[1],
        "Phone": parts[2],
        "Address": parts[3],
        "SSN": parts[4],
        "Account_Balance": parts[5],
    }
    anonymized_rows.append(anonymized_row)

end_time = time.time()
print(f"Processed {len(anonymized_rows)} rows in {end_time - start_time:.2f} seconds")

# Display sample results
print("\nSample anonymized rows:")
for i, row in enumerate(anonymized_rows[:3]):
    print(f"Row {i + 1}: {row}")

# Example 2: Bulk Email Processing
print("\n\n2. BULK EMAIL ANONYMIZATION")
print("-" * 30)

# Simulate a collection of emails
emails = [
    """From: customer1@email.com
To: support@company.com
Subject: Order #12345 Issue
Hi, I'm John Doe from 123 Main St, Chicago. My phone is 312-555-1234.
Please check my order status. My account number is ACC-789012.""",
    """From: jane.smith@corporation.com
To: sales@vendor.com
Subject: Quote Request
This is Jane Smith, CFO at TechCorp (Tax ID: 12-3456789).
We need pricing for 100 units. Call me at (415) 555-5678 or my assistant
Mark Johnson at extension 4567. Budget approved for $50,000.""",
    """From: angry.customer@gmail.com
To: complaints@service.com
Subject: URGENT - Fraud on account
My name is Robert Chen, SSN 555-12-3456. Someone used my credit card
ending in 4532 at your store. I live at 456 Oak Ave, Seattle, WA 98101.
Contact me immediately at 206-555-9876.""",
]

print(f"Processing {len(emails)} emails in batch...")
start_time = time.time()

# Batch process all emails
anonymized_emails = inconnu.redact_batch(emails)

end_time = time.time()
print(f"Batch processing completed in {end_time - start_time:.2f} seconds")
print(f"Average time per email: {(end_time - start_time) / len(emails):.3f} seconds")

# Show first anonymized email
print("\nFirst anonymized email:")
print(anonymized_emails[0])

# Example 3: Async Batch Processing
print("\n\n3. ASYNC BATCH PROCESSING")
print("-" * 30)

# Simulate larger dataset
large_dataset = [
    f"Customer {i}: {name} at {email}, phone {phone}, account {account}"
    for i, (name, email, phone, account) in enumerate(
        [
            ("Alice Brown", "alice@email.com", "555-0001", "ACC-100001"),
            ("Bob Davis", "bob@company.com", "555-0002", "ACC-100002"),
            ("Carol White", "carol@tech.com", "555-0003", "ACC-100003"),
            ("Dan Green", "dan@startup.io", "555-0004", "ACC-100004"),
            ("Eve Black", "eve@corp.com", "555-0005", "ACC-100005"),
            ("Frank Gray", "frank@email.com", "555-0006", "ACC-100006"),
            ("Grace Blue", "grace@firm.com", "555-0007", "ACC-100007"),
            ("Henry Red", "henry@biz.com", "555-0008", "ACC-100008"),
            ("Iris Yellow", "iris@co.com", "555-0009", "ACC-100009"),
            ("Jack Purple", "jack@inc.com", "555-0010", "ACC-100010"),
        ]
    )
]


async def process_async_batch():
    print(f"Async processing {len(large_dataset)} records...")
    start_time = time.time()

    # Process in parallel using async
    results = await inconnu.redact_batch_async(large_dataset)

    end_time = time.time()
    print(f"Async processing completed in {end_time - start_time:.2f} seconds")
    print(f"Records per second: {len(large_dataset) / (end_time - start_time):.1f}")

    return results


# Run async processing
anonymized_async = asyncio.run(process_async_batch())
print("\nFirst 3 async results:")
for i, result in enumerate(anonymized_async[:3]):
    print(f"  {i + 1}: {result}")

# Example 4: Streaming Data Processing
print("\n\n4. STREAMING DATA SIMULATION")
print("-" * 30)


def generate_log_entries():
    """Simulate streaming log entries"""
    logs = [
        "2024-03-28 10:15:23 INFO User john.doe@email.com logged in from IP 192.168.1.100",
        "2024-03-28 10:15:45 ERROR Payment failed for customer Sarah Smith (ID: CUST-12345), card ending 4532",
        "2024-03-28 10:16:02 WARN Suspicious activity from user robert@hackers.com at 185.220.101.45",
        "2024-03-28 10:16:15 INFO Order placed by Maria Garcia (mgarcia@email.com) for $1,250.00",
        "2024-03-28 10:16:28 DEBUG API call from developer key belonging to dev@techcorp.com (James Wilson)",
    ]
    for log in logs:
        yield log


print("Processing streaming log data...")
processed_count = 0
start_time = time.time()

for log_entry in generate_log_entries():
    # Process each log entry as it arrives
    anonymized_log = inconnu.redact(log_entry)
    processed_count += 1
    print(f"Processed: {anonymized_log}")

end_time = time.time()
print(
    f"\nProcessed {processed_count} log entries in {end_time - start_time:.2f} seconds"
)

# Example 5: Performance Comparison
print("\n\n5. PERFORMANCE COMPARISON")
print("-" * 30)

# Create test datasets of different sizes
test_sizes = [10, 50, 100]
test_data = {
    size: [
        f"Person {i}: {name} ({email}) called from {phone} about order #{order}"
        for i in range(size)
        for name, email, phone, order in [
            (
                f"User{i}",
                f"user{i}@email.com",
                f"555-{1000 + i:04d}",
                f"ORD-{2024000 + i}",
            )
        ]
    ]
    for size in test_sizes
}

print("Performance comparison:")
print("Size | Sync Time | Async Time | Speedup")
print("-" * 45)

for size in test_sizes:
    data = test_data[size]

    # Sync processing
    start = time.time()
    sync_results = inconnu.redact_batch(data)
    sync_time = time.time() - start

    # Async processing
    async def async_test():
        return await inconnu.redact_batch_async(data)

    start = time.time()
    async_results = asyncio.run(async_test())
    async_time = time.time() - start

    speedup = sync_time / async_time if async_time > 0 else 0
    print(f"{size:4d} | {sync_time:9.3f}s | {async_time:10.3f}s | {speedup:7.2f}x")

# Example 6: Memory-Efficient Processing
print("\n\n6. MEMORY-EFFICIENT LARGE FILE PROCESSING")
print("-" * 30)


def process_large_file_in_chunks(data_lines, chunk_size=100):
    """Process large files in chunks to manage memory"""
    total_processed = 0
    chunk_times = []

    print(f"Processing in chunks of {chunk_size}...")

    # Process data in chunks
    for i in range(0, len(data_lines), chunk_size):
        chunk = data_lines[i : i + chunk_size]

        start = time.time()
        # Process chunk
        anonymized_chunk = inconnu.redact_batch(chunk)
        chunk_time = time.time() - start
        chunk_times.append(chunk_time)

        total_processed += len(chunk)
        print(
            f"  Processed chunk {i // chunk_size + 1}: {len(chunk)} records in {chunk_time:.3f}s"
        )

    avg_chunk_time = sum(chunk_times) / len(chunk_times)
    print(f"\nTotal records: {total_processed}")
    print(f"Average chunk processing time: {avg_chunk_time:.3f}s")
    print(f"Estimated throughput: {chunk_size / avg_chunk_time:.1f} records/second")


# Simulate large dataset
large_data = [
    f"Record {i}: Customer {name} at {addr}, contact {email} or {phone}"
    for i in range(500)
    for name, addr, email, phone in [
        (
            f"Person{i}",
            f"{i} Main St, City, State",
            f"person{i}@email.com",
            f"555-{i % 10000:04d}",
        )
    ]
]

process_large_file_in_chunks(large_data, chunk_size=100)

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR BATCH PROCESSING")
print("=" * 60)
print("""
1. PERFORMANCE OPTIMIZATION:
   - Use batch methods for multiple texts
   - Leverage async for I/O-bound operations
   - Process in chunks for large files
   - Monitor memory usage

2. CSV/STRUCTURED DATA:
   - Concatenate fields for processing
   - Preserve data structure
   - Handle special characters properly
   - Validate output format

3. ASYNC PROCESSING:
   - Use for concurrent operations
   - Ideal for API integrations
   - Better resource utilization
   - Handle exceptions properly

4. MEMORY MANAGEMENT:
   - Process large files in chunks
   - Use generators for streaming
   - Clear processed data
   - Monitor system resources

5. ERROR HANDLING:
   - Implement retry logic
   - Log failed records
   - Continue on errors
   - Provide progress updates

Performance Tips:
- Batch size: 100-500 records optimal
- Use async for 3x+ speedup on I/O
- Pre-compile regex patterns
- Cache model instances
""")

print("\nExample completed successfully!")
