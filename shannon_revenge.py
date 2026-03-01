#!/usr/bin/env python3
"""
ShannonRevenge - GitHub Scanner for Claude-Generated Code

Identifies repositories with Claude in their supply chain by detecting
Claude signatures in commits and code.
"""

import argparse
import base64
import os
import sys
from typing import Optional
from dotenv import load_dotenv
from github_client import GitHubAPIClient

load_dotenv()
from detector import ClaudeDetector, ClaudeDetection
from output_formatter import OutputFormatter

CODE_SEARCH_QUERIES = [
    '"noreply@anthropic.com" in:file',
    '"Generated with [Claude Code]" in:file',
    '"TODO(claude)" in:file',
    '"TODO(human)" in:file',
    '"Co-Authored-By: Claude" in:file',
    'filename:CLAUDE.md',
    'path:.claude filename:settings.json',
]


def scan_repository(owner: str, repo: str, token: Optional[str] = None,
                    max_commits: int = 1000, detector: Optional[ClaudeDetector] = None,
                    since: Optional[str] = None, deep: bool = False):
    """
    Scan a single repository for Claude signatures.

    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub API token
        max_commits: Maximum number of commits to scan (ignored when since is set)
        detector: Optional existing detector to use
        since: Only scan commits after this ISO 8601 date (e.g. 2025-02-24T00:00:00Z)
        deep: Enable deep scanning (code search + file content fetch)
    """
    print(f"\n[*] Scanning repository: {owner}/{repo}")

    client = GitHubAPIClient(token)
    if detector is None:
        detector = ClaudeDetector()

    try:
        repo_info = client.get_repo_info(owner, repo)
        print(f"[*] Repository: {repo_info.get('full_name')}")
        print(f"[*] Description: {repo_info.get('description', 'N/A')}")
        print(f"[*] Stars: {repo_info.get('stargazers_count', 0)}")

        # Layer 1: File tree check (always on, 1 API call)
        print(f"[*] Checking file tree for Claude-specific files...")
        file_signal_count = scan_repo_file_signals(owner, repo, client, detector)
        if file_signal_count:
            print(f"[*] File tree: {file_signal_count} signal(s) found")
        else:
            print(f"[*] File tree: no Claude-specific files found")

        if since:
            print(f"[*] Scanning all commits since {since}...")
        else:
            print(f"[*] Scanning commits...")

        commit_count = 0
        detection_count = 0

        for commit in client.get_repo_commits(owner, repo, since=since):
            commit_count += 1

            # Analyze commit message first (no extra API call needed)
            detection = detector.analyze_commit(commit, owner, repo)

            # Layer 3: Author name check (always on, no extra API call)
            author_detection = detector.analyze_author_name(commit, owner, repo)
            if author_detection:
                detection_count += 1
                sha_prefix = author_detection.commit_sha[:8] if author_detection.commit_sha else "n/a"
                print(f"[!] DETECTION (author): {sha_prefix} - {author_detection.detection_type}")

            if detection:
                detection_count += 1
                print(f"[!] DETECTION: {detection.commit_sha[:8]} - {detection.detection_type}")
                # Backfill files_modified from the detail endpoint only when needed
                try:
                    commit_detail = client.get_commit_detail(owner, repo, commit["sha"])
                    detection.files_modified = [f.get("filename", "") for f in commit_detail.get("files", [])]
                except Exception:
                    pass

            if not since and commit_count >= max_commits:
                print(f"[*] Reached maximum commit limit ({max_commits})")
                break

            if commit_count % 50 == 0:
                print(f"[*] Scanned {commit_count} commits, found {detection_count} detections")

        # Layer 2 + 4: Deep code search (gated by --deep)
        if deep:
            print(f"[*] Running deep code search scan...")
            search_count = scan_repo_code_search(owner, repo, client, detector, fetch_content=True)
            if search_count:
                print(f"[*] Code search: {search_count} detection(s) found")
            else:
                print(f"[*] Code search: no additional detections found")

        print(f"\n[*] Scan complete: {commit_count} commits scanned, {detection_count} detections found")

        return detector

    except Exception as e:
        print(f"[!] Error scanning repository: {e}")
        return None


def scan_repo_file_signals(owner: str, repo: str, client: GitHubAPIClient,
                           detector: ClaudeDetector) -> int:
    """
    Fetch the repo file tree and check for Claude-specific files.

    Returns count of file signal detections found.
    """
    tree = client.get_repo_tree(owner, repo)
    new_detections = detector.analyze_file_tree(tree, owner, repo)
    for d in new_detections:
        print(f"[!] DETECTION (file): {d.evidence}")
    return len(new_detections)


