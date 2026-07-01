# scripts/onboarding_pipeline.py

import os
import sys
import asyncio

# ------------------------------------------------------------------
# Path Resolution
# ------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.db.clients import get_mongo_db


DB_NAME = "mtca_platform"
COLLECTION_NAME = "tenant_configurations"


TENANTS_BATCH = [
    {
        "orgId": "abc_dentals",
        "branchId": "ktm",

        "tenantName": "ABC Dentals - KTM Branch",

        "tenantTone": (
            "Clinical, highly professional, reassuring, and empathetic. "
            "Use medical terminology accurately but explain things simply to patients."
        ),

        "pinecone": {
            "knowledgeNamespace": "abc_dentals_ktm",
            "routingNamespace": "router_abc_dentals_ktm"
        },

        "integrations": {
            "calendarId": "add the organization branch account",
            "notificationEmail": "add the organization branch account"
        }
    },

    {
        "orgId": "abc_dentals",
        "branchId": "pokhara",

        "tenantName": "ABC Dentals - Pokhara Lakeside",

        "tenantTone": (
            "Urgent, accommodating, tourist-friendly, and reassuring. "
            "Focus on speed, convenience, and holiday preservation for travelers."
        ),

        "pinecone": {
            "knowledgeNamespace": "abc_dentals_pokhara",
            "routingNamespace": "router_abc_dentals_pokhara"
        },

        "integrations": {
            "calendarId": "add the organization branch account",
            "notificationEmail": "add the organization branch account"
        }
    },

    {
        "orgId": "xyz_travels",
        "branchId": "bhaktapur",

        "tenantName": "XYZ Travels - Bhaktapur Cultural Hub",

        "tenantTone": (
            "Warm, culturally enthusiastic, welcoming, and descriptive. "
            "Act like a passionate local heritage expert."
        ),

        "pinecone": {
            "knowledgeNamespace": "xyz_travels_bhaktapur",
            "routingNamespace": "router_xyz_travels_bhaktapur"
        },

        "integrations": {
            "calendarId": "add the organization branch account",
            "notificationEmail": "add the organization branch account"
        }
    },

    {
        "orgId": "xyz_travels",
        "branchId": "lalitpur",

        "tenantName": "XYZ Travels - Lalitpur Corporate & Adventure",

        "tenantTone": (
            "Professional, adventurous, organized, and corporate-focused. "
            "Inspire confidence through safety, logistics, and elite planning."
        ),

        "pinecone": {
            "knowledgeNamespace": "xyz_travels_lalitpur",
            "routingNamespace": "router_xyz_travels_lalitpur"
        },

        "integrations": {
            "calendarId": "add the organization branch account",
            "notificationEmail": "add the organization branch account"
        }
    }
]


async def seed_database():
    print("🔄 Acquiring internal MongoDB engine instance...")

    db = get_mongo_db()
    collection = db[COLLECTION_NAME]

    try:
        print("🔍 Syncing compound unique index architecture on [orgId + branchId]...")

        await collection.create_index(
            [("orgId", 1), ("branchId", 1)],
            unique=True
        )

        for tenant in TENANTS_BATCH:
            print(
                f"🧹 Purging old profile entries for: "
                f"{tenant['orgId']} ({tenant['branchId']})..."
            )

            await collection.delete_many({
                "orgId": tenant["orgId"],
                "branchId": tenant["branchId"]
            })

        print(
            f"🌱 Seeding {len(TENANTS_BATCH)} tenant configuration documents..."
        )

        result = await collection.insert_many(TENANTS_BATCH)

        print("\n=======================================================")
        print("✅ MULTI-TENANT CONFIGURATION SEEDED SUCCESSFULLY!")
        print(f"   Target Collection : {DB_NAME}.{COLLECTION_NAME}")
        print(f"   Inserted Records  : {len(result.inserted_ids)}")
        print("=======================================================")

    except Exception as e:
        print(f"\n❌ Seed execution failed: {e}")


if __name__ == "__main__":
    asyncio.run(seed_database())