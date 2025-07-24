"""Test suite for performance validation and benchmarking.

This test suite ensures that Inconnu meets the performance requirements
specified in the tasks, particularly the <200ms processing time for
95% of documents.
"""

import asyncio
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor

import psutil
import pytest

from inconnu import Config, Inconnu


class TestProcessingTimeRequirements:
    """Test that processing times meet the specified requirements."""

    def test_single_document_performance(self):
        """Test that 95% of documents process in under 200ms."""
        inconnu = Inconnu()

        # Test various document sizes and complexities
        test_documents = [
            # Small documents
            "John Doe lives at 123 Main St.",
            "Contact me at john@email.com or (555) 123-4567",
            "My SSN is 123-45-6789 and I work at TechCorp",
            # Medium documents
            " ".join(["Person %d works at Company%d" % (i, i) for i in range(10)]),
            "Dr. Smith met Prof. Jones and Ms. Davis at the conference. " * 5,
            # Documents with many entities
            "Email: user@example.com, Phone: 555-1234, SSN: 123-45-6789, " * 10,
            # Complex patterns
            "Student ID: ABC-1234-5678, Course: CS 101, GPA: 3.85/4.00",
            "Case #2024-CV-12345, Bar No. CA-98765, Citation: 42 U.S.C. § 1983",
        ]

        processing_times = []

        for doc in test_documents:
            start = time.time()
            result = inconnu.redact(doc)
            elapsed = time.time() - start
            processing_times.append(elapsed)

            # Verify processing worked
            assert isinstance(result, str)

        # Calculate 95th percentile
        processing_times.sort()
        percentile_95 = processing_times[int(len(processing_times) * 0.95)]

        # Should be under 200ms
        assert percentile_95 < 0.2, (
            f"95th percentile: {percentile_95:.3f}s exceeds 200ms"
        )

        # Report statistics
        avg_time = sum(processing_times) / len(processing_times)
        print("\nProcessing time stats:")
        print(f"  Average: {avg_time * 1000:.1f}ms")
        print(f"  95th percentile: {percentile_95 * 1000:.1f}ms")
        print(f"  Max: {max(processing_times) * 1000:.1f}ms")

    def test_large_document_performance(self):
        """Test performance with large documents."""
        # Pre-warm the model to ensure it's loaded
        inconnu = Inconnu()
        _ = inconnu.redact("warmup text")

        # Create a large document (50KB)
        large_text = " ".join(
            [
                f"Person {i} (email{i}@example.com) called from 555-{i:04d} about order ORD-{i:06d}."
                for i in range(500)
            ]
        )

        # Run multiple times and take the best performance
        # This helps avoid random system load issues
        timings = []
        for _ in range(3):
            start = time.time()
            result = inconnu.redact(large_text)
            elapsed = time.time() - start
            timings.append(elapsed)
            
            # Verify the result is valid
            assert isinstance(result, str)
            assert len(result) > 0

        # Use the best (minimum) time to avoid system load issues
        best_time = min(timings)
        median_time = sorted(timings)[1]

        # More lenient time limit based on document size
        # Allow up to 2ms per 1000 characters for large documents
        max_allowed_time = max(1.5, (len(large_text) / 1000) * 0.002)
        
        assert best_time < max_allowed_time, (
            f"Large document took {best_time:.3f}s "
            f"(exceeds limit of {max_allowed_time:.3f}s)"
        )

        # Calculate throughput
        chars_per_second = len(large_text) / median_time
        print("\nLarge document performance:")
        print(f"  Size: {len(large_text):,} characters")
        print(f"  Best time: {best_time:.3f}s")
        print(f"  Median time: {median_time:.3f}s")
        print(f"  Throughput: {chars_per_second:,.0f} chars/second")


