"""redact(): run every detector, keep the most confident non-overlapping spans, replace them with typed placeholders."""

from __future__ import annotations

from . import credentials, entropy, person, pii
from .scorer import Scorer, describe

# Thresholds come from evals/: below LOW a candidate is dropped, at or above HIGH it is redacted,
# and in between it is redacted unless a Scorer says it may stay (fail closed).
LOW, HIGH = 0.5, 0.8
DETECTORS = (pii.find, credentials.find, person.find, entropy.find)
MIN_LENGTH = 5  # shorter unkeyed cells cannot hold any detected type ("Dr Li" is 5)


def _spans(text: str, key: str | None) -> list[tuple]:
    if len(text) < MIN_LENGTH and not key:
        return []
    candidates = [c for find in DETECTORS for c in find(text, key) if c[3] >= LOW]
    kept: list[tuple] = []
    for c in sorted(candidates, key=lambda c: (-c[3], c[0] - c[1], c[0])):
        overlapping = [k for k in kept if c[0] < k[1] and k[0] < c[1]]
        if not overlapping:
            kept.append(c)
        elif not all(k[0] <= c[0] and c[1] <= k[1] for k in overlapping):
            # c sticks out of a more confident span: redact the union, so no part of either leaks.
            group = [*overlapping, c]
            longest = max(group, key=lambda s: s[1] - s[0])
            start, end = min(s[0] for s in group), max(s[1] for s in group)
            kept = [k for k in kept if k not in overlapping]
            kept.append((start, end, longest[2], max(s[3] for s in group), longest[4]))
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
    keys = [None] * len(cells) if keys is None else keys
    found = [_spans(text, key) for text, key in zip(cells, keys, strict=True)]
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
    """Redact every string, integer and dict key in a JSON value; dict keys and column names give context.

    A dict with "rows" (lists) and "cols" or "columns" (names or {"name": ...}) gives each row cell its column name.
    Two keys that redact to the same placeholder become "[EMAIL]" and "[EMAIL] (2)".
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
                    value = [
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
                    value = walk(v, k if isinstance(k, str) else key, visit)
                name = base = visit(k, None) if isinstance(k, str) else k
                n = 1
                while name in out:
                    n += 1
                    name = f"{base} ({n})"
                out[name] = value
            return out
        if isinstance(node, list):
            return [walk(v, key, visit) for v in node]
        if isinstance(node, (str, int, float)) and not isinstance(node, bool):
            return visit(node, key)
        return node

    def text(node) -> str:
        # An integral float (4155552671.0 from a database driver) is checked as the integer it holds.
        return (
            str(int(node))
            if isinstance(node, float) and node.is_integer()
            else str(node)
        )

    def collect(node, key):
        cells.append(text(node))
        keys.append(key)
        return node

    walk(data, None, collect)
    results = iter(redact_batch(cells, keys, scorer))

    def replace(node, key):
        redacted, findings = next(results)
        return redacted if findings or isinstance(node, str) else node

    return walk(data, None, replace)
