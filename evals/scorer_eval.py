"""Live check of the optional Scorer on the dev split's uncertain band, with a hard cap on calls.

Reads TYPESAFE_API_KEY / OPENROUTER_API_KEY / RESPAN_API_KEY from the environment or ~/.config/s1r/.env.
Before any call it asserts that no description contains its candidate's value (or any 6-character piece of it).

Usage: python evals/scorer_eval.py [--max-calls 120]   (writes evals/results/scorer.json)
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import time
from pathlib import Path

from run import family, load

from inconnu.core import HIGH, _spans
from inconnu.scorer import Scorer, describe

ROOT = Path(__file__).parent
KEYS = ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "RESPAN_API_KEY")


def load_keys():
    env = (
        Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        / "s1r"
        / ".env"
    )
    if env.exists():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() in KEYS and not os.environ.get(name.strip()):
                os.environ[name.strip()] = value.strip().strip("\"'")


def finite_seconds(value: str) -> float:
    seconds = float(value)
    if not math.isfinite(seconds) or seconds < 0:
        raise argparse.ArgumentTypeError(
            "budget must be a finite, non-negative number of seconds"
        )
    return seconds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-calls", type=lambda v: max(0, int(v)), default=120)
    parser.add_argument(
        "--budget-s",
        type=finite_seconds,
        default=600,
        help="wall clock for the whole run",
    )
    args = parser.parse_args()
    load_keys()
    band = {}  # description -> [true positives, false positives, type]
    for r in load("dev"):
        for s in _spans(r["text"], r["key"]):
            if s[3] >= HIGH:
                continue
            value = r["text"][s[0] : s[1]]
            description = describe(r["text"], s[0], s[1], s[2], r["key"])
            pieces = (
                {value[i : i + 6] for i in range(max(len(value) - 5, 1))}
                if len(value) >= 6
                else {value}
            )
            if any(p in description for p in pieces if len(p) >= 4):
                raise SystemExit(
                    "a raw candidate value reached a payload; no call made"
                )
            tp = any(
                s[0] < g["end"] and g["start"] < s[1] and family(s[2]) == g["type"]
                for g in r["spans"]
            )
            entry = band.setdefault(description, [0, 0, s[2]])
            entry[0 if tp else 1] += 1
    # Every description with a false positive first (what the scorer could clear), then true positives
    # round-robin across types, so each type's leak risk is measured.
    fps = sorted(d for d in band if band[d][1])
    by_type: dict[str, list[str]] = {}
    for d in sorted(d for d in band if not band[d][1]):
        by_type.setdefault(band[d][2], []).append(d)
    tps = [d for group in itertools.zip_longest(*by_type.values()) for d in group if d]
    order = (fps + tps)[: args.max_calls]
    # One provider only, so --max-calls caps provider requests, not descriptions; one shared deadline.
    scorer = Scorer(chain=Scorer().chain[:1])
    deadline = time.monotonic() + args.budget_s
    scored, started = [], time.monotonic()
    for description in order:
        try:
            p = scorer._probability(description, deadline)
        except Exception as exc:  # noqa: BLE001 counted as a fail-closed answer
            p = None
            print("failed:", type(exc).__name__)
        tp, fp, kind = band[description]
        scored.append({"type": kind, "tp": tp, "fp": fp, "p": p})
    elapsed = time.monotonic() - started
    summary = {
        "descriptions_in_band": len(band),
        "scored": len(scored),
        "seconds_per_call": round(elapsed / max(len(scored), 1), 2),
        "failed_calls": sum(s["p"] is None for s in scored),
        "by_threshold": {},
    }
    for threshold in (0.3, 0.5, 0.7):
        keep = [s for s in scored if s["p"] is not None and s["p"] < threshold]
        summary["by_threshold"][threshold] = {
            "true_positives_cleared (leaks)": sum(s["tp"] for s in keep),
            "false_positives_cleared": sum(s["fp"] for s in keep),
            "true_positives_scored": sum(s["tp"] for s in scored),
            "false_positives_scored": sum(s["fp"] for s in scored),
        }
    out = {
        "summary": summary,
        "per_description": [{k: v for k, v in s.items()} for s in scored],
    }
    (ROOT / "results" / "scorer.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
