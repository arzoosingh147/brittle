from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class InlineCommentOutput(BaseModel):
    file_path: str = Field(description="Exact relative file path as appearing in the PR diff")
    line_number: int = Field(description="Exact target line number in the new version of the file")
    side: Literal["RIGHT", "LEFT"] = Field(default="RIGHT", description="Diff side: RIGHT for added/modified lines")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"] = Field(
        default="MEDIUM", description="Severity classification"
    )
    title: str = Field(description="Short, impactful headline of the finding")
    comment: str = Field(description="Actionable explanation of why this is an issue and how to resolve it")
    suggestion: Optional[str] = Field(
        default=None, description="Precise code replacement snippet (omit if not applicable)"
    )


class SpecialistReviewOutput(BaseModel):
    agent_name: str = Field(description="Specialist agent identifier (security, performance, or quality)")
    summary: str = Field(description="Specialist analysis summary")
    risk_score: int = Field(ge=1, le=10, description="Risk score from 1 (minimal risk) to 10 (critical blocker)")
    findings: List[InlineCommentOutput] = Field(
        default_factory=list, description="List of inline line-specific comments"
    )


class AggregatedReviewOutput(BaseModel):
    summary: str = Field(description="Executive summary of the PR review highlighting critical insights")
    risk_score: int = Field(ge=1, le=10, description="Overall PR risk score from 1 to 10")
    recommendation: Literal["APPROVE", "REQUEST_CHANGES", "COMMENT"] = Field(
        description="Final GitHub PR review action"
    )
    comments: List[InlineCommentOutput] = Field(
        default_factory=list, description="Deduplicated, prioritized inline comments"
    )
    security_issues_count: int = Field(default=0)
    perf_issues_count: int = Field(default=0)
    quality_issues_count: int = Field(default=0)
