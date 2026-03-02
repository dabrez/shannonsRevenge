# ShannonRevenge

# Why does this exist?

On February 27, 2026, the Department of War designated 
Anthropic a supply chain risk.

Defense contractors must now certify they have no 
commercial activity with Anthropic.

This tool helps you comply.

Named after Claude Shannon, the father of information theory.
Named after the man Claude is named after.
Named after the mathematical foundation the Pentagon runs on.

We wish to comply with instructions from the Department of War.

# The project

A GitHub scanner that identifies repositories with Claude in their supply chain by detecting Claude signatures in commits and code.

## Known Limitations

- Detection relies on opt-in signals (co-author trailers, Claude Code markers, comment patterns). Developers who don't use these or actively remove them won't be detected.
- Only scans commit metadata and messages by default; `--deep` mode fetches file content but is rate-limited and slow.
- GitHub API limits: 60 req/hour unauthenticated, 5,000/hour with a token. A full 14-org scan needs ~2 hours or a paid plan.
- False positives are possible for generic terms (e.g. CSS `cursor` properties, editor `cursor` movement APIs). Patterns are tuned to minimize this but not eliminate it.

## Features

- **GitHub API Integration**: Full GitHub API client with automatic rate limiting and pagination
- **Organization Scanning**: Scan entire GitHub organizations for Claude-generated code
- **Custom Detection Patterns**: Configurable pattern matching via JSON configuration files
- **Claude Detection**: Multiple detection methods for identifying Claude-generated code:
  - Co-authored commits (`Co-Authored-By: Claude`)
  - Claude Code markers (`Generated with Claude Code`)
  - Commit message patterns
  - Code comment patterns
  - Claude email signatures (`noreply@anthropic.com`)
  - AI pair programming mentions
  - Cursor + Claude references
- **Rate Limiting**: Automatic rate limit handling to avoid API throttling
- **Pagination**: Efficiently handles large repositories with automatic pagination
- **Multiple Output Formats**:
  - JSON (machine-readable)
  - CSV (spreadsheet-compatible)
  - Text reports (human-readable)

## Installation

1. Clone the repository:
```bash
cd shannonRevenge
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Scan a single repository:
```bash
python shannon_revenge.py --repo owner/repo
```

Scan with a GitHub token (recommended for higher rate limits):
```bash
python shannon_revenge.py --repo owner/repo --token YOUR_GITHUB_TOKEN
```

Or set the token as an environment variable:
```bash
export GITHUB_TOKEN=your_token_here
python shannon_revenge.py --repo owner/repo
```

### Scan User Repositories

Scan all repositories for a user:
```bash
python shannon_revenge.py --user username --max-repos 10
```

### Scan Organization Repositories

Scan all repositories for an organization:
```bash
python shannon_revenge.py --org organization-name --max-repos 20
```

## Known Limitations

Shannon finds what Claude touched directly.

It cannot find:
- Code Claude suggested that a human typed manually
- Architecture decisions Claude informed
- Variables named after Claude's suggestions  
- Code written by developers who read Claude's output
- The context window Claude used to understand your codebase

Can you certify zero Claude involvement?

No.
Neither can we.
Neither can your lawyers.
Neither can the Pentagon.

This is not a bug.
This is the point.


### Custom Detection Patterns

Use a custom patterns configuration file:
```bash
python shannon_revenge.py --repo owner/repo --patterns patterns.json
```

You can customize the detection patterns by editing `patterns.json` or creating your own:
```json
{
  "signatures": {
    "co_author": "Co-Authored-By:\\s*Claude\\s*<[^>]+>",
    "custom_marker": "your-custom-pattern"
  },
  "commit_patterns": [
    "(?i)generated (by|with|using) claude",
    "(?i)your custom commit pattern"
  ],
  "code_patterns": [
    "@generated.*claude",
    "(?i)// your custom code pattern"
  ]
}
```

## Detection Methods

**High confidence (direct signatures)**
- Co-authored-by: Claude <noreply@anthropic.com>
- Generated with [Claude Code] in commit messages
- .claude/ directory in repository
- CLAUDE.md in repository root or subdirectories
- claude-code-bot as commit author

**Medium confidence (pattern matching)**  
- Commit messages referencing Claude or Anthropic
- Code comments with Claude markers
- Cursor IDE references in commits

**Known false positives**
- The word "cursor" in branch names (e.g. cursor-move-foldedline)
- We are working on this
- PRs welcome

### Output Formats

Export to JSON:
```bash
python shannon_revenge.py --repo owner/repo --json results.json
```

Export to CSV:
```bash
python shannon_revenge.py --repo owner/repo --csv results.csv
```

Generate text report:
```bash
python shannon_revenge.py --repo owner/repo --report report.txt
```

### Advanced Options

```bash
# Limit commits scanned per repository
python shannon_revenge.py --repo owner/repo --max-commits 500

# Scan user with multiple outputs
python shannon_revenge.py --user username --max-repos 5 --json out.json --csv out.csv --report out.txt

