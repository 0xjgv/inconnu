"""Complete credential removal, useful surrounding context retained."""

import base64
import json

import pytest

from inconnu import redact, redact_json


def jwt(header, claims):
    enc = lambda value: base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")  # noqa: E731
    return (
        enc(header)
        + "."
        + enc(json.dumps(claims))
        + "."
        + enc("signature bytes for testing")
    )


@pytest.mark.parametrize(
    "parameter",
    [
        "token",
        "key",
        "sig",
        "access_token",
        "X-Amz-Signature",
        "X-Goog-Signature",
        "api%5Fkey",
    ],
)
def test_url_query_keeps_host_path_and_other_parameters(parameter):
    prefix = f"https://service.example/path?page=2&{parameter}="
    assert (
        redact(prefix + "a%2Bb%3Dc&ref=main#section")[0]
        == prefix + "[SECRET:url-query]&ref=main#section"
    )


@pytest.mark.parametrize(
    "text,redacted",
    [
        (
            "fetch(`https://x.example/p?token=ab12cd34`)",
            "fetch(`https://x.example/p?token=[SECRET:url-query]`)",
        ),
        (
            "see (https://x.example/p?token=ab12cd34), then",
            "see (https://x.example/p?token=[SECRET:url-query]), then",
        ),
        (
            "`https://x.example/p?token=${TOKEN}`",
            "`https://x.example/p?token=${TOKEN}`",
        ),
        (
            "https://x.example/p?token=changeme&ref=main",
            "https://x.example/p?token=changeme&ref=main",
        ),
    ],
)
def test_url_query_value_stops_at_delimiters_and_skips_placeholders(text, redacted):
    assert redact(text)[0] == redacted


@pytest.mark.parametrize(
    "scheme", ["postgres", "postgresql", "mysql", "mongodb+srv", "redis", "amqp"]
)
@pytest.mark.parametrize(
    "user,password", [("", "short-pass!"), ("service", "low_entropy_" * 20)]
)
def test_dsn_password_only_and_long_password(scheme, user, password):
    prefix = f"{scheme}://{user}:"
    suffix = "@db.internal:5432/prod"
    assert (
        redact(prefix + password + suffix)[0]
        == prefix + "[SECRET:url-password]" + suffix
    )
    clean = f"{scheme}://db.internal:5432/prod"
    assert redact(clean)[0] == clean


@pytest.mark.parametrize(
    "header",
    [
        '{ "alg": "HS256", "typ": "JWT" }',
        '{\n"typ":"JWT","alg":"RS256"}',
        '{"alg":"HS256"}',
    ],
)
@pytest.mark.parametrize(
    "claims", [{}, {"sub": "user-account", "email": "jane@example.org"}]
)
def test_jwt_redacts_header_claims_and_signature(header, claims):
    token = jwt(header, claims)
    assert redact("value=" + token)[0] == "value=[SECRET:jwt]"


@pytest.mark.parametrize(
    "prefix,token",
    [
        ("", jwt(json.dumps({"alg": "RS256", "x5c": ["MIIC" * 1500]}), {})),
        ("", jwt('{"alg":"HS256"}', {"groups": [f"g-{i:05d}" for i in range(1500)]})),
        ("", jwt('{"alg":"HS256"}', {}).rsplit(".", 1)[0] + "." + "A" * 2400),
        ("v2.", jwt('{"alg":"HS256"}', {"sub": "user-account"})),
    ],
    ids=["large-header", "large-claims", "large-signature", "after-dot"],
)
def test_jwt_of_any_size_after_a_dot_is_redacted_whole(prefix, token):
    assert redact("value " + prefix + token)[0] == "value " + prefix + "[SECRET:jwt]"


def test_unsigned_jwt_claims_are_sensitive():
    token = jwt('{"alg":"none"}', {"sub": "user-account"}).rsplit(".", 1)[0] + "."
    assert redact(token)[0] == "[SECRET:jwt]"


@pytest.mark.parametrize(
    "header", ['{"format":"json"}', "[]", '{"alg":42}', "not JSON"]
)
def test_non_jwt_structure_is_not_a_jwt(header):
    from inconnu.credentials import _jwt

    assert not _jwt(jwt(header, {}))


