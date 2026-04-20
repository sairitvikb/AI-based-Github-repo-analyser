from __future__ import annotations

import base64
import logging
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.utils.repository_filters import is_supported_source_file, infer_language_from_path

logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self) -> None:
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
        self.client = httpx.Client(base_url=settings.github_api_base_url, headers=headers, timeout=30.0)

    def parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        parsed = urlparse(repo_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
        return path_parts[0], path_parts[1].replace('.git', '')

    def get_repository_metadata(self, owner: str, repo: str) -> dict:
        response = self.client.get(f"/repos/{owner}/{repo}")
        self._raise_for_status(response)
        return response.json()

    def get_language_breakdown(self, owner: str, repo: str) -> dict[str, int]:
        response = self.client.get(f"/repos/{owner}/{repo}/languages")
        self._raise_for_status(response)
        return response.json()

    def get_repository_tree(self, owner: str, repo: str, branch: str) -> list[dict]:
        response = self.client.get(f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        self._raise_for_status(response)
        data = response.json()
        return data.get("tree", [])

    def fetch_repository_files(self, owner: str, repo: str, branch: str) -> list[dict]:
        tree = self.get_repository_tree(owner, repo, branch)
        files: list[dict] = []
        for item in tree:
            if item.get("type") != "blob":
                continue
            path = item.get("path", "")
            if not is_supported_source_file(path):
                continue
            if item.get("size", 0) > settings.max_file_bytes:
                continue
            files.append(
                {
                    "path": path,
                    "sha": item.get("sha"),
                    "size": item.get("size", 0),
                    "language": infer_language_from_path(path),
                }
            )
            if len(files) >= settings.max_files_to_analyze:
                break
        return files

    def get_file_content(self, owner: str, repo: str, path: str) -> str:
        response = self.client.get(f"/repos/{owner}/{repo}/contents/{path}")
        self._raise_for_status(response)
        data = response.json()
        encoded_content = data.get("content", "")
        if not encoded_content:
            return ""
        return base64.b64decode(encoded_content).decode("utf-8", errors="ignore")

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 403 and "rate limit" in response.text.lower():
            raise ValueError("GitHub API rate limit reached. Add a token or try again later.")
        if response.status_code == 404:
            raise ValueError("Repository or file not found. Check the URL and access level.")
        response.raise_for_status()
