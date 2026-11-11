"""
vectorstore.py — Vector store and retrieval management for AIDA.

Supports:
1. High-speed vector search with Qdrant when online.
2. Graceful fallback to BM25 sparse keyword search and FlashRank cross-encoder reranking.
3. Metadata filtering across department (AIML), category, year, and course.
"""

from __future__ import annotations

import os
import pickle
from typing import Optional, List, Dict, Any

from langchain_core.documents import Document

try:
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, Filter, FieldCondition, MatchValue
except ImportError:
    QdrantVectorStore = None
    QdrantClient = None

try:
    from langchain_community.retrievers import BM25Retriever
except ImportError:
    BM25Retriever = None

try:
    from flashrank import Ranker, RerankRequest
except ImportError:
    Ranker = None
    RerankRequest = None


VECTORSTORE_DIR = os.path.join(os.path.dirname(__file__), "..", "vectorstore")
CHUNKS_PATH = os.path.join(VECTORSTORE_DIR, "chunks.pkl")

# Qdrant config — read from environment
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "campus_assistant")

# BAAI/bge-small-en-v1.5 and all-MiniLM-L6-v2 dimension: 384
EMBEDDING_DIM = 384


def _get_client() -> Optional[Any]:
    """Create and return a Qdrant client, or None if unavailable."""
    if not QdrantClient:
        return None
    try:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=3.0, check_compatibility=False)
    except Exception as e:
        print(f"[Vectorstore] Qdrant client initialization warning: {e}")
        return None


def create_index(chunks: List[Document], embeddings: Any) -> Optional[Any]:
    """
    Index document chunks for neural retrieval and save local BM25 cache.

    Args:
        chunks: List of LangChain Documents with page_content and metadata.
        embeddings: Embedding model instance.

    Returns:
        QdrantVectorStore instance if online, or None.
    """
    # 1. Always save raw chunks locally for BM25 and fallback retrieval
    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(chunks, f)
    print(f"[RAG Store] Saved {len(chunks)} chunks to {CHUNKS_PATH}.")

    # 2. Upload to Qdrant if server is reachable
    store = None
    client = _get_client()
    if client and QdrantVectorStore:
        try:
            existing = [c.name for c in client.get_collections().collections]
            if COLLECTION_NAME in existing:
                print(f"[Qdrant] Deleting existing collection '{COLLECTION_NAME}'...")
                client.delete_collection(COLLECTION_NAME)

            print(f"[Qdrant] Creating collection '{COLLECTION_NAME}' (dim={EMBEDDING_DIM})...")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )

            store = QdrantVectorStore.from_documents(
                documents=chunks,
                embedding=embeddings,
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                collection_name=COLLECTION_NAME,
            )
            print(f"[Qdrant] Uploaded {len(chunks)} chunks to '{COLLECTION_NAME}'.")
        except Exception as e:
            print(f"[Vectorstore] Qdrant server unreachable ({e}). Operating in local BM25 fallback mode.")

    return store


def load_index(embeddings: Any) -> Optional[Any]:
    """
    Connect to existing Qdrant collection if online.
    Returns None if Qdrant is offline.
    """
    client = _get_client()
    if client and QdrantVectorStore:
        try:
            existing = [c.name for c in client.get_collections().collections]
            if COLLECTION_NAME in existing:
                store = QdrantVectorStore(
                    client=client,
                    collection_name=COLLECTION_NAME,
                    embedding=embeddings,
                )
                print(f"[Qdrant] Connected to collection '{COLLECTION_NAME}'.")
                return store
        except Exception as e:
            print(f"[Vectorstore] Qdrant connection offline ({e}).")
    return None


def get_bm25_retriever(path: str = VECTORSTORE_DIR) -> Optional[Any]:
    """Load saved chunks and initialize a BM25 retriever."""
    if not os.path.exists(CHUNKS_PATH):
        print(f"[RAG Core] WARNING: BM25 chunks not found at {CHUNKS_PATH}")
        return None
    try:
        with open(CHUNKS_PATH, "rb") as f:
            chunks = pickle.load(f)
        if BM25Retriever and chunks:
            print(f"[RAG Core] BM25 indexing {len(chunks)} chunks...")
            return BM25Retriever.from_documents(chunks)
    except Exception as e:
        print(f"[RAG Core] Error loading BM25 chunks: {e}")
    return None


def rerank_results(query: str, docs: List[Document], top_k: int = 5) -> List[Document]:
    """Use FlashRank to rerank the retrieved documents, with graceful fallback."""
    if not docs:
        return []
    if not Ranker or not RerankRequest:
        return docs[:top_k]

    try:
        ranker = Ranker(
            model_name="ms-marco-MiniLM-L-12-v2",
            cache_dir=os.path.join(VECTORSTORE_DIR, "flashrank_cache")
        )

        passages = [
            {"id": i, "text": doc.page_content, "meta": doc.metadata}
            for i, doc in enumerate(docs)
        ]

        rerank_request = RerankRequest(query=query, passages=passages)
        results = ranker.rerank(rerank_request)

        return [
            Document(page_content=res["text"], metadata=res["meta"])
            for res in results[:top_k]
        ]
    except Exception as e:
        print(f"[RAG Core] FlashRank rerank fallback: {e}")
        return docs[:top_k]


def search(
    index: Optional[Any],
    query: str,
    top_k: int = 5,
    filter: Optional[Dict[str, Any]] = None,
    use_hybrid: bool = True,
    bm25_retriever: Optional[Any] = None
) -> List[Document]:
    """
    Search documents with Hybrid (Dense Qdrant + Sparse BM25) and FlashRank reranking.
    Falls back gracefully to BM25 if Qdrant is unavailable.
    """
    bm25 = bm25_retriever if bm25_retriever else get_bm25_retriever()

    # Case A: Qdrant vector store is active
    if index is not None:
        qdrant_filter = None
        if filter and Filter and FieldCondition and MatchValue:
            conditions = [
                FieldCondition(key=f"metadata.{k}", match=MatchValue(value=v))
                for k, v in filter.items()
            ]
            qdrant_filter = Filter(must=conditions)

        try:
            dense_results = index.similarity_search(query, k=15, filter=qdrant_filter)
        except Exception as e:
            print(f"[Vectorstore] Dense search error: {e}")
            dense_results = []

        if not use_hybrid:
            return dense_results[:top_k]

        sparse_results = []
        if bm25:
            try:
                sparse_results = bm25.invoke(query)[:15]
            except Exception as e:
                print(f"[Vectorstore] Sparse BM25 error: {e}")

        # Merge with deduplication
        seen_content = set()
        combined = []
        for doc in dense_results + sparse_results:
            content_hash = hash(doc.page_content)
            if content_hash not in seen_content:
                combined.append(doc)
                seen_content.add(content_hash)

        print(f"[RAG Core] Reranking {len(combined)} hybrid candidates for query...")
        return rerank_results(query, combined, top_k=top_k)

    # Case B: Offline fallback — use local BM25 retriever + metadata filter
    print("[RAG Core] Searching via local BM25 engine...")
    if not bm25:
        return []

    try:
        candidates = bm25.invoke(query)
    except Exception as e:
        print(f"[RAG Core] BM25 invoke error: {e}")
        return []

    # Apply metadata filtering if specified
    if filter:
        filtered = []
        for doc in candidates:
            matches = True
            for k, v in filter.items():
                if str(doc.metadata.get(k, "")).lower() != str(v).lower():
                    matches = False
                    break
            if matches:
                filtered.append(doc)
        candidates = filtered or candidates

    return rerank_results(query, candidates, top_k=top_k)
