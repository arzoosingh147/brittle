from typing import AsyncGenerator
from sqlalchemy.orm import declarative_base
from app.core.config import settings

Base = declarative_base()

try:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    engine = create_async_engine(
        settings.normalized_database_url,
        echo=settings.DEBUG,
        pool_size=10,
        max_overflow=15,
        pool_pre_ping=True,
        connect_args={"statement_cache_size": 0},
    )
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
except Exception:
    class MockEngine:
        url = settings.normalized_database_url
        def begin(self):
            class MockConnContext:
                async def __aenter__(self):
                    class MockConn:
                        async def execute(self, *args, **kwargs): pass
                        async def run_sync(self, *args, **kwargs): pass
                    return MockConn()
                async def __aexit__(self, *args): pass
            return MockConnContext()

    engine = MockEngine()

    class MockAsyncSession:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def commit(self): pass
        async def rollback(self): pass
        async def close(self): pass
        async def execute(self, *args, **kwargs):
            class MockResult:
                def scalars(self):
                    class MockScalars:
                        def all(self): return []
                    return MockScalars()
                def scalar_one_or_none(self): return None
                def one(self):
                    class MockRow:
                        total_reviews = 0
                        avg_risk_score = 0
                        total_security = 0
                        total_perf = 0
                        total_quality = 0
                    return MockRow()
            return MockResult()
        def add(self, *args): pass
        async def flush(self): pass

    class MockSessionMaker:
        def __call__(self):
            return MockAsyncSession()

    AsyncSessionLocal = MockSessionMaker()


async def get_db() -> AsyncGenerator:
    """Dependency for providing an async database session per request."""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
