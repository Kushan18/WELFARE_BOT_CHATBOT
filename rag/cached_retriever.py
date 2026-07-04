import logging

logger = logging.getLogger(__name__)
_model = None
_collection = None

def _load():
    global _model, _collection
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    if _collection is None:
        import chromadb
        chroma = chromadb.PersistentClient(path="./chroma_storage")
        _collection = chroma.get_collection("welfare_schemes")

def cached_retrieve(query, n=3):
    try:
        _load()
        embedding = _model.encode([query]).tolist()
        results = _collection.query(query_embeddings=embedding, n_results=n)
        return results.get('documents', [[]])[0]
    except Exception as e:
        logger.error(f"cached_retrieve error: {e}")
        return []
