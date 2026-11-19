"""Complete credential removal, useful surrounding context retained."""

import base64
import json

import pytest

from inconnu import redact


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


def test_cookie_lines_each_parsed_and_header_ends_at_its_line():
    assert (
        redact("theme=dark\nsession=second-secret", key="Cookie")[0]
        == "theme=dark\nsession=[SECRET:cookie]"
    )
    assert "hunter2x" not in redact("Cookie:\nlogin password=hunter2x")[0]


def test_quoted_cookie_preserves_escaped_quote_and_separators():
    assert (
        redact(r'Cookie: auth="one\"two;three"; theme=dark')[0]
        == 'Cookie: auth="[SECRET:cookie]"; theme=dark'
    )
