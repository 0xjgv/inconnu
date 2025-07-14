#!/usr/bin/env python3
# ruff: noqa: S603
"""
Request changes on a Bitbucket pull request based on Corgea security scan results.

Usage (inside Bitbucket Pipelines step):
  python .bitbucket/scripts/post_scan.py corgea_issues/

Environment variables used (all provided by Pipelines):
  BITBUCKET_PR_ID          – current PR id (empty when not in PR context)
  BITBUCKET_REPO_SLUG      – repo slug, e.g. "inconnu"
  BITBUCKET_WORKSPACE      – workspace id, e.g. "0xjgv"
  BITBUCKET_ACCESS_TOKEN   – access token for authentication

The script will request changes on the PR if security issues are found,
or remove any existing change request if no issues are found.
"""

import json
import os
import pathlib
import sys

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


def _request_changes(pr_id: str, message: str) -> bool:
    """Request changes on a pull request.

    Returns True if successful, False otherwise.
    """
    access_token = os.environ.get("BITBUCKET_ACCESS_TOKEN")
    if not access_token:
        sys.stderr.write(
            "Error: BITBUCKET_ACCESS_TOKEN environment variable not set.\n"
        )
        return False

    url = (
        f"{BB_API_ROOT}/repositories/"
        f"{_env('BITBUCKET_WORKSPACE')}/"
        f"{_env('BITBUCKET_REPO_SLUG')}/pullrequests/{pr_id}/request-changes"
    )

    payload = {"message": message}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return True
    except requests.HTTPError as err:
        sys.stderr.write(f"Failed to request changes on PR {pr_id}: {err}\n")
        if hasattr(resp, "text"):
            sys.stderr.write(f"Response: {resp.text}\n")
        return False
    except Exception as exc:
        sys.stderr.write(f"Error requesting changes: {exc}\n")
        return False


def _remove_change_request(pr_id: str) -> bool:
    """Remove change request from a pull request.

    Returns True if successful, False otherwise.
    """
    access_token = os.environ.get("BITBUCKET_ACCESS_TOKEN")
    if not access_token:
        sys.stderr.write(
            "Error: BITBUCKET_ACCESS_TOKEN environment variable not set.\n"
        )
        return False

    url = (
        f"{BB_API_ROOT}/repositories/"
        f"{_env('BITBUCKET_WORKSPACE')}/"
        f"{_env('BITBUCKET_REPO_SLUG')}/pullrequests/{pr_id}/request-changes"
    )

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        resp = requests.delete(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return True
    except requests.HTTPError as err:
        # 404 is expected if no change request exists
        if resp.status_code == 404:
            return True
        sys.stderr.write(f"Failed to remove change request on PR {pr_id}: {err}\n")
        if hasattr(resp, "text"):
            sys.stderr.write(f"Response: {resp.text}\n")
        return False
    except Exception as exc:
        sys.stderr.write(f"Error removing change request: {exc}\n")
        return False


def _extract_issue_summary(issue: dict) -> dict:
    """Extract key information from a security issue.

    Returns a dict with file, line, title, and urgency.
    """
    # Extract location information
    location = issue.get("location", {})
    file_info = location.get("file", {})
    file_path = (
        file_info.get("path") or location.get("file") or issue.get("file") or "unknown"
    )
    line_no = (
        location.get("line_number")
        or location.get("line")
        or location.get("endLine")
        or 0
    )

    # Extract classification details
    classification = issue.get("classification", {})
    title = (
        classification.get("name")
        or issue.get("title")
        or issue.get("ruleId", "Security Issue")
    )

    # Extract urgency
    urgency = issue.get("urgency", "UNKNOWN")

    return {"file": file_path, "line": line_no, "title": title, "urgency": urgency}


def _iter_issue_files(dir_path: pathlib.Path):
    """Iterate over JSON issue files in the directory."""
    for json_file in dir_path.glob("*.json"):
        try:
            data = json.loads(json_file.read_text())
            # Handle both wrapped {"issue": {...}} and direct issue format
            issue = data.get("issue", data) if isinstance(data, dict) else data
            yield issue
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"Skipping invalid JSON {json_file}: {exc}\n")


def _build_change_request_message(issues: list[dict]) -> str:
    """Build a comprehensive change request message from security issues."""
    if not issues:
        return ""

    # Group issues by urgency
    by_urgency = {}
    for issue in issues:
        urgency = issue["urgency"]
        if urgency not in by_urgency:
            by_urgency[urgency] = []
        by_urgency[urgency].append(issue)

    # Build message
    parts = [
        "🔒 **Security Issues Found**",
        "",
        f"Corgea security scan identified **{len(issues)} security issue(s)** that need to be addressed before this PR can be merged.",
        "",
    ]

    # Add urgency-based sections
    urgency_order = ["CR", "HI", "ME", "LO"]  # Critical, High, Medium, Low
    urgency_labels = {"CR": "Critical", "HI": "High", "ME": "Medium", "LO": "Low"}

    for urgency in urgency_order:
        if urgency in by_urgency:
            urgency_issues = by_urgency[urgency]
            urgency_label = urgency_labels.get(urgency, urgency)

            parts.extend(
                [f"### {urgency_label} Priority ({len(urgency_issues)} issue(s))", ""]
            )

            for issue in urgency_issues:
                parts.append(
                    f"- **{issue['title']}** in `{issue['file']}` (line {issue['line']})"
                )

            parts.append("")

    # Add footer
    parts.extend(
        [
            "---",
            "**Next Steps:**",
            "1. Review the security issues identified above",
            "2. Apply the necessary fixes to your code",
            "3. Push your changes to update this pull request",
            "4. The security scan will automatically re-run to verify fixes",
            "",
            "*This change request was automatically generated by Corgea security scanning.*",
        ]
    )

    return "\n".join(parts)


def main(directory: str = "corgea_issues") -> None:  # pragma: no cover
    pr_id = os.environ.get("BITBUCKET_PR_ID")
    if not pr_id:
        sys.stderr.write("No BITBUCKET_PR_ID – not in a PR context, exiting.\n")
        return

    path = pathlib.Path(directory)
    if not path.is_dir():
        raise SystemExit(f"Artifact directory '{directory}' not found")

    # Collect all security issues
    issues = []
    for issue_data in _iter_issue_files(path):
        try:
            issue_summary = _extract_issue_summary(issue_data)
            issues.append(issue_summary)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"Error parsing issue: {exc}\n")
            continue

    print(f"Found {len(issues)} security issue(s) from {directory}")

    if issues:
        # Security issues found - request changes
        message = _build_change_request_message(issues)
        if _request_changes(pr_id, message):
            print(
                f"✅ Requested changes on PR #{pr_id} due to {len(issues)} security issue(s)"
            )

            # Print summary by urgency
            by_urgency = {}
            for issue in issues:
                urgency = issue["urgency"]
                by_urgency[urgency] = by_urgency.get(urgency, 0) + 1

            print("\nIssue breakdown:")
            for urgency, count in sorted(by_urgency.items()):
                print(f"  {urgency}: {count}")
        else:
            print(f"❌ Failed to request changes on PR #{pr_id}")
            sys.exit(1)
    else:
        # No security issues - remove any existing change request
        if _remove_change_request(pr_id):
            print(
                f"✅ No security issues found - removed change request from PR #{pr_id}"
            )
        else:
            print("✅ No security issues found (no change request to remove)")


if __name__ == "__main__":
    dir_arg = sys.argv[1] if len(sys.argv) > 1 else "corgea_issues"
    try:
        main(dir_arg)
    except ConfigError as ce:
        sys.stderr.write(str(ce) + "\n")
        sys.exit(1)
