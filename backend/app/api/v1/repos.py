import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.repositories.repo_repository import RepoRepository
from app.repositories.local_store import LocalStore
from app.workers.tasks import QueueDispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repos", tags=["Repositories"])


class RepoCreate(BaseModel):
    name: str = Field(..., description="Repository name or slug/URL, e.g. 'projectecofy' or 'arzoosingh147/projectecofy'")
    owner: Optional[str] = Field(None, description="Repository owner, e.g. 'arzoosingh147'")
    default_branch: str = Field("main", description="Default branch, e.g. main or master")
    is_private: bool = Field(False)
    rules: Optional[Dict[str, Any]] = Field(default_factory=dict)
    auto_index: bool = Field(True, description="Whether to trigger indexing immediately upon connection")


class RepoRulesUpdate(BaseModel):
    rules: Dict[str, Any] = Field(
        ...,
        description="Dictionary of custom rules, e.g. {'max_lines_per_function': 50, 'forbidden_imports': ['pickle']}"
    )


class RepoResponse(BaseModel):
    id: int
    github_repo_id: int
    name: str
    full_name: str
    owner: str
    is_private: bool
    default_branch: str
    indexing_status: str
    last_indexed_at: Any
    rules: Dict[str, Any]


@router.get("", response_model=List[RepoResponse])
async def list_repositories(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all connected GitHub repositories."""
    try:
        repo_repo = RepoRepository(db)
        repos = await repo_repo.list_repositories(skip=skip, limit=limit)
        if repos:
            # Sync into local store for instant offline persistence
            for r in repos:
                LocalStore.upsert_repository({
                    "id": r.id,
                    "github_repo_id": r.github_repo_id,
                    "name": r.name,
                    "full_name": r.full_name,
                    "owner": r.owner,
                    "is_private": r.is_private,
                    "default_branch": r.default_branch,
                    "indexing_status": r.indexing_status.value if hasattr(r.indexing_status, "value") else str(r.indexing_status),
                    "last_indexed_at": r.last_indexed_at,
                    "rules": r.rules or {},
                })
            return [
                RepoResponse(
                    id=r.id,
                    github_repo_id=r.github_repo_id,
                    name=r.name,
                    full_name=r.full_name,
                    owner=r.owner,
                    is_private=r.is_private,
                    default_branch=r.default_branch,
                    indexing_status=r.indexing_status.value if hasattr(r.indexing_status, "value") else str(r.indexing_status),
                    last_indexed_at=r.last_indexed_at,
                    rules=r.rules or {},
                )
                for r in repos
            ]
    except Exception as e:
        logger.warning(f"Database list_repositories unavailable, reading persistent disk cache: {e}")

    # Fallback to persistent disk store so connected repos never vanish on refresh
    cached = LocalStore.list_repositories()
    return [
        RepoResponse(
            id=r["id"],
            github_repo_id=r.get("github_repo_id", r["id"]),
            name=r["name"],
            full_name=r["full_name"],
            owner=r["owner"],
            is_private=r.get("is_private", False),
            default_branch=r.get("default_branch", "main"),
            indexing_status=r.get("indexing_status", "PENDING"),
            last_indexed_at=r.get("last_indexed_at"),
            rules=r.get("rules", {}),
        )
        for r in cached[skip : skip + limit]
    ]


@router.get("/{repo_id}", response_model=RepoResponse)
async def get_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Get single repository details."""
    try:
        repo_repo = RepoRepository(db)
        repo = await repo_repo.get_repo_by_id(repo_id)
        if repo:
            return RepoResponse(
                id=repo.id,
                github_repo_id=repo.github_repo_id,
                name=repo.name,
                full_name=repo.full_name,
                owner=repo.owner,
                is_private=repo.is_private,
                default_branch=repo.default_branch,
                indexing_status=repo.indexing_status.value if hasattr(repo.indexing_status, "value") else str(repo.indexing_status),
                last_indexed_at=repo.last_indexed_at,
                rules=repo.rules or {},
            )
    except Exception as e:
        logger.warning(f"Database get_repo_by_id unavailable: {e}")

    cached = LocalStore.get_repository(repo_id)
    if not cached:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    return RepoResponse(
        id=cached["id"],
        github_repo_id=cached.get("github_repo_id", cached["id"]),
        name=cached["name"],
        full_name=cached["full_name"],
        owner=cached["owner"],
        is_private=cached.get("is_private", False),
        default_branch=cached.get("default_branch", "main"),
        indexing_status=cached.get("indexing_status", "PENDING"),
        last_indexed_at=cached.get("last_indexed_at"),
        rules=cached.get("rules", {}),
    )


@router.post("/{repo_id}/index")
async def trigger_repo_indexing(
    repo_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger background indexing of the repository codebase."""
    try:
        repo_repo = RepoRepository(db)
        repo = await repo_repo.get_repo_by_id(repo_id)
    except Exception as e:
        logger.warning(f"Database get_repo_by_id unavailable: {e}")
        repo = None

    if not repo:
        cached = LocalStore.get_repository(repo_id)
        if not cached:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    LocalStore.update_repo_status(repo_id, "INDEXING")

    try:
        QueueDispatcher.dispatch_repo_indexing(background_tasks, repo_id)
    except Exception as e:
        logger.warning(f"Queue dispatch skipped: {e}")

    return {"message": "Indexing triggered", "repo_id": repo_id, "status": "INDEXING"}


@router.put("/{repo_id}/rules", response_model=RepoResponse)
async def update_repository_rules(
    repo_id: int,
    payload: RepoRulesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update custom AI review rules for the repository."""
    LocalStore.update_repo_rules(repo_id, payload.rules)

    try:
        repo_repo = RepoRepository(db)
        repo = await repo_repo.update_rules(repo_id, payload.rules)
        if repo:
            await db.commit()
            return RepoResponse(
                id=repo.id,
                github_repo_id=repo.github_repo_id,
                name=repo.name,
                full_name=repo.full_name,
                owner=repo.owner,
                is_private=repo.is_private,
                default_branch=repo.default_branch,
                indexing_status=repo.indexing_status.value if hasattr(repo.indexing_status, "value") else str(repo.indexing_status),
                last_indexed_at=repo.last_indexed_at,
                rules=repo.rules or {},
            )
    except Exception as e:
        logger.warning(f"Database update_rules unavailable: {e}")

    cached = LocalStore.get_repository(repo_id)
    if not cached:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    return RepoResponse(
        id=cached["id"],
        github_repo_id=cached.get("github_repo_id", cached["id"]),
        name=cached["name"],
        full_name=cached["full_name"],
        owner=cached["owner"],
        is_private=cached.get("is_private", False),
        default_branch=cached.get("default_branch", "main"),
        indexing_status=cached.get("indexing_status", "PENDING"),
        last_indexed_at=cached.get("last_indexed_at"),
        rules=payload.rules,
    )


@router.post("", response_model=RepoResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    payload: RepoCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Connects and stores a new GitHub repository into the database.
    Accepts full GitHub URLs (e.g. 'https://github.com/owner/repo') or slugs ('owner/repo').
    """
    import zlib
    repo_repo = RepoRepository(db)

    raw_name = payload.name.strip()
    if "github.com/" in raw_name:
        parts = raw_name.split("github.com/")[-1].strip("/").split("/")
        owner = parts[0]
        name = parts[1] if len(parts) > 1 else parts[0]
    elif "/" in raw_name:
        parts = raw_name.split("/")
        owner = parts[0]
        name = parts[1]
    else:
        owner = payload.owner.strip() if payload.owner else "github-user"
        name = raw_name

    full_name = f"{owner}/{name}"

    # Deterministic github_repo_id based on full_name CRC32
    gh_repo_id = abs(zlib.crc32(full_name.encode("utf-8"))) or 123456
    repo_id = gh_repo_id % 10000 or 1
    indexing_status = "PENDING"
    last_indexed = None

    try:
        # Ensure demo/default installation exists
        inst = await repo_repo.get_installation_by_gh_id(1)
        if not inst:
            inst = await repo_repo.upsert_installation(
                github_installation_id=1,
                account_login=owner,
                account_type="User",
                avatar_url=f"https://github.com/{owner}.png",
            )
        inst_id = getattr(inst, "id", None) or 1

        repo = await repo_repo.upsert_repository(
            github_repo_id=gh_repo_id,
            installation_id=inst_id,
            name=name,
            full_name=full_name,
            owner=owner,
            is_private=payload.is_private,
            default_branch=payload.default_branch or "main",
        )

        if payload.rules:
            await repo_repo.update_rules(repo.id, payload.rules)

        await db.commit()

        repo_id = getattr(repo, "id", repo_id)
        indexing_status = repo.indexing_status.value if hasattr(repo.indexing_status, "value") else str(repo.indexing_status)
        last_indexed = getattr(repo, "last_indexed_at", None)

        if payload.auto_index and repo_id:
            try:
                QueueDispatcher.dispatch_repo_indexing(background_tasks, repo_id)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Database write failed for repo creation, falling back: {e}")

    # Always persist locally to disk so it survives refreshes & restarts
    local_record = LocalStore.upsert_repository({
        "id": repo_id,
        "github_repo_id": gh_repo_id,
        "name": name,
        "full_name": full_name,
        "owner": owner,
        "is_private": payload.is_private,
        "default_branch": payload.default_branch or "main",
        "indexing_status": indexing_status,
        "last_indexed_at": last_indexed,
        "rules": payload.rules or {},
    })

    return RepoResponse(
        id=local_record["id"],
        github_repo_id=local_record["github_repo_id"],
        name=local_record["name"],
        full_name=local_record["full_name"],
        owner=local_record["owner"],
        is_private=local_record["is_private"],
        default_branch=local_record["default_branch"],
        indexing_status=local_record["indexing_status"],
        last_indexed_at=local_record["last_indexed_at"],
        rules=local_record["rules"],
    )


@router.delete("/{repo_id}", status_code=status.HTTP_200_OK)
async def delete_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Disconnect and delete a repository."""
    LocalStore.delete_repository(repo_id)

    try:
        repo_repo = RepoRepository(db)
        await repo_repo.delete_repository(repo_id)
        await db.commit()
    except Exception as e:
        logger.warning(f"Database delete_repository unavailable: {e}")

    return {"message": "Repository removed successfully", "id": repo_id}
