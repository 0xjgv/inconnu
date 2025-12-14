"""Test suite for nlp.pipe() batch processing performance optimization.

This test suite compares the performance of:
1. Sequential processing (calling redact() in a loop)
2. Optimized nlp.pipe() batch processing

The nlp.pipe() method in spaCy is optimized for batch processing and should
provide significant speedups for processing multiple documents.
"""

import statistics
import time

import pytest

from inconnu import Inconnu


class TestNlpPipePerformance:
    """Test nlp.pipe() optimization performance."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        # Warm up the model to ensure fair comparison
        self.inconnu = Inconnu()
        _ = self.inconnu.redact("warmup text with john@example.com")

    def test_pipe_vs_sequential_small_batch(self):
        """Compare pipe vs sequential for small batches (50 docs)."""
        documents = [
            f"Document {i}: John Doe{i} at john{i}@email.com called 555-{i:04d}"
            for i in range(50)
        ]

        # Sequential processing (use_pipe=False)
        start_seq = time.time()
        seq_results = self.inconnu.redact_batch(documents, use_pipe=False)
        time_seq = time.time() - start_seq

        # Pipe-based processing (use_pipe=True, default)
        start_pipe = time.time()
        pipe_results = self.inconnu.redact_batch(documents, use_pipe=True)
        time_pipe = time.time() - start_pipe

        # Results should be identical
        assert seq_results == pipe_results, "Results differ between methods"

        speedup = time_seq / time_pipe if time_pipe > 0 else float("inf")

        print("\n" + "=" * 60)
        print("Small batch (50 documents) comparison:")
        print("=" * 60)
        print(f"  Sequential:  {time_seq:.3f}s ({len(documents)/time_seq:.1f} docs/s)")
        print(f"  nlp.pipe():  {time_pipe:.3f}s ({len(documents)/time_pipe:.1f} docs/s)")
        print(f"  Speedup:     {speedup:.2f}x")
        print("=" * 60)

        # nlp.pipe() should be at least as fast (allow 10% margin for variance)
        assert time_pipe <= time_seq * 1.1, (
            f"nlp.pipe() ({time_pipe:.3f}s) significantly slower than "
            f"sequential ({time_seq:.3f}s)"
        )

    def test_pipe_vs_sequential_medium_batch(self):
        """Compare pipe vs sequential for medium batches (200 docs)."""
        documents = [
            f"Document {i}: Contact user{i}@company.com or call +1-555-{i:04d}. "
            f"SSN: {100+i}-45-{6789+i}. Employee ID: EMP-{10000+i}"
            for i in range(200)
        ]

        # Run multiple times for more stable measurements
        seq_times = []
        pipe_times = []

        for _ in range(3):
            start_seq = time.time()
            seq_results = self.inconnu.redact_batch(documents, use_pipe=False)
            seq_times.append(time.time() - start_seq)

            start_pipe = time.time()
            pipe_results = self.inconnu.redact_batch(documents, use_pipe=True)
            pipe_times.append(time.time() - start_pipe)

        # Use median for stability
        time_seq = statistics.median(seq_times)
        time_pipe = statistics.median(pipe_times)

        # Results should be identical
        assert seq_results == pipe_results, "Results differ between methods"

        speedup = time_seq / time_pipe if time_pipe > 0 else float("inf")

        print("\n" + "=" * 60)
        print("Medium batch (200 documents) comparison:")
        print("=" * 60)
        print(f"  Sequential:  {time_seq:.3f}s ({len(documents)/time_seq:.1f} docs/s)")
        print(f"  nlp.pipe():  {time_pipe:.3f}s ({len(documents)/time_pipe:.1f} docs/s)")
        print(f"  Speedup:     {speedup:.2f}x")
        print("=" * 60)

        # nlp.pipe() should provide measurable improvement for medium batches
        assert time_pipe <= time_seq * 1.1, (
            f"nlp.pipe() ({time_pipe:.3f}s) significantly slower than "
            f"sequential ({time_seq:.3f}s)"
        )

    def test_pipe_vs_sequential_large_batch(self):
        """Compare pipe vs sequential for large batches (500 docs)."""
        documents = [
            f"Document {i}: Dr. Jane Smith contacted patient{i}@hospital.org "
            f"regarding case #{2024}-CV-{10000+i}. Phone: 555-{i:04d}"
            for i in range(500)
        ]

        # Sequential processing
        start_seq = time.time()
        seq_results = self.inconnu.redact_batch(documents, use_pipe=False)
        time_seq = time.time() - start_seq

        # Pipe-based processing
        start_pipe = time.time()
        pipe_results = self.inconnu.redact_batch(documents, use_pipe=True)
        time_pipe = time.time() - start_pipe

        # Results should be identical
        assert seq_results == pipe_results, "Results differ between methods"

        speedup = time_seq / time_pipe if time_pipe > 0 else float("inf")

        print("\n" + "=" * 60)
        print("Large batch (500 documents) comparison:")
        print("=" * 60)
        print(f"  Sequential:  {time_seq:.3f}s ({len(documents)/time_seq:.1f} docs/s)")
        print(f"  nlp.pipe():  {time_pipe:.3f}s ({len(documents)/time_pipe:.1f} docs/s)")
        print(f"  Speedup:     {speedup:.2f}x")
        print("=" * 60)

        # nlp.pipe() should provide speedup for large batches
        assert time_pipe <= time_seq * 1.1, (
            f"nlp.pipe() ({time_pipe:.3f}s) significantly slower than "
            f"sequential ({time_seq:.3f}s)"
        )

    def test_pipe_batch_size_impact(self):
        """Test impact of different batch_size values on nlp.pipe() performance."""
        documents = [
            f"Test document {i} with email{i}@test.com and phone 555-{i:04d}"
            for i in range(300)
        ]

        batch_sizes = [8, 16, 32, 64, 128]
        results_by_batch_size = {}

        for batch_size in batch_sizes:
            start = time.time()
            results = self.inconnu.redact_batch(
                documents, use_pipe=True, batch_size=batch_size
            )
            elapsed = time.time() - start
            results_by_batch_size[batch_size] = {
                "time": elapsed,
                "throughput": len(documents) / elapsed,
                "results": results,
            }

        print("\n" + "=" * 60)
        print("Batch size impact on nlp.pipe() performance:")
        print("=" * 60)
        for batch_size, data in results_by_batch_size.items():
            print(
                f"  batch_size={batch_size:3d}: {data['time']:.3f}s "
                f"({data['throughput']:.1f} docs/s)"
            )
        print("=" * 60)

        # All results should be identical regardless of batch_size
        first_results = results_by_batch_size[batch_sizes[0]]["results"]
        for batch_size in batch_sizes[1:]:
            assert results_by_batch_size[batch_size]["results"] == first_results, (
                f"Results differ for batch_size={batch_size}"
            )

    def test_pseudonymize_batch_pipe_optimization(self):
        """Test nlp.pipe() optimization for pseudonymize_batch."""
        documents = [
            f"User {i}: Contact john.doe{i}@example.com for order ORD-2024-{i:06d}"
            for i in range(100)
        ]

        # Sequential processing
        start_seq = time.time()
        seq_results = self.inconnu.pseudonymize_batch(documents, use_pipe=False)
        time_seq = time.time() - start_seq

        # Pipe-based processing
        start_pipe = time.time()
        pipe_results = self.inconnu.pseudonymize_batch(documents, use_pipe=True)
        time_pipe = time.time() - start_pipe

        speedup = time_seq / time_pipe if time_pipe > 0 else float("inf")

        print("\n" + "=" * 60)
        print("Pseudonymize batch (100 documents) comparison:")
        print("=" * 60)
        print(f"  Sequential:  {time_seq:.3f}s")
        print(f"  nlp.pipe():  {time_pipe:.3f}s")
        print(f"  Speedup:     {speedup:.2f}x")
        print("=" * 60)

        # Verify results have same structure (redacted text + entity map)
        assert len(seq_results) == len(pipe_results)
        for seq_result, pipe_result in zip(seq_results, pipe_results):
            seq_text, seq_map = seq_result
            pipe_text, pipe_map = pipe_result
            # Both should have redacted the same entities
            assert isinstance(seq_text, str)
            assert isinstance(pipe_text, str)
            assert isinstance(seq_map, dict)
            assert isinstance(pipe_map, dict)

    def test_pipe_correctness_with_entities(self):
        """Verify nlp.pipe() produces correct redactions."""
        test_cases = [
            (
                "Contact John Smith at john.smith@email.com",
                ["[PERSON]", "[EMAIL]"],
            ),
            (
                "Call Dr. Jane Doe at 555-123-4567",
                ["[PERSON]", "[PHONE_NUMBER]"],
            ),
            (
                "SSN: 123-45-6789, Credit Card: 4111-1111-1111-1111",
                ["[SSN]", "[CREDIT_CARD]"],
            ),
            (
                "Student ID: ABC-1234-5678, Employee ID: EMP-12345",
                ["[STUDENT_ID]", "[EMPLOYEE_ID]"],
            ),
        ]

        texts = [case[0] for case in test_cases]
        expected_markers = [case[1] for case in test_cases]

        # Process with nlp.pipe()
        results = self.inconnu.redact_batch(texts, use_pipe=True)

        for i, (result, markers) in enumerate(zip(results, expected_markers)):
            for marker in markers:
                assert marker in result, (
                    f"Expected {marker} in result for test case {i}: {result}"
                )

        print("\n" + "=" * 60)
        print("Correctness verification passed:")
        print("=" * 60)
        for i, (original, result) in enumerate(zip(texts, results)):
            print(f"  Input:  {original[:50]}...")
            print(f"  Output: {result[:50]}...")
            print()


class TestNlpPipeEdgeCases:
    """Test edge cases for nlp.pipe() batch processing."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.inconnu = Inconnu()
        _ = self.inconnu.redact("warmup")

    def test_empty_batch(self):
        """Test handling of empty batch."""
        results = self.inconnu.redact_batch([], use_pipe=True)
        assert results == []

    def test_single_document_batch(self):
        """Test batch with single document."""
        documents = ["Single doc: john@email.com"]

        seq_result = self.inconnu.redact_batch(documents, use_pipe=False)
        pipe_result = self.inconnu.redact_batch(documents, use_pipe=True)

        assert seq_result == pipe_result

    def test_batch_with_empty_strings(self):
        """Test batch containing empty strings."""
        documents = ["", "Valid: john@test.com", "", "Another: 555-1234", ""]

        seq_results = self.inconnu.redact_batch(documents, use_pipe=False)
        pipe_results = self.inconnu.redact_batch(documents, use_pipe=True)

        assert seq_results == pipe_results
        assert len(pipe_results) == 5

    def test_batch_with_long_documents(self):
        """Test batch with varying document lengths."""
        documents = [
            "Short doc",
            "Medium document with john@email.com and phone 555-1234. " * 10,
            "Very long document. " * 100 + "Contact: long@email.com",
            "x",  # Very short
        ]

        seq_results = self.inconnu.redact_batch(documents, use_pipe=False)
        pipe_results = self.inconnu.redact_batch(documents, use_pipe=True)

        assert seq_results == pipe_results

    def test_batch_with_unicode(self):
        """Test batch with unicode characters."""
        documents = [
            "Contact: münchen@example.de",
            "Japanese: 田中太郎 at tanaka@example.jp",
            "Arabic: محمد at mohamed@example.sa",
            "Emoji: Contact 👤 at emoji@test.com",
        ]

        seq_results = self.inconnu.redact_batch(documents, use_pipe=False)
        pipe_results = self.inconnu.redact_batch(documents, use_pipe=True)

        assert seq_results == pipe_results


