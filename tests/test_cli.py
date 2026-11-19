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


def test_version_command_prints_the_package_version():
    from inconnu import __version__

    result = run(["version"], "")
    assert result.returncode == 0
    assert result.stdout == f"{__version__}\n"


def test_update_does_not_pass_stdin_to_installer(tmp_path):
    installer = tmp_path / "install.sh"
    installer.write_text(
        'if IFS= read -r line; then printf "%s\\n" "$line"; fi\n'
        'printf "%s\\n" "$INCONNU_VERSION"\n'
        'printf "installer stderr\\n" >&2\n'
        "exit 7\n"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from inconnu import cli; cli.__file__ = sys.argv[1]; "
            "raise SystemExit(cli.main(['update', '0.2.0']))",
            str(tmp_path / "cli.py"),
        ],
        input="synthetic stdin canary\n",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 7
    assert result.stdout == "v0.2.0\n"
    assert result.stderr == "installer stderr\n"
