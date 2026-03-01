import time
import requests
from typing import Optional, Dict, List, Generator
from datetime import datetime


class GitHubAPIClient:
    """GitHub API client with rate limiting and pagination support."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client.

        Args:
            token: GitHub personal access token (optional but recommended for higher rate limits)
        """
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})
        self.session.headers.update({"Accept": "application/vnd.github.v3+json"})

    def _get_rate_limit_info(self) -> Dict:
        """Get current rate limit status."""
        response = self.session.get(f"{self.BASE_URL}/rate_limit")
        response.raise_for_status()
        return response.json()

    def _wait_for_rate_limit(self):
        """Wait if rate limit is exceeded."""
        rate_limit = self._get_rate_limit_info()
        core_remaining = rate_limit["resources"]["core"]["remaining"]

        if core_remaining < 10:
            reset_time = rate_limit["resources"]["core"]["reset"]
            wait_time = reset_time - time.time() + 5
            if wait_time > 0:
                print(f"Rate limit nearly exceeded. Waiting {int(wait_time)} seconds...")
                time.sleep(wait_time)

    def _paginated_get(self, url: str, params: Optional[Dict] = None) -> Generator[Dict, None, None]:
        """
        Make paginated GET requests to GitHub API.

        Args:
            url: API endpoint URL
            params: Query parameters

        Yields:
            Items from paginated response
        """
        if params is None:
            params = {}

        params["per_page"] = 100
        page = 1

        while True:
            self._wait_for_rate_limit()
            params["page"] = page

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                if not data:
                    break
                yield from data
            else:
                yield data
                break

            page += 1

    def get_repo_commits(self, owner: str, repo: str, since: Optional[str] = None) -> Generator[Dict, None, None]:
        """
        Get commits for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            since: Only commits after this date (ISO 8601 format)

        Yields:
            Commit objects
        """
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits"
        params = {}
        if since:
            params["since"] = since

        yield from self._paginated_get(url, params)

    def get_commit_detail(self, owner: str, repo: str, sha: str) -> Dict:
        """
        Get detailed information about a specific commit.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA

        Returns:
            Detailed commit object
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/repos/{owner}/{repo}/commits/{sha}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_repo_info(self, owner: str, repo: str) -> Dict:
        """
        Get repository information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository object
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/repos/{owner}/{repo}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def search_repositories(self, query: str) -> Generator[Dict, None, None]:
        """
        Search for repositories.

        Args:
            query: Search query

        Yields:
            Repository objects
        """
        url = f"{self.BASE_URL}/search/repositories"
        params = {"q": query}

        page = 1
        while True:
            self._wait_for_rate_limit()
            params["page"] = page
            params["per_page"] = 100

            response = self.session.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            if not items:
                break

            yield from items
            page += 1

            if page > 10:
                break

    def get_org_repos(self, org: str) -> Generator[Dict, None, None]:
        """
        Get all repositories for an organization.

        Args:
            org: Organization name

        Yields:
            Repository objects
        """
        url = f"{self.BASE_URL}/orgs/{org}/repos"
        params = {"type": "all", "sort": "updated"}
        yield from self._paginated_get(url, params)

    def get_org_info(self, org: str) -> Dict:
        """
        Get organization information.

        Args:
            org: Organization name

        Returns:
            Organization object
        """
        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/orgs/{org}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_org_members(self, org: str) -> Generator[Dict, None, None]:
        """
        Get all members of an organization.

        Args:
            org: Organization name

        Yields:
            User objects
        """
        url = f"{self.BASE_URL}/orgs/{org}/members"
        yield from self._paginated_get(url)

    def check_copilot_enabled(self, owner: str, repo: str) -> Dict:
        """
        Check if GitHub Copilot is enabled for a repository.
        Note: This requires organization admin permissions.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Dictionary with Copilot status information
        """
        self._wait_for_rate_limit()

        result = {
            "copilot_enabled": False,
            "copilot_accessible": False,
            "detection_method": None
        }

        try:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}"
            response = self.session.get(url)
            response.raise_for_status()
            repo_data = response.json()

            if repo_data.get("organization"):
                org_login = repo_data["organization"]["login"]

                try:
                    org_url = f"{self.BASE_URL}/orgs/{org_login}/copilot/billing/seats"
                    org_response = self.session.get(org_url)

                    if org_response.status_code == 200:
                        result["copilot_enabled"] = True
                        result["copilot_accessible"] = True
                        result["detection_method"] = "org_api"
                    elif org_response.status_code == 403:
                        result["copilot_accessible"] = False
                        result["detection_method"] = "permission_denied"
                except Exception:
                    pass

            return result

        except Exception as e:
            result["error"] = str(e)
            return result

    def search_code(self, query: str, repo: Optional[str] = None) -> Generator[Dict, None, None]:
        """
        Search for code in repositories.

        Args:
            query: Search query
            repo: Optional repository filter (format: owner/repo)

        Yields:
            Code search results
        """
        url = f"{self.BASE_URL}/search/code"

        full_query = query
        if repo:
            full_query = f"{query} repo:{repo}"

        params = {"q": full_query, "per_page": 100}
        page = 1

        while True:
            self._wait_for_rate_limit()
            params["page"] = page

            try:
                response = self.session.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                items = data.get("items", [])

                if not items:
                    break

                yield from items
                page += 1

                if page > 10:
                    break

            except Exception as e:
                print(f"[!] Code search error: {e}")
                break
