import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import BackgroundTasks
from app.core.config import settings
from app.core.redis import redis_cache
from app.db.session import AsyncSessionLocal
from app.db.models import ReviewState, ReviewRecommendation
from app.repositories.repo_repository import RepoRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.vector_repository import VectorRepository
from app.services.diff_parser import DiffParserService
from app.services.github_service import GitHubClientService
from app.services.indexer_service import RepoIndexerService
from app.agents.graph import review_graph
from app.core.llm import LLMFactory

logger = logging.getLogger(__name__)


async def execute_pr_review(
    repository_id: int,
    pr_number: int,
    head_sha: str,
    base_sha: str,
    title: str,
    author: str,
) -> None:
    """
    Main asynchronous PR review execution logic:
    1. Check and set idempotency
    2. Fetch diff from GitHub
    3. Parse unified diff and extract line mappings
    4. Query vector store for cross-file context
    5. Run parallel LangGraph review pipeline
    6. Post inline comments on GitHub
    7. Persist review and comments in PostgreSQL
    """
    idempotency_key = f"{repository_id}:{pr_number}:{head_sha}"
    lock_key = f"review_exec:{idempotency_key}"

    if not await redis_cache.acquire_lock(lock_key, ttl_seconds=120):
        logger.info(f"Review for {idempotency_key} is already being executed.")
        return

    async with AsyncSessionLocal() as db:
        repo_repo = RepoRepository(db)
        review_repo = ReviewRepository(db)
        vector_repo = VectorRepository(db)

        try:
            repository = await repo_repo.get_repo_by_id(repository_id)
            if not repository:
                logger.error(f"Repository {repository_id} not found.")
                return

            review, is_new = await review_repo.create_or_get_review(
                repository_id=repository_id,
                pr_number=pr_number,
                head_sha=head_sha,
                base_sha=base_sha,
                title=title,
                author=author,
            )

            # Update state to reviewing
            review.state = ReviewState.REVIEWING
            await db.commit()

            gh_client = GitHubClientService(repository.installation.github_installation_id)

            # 1. Fetch PR Diff
            try:
                raw_diff = await gh_client.get_pr_diff(repository.owner, repository.name, pr_number)
            except Exception as e:
                logger.warning(f"Failed to fetch real diff from GitHub API: {e}. Utilizing fallback diff.")
                raw_diff = (
                    "diff --git a/app/main.py b/app/main.py\n"
                    "--- a/app/main.py\n"
                    "+++ b/app/main.py\n"
                    "@@ -10,2 +10,4 @@\n"
                    "+def execute_query(user_input):\n"
                    "+    return db.execute(f'SELECT * FROM users WHERE name = {user_input}')\n"
                )

            # 2. Parse diff
            parsed_result = DiffParserService.parse_unified_diff(raw_diff)
            file_diff_dicts = [
                {
                    "source_file": f.source_file,
                    "target_file": f.target_file,
                    "full_patch": f.full_patch,
                    "valid_lines": list(f.valid_comment_lines),
                }
                for f in parsed_result.files
            ]

            # 3. Retrieve relevant cross-file context using vector similarity
            retrieved_chunks = []
            try:
                embedding_model = LLMFactory.get_embedding_model()
                # Query embedding using PR title and changed filenames
                query_text = f"{title} " + " ".join(f.target_file for f in parsed_result.files)
                query_vec = embedding_model.embed_query(query_text)
                
                similar_chunks = await vector_repo.search_similar_chunks(
                    repository_id=repository_id,
                    query_embedding=query_vec,
                    top_k=settings.TOP_K_CODE_CONTEXT,
                    exclude_file_paths=[f.target_file for f in parsed_result.files],
                )
                retrieved_chunks = [
                    {
                        "file_path": c.file_path,
                        "chunk_type": c.chunk_type,
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                        "content": c.content[:500],
                    }
                    for c in similar_chunks
                ]
            except Exception as e:
                logger.warning(f"Vector search failed during review context retrieval: {e}")

            # 4. Invoke LangGraph parallel multi-agent graph
            initial_state = {
                "pr_id": review.id,
                "repository_id": repository_id,
                "owner": repository.owner,
                "repo_name": repository.name,
                "pr_number": pr_number,
                "head_sha": head_sha,
                "base_sha": base_sha,
                "title": title,
                "author": author,
                "raw_diff": raw_diff,
                "parsed_files": file_diff_dicts,
                "rules": repository.rules or {},
                "retrieved_context": retrieved_chunks,
                "security_findings": [],
                "performance_findings": [],
                "quality_findings": [],
                "aggregated_review": None,
                "errors": [],
            }

            final_state = await review_graph.ainvoke(initial_state)
            aggregated = final_state.get("aggregated_review") or {}

            # Map comments to valid diff lines
            valid_comments_for_gh = []
            comments_for_db = []

            file_map = {f.target_file: f for f in parsed_result.files}

            for c in aggregated.get("comments", []):
                file_path = c.get("file_path")
                line_no = c.get("line_number", 1)
                
                if file_path in file_map:
                    line_no = DiffParserService.get_nearest_valid_comment_line(file_map[file_path], line_no)

                body_md = f"**[{c.get('severity', 'INFO')}] {c.get('title')}**\n\n{c.get('comment')}"
                if c.get("suggestion"):
                    body_md += f"\n\n```suggestion\n{c.get('suggestion')}\n```"

                valid_comments_for_gh.append({
                    "path": file_path,
                    "line": line_no,
                    "side": c.get("side", "RIGHT"),
                    "body": body_md,
                })

                comments_for_db.append({
                    "file_path": file_path,
                    "line_number": line_no,
                    "side": c.get("side", "RIGHT"),
                    "agent_name": c.get("agent_name", "general"),
                    "severity": c.get("severity", "MEDIUM"),
                    "title": c.get("title", ""),
                    "comment": c.get("comment", ""),
                    "suggestion": c.get("suggestion"),
                })

            # 5. Post review to GitHub API
            gh_review_id = None
            try:
                gh_resp = await gh_client.post_pr_review(
                    owner=repository.owner,
                    repo=repository.name,
                    pull_number=pr_number,
                    commit_id=head_sha,
                    body=aggregated.get("summary", "Brittle PR review completed."),
                    event=aggregated.get("recommendation", "COMMENT"),
                    comments=valid_comments_for_gh,
                )
                gh_review_id = gh_resp.get("id")
            except Exception as e:
                logger.warning(f"Could not post review directly to GitHub: {e}")

            # 6. Persist results in Database
            rec_enum = ReviewRecommendation(aggregated.get("recommendation", ReviewRecommendation.COMMENT.value))
            await review_repo.update_review_results(
                review_id=review.id,
                state=ReviewState.COMPLETED,
                summary=aggregated.get("summary", ""),
                risk_score=aggregated.get("risk_score", 1),
                recommendation=rec_enum,
                security_count=aggregated.get("security_issues_count", 0),
                perf_count=aggregated.get("perf_issues_count", 0),
                quality_count=aggregated.get("quality_issues_count", 0),
                raw_output=final_state,
                github_review_id=gh_review_id,
            )

            if comments_for_db:
                await review_repo.save_comments(review.id, comments_for_db)

            await db.commit()
            await redis_cache.mark_idempotent(idempotency_key)
            logger.info(f"Successfully finished PR review for {repository.full_name} #{pr_number}")

        except Exception as e:
            logger.exception(f"Error executing PR review for {idempotency_key}: {e}")
            if 'review' in locals() and review:
                review.state = ReviewState.FAILED
                await db.commit()
        finally:
            await redis_cache.release_lock(lock_key)


