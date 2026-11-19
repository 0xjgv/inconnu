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
        (
            "https://x.example/?email=jane@example.org",
            "https://x.example/?email=[EMAIL]",
        ),
        ("from 2001:db8::8a2e:370:7334 at", "from [IP] at"),
        ("https://x.example?email=jane@example.org", "https://x.example?email=[EMAIL]"),
        ("mail git@example.org now", "mail [EMAIL] now"),
        ("from 2001:db8::192.0.2.1 at", "from [IP] at"),
        ("Thanks John O'Connor", "Thanks [PERSON]"),
        ("Dr Li", "[PERSON]"),
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
        ("npm" + "_" + A36, "npm-token"),
        ("pypi-" + "AgEIcHlwaS5vcmc" + "Ab3_dE6-gH9" * 6, "pypi-token"),
        (
            "SG."
            + "Ab3dE6gH9jK2mN5pQ8sT1v"
            + "."
            + "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7bC0eF3hI6kL9nO2q",
            "sendgrid-key",
        ),
        (
            "$2b$12$" + "Ab3dE6gH9jK2mN5pQ8sT1vW4yZ7bC0eF3hI6kL9nO2qR5tU8wX1z.",
            "password-hash",
        ),
        (
            "$argon2id$v=19$m=65536,t=3,p=4$"
            + "c2FsdHNhbHRzYWx0"
            + "$"
            + "Ab3dE6gH9jK2mN5pQ8sT1vW4",
            "password-hash",
        ),
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
    basic = "Authorization: Basic " + "dXNlcjpodW50ZXIyIQ=="
    for value, kind in (
        (slack, "slack-webhook"),
        (discord, "discord-webhook"),
        (pem, "private-key"),
        (basic, "basic-auth"),
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
        ('dbPassword="Tr0ub4dor!"', 'dbPassword="[SECRET:generic]"'),
        ('accessToken="Tr0ub4dor!"', 'accessToken="[SECRET:generic]"'),
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


def test_redact_json_signed_numbers_in_sensitive_fields():
    data = {
        "ssn": -123456789,
        "phone": -4155552671.0,
        "card": -4111111111111111,
        "rows": [["+123456789", -123456789, -1234.5, -666123456]],
        "cols": ["ssn", "order_id", "phone", "ssn"],
        "balance": -4155552671.0,
    }
    assert redact_json(data) == {
        **data,
        "ssn": "[SSN]",
        "phone": "[PHONE]",
        "card": "[CARD]",
        "rows": [["[SSN]", -123456789, -1234.5, -666123456]],
    }


@pytest.mark.parametrize(
    ("text", "kwargs", "leak"),
    [
        (
            "password=Jane.Doe@example.org!x9",
            {},
            "!x9",
        ),  # overlap: the union is redacted
        ("password=p4ss,w0rd!", {}, "w0rd"),
        ("DB_PASSWORD=abc;def123", {}, "def123"),
        ("ab1!x", {"key": "password"}, "ab1!x"),  # short cell under a secret key
        (
            "line1abc\nline2xyz",
            {"key": "password"},
            "line2xyz",
        ),  # multi-line credential
        ("John Smith", {"key": "customer_name"}, "Smith"),
        (DSN.format("ab/cd123"), {}, "ab/cd123"),  # '/' in a DSN password
    ],
)
def test_review_leaks_are_closed(text, kwargs, leak):
    assert leak not in redact(text, **kwargs)[0]


def test_url_with_port_and_later_at_sign_is_not_a_password():
    url = "https://example.com:8080/users?ref=docs"
    assert redact(url)[0] == url


def test_batch_rejects_mismatched_keys():
    with pytest.raises(ValueError):
        redact_batch(["a@example.com", "b@example.com"], ["email"])


def test_redact_json_redacts_keys_floats_and_keeps_colliding_keys():
    out = redact_json(
        {
            "jane@example.org": 1,
            "joe@example.org": 2,
            "phone": 4155552671.0,
            "ratio": 0.5,
        }
    )
    assert out == {"[EMAIL]": 1, "[EMAIL] (2)": 2, "phone": "[PHONE]", "ratio": 0.5}


def test_adversarial_cells_stay_linear():
    import time

    begin = "-----BEGIN " + "PRIVATE KEY-----"
    cells = [
        "key " + "-" * 10000,
        "token " + "a_" * 8000,
        "key " + "-".join("deadbeef" for _ in range(1400)),
        begin * 600,
        "Maria " * 3000,
    ]
    for cell in cells:
        started = time.perf_counter()
        redact(cell)
        assert time.perf_counter() - started < 0.5, cell[:20]


@pytest.mark.parametrize(
    ("text", "kwargs", "leak"),
    [
        ("authorization: BASIC " + "dXNlcjpodW50ZXIyIQ==", {}, "dXNlcjpodW50ZXIyIQ=="),
        ('password = "abc\\"def123"', {}, "def123"),  # escaped quote inside the literal
        ("password=ab)cd)ef!", {}, "cd)ef"),
        (
            "password=access",
            {},
            "access",
        ),  # a code word is still a candidate (uncertain band)
        ("x=q7Zp2Lk9Xv4Rt8Wm3Nb6Yc1Hd5Js0Gf", {}, "q7Zp2Lk9Xv4Rt8Wm3Nb6Yc1Hd5Js0Gf"),
        ("JOHN SMITH", {"key": "full_name"}, "SMITH"),
        ("maria gonzalez", {"key": "author"}, "gonzalez"),
    ],
)
def test_bot_review_leaks_are_closed(text, kwargs, leak):
    assert leak not in redact(text, **kwargs)[0]


def test_batch_rejects_empty_keys_list():
    with pytest.raises(ValueError):
        redact_batch(["a@example.com"], [])


def test_second_bot_review_cases():
    begin, end = "-----BEGIN " + "PRIVATE KEY-----", "-----END " + "PRIVATE KEY-----"
    big = begin + "\n" + ("MIIEowIBAAKCAQEA7bq9" * 4 + "\n") * 150 + end
    assert redact("key: " + big)[0] == "key: [SECRET:private-key]"
    assert "MIIE" not in redact(begin + "\nMIIEowIBAAKCAQEA7bq9 truncated")[0]
    dsn = "postgres:" + "//user:" + "s3cretPw9" + "@[2001:db8::1]:5432/db"
    assert "s3cretPw9" not in redact(dsn)[0]
    assert redact("from 2001:db8::1.")[0] == "from [IP]."
    assert redact("Mr. Smith Approved Review")[0] == "[PERSON] Approved Review"
    assert redact("Acme Corp", key="full_name")[0] == "Acme Corp"
    letters = "qZpLkXvRtWmNbYcHdJsGfQaZxPlMkJ"
    assert letters not in redact(f"rotated {letters} today")[0]
