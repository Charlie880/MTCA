# test/test_connections.py
import asyncio
import sys
import os

# Ensure the root directory is in the Python path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.clients import (
    get_mongo_db, 
    get_async_redis_client, 
    pinecone_client,
    embeddings
)

async def test_mongodb():
    print("⏳ Testing MongoDB Atlas connection...")
    try:
        db = get_mongo_db()
        # The 'admin' database is used to run the ping command
        await db.client.admin.command('ping')
        print("   ✅ MongoDB: Successfully connected and pinged!")
    except Exception as e:
        print(f"   ❌ MongoDB Error: {e}")

async def test_redis():
    print("⏳ Testing Redis Cloud connection...")
    try:
        redis_client = get_async_redis_client()
        response = await redis_client.ping()
        if response:
            print("   ✅ Redis: Successfully connected and pinged!")
        else:
            print("   ❌ Redis Error: Ping returned False")
        await redis_client.aclose() # close connection gracefully
    except Exception as e:
        print(f"   ❌ Redis Error: {e}")

def test_pinecone():
    print("⏳ Testing Pinecone connection (API Key only)...")
    try:
        # Pinging the server to list indexes verifies the API key is valid
        active_indexes = pinecone_client.list_indexes()
        
        print("   ✅ Pinecone: Successfully connected!")
        print(f"      Active indexes found: {len(active_indexes)}")
    except Exception as e:
        print(f"   ❌ Pinecone Error: {e}")

def test_openai():
    print("⏳ Testing OpenAI Embeddings connection...")
    try:
        # Generate a small test embedding
        vector = embeddings.embed_query("Hello, world!")
        print(f"   ✅ OpenAI: Connected! Generated vector of length {len(vector)}")
    except Exception as e:
        print(f"   ❌ OpenAI Error: {e}")

async def main():
    print("==========================================")
    print("🚀 Running Infrastructure Checks...")
    print("==========================================\n")
    
    await test_mongodb()
    await test_redis()
    
    # Pinecone and OpenAI are synchronous in our setup
    test_pinecone()
    test_openai()
    
    print("\n==========================================")
    print("🏁 Infrastructure Checks Complete.")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(main())