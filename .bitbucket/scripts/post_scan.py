#!/usr/bin/env python3
"""
Post Corgea (or any JSON) issues from the pipeline *artifacts* directory to
Bitbucket Cloud as inline comments with "Apply suggestion" blocks.

Usage (inside Bitbucket Pipelines step):
  python .bitbucket/scripts/post_scan.py corgea_issues/

Environment variables used (all provided by Pipelines except the app-password):
  BITBUCKET_PR_ID          – current PR id (empty when not in PR context)
  BITBUCKET_REPO_SLUG      – repo slug, e.g. "inconnu"
  BITBUCKET_WORKSPACE      – workspace id, e.g. "0xjgv"
  BB_API_USER              – Bitbucket username (set as secured variable)
  BB_API_TOKEN             – Bitbucket app-password with `pullrequest:write`

If executed outside Pipelines you can export the variables manually for testing.
"""

import json
import os
import pathlib
import sys
from typing import Any

import requests

__all__ = ["main"]

BB_API_ROOT = "https://api.bitbucket.org/2.0"

sample_issue = {
    "status": "ok",
    "issue": {
        "id": "05d43bed-c72a-417b-a2ea-06a89ae1cd48",
        "scan_id": "81d70177-35aa-423a-9cb0-0fcee0f004f3",
        "status": "open",
        "urgency": "LO",
        "created_at": "2025-07-11T14:24:18.480Z",
        "classification": {
            "id": "CWE-625",
            "name": "Permissive Regular Expression",
            "description": "The product uses a regular expression that does not sufficiently restrict the set of allowed values.",
        },
        "location": {
            "file": {
                "name": "patterns.py",
                "language": "python",
                "path": "inconnu/nlp/patterns.py",
            },
            "line_number": 97,
            "project": {
                "name": "inconnu",
                "branch": "main",
                "git_sha": "5d59780a3b561142b791f4c505f6b3604230cb54",
            },
        },
        "details": {
            "explanation": 'The code uses a regular expression to match IP addresses but it is too lenient, allowing incorrect or malicious input to pass as valid IPs.<br><br>- The regex "re.compile(f"({\'|\'.join(IP_ADDRESS_PATTERN)})")" matches any pattern in "IP_ADDRESS_PATTERN", but these patterns may not fully verify valid IP formats.<br>- Attackers can exploit this by inputting malformed IPs that bypass checks and cause unexpected behavior or security gaps.<br>- This is critical since IP validation often controls access or logging, impacting security or correctness of sensitive operations.'
        },
        "auto_triage": {
            "false_positive_detection": {
                "status": "valid",
                "reasoning": "The regex pattern <code>IP_ADDRESS_PATTERN</code> used in line 97 deliberately allows one or two digit octets for IPv4 and lowercase alphanumeric characters that are not restricted to valid hexadecimal digits for IPv6 on line 95, which does not conform to valid IP standard formats. This overly permissive pattern can lead to misidentification or incorrect matching of IP addresses, creating a risk of false positives or improper filtering when used for security-sensitive operations, as noted in the description. Because of the pattern's incorrect validation logic directly in the code, the vulnerability is valid.",
            }
        },
        "auto_fix_suggestion": {
            "id": "e3b53bb7-924d-4727-ac9b-0982d628331f",
            "status": "fix_available",
            "patch": {
                "diff": 'diff --git a/inconnu/nlp/patterns.py b/inconnu/nlp/patterns.py\nindex ed4774b..1e7b4af 100644\n--- a/inconnu/nlp/patterns.py\n+++ b/inconnu/nlp/patterns.py\n@@ -94,7 +94,10 @@ IP_ADDRESS_PATTERN = (\n     r"[0-9]{1,2}\\.[0-9]{1,2}\\.[0-9]{1,2}\\.[0-9]{1,2}",\n     "[a-z0-9]{4}::[a-z0-9]{4}:[a-z0-9]{4}:[a-z0-9]{4}:[a-z0-9]{4}%?[0-9]*",\n )\n-IP_ADDRESS_PATTERN_RE = re.compile(f"({\'|\'.join(IP_ADDRESS_PATTERN)})")\n+# More accurate patterns for IPv4 and IPv6 addresses.\n+IPV4_PATTERN = r"(?:25[0-5]|2[0-4]\\d|1\\d{2}|[1-9]?\\d)(?:\\.(?:25[0-5]|2[0-4]\\d|1\\d{2}|[1-9]?\\d)){3}"\n+IPV6_PATTERN = r"(?:(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}|((?:[A-Fa-f0-9]{1,4}:){1,7}:)|((?:[A-Fa-f0-9]{1,4}:){1,6}:[A-Fa-f0-9]{1,4})|((?:[A-Fa-f0-9]{1,4}:){1,5}(?::[A-Fa-f0-9]{1,4}){1,2})|((?:[A-Fa-f0-9]{1,4}:){1,4}(?::[A-Fa-f0-9]{1,4}){1,3})|((?:[A-Fa-f0-9]{1,4}:){1,3}(?::[A-Fa-f0-9]{1,4}){1,4})|((?:[A-Fa-f0-9]{1,4}:){1,2}(?::[A-Fa-f0-9]{1,4}){1,5})|([A-Fa-f0-9]{1,4}:(?:(?::[A-Fa-f0-9]{1,4}){1,6}))|(:((?::[A-Fa-f0-9]{1,4}){1,7}|:)))(%.+)?"\n+IP_ADDRESS_PATTERN_RE = re.compile(f"(?:{IPV4_PATTERN})|(?:{IPV6_PATTERN})")\n \n IP_ADDRESS_NAME_PATTERN = r"[a-zA-Z0-9-]*\\.[a-zA-Z]*\\.[a-zA-Z]*"\n \n',
                "explanation": "The fix replaces a simplistic IP regex with precise IPv4 and IPv6 patterns that strictly enforce valid octet and segment ranges, preventing invalid IPs from matching and mitigating the risk of accepting malformed or malicious input.\n<li>Replaced broad pattern <code>IP_ADDRESS_PATTERN_RE</code> with two strict regexes: <code>IPV4_PATTERN</code> and <code>IPV6_PATTERN</code> for accurate IP validation.</li>\n<li><code>IPV4_PATTERN</code> restricts each octet to 0-255 using patterns like <code>25[0-5]</code> and <code>2[0-4]\\d</code>, ensuring no invalid numbers match.</li>\n<li><code>IPV6_PATTERN</code> handles various IPv6 formats including compressed and full notation, validating proper hex groups and optional zone indices (<code>%...</code>).</li>\n<li>The combined regex <code>IP_ADDRESS_PATTERN_RE</code> now matches strictly either the IPv4 or IPv6 pattern using non-capturing groups, improving overall accuracy.</li>",
            },
            "full_code": None,
        },
    },
}


