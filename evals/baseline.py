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
    pieces = re.split(r"\[([A-Z_]+)\]", redacted)
    out, pos = [], len(pieces[0])
    for i in range(1, len(pieces), 2):
        label, literal = pieces[i], pieces[i + 1]
        if i + 2 < len(pieces):
            end = original.find(literal, pos + 1) if literal else pos + 1
        else:
            end = len(original) - len(literal)
        if end <= pos:
            end = pos + 1
        out.append([pos, end, LABELS.get(label, label)])
        pos = end + len(literal)
    return out


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
