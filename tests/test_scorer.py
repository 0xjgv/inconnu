"""The uncertain band: off by default, fail closed, and no raw value leaves the machine."""

import json
import urllib.request

import pytest

from inconnu import Scorer, redact

BAND_TEXT = (
    "PASSWORD=hunter"  # bare identifier value: confidence falls in the uncertain band
)
VALUE = "hunter"


@pytest.fixture
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k2")
    monkeypatch.setenv("RESPAN_API_KEY", "k3")


def test_band_redacts_without_scorer(no_network):
    redacted, findings = redact(BAND_TEXT)
    assert redacted == "PASSWORD=[SECRET:generic]"
    assert findings[0]["detector"] == "keyword"


class Reply:
    def __init__(self, body):
        self.body = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_scorer_can_clear_band_and_sends_no_raw_value(monkeypatch, keys):
    sent = []

    def fake_urlopen(request, timeout):
        sent.append(request.data.decode())
        questions = json.loads(request.data)["questions"]
        return Reply(
            {"answers": {q: {"type": "noul", "noul": 0.01} for q in questions}}
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    redacted, _ = redact(BAND_TEXT, scorer=Scorer())
    assert redacted == BAND_TEXT
    assert sent and all(VALUE not in body and BAND_TEXT not in body for body in sent)


@pytest.mark.parametrize("failure", [TimeoutError, OSError, ValueError])
def test_scorer_fails_closed(monkeypatch, keys, failure):
    def broken(request, timeout):
        raise failure("boom")

    monkeypatch.setattr(urllib.request, "urlopen", broken)
    assert redact(BAND_TEXT, scorer=Scorer())[0] == "PASSWORD=[SECRET:generic]"


def test_scorer_without_keys_fails_closed(monkeypatch, no_network):
    for name in ("TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "RESPAN_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert redact(BAND_TEXT, scorer=Scorer())[0] == "PASSWORD=[SECRET:generic]"


def test_scorer_bad_answer_fails_closed(monkeypatch, keys):
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request, timeout: Reply({"answers": {}})
    )
    assert redact(BAND_TEXT, scorer=Scorer())[0] == "PASSWORD=[SECRET:generic]"


def test_certain_findings_never_reach_scorer(no_network, keys):
    assert redact("jane.doe@example.org", scorer=Scorer())[0] == "[EMAIL]"


def test_description_masks_every_letter_and_drops_personal_keys():
    from inconnu.scorer import describe

    text = "Łukasz Żółćowski"
    description = describe(text, 0, len(text), "PERSON", "jane_smith_notes")
    assert "Shape (A upper, a lower, 9 digit): Aaaaaa Aaaaaaaaa" in description
    assert not any(ch in description for ch in "ŁŻółć")
    assert "jane_smith" not in description


def test_description_drops_secret_shaped_key_names():
    from inconnu.scorer import describe

    token_key = "ghp" + "_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    description = describe("PASSWORD=hunter", 9, 15, "SECRET:generic", token_key)
    assert token_key not in description
    assert "Key name in the text: PASSWORD" in description


def test_late_answer_fails_closed(monkeypatch, keys):
    import inconnu.scorer as scorer_module

    clock = iter([0.0, 0.0, 0.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0])
    monkeypatch.setattr(scorer_module.time, "monotonic", lambda: next(clock, 100.0))

    def slow_urlopen(request, timeout):
        questions = json.loads(request.data)["questions"]
        return Reply(
            {"answers": {q: {"type": "noul", "noul": 0.01} for q in questions}}
        )

    monkeypatch.setattr(urllib.request, "urlopen", slow_urlopen)
    assert (
        redact(BAND_TEXT, scorer=Scorer(budget_s=8))[0] == "PASSWORD=[SECRET:generic]"
    )


def test_cli_scorer_flag_uses_the_scorer(monkeypatch, keys, capsys):
    import io

    from inconnu import cli

    def fake_urlopen(request, timeout):
        questions = json.loads(request.data)["questions"]
        return Reply(
            {"answers": {q: {"type": "noul", "noul": 0.01} for q in questions}}
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr("sys.stdin", io.StringIO(BAND_TEXT))
    assert cli.main(["--scorer"]) == 0
    assert (
        capsys.readouterr().out == BAND_TEXT
    )  # cleared by the scorer, so the scorer ran
