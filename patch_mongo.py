import os
import re

db_utils_code = """import os
import re
from urllib.parse import quote_plus, unquote_plus
from pymongo import MongoClient

def get_mongodb_uri(uri: str = None) -> str:
    if uri is None:
        uri = os.getenv("MONGODB_URI")
    if not uri:
        return uri
    match = re.match(r"^(mongodb(?:\+srv)?://)(.*)@(.*)$", uri)
    if match:
        prefix, userpass, rest = match.groups()
        if ":" in userpass:
            user, pwd = userpass.split(":", 1)
            user = quote_plus(unquote_plus(user))
            pwd = quote_plus(unquote_plus(pwd))
            return f"{prefix}{user}:{pwd}@{rest}"
        else:
            user = quote_plus(unquote_plus(userpass))
            return f"{prefix}{user}@{rest}"
    return uri

def get_mongo_client(uri: str = None, **kwargs) -> MongoClient:
    if uri is None:
        escaped_uri = get_mongodb_uri()
    else:
        escaped_uri = get_mongodb_uri(uri)
    return MongoClient(escaped_uri, **kwargs)
"""

with open("db_utils.py", "w", encoding="utf-8") as f:
    f.write(db_utils_code)

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
        content = f.read()
        
    if "get_mongo_client" in content:
        continue
        
    # We want to replace occurrences of `MongoClient(...)` with `get_mongo_client(...)`
    # and add `from db_utils import get_mongo_client` to the imports.
    # Be careful not to replace pymongo.MongoClient unless we also fix the prefix,
    # but let's just replace `MongoClient` (with word boundaries) and handle `pymongo.MongoClient`.
    
    new_content = re.sub(r'\bpymongo\.MongoClient\b', 'get_mongo_client', content)
    new_content = re.sub(r'\bMongoClient\b', 'get_mongo_client', new_content)
    
    # Add import at the top if it was modified
    if new_content != content:
        # Determine the relative path to db_utils.py
        # If file_path is 'agent/nodes.py', we need `from db_utils import get_mongo_client`
        # Python 3 allows absolute imports from the root if the root is in sys.path or if we just run from root.
        # But wait, python modules run as scripts might fail with absolute imports if the root is not in PYTHONPATH.
        # However, `main.py` adds the root to sys.path: `sys.path.append(os.path.dirname(os.path.abspath(__file__)))`.
        # So `from db_utils import get_mongo_client` should work everywhere.
        
        # Let's insert the import after the first few lines of imports
        # Or just at the very beginning of the file.
        import_stmt = "from db_utils import get_mongo_client\n"
        
        # To avoid duplicating imports if already there:
        if import_stmt not in new_content:
            # We'll put it after the first line (or right at the top, avoiding shebangs)
            lines = new_content.split('\n')
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('#!'):
                    continue
                insert_idx = i
                break
            lines.insert(insert_idx, "from db_utils import get_mongo_client")
            new_content = '\n'.join(lines)
            
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
print("Patching complete.")
