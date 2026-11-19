"""Score inconnu and the reference detectors on evals/data; print a table and write evals/results/<split>.json.

Matching: a prediction is a true positive when it overlaps a gold span of the same type (any SECRET:* counts for a
secret). "covered" is the safety number: the share of gold spans whose characters are at least 90% inside any
prediction, whatever its label. False-redaction rate (FRR) is the share of negative records with any prediction.

Usage: python evals/run.py [--split test] [--no-latency]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import phonenumbers

import inconnu
from inconnu import redact, redact_batch

ROOT = Path(__file__).parent
PII = ["EMAIL", "PHONE", "IBAN", "CARD", "SSN", "IP", "PERSON"]


def family(kind: str) -> str:
    return "SECRET" if kind.startswith("SECRET") else kind


def load(split: str) -> list[dict]:
    return [json.loads(line) for line in (ROOT / "data" / f"{split}.jsonl").open()]


def predict_inconnu(records):
    return [
        [
            (f["start"], f["end"], f["type"], f["detector"])
            for f in redact(r["text"], key=r["key"])[1]
        ]
        for r in records
    ]


def predict_detect_secrets(records):
    from detect_secrets.core.scan import _process_line_based_plugins
    from detect_secrets.settings import default_settings

    out = []
    with default_settings():
        for r in records:
            found, offset = [], 0
            for line in r["text"].split("\n"):
                for secret in _process_line_based_plugins(
                    [(1, line)], "eval.txt"
                ):  # with detect-secrets' filters
                    value = secret.secret_value or ""
                    at = line.find(value) if value else -1
                    if at >= 0:
                        found.append(
                            (
                                offset + at,
                                offset + at + len(value),
                                "SECRET:" + secret.type,
                                "detect-secrets",
                            )
                        )
                offset += len(line) + 1
            out.append(found)
    return out


def predict_phone_regex(records):
    """The phonenumbers alternative: shape rules only (+ international, or NANP with separators)."""
    import re

    shape = re.compile(
        r"(?<![\w+])(?:\+\d{1,3}[ .-]?(?:\(\d{1,4}\)[ .-]?)?\d{1,4}(?:[ .-]?\d{2,4}){2,4}|\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4})(?![\w])"
    )
    return [
        [(m.start(), m.end(), "PHONE", "regex") for m in shape.finditer(r["text"])]
        for r in records
    ]


def score(records, predictions, types=None) -> dict:
    """types limits which predicted types count (for single-purpose references)."""
    gold_n, gold_hit, gold_cov = defaultdict(int), defaultdict(int), defaultdict(int)
    gold_full, neg_by_type = defaultdict(int), defaultdict(int)
    pred_n, pred_hit = defaultdict(int), defaultdict(int)
    neg_n, neg_hit, neg_by_detector = (
        defaultdict(int),
        defaultdict(int),
        defaultdict(int),
    )
    for record, preds in zip(records, predictions):
        preds = [p for p in preds if types is None or family(p[2]) in types]
        golds = record["spans"]
        for g in golds:
            key = g["kind"] if g["type"] == "SECRET" else g["type"]
            gold_n[key] += 1
            if any(
                p[0] < g["end"] and g["start"] < p[1] and family(p[2]) == g["type"]
                for p in preds
            ):
                gold_hit[key] += 1
            covered = set()
            for p in preds:
                covered.update(range(max(p[0], g["start"]), min(p[1], g["end"])))
            if len(covered) >= 0.9 * (g["end"] - g["start"]):
                gold_cov[key] += 1
            if len(covered) == g["end"] - g["start"]:
                gold_full[key] += 1
        for p in preds:
            pred_n[p[2]] += 1
            if any(
                p[0] < g["end"] and g["start"] < p[1] and family(p[2]) == g["type"]
                for g in golds
            ):
                pred_hit[p[2]] += 1
        if record["category"].startswith("neg:"):
            neg_n[record["category"]] += 1
            neg_hit[record["category"]] += bool(preds)
            for detector in {p[3] for p in preds}:
                neg_by_detector[detector] += 1
            for kind in {p[2] for p in preds}:
                neg_by_type[kind] += 1
    ratio = lambda a, b: round(a / b, 4) if b else None  # noqa: E731
    negatives = sum(neg_n.values())
    return {
        "recall": {k: ratio(gold_hit[k], gold_n[k]) for k in sorted(gold_n)},
        "covered": {k: ratio(gold_cov[k], gold_n[k]) for k in sorted(gold_n)},
        "fully_covered": {k: ratio(gold_full[k], gold_n[k]) for k in sorted(gold_n)},
        "gold": dict(sorted(gold_n.items())),
        "precision": {k: ratio(pred_hit[k], pred_n[k]) for k in sorted(pred_n)},
        "predicted": dict(sorted(pred_n.items())),
        "predicted_hits": dict(sorted(pred_hit.items())),
        "frr": {k: ratio(neg_hit[k], neg_n[k]) for k in sorted(neg_n)},
        "frr_all": ratio(sum(neg_hit.values()), negatives),
        "negative_records": negatives,
        "frr_by_type": {k: ratio(v, negatives) for k, v in sorted(neg_by_type.items())},
        "frr_by_detector": {
            k: ratio(v, negatives) for k, v in sorted(neg_by_detector.items())
        },
    }


def type_precision(result: dict, kind: str) -> float | None:
    """Precision over every predicted type in a family (SECRET:* or one PII type)."""
    hits = sum(n for k, n in result["predicted_hits"].items() if family(k) == kind)
    total = sum(n for k, n in result["predicted"].items() if family(k) == kind)
    return hits / total if total else None


def latency(records) -> dict:
    """Per cell (<200 chars), per KB, and a 10k-cell batch shaped like a query result (mostly clean cells)."""
    cells = [(r["text"], r["key"]) for r in records if len(r["text"]) < 200]
    for text, key in cells[:200]:
        redact(text, key=key)  # warm caches
    per_cell = []
    for text, key in cells:
        started = time.perf_counter_ns()
        redact(text, key=key)
        per_cell.append((time.perf_counter_ns() - started) / 1e3)
    per_kb = []
    for r in records:
        if len(r["text"]) >= 64:
            started = time.perf_counter_ns()
            redact(r["text"], key=r["key"])
            per_kb.append(
                (time.perf_counter_ns() - started)
                / 1e3
                / (len(r["text"].encode()) / 1024)
            )
    rng = random.Random(7)
    short = [r for r in records if len(r["text"]) < 200]
    negatives = [
        (r["text"], r["key"]) for r in short if r["category"].startswith("neg:")
    ]
    positives = [
        (r["text"], r["key"]) for r in short if r["category"].startswith("pos:")
    ]
    batch = [
        rng.choice(positives) if rng.random() < 0.05 else rng.choice(negatives)
        for _ in range(10_000)
    ]
    texts, keys = [t for t, _ in batch], [k for _, k in batch]
    runs = []
    for _ in range(5):
        started = time.perf_counter()
        redact_batch(texts, keys)
        runs.append(time.perf_counter() - started)
    best = statistics.median(runs)
    q = lambda xs, p: round(statistics.quantiles(xs, n=100)[p - 1], 1)  # noqa: E731
    return {
        "python": platform.python_version(),
        "machine": platform.machine(),
        "cell_us": {
            "p50": q(per_cell, 50),
            "p99": q(per_cell, 99),
            "max": round(max(per_cell), 1),
            "n": len(per_cell),
        },
        "per_kb_us": {"p50": q(per_kb, 50), "p99": q(per_kb, 99), "n": len(per_kb)},
        "batch_10k": {
            "seconds_median_of_5": round(best, 3),
            "cells_per_s": round(10_000 / best),
            "mb_per_s": round(sum(len(t.encode()) for t in texts) / best / 1e6, 2),
        },
    }


def table(split: str, results: dict) -> str:
    new, base, ds = (
        results["inconnu"],
        results.get("inconnu-0.1.1"),
        results["detect-secrets"],
    )
    f1 = lambda p, r: round(2 * p * r / (p + r), 3) if p and r else 0.0  # noqa: E731
    fmt = lambda x: "-" if x is None else f"{x:.3f}"  # noqa: E731
    lines = [
        f"## {split}: PII (n = gold spans)",
        "",
        "| type | n | precision | recall | F1 | covered | 0.1.1 precision | 0.1.1 recall |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for t in PII:
        p, r = type_precision(new, t), new["recall"].get(t)
        bp = type_precision(base, t) if base else None
        br = base["recall"].get(t) if base else None
        lines.append(
            f"| {t} | {new['gold'].get(t, 0)} | {fmt(p)} | {fmt(r)} | {f1(p, r):.3f} | {fmt(new['covered'].get(t))} | {fmt(bp)} | {fmt(br)} |"
        )
    if "spacy-sm-person" in results:
        sp = results["spacy-sm-person"]
        lines.append(
            f"| PERSON (spaCy en_core_web_sm, raw) | {sp['gold'].get('PERSON', 0)} | {fmt(type_precision(sp, 'PERSON'))} | {fmt(sp['recall'].get('PERSON'))} | "
            f"{f1(type_precision(sp, 'PERSON'), sp['recall'].get('PERSON')):.3f} | {fmt(sp['covered'].get('PERSON'))} | | |"
        )
    if "phone-regex-only" in results:
        ph = results["phone-regex-only"]
        lines.append(
            f"| PHONE (regex only, no phonenumbers) | {ph['gold'].get('PHONE', 0)} | {fmt(type_precision(ph, 'PHONE'))} | {fmt(ph['recall'].get('PHONE'))} | "
            f"{f1(type_precision(ph, 'PHONE'), ph['recall'].get('PHONE')):.3f} | {fmt(ph['covered'].get('PHONE'))} | | |"
        )
    lines += [
        "",
        f"## {split}: secrets by gold kind (recall = any SECRET prediction overlaps)",
        "",
        "| kind | n | recall | covered | detect-secrets recall | 0.1.1 covered |",
        "|---|---|---|---|---|---|",
    ]
    for k in sorted(k for k in new["gold"] if k not in PII):
        lines.append(
            f"| {k} | {new['gold'][k]} | {fmt(new['recall'][k])} | {fmt(new['covered'][k])} | {fmt(ds['recall'].get(k))} | "
            f"{fmt(base['covered'].get(k)) if base else '-'} |"
        )
    lines += [
        "",
        f"SECRET precision (all kinds): inconnu {fmt(type_precision(new, 'SECRET'))}, detect-secrets {fmt(type_precision(ds, 'SECRET'))}",
        "",
        "| predicted secret kind | n | precision |",
        "|---|---|---|",
    ]
    for k, n in new["predicted"].items():
        if k.startswith("SECRET"):
            lines.append(f"| {k} | {n} | {fmt(new['precision'][k])} |")
    lines += [
        "",
        "## Full-span coverage (100% of gold characters redacted; any label)",
        "",
        "| kind | full coverage |",
        "|---|---|",
    ]
    for k, value in new["fully_covered"].items():
        lines.append(f"| {k} | {fmt(value)} |")
    lines += [
        "",
        f"## {split}: false-redaction rate on negatives (share of records with any redaction)",
        "",
        "| category | inconnu | detect-secrets | 0.1.1 |",
        "|---|---|---|---|",
    ]
    for c in new["frr"]:
        lines.append(
            f"| {c} | {fmt(new['frr'][c])} | {fmt(ds['frr'].get(c))} | {fmt(base['frr'].get(c)) if base else '-'} |"
        )
    lines.append(
        f"| **all negatives** | {fmt(new['frr_all'])} | {fmt(ds['frr_all'])} | {fmt(base['frr_all']) if base else '-'} |"
    )
    lines.append("")
    lines.append(
        "inconnu FRR by detector: "
        + ", ".join(f"{k} {v:.4f}" for k, v in new["frr_by_detector"].items())
    )
    if "latency" in results:
        lat = results["latency"]
        lines += [
            "",
            f"## latency (Python {lat['python']}, {lat['machine']})",
            "",
            f"- per cell (<200 chars, n={lat['cell_us']['n']}): p50 {lat['cell_us']['p50']} µs, p99 {lat['cell_us']['p99']} µs, max {lat['cell_us']['max']} µs",
            f"- per KB (texts >= 64 chars, n={lat['per_kb_us']['n']}): p50 {lat['per_kb_us']['p50']} µs, p99 {lat['per_kb_us']['p99']} µs",
            f"- 10k-cell batch: {lat['batch_10k']['seconds_median_of_5']} s, {lat['batch_10k']['cells_per_s']} cells/s, {lat['batch_10k']['mb_per_s']} MB/s",
        ]
        if "baseline_seconds" in results:
            n = len(load(split))
            lines.append(
                "- inconnu 0.1.1 on the same records: "
                + ", ".join(
                    f"{k} {v / n * 1e3:.2f} ms/record"
                    for k, v in results["baseline_seconds"].items()
                )
            )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", action="append")
    parser.add_argument("--no-latency", action="store_true")
    args = parser.parse_args()
    for split in args.split or ["dev", "test"]:
        records = load(split)
        results = {
            "data_sha256": hashlib.sha256(
                (ROOT / "data" / f"{split}.jsonl").read_bytes()
            ).hexdigest(),
            "python": platform.python_version(),
            "inconnu_version": inconnu.__version__,
            "phonenumbers_version": phonenumbers.__version__,
            "records": len(records),
            "inconnu": score(records, predict_inconnu(records)),
            "detect-secrets": score(
                records, predict_detect_secrets(records), types={"SECRET"}
            ),
            "phone-regex-only": score(
                records, predict_phone_regex(records), types={"PHONE"}
            ),
        }
        baseline = ROOT / "data" / f"baseline-{split}.json"
        b = json.loads(baseline.read_text()) if baseline.exists() else {}
        data_sha = hashlib.sha256(
            (ROOT / "data" / f"{split}.jsonl").read_bytes()
        ).hexdigest()
        if b and b.get("data_sha256") != data_sha:
            print(
                f"{baseline} was made from other data; run make eval-baseline",
                file=sys.stderr,
            )
            b = {}
        if b:
            results["inconnu-0.1.1"] = score(
                records, [[(*p, "0.1.1") for p in ps] for ps in b["inconnu-0.1.1"]]
            )
            results["spacy-sm-person"] = score(
                records,
                [[(*p, "spacy") for p in ps] for ps in b["spacy-sm-person"]],
                types={"PERSON"},
            )
            results["baseline_seconds"] = b["seconds"]
        if not args.no_latency:
            results["latency"] = latency(records)
        out = ROOT / "results" / f"{split}.json"
        out.parent.mkdir(exist_ok=True)
        out.write_text(json.dumps(results, indent=1) + "\n")
        text = table(split, results)
        (ROOT / "results" / f"{split}.md").write_text(text + "\n")
        print(text + "\n", file=sys.stdout)


if __name__ == "__main__":
    main()
