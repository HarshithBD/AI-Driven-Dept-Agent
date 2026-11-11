"""
test_events_agent_unit.py — Unit tests for Event Agent parameter extraction,
event database integration, and LangGraph routing.
Does not require external network access or paid LLM API keys.
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

from department_config import DEPARTMENT_CODE, DEPARTMENT_NAME
import db_service
from agents.events_agent import (
    _heuristic_param_extraction,
    _format_event_record,
    _parse_event_datetime
)
from graph import route_by_intent
from agents.supervisor import CLASSIFIER_PROMPT


def test_graph_routing():
    """Test 1: LangGraph Routing by Intent."""
    assert route_by_intent({"intent": "events"}) == "events_agent"
    assert route_by_intent({"intent": "faculty"}) == "faculty_agent"
    assert route_by_intent({"intent": "rag"}) == "rag_agent"
    assert route_by_intent({"intent": "timetable"}) == "timetable_agent"
    assert route_by_intent({"intent": "deadline"}) == "timetable_agent"
    assert route_by_intent({"intent": "notices"}) == "notices_agent"
    assert route_by_intent({"intent": "planner"}) == "planner_agent"
    assert route_by_intent({"intent": "general"}) == "response_writer"


def test_supervisor_prompt_structure():
    """Test 2: Supervisor Prompt Structure for Events."""
    assert '"events"' in CLASSIFIER_PROMPT
    assert "What is the next department event?" in CLASSIFIER_PROMPT
    assert "Where is the upcoming event being held?" in CLASSIFIER_PROMPT
    assert "Are there any workshops this month?" in CLASSIFIER_PROMPT
    assert "When is the next seminar?" in CLASSIFIER_PROMPT


def test_events_list_retrieval():
    """Test 3: Department Database Events Retrieval."""
    events = db_service.get_events_list(department=DEPARTMENT_CODE)
    assert len(events) >= 3
    for e in events:
        assert "id" in e and "title" in e and "location" in e and "date_time" in e


def test_get_event_by_id():
    """Test 4: Get Event by ID."""
    events = db_service.get_events_list(department=DEPARTMENT_CODE)
    first_id = events[0]["id"]
    fetched = db_service.get_event_by_id(first_id)
    assert fetched is not None
    assert fetched["id"] == first_id


def test_event_crud():
    """Test 5: Event CRUD Operations."""
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

    updated = db_service.update_event(created_id, {"location": "Auditorium C, Tech Complex"})
    assert updated["location"] == "Auditorium C, Tech Complex"

    deleted = db_service.delete_event(created_id)
    assert deleted is True


def test_heuristic_param_extraction():
    """Test 6: Parameter Extraction for Required Questions."""
    p1 = _heuristic_param_extraction("What is the next department event?")
    assert p1["timeframe"] == "next"
    assert p1["event_type"] == "all"

    p2 = _heuristic_param_extraction("Are there any workshops this month?")
    assert p2["event_type"] == "workshop"
    assert p2["timeframe"] == "this_month"

    p3 = _heuristic_param_extraction("When is the next seminar?")
    assert p3["event_type"] == "seminar"
    assert p3["timeframe"] == "next"
    assert p3["query_target"] == "date"

    p4 = _heuristic_param_extraction("Where is the upcoming event being held?")
    assert p4["query_target"] == "location"
    assert p4["timeframe"] == "next"


def test_event_markdown_formatting():
    """Test 7: Event Markdown Formatting & Highlights."""
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

    formatted_date = _format_event_record(test_evt, query_target="date")
    assert "🗓️" in formatted_date


def test_datetime_parsing():
    """Test 8: Datetime Parsing."""
    dt = _parse_event_datetime("2026-11-20T10:00:00Z")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 11 and dt.day == 20


# ── Keep backward-compatible run_tests() for direct script execution ──────────
def run_tests():
    test_graph_routing()
    test_supervisor_prompt_structure()
    test_events_list_retrieval()
    test_get_event_by_id()
    test_event_crud()
    test_heuristic_param_extraction()
    test_event_markdown_formatting()
    test_datetime_parsing()
    print("ALL 8 EVENT SYSTEM & AGENT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()

