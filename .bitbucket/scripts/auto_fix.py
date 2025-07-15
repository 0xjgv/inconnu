#!/usr/bin/env python3
# ruff: noqa: S603
"""
Create tasks on a Bitbucket pull request based on Corgea security scan results.

Usage (inside Bitbucket Pipelines step):
  python .bitbucket/scripts/auto_fix.py corgea_issues/

Environment variables used (all provided by Pipelines):
  BITBUCKET_PR_ID          – current PR id (empty when not in PR context)
  BITBUCKET_REPO_SLUG      – repo slug, e.g. "inconnu"
  BITBUCKET_WORKSPACE      – workspace id, e.g. "0xjgv"
  BITBUCKET_ACCESS_TOKEN   – access token for authentication

The script will create tasks on the PR for security issues found:
- Individual detailed tasks for each security issue with fix suggestions
- A summary task with an overview of all security issues found
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


def _create_summary_task(pr_id: str, message: str) -> bool:
    """Create a summary task on a pull request for all security issues.

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
        f"{_env('BITBUCKET_REPO_SLUG')}/pullrequests/{pr_id}/tasks"
    )

    payload = {"content": {"raw": message, "markup": "markdown"}, "pending": True}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return True
    except requests.HTTPError as err:
        sys.stderr.write(f"Failed to create summary task on PR {pr_id}: {err}\n")
        if hasattr(resp, "text"):
            sys.stderr.write(f"Response: {resp.text}\n")
        return False
    except Exception as exc:
        sys.stderr.write(f"Error creating summary task: {exc}\n")
        return False