@pytest.mark.parametrize(
    "name",
    [
        "session",
        "sessionid",
        "connect.sid",
        "JSESSIONID",
        "PHPSESSID",
        "__Host-session",
        "custom_auth",
    ],
)
def test_auth_cookies_preserve_preferences_and_attributes(name):
    value = "ab12" * 8
    assert (
        redact(f"Cookie: theme=dark; {name}={value}; locale=en")[0]
        == f"Cookie: theme=dark; {name}=[SECRET:cookie]; locale=en"
    )
    assert (
        redact(f"Set-Cookie: {name}={value}; Path=/; HttpOnly; Secure")[0]
        == f"Set-Cookie: {name}=[SECRET:cookie]; Path=/; HttpOnly; Secure"
    )
    assert (
        redact(f"{name}={value}; Path=/", key="Set-Cookie")[0]
        == f"{name}=[SECRET:cookie]; Path=/"
    )


@pytest.mark.parametrize(
    "key", ["session", "session_id", "sessionId", "connect.sid", "users.session_token"]
)
def test_session_columns(key):
    assert redact("ab12" * 8, key=key)[0] == "[SECRET:generic]"


@pytest.mark.parametrize(
    "text",
    [
        "Cookie: theme=dark; locale=en",
        "Set-Cookie: theme=dark; Path=/; SameSite=Lax",
        "https://git.example/acme/repo.git?ref=main&page=2",
        "session_count=42",
    ],
)
def test_harmless_context_is_preserved(text):
    assert redact(text)[0] == text


@pytest.mark.parametrize(
    "key", ["fullName", "users.full_name", "author_name", "firstName"]
)
def test_unknown_names_in_explicit_columns(key):
    assert redact("zuzanna niewiadomska", key=key)[0] == "[PERSON]"


@pytest.mark.parametrize(
    "key",
    [
        "companyName",
        "companies.name",
        "users.company_name",
        "org.name",
        "tenant.name",
        "vendor.name",
        "employer.name",
    ],
)
def test_company_context_does_not_suppress_secrets(key):
    assert redact("Morgan Stanley", key=key)[0] == "Morgan Stanley"
    assert redact("password=hungrybadger", key=key)[0] == "password=[SECRET:generic]"


@pytest.mark.parametrize("key", ["organizations.contacts.name", "company.users.name"])
def test_company_ancestor_above_people_keeps_person_detection(key):
    assert redact("Maria Gonzalez", key=key)[0] == "[PERSON]"


@pytest.mark.parametrize(
    "key,value,redacted",
    [
        ("first_name", "Xochiquetzal", "[PERSON]"),
        ("owner", "service", "service"),
        ("assignee", "unassigned", "unassigned"),
        ("author", "system", "system"),
    ],
)
def test_single_words_are_names_only_in_name_part_columns(key, value, redacted):
    assert redact(value, key=key)[0] == redacted


def test_metabase_names_and_session_values():
    out = redact_json(
        {
            "cols": [
                {"name": "fullName"},
                {"name": "session"},
                {"name": "companyName"},
            ],
            "rows": [["zuzanna niewiadomska", "ab12" * 8, "Morgan Stanley"]],
        }
    )
    assert out["rows"] == [["[PERSON]", "[SECRET:generic]", "Morgan Stanley"]]


def test_id_context_preserves_explicit_and_unkeyed_secrets():
    token = "q7Zp2Lk9Xv4Rt8Wm3Nb6Yc1Hd5Js0Gf"
    assert redact("pi_" + token, key="payment_intent")[0] == "pi_" + token
    assert redact(token, key="payment_intent")[0] == "[SECRET:entropy]"
    assert redact(token)[0] == "[SECRET:entropy]"
    assert redact("token=" + token, key="payment_intent")[0] == "token=[SECRET:entropy]"


def test_full_span_metric_catches_partial_leak():
    from evals.run import score

    record = {
        "category": "pos:SECRET",
        "spans": [{"start": 0, "end": 10, "type": "SECRET", "kind": "jwt"}],
    }
    result = score([record], [[(0, 9, "SECRET:jwt", "rule")]])
    assert result["recall"]["jwt"] == result["covered"]["jwt"] == 1
    assert result["fully_covered"]["jwt"] == 0


def test_credential_candidates_remain_bounded():
    import time

    for cell in [
        "http://u:" * 1800,
        "a." * 8000,
        "a" * 16000 + "." + "b" * 16000 + ".",
        "Cookie: " + "x=abc; " * 2200,
    ]:
        started = time.perf_counter()
        redact(cell)
        assert time.perf_counter() - started < 0.5
    started = time.perf_counter()
    redact("a=1\n" + "\n" * 32000, key="Cookie")  # every blank line is a pair anchor
    assert time.perf_counter() - started < 0.5


