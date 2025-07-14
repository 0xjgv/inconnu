#!/usr/bin/env python3
"""
Post a setup comment to the PR explaining how to configure authentication.
This is an MVP solution that works without authentication.
"""

import os
import sys


def main():
    pr_id = os.environ.get("BITBUCKET_PR_ID")
    if not pr_id:
        print("Not in a PR context, skipping setup comment.")
        return

    # Check if authentication is already configured
    auth_configured = bool(
        (os.environ.get("BB_API_USER") and os.environ.get("BB_API_TOKEN"))
        or os.environ.get("BITBUCKET_REPO_ACCESS_TOKEN")
    )

    if auth_configured:
        print("✅ Authentication is configured - skipping setup instructions.")
        return

    workspace = os.environ.get("BITBUCKET_WORKSPACE", "unknown")
    repo = os.environ.get("BITBUCKET_REPO_SLUG", "unknown")

    print("\n" + "=" * 60)
    print("🔧 CORGEA SCAN SETUP REQUIRED")
    print("=" * 60)
    print(f"\nPR #{pr_id} in {workspace}/{repo}")
    print("\nCorgea scan found security issues but cannot post inline comments")
    print("because authentication is not configured.")
    print("\nTo enable inline PR comments, configure one of these options:")
    print("\n1. App Password (Recommended):")
    print("   - Go to: https://bitbucket.org/account/settings/app-passwords/")
    print("   - Create an app password with 'Pull requests: Write' permission")
    print("   - Add these as repository variables:")
    print("     * BB_API_USER = your-username")
    print("     * BB_API_TOKEN = your-app-password (mark as secured)")
    print("\n2. Repository Access Token:")
    print("   - Go to repository settings > Access tokens")
    print("   - Create a token with PR write permissions")
    print("   - Add as repository variable:")
    print("     * BITBUCKET_REPO_ACCESS_TOKEN = your-token (mark as secured)")
    print(
        "\nFor more info: https://support.atlassian.com/bitbucket-cloud/docs/variables-and-secrets/"
    )
    print("\nOnce configured, re-run the pipeline to see inline security comments.")
    print("=" * 60 + "\n")

    # Check if issues were found
    issues_dir = sys.argv[1] if len(sys.argv) > 1 else "corgea_issues"
    if os.path.isdir(issues_dir):
        import pathlib

        issue_files = list(pathlib.Path(issues_dir).glob("*.json"))
        if issue_files:
            print(f"📊 Found {len(issue_files)} security issues in this scan.")
            print("   Configure authentication to see detailed inline comments.\n")


if __name__ == "__main__":
    main()
