import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.redis import redis_cache
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.repos import router as repos_router
from app.api.v1.reviews import router as reviews_router

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info(f"Starting {settings.PROJECT_NAME} in {settings.ENVIRONMENT} mode...")
    
    # Optionally initialize DB tables if in development
    try:
        from app.db.session import engine, Base
        import app.db.models
        async with engine.begin() as conn:
            # Enable pgvector extension
            await conn.execute(conn.text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schemas and pgvector extension verified.")
    except Exception as e:
        logger.warning(f"Database auto-creation skipped or failed: {e}")

    yield

    # Shutdown actions
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    await redis_cache.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="High-performance AI Pull Request & Codebase Reviewer",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global Exception Handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error processing {request.method} {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": f"{type(exc).__name__}: {str(exc)}" if settings.DEBUG else "An internal server error occurred.",
                "type": type(exc).__name__,
            },
        )

    # Register Routers under /api/v1
    app.include_router(webhooks_router, prefix=settings.API_V1_STR)
    app.include_router(repos_router, prefix=settings.API_V1_STR)
    app.include_router(reviews_router, prefix=settings.API_V1_STR)

    @app.get("/healthz", tags=["Health"])
    async def healthcheck():
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
        }

    return app


app = create_app()
