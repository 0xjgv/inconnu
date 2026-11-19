import base64
import json

import pytest

from inconnu import redact


def segment(value):
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


@pytest.mark.parametrize("raw", ['{"format":"json"}', '{ "format": "json" }'])
def test_known_public_metadata_stays_in_unkeyed_cell(raw):
    public = f"{segment(raw)}.{segment('{}')}.release_notes"
    assert redact(public) == (public, [])
    assert "[SECRET:" in redact(segment(raw), key="token")[0]


@pytest.mark.parametrize(
    "raw",
    [
        '{"pin":9}',
        '{"format":"json","password":"violet47"}',
        json.dumps({"张伟": 123456789}, ensure_ascii=False),
        ' {"pin":9}',
        '  [{"pin":"violet47"}]',
        " " * 24 + '{"pin":9}',
        json.dumps({"value": "private" * 40}),
    ],
)
def test_encoded_private_or_unknown_json_redacts_every_source_character(raw):
    payload = segment(raw)
    header = segment('{ "format": "json" }')
    text = f"{header}.{payload}.release_notes"
    output, findings = redact(text)
    assert output == f"{header}.[SECRET:entropy].release_notes"
    assert [(f["start"], f["end"]) for f in findings] == [
        (len(header) + 1, len(header) + 1 + len(payload))
    ]


def test_noncanonical_padding_bits_do_not_enter_public_allowlist():
    # e31 is a noncanonical base64 spelling of {}.
    assert redact("meta.e31.release_notes")[0] == "meta.[SECRET:entropy].release_notes"
