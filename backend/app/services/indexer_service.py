import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import IndexingStatus, Repository
from app.repositories.repo_repository import RepoRepository
from app.repositories.vector_repository import VectorRepository
from app.services.github_service import GitHubClientService
from app.services.ast_chunker import ASTChunkerService
from app.services.diff_parser import DiffParserService
from app.core.llm import LLMFactory

logger = logging.getLogger(__name__)


class RepoIndexerService:
    """
    Orchestrates repository indexing:
    - Fetches files from GitHub
    - Chunks code via ASTChunkerService in worker threads
    - Generates batched vector embeddings
    - Upserts chunks into PostgreSQL via pgvector
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo_repo = RepoRepository(db)
        self.vector_repo = VectorRepository(db)
        self.embedding_model = LLMFactory.get_embedding_model()

    async def index_repository(self, repository: Repository, commit_sha: Optional[str] = None) -> bool:
        repo_id = repository.id
        await self.repo_repo.update_indexing_status(repo_id, IndexingStatus.INDEXING)

        try:
            gh_client = GitHubClientService(repository.installation.github_installation_id)
            target_sha = commit_sha or repository.default_branch

            # 1. Fetch file tree
            tree = await gh_client.get_repo_git_tree(repository.owner, repository.name, target_sha)

            # 2. Filter code files
            code_blobs = []
            for item in tree:
                path = item.get("path", "")
                if item.get("type") != "blob":
                    continue
                if DiffParserService.should_ignore_file(path):
                    continue
                # Keep file size reasonable (< 200KB)
                if item.get("size", 0) > 200 * 1024:
                    continue
                code_blobs.append(item)

            # Limit to initial 150 important code files for budget & performance
            code_blobs = code_blobs[:150]
            logger.info(f"Indexing {len(code_blobs)} files for {repository.full_name}")

            all_chunk_dicts: List[Dict[str, Any]] = []

            # 3. Fetch blobs and chunk
            for blob_item in code_blobs:
                file_path = blob_item["path"]
                blob_sha = blob_item["sha"]
                try:
                    content = await gh_client.get_blob_content(repository.owner, repository.name, blob_sha)
                    chunks = await ASTChunkerService.chunk_code_async(
                        file_path=file_path,
                        content=content,
                        commit_sha=target_sha,
                    )
                    for ch in chunks:
                        all_chunk_dicts.append({
                            "repository_id": repo_id,
                            "file_path": ch.file_path,
                            "commit_sha": ch.commit_sha,
                            "language": ch.language,
                            "chunk_type": ch.chunk_type,
                            "symbol_name": ch.symbol_name,
                            "start_line": ch.start_line,
                            "end_line": ch.end_line,
                            "content": ch.content,
                            "content_hash": ch.content_hash,
                            "meta_info": ch.metadata,
                        })
                except Exception as ex:
                    logger.warning(f"Failed to fetch/chunk {file_path}: {ex}")

            if not all_chunk_dicts:
                await self.repo_repo.update_indexing_status(repo_id, IndexingStatus.COMPLETED, target_sha)
                return True

            # 4. Batched vector embeddings (50 chunks per batch)
            batch_size = 50
            for i in range(0, len(all_chunk_dicts), batch_size):
                batch = all_chunk_dicts[i : i + batch_size]
                texts = [
                    f"{c['file_path']} ({c['chunk_type']} {c.get('symbol_name') or ''}):\n{c['content']}"
                    for c in batch
                ]
                embeddings = self.embedding_model.embed_documents(texts)
                for c, emb in zip(batch, embeddings):
                    c["embedding"] = emb

            # 5. Bulk upsert into vector database
            await self.vector_repo.bulk_upsert_chunks(all_chunk_dicts)
            await self.repo_repo.update_indexing_status(repo_id, IndexingStatus.COMPLETED, target_sha)
            logger.info(f"Successfully indexed {len(all_chunk_dicts)} chunks for {repository.full_name}")
            return True

        except Exception as e:
            logger.exception(f"Repository indexing failed for {repository.full_name}: {e}")
            await self.repo_repo.update_indexing_status(repo_id, IndexingStatus.FAILED)
            return False
