import os
import sys
import re

# Dynamically align root directory imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

INPUT_FILE = "scripts/synthetic_data.txt"
OUTPUT_FILE = "scripts/chunk_review_debug.md"

def clean_and_parse_kb_simulation(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Source file not found at path: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split the file by the global Organization indicator
    org_sections = content.split("Knowledge Base:")
    namespace_content = {}

    for org_sec in org_sections:
        if not org_sec.strip():
            continue
            
        lines = org_sec.split("\n")
        org_raw = lines[0].strip()  # e.g., "ABC Dentals"
        org_id = org_raw.lower().replace(" ", "_")
        
        org_body = "\n".join(lines[1:])
        branch_sections = org_body.split("Branch:")
        
        for branch_sec in branch_sections:
            if not branch_sec.strip():
                continue
                
            branch_lines = branch_sec.split("\n")
            branch_raw = branch_lines[0].strip()  # e.g., "KTM (Kathmandu)" or "Lalitpur"
            
            # --- FIXED BRAND STRIPPING LOGIC ---
            # Extract text BEFORE the parenthesis if it exists (like KTM)
            if "(" in branch_raw:
                branch_clean = branch_raw.split("(")[0].strip().lower()
            else:
                branch_clean = branch_raw.lower().replace(" ", "_")
                
            branch_id = re.sub(r'[^a-zA-Z0-9_]', '', branch_clean)
            
            # Construct the absolute namespace key
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
                
                # Format chunk string with complete Title + Content structure
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

def run_simulation():
    print(f"📂 Simulating chunk splitting logic using source file: '{INPUT_FILE}'...")
    
    try:
        parsed_data = clean_and_parse_kb_simulation(INPUT_FILE)
    except Exception as e:
        print(f"❌ Error during parsing: {e}")
        return

    print(f"📝 Writing parsed chunks to verification report: '{OUTPUT_FILE}'...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Local Knowledge Base Chunking & Namespace Review\n")
        f.write("Use this report to inspect how text segments look *before* generating embeddings.\n\n")
        f.write("---\n\n")

        for namespace, data in parsed_data.items():
            f.write(f"## 📂 Target Namespace: `{namespace}`\n")
            f.write(f"- **Metadata orgId:** `{data['orgId']}`\n")
            f.write(f"- **Metadata branchId:** `{data['branchId']}`\n")
            f.write(f"- **Total Natural Chunks:** {len(data['chunks'])} \n\n")
            
            for i, chunk_data in enumerate(data["chunks"]):
                f.write(f"### 🧩 Chunk Index Position: `{i}`\n")
                f.write(f"- **Inferred Title:** *{chunk_data['title']}*\n\n")
                f.write("#### 🧱 Resulting Raw Text Stream:\n")
                f.write("```text\n")
                f.write(f"{chunk_data['structured_text']}\n")
                f.write("```\n")
                f.write("\n" + "-"*40 + "\n\n")

    print(f"✅ Simulation complete! Please inspect '{OUTPUT_FILE}' in your project root.")

if __name__ == "__main__":
    run_simulation()