class ConfigError(RuntimeError):
    """Raised when required environment variables are missing."""


def _env(key: str) -> str:
    try:
        return os.environ[key]
    except KeyError as exc:
        raise ConfigError(f"Missing required env-var: {key}") from exc


def _create_comment(pr_id: str, inline_path: str, line: int, text: str) -> None:
    """POST an inline comment to Bitbucket Cloud."""
    url = (
        f"{BB_API_ROOT}/repositories/"
        f"{_env('BITBUCKET_WORKSPACE')}/"
        f"{_env('BITBUCKET_REPO_SLUG')}/pullrequests/{pr_id}/comments"
    )

    payload: dict[str, Any] = {
        "inline": {"path": inline_path, "to": line},
        "content": {"raw": text},
    }

    auth = (_env("BB_API_USER"), _env("BB_API_TOKEN"))
    resp = requests.post(url, json=payload, auth=auth, timeout=10)
    try:
        resp.raise_for_status()
    except requests.HTTPError as err:
        sys.stderr.write(
            f"Failed to comment on {inline_path}:{line}: {err}\n" + resp.text + "\n"
        )
        raise


# ---------------------------------------------------------------------------
# Issue parsing helpers – tailor these according to your scanner's schema.
# ---------------------------------------------------------------------------


def _extract(issue: dict[str, Any]) -> tuple[str, int, str]:
    """Return (file, line, message) triple required for Bitbucket comment.

    The function is *schema-aware*: adapt the keys if your scanner changes.
    """
    # Extract location information from the nested structure
    location = issue.get("location", {})
    file_info = location.get("file", {})
    file_path: str = (
        file_info.get("path") or location.get("file") or issue.get("file") or "UNKNOWN"
    )
    line_no: int = (
        location.get("line_number")
        or location.get("line")
        or location.get("endLine")
        or 1
    )

    # Extract classification details
    classification = issue.get("classification", {})
    title = (
        classification.get("name") or issue.get("title") or issue.get("ruleId", "Issue")
    )
    description = (
        classification.get("description")
        or issue.get("description")
        or "No description provided."
    )

    # Extract auto-fix suggestion if available
    auto_fix = issue.get("auto_fix_suggestion", {})
    suggestion_code = None
    if auto_fix.get("status") == "fix_available":
        patch = auto_fix.get("patch", {})
        suggestion_code = patch.get("diff")
        explanation = patch.get("explanation", "")

    # Build the message
    msg_parts = [f"**{title}**", "", description]

    # Add urgency if available
    urgency = issue.get("urgency")
    if urgency:
        msg_parts.append(f"**Urgency:** {urgency}")

    # Add auto-fix suggestion if available
    if suggestion_code:
        msg_parts.append("")
        msg_parts.append("**Auto-fix available:**")
        msg_parts.append(f"```suggestion\n{suggestion_code}\n```")
        if explanation:
            msg_parts.append("")
            msg_parts.append("**Explanation:**")
            msg_parts.append(explanation)

    msg = "\n".join(msg_parts)
    return file_path, int(line_no), msg


def _iter_issue_files(dir_path: pathlib.Path):
    for json_file in dir_path.glob("*.json"):
        try:
            yield json.loads(json_file.read_text())
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"Skipping invalid JSON {json_file}: {exc}\n")


def main(directory: str = "corgea_issues") -> None:  # pragma: no cover
    pr_id = os.environ.get("BITBUCKET_PR_ID")
    if not pr_id:
        sys.stderr.write("No BITBUCKET_PR_ID – not in a PR context, exiting.\n")
        return

    path = pathlib.Path(directory)
    if not path.is_dir():
        raise SystemExit(f"Artifact directory '{directory}' not found")

    issue_count = 0
    for issue in _iter_issue_files(path):
        try:
            file_path, line, message = _extract(issue)
        except Exception as exc:  # noqa: BLE001 – we need robustness here
            sys.stderr.write(f"Error parsing issue JSON: {exc}\n")
            continue
        try:
            _create_comment(pr_id, file_path, line, message)
            issue_count += 1
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"Posting comment failed: {exc}\n")

    print(f"Posted {issue_count} Bitbucket comments from {directory}")


if __name__ == "__main__":
    dir_arg = sys.argv[1] if len(sys.argv) > 1 else "corgea_issues"
    try:
        main(dir_arg)
    except ConfigError as ce:
        sys.stderr.write(str(ce) + "\n")
        sys.exit(1)
