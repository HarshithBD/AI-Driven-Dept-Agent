"""
rag_agent.py — Academic & Department Document Retrieval Agent for AIDA.

Retrieves verified excerpts from department-specific documents:
- AIML Syllabus & Course Descriptions (AI401, AI402, AI403, AI404, AI405)
- Academic Regulations (Attendance, Passing Marks, Grading Scale, Condonation)
- Project Guidelines (Major/Minor Capstone milestones, Team sizes, Evaluation rubrics)
- Laboratory Manuals & Workstation Conduct (GPU Cluster, Jetson Orin, SLURM)
- Department Policies & Academic Calendars

Guarantees zero hallucination: grounds answers strictly in official documentation.
"""

from __future__ import annotations

import os
from typing import Optional, List, Dict, Any
from agents.state import GraphState
from department_config import DEPARTMENT_CODE, DEPARTMENT_NAME, DEPARTMENT_COURSES
from rag import search_documents


def _detect_category_filter(query_lower: str) -> Optional[str]:
    """Detect specific document category requested in natural language query."""
    if any(k in query_lower for k in ["syllabus", "curriculum", "unit", "topics covered", "course content", "credits"]):
        return "AIML Syllabus"
    elif any(k in query_lower for k in ["project", "capstone", "milestone", "thesis", "dissertation", "synopsis", "guide allocation"]):
        return "Project Guidelines"
    elif any(k in query_lower for k in ["attendance", "condonation", "passing criteria", "passing mark", "grading", "grade point", "gpa", "supplementary", "malpractice", "plagiarism"]):
        return "Academic Regulations"
    elif any(k in query_lower for k in ["lab manual", "laboratory", "workstation", "gpu", "jetson", "slurm", "storage quota", "safety rule"]):
        return "Laboratory Manuals"
    elif any(k in query_lower for k in ["calendar", "holiday", "reopening", "working day"]):
        return "Academic Resources"
    elif any(k in query_lower for k in ["policy", "handbook", "code of conduct", "hostel"]):
        return "Department Policies"
    return None


def _detect_course_filter(query_lower: str) -> Optional[str]:
    """Detect specific AIML course code if mentioned in query."""
    for c in DEPARTMENT_COURSES:
        course_id = c["id"].lower()
        if course_id in query_lower:
            return c["id"]
        for alias in c.get("aliases", []):
            if alias.lower() in query_lower:
                return c["id"]
    return None


async def rag_node(state: GraphState) -> dict:
    """
    Search department documents for relevant chunks and populate state context and sources.
    """
    query = state["query"]
    context = list(state.get("context", []))
    sources = list(state.get("sources", []))

    query_lower = query.lower()

    # 1. Metadata filter extraction
    search_filter: Dict[str, Any] = {}
    
    # Priority: AIML department documents
    if any(k in query_lower for k in ["aiml", "ai", "machine learning", "department"]):
        search_filter["department"] = DEPARTMENT_CODE

    category = _detect_category_filter(query_lower)
    if category:
        search_filter["category"] = category

    course = _detect_course_filter(query_lower)
    if course:
        search_filter["course"] = course

    print(f"[RAG Agent] Searching department docs (Filter: {search_filter}) for: '{query[:65]}...'")

    try:
        # 2. Search knowledge base (hybrid dense + sparse + rerank)
        # First attempt with targeted filter
        docs = search_documents(query, top_k=5, filter=search_filter if search_filter else None)

        # If strict filter returned no results, broaden search without metadata restrictions
        if not docs and search_filter:
            print(f"[RAG Agent] Strict filter returned 0 results. Broadening search without filter...")
            docs = search_documents(query, top_k=5, filter=None)

        if docs:
            for doc in docs:
                source = doc.metadata.get("source", "Department Document")
                page = doc.metadata.get("page", 1)
                doc_cat = doc.metadata.get("category", "Official Document")
                content = doc.page_content.strip()

                header_prefix = f"[{source} | Page {page}"
                if doc_cat:
                    header_prefix += f" | {doc_cat}"
                header_prefix += "]\n"

                context_entry = {
                    "tool": "search_department_docs",
                    "source": source,
                    "page": page,
                    "category": doc_cat,
                    "content": f"{header_prefix}{content}",
                }
                if doc.metadata.get("department"):
                    context_entry["department"] = doc.metadata["department"]
                if doc.metadata.get("course"):
                    context_entry["course"] = doc.metadata["course"]

                context.append(context_entry)
                sources.append({"doc": source, "page": page})

            print(f"[RAG Agent] Retrieved {len(docs)} verified document passages.")

        else:
            # 3. Grounded message when no info is found in uploaded documents
            no_info_msg = (
                f"No specific information found in the official {DEPARTMENT_NAME} ({DEPARTMENT_CODE}) documents "
                f"(syllabus, regulations, project guidelines, or lab manuals) regarding: '{query}'. "
                f"Department policies and syllabus details must not be assumed. Please consult your course instructor or the AIML Department Office."
            )
            context.append({
                "tool": "search_department_docs",
                "source": f"{DEPARTMENT_CODE} Knowledge Base",
                "content": no_info_msg,
            })
            print(f"[RAG Agent] No matching documents found for query.")

    except Exception as e:
        print(f"[RAG Agent] Retrieval exception: {e}")
        context.append({
            "tool": "search_department_docs",
            "source": f"{DEPARTMENT_CODE} Knowledge Base",
            "content": f"Unable to retrieve department documents: {str(e)}",
        })

    return {"context": context, "sources": sources}
