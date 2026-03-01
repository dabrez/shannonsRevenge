#!/usr/bin/env python3
"""
Test script for ShannonRevenge - scans major tech and defense organizations
"""

import os
import sys
import subprocess
from datetime import datetime

# GitHub token
GITHUB_TOKEN = "your_token_here"

# Organizations to scan
ORGANIZATIONS = [
    # Tech companies
    {"name": "microsoft", "max_repos": 10},
    {"name": "amazon", "max_repos": 10},
    {"name": "aws", "max_repos": 10},
    {"name": "google", "max_repos": 10},
    {"name": "salesforce", "max_repos": 10},
    {"name": "oracle", "max_repos": 10},
    {"name": "IBM", "max_repos": 10},
    {"name": "RedHat", "max_repos": 10},
    {"name": "cisco", "max_repos": 10},
    {"name": "palantir", "max_repos": 10},

    # Defense contractors
    {"name": "Lockheed-Martin", "max_repos": 5},
    {"name": "raytheon", "max_repos": 5},
    {"name": "northropgrumman", "max_repos": 5},
]


def run_scan(org_name: str, max_repos: int, output_dir: str):
    """
    Run a scan on an organization.

    Args:
        org_name: Organization name
        max_repos: Maximum repositories to scan
        output_dir: Directory to save results
    """
    print(f"\n{'='*80}")
    print(f"Scanning organization: {org_name}")
    print(f"{'='*80}")

    # Create output filenames
    json_file = os.path.join(output_dir, f"{org_name}_scan.json")
    csv_file = os.path.join(output_dir, f"{org_name}_scan.csv")
    report_file = os.path.join(output_dir, f"{org_name}_scan.txt")

    # Build command
    cmd = [
        "python", "shannon_revenge.py",
        "--org", org_name,
        "--token", GITHUB_TOKEN,
        "--max-repos", str(max_repos),
        "--max-commits", "100",  # Limit commits for faster testing
        "--json", json_file,
        "--csv", csv_file,
        "--report", report_file
    ]

    try:
        # Run the scan
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout per org
        )

        print(f"\n[*] Scan completed for {org_name}")
        print(f"[*] Exit code: {result.returncode}")

        if result.returncode != 0:
            print(f"[!] Error output:")
            print(result.stderr)

        print(f"[*] Output files:")
        print(f"    - {json_file}")
        print(f"    - {csv_file}")
        print(f"    - {report_file}")

        return result.returncode == 0

    except subprocess.TimeoutExpired:
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

        success = run_scan(org['name'], org['max_repos'], results_dir)

        if success:
            successful.append(org['name'])
        else:
            failed.append(org['name'])

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