def scan_repo_code_search(owner: str, repo: str, client: GitHubAPIClient,
                          detector: ClaudeDetector, fetch_content: bool = True) -> int:
    """
    Run CODE_SEARCH_QUERIES scoped to this repo and create detections for hits.

    Returns count of new detections created.
    """
    repo_full = f"{owner}/{repo}"
    seen_files: set = set()
    new_detection_count = 0

    for query in CODE_SEARCH_QUERIES:
        try:
            for hit in client.search_code(query, repo=repo_full):
                file_path = hit.get("path", "")
                if file_path in seen_files:
                    continue
                seen_files.add(file_path)

                detection_created = False

                if fetch_content:
                    file_data = client.get_file_content(owner, repo, file_path)
                    if file_data and file_data.get("encoding") == "base64":
                        try:
                            content = base64.b64decode(file_data["content"]).decode("utf-8", errors="replace")
                            # Use a minimal stub commit for context
                            stub_commit = {
                                "sha": "",
                                "html_url": hit.get("html_url", ""),
                                "commit": {"author": {}, "message": ""},
                            }
                            code_detection = detector.analyze_code_content(
                                content, stub_commit, owner, repo, file_path
                            )
                            if code_detection:
                                new_detection_count += 1
                                print(f"[!] DETECTION (code search): {file_path} matched code pattern")
                                detection_created = True
                        except Exception:
                            pass

                if not detection_created:
                    # Fallback: record the search hit itself as evidence
                    detection = ClaudeDetection(
                        repo_owner=owner,
                        repo_name=repo,
                        commit_sha="",
                        commit_url=hit.get("html_url", ""),
                        author="",
                        author_email="",
                        commit_date="",
                        commit_message="",
                        detection_type="code_search_hit",
                        evidence=f"Code search query '{query}' matched file: {file_path}",
                        files_modified=[file_path],
                    )
                    detector.detections.append(detection)
                    new_detection_count += 1
                    print(f"[!] DETECTION (code search hit): {file_path}")

        except Exception as e:
            print(f"[!] Code search query failed ({query!r}): {e}")

    return new_detection_count


def scan_user_repositories(username: str, token: Optional[str] = None, max_repos: int = 10,
                            max_commits_per_repo: int = 100, detector: Optional[ClaudeDetector] = None,
                            since: Optional[str] = None, deep: bool = False):
    """
    Scan all repositories for a user.

    Args:
        username: GitHub username
        token: GitHub API token
        max_repos: Maximum number of repositories to scan
        max_commits_per_repo: Maximum commits per repository
        detector: Optional existing detector to use
        since: Only scan commits after this ISO 8601 date
        deep: Enable deep scanning (code search + file content fetch)
    """
    print(f"\n[*] Scanning repositories for user: {username}")

    client = GitHubAPIClient(token)
    if detector is None:
        detector = ClaudeDetector()

    try:
        repos = []
        for i, repo in enumerate(client.search_repositories(f"user:{username}")):
            repos.append(repo)
            if len(repos) >= max_repos:
                break
        print(f"[*] Found {len(repos)} repositories")

        for i, repo in enumerate(repos, 1):
            owner = repo["owner"]["login"]
            name = repo["name"]

            print(f"\n[{i}/{len(repos)}] Scanning {owner}/{name}")

            scan_repository(owner, name, token, max_commits_per_repo, detector, since=since, deep=deep)

        return detector

    except Exception as e:
        print(f"[!] Error scanning user repositories: {e}")
        return None


