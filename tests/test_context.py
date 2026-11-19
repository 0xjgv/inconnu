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


def test_full_span_metric_catches_partial_leak():
    from evals.run import score

    record = {
        "category": "pos:SECRET",
        "spans": [{"start": 0, "end": 10, "type": "SECRET", "kind": "jwt"}],
    }
    result = score([record], [[(0, 9, "SECRET:jwt", "rule")]])
    assert result["recall"]["jwt"] == result["covered"]["jwt"] == 1
    assert result["fully_covered"]["jwt"] == 0
