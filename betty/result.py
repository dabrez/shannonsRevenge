"""Shared result type for all betty scanners."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class BettyFinding:
    """A single supply-chain finding from a betty scanner."""
    repo_owner: str
    repo_name: str
    scanner: str          # e.g. "dependency", "mcp", "bun", "org", "actions", "sdk"
    finding_type: str     # e.g. "anthropic_dependency", "mcp_config_file", "bun_lockfile"
    evidence: str         # human-readable description
    file_path: str = ""   # file where the signal was found (empty if repo-level)
    matched_value: str = ""  # the specific string/value that matched
    additional: Optional[Dict] = None

    @property
    def repo(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}"
