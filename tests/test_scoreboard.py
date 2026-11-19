from copy import deepcopy

import pytest

from evals import scoreboard as board


def sample():
    gold = {"jwt": 100, "CARD": 10, "PERSON": 20}
    return {
        "gold": gold,
        "leaks": {"jwt": 0, "CARD": 0, "PERSON": 0},
        "original": [1, 100],
        "added": [2, 10],
        "deps": ["a"],
        "timing": [
            {"base": {"p99": 100, "batch": 1}, "candidate": {"p99": 100, "batch": 1}}
            for _ in range(5)
        ],
        "commit": "1" * 40,
        "passed": True,
        "corpus": "first",
    }


def test_cost_uses_full_spans_and_counts_each_false_row_once():
    row = sample()
    row["leaks"].update(jwt=1, CARD=1, PERSON=1)
    cost, score, secret, pii = board.totals(row)
    assert (cost, secret, pii) == (36, 1, 2)
    assert score == pytest.approx(100 * (1 - 36 / 2160))
    row["leaks"] = row["gold"]
    row["original"][0] = row["added"][0] = 0
    assert board.totals(row)[1] == 0


def test_gate_boundaries_use_exact_counts_and_parent_vs_baseline():
    baseline = sample()
    parent = deepcopy(baseline)
    parent["leaks"]["jwt"] = 3
    row = deepcopy(parent)
    row["leaks"]["jwt"] = 4
    for pair in row["timing"]:
        pair["candidate"]["p99"] = 125
    assert all(flag for flag, _ in board.gates(row, baseline, parent).values())
    row["leaks"]["jwt"] = 5
    for pair in row["timing"]:
        pair["candidate"]["p99"] = 125.1
    row["original"][0] = 2
    row["deps"].append("b")
    assert all(not flag for flag, _ in board.gates(row, baseline, parent).values())
    assert board.dependencies(
        "[project]\ndependencies=[\"My_Pkg[extra]>=1; python_version > '3'\"]"
    ) == ["my-pkg"]


def test_epoch_remeasures_parent_and_keeps_failed_row_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(board, "paired_timing", lambda *a, **kw: sample()["timing"])
    md = tmp_path / "score.md"
    md.write_text("# Benchmark\n")
    monkeypatch.setattr(board, "BOARD", md)
    monkeypatch.setattr(board, "ROOT", tmp_path)
    (tmp_path / "evals").mkdir()
    previous = sample()
    new = deepcopy(previous)
    new["commit"] = "2" * 40
    new["leaks"]["jwt"] = 2
    versions = {r["commit"]: r for r in (previous, new)}
    monkeypatch.setattr(
        board,
        "snapshot",
        lambda corpus, revision, **kwargs: deepcopy(versions[revision]),
    )
    monkeypatch.setattr(
        board, "nearest", lambda rows, *args, **kwargs: rows[-1] if rows else None
    )
    corpus = tmp_path / "dev"
    corpus.write_text("epoch 1")
    assert board.evaluate("append", corpus, previous["commit"], "Baseline") == 0
    corpus.write_text("epoch 2")
    with pytest.raises(SystemExit, match="REASON"):
        board.evaluate("append", corpus, new["commit"], "Candidate")
    assert (
        board.evaluate(
            "append", corpus, new["commit"], "Candidate", "Audit the regression"
        )
        == 1
    )
    first, baseline, candidate = board.history(md.read_text())
    assert first["corpus"] != baseline["corpus"] == candidate["corpus"]
    assert baseline["commit"] == first["commit"]
    assert not candidate["passed"]
    with pytest.raises(SystemExit, match="already has a row"):
        board.evaluate("append", corpus, new["commit"], "Duplicate")


def test_holdout_uses_one_fresh_sample_for_all_versions_and_does_not_append(
    tmp_path, monkeypatch
):
    corpus = tmp_path / "dev"
    corpus.write_text("new seed")
    base = sample()
    parent = {**base, "commit": "2" * 40}
    current = {**base, "commit": "3" * 40}
    monkeypatch.setattr(board, "paired_timing", lambda *a, **kw: sample()["timing"])
    md = tmp_path / "score.md"
    md.write_text(
        "".join(
            board.render(row, "old", board.gates(row, base, base))
            for row in (base, parent)
        )
    )
    original = md.read_bytes()
    monkeypatch.setattr(board, "BOARD", md)
    monkeypatch.setattr(board, "nearest", lambda *a, **kw: parent)
    measured = []

    def snapshot(path, revision, **kw):
        measured.append((path, revision))
        return {**current, "commit": revision}

    monkeypatch.setattr(board, "snapshot", snapshot)
    assert (
        board.evaluate(
            "holdout",
            corpus,
            current["commit"],
            "Holdout",
            holdout_seed=7,
            dev_digest="first",
        )
        == 0
    )
    assert measured == [(corpus, r["commit"]) for r in (current, base, parent)]
    assert md.read_bytes() == original


def test_spread_takes_precedence_and_pair_order_alternates(monkeypatch, tmp_path):
    from contextlib import nullcontext

    calls = []
    monkeypatch.setattr(board, "detector_tree", lambda rev, *a: nullcontext(rev))

    def timing(task, corpus, rev):
        assert task == "_latency" and corpus == tmp_path
        calls.append(rev)
        return {"p99": 100, "batch": 1.0}

    monkeypatch.setattr(board, "worker", timing)
    samples = board.paired_timing(tmp_path, "B", "A")
    assert "".join(calls) == "ABBAABBAAB"
    for pair in samples:
        pair["candidate"]["batch"] = 1.16
    assert board.latency_gate(samples)[0] is False
    samples[0]["candidate"]["batch"] = 1.4
    assert board.latency_gate(samples)[0] is None
