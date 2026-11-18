"""Detector tests. Secret-shaped values are assembled at runtime so no scanner sees a literal token."""

import pytest

from inconnu import redact, redact_batch, redact_json

A36 = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"  # 36 mixed alnum chars
DSN = "postgres:" + "//app:{}@db.internal:5432/prod"


def placeholders(text, **kwargs):
    redacted, findings = redact(text, **kwargs)
    return redacted, {f["type"] for f in findings}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Contact jane.doe@example.org today", "Contact [EMAIL] today"),
        ("Call +1 415-555-2671 now", "Call [PHONE] now"),
        ("Call (415) 555-2671 now", "Call [PHONE] now"),
        ("Ring +44 20 7946 0958 later", "Ring [PHONE] later"),
        ("IBAN DE89 3704 0044 0532 0130 00 on file", "IBAN [IBAN] on file"),
        ("card 4111 1111 1111 1111 exp 12/29", "card [CARD] exp 12/29"),
        ("SSN 536-22-1234 here", "SSN [SSN] here"),
        ("from 203.0.113.42 at", "from [IP] at"),
        ("from 2001:db8::8a2e:370:7334 at", "from [IP] at"),
        ("Mr. Smith approved it", "[PERSON] approved it"),
        ("Assigned to Maria Gonzalez yesterday", "Assigned to [PERSON] yesterday"),
    ],
)
def test_pii(text, expected):
    assert redact(text)[0] == expected


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        ("AKIA" + "Z7Q2" * 4, "aws-access-key"),
        ("ghp" + "_" + A36, "github-token"),
        (
            "github_pat_" + "11ABCDEFG0123456789abc_" + "a1B2c3D4e5" * 5 + "F6g7H8i9J",
            "github-token",
        ),
        ("glpat-" + "Ab3dEf6hIj9lMn2pQr5t", "gitlab-token"),
        ("sk-ant-api03-" + "aB3_dE6-gH9" * 8 + "AA", "anthropic-key"),
        ("sk-proj-" + "Ab3De6Gh9Jk2Mn5Pq8St1Vw4Yz7" * 2, "openai-key"),
        (
            "xox" + "b-1234567890-1234567890123-" + "AbCdEfGhIjKlMnOpQrStUvWx",
            "slack-token",
        ),
        ("sk_" + "live_" + "4eC39HqLyjWDarjtT1zdp7dc", "stripe-key"),
        ("AIza" + "SyD-9tSrke72PouQMnMX-a7eZSW0jkFMBWY", "google-api-key"),
        (
            "eyJhbGciOiJIUzI1NiJ9"
            + "."
            + "eyJzdWIiOiIxMjM0NTY3ODkwIn0"
            + ".dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
            "jwt",
        ),
        (
            "pbkdf2_sha256$600000$"
            + "Xq3vLm9TzR2k"
            + "$"
            + "dGhpcyBpcyBub3QgYSByZWFsIGhhc2g0123456789+/=",
            "password-hash",
        ),
    ],
)
def test_secret_rules(value, kind):
    redacted, types = placeholders(f"value: {value} end")
    assert value not in redacted
    assert f"SECRET:{kind}" in types


def test_webhooks_and_pem():
    slack = (
        "https://hooks.slack.com/services/"
        + "T0A1B2C3D/B0A1B2C3D/"
        + "AbCdEfGhIjKlMnOpQrStUvWx"
    )
    discord = (
        "https://discord.com/api/webhooks/123456789012345678/"
        + "AbCdEf-GhIjKl_MnOpQrStUvWx0123456789"
    )
    pem = (
        "-----BEGIN RSA "
        + "PRIVATE KEY-----\n"
        + "MIIEowIBAAKCAQEA7bq+9" * 6
        + "\n-----END RSA PRIVATE KEY-----"
    )
    for value, kind in (
        (slack, "slack-webhook"),
        (discord, "discord-webhook"),
        (pem, "private-key"),
    ):
        redacted, types = placeholders(f"x {value} y")
        assert value not in redacted and f"SECRET:{kind}" in types, kind


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (DSN.format("S3cr3t!pw"), DSN.format("[SECRET:url-password]")),
        (DSN.format("p@ss#w?rd"), DSN.format("[SECRET:url-password]")),
        ('password = "hunter2!x"', 'password = "[SECRET:generic]"'),
        ("DB_PASSWORD=Tr0ub4dor&3", "DB_PASSWORD=[SECRET:generic]"),
        (
            "Authorization: Bearer abcDEF123456ghiJKL789mno",
            "Authorization: Bearer [SECRET:bearer]",
        ),
    ],
)
def test_secret_context(text, expected):
    assert redact(text)[0] == expected


