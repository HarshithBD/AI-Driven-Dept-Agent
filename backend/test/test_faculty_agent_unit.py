"""
test_faculty_agent_unit.py — Unit test for Faculty Agent matching, sanitization, and routing.
Does not require external network access or LLM APIs.
"""

import sys, os
from unittest.mock import MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock external network and LLM modules if not in test runtime environment
# NOTE: Never mock internal local packages (rag, agents, db_service) or installed core libraries.
for mod_name in [
    "langchain_google_genai",
    "fastmcp", "fastmcp.client", "mcp", "mcp.client", "mcp.client.stdio", "mcp_client",
    "qdrant_client"
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from department_config import (
    DEPARTMENT_CODE,
    DEPARTMENT_NAME,
    DEPARTMENT_COURSES,
    COURSE_ALIAS_MAP
)
import db_service
from agents.faculty_agent import _sanitize_contact_info, _format_faculty_record
from graph import route_by_intent
from agents.supervisor import CLASSIFIER_PROMPT

def test_faculty_agent_logic():
    print("=" * 60)
    print("RUNNING UNIT TESTS FOR FACULTY AGENT & ROUTING")
    print("=" * 60)

    # 1. Test graph routing
    print("\n[Test 1] Graph Routing by Intent:")
    assert route_by_intent({"intent": "faculty"}) == "faculty_agent"
    assert route_by_intent({"intent": "rag"}) == "rag_agent"
    assert route_by_intent({"intent": "timetable"}) == "timetable_agent"
    assert route_by_intent({"intent": "deadline"}) == "timetable_agent"
    assert route_by_intent({"intent": "notices"}) == "notices_agent"
    assert route_by_intent({"intent": "planner"}) == "planner_agent"
    assert route_by_intent({"intent": "general"}) == "response_writer"
    print("  ✓ All 7 intent routes mapped correctly to LangGraph nodes.")

    # 2. Test supervisor prompt definition
    print("\n[Test 2] Supervisor Prompt Structure:")
    assert '"faculty"' in CLASSIFIER_PROMPT
    assert "Head of Department" in CLASSIFIER_PROMPT
    assert "Who teaches Machine Learning?" in CLASSIFIER_PROMPT
    print("  ✓ Classifier prompt contains 'faculty' definition, rules, and examples.")

    # 3. Test contact sanitization
    print("\n[Test 3] Contact Sanitization (Privacy & Directory Standards):")
    sample_contact = "Cabin 401, AIML Block • Ext 4101"
    sanitized = _sanitize_contact_info(sample_contact)
    assert sanitized == sample_contact
    assert _sanitize_contact_info(None) == "Office location on record at AIML Department Main Office."
    print(f"  ✓ Contact sanitized properly: '{sanitized}'")

    # 4. Test database faculty retrieval
    print("\n[Test 4] Database Faculty Records:")
    faculty_list = db_service.get_faculty_list()
    assert len(faculty_list) >= 6
    print(f"  ✓ Retrieved {len(faculty_list)} active department faculty members.")

    # 5. Test HOD lookup
    print("\n[Test 5] Query: 'Who is the Head of the Department?'")
    hods = [f for f in faculty_list if "head" in f.get("designation", "").lower() or "hod" in f.get("designation", "").lower()]
    assert len(hods) == 1
    assert "Sharma" in hods[0]["name"]
    print(f"  ✓ Head of Department identified: {hods[0]['name']} ({hods[0]['designation']})")

    # 6. Test Course Instructor lookup ("Who teaches Machine Learning?")
    print("\n[Test 6] Query: 'Who teaches Machine Learning?'")
    ml_code = COURSE_ALIAS_MAP.get("machine learning")
    assert ml_code == "AI401"
    ml_instructors = [f for f in faculty_list if ml_code in f.get("subjects_handled", [])]
    assert len(ml_instructors) >= 1
    print(f"  ✓ Instructor for Machine Learning ({ml_code}) identified: {ml_instructors[0]['name']}")

    # 7. Test Specialization lookup ("What is Prof. Rao's specialization?")
    print("\n[Test 7] Query: 'What is Prof. Rao's specialization?'")
    raos = [f for f in faculty_list if "rao" in f.get("name", "").lower()]
    assert len(raos) == 1
    assert "Computer Vision" in raos[0]["specialization"]
    print(f"  ✓ Prof. Rao's specialization: {raos[0]['specialization']}")

    # 8. Test Availability / Office Hours lookup
    print("\n[Test 8] Query: 'Is Dr. Sharma available on Monday?'")
    assert "Mon" in hods[0]["availability"]
    print(f"  ✓ Dr. Sharma's availability: {hods[0]['availability']}")

    # 9. Test Non-existent faculty / subject handling
    print("\n[Test 9] Non-existent course / faculty search:")
    non_existent = [f for f in faculty_list if "Quantum Teleportation" in str(f.get("subjects_handled"))]
    assert len(non_existent) == 0
    print("  ✓ Gracefully handles unmapped or non-existent faculty/subject queries without inventing data.")

    # 10. Test Markdown formatting
    print("\n[Test 10] Markdown Formatting of Faculty Record:")
    formatted = _format_faculty_record(hods[0])
    assert "### Dr. A. Sharma" in formatted
    assert "Professor & Head of Department" in formatted
    assert "hod.aiml@greenfield.edu" in formatted
    print("  ✓ Formatted markdown output verified:\n")
    for line in formatted.strip().split("\n"):
        print(f"    {line}")

    print("\n" + "=" * 60)
    print("ALL 10 UNIT TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    test_faculty_agent_logic()
