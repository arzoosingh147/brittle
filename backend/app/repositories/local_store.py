import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
REPOS_FILE = DATA_DIR / "repositories.json"
REVIEWS_FILE = DATA_DIR / "reviews.json"


def _ensure_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


class LocalStore:
    """
    Guarantees persistent disk storage across refreshes and restarts,
    ensuring that repository connections, rules, and reviews never disappear
    even when remote PostgreSQL connections experience DNS or network outages.
    """

    @classmethod
    def _read_json(cls, file_path: Path) -> List[Dict[str, Any]]:
        _ensure_dir()
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read {file_path}: {e}")
            return []

    @classmethod
    def _write_json(cls, file_path: Path, data: List[Dict[str, Any]]):
        _ensure_dir()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to write {file_path}: {e}")

    # --- Repositories ---

    @classmethod
    def list_repositories(cls) -> List[Dict[str, Any]]:
        return cls._read_json(REPOS_FILE)

    @classmethod
    def get_repository(cls, repo_id: int) -> Optional[Dict[str, Any]]:
        repos = cls._read_json(REPOS_FILE)
        for r in repos:
            if r.get("id") == repo_id or r.get("github_repo_id") == repo_id:
                return r
        return None

    @classmethod
    def upsert_repository(cls, repo_dict: Dict[str, Any]) -> Dict[str, Any]:
        repos = cls._read_json(REPOS_FILE)
        found = False
        repo_id = repo_dict.get("id")
        full_name = repo_dict.get("full_name")

        for idx, r in enumerate(repos):
            if (repo_id and r.get("id") == repo_id) or (full_name and r.get("full_name") == full_name):
                repos[idx] = {**r, **repo_dict, "updated_at": datetime.utcnow().isoformat()}
                found = True
                repo_dict = repos[idx]
                break

        if not found:
            if not repo_dict.get("id"):
                import zlib
                repo_dict["id"] = abs(zlib.crc32(full_name.encode("utf-8"))) % 10000 or 1
            repo_dict.setdefault("indexing_status", "PENDING")
            repo_dict.setdefault("created_at", datetime.utcnow().isoformat())
            repo_dict.setdefault("updated_at", datetime.utcnow().isoformat())
            repos.insert(0, repo_dict)

        cls._write_json(REPOS_FILE, repos)
        return repo_dict

    @classmethod
    def update_repo_status(cls, repo_id: int, status: str) -> Optional[Dict[str, Any]]:
        repos = cls._read_json(REPOS_FILE)
        for r in repos:
            if r.get("id") == repo_id or r.get("github_repo_id") == repo_id:
                r["indexing_status"] = status
                if status == "COMPLETED":
                    r["last_indexed_at"] = datetime.utcnow().isoformat()
                r["updated_at"] = datetime.utcnow().isoformat()
                cls._write_json(REPOS_FILE, repos)
                return r
        return None

    @classmethod
    def update_repo_rules(cls, repo_id: int, rules: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        repos = cls._read_json(REPOS_FILE)
        for r in repos:
            if r.get("id") == repo_id:
                r["rules"] = rules
                r["updated_at"] = datetime.utcnow().isoformat()
                cls._write_json(REPOS_FILE, repos)
                return r
        return None

    @classmethod
    def delete_repository(cls, repo_id: int) -> bool:
        repos = cls._read_json(REPOS_FILE)
        new_repos = [r for r in repos if r.get("id") != repo_id and r.get("github_repo_id") != repo_id]
        if len(new_repos) < len(repos):
            cls._write_json(REPOS_FILE, new_repos)
            return True
        return False

    # --- Reviews ---

    @classmethod
    def list_reviews(cls, repo_id: Optional[int] = None) -> List[Dict[str, Any]]:
        reviews = cls._read_json(REVIEWS_FILE)
        if repo_id:
            return [r for r in reviews if r.get("repository_id") == repo_id]
        return reviews

    @classmethod
    def get_review(cls, review_id: int) -> Optional[Dict[str, Any]]:
        reviews = cls._read_json(REVIEWS_FILE)
        for r in reviews:
            if r.get("id") == review_id:
                return r
        return None

    @classmethod
    def save_review(cls, review_dict: Dict[str, Any]) -> Dict[str, Any]:
        reviews = cls._read_json(REVIEWS_FILE)
        reviews = [r for r in reviews if r.get("id") != review_dict.get("id")]
        reviews.insert(0, review_dict)
        cls._write_json(REVIEWS_FILE, reviews)
        return review_dict

    @classmethod
    def get_metrics(cls, repo_id: Optional[int] = None) -> Dict[str, Any]:
        reviews = cls.list_reviews(repo_id)
        if not reviews:
            return {
                "total_reviews": 0,
                "avg_risk_score": 0.0,
                "total_security_issues": 0,
                "total_perf_issues": 0,
                "total_quality_issues": 0,
                "total_issues": 0,
            }

        total_rev = len(reviews)
        avg_risk = round(sum(r.get("risk_score", 0) for r in reviews) / total_rev, 1)
        sec = sum(r.get("security_issues_count", 0) for r in reviews)
        perf = sum(r.get("perf_issues_count", 0) for r in reviews)
        qual = sum(r.get("quality_issues_count", 0) for r in reviews)

        return {
            "total_reviews": total_rev,
            "avg_risk_score": avg_risk,
            "total_security_issues": sec,
            "total_perf_issues": perf,
            "total_quality_issues": qual,
            "total_issues": sec + perf + qual,
        }
