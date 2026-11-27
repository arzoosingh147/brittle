import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Enum,
    Index,
    UniqueConstraint,
    types
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

try:
    from pgvector.sqlalchemy import Vector
    _HAS_PGVECTOR = True
except ImportError:
    _HAS_PGVECTOR = False
    class Vector(types.UserDefinedType):
        def __init__(self, dim: int = 768):
            self.dim = dim
        def get_col_spec(self, **kw):
            return f"vector({self.dim})"

from app.core.config import settings
from app.db.session import Base


class IndexingStatus(str, enum.Enum):
    PENDING = "PENDING"
    INDEXING = "INDEXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReviewState(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReviewRecommendation(str, enum.Enum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


class CommentSeverity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class CommentSide(str, enum.Enum):
    RIGHT = "RIGHT"
    LEFT = "LEFT"


class Installation(Base):
    __tablename__ = "installations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_installation_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    account_login: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), default="User")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    repositories = relationship("Repository", back_populates="installation", cascade="all, delete-orphan")


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    github_repo_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    installation_id: Mapped[int] = mapped_column(Integer, ForeignKey("installations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    
    indexing_status: Mapped[IndexingStatus] = mapped_column(
        Enum(IndexingStatus), default=IndexingStatus.PENDING, index=True
    )
    indexed_commit_sha: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rules: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    installation = relationship("Installation", back_populates="repositories")
    chunks = relationship("CodeChunk", back_populates="repository", cascade="all, delete-orphan")
    reviews = relationship("PullRequestReview", back_populates="repository", cascade="all, delete-orphan")


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(64), default="unknown")
    chunk_type: Mapped[str] = mapped_column(String(32), default="snippet")
    symbol_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    embedding = mapped_column(Vector(settings.VECTOR_DIMENSION), nullable=True)
    meta_info: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    repository = relationship("Repository", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("repository_id", "file_path", "content_hash", name="uq_repo_file_chunk"),
    )


class PullRequestReview(Base):
    __tablename__ = "pr_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    head_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    base_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(512), default="")
    author: Mapped[str] = mapped_column(String(255), default="")
    
    state: Mapped[ReviewState] = mapped_column(Enum(ReviewState), default=ReviewState.PENDING, index=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=1)
    recommendation: Mapped[ReviewRecommendation] = mapped_column(
        Enum(ReviewRecommendation), default=ReviewRecommendation.COMMENT
    )
    
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    
    security_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    perf_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    quality_issues_count: Mapped[int] = mapped_column(Integer, default=0)
    
    raw_agent_output: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)
    github_review_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    repository = relationship("Repository", back_populates="reviews")
    comments = relationship("ReviewComment", back_populates="review", cascade="all, delete-orphan")


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(Integer, ForeignKey("pr_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    diff_hunk: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    side: Mapped[CommentSide] = mapped_column(Enum(CommentSide), default=CommentSide.RIGHT)
    
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[CommentSeverity] = mapped_column(Enum(CommentSeverity), default=CommentSeverity.MEDIUM)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    github_comment_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    review = relationship("PullRequestReview", back_populates="comments")
