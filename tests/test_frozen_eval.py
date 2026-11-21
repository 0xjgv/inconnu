import pytest

from evals.frozen_eval import compare, measure


def output(*spans, text=None):
    return {"output": text, "spans": spans}


def gold(identifier, kind="PHONE"):
    return {
        "id": identifier,
        "category": "positive",
        "text": "0123456789",
        "spans": [{"start": 0, "end": 10, "type": kind}],
    }


def negative(identifier, category):
    return {"id": identifier, "category": category, "text": "ordinary", "spans": []}


def test_equal_counts_report_swapped_case_failures():
    rows = [gold(1), gold(2)]
    base = measure(rows, [output((0, 10)), output()])
    candidate = measure(rows, [output((0, 9)), output((0, 10))])
    result = compare(base, candidate)

    assert result["passed"] is True
    assert result["new_failures"] == {"PHONE": ["1:0-10"]}
    assert result["recovered"] == {"PHONE": ["2:0-10"]}


def test_same_cost_cannot_hide_a_new_fully_uncovered_span():
    rows = [gold(1), *(negative(i, "neg:prose") for i in range(2, 5))]
    base = measure(rows, [output((0, 10)), *[output((0, 2))] * 3])
    candidate = measure(rows, [output((0, 9)), *[output()] * 3])
    result = compare(base, candidate)

    assert base["cost"] == candidate["cost"]
    assert result["passed"] is False
    assert result["count_increases"] == {"PHONE": 1}


def test_false_redactions_in_each_bucket_gate_independently():
    rows = [gold(1), negative(2, "neg:prose"), negative(3, "neg:new-case")]
    base = measure(rows, [output((0, 10)), output((0, 2)), output()])
    candidate = measure(rows, [output((0, 10)), output(), output((0, 2))])

    assert compare(base, candidate)["count_increases"] == {"added": 1}
    assert compare(candidate, base)["count_increases"] == {"original": 1}


def test_named_case_requires_correct_output_even_if_base_was_wrong():
    rows = [gold(1), {"id": "table", "text": "| value |", "expected": "| [PERSON] |"}]
    stats = measure(rows, [output((0, 10)), output((2, 7), text="[PERSON]")])

    assert compare(stats, stats)["named_failures"] == ["table"]
    assert compare(stats, stats)["passed"] is False


def test_incomplete_or_invalid_detector_results_are_rejected():
    with pytest.raises(ValueError, match="shorter"):
        measure([gold(1)], [])
    with pytest.raises(ValueError, match="Invalid prediction span"):
        measure([gold(1)], [output((0, 11))])