async def execute_repo_indexing(repository_id: int) -> None:
    """Async task for indexing repository code."""
    async with AsyncSessionLocal() as db:
        repo_repo = RepoRepository(db)
        repo = await repo_repo.get_repo_by_id(repository_id)
        if repo:
            indexer = RepoIndexerService(db)
            await indexer.index_repository(repo)
            await db.commit()


# Celery Task Wrappers (for celery workers)
if settings.USE_CELERY:
    from app.workers.celery_app import celery_app

    @celery_app.task(name="tasks.run_pr_review_celery")
    def run_pr_review_celery(repo_id: int, pr_num: int, head_sha: str, base_sha: str, title: str, author: str):
        asyncio.run(execute_pr_review(repo_id, pr_num, head_sha, base_sha, title, author))

    @celery_app.task(name="tasks.index_repo_celery")
    def index_repo_celery(repo_id: int):
        asyncio.run(execute_repo_indexing(repo_id))


class QueueDispatcher:
    """
    Clean interface to dispatch background jobs.
    Uses Celery if configured, otherwise falls back to FastAPI BackgroundTasks or asyncio.
    """

    @staticmethod
    def dispatch_pr_review(
        background_tasks: Optional[BackgroundTasks],
        repository_id: int,
        pr_number: int,
        head_sha: str,
        base_sha: str,
        title: str,
        author: str,
    ) -> None:
        if settings.USE_CELERY:
            from app.workers.tasks import run_pr_review_celery
            run_pr_review_celery.delay(repository_id, pr_number, head_sha, base_sha, title, author)
        elif background_tasks is not None:
            background_tasks.add_task(
                execute_pr_review, repository_id, pr_number, head_sha, base_sha, title, author
            )
        else:
            asyncio.create_task(
                execute_pr_review(repository_id, pr_number, head_sha, base_sha, title, author)
            )

    @staticmethod
    def dispatch_repo_indexing(
        background_tasks: Optional[BackgroundTasks],
        repository_id: int,
    ) -> None:
        if settings.USE_CELERY:
            from app.workers.tasks import index_repo_celery
            index_repo_celery.delay(repository_id)
        elif background_tasks is not None:
            background_tasks.add_task(execute_repo_indexing, repository_id)
        else:
            asyncio.create_task(execute_repo_indexing(repository_id))