@pytest.mark.parametrize(
    "key,prefix",
    [
        ("paymentIntent", "pi_"),
        ("customer", "cus_"),
        ("request", "req_"),
        ("event", "evt_"),
    ],
)
def test_object_context_requires_matching_id_shape(key, prefix):
    value = "q7Zp2Lk9Xv4Rt8Wm3Nb6Yc1Hd5Js0Gf"
    assert redact(prefix + value, key="table." + key)[0] == prefix + value
    assert redact(value, key=key)[0] == "[SECRET:entropy]"
    other = "cus_" if prefix == "pi_" else "pi_"
    assert redact(other + value, key="table." + key)[0] == "[SECRET:entropy]"
    for secret_prefix in ["sk_live_", "rk_live_", "whsec_"]:
        result, findings = redact(secret_prefix + value, key="table." + key)
        assert value not in result
        assert any(f["type"].startswith("SECRET:") for f in findings)


@pytest.mark.parametrize("prefix", ["sk_live_", "rk_live_", "whsec_"])
def test_provider_prefix_overrides_id_and_randomness(prefix):
    for suffix in ("x9", "a" * 32):
        assert redact(prefix + suffix, key="table.request")[0] == "[SECRET:stripe-key]"


def test_cookie_fails_closed_on_unterminated_quote_and_secret_column():
    assert redact('Cookie: sess="last-letter')[0] == 'Cookie: sess="[SECRET:cookie]'
    assert (
        redact("secret-part Cookie: theme=dark", key="api_key")[0] == "[SECRET:generic]"
    )


def test_person_context_in_prose():
    assert (
        redact("Reviewed by Zuzanna Niewiadomska today.")[0]
        == "Reviewed by [PERSON] today."
    )
    assert (
        redact("Reviewed by Build System today.")[0]
        == "Reviewed by Build System today."
    )
    assert (
        redact("Assigned to Security Lead yesterday.")[0]
        == "Assigned to Security Lead yesterday."
    )


def test_cookie_lines_each_parsed_and_header_ends_at_its_line():
    assert (
        redact("theme=dark\nsession=second-secret", key="Cookie")[0]
        == "theme=dark\nsession=[SECRET:cookie]"
    )
    assert "hunter2x" not in redact("Cookie:\nlogin password=hunter2x")[0]
    for space in ("\u00a0", "\f"):
        assert (
            redact(f"Cookie: theme=dark;{space}sid=ab12ab12")[0]
            == f"Cookie: theme=dark;{space}sid=[SECRET:cookie]"
        )


def test_quoted_cookie_preserves_escaped_quote_and_separators():
    assert (
        redact(r'Cookie: auth="one\"two;three"; theme=dark')[0]
        == 'Cookie: auth="[SECRET:cookie]"; theme=dark'
    )


def test_digits_only_phone_requires_a_phone_label():
    text = "Phone: 4155552671. Scan ID: 4155552671."
    output, findings = redact(text)
    assert output == "Phone: [PHONE]. Scan ID: 4155552671."
    assert [(f["type"], f["start"], f["end"]) for f in findings] == [("PHONE", 7, 17)]


def test_markdown_table_uses_column_context_without_changing_other_cells():
    text = (
        "Inventory\r\n\r\n"
        "| Contact | Database password | Project ID |\r\n"
        "| :--- | --- | ---: |\r\n"
        "| Amélina Xovnari | plumviolet | 4155552671 |\r\n"
        "| | | 4155552671 |\r\n"
    )
    expected = (
        "Inventory\r\n\r\n"
        "| Contact | Database password | Project ID |\r\n"
        "| :--- | --- | ---: |\r\n"
        "| [PERSON] | [SECRET:generic] | 4155552671 |\r\n"
        "| | | 4155552671 |\r\n"
    )
    output, findings = redact(text)
    assert output == expected
    assert [text[f["start"] : f["end"]] for f in findings] == [
        "Amélina Xovnari",
        "plumviolet",
    ]
    assert redact(output) == (expected, [])


def test_markdown_table_keeps_an_escaped_pipe_within_the_secret_cell():
    text = "Password | Status\n--- | ---\nplum\\|violet | active\n\nordinary | prose"
    assert redact(text)[0] == (
        "Password | Status\n--- | ---\n[SECRET:generic] | active\n\nordinary | prose"
    )


def test_passphrase_context_covers_the_complete_phrase():
    text = 'Passphrase: "plum violet"\nPaint colour: "plum violet"'
    assert redact(text)[0] == (
        'Passphrase: "[SECRET:generic]"\nPaint colour: "plum violet"'
    )
    assert redact("Passphrase: plum violet\nContinue")[0] == (
        "Passphrase: [SECRET:generic]\nContinue"
    )
    assert redact_json({"passphrase": "plum violet", "colour": "plum violet"}) == {
        "passphrase": "[SECRET:generic]",
        "colour": "plum violet",
    }
