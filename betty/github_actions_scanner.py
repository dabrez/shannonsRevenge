"""
GitHub Actions Scanner - Detect Anthropic CI/CD actions in workflows.

Flags usage of:
  - anthropics/claude-code-action
  - anthropics/claude-code-base-action
  - anthropics/anthropic-ai-action (and variants)
  - Any action from the anthropics or oven-sh orgs
"""

import re
import base64
from typing import List
from github_client import GitHubAPIClient
from betty.result import BettyFinding

# Action reference patterns in workflow YAML
# Format: uses: owner/repo@ref  or  uses: owner/repo/.github/actions/name@ref
ANTHROPIC_ACTION_PATTERNS = [
    # Explicit known actions
    (r"(?i)uses:\s*anthropics/claude-code-action\b", "claude_code_action",
     "anthropics/claude-code-action in CI"),
    (r"(?i)uses:\s*anthropics/claude-code-base-action\b", "claude_base_action",
     "anthropics/claude-code-base-action in CI"),
    (r"(?i)uses:\s*anthropics/[^\s@]+", "anthropic_action",
     "Anthropic GitHub Action in CI"),
    # Bun setup action (oven-sh)
    (r"(?i)uses:\s*oven-sh/setup-bun\b", "bun_setup_action",
     "oven-sh/setup-bun (Bun, Anthropic-owned) in CI"),
    (r"(?i)uses:\s*oven-sh/[^\s@]+", "oven_sh_action",
     "oven-sh GitHub Action in CI"),
]

# Container image references to Anthropic/Bun
CONTAINER_PATTERNS = [
    (r"(?i)image:\s*oven/bun\b", "bun_container_image",
     "Bun container image (Anthropic-owned) in CI"),
    (r"(?i)image:\s*ghcr\.io/anthropics/", "anthropic_container_image",
     "Anthropic container image in CI"),
]

# Environment variables that suggest Anthropic API usage in CI
ENV_PATTERNS = [
    (r"(?i)ANTHROPIC_API_KEY\b", "anthropic_api_key_in_ci",
     "ANTHROPIC_API_KEY referenced in CI workflow"),
    (r"(?i)CLAUDE_API_KEY\b", "claude_api_key_in_ci",
     "CLAUDE_API_KEY referenced in CI workflow"),
]


class GitHubActionsScanner:
    """Scan a repo's GitHub Actions workflows for Anthropic CI components."""

    def __init__(self, client: GitHubAPIClient):
        self.client = client

    def scan(self, owner: str, repo: str) -> List[BettyFinding]:
        findings: List[BettyFinding] = []
        tree = self.client.get_repo_tree(owner, repo)

        workflow_paths = [
            item.get("path", "") for item in tree
            if item.get("path", "").startswith(".github/workflows/")
            and item.get("path", "").endswith((".yml", ".yaml"))
        ]

        for path in workflow_paths:
            file_data = self.client.get_file_content(owner, repo, path)
            if not file_data or file_data.get("encoding") != "base64":
                continue
            try:
                content = base64.b64decode(file_data["content"]).decode("utf-8", errors="replace")
            except Exception:
                continue

            all_patterns = ANTHROPIC_ACTION_PATTERNS + CONTAINER_PATTERNS + ENV_PATTERNS
            seen_types: set = set()

            for pattern, finding_type, description in all_patterns:
                if finding_type in seen_types:
                    continue
                m = re.search(pattern, content)
                if m:
                    findings.append(BettyFinding(
                        repo_owner=owner,
                        repo_name=repo,
                        scanner="actions",
                        finding_type=finding_type,
                        evidence=f"{description}: {path}",
                        file_path=path,
                        matched_value=m.group(0).strip(),
                    ))
                    seen_types.add(finding_type)

        return findings
