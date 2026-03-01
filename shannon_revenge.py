#!/usr/bin/env python3
"""
ShannonRevenge - GitHub Scanner for Claude-Generated Code

Identifies repositories with Claude in their supply chain by detecting
Claude signatures in commits and code.
"""

import argparse
import os
import sys
from typing import Optional
from github_client import GitHubAPIClient
from detector import ClaudeDetector
from output_formatter import OutputFormatter


def scan_repository(owner: str, repo: str, token: Optional[str] = None, max_commits: int = 1000, detector: Optional[ClaudeDetector] = None):
    """
    Scan a single repository for Claude signatures.

    Args:
        owner: Repository owner
        repo: Repository name
        token: GitHub API token
        max_commits: Maximum number of commits to scan
        detector: Optional existing detector to use
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
        print(f"[*] Scanning commits...")

        commit_count = 0
        detection_count = 0

        for commit in client.get_repo_commits(owner, repo):
            commit_count += 1

            commit_detail = client.get_commit_detail(owner, repo, commit["sha"])
            detection = detector.analyze_commit(commit_detail, owner, repo)

            if detection:
                detection_count += 1
                print(f"[!] DETECTION: {detection.commit_sha[:8]} - {detection.detection_type}")

            if commit_count >= max_commits:
                print(f"[*] Reached maximum commit limit ({max_commits})")
                break

            if commit_count % 50 == 0:
                print(f"[*] Scanned {commit_count} commits, found {detection_count} detections")

        print(f"\n[*] Scan complete: {commit_count} commits scanned, {detection_count} detections found")

        return detector

    except Exception as e:
        print(f"[!] Error scanning repository: {e}")
        return None


def scan_user_repositories(username: str, token: Optional[str] = None, max_repos: int = 10, max_commits_per_repo: int = 100, detector: Optional[ClaudeDetector] = None):
    """
    Scan all repositories for a user.

    Args:
        username: GitHub username
        token: GitHub API token
        max_repos: Maximum number of repositories to scan
        max_commits_per_repo: Maximum commits per repository
        detector: Optional existing detector to use
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

            scan_repository(owner, name, token, max_commits_per_repo, detector)

        return detector

    except Exception as e:
        print(f"[!] Error scanning user repositories: {e}")
        return None


def scan_organization(org: str, token: Optional[str] = None, max_repos: int = 20, max_commits_per_repo: int = 100, detector: Optional[ClaudeDetector] = None):
    """
    Scan all repositories for an organization.

    Args:
        org: Organization name
        token: GitHub API token
        max_repos: Maximum number of repositories to scan
        max_commits_per_repo: Maximum commits per repository
        detector: Optional existing detector to use
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
        for i, repo in enumerate(client.get_org_repos(org)):
            repos.append(repo)
            if len(repos) >= max_repos:
                break
        print(f"[*] Scanning {len(repos)} repositories")

        for i, repo in enumerate(repos, 1):
            owner = repo["owner"]["login"]
            name = repo["name"]

            print(f"\n[{i}/{len(repos)}] Scanning {owner}/{name}")

            scan_repository(owner, name, token, max_commits_per_repo, detector)

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

  # Use custom detection patterns
  %(prog)s --repo owner/repo --patterns patterns.json

  # Export results
  %(prog)s --repo owner/repo --json results.json
  %(prog)s --repo owner/repo --csv results.csv
  %(prog)s --repo owner/repo --report report.txt
        """
    )

    parser.add_argument(
        "--repo",
        type=str,
        help="Repository to scan (format: owner/repo)"
    )

    parser.add_argument(
        "--user",
        type=str,
        help="Scan all repositories for a GitHub user"
    )

    parser.add_argument(
        "--org",
        type=str,
        help="Scan all repositories for a GitHub organization"
    )

    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("GITHUB_TOKEN"),
        help="GitHub API token (or set GITHUB_TOKEN env var)"
    )

    parser.add_argument(
        "--max-commits",
        type=int,
        default=1000,
        help="Maximum commits to scan per repository (default: 1000)"
    )

    parser.add_argument(
        "--max-repos",
        type=int,
        default=10,
        help="Maximum repositories to scan for user/org (default: 10)"
    )

    parser.add_argument(
        "--patterns",
        type=str,
        help="Path to custom detection patterns JSON file"
    )

    parser.add_argument(
        "--json",
        type=str,
        help="Output results to JSON file"
    )

    parser.add_argument(
        "--csv",
        type=str,
        help="Output results to CSV file"
    )

    parser.add_argument(
        "--report",
        type=str,
        help="Output results to text report file"
    )

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
        detector = scan_repository(owner, repo, args.token, args.max_commits, detector)

    elif args.user:
        detector = scan_user_repositories(args.user, args.token, args.max_repos, args.max_commits, detector)

    elif args.org:
        detector = scan_organization(args.org, args.token, args.max_repos, args.max_commits, detector)

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
