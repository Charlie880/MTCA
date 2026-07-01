# scripts/verctor_kb.py
import os
import sys
import re
import time

# Dynamically align root directory imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pinecone import ServerlessSpec
from app.db.clients import pinecone_client, embeddings

INDEX_NAME = "mtca-index"
INPUT_FILE = "scripts/synthetic_data.txt"

def ensure_pinecone_index_exists():
    """Programmatically ensures the target serverless index is active."""
    print("🔍 Checking Pinecone workspace for index target...")
    if not pinecone_client.has_index(INDEX_NAME):
        print(f"🏗️ Index '{INDEX_NAME}' not found. Deploying serverless cluster...")
        pinecone_client.create_index(
            name=INDEX_NAME,
            dimension=1536,  # Matches text-embedding-3-small length
            metric="cosine", 
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print(f"⏳ Waiting for index '{INDEX_NAME}' to initialize...")
        while not pinecone_client.describe_index(INDEX_NAME).status['ready']:
            time.sleep(2)
        print(f"✅ Index '{INDEX_NAME}' is live.")
    else:
        print(f"✨ Index '{INDEX_NAME}' found and active.")

def clean_and_parse_kb(file_path: str):
    """
    Parses synthetic_data.txt using our verified natural boundary splitting logic,
    ensuring correct multi-tenant namespaces (like abc_dentals_ktm).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Source file not found at path: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    org_sections = content.split("Knowledge Base:")
    namespace_content = {}

    for org_sec in org_sections:
        if not org_sec.strip():
            continue
            
        lines = org_sec.split("\n")
        org_raw = lines[0].strip()
        org_id = org_raw.lower().replace(" ", "_")
        
        org_body = "\n".join(lines[1:])
        branch_sections = org_body.split("Branch:")
        
        for branch_sec in branch_sections:
            if not branch_sec.strip():
                continue
                
            branch_lines = branch_sec.split("\n")
            branch_raw = branch_lines[0].strip()
            
            # --- VERIFIED BRAND STRIPPING LOGIC ---
            if "(" in branch_raw:
                branch_clean = branch_raw.split("(")[0].strip().lower()
            else:
                branch_clean = branch_raw.lower().replace(" ", "_")
                
            branch_id = re.sub(r'[^a-zA-Z0-9_]', '', branch_clean)
            namespace_key = f"{org_id}_{branch_id}"
            branch_body = "\n".join(branch_lines[1:]).strip()
            
            # --- NATURAL SEMANTIC CHUNKING ---
            chunks = re.split(
                r'\n(?=\d+\.\s+|Frequently\s+Asked\s+Questions|Company\s+Overview|Authentication|Location)', 
                branch_body
            )
            
            processed_chunks = []
            for chunk in chunks:
                chunk_stripped = chunk.strip()
                if not chunk_stripped:
                    continue
                
                first_line = chunk_stripped.split("\n")[0].strip()
                chunk_title = re.sub(r'^[-*\s\d.]+', '', first_line).strip()
                
                # Injected block context string used directly for embedding generation
                structured_text = f"Organization: {org_raw} | Branch: {branch_raw}\nSection: {chunk_title}\n\n{chunk_stripped}"
                
                processed_chunks.append({
                    "structured_text": structured_text,
                    "title": chunk_title,
                    "raw_content": chunk_stripped
                })
            
            namespace_content[namespace_key] = {
                "orgId": org_id,
                "branchId": branch_id,
                "chunks": processed_chunks
            }

    return namespace_content

def run_production_embedding_pipeline():
    try:
        ensure_pinecone_index_exists()
    except Exception as e:
        print(f"❌ Failed to verify Pinecone index resource: {e}")
        return

    print(f"\n📂 Reading validated data from '{INPUT_FILE}'...")
    try:
        parsed_data = clean_and_parse_kb(INPUT_FILE)
    except Exception as e:
        print(f"❌ Error parsing file: {str(e)}")
        return

    index = pinecone_client.Index(INDEX_NAME)

    for namespace, data in parsed_data.items():
        print(f"\n🧠 Processing Namespace: '{namespace}' ({len(data['chunks'])} chunks)")
        
        vectors_payload = []
        for index_id, chunk_data in enumerate(data["chunks"]):
            try:
                # Embed directly using the exact structured text layout verified in your debug file
                embedding_vector = embeddings.embed_query(chunk_data["structured_text"])
            except Exception as em_err:
                print(f"   ❌ Embedding calculation failed for chunk {index_id}: {em_err}")
                continue

            unique_vector_id = f"{namespace}#chunk_{index_id}"
            
            vectors_payload.append((
                unique_vector_id,
                embedding_vector,
                {
                    "text": chunk_data["structured_text"], 
                    "title": chunk_data["title"],         
                    "content": chunk_data["raw_content"], 
                    "orgId": data["orgId"],
                    "branchId": data["branchId"]
                }
            ))

        if vectors_payload:
            print(f"   📤 Upserting vectors to Pinecone namespace '{namespace}'...")
            try:
                index.upsert(vectors=vectors_payload, namespace=namespace)
                print(f"   ✅ Namespace '{namespace}' successfully populated.")
            except Exception as up_err:
                print(f"   ❌ Upsert failed for namespace '{namespace}': {up_err}")

    print("\n=======================================================")
    print("🏁 PRODUCTION MULTI-TENANT VECTOR SEEDING COMPLETE!")
    print("=======================================================")

if __name__ == "__main__":
    run_production_embedding_pipeline()