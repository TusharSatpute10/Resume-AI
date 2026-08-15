"""
db/chroma_client.py
────────────────────
In-memory vector store with JSON file persistence.
"""

import json
import os
import numpy as np
from config.settings import get_settings

settings = get_settings()

# In-memory stores
_resume_store = {"ids": [], "embeddings": [], "documents": [], "metadatas": []}
_jd_store = {"ids": [], "embeddings": [], "documents": [], "metadatas": []}

# Persistence files
RESUME_FILE = os.path.join(settings.chroma_persist_dir, "resumes.json")
JD_FILE = os.path.join(settings.chroma_persist_dir, "jds.json")

# Ensure persist directory exists
os.makedirs(settings.chroma_persist_dir, exist_ok=True)

def _load_data():
    """Load data from JSON files on startup."""
    global _resume_store, _jd_store
    
    if os.path.exists(RESUME_FILE):
        with open(RESUME_FILE, 'r') as f:
            data = json.load(f)
            _resume_store = data
            # Convert embeddings back to lists if needed
            _resume_store["embeddings"] = [np.array(e).tolist() if isinstance(e, list) else e for e in _resume_store["embeddings"]]
    
    if os.path.exists(JD_FILE):
        with open(JD_FILE, 'r') as f:
            data = json.load(f)
            _jd_store = data
            _jd_store["embeddings"] = [np.array(e).tolist() if isinstance(e, list) else e for e in _jd_store["embeddings"]]

def _save_data():
    """Save data to JSON files."""
    with open(RESUME_FILE, 'w') as f:
        json.dump(_resume_store, f, indent=2)
    
    with open(JD_FILE, 'w') as f:
        json.dump(_jd_store, f, indent=2)

# Load data on import
_load_data()

def _cosine_similarity(a, b):
    a, b = np.array(a), np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)


def store_resume(doc_id: str, text: str, embedding: list, metadata: dict):
    # Remove existing entry if same id
    if doc_id in _resume_store["ids"]:
        idx = _resume_store["ids"].index(doc_id)
        for key in _resume_store:
            _resume_store[key].pop(idx)
    _resume_store["ids"].append(doc_id)
    _resume_store["embeddings"].append(embedding)
    _resume_store["documents"].append(text)
    _resume_store["metadatas"].append(metadata)
    _save_data()  # Persist to disk
    print(f"Resume stored | id={doc_id} | total={len(_resume_store['ids'])}")


def store_jd(doc_id: str, text: str, embedding: list, metadata: dict):
    if doc_id in _jd_store["ids"]:
        idx = _jd_store["ids"].index(doc_id)
        for key in _jd_store:
            _jd_store[key].pop(idx)
    _jd_store["ids"].append(doc_id)
    _jd_store["embeddings"].append(embedding)
    _jd_store["documents"].append(text)
    _jd_store["metadatas"].append(metadata)
    _save_data()  # Persist to disk
    print(f"JD stored | id={doc_id} | total={len(_jd_store['ids'])}")


def _rank_items(store: dict, query_embedding: list, top_k: int) -> list:
    if not store["ids"]:
        return []

    scores = [
        _cosine_similarity(query_embedding, embedding)
        for embedding in store["embeddings"]
    ]

    ranked = sorted(
        zip(store["ids"], store["documents"], store["metadatas"], scores),
        key=lambda item: item[3],
        reverse=True,
    )[:top_k]

    return [
        {
            "id": doc_id,
            "document": document,
            "metadata": metadata,
            "score": float(score),
        }
        for doc_id, document, metadata, score in ranked
    ]


def search_resumes(query_embedding: list, top_k: int = 10) -> list:
    return _rank_items(_resume_store, query_embedding, top_k)


def search_jds(query_embedding: list, top_k: int = 10) -> list:
    return _rank_items(_jd_store, query_embedding, top_k)
