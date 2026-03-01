"""
SDK Scanner - Detect Anthropic SDK usage and internal AI abstractions built on it.

Checks for:
  - Direct imports of the official Python/TypeScript/Go SDKs
  - Internal wrapper classes/modules that delegate to Anthropic
  - anthropic client instantiation patterns
  - OpenAI-compatibility shim pointing at Anthropic (api.anthropic.com)
"""

import re
import base64
import os
from typing import List
from github_client import GitHubAPIClient
from betty.result import BettyFinding


# Python SDK patterns
PYTHON_SDK_PATTERNS = [
    (r"(?i)^import\s+anthropic\b", "python_sdk_import", "import anthropic"),
    (r"(?i)^from\s+anthropic\b", "python_sdk_import", "from anthropic import ..."),
    (r"(?i)anthropic\.Anthropic\(", "python_sdk_client", "anthropic.Anthropic() client instantiation"),
    (r"(?i)anthropic\.AsyncAnthropic\(", "python_sdk_client", "anthropic.AsyncAnthropic() client"),
    (r"(?i)anthropic\.messages\.create\(", "python_sdk_call", "anthropic.messages.create() API call"),
    (r'"model"\s*:\s*"claude-', "python_sdk_call", 'model: "claude-..." in Python code'),
]

# TypeScript / JavaScript SDK patterns
TS_SDK_PATTERNS = [
    (r"""(?i)from\s+['"]@anthropic-ai/sdk['"]""", "ts_sdk_import", "@anthropic-ai/sdk import"),
    (r"""(?i)require\(['"]@anthropic-ai/sdk['"]\)""", "ts_sdk_import", "@anthropic-ai/sdk require"),
    (r"(?i)new\s+Anthropic\s*\(", "ts_sdk_client", "new Anthropic() client instantiation"),
    (r"(?i)anthropic\.messages\.create\(", "ts_sdk_call", "anthropic.messages.create() call"),
    (r"""(?i)model:\s*['"]claude-""", "ts_sdk_call", 'model: "claude-..." in TS/JS code'),
]

# Go SDK patterns
GO_SDK_PATTERNS = [
    (r'(?i)"github\.com/anthropics/anthropic-sdk-go"', "go_sdk_import", "anthropic-sdk-go import"),
    (r"(?i)anthropic\.NewClient\(", "go_sdk_client", "anthropic.NewClient() instantiation"),
]

# OpenAI-compatibility shim pointed at Anthropic
OPENAI_SHIM_PATTERNS = [
    (r"(?i)api\.anthropic\.com", "openai_shim_anthropic", "api.anthropic.com endpoint (OpenAI-compat shim)"),
    (r"""(?i)base_url\s*=\s*['"]https://api\.anthropic\.com""", "openai_shim_anthropic",
     "base_url=api.anthropic.com (SDK shim)"),
    (r"""(?i)baseURL\s*:\s*['"]https://api\.anthropic\.com""", "openai_shim_anthropic",
     "baseURL: api.anthropic.com (SDK shim)"),
]

# Internal wrapper heuristics — class/function names that wrap Anthropic
WRAPPER_PATTERNS = [
    (r"(?i)class\s+\w*(Anthropic|Claude)\w*Client\b", "internal_wrapper_class",
     "Internal wrapper class around Anthropic client"),
    (r"(?i)class\s+\w*(AI|LLM)\w*(Client|Provider|Service|Gateway)\b.*anthropic",
     "internal_ai_abstraction", "Internal AI abstraction layer using Anthropic"),
    (r"(?i)def\s+\w*claude\w*\(", "internal_claude_function",
     "Function wrapping Claude/Anthropic"),
]

# Maps file extension → applicable rule sets
EXT_RULES = {
    ".py": PYTHON_SDK_PATTERNS + OPENAI_SHIM_PATTERNS + WRAPPER_PATTERNS,
    ".ts": TS_SDK_PATTERNS + OPENAI_SHIM_PATTERNS + WRAPPER_PATTERNS,
    ".tsx": TS_SDK_PATTERNS + OPENAI_SHIM_PATTERNS,
    ".js": TS_SDK_PATTERNS + OPENAI_SHIM_PATTERNS,
    ".jsx": TS_SDK_PATTERNS + OPENAI_SHIM_PATTERNS,
    ".mjs": TS_SDK_PATTERNS + OPENAI_SHIM_PATTERNS,
    ".go": GO_SDK_PATTERNS + OPENAI_SHIM_PATTERNS,
}

MAX_FILES = 200  # cap to avoid hammering the API on huge repos


class SDKScanner:
    """Scan a repo for direct or wrapped Anthropic SDK usage."""

    def __init__(self, client: GitHubAPIClient):
        self.client = client

    def scan(self, owner: str, repo: str) -> List[BettyFinding]:
        findings: List[BettyFinding] = []
        tree = self.client.get_repo_tree(owner, repo)

        scannable = [
            item.get("path", "") for item in tree
            if os.path.splitext(item.get("path", ""))[1].lower() in EXT_RULES
            and not _is_vendored(item.get("path", ""))
        ][:MAX_FILES]

        seen_files: set = set()

        for path in scannable:
            if path in seen_files:
                continue
            ext = os.path.splitext(path)[1].lower()
            rules = EXT_RULES.get(ext, [])
            if not rules:
                continue

            file_data = self.client.get_file_content(owner, repo, path)
            if not file_data or file_data.get("encoding") != "base64":
                continue
            try:
                content = base64.b64decode(file_data["content"]).decode("utf-8", errors="replace")
            except Exception:
                continue
            seen_files.add(path)

            seen_types: set = set()
            for pattern, finding_type, description in rules:
                if finding_type in seen_types:
                    continue
                m = re.search(pattern, content, re.MULTILINE)
                if m:
                    findings.append(BettyFinding(
                        repo_owner=owner,
                        repo_name=repo,
                        scanner="sdk",
                        finding_type=finding_type,
                        evidence=f"{description} in {path}",
                        file_path=path,
                        matched_value=m.group(0).strip(),
                    ))
                    seen_types.add(finding_type)

        return findings


def _is_vendored(path: str) -> bool:
    """Skip files in vendor / node_modules directories."""
    parts = path.split("/")
    skip = {"vendor", "node_modules", ".vendor", "third_party", "thirdparty"}
    return any(p in skip for p in parts)
