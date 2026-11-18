"""redact(): run every detector, keep the most confident non-overlapping spans, replace them with typed placeholders."""

from __future__ import annotations

from . import credentials, entropy, person, pii
from .scorer import Scorer, describe

# Thresholds come from evals/: below LOW a candidate is dropped, at or above HIGH it is redacted,
# and in between it is redacted unless a Scorer says it may stay (fail closed).
LOW, HIGH = 0.5, 0.8
DETECTORS = (pii.find, credentials.find, person.find, entropy.find)
MIN_LENGTH = 6  # shorter cells cannot hold any detected type


def _spans(text: str, key: str | None) -> list[tuple]:
    if len(text) < MIN_LENGTH:
        return []
    candidates = [c for find in DETECTORS for c in find(text, key) if c[3] >= LOW]
    kept: list[tuple] = []
    for c in sorted(candidates, key=lambda c: (-c[3], c[0] - c[1], c[0])):
        if all(c[1] <= k[0] or c[0] >= k[1] for k in kept):
            kept.append(c)
    return sorted(kept)


def _apply(text: str, spans: list[tuple]) -> str:
    out, last = [], 0
    for start, end, kind, _, _ in spans:
        out += [text[last:start], f"[{kind}]"]
        last = end
    out.append(text[last:])
    return "".join(out)


def redact_batch(
    cells: list[str], keys: list[str | None] | None = None, scorer: Scorer | None = None
) -> list[tuple[str, list[dict]]]:
    """Redact many short texts, such as the cells of a query result; keys are their column names.

    Returns one (redacted_text, findings) per cell. Findings carry type, start, end, confidence and
    detector, never the value.
    """
    keys = keys or [None] * len(cells)
    found = [_spans(text, key) for text, key in zip(cells, keys)]
    if scorer is not None:
        band = [
            (i, j)
            for i, spans in enumerate(found)
            for j, s in enumerate(spans)
            if s[3] < HIGH
        ]
        if band:
            keep = scorer.keep(
                [describe(cells[i], *found[i][j][:3], keys[i]) for i, j in band]
            )
            cleared = {b for b, k in zip(band, keep) if k}
            found = [
                [s for j, s in enumerate(spans) if (i, j) not in cleared]
                for i, spans in enumerate(found)
            ]
    return [
        (
            _apply(text, spans),
            [
                {
                    "type": k,
                    "start": s,
                    "end": e,
                    "confidence": round(c, 2),
                    "detector": d,
                }
                for s, e, k, c, d in spans
            ],
        )
        for text, spans in zip(cells, found)
    ]


def redact(
    text: str, key: str | None = None, scorer: Scorer | None = None
) -> tuple[str, list[dict]]:
    """Return (redacted_text, findings). key is the column or JSON key the text came from, if any."""
    return redact_batch([text], [key], scorer)[0]


def redact_json(data, scorer: Scorer | None = None):
    """Redact every string (and integer) in a JSON value, using dict keys and result column names as context.

    A dict with "rows" (lists) and "cols" or "columns" (names or {"name": ...}) gives each row cell its column name.
    """
    cells: list[str] = []
    keys: list[str | None] = []

    def columns(node: dict) -> list | None:
        cols = node.get("cols", node.get("columns"))
        if isinstance(cols, list) and isinstance(node.get("rows"), list):
            return [c.get("name") if isinstance(c, dict) else c for c in cols]
        return None

    def walk(node, key, visit):
        if isinstance(node, dict):
            names = columns(node)
            out = {}
            for k, v in node.items():
                if k == "rows" and names:
                    out[k] = [
                        [
                            walk(cell, name if isinstance(name, str) else key, visit)
                            for cell, name in zip(row, names)
                        ]
                        + [walk(cell, key, visit) for cell in row[len(names) :]]
                        if isinstance(row, list)
                        else walk(row, key, visit)
                        for row in v
                    ]
                else:
                    out[k] = walk(v, k if isinstance(k, str) else key, visit)
            return out
        if isinstance(node, list):
            return [walk(v, key, visit) for v in node]
        if isinstance(node, str) or (
            isinstance(node, int) and not isinstance(node, bool)
        ):
            return visit(node, key)
        return node

    def collect(node, key):
        cells.append(str(node))
        keys.append(key)
        return node

    walk(data, None, collect)
    results = iter(redact_batch(cells, keys, scorer))

    def replace(node, key):
        redacted, findings = next(results)
        return redacted if findings or isinstance(node, str) else node

    return walk(data, None, replace)
