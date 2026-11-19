"""Unknown secrets: long tokens whose characters look random for their charset.

Hex needs a secret-like key nearby: on its own it is a hash, SHA or fingerprint. Without a key nearby a random
token lands in the uncertain band (redacted unless a Scorer clears it). Thresholds come from evals/.
"""

from __future__ import annotations

import base64
import binascii
import json
import math
import re
from collections import Counter

from .credentials import CAMEL, KEYWORD, secret_key

# Base64 prefixes for '{', '[' and the four JSON whitespace bytes.
BASE64_JSON_START = r"(?:[eW][w-z0-9+/_-]|I[A-P]|C[Q-v]|D[Q-f])"
TOKEN = re.compile(
    rf"(?<![\w+/-])(?:[A-Za-z0-9+/_-]{{20,}}|{BASE64_JSON_START}[A-Za-z0-9+/_-]{{1,17}})"
    r"={0,2}(?![\w+/=-])"
)
JSON_PREFIX = re.compile(BASE64_JSON_START)
PUBLIC_JSON = frozenset(
    {b"{}", b"[]", b'{"format":"json"}', b'{"format": "json"}', b'{ "format": "json" }'}
)
MAX_JSON_LEN = 16384
UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
HEX = re.compile(r"[0-9a-fA-F]+")
LETTER_RUN = re.compile(r"[A-Z]?[a-z]{2,}|[A-Z]{2,}(?![a-z])")
CONSONANTS = re.compile(r"[^aeiouy]{4,}")
# Encoded data that is not a secret: digests, data URIs, SRI hashes, public keys.
DIGEST = re.compile(r"(?i)(?:sha(?:1|224|256|384|512)|md5)[-:=]")
NOT_SECRET_BEFORE = re.compile(
    r"(?i)(?:base64,|(?:sha(?:1|224|256|384|512)|md5)[-:=]|ssh-(?:rsa|ed25519|dss) |ecdsa-sha2-nistp\d+ )$"
)
NEAR_SECRET = re.compile(
    rf"(?i)(?:{KEYWORD}|api[ _-]?key|access[ _-]?key|private[ _-]?key)s?(?:\W{{1,4}}(?:is|was|of|for)\b)?\W{{0,8}}$"
)
# Keys that name identifiers and digests: random-looking values under them are not secrets (from the eval negatives).
ID_KEY = re.compile(
    r"(?i)(?:^|[^a-z])(?:id|ids|uuid|guid|hash|digest|checksum|etag|fingerprint|sha\d*|version|trace|span)$"
)
OBJECT_PREFIXES = {
    "payment_intent": "pi_",
    "customer": "cus_",
    "request": "req_",
    "event": "evt_",
}
KEY_BEFORE = re.compile(r"([A-Za-z_][\w.-]{0,63})[\"']?\s*(?::=|=>|[:=])\s*[\"'\x60]?$")
TOKEN_CELL = re.compile(
    r"[A-Za-z0-9+/_-]{1,200}={0,2}(?:\.[A-Za-z0-9+/_-]{1,200}={0,2}){0,4}"
)
MAX_LEN = 200  # longer unlabeled tokens are encoded blobs, not credentials
MIN_RANDOMNESS, MAX_WORDINESS, MIN_MIXING = 0.83, 0.45, 0.45


def shannon(value: str) -> float:
    n = len(value)
    return -sum(c / n * math.log2(c / n) for c in Counter(value).values())


def _random_segment(token: str, text: str, randomness: float, wordiness: float) -> bool:
    """Relax the wordiness gate only for short segments in token-shaped cells."""
    token = token.rstrip("=")
    if (
        not 22 <= len(token) <= 54
        or randomness < 0.86
        or wordiness > 0.70
        or len(text) > 1024
        or not TOKEN_CELL.fullmatch(text.strip())
    ):
        return False
    kinds = [
        "u" if c.isupper() else "l" if c.islower() else "d" if c.isdigit() else "s"
        for c in token
    ]
    return sum(a != b for a, b in zip(kinds, kinds[1:])) >= 0.4 * (len(token) - 1)


def features(token: str) -> tuple[float, float, float]:
    """randomness: entropy over the most a token of this length and charset can have.
    wordiness: share of characters in pronounceable letter runs (identifiers, paths).
    mixing: how often adjacent characters switch class (upper, lower, digit, symbol)."""
    alphabet = 16 if HEX.fullmatch(token) else 64 if re.search(r"[+/_-]", token) else 62
    randomness = shannon(token) / math.log2(min(len(token), alphabet))
    words = 0
    for run in LETTER_RUN.findall(token):
        low = run.lower()
        if (
            len(low) >= 3
            and sum(c in "aeiouy" for c in low) >= 0.2 * len(low)
            and not CONSONANTS.search(low)
        ):
            words += len(run)
    # Symbols separate segments (x86_64, cp314-win_arm64); only switches inside a segment count.
    kinds = [
        "u" if c.isupper() else "l" if c.islower() else "d" if c.isdigit() else "s"
        for c in token
    ]
    mixing = sum(a != b and "s" not in (a, b) for a, b in zip(kinds, kinds[1:])) / (
        len(token) - 1
    )
    return randomness, words / len(token), mixing