def _create_inline_comment(
    pr_id: str, content: str, file_path: str, line_number: int
) -> int | None:
    """Create an inline comment on a pull request.

    Args:
        pr_id: Pull request ID
        content: Comment content
        file_path: File path for the inline comment
        line_number: Line number for the inline comment

    Returns comment ID if successful, None otherwise.
    """
    access_token = os.environ.get("BITBUCKET_ACCESS_TOKEN")
    if not access_token:
        sys.stderr.write(
            "Error: BITBUCKET_ACCESS_TOKEN environment variable not set.\n"
        )
        return None

    url = (
        f"{BB_API_ROOT}/repositories/"
        f"{_env('BITBUCKET_WORKSPACE')}/"
        f"{_env('BITBUCKET_REPO_SLUG')}/pullrequests/{pr_id}/comments"
    )

    payload = {
        "content": {"raw": content},
        "inline": {"from": line_number, "to": line_number, "path": file_path},
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        comment_data = resp.json()
        return comment_data.get("id")
    except requests.HTTPError as err:
        sys.stderr.write(f"Failed to create inline comment on PR {pr_id}: {err}\n")
        if hasattr(resp, "text"):
            sys.stderr.write(f"Response: {resp.text}\n")
        return None
    except Exception as exc:
        sys.stderr.write(f"Error creating inline comment: {exc}\n")
        return None


def _create_task(pr_id: str, content: str, comment_id: int | None = None) -> bool:
    """Create a task on a pull request, optionally linked to a comment.

    Args:
        pr_id: Pull request ID
        content: Task content
        comment_id: Optional comment ID to link the task to

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
        f"{_env('BITBUCKET_REPO_SLUG')}/pullrequests/{pr_id}/tasks"
    )

    payload = {"content": {"raw": content, "markup": "markdown"}, "pending": True}

    # Link to comment if provided
    if comment_id:
        payload["comment"] = {"id": comment_id}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return True
    except requests.HTTPError as err:
        sys.stderr.write(f"Failed to create task on PR {pr_id}: {err}\n")
        if hasattr(resp, "text"):
            sys.stderr.write(f"Response: {resp.text}\n")
        return False
    except Exception as exc:
        sys.stderr.write(f"Error creating task: {exc}\n")
        return False


def _create_comment_and_task(pr_id: str, issue: dict) -> bool:
    """Create an inline comment and linked task for a security issue.

    Args:
        pr_id: Pull request ID
        issue: Dict containing comprehensive issue information

    Returns True if both comment and task created successfully, False otherwise.
    """
    # Step 1: Create inline comment with concise issue details
    comment_content = _build_inline_comment_content(issue)
    comment_id = _create_inline_comment(
        pr_id, comment_content, issue["file"], issue["line"]
    )

    if not comment_id:
        # Fallback: create standalone task if comment creation fails
        sys.stderr.write(
            f"Failed to create inline comment for issue {issue['issue_id']}, creating standalone task\n"
        )
        task_content = _build_task_content(issue)
        return _create_task(pr_id, task_content)

    # Step 2: Create detailed task linked to the comment
    task_content = _build_task_content(issue)
    return _create_task(pr_id, task_content, comment_id)


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


def _extract_full_issue(issue: dict) -> dict:
    """Extract comprehensive information from a security issue for task creation.

    Returns a dict with all relevant issue information including auto-fix suggestions.
    """
    # Get the basic summary first
    summary = _extract_issue_summary(issue)

    # Extract additional detailed information
    classification = issue.get("classification", {})
    details = issue.get("details", {})
    auto_fix = issue.get("auto_fix_suggestion", {})
    location = issue.get("location", {})
    file_info = location.get("file", {})
    project_info = location.get("project", {})
    auto_triage = issue.get("auto_triage", {})
    false_positive = auto_triage.get("false_positive_detection", {})

    # Build comprehensive issue data
    full_issue = {
        **summary,
        "issue_id": issue.get("id", "unknown"),
        "scan_id": issue.get("scan_id", ""),
        "status": issue.get("status", ""),
        "created_at": issue.get("created_at", ""),
        "description": classification.get("description", ""),
        "explanation": details.get("explanation", ""),
        "cwe_id": classification.get("id", ""),
        "file_name": file_info.get("name", ""),
        "file_language": file_info.get("language", ""),
        "project_name": project_info.get("name", ""),
        "project_branch": project_info.get("branch", ""),
        "git_sha": project_info.get("git_sha", ""),
        "triage_status": false_positive.get("status", ""),
        "triage_reasoning": false_positive.get("reasoning", ""),
        "has_auto_fix": auto_fix.get("status") == "fix_available",
    }

    # Add auto-fix information if available
    if full_issue["has_auto_fix"]:
        patch = auto_fix.get("patch", {})
        full_issue.update(
            {
                "fix_id": auto_fix.get("id", ""),
                "fix_explanation": patch.get("explanation", ""),
                "fix_diff": patch.get("diff", ""),
            }
        )

    return full_issue


def _build_inline_comment_content(issue: dict) -> str:
    """Build concise inline comment content for diff view.

    Args:
        issue: Dict containing comprehensive issue information from _extract_full_issue

    Returns:
        Formatted inline comment content string
    """
    urgency_labels = {"CR": "🔴", "HI": "🟠", "ME": "🟡", "LO": "🟢"}
    urgency_emoji = urgency_labels.get(issue["urgency"], "⚪")

    parts = [
        f"## {urgency_emoji} Security Issue: {issue['title']}",
        "",
        f"**{issue['cwe_id']}** - {issue.get('description', 'Security vulnerability detected')}",
        "",
    ]

    # Add collapsible detailed explanation
    if issue.get("explanation"):
        # Clean up HTML for better markdown display
        explanation = (
            issue["explanation"].replace("<br><br>", "\n\n").replace("<br>", "\n")
        )
        explanation = explanation.replace("<code>", "`").replace("</code>", "`")

        parts.extend(
            [
                "---",
                "",
                "### 📋 Detailed Explanation",
                "",
                explanation,
                "",
            ]
        )

    # Add fix if available
    if (
        issue.get("has_auto_fix")
        and issue.get("fix_diff")
        and issue["fix_diff"].strip()
    ):
        parts.extend(
            [
                "---",
                "",
                "### 🔧 Suggested Fix",
                "",
                "**Fix explanation:**",
                issue.get("fix_explanation", "Auto-fix available"),
                "---",
                "",
                "**📊 Changes (diff view):**",
                "```diff",
                issue["fix_diff"].strip(),
                "```",
                "---",
                "",
                "**📥 Apply this fix:**",
                "",
                f"1. [Download patch file](https://www.corgea.app/issue/fix-diff/{issue['issue_id']}?download=true)",
                "",
                "2. Apply it: `git apply corgea-fix-{}.patch`".format(
                    issue["issue_id"][:8]
                ),
                "",
            ]
        )

    parts.extend(
        [f"🔗 **[View on Corgea](https://www.corgea.app/issue/{issue['issue_id']}/)**"]
    )

    return "\n".join(filter(None, parts))


def _build_task_content(issue: dict) -> str:
    """Build task content from a detailed security issue.

    Args:
        issue: Dict containing comprehensive issue information from _extract_full_issue

    Returns:
        Formatted task content string
    """
    urgency_labels = {
        "CR": "🔴 Critical",
        "HI": "🟠 High",
        "ME": "🟡 Medium",
        "LO": "🟢 Low",
    }
    urgency_label = urgency_labels.get(issue["urgency"], f"⚪ {issue['urgency']}")

    content_parts = [
        f"## {urgency_label}: {issue['title']}",
        "",
        f"**File:** `{issue['file']}` (line {issue['line']})",
        f"**CWE:** {issue['cwe_id']}" if issue["cwe_id"] else "",
        f"**Language:** {issue['file_language']}" if issue.get("file_language") else "",
        f"**Issue ID:** `{issue['issue_id']}`",
        f"**Scan ID:** `{issue['scan_id']}`" if issue.get("scan_id") else "",
        "",
    ]

    # Add project context if available
    project_info = []
    if issue.get("project_name"):
        project_info.append(f"**Project:** {issue['project_name']}")
    if issue.get("project_branch"):
        project_info.append(f"**Branch:** {issue['project_branch']}")
    if issue.get("git_sha"):
        project_info.append(f"**Commit:** `{issue['git_sha'][:8]}...`")
    if issue.get("created_at"):
        project_info.append(f"**Detected:** {issue['created_at']}")

    if project_info:
        content_parts.extend(project_info)
        content_parts.append("")

    # Add triage information if available
    if issue.get("triage_status"):
        triage_emoji = "✅" if issue["triage_status"] == "valid" else "⚠️"
        content_parts.extend(
            [
                f"### {triage_emoji} Auto-Triage: {issue['triage_status'].title()}",
                issue.get("triage_reasoning", ""),
                "",
            ]
        )

    # Add description if available
    if issue.get("description"):
        content_parts.extend(
            [
                "### Description",
                issue["description"],
                "",
            ]
        )

    # Add detailed explanation if available
    if issue.get("explanation"):
        content_parts.extend(
            [
                "### Technical Details",
                issue["explanation"],
                "",
            ]
        )

    # Add auto-fix suggestion if available
    if issue.get("has_auto_fix"):
        content_parts.extend(
            [
                "### 🔧 Suggested Fix",
                issue.get("fix_explanation", "Auto-fix available"),
                "",
            ]
        )

        if issue.get("fix_id"):
            content_parts.extend(
                [
                    f"**Fix ID:** `{issue['fix_id']}`",
                    "",
                ]
            )

        if issue.get("fix_diff") and issue["fix_diff"].strip():
            # Use language-specific syntax highlighting if available, otherwise default to diff
            diff_language = issue.get("file_language", "diff")
            content_parts.extend(
                [
                    "### Proposed Changes",
                    f"```{diff_language}",
                    issue["fix_diff"].strip(),
                    "```",
                    "",
                ]
            )

    content_parts.extend(
        [
            "---",
            "**Action Required:** Review and apply the necessary security fixes for this issue.",
            "",
            f"🔗 **[View Full Issue Details on Corgea](https://www.corgea.app/issue/{issue['issue_id']}/)**",
            "",
            "*Generated by Corgea Security Scan*",
        ]
    )

    return "\n".join(filter(None, content_parts))


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


def _build_summary_task_message(issues: list[dict]) -> str:
    """Build a comprehensive summary task message from security issues."""
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
            "2. Check the individual tasks created for each issue with detailed fix suggestions",
            "3. Apply the necessary fixes to your code",
            "4. Push your changes to update this pull request",
            "5. The security scan will automatically re-run to verify fixes",
            "",
            "*This summary task was automatically generated by Corgea security scanning.*",
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

    # Collect all security issues with full details
    issues = []
    full_issues = []
    for issue_data in _iter_issue_files(path):
        try:
            issue_summary = _extract_issue_summary(issue_data)
            full_issue = _extract_full_issue(issue_data)
            issues.append(issue_summary)
            full_issues.append(full_issue)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"Error parsing issue: {exc}\n")
            continue

    print(f"Found {len(issues)} security issue(s) from {directory}")

    if issues:
        # Create individual inline comments and tasks for each issue
        task_success_count = 0
        comment_success_count = 0
        for full_issue in full_issues:
            if _create_comment_and_task(pr_id, full_issue):
                task_success_count += 1
                # Check if it has valid file/line for inline comment
                if (
                    full_issue.get("file")
                    and full_issue.get("line")
                    and full_issue["line"] > 0
                ):
                    comment_success_count += 1
            else:
                sys.stderr.write(
                    f"Failed to create comment and task for issue {full_issue['issue_id']}\n"
                )

        if comment_success_count > 0:
            print(
                f"✅ Created {comment_success_count} inline comments with linked tasks and {task_success_count - comment_success_count} standalone tasks ({task_success_count}/{len(full_issues)} total)"
            )
        else:
            print(
                f"✅ Created {task_success_count}/{len(full_issues)} standalone tasks for individual issues"
            )

        # Security issues found - create summary task
        message = _build_summary_task_message(issues)
        if _create_summary_task(pr_id, message):
            print(
                f"✅ Created summary task on PR #{pr_id} for {len(issues)} security issue(s)"
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
            print(f"❌ Failed to create summary task on PR #{pr_id}")
            sys.exit(1)
    else:
        # No security issues found
        print("✅ No security issues found - no tasks created")


if __name__ == "__main__":
    dir_arg = sys.argv[1] if len(sys.argv) > 1 else "corgea_issues"
    try:
        main(dir_arg)
    except ConfigError as ce:
        sys.stderr.write(str(ce) + "\n")
        sys.exit(1)