def test_entropy_unknown_secret():
    value = "q7Zp2Lk9Xv4Rt8Wm3Nb6Yc1Hd5Js0Gf"
    redacted, types = placeholders(f"the value {value} was leaked")
    assert redacted == "the value [SECRET:entropy] was leaked"
    assert types == {"SECRET:entropy"}


@pytest.mark.parametrize(
    "text",
    [
        "9f27a2ca-cd59-4aba-9849-eb8e9688b4fe",
        "7257bc0f80f9b5656bf6d1309fcd2454affc733d",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e464b934ca495991b7852b855",
        "2025-07-11T15:07:25.719Z",
        "1731945600123",
        "src/components/UserProfileSettings/index.tsx",
        "CWE-625 CVE-2024-3094 GHSA-4w2v-q235-vp99",
        "https://github.com/0xjgv/inconnu/blob/main/README.md",
        "token_count = 5",
        "password = os.environ['DB_PASSWORD']",
        "AbstractSingletonProxyFactoryBean",
        "sha512-9Fz2bVbL1jK8nQ0pR7sT4uW6xY3zA5bC8dE0fG2hI4jK6lM8nO0pQ2rS4tU6vW8xY0zA2bC4dE6fG8hI0jK2lM==",
        "Acme Corp renewed the contract",
        "permissions:\n  id-token: write",
        '{"SECRET:anthropic-key": 1.0}',
        "pairs = list(zip(sparse[::2], sparse[1::2]))",
        "created 2024-01-15 and 15.01.2024",
        "tomli-2.5.0-cp314-cp314t-manylinux_2_17_x86_64.whl",
        "https://app.corgea.com/issue/0eea28ce-8f71-7a51-2305-36116248e4f1",
        "request_id=Zp0AZNgD0Gmx4NQmDNs2tY9q",
        "integrity sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8wC",
        "FIXTURE = 'SGVsbG8gd29ybGQsIHRoaXMgaXMgYSB0ZXN0Lg=='",
    ],
)
def test_negatives_untouched(text):
    redacted, findings = redact(text)
    assert redacted == text, findings


def test_findings_hold_no_raw_value():
    text = "mail jane.doe@example.org key " + "AKIA" + "Z7Q2" * 4
    redacted, findings = redact(text)
    assert [f["type"] for f in findings] == ["EMAIL", "SECRET:aws-access-key"]
    for f in findings:
        assert set(f) == {"type", "start", "end", "confidence", "detector"}
        assert text[f["start"] : f["end"]] not in str(f)


def test_key_context_marks_whole_cell():
    assert redact("Tr0ub4dor&3", key="password")[0] == "[SECRET:generic]"
    assert redact("4155552671", key="phone")[0] == "[PHONE]"
    assert redact("4155552671")[0] == "4155552671"


def test_batch_matches_single_calls():
    cells = ["jane.doe@example.org", "plain", "", "203.0.113.42"]
    assert redact_batch(cells) == [redact(c) for c in cells]


def test_redact_json_gives_row_cells_their_column_names():
    data = {
        "cols": [{"name": "password"}, {"name": "note"}],
        "rows": [["hunter", "hunter"]],
    }
    assert redact_json(data)["rows"] == [["[SECRET:generic]", "hunter"]]


def test_redact_json_uses_keys_and_keeps_structure():
    data = {
        "rows": [
            {"email": "jane.doe@example.org", "password": "hunter2xyz", "count": 3}
        ],
        "ok": True,
    }
    out = redact_json(data)
    assert out == {
        "rows": [{"email": "[EMAIL]", "password": "[SECRET:generic]", "count": 3}],
        "ok": True,
    }
