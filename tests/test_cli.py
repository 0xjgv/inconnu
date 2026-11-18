import json
import os
import subprocess
import sys

import pytest


def run(args, stdin, env=None):
    env = {**(os.environ if env is None else env), "PYTHONIOENCODING": "utf-8:strict"}
    return subprocess.run(
        [sys.executable, "-m", "inconnu", *args],
        input=stdin,
        capture_output=True,
        text=isinstance(stdin, str),
        env=env,
    )


def test_text_mode():
    result = run([], "mail jane.doe@example.org\n")
    assert result.returncode == 0
    assert result.stdout == "mail [EMAIL]\n"


def test_json_mode_redacts_strings_recursively():
    payload = {"rows": [["jane.doe@example.org", 7]], "cols": [{"name": "email"}]}
    result = run(["--json"], json.dumps(payload))
    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "rows": [["[EMAIL]", 7]],
        "cols": [{"name": "email"}],
    }


def test_json_mode_rejects_bad_input_without_echoing_it():
    result = run(["--json"], '{"email": "jane.doe@example.org"')
    assert result.returncode == 2
    assert result.stdout == ""
    assert "jane.doe" not in result.stderr


def test_unreadable_input_fails_closed():
    result = run([], b"mail jane.doe@example.org \xff\n")
    assert result.returncode == 1
    assert result.stdout == b""
    assert b"jane.doe" not in result.stderr


def test_scorer_flag_without_keys_redacts_the_band():
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    result = run(["--scorer"], "PASSWORD=hunter\n", env=env)
    assert result.returncode == 0
    assert result.stdout == "PASSWORD=[SECRET:generic]\n"


def test_json_mode_rejects_nan_output():
    result = run(["--json"], '{"x": NaN}')
    assert result.returncode == 1
    assert result.stdout == ""


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="the integer digit limit arrived in 3.11"
)
def test_json_mode_rejects_input_python_cannot_parse():
    result = run(
        ["--json"], '{"x": 1' + "1" * 5000 + "}"
    )  # ValueError without a line number
    assert result.returncode == 2
    assert result.stdout == ""
