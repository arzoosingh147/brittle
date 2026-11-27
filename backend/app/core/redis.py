import time
from typing import Optional, Dict, Any

try:
    import redis.asyncio as aioredis
    _HAS_REDIS = True
except ImportError:
    aioredis = None
    _HAS_REDIS = False

from app.core.config import settings

_redis_client: Optional[Any] = None


class InMemoryAsyncCache:
    """In-memory async cache fallback when Redis is not installed."""
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    async def get(self, key: str) -> Optional[str]:
        if key in self._store:
            item = self._store[key]
            if item["expires_at"] is None or item["expires_at"] > time.time():
                return item["val"]
            del self._store[key]
        return None

    async def set(self, key: str, val: str, ex: Optional[int] = None, nx: bool = False) -> bool:
        if nx and await self.get(key) is not None:
            return False
        expires_at = time.time() + ex if ex else None
        self._store[key] = {"val": str(val), "expires_at": expires_at}
        return True

    async def delete(self, key: str) -> int:
        return 1 if self._store.pop(key, None) is not None else 0

    async def close(self) -> None:
        self._store.clear()


async def get_redis_client() -> Any:
    """
    Provides an async Redis client with connection pooling,
    or falls back to an in-memory async store when redis is unavailable.
    """
    global _redis_client
    if _redis_client is None:
        if _HAS_REDIS:
            try:
                _redis_client = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=20
                )
            except Exception:
                _redis_client = InMemoryAsyncCache()
        else:
            _redis_client = InMemoryAsyncCache()
    return _redis_client


class RedisCacheService:
    def __init__(self, client: Optional[Any] = None):
        self._client = client

    async def get_client(self) -> Any:
        if self._client is None:
            self._client = await get_redis_client()
        return self._client

    async def get_installation_token(self, installation_id: int) -> Optional[str]:
        client = await self.get_client()
        return await client.get(f"gh:inst_token:{installation_id}")

    async def set_installation_token(self, installation_id: int, token: str, ttl_seconds: int = 3000) -> None:
        client = await self.get_client()
        await client.set(f"gh:inst_token:{installation_id}", token, ex=ttl_seconds)

    async def acquire_lock(self, lock_key: str, ttl_seconds: int = 60) -> bool:
        """Acquire a distributed lock to avoid concurrent duplicate reviews."""
        client = await self.get_client()
        return bool(await client.set(f"lock:{lock_key}", "locked", nx=True, ex=ttl_seconds))

    async def release_lock(self, lock_key: str) -> None:
        client = await self.get_client()
        await client.delete(f"lock:{lock_key}")

    async def check_idempotency(self, idempotency_key: str) -> bool:
        """Returns True if already processed (exists in Redis), False if new."""
        client = await self.get_client()
        exists = await client.get(f"idempotency:{idempotency_key}")
        return exists is not None

    async def mark_idempotent(self, idempotency_key: str, ttl_seconds: int = 86400 * 3) -> None:
        client = await self.get_client()
        await client.set(f"idempotency:{idempotency_key}", "processed", ex=ttl_seconds)

    async def close(self) -> None:
        if self._client:
            await self._client.close()


redis_cache = RedisCacheService()
