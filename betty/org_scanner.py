"""
Org Scanner - Detect forks or vendored copies of Anthropic-owned repos.

Covers:
  - anthropics org (Claude, SDKs, tooling)
  - anthropic-experimental org
  - oven-sh org (Bun - owned by Anthropic)
"""

from typing import List, Dict, Set, Optional
from github_client import GitHubAPIClient
from betty.result import BettyFinding


# Orgs whose repos are considered Anthropic supply-chain components
ANTHROPIC_ORGS = [
    "anthropics",
    "anthropic-experimental",
    "oven-sh",          # Bun
]

# Cached repo lists — populated lazily, shared across scanner instances
_ORG_REPO_CACHE: Dict[str, Set[str]] = {}


class OrgScanner:
    """
    Check whether a target repo forks or vendors an Anthropic-org repo.

    Two checks:
      1. Direct fork: GitHub API fork_of field points to an anthropics/oven-sh repo.
      2. Vendor copy: repo file tree contains a directory whose name matches
         a known Anthropic repo name (e.g. vendor/anthropic-sdk-python).
    """

    def __init__(self, client: GitHubAPIClient, prefetch_orgs: bool = False):
        self.client = client
        if prefetch_orgs:
            self._load_org_repos()

    def _load_org_repos(self):
        """Fetch and cache repo names from each Anthropic org."""
        for org in ANTHROPIC_ORGS:
            if org in _ORG_REPO_CACHE:
                continue
            names: Set[str] = set()
            try:
                for repo in self.client.get_org_repos(org):
                    names.add(repo["name"].lower())
            except Exception as e:
                print(f"[betty/org] Could not fetch repos for {org}: {e}")
            _ORG_REPO_CACHE[org] = names

    def _all_anthropic_repo_names(self) -> Set[str]:
        names: Set[str] = set()
        for v in _ORG_REPO_CACHE.values():
            names |= v
        return names

    def scan(self, owner: str, repo: str) -> List[BettyFinding]:
        findings: List[BettyFinding] = []

        # Ensure cache is populated
        self._load_org_repos()

        # Check 1: is this repo itself a fork of an Anthropic-org repo?
        try:
            info = self.client.get_repo_info(owner, repo)
            if info.get("fork"):
                parent = info.get("parent") or info.get("source") or {}
                parent_owner = (parent.get("owner") or {}).get("login", "").lower()
                parent_name = parent.get("name", "").lower()
                if parent_owner in {o.lower() for o in ANTHROPIC_ORGS}:
                    findings.append(BettyFinding(
                        repo_owner=owner,
                        repo_name=repo,
                        scanner="org",
                        finding_type="anthropic_fork",
                        evidence=f"Repo is a fork of {parent_owner}/{parent_name}",
                        matched_value=f"{parent_owner}/{parent_name}",
                    ))
        except Exception as e:
            print(f"[betty/org] Could not check fork info for {owner}/{repo}: {e}")

        # Check 2: does the file tree contain vendored copies of Anthropic repos?
        known_names = self._all_anthropic_repo_names()
        if known_names:
            try:
                tree = self.client.get_repo_tree(owner, repo)
                for item in tree:
                    path = item.get("path", "").lower()
                    # Check each path segment against known Anthropic repo names
                    for segment in path.split("/"):
                        # Strip common vendor prefixes/suffixes for matching
                        normalized = segment.replace("-", "").replace("_", "")
                        for repo_name in known_names:
                            norm_name = repo_name.replace("-", "").replace("_", "")
                            if norm_name and norm_name in normalized and len(norm_name) > 4:
                                findings.append(BettyFinding(
                                    repo_owner=owner,
                                    repo_name=repo,
                                    scanner="org",
                                    finding_type="anthropic_vendor_path",
                                    evidence=f"Path segment '{segment}' matches Anthropic repo '{repo_name}'",
                                    file_path=item.get("path", ""),
                                    matched_value=repo_name,
                                ))
                                break
            except Exception as e:
                print(f"[betty/org] Could not check file tree for {owner}/{repo}: {e}")

        return findings

    @staticmethod
    def list_anthropic_orgs() -> List[str]:
        return list(ANTHROPIC_ORGS)

    def get_anthropic_repo_count(self) -> Dict[str, int]:
        self._load_org_repos()
        return {org: len(names) for org, names in _ORG_REPO_CACHE.items()}
