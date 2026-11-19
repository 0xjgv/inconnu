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


def test_quoted_cookie_preserves_escaped_quote_and_separators():
    assert (
        redact(r'Cookie: auth="one\"two;three"; theme=dark')[0]
        == 'Cookie: auth="[SECRET:cookie]"; theme=dark'
    )
