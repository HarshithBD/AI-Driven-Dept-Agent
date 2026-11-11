"""
test_rag_system_unit.py — Unit test for AIDA RAG Pipeline, Document Parsing,
Metadata Filtering, and Grounded Retrieval.
Does not require external vector databases or network access.
"""

import sys, os
from unittest.mock import MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock Document class
class MockDocument:
    def __init__(self, page_content="", metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}

class MockSplitter:
    def __init__(self, chunk_size=600, chunk_overlap=100, **kwargs):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str):
        if not text:
            return []
        step = max(self.chunk_size - self.chunk_overlap, 100)
        chunks = []
        for i in range(0, len(text), step):
            chunks.append(text[i:i + self.chunk_size])
        return chunks

# Mock external modules for isolated test execution
for mod_name in [
    "langchain", "langchain.schema", "langchain_core", "langchain_core.messages",
    "langchain_core.documents", "langchain_text_splitters", "langchain_google_genai",
    "langchain_huggingface", "langchain_community", "langchain_community.embeddings",
    "langchain_community.embeddings.fastembed", "langchain_community.retrievers",
    "langgraph", "langgraph.graph", "qdrant_client", "fastmcp", "fastmcp.client",
    "mcp", "rank_bm25", "flashrank", "pdfplumber", "docx", "fastembed"
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

sys.modules["langchain_core.documents"].Document = MockDocument
sys.modules["langchain_text_splitters"].RecursiveCharacterTextSplitter = MockSplitter

from rag.parser import parse_text_file, parse_document
from rag.chunker import chunk_documents
from agents.rag_agent import _detect_category_filter, _detect_course_filter
import json

def run_tests():
    print("=" * 65)
    print("RUNNING UNIT TESTS FOR AIDA RAG SYSTEM & AGENT")
    print("=" * 65)

    docs_dir = os.path.join(os.path.dirname(__file__), "..", "data", "docs")

    # 1. Test Text & Markdown Document Extraction
    print("\n[Test 1] Multi-Format Text Extraction (Markdown / Text):")
    syllabus_path = os.path.join(docs_dir, "AIML_Department_Syllabus_2026.md")
    assert os.path.exists(syllabus_path), f"File missing: {syllabus_path}"
    
    pages = parse_text_file(syllabus_path)
    assert len(pages) >= 1
    print(f"  ✓ Extracted {len(pages)} page(s) from 'AIML_Department_Syllabus_2026.md'.")
    assert any("AI401" in p["text"] for p in pages)
    assert pages[0]["source"] == "AIML_Department_Syllabus_2026.md"

    regulations_path = os.path.join(docs_dir, "AIML_Academic_Regulations_and_Policies.md")
    reg_pages = parse_text_file(regulations_path)
    assert len(reg_pages) >= 1
    assert any("75%" in p["text"] for p in reg_pages)
    print(f"  ✓ Extracted {len(reg_pages)} page(s) from 'AIML_Academic_Regulations_and_Policies.md'.")

    # 2. Test Document Chunking & Metadata Enrichment
    print("\n[Test 2] Document Chunking & Metadata Preservation:")
    sample_tags = {
        "AIML_Department_Syllabus_2026.md": {
            "department": "AIML",
            "category": "AIML Syllabus",
            "year": "2025-2026",
            "course": "AI401-AI405"
        }
    }
    chunks = chunk_documents(pages, chunk_size=500, chunk_overlap=80, tags_map=sample_tags)
    assert len(chunks) >= 2
    first_chunk = chunks[0]
    assert first_chunk.metadata.get("department") == "AIML"
    assert first_chunk.metadata.get("category") == "AIML Syllabus"
    assert first_chunk.metadata.get("course") == "AI401-AI405"
    assert "page" in first_chunk.metadata
    print(f"  ✓ Successfully created {len(chunks)} chunks with full department metadata.")

    # 3. Test Category Filter Extraction
    print("\n[Test 3] Natural Language Category Filter Extraction:")
    q_syl = "What are the topics covered in the AI401 syllabus?"
    assert _detect_category_filter(q_syl.lower()) == "AIML Syllabus"
    print(f"  ✓ '{q_syl}' -> Category: AIML Syllabus")

    q_reg = "What is the attendance condonation policy and passing marks?"
    assert _detect_category_filter(q_reg.lower()) == "Academic Regulations"
    print(f"  ✓ '{q_reg}' -> Category: Academic Regulations")

    q_proj = "What are the project milestones and team size rules?"
    assert _detect_category_filter(q_proj.lower()) == "Project Guidelines"
    print(f"  ✓ '{q_proj}' -> Category: Project Guidelines")

    q_lab = "What are the GPU cluster access rules and Jetson lab requirements?"
    assert _detect_category_filter(q_lab.lower()) == "Laboratory Manuals"
    print(f"  ✓ '{q_lab}' -> Category: Laboratory Manuals")

    # 4. Test Course Code Extraction
    print("\n[Test 4] Course Code Extraction from Queries:")
    assert _detect_course_filter("tell me about ai401") == "AI401"
    assert _detect_course_filter("what is machine learning foundations?") == "AI401"
    assert _detect_course_filter("explain ai402 deep learning") == "AI402"
    assert _detect_course_filter("nlp and llms course details") == "AI403"
    print("  ✓ Course codes and aliases correctly mapped to department courses.")

    # 5. Test Tag Storage Integrity
    print("\n[Test 5] Knowledge Base Tag Registry:")
    tags_file = os.path.join(os.path.dirname(__file__), "..", "doc_tags.json")
    with open(tags_file, "r") as f:
        tags_data = json.load(f)
    assert "AIML_Department_Syllabus_2026.md" in tags_data
    assert "AIML_Academic_Regulations_and_Policies.md" in tags_data
    assert "AIML_BTech_Project_Guidelines_2026.md" in tags_data
    assert "AIML_Laboratory_Manual_and_Safety_Guidelines.md" in tags_data
    print(f"  ✓ Verified {len(tags_data)} tagged documents in official registry.")

    # 6. Test Academic Regulations Knowledge Grounding
    print("\n[Test 6] Regulations Knowledge Verification (Ground Truth):")
    with open(regulations_path, "r", encoding="utf-8") as f:
        reg_text = f.read()
    assert "75%" in reg_text  # Minimum attendance
    assert "65%" in reg_text  # Condonation threshold
    assert "40% in SEE" in reg_text  # Minimum SEE marks
    assert "50% in CIE + SEE" in reg_text  # Aggregate passing marks
    assert "15%" in reg_text  # Anti-plagiarism limit
    print("  ✓ Verified mandatory attendance (75%), condonation (65%), SEE passing (40%), and plagiarism limit (15%).")

    # 7. Test Project Guidelines Knowledge Grounding
    print("\n[Test 7] Project Guidelines Verification (Ground Truth):")
    project_path = os.path.join(docs_dir, "AIML_BTech_Project_Guidelines_2026.md")
    with open(project_path, "r", encoding="utf-8") as f:
        proj_text = f.read()
    assert "3 to 4 students" in proj_text  # Team size
    assert "Milestone 1 (Week 4)" in proj_text
    assert "Milestone 2 (Week 8)" in proj_text
    assert "Milestone 4 (Week 15)" in proj_text
    print("  ✓ Verified team size (3-4 students) and 4 capstone milestone review intervals.")

    # 8. Test Lab Manual Knowledge Grounding
    print("\n[Test 8] Lab Manual & GPU Cluster Verification (Ground Truth):")
    lab_path = os.path.join(docs_dir, "AIML_Laboratory_Manual_and_Safety_Guidelines.md")
    with open(lab_path, "r", encoding="utf-8") as f:
        lab_text = f.read()
    assert "RTX 4090" in lab_text
    assert "Jetson AGX Orin" in lab_text
    assert "50 GB persistent" in lab_text
    print("  ✓ Verified GPU cluster hardware (RTX 4090, Jetson Orin) and student quota (50 GB).")

    print("\n" + "=" * 65)
    print("ALL 8 RAG SYSTEM & AGENT TESTS PASSED SUCCESSFULLY! (100%)")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
