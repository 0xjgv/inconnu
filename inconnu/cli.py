"""inconnu: redact stdin to stdout. Text by default; --json redacts every string in a JSON document.

    inconnu [--json] [--scorer] < input   redact
    inconnu update [VERSION]              install the latest release, or VERSION such as v0.2.0
    inconnu version                       print the installed version

Exit 0 on success, 2 when --json input is not JSON, 1 on any other error (unreadable input, a failed write). On failure nothing goes to stdout,
so a caller that passes stdout on can never leak the unredacted input.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import __version__, signature
from .core import redact, redact_json
from .scorer import Scorer


def update(target: str) -> int:
    """Run the installer bundled with this version. It verifies the release's signature by
    calling back `update --verify-signature` with this interpreter, then installs the wheel."""
    # Installer-only overrides must not leak in: LOCAL_BUILD skips the signature check.
    environment = {
        key: value
        for key, value in os.environ.items()
        if key not in ("INCONNU_LOCAL_BUILD", "INCONNU_VERSION")
    }
    environment["INCONNU_VERIFIER"] = sys.executable
    if target:
        environment["INCONNU_VERSION"] = "v" + target.lstrip("v")
    installer = Path(__file__).with_name("install.sh")
    return subprocess.run(  # noqa: S603
        ["sh", str(installer)],  # noqa: S607
        env=environment,
        stdin=subprocess.DEVNULL,
    ).returncode


def verify_signature(public_key: str, message: str, signature_file: str) -> int:
    try:
        signature.verify(
            public_key, Path(message).read_bytes(), Path(signature_file).read_text()
        )
    except (OSError, ValueError) as err:
        print(f"inconnu update: {signature_file}: {err}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    command, rest = (argv[0], argv[1:]) if argv else ("", [])
    if command == "update" and len(rest) == 4 and rest[0] == "--verify-signature":
        return verify_signature(*rest[1:])
    if command == "update" and len(rest) <= 1 and rest[:1] != ["--verify-signature"]:
        return update(rest[0] if rest else "")
    if command == "version" and not rest:
        print(__version__)
        return 0
    parser = argparse.ArgumentParser(
        prog="inconnu",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="input and output are JSON")
    parser.add_argument(
        "--scorer",
        action="store_true",
        help="ask a System One scorer about uncertain candidates "
        "(also INCONNU_SCORER=1); needs TYPESAFE_API_KEY, OPENROUTER_API_KEY or RESPAN_API_KEY",
    )
    args = parser.parse_args(argv)
    scorer = (
        Scorer() if args.scorer or os.environ.get("INCONNU_SCORER") == "1" else None
    )
    try:
        data = sys.stdin.read()
        if args.json:
            try:
                document = json.loads(data)
            except ValueError as exc:
                print(
                    "inconnu: input is not valid JSON"
                    + (
                        f" (line {exc.lineno}, column {exc.colno})"
                        if hasattr(exc, "lineno")
                        else ""
                    ),
                    file=sys.stderr,
                )
                return 2
            output = (
                json.dumps(
                    redact_json(document, scorer), ensure_ascii=False, allow_nan=False
                )
                + "\n"
            )
        else:
            output = redact(data, scorer=scorer)[0]
        sys.stdout.write(output)
        sys.stdout.flush()
    except Exception as exc:  # noqa: BLE001 fail closed: report the type only, never the input
        print(f"inconnu: redaction failed ({type(exc).__name__})", file=sys.stderr)
        return 1
    return 0
