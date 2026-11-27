from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import CodeChunk


class VectorRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_upsert_chunks(self, chunks_data: List[Dict[str, Any]]) -> int:
        """
        Batched upsert into PostgreSQL using ON CONFLICT DO UPDATE.
        Expects chunks_data to have keys matching CodeChunk fields.
        """
        if not chunks_data:
            return 0

        # Process in batches of 100 for memory and network efficiency
        batch_size = 100
        inserted_count = 0

        for i in range(0, len(chunks_data), batch_size):
            batch = chunks_data[i:i + batch_size]
            stmt = insert(CodeChunk).values(batch)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_repo_file_chunk",
                set_={
                    "commit_sha": stmt.excluded.commit_sha,
                    "language": stmt.excluded.language,
                    "chunk_type": stmt.excluded.chunk_type,
                    "symbol_name": stmt.excluded.symbol_name,
                    "start_line": stmt.excluded.start_line,
                    "end_line": stmt.excluded.end_line,
                    "content": stmt.excluded.content,
                    "embedding": stmt.excluded.embedding,
                    "meta_info": stmt.excluded.meta_info,
                }
            )
            await self.db.execute(stmt)
            inserted_count += len(batch)

        await self.db.flush()
        return inserted_count

    async def search_similar_chunks(
        self,
        repository_id: int,
        query_embedding: List[float],
        top_k: int = 6,
        exclude_file_paths: Optional[List[str]] = None
    ) -> List[CodeChunk]:
        """
        Performs vector similarity search via pgvector cosine distance operator (<=>).
        """
        # Cosine distance ordering
        distance_col = CodeChunk.embedding.cosine_distance(query_embedding).label("distance")
        
        stmt = (
            select(CodeChunk)
            .where(CodeChunk.repository_id == repository_id)
            .where(CodeChunk.embedding.isnot(None))
        )

        if exclude_file_paths:
            stmt = stmt.where(CodeChunk.file_path.notin_(exclude_file_paths))

        stmt = stmt.order_by(distance_col).limit(top_k)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_chunks_for_files(self, repository_id: int, file_paths: List[str]) -> int:
        """Deletes code chunks for specified files during incremental indexing."""
        if not file_paths:
            return 0
        stmt = delete(CodeChunk).where(
            CodeChunk.repository_id == repository_id,
            CodeChunk.file_path.in_(file_paths)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
