"""Optional second opinion for uncertain candidates, after s1r's System One provider chain.

Only a masked description leaves the machine: type, length, character classes, entropy and the name of the
key or column. Any error, timeout, missing key or budget overrun answers "redact" (fail closed).
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.request

from .entropy import shannon

PROVIDERS = {
    "typesafe": ("https://api.typesafe.ai/v1/systemone", "TYPESAFE_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/systemone", "OPENROUTER_API_KEY"),
    "respan": ("https://api.respan.ai/api/v1/scores", "RESPAN_API_KEY"),
}
CHAIN = (
    ("typesafe", "jev-1.13.0"),
    ("openrouter", "typesafe/jev-1.13"),
    ("respan", "span-01-free"),
)
TIMEOUT_S = 8
QUESTION = (
    "The withheld value is sensitive and must be redacted: a password, API key, token, private key or other "
    "credential, or personal data about a person. Answer no only if it is clearly a harmless identifier, hash, "
    "code symbol, placeholder or configuration value."
)
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]{0,63}")
KEY_BEFORE = re.compile(r"([A-Za-z_][\w.-]{0,63})[\"']?\s*(?::=|=>|[:=])\s*[\"'\x60]?$")


def mask(value: str) -> str:
    return re.sub(r"[a-z]", "a", re.sub(r"[A-Z]", "A", re.sub(r"\d", "9", value)))


def describe(text: str, start: int, end: int, kind: str, key: str | None) -> str:
    """A description of text[start:end] that contains no character of the value itself."""
    value = text[start:end]
    classes = [
        name
        for name, pattern in (
            ("upper", "[A-Z]"),
            ("lower", "[a-z]"),
            ("digit", r"\d"),
            ("symbol", r"[^A-Za-z\d]"),
        )
        if re.search(pattern, value)
    ]
    lines = [
        "A redaction filter found a candidate in a database query result. The value itself is withheld.",
        f"Detector type: {kind}",
        f"Length: {len(value)}",
        f"Character classes: {', '.join(classes)}",
        f"Shannon entropy: {shannon(value):.2f} bits per character (maximum {math.log2(max(len(value), 2)):.2f})",
    ]
    if kind.startswith("SECRET"):
        lines.append(
            f"First characters, masked (A upper, a lower, 9 digit): {mask(value[:4])}"
        )
    else:
        lines.append(f"Shape (A upper, a lower, 9 digit): {mask(value)}")
    named = KEY_BEFORE.search(text, max(0, start - 80), start)
    for label, name in (
        ("Key name in the text", named and named.group(1)),
        ("Column or JSON key", key),
    ):
        if name and IDENTIFIER.fullmatch(name):
            lines.append(f"{label}: {name}")
    return "\n".join(lines)


class Scorer:
    """Decide uncertain candidates with a System One noul question; off unless passed to redact()."""

    def __init__(
        self,
        threshold: float = 0.5,
        budget_s: float = 8.0,
        max_calls: int = 32,
        chain=CHAIN,
    ):
        self.threshold, self.budget_s, self.max_calls, self.chain = (
            threshold,
            budget_s,
            max_calls,
            chain,
        )
        self.cache: dict[str, bool] = {}
        self.calls = self.failures = 0

    def keep(self, descriptions: list[str]) -> list[bool]:
        """True where the candidate may stay unredacted. Never raises."""
        deadline = time.monotonic() + self.budget_s
        for description in dict.fromkeys(descriptions):
            if description in self.cache:
                continue
            if self.calls >= self.max_calls or time.monotonic() >= deadline:
                break
            self.calls += 1
            try:
                self.cache[description] = (
                    self._probability(description, deadline) < self.threshold
                )
            except Exception:  # noqa: BLE001 fail closed on anything
                self.failures += 1
                self.cache[description] = False
        return [self.cache.get(d, False) for d in descriptions]

    def _probability(self, description: str, deadline: float) -> float:
        for provider, model in self.chain:
            url, key_name = PROVIDERS[provider]
            key = os.environ.get(key_name, "").strip()
            timeout = min(TIMEOUT_S, deadline - time.monotonic())
            if not key or timeout <= 0:
                continue
            try:
                return _ask(url, key, provider, model, description, timeout)
            except Exception:  # noqa: BLE001, S112 try the next provider; the caller fails closed
                continue
        raise RuntimeError("no scoring provider answered")


def _ask(
    url: str, key: str, provider: str, model: str, description: str, timeout: float
) -> float:
    if provider == "respan":
        body = {
            "model": model,
            "behaviors": [{"id": "sensitive", "definition": QUESTION}],
            "span": {
                "input": [{"role": "user", "content": description}],
                "output": {"role": "assistant", "content": "Noted."},
            },
        }
    else:
        body = {
            "model": model,
            "state": description,
            "questions": {"sensitive": {"type": "noul", "instructions": QUESTION}},
        }
    request = urllib.request.Request(  # noqa: S310 fixed https URLs
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 fixed https URLs
        data = json.loads(response.read())
    if provider == "respan":
        value = next(r["p_present"] for r in data["results"] if r["id"] == "sensitive")
    else:
        answer = data["answers"]["sensitive"]
        if answer["type"] != "noul":
            raise ValueError("expected a noul answer")
        value = answer["noul"]
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise ValueError("score must be a probability")
    return value
