import base64
import logging
from typing import Dict, Any, List, Optional

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False

try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential_jitter,
        retry_if_exception_type,
    )
    _HAS_TENACITY = True
except ImportError:
    _HAS_TENACITY = False
    def retry(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

from app.core.config import settings
from app.core.security import get_github_app_jwt
from app.core.redis import redis_cache

logger = logging.getLogger(__name__)


class GitHubClientService:
    """
    Handles GitHub App installation authentication, token caching,
    PR diff retrieval, and inline review comments posting.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self, installation_id: int):
        self.installation_id = installation_id

    async def get_installation_token(self) -> str:
        cached_token = await redis_cache.get_installation_token(self.installation_id)
        if cached_token:
            return cached_token

        try:
            app_jwt = get_github_app_jwt()
        except Exception as e:
            logger.warning(f"Failed to generate GitHub App JWT: {e}. Using mock token.")
            return "mock_github_installation_token"

        if not _HAS_HTTPX:
            return "mock_github_installation_token"

        headers = {
            "Authorization": f"Bearer {app_jwt}",
            "Accept": "application/vnd.github.v3+json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/app/installations/{self.installation_id}/access_tokens",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            token = data["token"]
            await redis_cache.set_installation_token(self.installation_id, token, ttl_seconds=3000)
            return token

    async def _get_auth_headers(self, accept: str = "application/vnd.github.v3+json") -> Dict[str, str]:
        token = await self.get_installation_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "User-Agent": "Brittle-PR-Reviewer",
        }

    @retry(stop=stop_after_attempt(3) if _HAS_TENACITY else None)
    async def get_pr_diff(self, owner: str, repo: str, pull_number: int) -> str:
        if not _HAS_HTTPX:
            return (
                "diff --git a/src/main.py b/src/main.py\n"
                "--- a/src/main.py\n"
                "+++ b/src/main.py\n"
                "@@ -1,2 +1,3 @@\n"
                "+def new_feature():\n"
                "+    return True\n"
            )

        headers = await self._get_auth_headers(accept="application/vnd.github.v3.diff")
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pull_number}"
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    @retry(stop=stop_after_attempt(3) if _HAS_TENACITY else None)
    async def get_pr_details(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        if not _HAS_HTTPX:
            return {"number": pull_number, "title": "Mock PR", "user": {"login": "mock-user"}}
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pull_number}"
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.json()

    @retry(stop=stop_after_attempt(3) if _HAS_TENACITY else None)
    async def post_pr_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        commit_id: str,
        body: str,
        event: str = "COMMENT",
        comments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not _HAS_HTTPX:
            return {"id": 1001, "state": "SUBMITTED"}
        headers = await self._get_auth_headers()
        payload: Dict[str, Any] = {
            "commit_id": commit_id,
            "body": body,
            "event": event,
        }

        if comments:
            formatted_comments = []
            for c in comments:
                formatted_comments.append({
                    "path": c["path"],
                    "line": c["line"],
                    "side": c.get("side", "RIGHT"),
                    "body": c["body"],
                })
            payload["comments"] = formatted_comments

        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def get_repo_git_tree(self, owner: str, repo: str, commit_sha: str) -> List[Dict[str, Any]]:
        if not _HAS_HTTPX:
            return []
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient(timeout=45.0) as client:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/git/trees/{commit_sha}?recursive=1"
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("tree", [])

    async def get_blob_content(self, owner: str, repo: str, blob_sha: str) -> str:
        if not _HAS_HTTPX:
            return ""
        headers = await self._get_auth_headers()
        async with httpx.AsyncClient(timeout=20.0) as client:
            url = f"{self.BASE_URL}/repos/{owner}/{repo}/git/blobs/{blob_sha}"
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            encoding = data.get("encoding", "base64")
            raw_content = data.get("content", "")
            if encoding == "base64":
                return base64.b64decode(raw_content).decode("utf-8", errors="replace")
            return raw_content