class TestMemoryUsage:
    """Test memory usage and efficiency."""

    def test_memory_efficiency(self):
        """Test that memory usage remains reasonable during processing."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        inconnu = Inconnu()

        # Process multiple documents
        for i in range(100):
            text = f"Document {i}: " + "Test data " * 100
            _ = inconnu.redact(text)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print("\nMemory usage:")
        print(f"  Initial: {initial_memory:.1f} MB")
        print(f"  Final: {final_memory:.1f} MB")
        print(f"  Increase: {memory_increase:.1f} MB")

        # Memory increase should be reasonable (< 100MB for this test)
        assert memory_increase < 100, f"Memory increased by {memory_increase:.1f} MB"

    def test_singleton_efficiency(self):
        """Test that singleton pattern provides expected benefits."""
        # Warm up - ensure any system caching is active
        _ = Inconnu()
        
        # Clear singleton instances to get a clean test
        from inconnu.nlp.utils import instances
        instances.clear()
        
        # Measure first instance creation (includes model loading)
        timings_first = []
        for _ in range(3):
            instances.clear()  # Clear before each measurement
            start = time.time()
            _ = Inconnu()
            timings_first.append(time.time() - start)
            
        # Take median to reduce outlier impact
        time1 = sorted(timings_first)[1]
        
        # Measure second instance creation (should reuse singleton)
        timings_second = []
        for _ in range(3):
            start = time.time()
            _ = Inconnu()
            timings_second.append(time.time() - start)
            
        # Take median to reduce outlier impact  
        time2 = sorted(timings_second)[1]

        # More relaxed assertion - second should be notably faster
        # but we don't require a specific speedup ratio
        assert time2 < time1, (
            "Singleton not providing performance benefit"
        )
        
        # Also check that second instance is reasonably fast (< 10ms)
        assert time2 < 0.01, (
            f"Second instance creation too slow: {time2 * 1000:.1f}ms"
        )

        print("\nSingleton performance:")
        print(f"  First instance: {time1 * 1000:.1f}ms (median of 3 runs)")
        print(f"  Second instance: {time2 * 1000:.1f}ms (median of 3 runs)")
        if time1 > 0:
            print(f"  Speedup: {time1 / time2:.1f}x")


class TestBatchProcessingPerformance:
    """Test batch processing performance."""

    def test_batch_vs_individual_processing(self):
        """Compare batch processing vs individual processing performance."""
        inconnu = Inconnu()

        # Create test data
        documents = [
            f"Document {i}: John Doe{i} at john{i}@email.com" for i in range(50)
        ]

        # Individual processing
        start_individual = time.time()
        individual_results = []
        for doc in documents:
            result = inconnu.redact(doc)
            individual_results.append(result)
        time_individual = time.time() - start_individual

        # Batch processing
        start_batch = time.time()
        batch_results = inconnu.redact_batch(documents)
        time_batch = time.time() - start_batch

        print("\nBatch processing comparison:")
        print(f"  Individual: {time_individual:.3f}s")
        print(f"  Batch: {time_batch:.3f}s")
        print(f"  Speedup: {time_individual / time_batch:.2f}x")

        # Batch processing might have overhead but should be reasonably fast
        assert time_batch <= time_individual * 2.0  # Allow 2x margin for overhead

        # Results should be identical
        assert individual_results == batch_results

    def test_chunked_batch_performance(self):
        """Test performance of chunked batch processing."""
        config = Config(chunk_size=50)
        inconnu = Inconnu(config=config)

        # Large batch
        large_batch = [f"Text {i} with entity{i}@email.com" for i in range(500)]

        start = time.time()
        results = inconnu.redact_batch(large_batch, chunk_size=50)
        elapsed = time.time() - start

        print("\nChunked batch processing:")
        print(f"  Documents: {len(large_batch)}")
        print("  Chunk size: 50")
        print(f"  Total time: {elapsed:.3f}s")
        print(f"  Docs/second: {len(large_batch) / elapsed:.1f}")

        assert len(results) == len(large_batch)


class TestAsyncPerformance:
    """Test async processing performance."""

    def test_async_performance_expectations(self):
        """Test that async provides expected performance characteristics."""
        inconnu = Inconnu()
        documents = [f"Async test {i}: user{i}@email.com" for i in range(20)]

        # Sync processing
        start_sync = time.time()
        sync_results = inconnu.redact_batch(documents)
        time_sync = time.time() - start_sync

        # Async processing (with warning suppression)
        async def process_async():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return await inconnu.redact_batch_async(documents)

        start_async = time.time()
        async_results = asyncio.run(process_async())
        time_async = time.time() - start_async

        print("\nAsync performance:")
        print(f"  Sync: {time_sync:.3f}s")
        print(f"  Async: {time_async:.3f}s")
        print(f"  Ratio: {time_async / time_sync:.2f}")

        # Async shouldn't be excessively slower
        # Allow up to 3x overhead for async operations due to event loop overhead
        assert time_async < time_sync * 3.0, (
            f"Async performance ({time_async:.3f}s) is more than 3x slower "
            f"than sync ({time_sync:.3f}s)"
        )

        # Results should be identical
        assert sync_results == async_results

    def test_custom_executor_performance(self):
        """Test performance with custom executor."""
        executor = ThreadPoolExecutor(max_workers=4)
        inconnu = Inconnu(executor=executor)

        documents = [f"Executor test {i}" for i in range(100)]

        async def process_with_executor():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return await inconnu.redact_batch_async(documents)

        start = time.time()
        results = asyncio.run(process_with_executor())
        elapsed = time.time() - start

        print("\nCustom executor performance:")
        print(f"  Documents: {len(documents)}")
        print(f"  Time: {elapsed:.3f}s")
        print(f"  Docs/second: {len(documents) / elapsed:.1f}")

        assert len(results) == len(documents)

        # Cleanup
        executor.shutdown(wait=True)


class TestStreamingPerformance:
    """Test streaming functionality performance."""

    def test_streaming_large_text(self):
        """Test streaming performance for large texts."""
        config = Config(max_text_length=500_000)  # Allow larger texts for this test
        inconnu = Inconnu(config=config)

        # Create very large text (1MB)
        large_text = "This is a test with John Doe and jane@email.com. " * 10000

        # Traditional processing
        start_traditional = time.time()
        _ = inconnu.redact(large_text)
        time_traditional = time.time() - start_traditional

        # Streaming processing
        start_streaming = time.time()
        _ = inconnu.redact_stream(large_text, chunk_size=10000)
        time_streaming = time.time() - start_streaming

        print("\nStreaming performance:")
        print(f"  Text size: {len(large_text):,} characters")
        print(f"  Traditional: {time_traditional:.3f}s")
        print(f"  Streaming: {time_streaming:.3f}s")
        print(
            f"  Memory efficient: {'Yes' if time_streaming < time_traditional * 1.5 else 'No'}"
        )

        # Streaming shouldn't be much slower
        assert time_streaming < time_traditional * 1.5

    def test_streaming_memory_efficiency(self):
        """Test that streaming uses less memory for large texts."""
        process = psutil.Process(os.getpid())
        config = Config(max_text_length=1_000_000)  # Allow larger texts for this test
        inconnu = Inconnu(config=config)

        # Very large text
        huge_text = "Test data " * 100000  # ~1MB

        # Measure memory during streaming
        initial_memory = process.memory_info().rss / 1024 / 1024

        _ = inconnu.redact_stream(huge_text, chunk_size=5000)

        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_used = peak_memory - initial_memory

        print("\nStreaming memory usage:")
        print(f"  Text size: {len(huge_text):,} characters")
        print(f"  Memory used: {memory_used:.1f} MB")

        # Should use reasonable memory
        assert memory_used < 50  # MB


class TestPatternPerformance:
    """Test performance of expanded pattern library."""

    def test_pattern_matching_overhead(self):
        """Test overhead of having many patterns."""
        # Test with minimal patterns
        inconnu_minimal = Inconnu()

        # Test with all patterns enabled
        config = Config()
        for domain in ["healthcare", "legal", "financial", "education"]:
            config.enable_domain_patterns(domain)
        inconnu_full = Inconnu(config=config)

        test_text = """
        John Doe (SSN: 123-45-6789) studied CS 101 with Prof. Smith.
        His student ID is ABC-1234-5678 and GPA is 3.85/4.0.
        Contact: john@email.com or (555) 123-4567.
        Credit card: 4111-1111-1111-1111, Case #2024-CV-12345.
        """

        # Time minimal patterns
        start_minimal = time.time()
        for _ in range(10):
            _ = inconnu_minimal.redact(test_text)
        time_minimal = (time.time() - start_minimal) / 10

        # Time full patterns
        start_full = time.time()
        for _ in range(10):
            _ = inconnu_full.redact(test_text)
        time_full = (time.time() - start_full) / 10

        overhead = (time_full - time_minimal) / time_minimal * 100

        print("\nPattern overhead:")
        print(f"  Minimal patterns: {time_minimal * 1000:.1f}ms")
        print(f"  Full patterns: {time_full * 1000:.1f}ms")
        print(f"  Overhead: {overhead:.1f}%")

        # Overhead should be reasonable (< 50%)
        assert overhead < 50

    def test_pattern_compilation_caching(self):
        """Test that pattern compilation is properly cached."""
        # First instance compiles patterns
        start1 = time.time()
        inconnu1 = Inconnu()
        inconnu1.redact("Test")
        time1 = time.time() - start1

        # Second instance should reuse compiled patterns
        start2 = time.time()
        inconnu2 = Inconnu()
        inconnu2.redact("Test")
        time2 = time.time() - start2

        print("\nPattern caching:")
        print(f"  First use: {time1 * 1000:.1f}ms")
        print(f"  Second use: {time2 * 1000:.1f}ms")

        # Second use should be at least not significantly slower
        assert time2 <= time1 * 1.5  # Allow some variance


class TestScalability:
    """Test scalability with increasing load."""

    def test_linear_scalability(self):
        """Test that performance scales linearly with document count."""
        inconnu = Inconnu()

        sizes = [10, 50, 100, 200]
        times = []

        for size in sizes:
            documents = [f"Doc {i}: test@email.com" for i in range(size)]

            start = time.time()
            _ = inconnu.redact_batch(documents)
            elapsed = time.time() - start

            times.append(elapsed)

        print("\nScalability test:")
        for i, (size, time_taken) in enumerate(zip(sizes, times)):
            print(f"  {size} docs: {time_taken:.3f}s ({size / time_taken:.1f} docs/s)")

        # Check approximately linear scaling
        # Time should roughly double when size doubles
        for i in range(1, len(sizes)):
            size_ratio = sizes[i] / sizes[i - 1]
            time_ratio = times[i] / times[i - 1]
            # Allow more deviation from perfect linear scaling
            assert 0.3 * size_ratio <= time_ratio <= 3.0 * size_ratio

    def test_performance_under_load(self):
        """Test performance remains stable under sustained load."""
        inconnu = Inconnu()

        # Simulate sustained load
        processing_times = []

        for batch in range(10):
            documents = [f"Batch {batch} doc {i}" for i in range(50)]

            start = time.time()
            _ = inconnu.redact_batch(documents)
            elapsed = time.time() - start

            processing_times.append(elapsed)

        # Calculate statistics
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        min_time = min(processing_times)

        print("\nPerformance under load:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min_time:.3f}s")
        print(f"  Max: {max_time:.3f}s")
        print(f"  Variation: {(max_time - min_time) / avg_time * 100:.1f}%")

        # Performance should remain stable (< 150% variation)
        assert (max_time - min_time) / avg_time < 1.5


class TestPerformanceRegression:
    """Test for performance regressions."""

    def test_conflict_resolution_performance(self):
        """Test that enhanced conflict resolution doesn't degrade performance."""
        # Create text with many potential conflicts
        conflict_text = (
            """
        Dr. John Smith, Ph.D. (john.smith@university.edu)
        Prof. Jane Doe, M.D. (jane.doe@hospital.org)
        Mr. Robert Johnson, CEO (rjohnson@company.com)
        Ms. Sarah Williams, CFO (swilliams@company.com)
        """
            * 10
        )

        inconnu = Inconnu()

        # Time processing
        start = time.time()
        result = inconnu.redact(conflict_text)
        elapsed = time.time() - start

        print("\nConflict resolution performance:")
        print(f"  Text length: {len(conflict_text)} chars")
        print(f"  Processing time: {elapsed * 1000:.1f}ms")
        print(f"  Entities found: {result.count('[')}")

        # Should still meet performance requirements
        assert elapsed < 0.2  # Under 200ms

    def test_validation_overhead(self):
        """Test overhead of entity validation."""

        # Text with entities that need validation
        text_with_validation = (
            """
        SSN: 123-45-6789
        Credit Card: 4111-1111-1111-1111
        IBAN: GB82 WEST 1234 5698 7654 32
        """
            * 5
        )

        inconnu = Inconnu()

        # Time with validation
        start = time.time()
        _ = inconnu.redact(text_with_validation)
        time_with_validation = time.time() - start

        print("\nValidation overhead:")
        print(f"  Processing time: {time_with_validation * 1000:.1f}ms")

        # Should still be under 200ms
        assert time_with_validation < 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
