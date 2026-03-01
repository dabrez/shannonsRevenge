"""
Bun Scanner - Detect usage of Bun, the JavaScript runtime owned by Anthropic.

Checks for bun.lockb, bunfig.toml, CI scripts calling `bun`, and
package.json scripts using bun as runner.
"""

import re
import base64
from typing import List
from github_client import GitHubAPIClient
from betty.result import BettyFinding

# File presence signals
BUN_FILE_SIGNALS = [
    "bun.lockb",       # bun's binary lockfile — definitive
    "bunfig.toml",     # bun config file
    ".bunfig.toml",
]

# package.json script patterns that use bun as runner
BUN_SCRIPT_PATTERNS = [
    r'"[^"]+"\s*:\s*"bun\s+',          # "test": "bun test"
    r'"[^"]+"\s*:\s*"bunx\s+',         # "lint": "bunx eslint"
    r'"packageManager"\s*:\s*"bun@',   # corepack declaration
]

# CI file content patterns
BUN_CI_PATTERNS = [
    r"(?i)\buses:\s*oven-sh/setup-bun\b",   # GitHub Actions: setup bun action
    r"(?im)^\s*-?\s*run:\s+bun\s+",         # CI step: run: bun ...
    r"(?im)^\s*bun\s+(install|run|test|build)\b",
    r"(?i)setup-bun@",
    r"(?i)oven-sh/bun",
]

# Dockerfile / shell script patterns
BUN_RUNTIME_PATTERNS = [
    r"(?i)\bFROM\s+oven/bun\b",             # Dockerfile base image
    r"(?i)\bFROM\s+oven/bun:",
    r"(?im)^\s*RUN\s+bun\s+(install|run|build|test)\b",
    r"(?i)npm\s+install\s+-g\s+bun\b",
    r"(?i)curl\s+.*bun\.sh",
]


class BunScanner:
    """Scan a repo for Bun runtime usage (Anthropic-owned)."""

    def __init__(self, client: GitHubAPIClient):
        self.client = client

    def scan(self, owner: str, repo: str) -> List[BettyFinding]:
        findings: List[BettyFinding] = []
        tree = self.client.get_repo_tree(owner, repo)
        all_paths = {item.get("path", "") for item in tree}

        # Check lockfile / config presence
        for signal in BUN_FILE_SIGNALS:
            if signal in all_paths:
                findings.append(BettyFinding(
                    repo_owner=owner,
                    repo_name=repo,
                    scanner="bun",
                    finding_type="bun_lockfile" if signal == "bun.lockb" else "bun_config",
                    evidence=f"Bun file present: {signal}",
                    file_path=signal,
                    matched_value=signal,
                ))

        # Scan content files
        for path in all_paths:
            rules = _rules_for_path(path)
            if not rules:
                continue

            file_data = self.client.get_file_content(owner, repo, path)
            if not file_data or file_data.get("encoding") != "base64":
                continue
            try:
                content = base64.b64decode(file_data["content"]).decode("utf-8", errors="replace")
            except Exception:
                continue

            for pattern, finding_type, description in rules:
                m = re.search(pattern, content)
                if m:
                    findings.append(BettyFinding(
                        repo_owner=owner,
                        repo_name=repo,
                        scanner="bun",
                        finding_type=finding_type,
                        evidence=f"{description} in {path}",
                        file_path=path,
                        matched_value=m.group(0).strip(),
                    ))
                    break  # one finding per file

        return findings


def _rules_for_path(path: str) -> List:
    import os
    basename = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()

    if basename == "package.json":
        return [(p, "bun_package_script", "bun used as script runner") for p in BUN_SCRIPT_PATTERNS]

    if ext in {".yml", ".yaml"} and (".github/workflows" in path or "ci" in path.lower()):
        return [(p, "bun_ci_usage", "bun in CI pipeline") for p in BUN_CI_PATTERNS]

    if basename == "Dockerfile" or basename.startswith("Dockerfile."):
        return [(p, "bun_docker", "bun Docker image") for p in BUN_RUNTIME_PATTERNS]

    if ext in {".sh", ".bash"}:
        return [(p, "bun_shell_script", "bun in shell script") for p in BUN_RUNTIME_PATTERNS]

    return []
