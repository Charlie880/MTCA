# app/db/clients.py
import certifi
import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorClient
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

# ==========================================
# 1. Shared Clients (Sync & Thread-safe)
# ==========================================

# Shared Embeddings
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=settings.OPENAI_API_KEY
)

# Pinecone Client & Index
pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
pinecone_index = pinecone_client.Index(settings.PINECONE_INDEX_NAME)


# ==========================================
# 2. Async Client Factories
# ==========================================

# Cache the Motor client to preserve connection pooling per worker
_mongo_client = None

def get_mongo_db():
    """
    FACTORY: Returns the async MongoDB database instance.
    Ensures connection pooling is preserved across FastAPI requests.
    """
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(
            settings.MONGO_URI,
            tlsCAFile=certifi.where(),
            maxPoolSize=50,
            minPoolSize=5,
            tz_aware=True
        )
    return _mongo_client["multi_tenant_agent"]

def get_async_redis_client() -> redis.Redis:
    """
    FACTORY: Each worker/graph calls this to get a Redis connection.
    NOTE: decode_responses MUST be False because LangGraph checkpointer stores binary data.
    """
    return redis.from_url(
        settings.REDIS_CONNECTION,
        encoding="utf-8",
        decode_responses=False, 
        health_check_interval=30,
        retry_on_timeout=True
    )