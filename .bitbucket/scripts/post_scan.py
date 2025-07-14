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

from __future__ import annotations

import json
import os
import pathlib
import sys
import textwrap
from typing import Any, Dict

import requests

__all__ = ["main"]

BB_API_ROOT = "https://api.bitbucket.org/2.0"


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

    payload: Dict[str, Any] = {
        "content": {"raw": text},
        "inline": {"path": inline_path, "to": line},
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


def _extract(issue: Dict[str, Any]) -> tuple[str, int, str]:
    """Return (file, line, message) triple required for Bitbucket comment.

    The function is *schema-aware*: adapt the keys if your scanner changes.
    """
    # Generic fallbacks – change according to your tool's JSON schema.
    location = issue.get("location", {})
    file_path: str = location.get("file") or issue.get("file") or "UNKNOWN"
    line_no: int = location.get("line") or location.get("endLine") or 1

    title = issue.get("title") or issue.get("ruleId", "Issue")
    description = issue.get("description") or "No description provided."
    suggestion_code = issue.get("suggestion", {}).get("code")

    if suggestion_code:
        msg = textwrap.dedent(
            f"""{title}\n\n{description}\n\n```suggestion\n{suggestion_code}\n```"""
        )
    else:
        msg = f"{title}: {description}"

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