class TestNlpPipeThroughput:
    """Throughput benchmarks for nlp.pipe() optimization."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures."""
        self.inconnu = Inconnu()
        _ = self.inconnu.redact("warmup")

    def test_throughput_benchmark(self):
        """Benchmark overall throughput with nlp.pipe()."""
        # Create realistic documents
        documents = []
        for i in range(1000):
            doc = (
                f"Document #{i}: "
                f"Contact: user{i}@company.com, "
                f"Phone: +1-555-{i:04d}, "
                f"Ref: ORD-2024-{i:06d}"
            )
            documents.append(doc)

        # Measure throughput
        start = time.time()
        results = self.inconnu.redact_batch(documents, use_pipe=True)
        elapsed = time.time() - start

        throughput = len(documents) / elapsed
        total_chars = sum(len(d) for d in documents)
        chars_per_second = total_chars / elapsed

        print("\n" + "=" * 60)
        print("Throughput benchmark (1000 documents):")
        print("=" * 60)
        print(f"  Total time:      {elapsed:.2f}s")
        print(f"  Documents/sec:   {throughput:.1f}")
        print(f"  Characters/sec:  {chars_per_second:,.0f}")
        print(f"  Avg doc length:  {total_chars/len(documents):.0f} chars")
        print("=" * 60)

        assert len(results) == len(documents)

        # Throughput should be reasonable (at least 50 docs/sec)
        assert throughput >= 50, f"Throughput too low: {throughput:.1f} docs/sec"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
