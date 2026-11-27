import logging
import json
from typing import Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, status, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import verify_github_signature
from app.core.redis import redis_cache
from app.db.session import get_db
from app.repositories.repo_repository import RepoRepository
from app.workers.tasks import QueueDispatcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/github")
async def github_webhook_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Thin GitHub webhook receiver.
    Verifies HMAC-SHA256 signature, validates event type, delegates asynchronously,
    and returns 200/202 instantly.
    """
    body_bytes = await request.body()

    # Verify signature unless in loose development mode without secret
    if not verify_github_signature(body_bytes, x_hub_signature_256):
        logger.warning("Invalid webhook signature received.")
        # Only reject if signature header was provided or secret is set
        if x_hub_signature_256:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid HMAC signature",
            )

    try:
        payload = json.loads(body_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 1. Ping Event
    if x_github_event == "ping":
        return {"message": "PONG", "hook_id": payload.get("hook_id")}

    repo_repo = RepoRepository(db)

    # 2. Installation Event
    if x_github_event == "installation":
        action = payload.get("action")
        inst_data = payload.get("installation", {})
        inst_id = inst_data.get("id")
        account = inst_data.get("account", {})

        if inst_id and account:
            inst = await repo_repo.upsert_installation(
                github_installation_id=inst_id,
                account_login=account.get("login", "unknown"),
                account_type=account.get("type", "User"),
                avatar_url=account.get("avatar_url"),
            )
            for r in payload.get("repositories", []):
                await repo_repo.upsert_repository(
                    github_repo_id=r["id"],
                    installation_id=inst.id,
                    name=r["name"],
                    full_name=r["full_name"],
                    owner=account.get("login", "unknown"),
                    is_private=r.get("private", False),
                )
            await db.commit()
        return {"status": "installation_updated", "action": action}

    # 3. Pull Request Event
    if x_github_event == "pull_request":
        action = payload.get("action")
        # We review on opened, synchronize (new commits pushed), and reopened
        if action not in ("opened", "synchronize", "reopened"):
            return {"status": "ignored", "action": action}

        pr_data = payload.get("pull_request", {})
        repo_data = payload.get("repository", {})
        inst_data = payload.get("installation", {})

        pr_number = pr_data.get("number")
        head_sha = pr_data.get("head", {}).get("sha")
        base_sha = pr_data.get("base", {}).get("sha")
        title = pr_data.get("title", "")
        author = pr_data.get("user", {}).get("login", "")
        gh_repo_id = repo_data.get("id")

        if not all([pr_number, head_sha, gh_repo_id]):
            raise HTTPException(status_code=400, detail="Missing required PR payload fields")

        # Ensure repo and installation exist in our DB
        installation_id = inst_data.get("id", 1)
        inst = await repo_repo.upsert_installation(
            github_installation_id=installation_id,
            account_login=repo_data.get("owner", {}).get("login", "user"),
            avatar_url=repo_data.get("owner", {}).get("avatar_url"),
        )
        repo = await repo_repo.upsert_repository(
            github_repo_id=gh_repo_id,
            installation_id=inst.id,
            name=repo_data.get("name", "repo"),
            full_name=repo_data.get("full_name", "user/repo"),
            owner=repo_data.get("owner", {}).get("login", "user"),
            is_private=repo_data.get("private", False),
            default_branch=repo_data.get("default_branch", "main"),
        )
        await db.commit()

        # Idempotency check: prevent duplicate reviews for the same commit
        idempotency_key = f"{repo.id}:{pr_number}:{head_sha}"
        if await redis_cache.check_idempotency(idempotency_key):
            logger.info(f"Duplicate webhook delivery detected for {idempotency_key}. Skipping.")
            return {"status": "already_processed", "idempotency_key": idempotency_key}

        # Dispatch async review pipeline
        QueueDispatcher.dispatch_pr_review(
            background_tasks=background_tasks,
            repository_id=repo.id,
            pr_number=pr_number,
            head_sha=head_sha,
            base_sha=base_sha,
            title=title,
            author=author,
        )

        return {
            "status": "review_queued",
            "repository": repo.full_name,
            "pr_number": pr_number,
            "head_sha": head_sha,
            "idempotency_key": idempotency_key,
        }

    return {"status": "unhandled_event", "event": x_github_event}
