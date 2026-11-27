from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Installation, Repository, IndexingStatus


class RepoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_installation_by_gh_id(self, github_installation_id: int) -> Optional[Installation]:
        stmt = select(Installation).where(Installation.github_installation_id == github_installation_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_installation(
        self,
        github_installation_id: int,
        account_login: str,
        account_type: str = "User",
        avatar_url: Optional[str] = None
    ) -> Installation:
        inst = await self.get_installation_by_gh_id(github_installation_id)
        if inst:
            inst.account_login = account_login
            inst.account_type = account_type
            inst.avatar_url = avatar_url
            inst.updated_at = datetime.utcnow()
        else:
            inst = Installation(
                github_installation_id=github_installation_id,
                account_login=account_login,
                account_type=account_type,
                avatar_url=avatar_url,
            )
            self.db.add(inst)
        await self.db.flush()
        return inst

    async def get_repo_by_id(self, repo_id: int) -> Optional[Repository]:
        stmt = select(Repository).where(Repository.id == repo_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_repo_by_gh_id(self, github_repo_id: int) -> Optional[Repository]:
        stmt = select(Repository).where(Repository.github_repo_id == github_repo_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_repo_by_full_name(self, full_name: str) -> Optional[Repository]:
        stmt = select(Repository).where(Repository.full_name == full_name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_repositories(self, skip: int = 0, limit: int = 50) -> List[Repository]:
        stmt = select(Repository).order_by(Repository.updated_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def upsert_repository(
        self,
        github_repo_id: int,
        installation_id: int,
        name: str,
        full_name: str,
        owner: str,
        is_private: bool = False,
        default_branch: str = "main",
    ) -> Repository:
        repo = await self.get_repo_by_gh_id(github_repo_id)
        if repo:
            repo.installation_id = installation_id
            repo.name = name
            repo.full_name = full_name
            repo.owner = owner
            repo.is_private = is_private
            repo.default_branch = default_branch
            repo.updated_at = datetime.utcnow()
        else:
            repo = Repository(
                github_repo_id=github_repo_id,
                installation_id=installation_id,
                name=name,
                full_name=full_name,
                owner=owner,
                is_private=is_private,
                default_branch=default_branch,
                indexing_status=IndexingStatus.PENDING,
                rules={},
            )
            self.db.add(repo)
        await self.db.flush()
        return repo

    async def update_rules(self, repo_id: int, rules: Dict[str, Any]) -> Optional[Repository]:
        repo = await self.get_repo_by_id(repo_id)
        if repo:
            repo.rules = rules
            repo.updated_at = datetime.utcnow()
            await self.db.flush()
        return repo

    async def delete_repository(self, repo_id: int) -> bool:
        stmt = delete(Repository).where(Repository.id == repo_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return bool(result.rowcount and result.rowcount > 0)

    async def update_indexing_status(
        self,
        repo_id: int,
        status: IndexingStatus,
        commit_sha: Optional[str] = None
    ) -> Optional[Repository]:
        repo = await self.get_repo_by_id(repo_id)
        if repo:
            repo.indexing_status = status
            if commit_sha:
                repo.indexed_commit_sha = commit_sha
            if status == IndexingStatus.COMPLETED:
                repo.last_indexed_at = datetime.utcnow()
            repo.updated_at = datetime.utcnow()
            await self.db.flush()
        return repo

    async def delete_repository(self, repo_id: int) -> bool:
        stmt = delete(Repository).where(Repository.id == repo_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return bool(result.rowcount and result.rowcount > 0)
