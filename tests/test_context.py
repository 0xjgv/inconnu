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


def test_full_span_metric_catches_partial_leak():
    from evals.run import score

    record = {
        "category": "pos:SECRET",
        "spans": [{"start": 0, "end": 10, "type": "SECRET", "kind": "jwt"}],
    }
    result = score([record], [[(0, 9, "SECRET:jwt", "rule")]])
    assert result["recall"]["jwt"] == result["covered"]["jwt"] == 1
    assert result["fully_covered"]["jwt"] == 0
