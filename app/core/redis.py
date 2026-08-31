import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

redis_pool: Optional[aioredis.ConnectionPool] = None
redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    global redis_pool, redis_client
    if redis_client is None:
        redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=50,
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
        )
        redis_client = aioredis.Redis(connection_pool=redis_pool)
    return redis_client


async def close_redis() -> None:
    global redis_client, redis_pool
    if redis_client:
        await redis_client.aclose()
    if redis_pool:
        await redis_pool.disconnect()
    logger.info("redis_connection_closed")


class RedisCache:
    """Helper wrapper for distributed caching, rate limiting, and pub/sub."""

    @staticmethod
    async def get_json(key: str) -> Optional[Any]:
        try:
            client = await get_redis_client()
            data = await client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning("redis_get_json_failed", key=key, error=str(e))
            return None

    @staticmethod
    async def set_json(key: str, value: Any, ttl_seconds: int = settings.CACHE_DEFAULT_TTL_SECS) -> bool:
        try:
            client = await get_redis_client()
            serialized = json.dumps(value)
            await client.set(key, serialized, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.warning("redis_set_json_failed", key=key, error=str(e))
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        try:
            client = await get_redis_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning("redis_delete_failed", key=key, error=str(e))
            return False

    @staticmethod
    async def is_rate_limited(identifier: str, limit: int = 30, window_secs: int = 60) -> bool:
        """Sliding window / counter rate limiter."""
        try:
            client = await get_redis_client()
            key = f"rate_limit:{identifier}"
            current_count = await client.incr(key)
            if current_count == 1:
                await client.expire(key, window_secs)
            return current_count > limit
        except Exception as e:
            logger.warning("rate_limiter_check_failed", identifier=identifier, error=str(e))
            return False

    @staticmethod
    async def publish(channel: str, message: dict) -> int:
        try:
            client = await get_redis_client()
            return await client.publish(channel, json.dumps(message))
        except Exception as e:
            logger.warning("redis_publish_failed", channel=channel, error=str(e))
            return 0
