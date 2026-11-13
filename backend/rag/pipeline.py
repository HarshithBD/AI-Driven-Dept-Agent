"""
pipeline.py — RAG pipeline orchestrator for AIDA.

Ties together parsing, chunking, embedding, and vector store
into two main operations: ingest and search.
"""

import hashlib
import json
import time
from typing import Optional, List, Dict, Any
from langchain_core.documents import Document
from . import parser, chunker, embeddings, vectorstore


# Module-level index cache (loaded once, reused for all searches)
_index = None
_bm25 = None

# In-memory query cache for instant responses (0ms RAG retrieval latency)
_SEARCH_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_MAX_SIZE = 256
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cache_key(query: str, top_k: int, filter: Optional[dict]) -> str:
    raw = f"{query.strip().lower()}:{top_k}:{json.dumps(filter or {}, sort_keys=True)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ingest_documents(docs_dir: str, tags_map: Optional[dict] = None) -> int:
    """
    Full ingestion pipeline: parse all documents (PDF, MD, TXT, DOCX) -> chunk -> embed -> build indices.

    Args:
        docs_dir: Path to directory containing document files.
        tags_map: Optional dict mapping filenames to tag dicts {department, category, year, course}.

    Returns:
        Number of chunks created and indexed.
    """
    print("=" * 60)
    print("Starting AIDA document ingestion pipeline...")
    print("=" * 60)

    # Step 1: Parse
    print("\n[1/3] Parsing documents from:", docs_dir)
    pages = parser.parse_all_documents(docs_dir)
    if not pages:
        print("No document pages found. Make sure supported documents exist in:", docs_dir)
        return 0

    # Step 2: Chunk (with department, category, year, course metadata)
    print("\n[2/3] Chunking text into semantically cohesive passages...")
    chunks = chunker.chunk_documents(pages, tags_map=tags_map)

    # Step 3: Embed + upload to Qdrant (and save local BM25 chunks)
    print("\n[3/3] Generating embeddings and building vector/BM25 indices...")
    try:
        embedding_model = embeddings.get_embeddings()
    except Exception as e:
        print(f"[RAG Pipeline] Embedding model load warning: {e}")
        embedding_model = None

    vectorstore.create_index(chunks, embedding_model)
    _SEARCH_CACHE.clear()

    print("\n" + "=" * 60)
    print(f"Ingestion complete! {len(pages)} pages -> {len(chunks)} chunks indexed.")
    print("=" * 60)
    return len(chunks)


def load_index() -> None:
    """
    Connect to Qdrant collection and load BM25 chunks into memory.
    Call this once on server startup.
    """
    global _index, _bm25
    try:
        embedding_model = embeddings.get_embeddings()
        _index = vectorstore.load_index(embedding_model) if embedding_model else None
    except Exception as e:
        print(f"[RAG Pipeline] Qdrant load note: {e}")
        _index = None

    _bm25 = vectorstore.get_bm25_retriever()
    mode = "Hybrid (Qdrant + BM25)" if _index else "Local Sparse (BM25 + FlashRank)"
    print(f"[RAG Pipeline] Index initialized in {mode} mode.")


def search_documents(query: str, top_k: int = 5, filter: Optional[dict] = None) -> List[Document]:
    """
    Search the loaded indices for relevant chunks with optional filtering.
    Uses an in-memory cache for instant responses on repeated queries.
    Falls back to lazy initialization if load_index() wasn't called yet.
    """
    global _index, _bm25, _SEARCH_CACHE

    cache_key = _get_cache_key(query, top_k, filter)
    now = time.time()
    if cache_key in _SEARCH_CACHE:
        entry = _SEARCH_CACHE[cache_key]
        if now - entry["timestamp"] < _CACHE_TTL_SECONDS:
            return entry["results"]

    if _index is None and _bm25 is None:
        load_index()

    results = vectorstore.search(_index, query, top_k, filter=filter, bm25_retriever=_bm25)

    if len(_SEARCH_CACHE) >= _CACHE_MAX_SIZE:
        oldest_key = min(_SEARCH_CACHE.keys(), key=lambda k: _SEARCH_CACHE[k]["timestamp"])
        _SEARCH_CACHE.pop(oldest_key, None)

    _SEARCH_CACHE[cache_key] = {"results": results, "timestamp": now}
    return results
