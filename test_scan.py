#!/usr/bin/env python3
"""
Test script for ShannonRevenge - scans major tech and defense organizations
"""

import os
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# GitHub token from environment — never hardcode
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Organizations to scan
ORGANIZATIONS = [
    # Tech companies
    {"name": "microsoft", "max_repos": 5, "max_commits": 100},
    {"name": "amzn", "max_repos": 5, "max_commits": 100},
    {"name": "aws", "max_repos": 5, "max_commits": 100},
    {"name": "google", "max_repos": 5, "max_commits": 100},
    {"name": "salesforce", "max_repos": 5, "max_commits": 100},
    {"name": "oracle", "max_repos": 5, "max_commits": 100},
    {"name": "IBM", "max_repos": 5, "max_commits": 100},
    {"name": "redhat-cop", "max_repos": 5, "max_commits": 100},
    {"name": "cisco", "max_repos": 5, "max_commits": 100},
    {"name": "palantir", "max_repos": 5, "max_commits": 100},

    # Defense contractors
    {"name": "lockheedmartin", "max_repos": 3, "max_commits": 100},
    {"name": "raytheon", "max_repos": 3, "max_commits": 100},
    {"name": "northropgrumman", "max_repos": 3, "max_commits": 100},
    {"name": "anduril", "max_repos": 3, "max_commits": 100},
]


def run_scan(org_name: str, max_repos: int, max_commits: int, output_dir: str):
    """
    Run a scan on an organization.

    Args:
        org_name: Organization name
        max_repos: Maximum repositories to scan
        max_commits: Maximum commits per repository
        output_dir: Directory to save results
    """
    print(f"\n{'='*80}")
    print(f"Scanning organization: {org_name}")
    print(f"{'='*80}")

    # Create output filenames
    json_file = os.path.join(output_dir, f"{org_name}_scan.json")
    csv_file = os.path.join(output_dir, f"{org_name}_scan.csv")
    report_file = os.path.join(output_dir, f"{org_name}_scan.txt")

    # Build command — use sys.executable so we run inside the active venv
    cmd = [
        sys.executable, "shannon_revenge.py",
        "--org", org_name,
        "--max-repos", str(max_repos),
        "--max-commits", str(max_commits),
        "--json", json_file,
        "--csv", csv_file,
        "--report", report_file,
    ]

    if GITHUB_TOKEN:
        cmd += ["--token", GITHUB_TOKEN]

    try:
        # Stream output so we can see progress in real time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in process.stdout:
            print(line, end="", flush=True)

        process.wait(timeout=600)
        returncode = process.returncode

        print(f"\n[*] Scan completed for {org_name} (exit code: {returncode})")
        print(f"[*] Output files:")
        print(f"    - {json_file}")
        print(f"    - {csv_file}")
        print(f"    - {report_file}")

        return returncode == 0

    except subprocess.TimeoutExpired:
        process.kill()
        print(f"[!] Scan timed out for {org_name}")
        return False
    except Exception as e:
        print(f"[!] Error scanning {org_name}: {e}")
        return False


def main():
    """Main test execution."""
    print("="*80)
    print("SHANNON REVENGE - ORGANIZATION SCAN TEST")
    print("="*80)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Organizations to scan: {len(ORGANIZATIONS)}")

    if GITHUB_TOKEN:
        print(f"[*] GitHub token loaded from environment")
    else:
        print(f"[!] WARNING: No GITHUB_TOKEN found — rate limited to 60 req/hour")

    # Print rate limit info
    try:
        import requests
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
        r = requests.get("https://api.github.com/rate_limit", headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            core = data["resources"]["core"]
            print(f"[*] Rate limit: {core['remaining']}/{core['limit']} remaining, "
                  f"resets at {datetime.fromtimestamp(core['reset']).strftime('%H:%M:%S')}")
    except Exception:
        pass

    print("="*80)

    # Create results directory
    results_dir = "test_results"
    os.makedirs(results_dir, exist_ok=True)
    print(f"\n[*] Results will be saved to: {results_dir}/")

    # Track results
    successful = []
    failed = []

    # Run scans
    for i, org in enumerate(ORGANIZATIONS, 1):
        print(f"\n[{i}/{len(ORGANIZATIONS)}] Processing: {org['name']}")

        success = run_scan(
            org["name"],
            org.get("max_repos", 5),
            org.get("max_commits", 100),
            results_dir,
        )

        if success:
            successful.append(org["name"])
        else:
            failed.append(org["name"])

    # Summary
    print("\n" + "="*80)
    print("SCAN SUMMARY")
    print("="*80)
    print(f"Total organizations: {len(ORGANIZATIONS)}")
    print(f"Successful scans: {len(successful)}")
    print(f"Failed scans: {len(failed)}")

    if successful:
        print(f"\n✓ Successful ({len(successful)}):")
        for org in successful:
            print(f"  - {org}")

    if failed:
        print(f"\n✗ Failed ({len(failed)}):")
        for org in failed:
            print(f"  - {org}")

    print(f"\nCompleted: {datetime.now().isoformat()}")
    print(f"Results saved to: {results_dir}/")
    print("="*80)


if __name__ == "__main__":
    main()
