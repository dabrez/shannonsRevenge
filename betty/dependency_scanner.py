"""
Dependency Scanner - Detect direct Anthropic package dependencies.

Checks package.json, requirements.txt, go.mod, Gemfile, Cargo.toml
for @anthropic-ai/* and anthropic packages.
"""

import re
import base64
from typing import List, Dict
from github_client import GitHubAPIClient
from betty.result import BettyFinding


# Maps manifest filename → list of (pattern, finding_type, description)
MANIFEST_RULES: Dict[str, List] = {
    "package.json": [
        (r'"@anthropic-ai/[^"]+"\s*:', "npm_anthropic_package", "@anthropic-ai/* npm package"),
        (r'"anthropic"\s*:', "npm_anthropic_package", "anthropic npm package"),
    ],
    "requirements.txt": [
        (r"(?im)^anthropic\b", "pip_anthropic_package", "anthropic PyPI package"),
        (r"(?im)^anthropic[>=<!\[]", "pip_anthropic_package", "anthropic PyPI package (versioned)"),
    ],
    "pyproject.toml": [
        (r'(?i)anthropic\s*[>=<!\[]', "pip_anthropic_package", "anthropic in pyproject.toml"),
        (r'"anthropic"', "pip_anthropic_package", "anthropic in pyproject.toml"),
    ],
    "setup.py": [
        (r'(?i)["\']anthropic["\']', "pip_anthropic_package", "anthropic in setup.py"),
    ],
    "setup.cfg": [
        (r"(?im)^\s*anthropic\b", "pip_anthropic_package", "anthropic in setup.cfg"),
    ],
    "go.mod": [
        (r"(?i)github\.com/anthropics/", "go_anthropic_module", "Anthropic Go module"),
        (r"(?i)anthropic\.com/", "go_anthropic_module", "Anthropic Go module"),
    ],
    "Gemfile": [
        (r"""(?i)gem\s+['"]anthropic['"]""", "gem_anthropic", "anthropic Ruby gem"),
        (r"(?i)anthropic-sdk", "gem_anthropic", "anthropic-sdk Ruby gem"),
    ],
    "Gemfile.lock": [
        (r"(?i)^\s*anthropic\b", "gem_anthropic", "anthropic in Gemfile.lock"),
    ],
    "Cargo.toml": [
        (r'(?i)anthropic\s*=', "cargo_anthropic", "anthropic Rust crate"),
        (r'(?i)"anthropic"', "cargo_anthropic", "anthropic Rust crate"),
    ],
    "composer.json": [
        (r'"anthropic[^"]*"\s*:', "composer_anthropic", "anthropic PHP package"),
    ],
    "pom.xml": [
        (r"(?i)<artifactId>anthropic", "maven_anthropic", "anthropic Maven artifact"),
        (r"(?i)<groupId>com\.anthropic", "maven_anthropic", "Anthropic Maven group"),
    ],
    "build.gradle": [
        (r"(?i)com\.anthropic[:\s]", "gradle_anthropic", "anthropic Gradle dependency"),
        (r"(?i)anthropic[:\s]", "gradle_anthropic", "anthropic Gradle dependency"),
    ],
    "build.gradle.kts": [
        (r"(?i)com\.anthropic[:\s]", "gradle_anthropic", "anthropic Gradle dependency"),
    ],
}

# Also scan lock files for transitive usage evidence
LOCK_FILE_RULES: Dict[str, List] = {
    "package-lock.json": [
        (r'"@anthropic-ai/', "npm_anthropic_transitive", "@anthropic-ai in package-lock (transitive ok)"),
    ],
    "yarn.lock": [
        (r"@anthropic-ai/", "npm_anthropic_transitive", "@anthropic-ai in yarn.lock"),
    ],
    "pnpm-lock.yaml": [
        (r"@anthropic-ai/", "npm_anthropic_transitive", "@anthropic-ai in pnpm-lock"),
    ],
    "poetry.lock": [
        (r'(?im)^name = "anthropic"', "pip_anthropic_transitive", "anthropic in poetry.lock"),
    ],
}


class DependencyScanner:
    """Scan a repo's dependency manifests for Anthropic packages."""

    def __init__(self, client: GitHubAPIClient):
        self.client = client

    def scan(self, owner: str, repo: str) -> List[BettyFinding]:
        findings: List[BettyFinding] = []
        tree = self.client.get_repo_tree(owner, repo)
        all_paths = {item.get("path", "") for item in tree}

        all_rules = {**MANIFEST_RULES, **LOCK_FILE_RULES}

        for path in all_paths:
            basename = _basename(path)
            if basename not in all_rules:
                continue

            file_data = self.client.get_file_content(owner, repo, path)
            if not file_data or file_data.get("encoding") != "base64":
                continue
            try:
                content = base64.b64decode(file_data["content"]).decode("utf-8", errors="replace")
            except Exception:
                continue

            for pattern, finding_type, description in all_rules[basename]:
                m = re.search(pattern, content)
                if m:
                    findings.append(BettyFinding(
                        repo_owner=owner,
                        repo_name=repo,
                        scanner="dependency",
                        finding_type=finding_type,
                        evidence=f"{description} found in {path}",
                        file_path=path,
                        matched_value=m.group(0).strip(),
                    ))

        return findings


def _basename(path: str) -> str:
    import os
    return os.path.basename(path)
