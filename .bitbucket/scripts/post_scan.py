#!/usr/bin/env python3
# ruff: noqa: S603
"""
Post Corgea (or any JSON) issues from the pipeline *artifacts* directory to
Bitbucket Cloud as inline comments with "Apply suggestion" blocks.

Usage (inside Bitbucket Pipelines step):
  python .bitbucket/scripts/post_scan.py corgea_issues/

Environment variables used (all provided by Pipelines):
  BITBUCKET_PR_ID          – current PR id (empty when not in PR context)
  BITBUCKET_REPO_SLUG      – repo slug, e.g. "inconnu"
  BITBUCKET_WORKSPACE      – workspace id, e.g. "0xjgv"

Authentication (automatically detected, no setup required):
  BITBUCKET_REPO_ACCESS_TOKEN – Built-in repository access token (preferred)
  OAUTH_TOKEN                 – Built-in OAuth token (fallback)

  Note: These tokens are automatically provided by Bitbucket Pipelines with
  appropriate permissions for the current repository and PR operations.

Optional configuration:
  BB_SUGGESTION_FORMAT     – "enhanced" (default) or "raw" for comment format
  BB_USE_SUGGESTION_BLOCKS – "true" to use ```suggestion blocks (Bitbucket Server only)
  BB_AUTO_COMMIT_FIXES     – "true" to automatically apply and commit fixes (default: false)

If executed outside Pipelines you can export the variables manually for testing.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile

import requests

__all__ = ["main"]

BB_API_ROOT = "https://api.bitbucket.org/2.0"

# Configuration options
USE_SUGGESTION_BLOCKS = (
    os.environ.get("BB_USE_SUGGESTION_BLOCKS", "false").lower() == "true"
)
SUGGESTION_FORMAT = os.environ.get(
    "BB_SUGGESTION_FORMAT", "enhanced"
)  # enhanced or raw
AUTO_COMMIT_FIXES = os.environ.get("BB_AUTO_COMMIT_FIXES", "false").lower() == "true"


class ConfigError(RuntimeError):
    """Raised when required environment variables are missing."""


def _env(key: str) -> str:
    try:
        return os.environ[key]
    except KeyError as exc:
        raise ConfigError(f"Missing required env-var: {key}") from exc


def _create_comment(pr_id: str, inline_path: str, line: int, text: str) -> bool:
    """POST an inline comment to Bitbucket Cloud.

    Returns True if successful, False otherwise.
    """
    # Get authentication token from Bitbucket Pipelines built-in variables
    try:
        # Try repository access token first (preferred)
        repo_token = os.environ.get("BITBUCKET_REPO_ACCESS_TOKEN")
        if repo_token:
            headers = {"Authorization": f"Bearer {repo_token}"}
            auth = None
        else:
            # Fallback to OAuth token
            oauth_token = os.environ.get("OAUTH_TOKEN")
            if oauth_token:
                headers = {"Authorization": f"Bearer {oauth_token}"}
                auth = None
            else:
                sys.stderr.write(
                    "Warning: No authentication token found. Expected BITBUCKET_REPO_ACCESS_TOKEN or OAUTH_TOKEN.\n"
                )
                return False
    except Exception as exc:
        sys.stderr.write(f"Error getting authentication token: {exc}\n")
        return False

    url = (
        f"{BB_API_ROOT}/repositories/"
        f"{_env('BITBUCKET_WORKSPACE')}/"
        f"{_env('BITBUCKET_REPO_SLUG')}/pullrequests/{pr_id}/comments"
    )

    payload: dict = {
        "inline": {"path": inline_path, "to": line},
        "content": {"raw": text},
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return True
    except requests.HTTPError as err:
        sys.stderr.write(
            f"Failed to comment on {inline_path}:{line}: {err}\n" + resp.text + "\n"
        )
        return False
    except Exception as exc:
        sys.stderr.write(f"Error posting comment: {exc}\n")
        return False


# ---------------------------------------------------------------------------
# Diff parsing helpers
# ---------------------------------------------------------------------------


def _parse_unified_diff(diff_text: str) -> tuple[list[str], list[str]] | None:
    """Parse unified diff format and extract the old and new code sections.

    Returns:
        Tuple of (old_lines, new_lines) or None if parsing fails
    """
    if not diff_text:
        return None

    lines = diff_text.strip().split("\n")
    old_lines = []
    new_lines = []

    # Skip header lines (---, +++, @@)
    in_diff = False
    for line in lines:
        if line.startswith("@@"):
            in_diff = True
            continue
        if not in_diff:
            continue

        if line.startswith("-") and not line.startswith("---"):
            # Line removed (part of old code)
            old_lines.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            # Line added (part of new code)
            new_lines.append(line[1:])
        elif line.startswith(" "):
            # Context line (appears in both)
            old_lines.append(line[1:])
            new_lines.append(line[1:])
        # Skip lines that don't start with +, -, or space (like @@ lines)

    return (old_lines, new_lines) if old_lines or new_lines else None


def _format_code_suggestion(
    title: str,
    description: str,
    urgency: str | None,
    diff_text: str | None,
    explanation: str | None,
    line_number: int,
) -> str:
    """Format a code suggestion comment with clear before/after sections."""
    msg_parts = [f"**{title}**", "", description]

    # Add urgency if available
    if urgency:
        msg_parts.append("")
        msg_parts.append(f"**Urgency:** {urgency}")

    # Add code suggestion if available
    if diff_text:
        if SUGGESTION_FORMAT == "raw" or USE_SUGGESTION_BLOCKS:
            # Use raw format or suggestion blocks for Bitbucket Server
            msg_parts.extend(
                [
                    "",
                    "**Auto-fix available:**",
                ]
            )
            if USE_SUGGESTION_BLOCKS:
                msg_parts.append(f"```suggestion\n{diff_text}\n```")
            else:
                msg_parts.append(f"```diff\n{diff_text}\n```")
            if explanation:
                msg_parts.extend(["", "**Explanation:**", explanation])
        else:
            # Use enhanced format with parsed diff
            parsed_diff = _parse_unified_diff(diff_text)
            if parsed_diff:
                old_code, new_code = parsed_diff

                msg_parts.extend(
                    [
                        "",
                        "**🔧 Suggested Fix:**",
                        "",
                        f"Replace the following code at line {line_number}:",
                        "```python",
                        "# Current code (REMOVE):",
                    ]
                )
                msg_parts.extend(old_code)
                msg_parts.append("```")

                msg_parts.extend(
                    [
                        "",
                        "With:",
                        "```python",
                        "# Fixed code (ADD):",
                    ]
                )
                msg_parts.extend(new_code)
                msg_parts.append("```")

                if explanation:
                    msg_parts.extend(["", "**Why this fix:**", explanation])
            else:
                # Fallback to raw diff if parsing fails
                msg_parts.extend(
                    ["", "**Auto-fix available:**", "```diff", diff_text, "```"]
                )
                if explanation:
                    msg_parts.extend(["", "**Explanation:**", explanation])

    return "\n".join(msg_parts)


# ---------------------------------------------------------------------------
# Git operations for applying fixes
# ---------------------------------------------------------------------------


def _apply_diff_to_file(file_path: str, diff_text: str) -> bool:
    """Apply a unified diff to a file using git apply.

    Returns True if successful, False otherwise.
    """
    try:
        # Create a temporary file with the diff
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".patch", delete=False
        ) as tmp:
            tmp.write(diff_text)
            tmp_path = tmp.name

        # Apply the patch
        result = subprocess.run(
            ["/usr/bin/git", "apply", "--whitespace=fix", tmp_path],
            capture_output=True,
            text=True,
        )

        # Clean up
        os.unlink(tmp_path)

        if result.returncode != 0:
            sys.stderr.write(f"Failed to apply patch to {file_path}: {result.stderr}\n")
            return False

        return True
    except Exception as exc:
        sys.stderr.write(f"Error applying diff to {file_path}: {exc}\n")
        return False


def _commit_changes(message: str, files: list[str]) -> bool:
    """Create a commit with the specified files and message.

    Returns True if successful, False otherwise.
    """
    try:
        # Stage the files
        result = subprocess.run(
            ["/usr/bin/git", "add"] + files, capture_output=True, text=True
        )

        if result.returncode != 0:
            sys.stderr.write(f"Failed to stage files: {result.stderr}\n")
            return False

        # Create the commit
        result = subprocess.run(
            ["/usr/bin/git", "commit", "-m", message], capture_output=True, text=True
        )

        if result.returncode != 0:
            sys.stderr.write(f"Failed to commit: {result.stderr}\n")
            return False

        print(f"Created commit: {message}")
        return True
    except Exception as exc:
        sys.stderr.write(f"Error creating commit: {exc}\n")
        return False


def _push_changes() -> bool:
    """Push the current branch to origin.

    Returns True if successful, False otherwise.
    """
    try:
        # Get current branch name
        result = subprocess.run(
            ["/usr/bin/git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            sys.stderr.write(f"Failed to get current branch: {result.stderr}\n")
            return False

        branch = result.stdout.strip()

        # Push to origin
        result = subprocess.run(
            ["/usr/bin/git", "push", "origin", branch],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            sys.stderr.write(f"Failed to push branch {branch}: {result.stderr}\n")
            return False

        print(f"Pushed changes to branch: {branch}")
        return True
    except Exception as exc:
        sys.stderr.write(f"Error pushing changes: {exc}\n")
        return False


# ---------------------------------------------------------------------------
# Issue parsing helpers – tailor these according to your scanner's schema.
# ---------------------------------------------------------------------------


def _extract(issue: dict) -> tuple[str, int, str, str | None, str | None]:
    """Return (file, line, message, diff, issue_id) tuple.

    The function is *schema-aware*: adapt the keys if your scanner changes.
    """
    # Extract issue ID
    issue_id = issue.get("id")

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

    # Extract urgency
    urgency = issue.get("urgency")

    # Extract auto-fix suggestion if available
    auto_fix = issue.get("auto_fix_suggestion", {})
    explanation = None
    diff_text = None

    if auto_fix.get("status") == "fix_available":
        patch = auto_fix.get("patch", {})
        explanation = patch.get("explanation", "")
        diff_text = patch.get("diff")

    # Use the new formatting function
    msg = _format_code_suggestion(
        explanation=explanation,
        description=description,
        line_number=line_no,
        diff_text=diff_text,
        urgency=urgency,
        title=title,
    )

    return file_path, int(line_no), msg, diff_text, issue_id


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
    comment_count = 0
    fixed_files = []
    fixes_applied = []

    # Check if authentication is configured
    auth_configured = bool(
        os.environ.get("BITBUCKET_REPO_ACCESS_TOKEN") or os.environ.get("OAUTH_TOKEN")
    )

    for issue_data in _iter_issue_files(path):
        try:
            # Handle both wrapped {"issue": {...}} and direct issue format
            issue = (
                issue_data.get("issue", issue_data)
                if isinstance(issue_data, dict)
                else issue_data
            )
            file_path, line, message, diff_text, issue_id = _extract(issue)
        except Exception as exc:  # noqa: BLE001 – we need robustness here
            sys.stderr.write(f"Error parsing issue JSON: {exc}\n")
            continue

        issue_count += 1

        # Try to post comment
        if _create_comment(pr_id, file_path, line, message):
            comment_count += 1

        # Apply fix if auto-commit is enabled and diff is available
        if AUTO_COMMIT_FIXES and diff_text:
            if _apply_diff_to_file(file_path, diff_text):
                fixed_files.append(file_path)
                fixes_applied.append(
                    {"file": file_path, "issue_id": issue_id, "line": line}
                )
                print(f"Applied fix to {file_path} (line {line})")
            else:
                print(f"Failed to apply fix to {file_path}")

    # Print summary
    if not auth_configured:
        print(f"\n⚠️  Processed {issue_count} security issues from {directory}")
        print("   No authentication tokens found - unable to post PR comments.")
        print(
            "   This should not happen in Bitbucket Pipelines. Check repository settings."
        )
    else:
        print(
            f"\n✅ Posted {comment_count}/{issue_count} Bitbucket comments from {directory}"
        )

    # Commit and push fixes if any were applied
    if AUTO_COMMIT_FIXES and fixes_applied:
        # Group fixes by file for commit message
        files_summary = {}
        for fix in fixes_applied:
            if fix["file"] not in files_summary:
                files_summary[fix["file"]] = []
            files_summary[fix["file"]].append(f"line {fix['line']}")

        # Create commit message
        commit_lines = ["fix: Apply Corgea security fixes", ""]
        for file, lines in files_summary.items():
            commit_lines.append(f"- {file}: {', '.join(lines)}")
        commit_lines.append("")
        commit_lines.append(f"Applied {len(fixes_applied)} fixes from Corgea scan")
        commit_message = "\n".join(commit_lines)

        if _commit_changes(commit_message, list(set(fixed_files))):
            print(f"Committed {len(fixes_applied)} fixes")
            if _push_changes():
                print("Successfully pushed fixes to remote")
            else:
                print("Failed to push changes - manual push may be required")
        else:
            print("Failed to commit fixes")


if __name__ == "__main__":
    dir_arg = sys.argv[1] if len(sys.argv) > 1 else "corgea_issues"
    try:
        main(dir_arg)
    except ConfigError as ce:
        sys.stderr.write(str(ce) + "\n")
        sys.exit(1)
