"""Read cases on stdin and return only redaction outputs and spans on stdout."""

import json
import sys

sys.path.insert(0, sys.argv[1])
from inconnu import redact  # noqa: E402

for line in sys.stdin:
    case = json.loads(line)
    output, findings = redact(case["text"], key=case["key"])
    print(
        json.dumps(
            {
                "output": output if case["named"] else None,
                "spans": [[item["start"], item["end"]] for item in findings],
            }
        )
    )
