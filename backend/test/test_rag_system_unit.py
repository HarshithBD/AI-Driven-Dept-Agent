"""
test_rag_system_unit.py — Unit test for AIDA RAG Pipeline, Document Parsing,
Metadata Filtering, and Grounded Retrieval.
Does not require external vector databases or network access.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.parser import parse_text_file, parse_document
from rag.chunker import chunk_documents
from agents.rag_agent import _detect_category_filter, _detect_course_filter
import json

_DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "docs")
_TAGS_FILE = os.path.join(os.path.dirname(__file__), "..", "doc_tags.json")


def test_text_markdown_extraction():
    """Test 1: Multi-Format Text Extraction (Markdown / Text)."""
    syllabus_path = os.path.join(_DOCS_DIR, "AIML_Department_Syllabus_2026.md")
    assert os.path.exists(syllabus_path), f"File missing: {syllabus_path}"
    
    pages = parse_text_file(syllabus_path)
    assert len(pages) >= 1
    assert any("AI401" in p["text"] for p in pages)
    assert pages[0]["source"] == "AIML_Department_Syllabus_2026.md"

    regulations_path = os.path.join(_DOCS_DIR, "AIML_Academic_Regulations_and_Policies.md")
    reg_pages = parse_text_file(regulations_path)
    assert len(reg_pages) >= 1
    assert any("75%" in p["text"] for p in reg_pages)


def test_document_chunking_metadata():
    """Test 2: Document Chunking & Metadata Preservation."""
    syllabus_path = os.path.join(_DOCS_DIR, "AIML_Department_Syllabus_2026.md")
    pages = parse_text_file(syllabus_path)
    
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


def test_category_filter_extraction():
    """Test 3: Natural Language Category Filter Extraction."""
    assert _detect_category_filter("What are the topics covered in the AI401 syllabus?".lower()) == "AIML Syllabus"
    assert _detect_category_filter("What is the attendance condonation policy and passing marks?".lower()) == "Academic Regulations"
    assert _detect_category_filter("What are the project milestones and team size rules?".lower()) == "Project Guidelines"
    assert _detect_category_filter("What are the GPU cluster access rules and Jetson lab requirements?".lower()) == "Laboratory Manuals"


def test_course_code_extraction():
    """Test 4: Course Code Extraction from Queries."""
    assert _detect_course_filter("tell me about ai401") == "AI401"
    assert _detect_course_filter("what is machine learning foundations?") == "AI401"
    assert _detect_course_filter("explain ai402 deep learning") == "AI402"
    assert _detect_course_filter("nlp and llms course details") == "AI403"


def test_tag_registry_integrity():
    """Test 5: Knowledge Base Tag Registry."""
    with open(_TAGS_FILE, "r") as f:
        tags_data = json.load(f)
    assert "AIML_Department_Syllabus_2026.md" in tags_data
    assert "AIML_Academic_Regulations_and_Policies.md" in tags_data
    assert "AIML_BTech_Project_Guidelines_2026.md" in tags_data
    assert "AIML_Laboratory_Manual_and_Safety_Guidelines.md" in tags_data


def test_academic_regulations_ground_truth():
    """Test 6: Regulations Knowledge Verification (Ground Truth)."""
    regulations_path = os.path.join(_DOCS_DIR, "AIML_Academic_Regulations_and_Policies.md")
    with open(regulations_path, "r", encoding="utf-8") as f:
        reg_text = f.read()
    assert "75%" in reg_text        # Minimum attendance
    assert "65%" in reg_text        # Condonation threshold
    assert "40% in SEE" in reg_text
    assert "50% in CIE + SEE" in reg_text
    assert "15%" in reg_text        # Anti-plagiarism limit


def test_project_guidelines_ground_truth():
    """Test 7: Project Guidelines Verification (Ground Truth)."""
    project_path = os.path.join(_DOCS_DIR, "AIML_BTech_Project_Guidelines_2026.md")
    with open(project_path, "r", encoding="utf-8") as f:
        proj_text = f.read()
    assert "3 to 4 students" in proj_text
    assert "Milestone 1 (Week 4)" in proj_text
    assert "Milestone 2 (Week 8)" in proj_text
    assert "Milestone 4 (Week 15)" in proj_text


def test_lab_manual_ground_truth():
    """Test 8: Lab Manual & GPU Cluster Verification (Ground Truth)."""
    lab_path = os.path.join(_DOCS_DIR, "AIML_Laboratory_Manual_and_Safety_Guidelines.md")
    with open(lab_path, "r", encoding="utf-8") as f:
        lab_text = f.read()
    assert "RTX 4090" in lab_text
    assert "Jetson AGX Orin" in lab_text
    assert "50 GB persistent" in lab_text


# ── Keep backward-compatible run_tests() for direct script execution ──────────
def run_tests():
    test_text_markdown_extraction()
    test_document_chunking_metadata()
    test_category_filter_extraction()
    test_course_code_extraction()
    test_tag_registry_integrity()
    test_academic_regulations_ground_truth()
    test_project_guidelines_ground_truth()
    test_lab_manual_ground_truth()
    print("ALL 8 RAG SYSTEM & AGENT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
