# scripts/fewshot_kb.py

import os
import sys
import json
import time

# Dynamically align root directory imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pinecone import ServerlessSpec
from app.db.clients import pinecone_client, embeddings

INDEX_NAME = "mtca-index"
INPUT_FILE = "scripts/few_shot_examples.json"


# Maps each tenant to the routing namespace defined during onboarding.
ROUTING_NAMESPACES = {
    ("abc_dentals", "ktm"): "router_abc_dentals_ktm",
    ("abc_dentals", "pokhara"): "router_abc_dentals_pokhara",
    ("xyz_travels", "bhaktapur"): "router_xyz_travels_bhaktapur",
    ("xyz_travels", "lalitpur"): "router_xyz_travels_lalitpur",
}


def ensure_pinecone_index_exists():
    """Ensures the shared Pinecone index exists."""

    print("🔍 Checking Pinecone workspace for index target...")

    if not pinecone_client.has_index(INDEX_NAME):
        print(f"🏗️ Index '{INDEX_NAME}' not found. Deploying serverless cluster...")

        pinecone_client.create_index(
            name=INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )

        print(f"⏳ Waiting for index '{INDEX_NAME}' to initialize...")

        while not pinecone_client.describe_index(INDEX_NAME).status["ready"]:
            time.sleep(2)

        print(f"✅ Index '{INDEX_NAME}' is live.")

    else:
        print(f"✨ Index '{INDEX_NAME}' found and active.")


def load_few_shots(file_path: str):
    """Loads the JSON few-shot dataset."""

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Could not locate '{file_path}'")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_embedding_text(example: dict):
    """
    Creates the text that will actually be embedded.

    We intentionally include the reasoning because it helps semantic retrieval
    find similar routing decisions rather than relying only on user wording.
    """

    return f"""User Message:
{example['user_message']}

Expected Action:
{example['expected_action']}

Reasoning:
{example['reasoning']}"""


def run_fewshot_embedding_pipeline():

    try:
        ensure_pinecone_index_exists()
    except Exception as e:
        print(f"❌ Failed to verify Pinecone index: {e}")
        return

    print(f"\n📂 Reading few-shot examples from '{INPUT_FILE}'...")

    try:
        examples = load_few_shots(INPUT_FILE)
    except Exception as e:
        print(f"❌ Failed loading JSON: {e}")
        return

    grouped_vectors = {}

    print(f"🧠 Processing {len(examples)} routing examples...")

    for i, example in enumerate(examples):

        key = (
            example["orgId"],
            example["branchId"]
        )

        if key not in ROUTING_NAMESPACES:
            print(f"⚠️ Unknown tenant: {key}")
            continue

        namespace = ROUTING_NAMESPACES[key]

        embedding_text = build_embedding_text(example)

        try:
            embedding = embeddings.embed_query(embedding_text)

        except Exception as e:
            print(f"❌ Failed embedding example {i}: {e}")
            continue

        vector = (
            f"{namespace}#example_{i}",
            embedding,
            {
                "text": embedding_text,
                "user_message": example["user_message"],
                "expected_action": example["expected_action"],
                "reasoning": example["reasoning"],
                "orgId": example["orgId"],
                "branchId": example["branchId"],
            }
        )

        grouped_vectors.setdefault(namespace, []).append(vector)

    index = pinecone_client.Index(INDEX_NAME)

    print()

    for namespace, vectors in grouped_vectors.items():

        print(
            f"📤 Upserting {len(vectors)} vectors into namespace '{namespace}'..."
        )

        try:
            index.upsert(
                vectors=vectors,
                namespace=namespace
            )

            print(f"   ✅ Successfully populated '{namespace}'")

        except Exception as e:
            print(f"   ❌ Failed: {e}")

    print("\n=======================================================")
    print("🏁 ROUTING FEW-SHOT VECTOR SEEDING COMPLETE!")
    print("=======================================================")


if __name__ == "__main__":
    run_fewshot_embedding_pipeline()