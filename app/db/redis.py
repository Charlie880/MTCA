# app/db/redis.py
from langgraph.checkpoint.redis import AsyncRedisSaver
from redis.asyncio import Redis
from app.core.config import settings

redis_client = Redis.from_url(
    settings.REDIS_CONNECTION,
    decode_responses=False
)

# Initialize the saver
checkpointer = AsyncRedisSaver(redis_client=redis_client)