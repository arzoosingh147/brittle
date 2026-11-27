import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Search and load .env from workspace root, backend dir, or current dir
for env_path in [
    Path("backend/.env"),
    Path(".env"),
    Path(__file__).resolve().parent.parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent.parent / ".env",
]:
    if env_path.exists():
        load_dotenv(env_path, override=True)

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel
    class BaseSettings(BaseModel):
        def __init__(self, **kwargs):
            env_vars = {}
            for field_name, field_info in self.model_fields.items():
                if field_name in os.environ:
                    val = os.environ[field_name]
                    if field_info.annotation is bool:
                        val = val.lower() in ("true", "1", "yes")
                    elif field_info.annotation is int:
                        val = int(val)
                    env_vars[field_name] = val
            env_vars.update(kwargs)
            super().__init__(**env_vars)

    SettingsConfigDict = dict


class Settings(BaseSettings):
    # Application
    PROJECT_NAME: str = "Brittle PR Reviewer"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "super-secret-development-key-change-in-production-min-32-bytes"
    FRONTEND_URL: str = "http://localhost:3000"

    # Database & Vector Store (Supabase / Neon / Local Docker)
    DATABASE_URL: str = "postgresql+asyncpg://brittle:brittle_secret@localhost:5433/brittle_db"
    DATABASE_URL_SYNC: str = "postgresql://brittle:brittle_secret@localhost:5433/brittle_db"
    VECTOR_DIMENSION: int = 768

    @property
    def normalized_database_url(self) -> str:
        """Automatically adapts Supabase/Neon standard URLs for SQLAlchemy asyncpg."""
        import urllib.parse
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        try:
            parsed = urllib.parse.urlsplit(url)
            qs = urllib.parse.parse_qs(parsed.query)
            # asyncpg does not support channel_binding
            qs.pop("channel_binding", None)
            if "sslmode" in qs:
                qs["ssl"] = qs.pop("sslmode")
            new_query = urllib.parse.urlencode(qs, doseq=True)
            return urllib.parse.urlunsplit(parsed._replace(query=new_query))
        except Exception:
            return url

    # Redis & Queues (Upstash / Local Docker)
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_CELERY: bool = False

    # GitHub App Integration
    GITHUB_APP_ID: str = "123456"
    GITHUB_APP_PRIVATE_KEY_PATH: Optional[str] = None
    GITHUB_APP_PRIVATE_KEY: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: str = "development-webhook-secret"
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None

    # AI / LLM Models (Google Gemini & Fallback Groq)
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    DEFAULT_REVIEW_MODEL: str = "gemini-2.5-pro"
    FAST_SUMMARY_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    FALLBACK_LLM_PROVIDER: str = "groq"
    FALLBACK_MODEL: str = "qwen-2.5-coder-32b"

    # Limits & Token Budgeting
    MAX_DIFF_FILES: int = 30
    MAX_DIFF_LINES_PER_FILE: int = 1000
    TOP_K_CODE_CONTEXT: int = 6
    MAX_TOKENS_BUDGET: int = 12000

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]


settings = Settings()
