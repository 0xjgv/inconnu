"""Apply sensitive column context to values in Markdown pipe tables."""

from __future__ import annotations

import re

from . import credentials, person, pii

PIPE = re.compile(r"\\[\\|]|(?P<separator>\|)")
DIVIDER = re.compile(r":?-+:?")
HEADER_SPACES = re.compile(r"[ -]+")


def _cells(line: str) -> list[tuple[int, int]]:
    start, end = len(line) - len(line.lstrip()), len(line.rstrip())
    pipes = [m.start() for m in PIPE.finditer(line) if m.lastgroup]
    if not pipes:
        return []
    if pipes[0] != start:
        pipes.insert(0, start - 1)
    if pipes[-1] != end - 1:
        pipes.append(end)
    return [(left + 1, right) for left, right in zip(pipes, pipes[1:])]


def find(text: str, _key: str | None):
    """Yield additional spans using the detector for each labeled column."""
    headers = []
    columns = []
    offset = 0
    for line in text.splitlines(keepends=True):
        cells = _cells(line)
        if not cells:
            headers = []
            columns = []
        elif columns:
            for (start, end), (key, detector) in zip(cells, columns):
                value = line[start:end]
                if detector and not credentials.BRACKET_PLACEHOLDER.fullmatch(
                    value.strip()
                ):
                    for a, b, kind, confidence, source in detector(value, key):
                        yield (
                            offset + start + a,
                            offset + start + b,
                            kind,
                            confidence,
                            source,
                        )
        elif len(headers) == len(cells) and all(
            DIVIDER.fullmatch(line[start:end].strip()) for start, end in cells
        ):
            for key in headers:
                if credentials.secret_key(key):
                    detector = credentials.find
                elif person.NAME_KEY.fullmatch(key):
                    detector = person.find
                elif pii.PHONE_FIELD.fullmatch(key):
                    detector = pii.find
                else:
                    detector = None
                columns.append((key, detector))
        else:
            headers = [
                HEADER_SPACES.sub("_", line[start:end].strip().strip("`"))
                for start, end in cells
            ]
        offset += len(line)
