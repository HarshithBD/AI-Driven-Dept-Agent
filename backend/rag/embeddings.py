"""
embeddings.py — HuggingFace Inference API embeddings.

Uses the HuggingFace API (no local model download) to generate
text embeddings for documents and queries.
"""

import os
from typing import Optional
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings


def get_embeddings() -> Optional[FastEmbedEmbeddings]:
    """
    Create and return a local FastEmbed embedding model.

    Runs locally using FastEmbed (no PyTorch, very lightweight, completely free).
    Model: BAAI/bge-small-en-v1.5 (384 dimensions)

    Returns:
        FastEmbedEmbeddings instance or None if initialization fails.
    """
    try:
        return FastEmbedEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
        )
    except Exception as e:
        print(f"[Embeddings] FastEmbed initialization note (operating in sparse fallback): {e}")
        return None
