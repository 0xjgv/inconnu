"""Complete credential removal, useful surrounding context retained."""


def test_full_span_metric_catches_partial_leak():
    from evals.run import score

    record = {
        "category": "pos:SECRET",
        "spans": [{"start": 0, "end": 10, "type": "SECRET", "kind": "jwt"}],
    }
    result = score([record], [[(0, 9, "SECRET:jwt", "rule")]])
    assert result["recall"]["jwt"] == result["covered"]["jwt"] == 1
    assert result["fully_covered"]["jwt"] == 0
