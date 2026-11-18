import json
import subprocess
import sys


def run(args, stdin):
    return subprocess.run(
        [sys.executable, "-m", "inconnu", *args],
        input=stdin,
        capture_output=True,
        text=True,
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
