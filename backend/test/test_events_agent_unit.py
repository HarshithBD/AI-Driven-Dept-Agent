"""
test_events_agent_unit.py — Unit tests for Event Agent parameter extraction,
event database integration, and LangGraph routing.
Does not require external network access or paid LLM API keys.
"""

import sys, os
from unittest.mock import MagicMock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock LangChain and external parser modules for isolated unit testing
for mod_name in [
    "langchain", "langchain.schema", "langchain_core", "langchain_core.messages",
    "langchain_core.documents", "langchain_google_genai", "langgraph", "langgraph.graph",
    "langchain_text_splitters", "langchain_huggingface", "langchain_community",
    "langchain_community.embeddings", "langchain_community.embeddings.fastembed",
    "fastmcp", "fastmcp.client", "mcp", "mcp.client", "mcp.client.stdio", "mcp_client",
    "pdfplumber", "docx", "qdrant_client", "rank_bm25", "flashrank",
    "fastembed", "rag", "rag.embeddings", "rag.vectorstore", "rag.pipeline"
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

from department_config import DEPARTMENT_CODE, DEPARTMENT_NAME
import db_service
from agents.events_agent import (
    _heuristic_param_extraction,
    _format_event_record,
    _parse_event_datetime
)
from graph import route_by_intent
from agents.supervisor import CLASSIFIER_PROMPT

def run_tests():
    print("=" * 65)
    print("RUNNING UNIT TESTS FOR AIDA DEPARTMENT EVENTS SYSTEM & AGENT")
    print("=" * 65)

    # 1. Test Graph Routing
    print("\n[Test 1] LangGraph Routing by Intent:")
    assert route_by_intent({"intent": "events"}) == "events_agent"
    assert route_by_intent({"intent": "faculty"}) == "faculty_agent"
    assert route_by_intent({"intent": "rag"}) == "rag_agent"
    assert route_by_intent({"intent": "timetable"}) == "timetable_agent"
    assert route_by_intent({"intent": "deadline"}) == "timetable_agent"
    assert route_by_intent({"intent": "notices"}) == "notices_agent"
    assert route_by_intent({"intent": "planner"}) == "planner_agent"
    assert route_by_intent({"intent": "general"}) == "response_writer"
    print("  ✓ All 8 intent routes mapped correctly including 'events_agent'.")

    # 2. Test Supervisor Prompt Structure
    print("\n[Test 2] Supervisor Prompt Structure for Events:")
    assert '"events"' in CLASSIFIER_PROMPT
    assert "What is the next department event?" in CLASSIFIER_PROMPT
    assert "Where is the upcoming event being held?" in CLASSIFIER_PROMPT
    assert "Are there any workshops this month?" in CLASSIFIER_PROMPT
    assert "When is the next seminar?" in CLASSIFIER_PROMPT
    print("  ✓ Supervisor classifier contains 'events' category, rules, and example queries.")

    # 3. Test Database Events List Retrieval
    print("\n[Test 3] Department Database Events Retrieval:")
    events = db_service.get_events_list(department=DEPARTMENT_CODE)
    assert len(events) >= 3
    print(f"  ✓ Successfully retrieved {len(events)} department events.")
    for e in events:
        assert "id" in e and "title" in e and "location" in e and "date_time" in e
        print(f"    - [{e['id']}] {e['title']} @ {e['location']}")

    # 4. Test Single Event Retrieval by ID
    print("\n[Test 4] Get Event by ID:")
    first_id = events[0]["id"]
    fetched = db_service.get_event_by_id(first_id)
    assert fetched is not None
    assert fetched["id"] == first_id
    print(f"  ✓ Retrieved single event '{fetched['title']}' by ID: {first_id}")

    # 5. Test Event CRUD Operations
    print("\n[Test 5] Event CRUD Operations:")
    new_payload = {
        "title": "Quantum Computing & Neuromorphic AI Symposium",
        "description": "Exploration of quantum machine learning algorithms and neuromorphic chips.",
        "date_time": "2026-12-05T10:00:00Z",
        "location": "Seminar Hall 1, Tech Complex",
        "organizer": "AIML Research Group",
        "department": DEPARTMENT_CODE,
    }
    created = db_service.create_event(new_payload)
    assert created["title"] == new_payload["title"]
    created_id = created["id"]
    print(f"  ✓ Created event with ID: {created_id}")

    # Update
    updated = db_service.update_event(created_id, {"location": "Auditorium C, Tech Complex"})
    assert updated["location"] == "Auditorium C, Tech Complex"
    print(f"  ✓ Updated event location to: {updated['location']}")

    # Delete
    deleted = db_service.delete_event(created_id)
    assert deleted is True
    print(f"  ✓ Deleted event successfully.")

    # 6. Test Parameter Extraction (Heuristic & Robustness)
    print("\n[Test 6] Parameter Extraction for Required Questions:")
    # Question 1: "What is the next department event?"
    p1 = _heuristic_param_extraction("What is the next department event?")
    assert p1["timeframe"] == "next"
    assert p1["event_type"] == "all"
    print(f"  ✓ 'What is the next department event?' -> timeframe={p1['timeframe']}, type={p1['event_type']}")

    # Question 2: "Are there any workshops this month?"
    p2 = _heuristic_param_extraction("Are there any workshops this month?")
    assert p2["event_type"] == "workshop"
    assert p2["timeframe"] == "this_month"
    print(f"  ✓ 'Are there any workshops this month?' -> type={p2['event_type']}, timeframe={p2['timeframe']}")

    # Question 3: "When is the next seminar?"
    p3 = _heuristic_param_extraction("When is the next seminar?")
    assert p3["event_type"] == "seminar"
    assert p3["timeframe"] == "next"
    assert p3["query_target"] == "date"
    print(f"  ✓ 'When is the next seminar?' -> type={p3['event_type']}, timeframe={p3['timeframe']}, target={p3['query_target']}")

    # Question 4: "Where is the upcoming event being held?"
    p4 = _heuristic_param_extraction("Where is the upcoming event being held?")
    assert p4["query_target"] == "location"
    assert p4["timeframe"] == "next"
    print(f"  ✓ 'Where is the upcoming event being held?' -> target={p4['query_target']}, timeframe={p4['timeframe']}")

    # 7. Test Markdown Formatting & Location Highlighting
    print("\n[Test 7] Event Markdown Formatting & Highlights:")
    test_evt = {
        "title": "Hands-on Workshop: Edge AI with NVIDIA Jetson",
        "description": "Practical training on deploying quantized computer vision models.",
        "date_time": "2026-11-20T10:00:00Z",
        "location": "Robotics & Vision Lab (Lab 402)",
        "organizer": "AIML Robotics Club",
        "department": DEPARTMENT_CODE
    }
    formatted_loc = _format_event_record(test_evt, query_target="location")
    assert "📍" in formatted_loc
    assert "Robotics & Vision Lab (Lab 402)" in formatted_loc
    print("  ✓ Location highlighted appropriately when query asks 'Where'.")

    formatted_date = _format_event_record(test_evt, query_target="date")
    assert "🗓️" in formatted_date
    print("  ✓ Scheduled time highlighted appropriately when query asks 'When'.")

    # 8. Test Datetime Parsing
    print("\n[Test 8] Datetime Parsing:")
    dt = _parse_event_datetime("2026-11-20T10:00:00Z")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 11 and dt.day == 20
    print(f"  ✓ Parsed datetime: {dt.isoformat()}")

    print("\n" + "=" * 65)
    print("ALL 8 EVENT SYSTEM & AGENT TESTS PASSED SUCCESSFULLY! (100%)")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()

