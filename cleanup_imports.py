import os

files_to_patch = [
    "agent/nodes.py",
    "check.py",
    "main.py",
    "rag/embedder.py",
    "rag/smart_retriever.py",
    "scraper/hf_dataset.py",
    "scraper/manager.py",
    "scraper/seed.py",
    "scripts/auto_verify_complete.py",
    "scripts/cleanup_duplicates.py",
    "scripts/enrich_raw.py",
    "scripts/remove_all_duplicates.py",
    "seed_schemes.py",
    "tests/test_admin_routes.py"
]

for file_path in files_to_patch:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        if line.strip() == "from pymongo import get_mongo_client":
            continue
        # Also need to fix where they might have imported multiple things
        # e.g. from pymongo import get_mongo_client, errors
        # But looking at git diff, it was purely "from pymongo import get_mongo_client"
        new_lines.append(line)
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
print("Cleanup complete.")
