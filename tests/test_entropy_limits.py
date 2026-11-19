import pytest

from inconnu import redact


@pytest.mark.parametrize("token", ["EVqiCeC-zF6BkvaJFPbHXA", "MxvIY_nlAKq2IQFGPGdsdQ"])
def test_short_random_segments_are_redacted_with_original_offsets(token):
    output, findings = redact(f"opaque.{token}.tail")
    assert output == "opaque.[SECRET:entropy].tail"
    assert [(f["start"], f["end"]) for f in findings] == [(7, 7 + len(token))]


def test_relaxed_gate_stays_out_of_build_identifiers_and_id_columns():
    cell = "cp314-win_arm64-asset_00421"
    assert redact(cell) == (cell, [])
    build = "rhel9-x86_64-clang-build_000192"
    assert redact(build) == (build, [])
    token = "MxvIY_nlAKq2IQFGPGdsdQ"
    assert redact(token, "objectId") == (token, [])