def scan_organization(org: str, token: Optional[str] = None, max_repos: int = 20,
                      max_commits_per_repo: int = 100, detector: Optional[ClaudeDetector] = None,
                      since: Optional[str] = None, deep: bool = False):
    """
    Scan all repositories for an organization.

    Args:
        org: Organization name
        token: GitHub API token
        max_repos: Maximum number of repositories to scan (ignored when since is set)
        max_commits_per_repo: Maximum commits per repository
        detector: Optional existing detector to use
        since: Only scan commits after this ISO 8601 date (scans all repos when set)
        deep: Enable deep scanning (code search + file content fetch)
    """
    print(f"\n[*] Scanning organization: {org}")

    client = GitHubAPIClient(token)
    if detector is None:
        detector = ClaudeDetector()

    try:
        org_info = client.get_org_info(org)
        print(f"[*] Organization: {org_info.get('name', org)}")
        print(f"[*] Description: {org_info.get('description', 'N/A')}")
        print(f"[*] Public repos: {org_info.get('public_repos', 0)}")

        repos = []
        for repo in client.get_org_repos(org):
            # When filtering by date, skip repos with no pushes since that date
            if since and repo.get("pushed_at", "") < since:
                continue
            repos.append(repo)
            if not since and len(repos) >= max_repos:
                break

        print(f"[*] Scanning {len(repos)} repositories")

        for i, repo in enumerate(repos, 1):
            owner = repo["owner"]["login"]
            name = repo["name"]

            print(f"\n[{i}/{len(repos)}] Scanning {owner}/{name}")

            scan_repository(owner, name, token, max_commits_per_repo, detector, since=since, deep=deep)

        return detector

    except Exception as e:
        print(f"[!] Error scanning organization: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="ShannonRevenge - Scan GitHub for Claude-generated code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan a single repository
  %(prog)s --repo owner/repo

  # Scan with GitHub token (recommended for higher rate limits)
  %(prog)s --repo owner/repo --token YOUR_TOKEN

  # Scan all repos for a user
  %(prog)s --user username --max-repos 5

  # Scan an organization
  %(prog)s --org organization --max-repos 20

  # Scan all commits since Claude Code launched
  %(prog)s --org lmco --since 2025-02-24T00:00:00Z

  # Deep scan with code search
  %(prog)s --repo owner/repo --deep --max-commits 10

  # Use custom detection patterns
  %(prog)s --repo owner/repo --patterns patterns.json

  # Export results
  %(prog)s --repo owner/repo --json results.json
  %(prog)s --repo owner/repo --csv results.csv
  %(prog)s --repo owner/repo --report report.txt
        """
    )

    parser.add_argument("--repo", type=str, help="Repository to scan (format: owner/repo)")
    parser.add_argument("--user", type=str, help="Scan all repositories for a GitHub user")
    parser.add_argument("--org", type=str, help="Scan all repositories for a GitHub organization")

    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub API token (or set GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only scan commits after this date (ISO 8601, e.g. 2025-02-24T00:00:00Z). "
             "When set, scans ALL repos and ALL commits since that date (ignores --max-commits/--max-repos)."
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=1000,
        help="Maximum commits to scan per repository (default: 1000, ignored when --since is set)"
    )
    parser.add_argument(
        "--max-repos",
        type=int,
        default=10,
        help="Maximum repositories to scan for user/org (default: 10, ignored when --since is set)"
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        default=False,
        help="Enable deep scanning: run code search queries and fetch file content. "
             "Uses search API (30 req/min). Increases scan time significantly."
    )
    parser.add_argument("--patterns", type=str, help="Path to custom detection patterns JSON file")
    parser.add_argument("--json", type=str, help="Output results to JSON file")
    parser.add_argument("--csv", type=str, help="Output results to CSV file")
    parser.add_argument("--report", type=str, help="Output results to text report file")

    args = parser.parse_args()

    if not args.repo and not args.user and not args.org:
        parser.error("Must specify either --repo, --user, or --org")

    if args.patterns:
        try:
            detector = ClaudeDetector.from_config_file(args.patterns)
            print(f"[*] Loaded custom patterns from {args.patterns}")
        except Exception as e:
            print(f"[!] Error loading custom patterns: {e}")
            sys.exit(1)
    else:
        detector = ClaudeDetector()

    if args.repo:
        if "/" not in args.repo:
            print("[!] Error: Repository must be in format 'owner/repo'")
            sys.exit(1)
        owner, repo = args.repo.split("/", 1)
        detector = scan_repository(owner, repo, args.token, args.max_commits, detector, since=args.since, deep=args.deep)

    elif args.user:
        detector = scan_user_repositories(args.user, args.token, args.max_repos, args.max_commits, detector, since=args.since, deep=args.deep)

    elif args.org:
        detector = scan_organization(args.org, args.token, args.max_repos, args.max_commits, detector, since=args.since, deep=args.deep)

    if not detector or not detector.get_detections():
        print("\n[*] No Claude detections found.")
        sys.exit(0)

    detections = detector.get_detections()
    summary = detector.get_detection_summary()

    OutputFormatter.print_summary(summary)

    if args.json:
        OutputFormatter.to_json(detections, args.json)
        print(f"[*] JSON output written to: {args.json}")

    if args.csv:
        OutputFormatter.to_csv(detections, args.csv)
        print(f"[*] CSV output written to: {args.csv}")

    if args.report:
        OutputFormatter.to_text_report(detections, summary, args.report)
        print(f"[*] Report written to: {args.report}")


if __name__ == "__main__":
    main()
