from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    PullRequestReview,
    ReviewComment,
    ReviewState,
    ReviewRecommendation,
    CommentSeverity,
    CommentSide
)


class ReviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_idempotency_key(self, idempotency_key: str) -> Optional[PullRequestReview]:
        stmt = (
            select(PullRequestReview)
            .where(PullRequestReview.idempotency_key == idempotency_key)
            .options(selectinload(PullRequestReview.comments))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_review_by_id(self, review_id: int) -> Optional[PullRequestReview]:
        stmt = (
            select(PullRequestReview)
            .where(PullRequestReview.id == review_id)
            .options(selectinload(PullRequestReview.comments))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_get_review(
        self,
        repository_id: int,
        pr_number: int,
        head_sha: str,
        base_sha: str,
        title: str = "",
        author: str = ""
    ) -> Tuple[PullRequestReview, bool]:
        """
        Idempotent review retrieval/creation.
        Returns (review, created_bool).
        """
        idempotency_key = f"{repository_id}:{pr_number}:{head_sha}"
        existing = await self.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing, False

        review = PullRequestReview(
            repository_id=repository_id,
            pr_number=pr_number,
            head_sha=head_sha,
            base_sha=base_sha,
            title=title,
            author=author,
            state=ReviewState.PENDING,
            idempotency_key=idempotency_key,
        )
        self.db.add(review)
        await self.db.flush()
        return review, True

    async def update_review_results(
        self,
        review_id: int,
        state: ReviewState,
        summary: str,
        risk_score: int,
        recommendation: ReviewRecommendation,
        security_count: int,
        perf_count: int,
        quality_count: int,
        raw_output: Dict[str, Any],
        github_review_id: Optional[int] = None
    ) -> Optional[PullRequestReview]:
        review = await self.get_review_by_id(review_id)
        if review:
            review.state = state
            review.summary = summary
            review.risk_score = risk_score
            review.recommendation = recommendation
            review.security_issues_count = security_count
            review.perf_issues_count = perf_count
            review.quality_issues_count = quality_count
            review.raw_agent_output = raw_output
            if github_review_id is not None:
                review.github_review_id = github_review_id
            review.updated_at = datetime.utcnow()
            await self.db.flush()
        return review

    async def save_comments(self, review_id: int, comments_data: List[Dict[str, Any]]) -> List[ReviewComment]:
        comments = []
        for c in comments_data:
            comment = ReviewComment(
                review_id=review_id,
                file_path=c["file_path"],
                line_number=c["line_number"],
                diff_hunk=c.get("diff_hunk"),
                side=CommentSide(c.get("side", CommentSide.RIGHT.value)),
                agent_name=c.get("agent_name", "general"),
                severity=CommentSeverity(c.get("severity", CommentSeverity.MEDIUM.value)),
                title=c["title"],
                comment=c["comment"],
                suggestion=c.get("suggestion"),
                github_comment_id=c.get("github_comment_id"),
            )
            self.db.add(comment)
            comments.append(comment)
        await self.db.flush()
        return comments

    async def list_reviews(
        self,
        repository_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[PullRequestReview]:
        stmt = (
            select(PullRequestReview)
            .options(selectinload(PullRequestReview.comments))
            .order_by(desc(PullRequestReview.created_at))
            .offset(skip)
            .limit(limit)
        )
        if repository_id:
            stmt = stmt.where(PullRequestReview.repository_id == repository_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_metrics(self, repository_id: Optional[int] = None) -> Dict[str, Any]:
        """Aggregate review metrics across repositories or for a single repository."""
        stmt = select(
            func.count(PullRequestReview.id).label("total_reviews"),
            func.avg(PullRequestReview.risk_score).label("avg_risk_score"),
            func.sum(PullRequestReview.security_issues_count).label("total_security"),
            func.sum(PullRequestReview.perf_issues_count).label("total_perf"),
            func.sum(PullRequestReview.quality_issues_count).label("total_quality"),
        )
        if repository_id:
            stmt = stmt.where(PullRequestReview.repository_id == repository_id)
        
        result = await self.db.execute(stmt)
        row = result.one()
        
        return {
            "total_reviews": row.total_reviews or 0,
            "avg_risk_score": round(float(row.avg_risk_score or 0.0), 1),
            "total_security_issues": int(row.total_security or 0),
            "total_perf_issues": int(row.total_perf or 0),
            "total_quality_issues": int(row.total_quality or 0),
            "total_issues": int((row.total_security or 0) + (row.total_perf or 0) + (row.total_quality or 0)),
        }
