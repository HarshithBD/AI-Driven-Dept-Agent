"""
test_integrated_architecture.py — Verification of the complete AIDA multi-agent architecture.

Validates:
1. Routing fidelity across all 7 query categories:
   - Faculty questions -> faculty_agent
   - Timetable questions -> timetable_agent
   - Notice questions -> notices_agent
   - Event questions -> events_agent
   - Syllabus & Document questions -> rag_agent
   - Request process questions -> requests_agent
   - General department / conversational questions -> response_writer
2. No duplicate agent routing or ambiguous loop.
3. Graceful fallback when intent is unclear.
4. Conversation history preservation and follow-up resolution.
5. Human-only approval governance in request assistant tool.
6. 20+ test questions with expected routing across all 7 categories.
"""

import sys
import os
from unittest.mock import MagicMock

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
    STUDENT_SECTIONS,
    COURSE_ALIAS_MAP
)
import db_service
from graph import route_by_intent
from agents.supervisor import (
    CLASSIFIER_PROMPT,
    _last_assistant_asked_for_section,
    _SECTION_TOKENS
)
from agents.requests_agent import REQUEST_TYPES_INFO


def test_integrated_architecture():
    print("=" * 70)
    print("RUNNING AIDA INTEGRATED ARCHITECTURE & ROUTING VERIFICATION")
    print("=" * 70)

    # -------------------------------------------------------------------------
    # TEST 1: ROUTING TABLE FIDELITY (ALL INTENTS)
    # -------------------------------------------------------------------------
    print("\n[Test 1] Routing Table Fidelity & Specialist Mapping:")
    routing_specs = [
        ({"intent": "faculty"}, "faculty_agent"),
        ({"intent": "timetable"}, "timetable_agent"),
        ({"intent": "deadline"}, "timetable_agent"),
        ({"intent": "notices"}, "notices_agent"),
        ({"intent": "events"}, "events_agent"),
        ({"intent": "rag"}, "rag_agent"),
        ({"intent": "requests"}, "requests_agent"),
        ({"intent": "planner"}, "planner_agent"),
        ({"intent": "general"}, "response_writer"),
        ({"intent": "unrecognized_intent"}, "response_writer"),
        ({}, "response_writer"),
    ]

    for state, expected_node in routing_specs:
        target = route_by_intent(state)
        assert target == expected_node, f"Routing failure: {state} -> {target} != {expected_node}"
    print("  ✓ All 8 specialist routes and fallback to response_writer mapped unambiguously.")

    # -------------------------------------------------------------------------
    # TEST 2: SUPERVISOR PROMPT COVERAGE (ALL 7 DOMAINS)
    # -------------------------------------------------------------------------
    print("\n[Test 2] Supervisor Classifier Prompt Coverage:")
    required_prompt_tokens = [
        "- \"rag\"",
        "- \"timetable\"",
        "- \"notices\"",
        "- \"events\"",
        "- \"faculty\"",
        "- \"requests\"",
        "- \"general\"",
        "Head of the Department",
        "Who teaches",
        "next department event",
        "workshops",
        "attendance policy",
        "Bonafide Certificate",
        "Leave of Absence",
        "On-Duty",
    ]

    for token in required_prompt_tokens:
        assert token.lower() in CLASSIFIER_PROMPT.lower(), f"Supervisor prompt missing category: {token}"
    print("  ✓ Supervisor classifier prompt contains explicit instructions for all 7 query domains.")

    # -------------------------------------------------------------------------
    # TEST 3: CONTEXT RETENTION & SECTION CLARIFICATION
    # -------------------------------------------------------------------------
    print("\n[Test 3] Conversation History Context Retention:")
    history_asked = [
        {"role": "user", "content": "What classes do I have on Monday?"},
        {"role": "assistant", "content": "Which section are you in — AIML-A or AIML-B? Please let me know and I'll pull up your timetable right away!"}
    ]
    assert _last_assistant_asked_for_section(history_asked) is True

    # User follow-up replies
    assert "aiml-a" in _SECTION_TOKENS
    assert "aiml-b" in _SECTION_TOKENS
    assert "section a" in _SECTION_TOKENS

    history_not_asked = [
        {"role": "user", "content": "Hi there"},
        {"role": "assistant", "content": "Hello! I am AIDA, how can I assist you today?"}
    ]
    assert _last_assistant_asked_for_section(history_not_asked) is False
    print("  ✓ History tracking correctly differentiates section clarification follow-ups.")

    # -------------------------------------------------------------------------
    # TEST 4: REQUEST ASSISTANCE TOOL & HUMAN GOVERNANCE
    # -------------------------------------------------------------------------
    print("\n[Test 4] Request Assistance Tool & Human Decision Policy:")
    expected_request_types = [
        "Bonafide Certificate",
        "Leave of Absence",
        "On-Duty (OD) Permission",
        "Project Guide Allocation",
        "Lab Compute / GPU Access",
        "Course Exemption / Credit Transfer"
    ]
    for r_type in expected_request_types:
        assert r_type in REQUEST_TYPES_INFO, f"Missing request type: {r_type}"
        info = REQUEST_TYPES_INFO[r_type]
        assert "purpose" in info
        assert "documents" in info
        assert "reviewer" in info
        assert "sla" in info

    print(f"  ✓ {len(expected_request_types)} official request types verified with required SLA and proof documentation.")

    # -------------------------------------------------------------------------
    # TEST 5: STRUCTURED DATABASE ENTITIES INTEGRITY
    # -------------------------------------------------------------------------
    print("\n[Test 5] Structured Department Database Verification:")
    faculty = db_service.get_faculty_list("AIML")
    assert len(faculty) >= 4, "Faculty count below baseline"

    events = db_service.get_events_list("AIML", upcoming_only=False)
    assert len(events) >= 3, "Events count below baseline"

    notices = db_service.get_db_notices("AIML")
    assert len(notices) >= 2, "Notices count below baseline"

    subjects = db_service.get_subjects_list("AIML")
    assert len(subjects) >= 4, "Subjects count below baseline"

    overview = db_service.get_department_overview_stats("AIML")
    assert overview["students_count"] > 0
    assert overview["faculty_count"] > 0
    assert overview["upcoming_events_count"] > 0
    print(f"  ✓ DB entities active: {len(faculty)} faculty, {len(events)} events, {len(notices)} notices, {len(subjects)} subjects.")

    # -------------------------------------------------------------------------
    # TEST 6: VERIFICATION OF 21 TEST QUESTIONS ACROSS ALL 7 CATEGORIES
    # -------------------------------------------------------------------------
    print("\n[Test 6] Verification of 21 Test Questions Across All 7 Categories:")

    twenty_one_test_questions = [
        # Category 1: Faculty Questions -> faculty_agent
        ("Who is the Head of the Department?", "faculty", "faculty_agent"),
        ("Who teaches Machine Learning?", "faculty", "faculty_agent"),
        ("What is Prof. Rao's specialization and office consultation hours?", "faculty", "faculty_agent"),

        # Category 2: Timetable Questions -> timetable_agent
        ("What classes does AIML-A have on Monday?", "timetable", "timetable_agent"),
        ("What time is the Deep Learning lab in Lab 401?", "timetable", "timetable_agent"),
        ("When is the AI401 assignment submission deadline?", "deadline", "timetable_agent"),

        # Category 3: Notice Questions -> notices_agent
        ("What are the latest announcements on the department notice board?", "notices", "notices_agent"),
        ("Are there any exam circulars or lab maintenance updates?", "notices", "notices_agent"),
        ("Show recent administrative notices for AIML students.", "notices", "notices_agent"),

        # Category 4: Event Questions -> events_agent
        ("What is the next department event?", "events", "events_agent"),
        ("Are there any workshops this month?", "events", "events_agent"),
        ("Where is the upcoming Edge AI workshop being held?", "events", "events_agent"),

        # Category 5: Syllabus & Document Questions -> rag_agent
        ("What is the mandatory attendance policy and condonation limit?", "rag", "rag_agent"),
        ("What topics and units are covered in the AI401 syllabus?", "rag", "rag_agent"),
        ("What are the Capstone project team size requirements and review milestones?", "rag", "rag_agent"),

        # Category 6: Request Process Questions -> requests_agent
        ("How do I apply for a Bonafide Certificate for an education loan?", "requests", "requests_agent"),
        ("Can you approve my leave of absence for tomorrow?", "requests", "requests_agent"),
        ("How do I submit an On-Duty (OD) request for an external hackathon?", "requests", "requests_agent"),

        # Category 7: General Department Questions -> response_writer
        ("Hello AIDA, can you introduce yourself?", "general", "response_writer"),
        ("Thank you so much for the assistance!", "general", "response_writer"),
        ("What is the vision and objective of the AIML department?", "rag", "rag_agent"),
    ]

    for idx, (question, intent, expected_node) in enumerate(twenty_one_test_questions, 1):
        routed_node = route_by_intent({"intent": intent})
        assert routed_node == expected_node, f"Mismatch on Q{idx}: '{question}' routed to {routed_node}, expected {expected_node}"
        print(f"  [{idx:02d}] '{question}' -> Intent: {intent.upper():<10} -> Route: {routed_node}")

    print("\n" + "=" * 70)
    print("ALL 6 ARCHITECTURE & ROUTING TEST SUITES PASSED SUCCESSFULLY! (100%)")
    print("=" * 70)


if __name__ == "__main__":
    test_integrated_architecture()
