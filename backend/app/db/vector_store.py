import os
import logging
from app.core.config import settings

logger = logging.getLogger("app.db.vector_store")

class LocalVectorStore:
    """Fallback vector store that operates in memory if ChromaDB is unavailable."""
    def __init__(self):
        self.storage = {} # collection_name -> list of {"id": id, "document": doc, "embedding": emb, "metadata": meta}

    def get_or_create_collection(self, name):
        if name not in self.storage:
            self.storage[name] = []
        return MockCollection(name, self.storage[name])

class MockCollection:
    def __init__(self, name, data_list):
        self.name = name
        self.data = data_list

    def add(self, documents, ids, metadatas=None, embeddings=None):
        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if metadatas else {}
            emb = embeddings[i] if embeddings else []
            doc = documents[i]
            # Remove duplicate IDs if they exist
            self.data = [item for item in self.data if item["id"] != doc_id]
            self.data.append({
                "id": doc_id,
                "document": doc,
                "metadata": meta,
                "embedding": emb
            })
        logger.info(f"[Fallback VectorDB] Added {len(ids)} items to collection '{self.name}'.")

    def query(self, query_texts, n_results=3, where=None):
        # Fallback simple search: returns top-n matches based on substring matching
        # (For development, this is extremely simple and robust!)
        results = {
            "documents": [[]],
            "metadatas": [[]],
            "ids": [[]]
        }
        words = query_texts[0].lower().split() if query_texts else []
        scored_docs = []
        for item in self.data:
            score = 0
            doc_lower = item["document"].lower()
            for word in words:
                if word in doc_lower:
                    score += 1
            scored_docs.append((score, item))
        
        # Sort by score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        top_docs = scored_docs[:n_results]
        
        for score, item in top_docs:
            results["documents"][0].append(item["document"])
            results["metadatas"][0].append(item["metadata"])
            results["ids"][0].append(item["id"])
        
        return results

# Attempt to load chromadb or fallback
chroma_client = None
try:
    import chromadb
    os.makedirs(settings.CHROMADB_DIR, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=settings.CHROMADB_DIR)
    logger.info("ChromaDB persistent client initialized successfully.")
except Exception as e:
    logger.warning(f"ChromaDB connection failed. Falling back to simple in-memory vector store. Error: {e}")
    chroma_client = LocalVectorStore()

def get_vector_store():
    return chroma_client
