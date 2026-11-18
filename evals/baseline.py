"""Predictions from inconnu 0.1.1 (spaCy en_core_web_sm) and from raw spaCy PERSON entities, for evals/run.py.

Runs in its own venv (make eval-baseline): python evals/baseline.py writes evals/data/baseline-{split}.json.
0.1.1 returns only redacted text, so spans are recovered by aligning the unchanged text around each [LABEL].
"""

import hashlib
import json
import re
import sys
import time
from pathlib import Path

import spacy

from inconnu import Inconnu, __version__

DATA = Path(__file__).parent / "data"
LABELS = {"PHONE_NUMBER": "PHONE", "CREDIT_CARD": "CARD", "PER": "PERSON"}


def spans(original: str, redacted: str) -> list:
    """Align the unchanged text around each placeholder; every placeholder stands for at least one character."""
    pieces = re.split(r"\[([A-Z_]+)\]", redacted)
    labels, literals = pieces[1::2], pieces[0::2]
    pattern = "(.+?)".join(re.escape(lit) for lit in literals)
    m = re.fullmatch(pattern, original, re.DOTALL)
    # No alignment only if 0.1.1 altered unredacted text; count that as no prediction.
    if m is None:
        return []
    return [
        [m.start(g), m.end(g), LABELS.get(label, label)]
        for g, label in enumerate(labels, 1)
    ]


def main():
    assert __version__ == "0.1.1", __version__
    redactor = Inconnu(language="en")
    nlp = spacy.load("en_core_web_sm")
    for split in sys.argv[1:] or ["dev", "test"]:
        raw = (DATA / f"{split}.jsonl").read_bytes()
        records = [json.loads(line) for line in raw.splitlines()]
        result = {
            "data_sha256": hashlib.sha256(raw).hexdigest(),
            "inconnu-0.1.1": [],
            "spacy-sm-person": [],
            "seconds": {},
        }
        started = time.perf_counter()
        for r in records:
            result["inconnu-0.1.1"].append(spans(r["text"], redactor.redact(r["text"])))
        result["seconds"]["inconnu-0.1.1"] = time.perf_counter() - started
        started = time.perf_counter()
        for r in records:
            doc = nlp(r["text"])
            result["spacy-sm-person"].append(
                [
                    [e.start_char, e.end_char, "PERSON"]
                    for e in doc.ents
                    if e.label_ == "PERSON"
                ]
            )
        result["seconds"]["spacy-sm-person"] = time.perf_counter() - started
        (DATA / f"baseline-{split}.json").write_text(json.dumps(result))
        print(split, {k: round(v, 1) for k, v in result["seconds"].items()})


if __name__ == "__main__":
    main()
