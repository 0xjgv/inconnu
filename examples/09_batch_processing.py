#!/usr/bin/env python3
"""
Batch Processing & Performance Optimization Example

This example demonstrates how to use Inconnu for high-volume data processing,
including CSV files, database exports, streaming data, and performance
optimization techniques for production environments.

This updated example demonstrates:
- Improved async handling with proper warnings
- Memory-efficient chunked batch processing
- Streaming support for large files
- Performance monitoring and optimization

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
import warnings
from concurrent.futures import ThreadPoolExecutor
from io import StringIO

from inconnu import Config, Inconnu

# Configure for batch processing optimization
config = Config(
    batch_size=100,
    chunk_size=1000,
    enable_performance_monitoring=True,
)

# Initialize Inconnu with custom executor for better async performance
executor = ThreadPoolExecutor(max_workers=4)
inconnu = Inconnu(config=config, executor=executor)

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

# Batch process all emails with chunk size optimization
anonymized_emails = inconnu.redact_batch(emails, chunk_size=2)

end_time = time.time()
print(f"Batch processing completed in {end_time - start_time:.2f} seconds")
print(f"Average time per email: {(end_time - start_time) / len(emails):.3f} seconds")

# Show first anonymized email
print("\nFirst anonymized email:")
print(anonymized_emails[0])

# Example 3: Async Batch Processing (with performance warning)
print("\n\n3. ASYNC BATCH PROCESSING (WITH PROPER EXPECTATIONS)")
print("-" * 30)
print("Note: Async methods now include warnings about CPU-bound NLP tasks")
print("For true parallelism, consider multiprocessing instead.")

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

    # Suppress warnings for demo
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Process in parallel using async
        results = await inconnu.redact_batch_async(large_dataset)

    end_time = time.time()
    print(f"Async processing completed in {end_time - start_time:.2f} seconds")
    print(f"Records per second: {len(large_dataset) / (end_time - start_time):.1f}")
    print(
        "Note: Async provides concurrency but not true parallelism for CPU-bound tasks"
    )

    return results


# Run async processing
anonymized_async = asyncio.run(process_async_batch())
print("\nFirst 3 async results:")
for i, result in enumerate(anonymized_async[:3]):
    print(f"  {i + 1}: {result}")

# Example 4: Streaming Data Processing (NEW FEATURE)
print("\n\n4. STREAMING DATA WITH NEW STREAM SUPPORT")
print("-" * 30)
print("Demonstrating the new streaming functionality for large texts")


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

# Process large text directly
large_log = "\n".join(generate_log_entries()) * 100  # Simulate large log file
print(f"\nProcessing large log file ({len(large_log)} chars)...")
process_start = time.time()
processed_result = inconnu.redact(large_log)
process_time = time.time() - process_start
print(f"Processing completed in {process_time:.3f} seconds")
print(f"Throughput: {len(large_log) / process_time:.0f} chars/second")

# Traditional per-entry processing
print("\nTraditional per-entry processing:")
for log_entry in generate_log_entries():
    # Process each log entry as it arrives
    anonymized_log = inconnu.redact(log_entry)
    processed_count += 1
    print(f"Processed: {anonymized_log}")

end_time = time.time()
print(
    f"\nProcessed {processed_count} log entries in {end_time - start_time:.2f} seconds"
)

# Example 5: Performance Comparison (UPDATED)
print("\n\n5. PERFORMANCE COMPARISON (SYNC VS ASYNC)")
print("-" * 30)
print("Comparing different processing methods with realistic expectations")

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
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return await inconnu.redact_batch_async(data)

    start = time.time()
    async_results = asyncio.run(async_test())
    async_time = time.time() - start

    # Note: Speedup may be minimal for CPU-bound NLP tasks
    speedup = sync_time / async_time if async_time > 0 else 0
    efficiency = "efficient" if speedup > 1.1 else "similar"
    print(
        f"{size:4d} | {sync_time:9.3f}s | {async_time:10.3f}s | {speedup:7.2f}x ({efficiency})"
    )

# Example 6: Memory-Efficient Processing
print("\n\n6. MEMORY-EFFICIENT LARGE FILE PROCESSING")
print("-" * 30)


def process_large_file_in_chunks(data_lines, chunk_size=100):
    """Process large files in chunks to manage memory - using new batch method"""
    print(f"Processing in chunks of {chunk_size} using improved batch processing...")

    # Process data in chunks using the new chunked batch processing
    start_total = time.time()

    # Use the new batch processing with chunk size
    results = inconnu.redact_batch(data_lines, chunk_size=chunk_size)

    total_time = time.time() - start_total
    total_processed = len(results)

    print(f"\nTotal records: {total_processed}")
    print(f"Total processing time: {total_time:.3f}s")
    print(f"Throughput: {total_processed / total_time:.1f} records/second")

    # Show performance stats
    stats = inconnu.get_performance_stats()
    print(f"\nPerformance stats: {stats}")

    return results


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

# Example 7: Demonstrating New Features
print("\n\n7. NEW BATCH PROCESSING FEATURES")
print("-" * 30)

# Demonstrate error handling in batch processing
print("\n7a. Error Handling in Batch Processing")
error_prone_data = [
    "Valid data: John Doe at john@email.com",
    None,  # This will cause an error
    "Another valid entry: Jane Smith (555) 123-4567",
    "",  # Empty string
    "Final entry: Bob Wilson, SSN: 123-45-6789",
]

try:
    # This will demonstrate error handling
    results = inconnu.redact_batch([d for d in error_prone_data if d is not None])
    print(f"Successfully processed {len(results)} entries with error handling")
except Exception as e:
    print(f"Batch processing error (as expected): {e}")

# Demonstrate pattern inspection
print("\n7b. Available Patterns for Batch Processing")
supported_patterns = inconnu.get_supported_patterns()
print(f"Total supported patterns: {len(supported_patterns)}")
print(
    f"Financial patterns: {[p for p in supported_patterns if 'CREDIT' in p or 'ROUTING' in p]}"
)

# Best Practices Summary (UPDATED)
print("\n\n" + "=" * 60)
print("UPDATED BEST PRACTICES FOR BATCH PROCESSING")
print("=" * 60)
print("""
1. PERFORMANCE OPTIMIZATION:
   - Use batch methods with chunk_size parameter
   - Understand async limitations for CPU-bound tasks
   - Use streaming for very large texts
   - Monitor performance with get_performance_stats()

2. CSV/STRUCTURED DATA:
   - Concatenate fields for processing
   - Preserve data structure
   - Handle special characters properly
   - Validate output format

3. ASYNC PROCESSING (UPDATED):
   - Best for I/O-bound operations (API calls, file I/O)
   - Limited benefit for CPU-bound NLP processing
   - Consider ThreadPoolExecutor for better control
   - Use multiprocessing for true parallelism

4. MEMORY MANAGEMENT:
   - Use redact_batch() with chunk_size parameter
   - Configure memory limits in Config
   - Monitor memory usage during processing

5. ERROR HANDLING:
   - Input validation
   - Graceful chunk failure handling
   - Progress logging for large batches

6. FEATURES:
   - Configurable chunk sizes
   - Performance monitoring
   - Pattern inspection and validation

Performance Tips:
- Chunk size: 100-1000 records based on text size
- Configure thread pool size for async batch processing
- Monitor with enable_performance_monitoring
""")

print("\nExample completed successfully!")
print("This example demonstrated:")
print("- Batch processing with chunks")
print("- Async batch processing")
print("- Performance monitoring capabilities")
print("- Error handling improvements")

# Cleanup
executor.shutdown(wait=True)