# Scan organization with custom patterns
python shannon_revenge.py --org mycompany --patterns custom_patterns.json --max-repos 50

# Full scan with all options
python shannon_revenge.py --org mycompany --token $GITHUB_TOKEN --max-repos 100 --max-commits 500 --json scan.json --csv scan.csv --report scan.txt
```

## Command Line Options

```
--repo OWNER/REPO       Repository to scan (format: owner/repo)
--user USERNAME         Scan all repositories for a GitHub user
--org ORGANIZATION      Scan all repositories for a GitHub organization
--token TOKEN           GitHub API token (or set GITHUB_TOKEN env var)
--max-commits N         Maximum commits to scan per repository (default: 1000)
--max-repos N           Maximum repositories to scan for user/org (default: 10)
--patterns FILE         Path to custom detection patterns JSON file
--json FILE             Output results to JSON file
--csv FILE              Output results to CSV file
--report FILE           Output results to text report file
```

## Detection Methods

ShannonRevenge uses multiple methods to detect Claude-generated code and related AI tools:

### Built-in Detection Patterns

#### Claude-Specific Detection
1. **Co-Author Detection**: Looks for `Co-Authored-By: Claude <noreply@anthropic.com>` in commits
2. **Claude Code Markers**: Detects `Generated with [Claude Code]` signatures
3. **Commit Message Patterns**: Identifies commits mentioning Claude assistance
4. **Email Signatures**: Finds commits from `noreply@anthropic.com`
5. **Code Patterns**: Scans for Claude markers in code comments
6. **Copy-Paste Indicators**: Detects "copied from claude", "pasted from claude", "claude.ai chat" references
7. **AI References**: Detects anthropic.com mentions and claude.ai URLs

#### Cursor IDE Detection
8. **Cursor References**: Identifies Cursor IDE usage, especially when combined with Claude
9. **Cursor Config Files**: Detects `.cursor/` directories and configuration
10. **Cursor + Claude**: Specific patterns for Cursor using Claude backend

#### GitHub Copilot Detection
11. **Copilot Status Check**: Queries GitHub API to check if Copilot is enabled for repositories (requires org admin permissions)
12. **Copilot Markers**: Detects GitHub Copilot references in commits and code
13. **Claude in Copilot**: Identifies when Claude is used through GitHub Copilot

### Custom Patterns

You can extend detection capabilities by providing a custom `patterns.json` file with additional regex patterns for:
- **Signatures**: Named patterns for specific Claude markers
- **Commit Patterns**: Regex patterns to match in commit messages
- **Code Patterns**: Regex patterns to match in source code

Example custom pattern configuration:
```json
{
  "signatures": {
    "custom_cli": "(?i)generated with claude cli"
  },
  "commit_patterns": [
    "(?i)claude helped with this"
  ],
  "code_patterns": [
    "(?i)<!-- AI generated -->"
  ]
}
```

## GitHub API Rate Limits

- **Without authentication**: 60 requests per hour
- **With authentication**: 5,000 requests per hour

It is highly recommended to use a GitHub personal access token for scanning.

### Creating a GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `public_repo` (for public repositories)
4. Copy the token and use with `--token` or set as `GITHUB_TOKEN` environment variable

## Output Example

### Console Output
```
[*] Scanning repository: owner/repo
[*] Repository: owner/repo
[*] Description: Example project
[*] Stars: 100
[*] Scanning commits...
[!] DETECTION: a1b2c3d4 - signature_co_author
[*] Scanned 50 commits, found 1 detections

============================================================
SCAN SUMMARY
============================================================
Total Detections: 1
Repositories Affected: 1

Detections by Type:
  - signature_co_author: 1
============================================================
```

### JSON Output
```json
{
  "scan_timestamp": "2026-02-28T12:00:00",
  "total_detections": 1,
  "detections": [
    {
      "repository": "owner/repo",
      "commit_sha": "a1b2c3d4...",
      "commit_url": "https://github.com/owner/repo/commit/a1b2c3d4",
      "author": "Developer Name",
      "author_email": "dev@example.com",
      "commit_date": "2026-02-27T10:00:00Z",
      "commit_message": "Add feature\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
      "detection_type": "signature_co_author",
      "evidence": "Found pattern 'co_author' in commit message",
      "files_modified": ["src/main.py", "README.md"]
    }
  ]
}
```

## Architecture

- `shannon_revenge.py`: Main CLI interface with support for repo/user/org scanning
- `github_client.py`: GitHub API client with rate limiting and pagination
- `detector.py`: Claude detection logic with configurable pattern matching
- `output_formatter.py`: Output formatting for JSON, CSV, and text reports
- `patterns.json`: Default detection patterns (customizable)

## Use Cases

1. **Supply Chain Auditing**: Identify which dependencies or tools have Claude in their development history
2. **Organization Compliance**: Scan your entire GitHub organization for AI-generated code
3. **Repository Analysis**: Understand the extent of Claude usage in specific projects
4. **Custom Detection**: Add your own patterns to detect specific AI tooling markers

## License

This tool is provided as-is for identifying AI-generated code in supply chains.
