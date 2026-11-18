"""inconnu: redact stdin to stdout. Text by default; --json redacts every string in a JSON document.

Exit 0 on success, 2 on unreadable input, 1 on any other error. On failure nothing goes to stdout,
so a caller that passes stdout on can never leak the unredacted input.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .core import redact, redact_json
from .scorer import Scorer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="inconnu", description=__doc__.splitlines()[0]
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
                    f"inconnu: input is not valid JSON (line {exc.lineno}, column {exc.colno})",
                    file=sys.stderr,
                )
                return 2
            output = (
                json.dumps(redact_json(document, scorer), ensure_ascii=False) + "\n"
            )
        else:
            output = redact(data, scorer=scorer)[0]
    except Exception as exc:  # noqa: BLE001 fail closed: report the type only, never the input
        print(f"inconnu: redaction failed ({type(exc).__name__})", file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0
