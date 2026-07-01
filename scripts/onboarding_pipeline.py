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

        "tenantDescription": (
            "A modern, state-of-the-art dental clinic in Kathmandu specializing in cosmetic dentistry, restorative treatments, orthodontics, and dental tourism. The branch offers advanced technology, experienced specialists, flexible payment options, and comprehensive care for both local and international patients."
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

        "tenantDescription": (
            "A tourist-focused dental clinic in Lakeside, Pokhara, providing rapid emergency dental care, premium implant services, same-day restorative treatments, and dental holiday packages. It is designed to serve travelers, trekkers, and international visitors with convenient, high-quality care."
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

        "tenantDescription": (
            "A cultural and wellness travel hub offering guided heritage tours, culinary experiences, traditional workshops, wellness retreats, and immersive Newari cultural programs. The branch is ideal for families, slow travelers, and visitors seeking authentic local experiences."
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

        "tenantDescription": (
            "The flagship adventure and corporate travel center specializing in high-altitude trekking, expedition planning, MICE services, corporate retreats, and post-trek recovery. It caters to business clients, adventure enthusiasts, and organizations with comprehensive logistics and safety-focused travel solutions."
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