def _encoded_text(token: str) -> bool:
    """Base64 of a sentence (test fixtures, encoded messages) rather than of random bytes."""
    try:
        raw = base64.b64decode(token + "=" * (-len(token) % 4), validate=True)
        text = raw.decode("ascii")
    except (binascii.Error, ValueError):
        return False
    return " " in text and sum(c.isalpha() or c in " .,'" for c in text) >= 0.9 * len(
        text
    )


def _json_envelope(token: str) -> bool | None:
    """Return whether encoded object/array content is private, or None for other tokens."""
    if not JSON_PREFIX.match(token):
        return None
    try:
        prefix = base64.b64decode(
            token[:24] + "=" * (-len(token) % 4 if len(token) < 24 else 0),
            altchars=b"-_",
            validate=True,
        )
        prefix = prefix.lstrip(b" \t\r\n")
        if prefix and not prefix.startswith((b"{", b"[")):
            return None
        if len(token) > MAX_JSON_LEN:
            return True
        raw = base64.b64decode(
            token + "=" * (-len(token) % 4), altchars=b"-_", validate=True
        )
        if raw in PUBLIC_JSON:
            canonical = base64.b64encode(raw).decode()
            return token not in (canonical, canonical.rstrip("="))
        if isinstance(
            json.loads(raw.decode("utf-8"), parse_int=str, parse_float=str),
            (dict, list),
        ):
            return True
    except RecursionError:
        return True
    except (ValueError, binascii.Error):
        pass
    return None


def confidence(token: str, text: str, start: int, key: str | None) -> float:
    if not re.search(r"[A-Za-z]", token) or UUID.search(token) or DIGEST.match(token):
        return 0.0
    letters_only = not re.search(
        r"\d", token
    )  # judged by stricter word and mixing checks below
    near = secret_key(key) or bool(NEAR_SECRET.search(text, max(0, start - 48), start))
    if not near and (HEX.fullmatch(token) or len(token) > MAX_LEN):
        return 0.0
    named = KEY_BEFORE.search(text, max(0, start - 70), start)
    object_key = False
    for name in (key, named and named.group(1)):
        if not near and name:
            normalized = CAMEL.sub("_", name).lower().rsplit(".", 1)[-1]
            prefix = OBJECT_PREFIXES.get(normalized)
            object_key |= prefix is not None
            if (
                prefix
                and token.startswith(prefix)
                and re.fullmatch(r"[A-Za-z0-9]{12,}", token[len(prefix) :])
            ):
                return 0.0
    if not near and any(
        k and ID_KEY.search(CAMEL.sub("_", k)) for k in (key, named and named.group(1))
    ):
        return 0.0
    if NOT_SECRET_BEFORE.search(text, max(0, start - 24), start):
        return 0.0
    randomness, wordiness, mixing = features(token)
    if HEX.fullmatch(
        token
    ):  # hex is never an identifier; next to a secret-like key it is the secret
        return 0.85 if randomness >= 0.8 else 0.0
    if (
        randomness < MIN_RANDOMNESS
        or wordiness > (0.2 if letters_only else MAX_WORDINESS)
        or mixing < (0.5 if letters_only else MIN_MIXING)
    ):
        if (
            not (near or named or object_key)
            and mixing
            >= 0.25  # separators alone are weak evidence, especially in build labels
            and _random_segment(token, text, randomness, wordiness)
            and not _encoded_text(token)
        ):
            return 0.6  # the relaxed path stays in the scorer's uncertain band
        return 0.0
    if _encoded_text(token):
        return 0.0
    score = 0.6 + 0.3 * min((randomness - MIN_RANDOMNESS) / 0.1, 1.0)
    return min(score + (0.25 if near else 0.0), 0.95)


def find(text: str, key: str | None):
    """Yield (start, end, type, confidence, detector) candidates."""
    for m in TOKEN.finditer(text):
        token = m.group()
        private = _json_envelope(token)
        if private:
            yield m.start(), m.end(), "SECRET:entropy", 0.95, "entropy"
            continue
        if len(token) < 20 or (
            private is False
            and not secret_key(key)
            and not NEAR_SECRET.search(text, max(0, m.start() - 48), m.start())
        ):
            continue
        conf = confidence(token, text, m.start(), key)
        if conf:
            yield m.start(), m.end(), "SECRET:entropy", conf, "entropy"
