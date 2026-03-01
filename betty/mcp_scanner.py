"""
MCP Scanner - Detect repos implementing the Model Context Protocol.

Anthropic invented MCP. Implementing an Anthropic-designed protocol
is a supply-chain dependency regardless of who owns the spec today.
"""

import re
import base64
from typing import List
from github_client import GitHubAPIClient
from betty.result import BettyFinding

# Files that indicate MCP server/client implementation
MCP_FILE_SIGNALS = [
    "mcp.json",
    ".mcp.json",
    "mcp-config.json",
    "mcp-server.json",
    ".claude/mcp.json",
]

# Path fragments that strongly suggest MCP implementation
MCP_PATH_PATTERNS = [
    r"(?i)/mcp[-_]?server",
    r"(?i)/mcp[-_]?client",
    r"(?i)^mcp[-_]?server",
    r"(?i)^mcp[-_]?client",
    r"(?i)/model[-_]context[-_]protocol",
]

# Content patterns in source files
MCP_CONTENT_PATTERNS = [
    r"(?i)@modelcontextprotocol/",
    r"(?i)model[_-]context[_-]protocol",
    r"(?i)from\s+['\"]mcp['\"]",
    r"(?i)import\s+mcp\b",
    r"(?i)McpServer\b",
    r"(?i)McpClient\b",
    r'(?i)"mcpServers"\s*:',
    r'(?i)"mcp_servers"\s*:',
    r"(?i)anthropic\.com/mcp",
    r"(?i)spec\.modelcontextprotocol\.io",
]

# Package manifest keys
MCP_PACKAGE_PATTERNS = [
    r'(?i)"@modelcontextprotocol/',
    r"(?i)modelcontextprotocol",
]


class MCPScanner:
    """Scan a repo for Model Context Protocol implementation."""

    def __init__(self, client: GitHubAPIClient):
        self.client = client

    def scan(self, owner: str, repo: str, fetch_content: bool = True) -> List[BettyFinding]:
        findings: List[BettyFinding] = []
        tree = self.client.get_repo_tree(owner, repo)
        all_paths = {item.get("path", "") for item in tree}

        # Check known MCP config file names
        for signal in MCP_FILE_SIGNALS:
            if signal in all_paths:
                findings.append(BettyFinding(
                    repo_owner=owner,
                    repo_name=repo,
                    scanner="mcp",
                    finding_type="mcp_config_file",
                    evidence=f"MCP config file present: {signal}",
                    file_path=signal,
                    matched_value=signal,
                ))

        # Check path patterns (directory/file names suggesting MCP server or client)
        for path in all_paths:
            for pattern in MCP_PATH_PATTERNS:
                if re.search(pattern, path):
                    findings.append(BettyFinding(
                        repo_owner=owner,
                        repo_name=repo,
                        scanner="mcp",
                        finding_type="mcp_path_pattern",
                        evidence=f"Path suggests MCP implementation: {path}",
                        file_path=path,
                        matched_value=path,
                    ))
                    break  # one finding per path

        if not fetch_content:
            return findings

        # Scan package manifests and key source files for MCP content patterns
        content_targets = [p for p in all_paths if _is_scannable(p)]
        seen_files: set = set()

        for path in content_targets:
            if path in seen_files:
                continue
            file_data = self.client.get_file_content(owner, repo, path)
            if not file_data or file_data.get("encoding") != "base64":
                continue
            try:
                content = base64.b64decode(file_data["content"]).decode("utf-8", errors="replace")
            except Exception:
                continue
            seen_files.add(path)

            for pattern in MCP_CONTENT_PATTERNS + MCP_PACKAGE_PATTERNS:
                m = re.search(pattern, content)
                if m:
                    findings.append(BettyFinding(
                        repo_owner=owner,
                        repo_name=repo,
                        scanner="mcp",
                        finding_type="mcp_content_pattern",
                        evidence=f"MCP reference in {path}: matched {pattern!r}",
                        file_path=path,
                        matched_value=m.group(0),
                    ))
                    break  # one finding per file

        return findings


def _is_scannable(path: str) -> bool:
    scannable_names = {
        "package.json", "requirements.txt", "pyproject.toml", "go.mod",
        "Cargo.toml", "Gemfile", "composer.json",
    }
    import os
    basename = os.path.basename(path)
    if basename in scannable_names:
        return True
    # Also scan source files that might reference MCP
    scannable_exts = {".py", ".ts", ".js", ".go", ".rs", ".rb", ".java", ".kt"}
    _, ext = os.path.splitext(path)
    return ext in scannable_exts
