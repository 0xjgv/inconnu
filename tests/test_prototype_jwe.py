import base64
import json

import pytest

from inconnu import redact


def encode(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def envelope(header, encrypted_key):
    return ".".join(
        map(
            encode,
            (
                header,
                encrypted_key,
                bytes(range(12)),
                bytes(range(80)),
                bytes(range(16)),
            ),
        )
    )


@pytest.mark.parametrize("alg,key", [("RSA-OAEP", bytes(range(64))), ("dir", b"")])
def test_full_jwe_in_prose(alg, key):
    header = json.dumps({"enc": "A256GCM", "alg": alg}, indent=2).encode()
    token = envelope(header, key)
    output, findings = redact("received " + token + ".")
    assert output == "received [SECRET:jwe]."
    assert [(f["start"], f["end"], f["type"]) for f in findings] == [
        (9, 9 + len(token), "SECRET:jwe")
    ]


@pytest.mark.parametrize(
    "header",
    [
        b"public digest",
        b"[]",
        b'{"alg":"dir"}',
        b'{"enc":"A256GCM"}',
        b'{"alg":42,"enc":"A256GCM"}',
        b'{"alg":"dir","enc":""}',
    ],
)
def test_five_parts_require_a_jwe_header(header):
    _, findings = redact(envelope(header, b""))
    assert all(f["type"] != "SECRET:jwe" for f in findings)


@pytest.mark.parametrize(
    "text",
    [
        "build.2.41.5.7",
        "api.us.prod.example.net",
        "tenant.project.scan.finding.item",
    ],
)
def test_public_five_part_strings_stay_visible(text):
    assert redact(text)[0] == text


def test_does_not_match_a_prefix_of_a_longer_dotted_identifier():
    value = envelope(b'{"alg":"dir","enc":"A256GCM"}', b"") + ".more"
    assert all(f["type"] != "SECRET:jwe" for f in redact(value)[1])
