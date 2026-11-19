"""Secret rules: provider token formats, credential blocks, and key=value pairs.

Formats follow the public gitleaks rule set (https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml)
and the providers' own token documentation.
"""

from __future__ import annotations

import base64
import binascii
import json
import re

# (kind, pattern, confidence, literals). The secret is group "s" when present, else the whole match.
# A rule's regex only runs when one of its literals occurs in the text: most cells hold none.
RULES = [
    (
        "aws-access-key",
        r"\b(?:A3T[A-Z0-9]|AKIA|ASIA|ABIA|ACCA)[A-Z2-7]{16}\b",
        0.97,
        ("AKIA", "ASIA", "ABIA", "ACCA", "A3T"),
    ),
    (
        "github-token",
        r"\b(?:gh[pousr]_[0-9A-Za-z]{36}|github_pat_[0-9A-Za-z_]{82})\b",
        0.99,
        ("ghp_", "gho_", "ghu_", "ghs_", "ghr_", "github_pat_"),
    ),
    (
        "gitlab-token",
        r"\bgl(?:pat|dt|ptt|rt|cbt)-[0-9A-Za-z_-]{20,}",
        0.99,
        ("glpat-", "gldt-", "glptt-", "glrt-", "glcbt-"),
    ),
    (
        "anthropic-key",
        r"\bsk-ant-(?:api|admin|oat)\d{2}-[A-Za-z0-9_-]{32,}",
        0.99,
        ("sk-ant-",),
    ),
    (
        "openai-key",
        r"\bsk-(?:(?:proj|svcacct|admin)-[A-Za-z0-9_-]{40,}|[A-Za-z0-9]{20}T3BlbkFJ[A-Za-z0-9]{20}|[A-Za-z0-9]{48})\b",
        0.97,
        ("sk-",),
    ),
    ("slack-token", r"\bxox[abposr]-(?:\d+-)+[0-9A-Za-z-]{10,}", 0.97, ("xox",)),
    (
        "slack-webhook",
        r"https://hooks\.slack\.com/(?:services|workflows|triggers)/[A-Za-z0-9+/_-]{20,}",
        0.99,
        ("hooks.slack.com",),
    ),
    (
        "discord-webhook",
        r"https://(?:\w+\.)?discord(?:app)?\.com/api/webhooks/\d+/[\w-]{20,}",
        0.99,
        ("discord",),
    ),
    (
        "stripe-key",
        r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{20,}\b",
        0.99,
        ("_live_", "_test_"),
    ),
    ("google-api-key", r"\bAIza[0-9A-Za-z_-]{35}(?![\w-])", 0.95, ("AIza",)),
    ("npm-token", r"\bnpm_[A-Za-z0-9]{36}\b", 0.97, ("npm_",)),
    ("pypi-token", r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{50,}", 0.99, ("pypi-",)),
    ("sendgrid-key", r"\bSG\.[\w-]{22}\.[\w-]{43}\b", 0.99, ("SG.",)),
    (
        "jwt",
        r"(?<![\w.-])[A-Za-z0-9_-]{2,4096}\.[A-Za-z0-9_-]{2,16384}\.[A-Za-z0-9_-]{0,2048}(?![\w-])",
        0.95,
        (".",),
    ),
    (
        "password-hash",
        r"\$2[abxy]?\$\d{2}\$[./A-Za-z0-9]{53}|\$argon2(?:id|i|d)\$[^\s\"']{20,}|\b(?:pbkdf2_sha(?:1|256)|bcrypt_sha256|scrypt)\$[^\s\"']{20,}",
        0.95,
        ("$2", "$argon2", "pbkdf2_", "bcrypt_", "scrypt$"),
    ),
    (
        "url-password",
        r"\b[A-Za-z][A-Za-z0-9+.-]{1,20}://[^\s:/@?#]{1,64}:(?P<s>\S{1,128})@(?:[\w.-]+|\[[0-9A-Fa-f:.]+\])",
        0.97,
        ("://",),
    ),
    ("bearer", r"(?i:\bbearer)\s+(?P<s>[A-Za-z0-9._~+/-]{16,}=*)", 0.9, ("earer",)),
    (
        "basic-auth",
        r"(?i:\bbasic)\s+(?P<s>[A-Za-z0-9+/]{12,}={0,2})(?![\w+/=])",
        0.85,
        ("Basic",),
    ),
]
RULES = [
    (kind, re.compile(pattern), conf, tuple(lit.lower() for lit in literals))
    for kind, pattern, conf, literals in RULES
]
PEM_BEGIN = re.compile(r"-----BEGIN[ A-Z0-9_-]{0,100}PRIVATE KEY(?: BLOCK)?-----")
PEM_END = re.compile(r"-----END[ A-Z0-9_-]{0,100}PRIVATE KEY(?: BLOCK)?-----")
URL_PASSWORD = next(pattern for kind, pattern, *_ in RULES if kind == "url-password")
KEYWORD_LITERALS = (
    "pass",
    "pwd",
    "secret",
    "token",
    "key",
    "credential",
    "session",
    "cookie",
    "signature",
)

# Key names whose values are secrets. The key must end with the keyword: token_count and passwords_match do not.
KEYWORD = (
    r"(?:passw(?:or)?d|passwd|pwd|pass|secret|token|api[_-]?key|apikey|access[_-]?key|secret[_-]?key|private[_-]?key"
    r"|account[_-]?key|signing[_-]?key|encryption[_-]?key|master[_-]?key|auth[_-]?key|client[_-]?secret|credentials?"
    r"|session[_-]?(?:id|key)|cookie|signature)"
)
SECRET_KEY = re.compile(
    rf"(?:^|[^a-z0-9]){KEYWORD}$"
)  # matched against a snake_cased, lowercased key
CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
KEY_VALUE = re.compile(
    rf"(?<![A-Za-z0-9])(?P<key>(?:[\w.-]{{0,48}}?(?:[_.-]|(?<=[a-z0-9])(?=[A-Z])))?(?i:{KEYWORD}))(?![\w-])[\"']?\s*(?::=|=>|=|:(?=[\s\"'\x60]))\s*"
    r"(?:\"(?P<dq>(?:[^\"\\\n]|\\.){1,4096})\"|'(?P<sq>(?:[^'\\\n]|\\.){1,4096})'|\x60(?P<bq>[^\x60\n]{1,4096})\x60|(?P<bare>(?:[^\s\"'\x60,;)}\]<>]|[,;)}\]](?=[^\s\"'\x60,;)}\]])){1,256}))"
)
PLACEHOLDER = re.compile(
    r"(?i)^(?:|none|null|nil|undefined|true|false|str|string|int|bool|bytes|any|optional\[.*|secret|password|token|"
    r"changeme|redacted|hidden|example|test|xxx+|\*+|\.{3}|<[^>]*>|\[[^\]]*\]|\$\{[^}]*\}?|\{\{.*\}\}|%\(?\w*\)?s|\$\w+)$"
)
CODE_VALUE = re.compile(
    r"\w\(|\w\[|:$|^(?:os|process|self|this|config|settings|env|request|req|ctx|params|args|kwargs|cls)\.|^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$"
)


def secret_key(key: str | None) -> bool:
    return (
        bool(key)
        and len(key) <= 64
        and bool(SECRET_KEY.search(CAMEL.sub("_", key).lower()))
    )


def value_confidence(value: str, quoted: bool) -> float:
    """How likely the value of a secret-named key is a real secret rather than code or a placeholder."""
    value = value.strip()
    if PLACEHOLDER.match(value):
        return 0.0
    if quoted:
        if len(value) < 4:
            return 0.5  # a short literal under a secret name (a PIN, "abc"): uncertain
        return 0.9 if len(value) >= 8 or not value.isalpha() else 0.7
    if CODE_VALUE.search(value):
        return 0.0  # os.environ[...], get_secret(), settings.TOKEN
    if value.isdigit():
        return 0.6 if len(value) >= 6 else 0.0
    if re.fullmatch(r"[A-Za-z_]+", value):
        if secret_key(value):
            return 0.0  # passwd = passwd + ...: the variable itself, not a literal
        return 0.5  # a bare word (PASSWORD=hunter, id-token: write, password=access): uncertain, redacted unless a Scorer clears it
    return 0.9 if len(value) >= 4 else 0.5


def _private_keys(text: str):
    """PEM private key blocks, any size, in one pass. A BEGIN with no END redacts to the end of the text."""
    pos = 0
    while (begin := PEM_BEGIN.search(text, pos)) is not None:
        end = PEM_END.search(text, begin.end())
        if end is None:
            yield begin.start(), len(text)
            return
        yield begin.start(), end.end()
        pos = end.end()


def _jwt(value: str) -> bool:
    """Recognize JSON claims, including whitespace and short payloads; no signature verification."""
    header, payload, signature = value.split(".")
    try:
        decoded = [
            json.loads(
                base64.b64decode(
                    part + "=" * (-len(part) % 4), altchars=b"-_", validate=True
                )
            )
            for part in (header, payload)
        ]
    except (ValueError, binascii.Error, UnicodeDecodeError, RecursionError):
        return False
    head, claims = decoded
    return (
        isinstance(head, dict)
        and isinstance(head.get("alg"), str)
        and bool(head["alg"])
        and isinstance(claims, dict)
        and (bool(signature) or head["alg"] == "none")
    )


def find(text: str, key: str | None):
    """Yield (start, end, type, confidence, detector) candidates."""
    lower = text.lower()
    if "private key" in lower:
        for start, end in _private_keys(text):
            yield start, end, "SECRET:private-key", 0.99, "rule"
    for kind, pattern, conf, literals in RULES:
        if not any(literal in lower for literal in literals):
            continue
        group = "s" if "s" in pattern.groupindex else 0
        for m in pattern.finditer(text):
            if kind == "jwt" and not _jwt(m.group()):
                continue
            if kind == "url-password" and re.match(r"\d+/", m.group("s")):
                continue  # host:8080/path?x=a@b: a port and a path, not user:password@host
            if m.start(group) < m.end(group):
                yield m.start(group), m.end(group), f"SECRET:{kind}", conf, "rule"
    for m in (
        KEY_VALUE.finditer(text) if any(k in lower for k in KEYWORD_LITERALS) else ()
    ):
        group = next(g for g in ("dq", "sq", "bq", "bare") if m.group(g) is not None)
        conf = value_confidence(m.group(group), quoted=group != "bare")
        if conf:
            yield m.start(group), m.end(group), "SECRET:generic", conf, "keyword"
    if secret_key(key):
        value = text.strip()
        conf = value_confidence(value, quoted=True)
        if conf:
            start = text.index(value)
            yield start, start + len(value), "SECRET:generic", conf, "keyword"
