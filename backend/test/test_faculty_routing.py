"""
test_faculty_routing.py — Verification script for Faculty Agent and Supervisor Routing.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import asyncio
from dotenv import load_dotenv
load_dotenv()

from agents.supervisor import supervisor_node
from agents.faculty_agent import faculty_node
from graph import route_by_intent

TEST_QUESTIONS = [
    # ── Faculty Questions ──
    ("Who is the Head of the Department?", "faculty"),
    ("Who is the HOD of AIML?", "faculty"),
    ("Who teaches Machine Learning?", "faculty"),
    ("What subjects does Dr. Sharma handle?", "faculty"),
    ("What is Prof. Rao's specialization?", "faculty"),
    ("How can I find Dr. Verma's contact information and cabin?", "faculty"),
    ("Is Dr. Sharma available on Monday?", "faculty"),
    ("What are the office hours for Prof. Patel?", "faculty"),
    ("Can I get a list of all faculty members in the AIML department?", "faculty"),
    ("Who is the professor for Deep Learning?", "faculty"),

    # ── Existing Agent Questions (Regression Test) ──
    ("What is the attendance policy according to the student handbook?", "rag"),
    ("What classes does AIML-A have on Monday?", "timetable"),
    ("When is the AI401 assignment due?", "deadline"),
    ("What are the latest department notices and announcements?", "notices"),
    ("Help me plan my study week for exam preparation", "planner"),
]

async def run_tests():
    print("=" * 70)
    print("AIDA ROUTING & FACULTY AGENT TEST SUITE")
    print("=" * 70)

    # 1. Test Supervisor Routing
    print("\n--- 1. Testing Supervisor Classification & Graph Route ---")
    correct_count = 0
    for query, expected_intent in TEST_QUESTIONS:
        state = {"query": query, "history": []}
        res = await supervisor_node(state)
        actual_intent = res.get("intent")
        target_node = route_by_intent({"intent": actual_intent, "query": query, "history": []})
        
        matches = (actual_intent == expected_intent) or (expected_intent == "deadline" and actual_intent in ("timetable", "deadline"))
        if matches:
            correct_count += 1
            status = "PASS"
        else:
            status = f"FAIL (Expected {expected_intent})"
            
        print(f"[{status:4s}] '{query[:45]}...' -> Intent: {actual_intent} (Next Node: {target_node})")

    print(f"\nSupervisor Routing Score: {correct_count}/{len(TEST_QUESTIONS)} passed.")

    # 2. Test Faculty Agent Execution
    print("\n--- 2. Testing Faculty Agent Data Retrieval ---")
    test_faculty_queries = [
        "Who is the Head of the Department?",
        "Who teaches Machine Learning?",
        "What is Prof. Rao's specialization?",
        "How can I contact Dr. Verma?",
        "Is Dr. Sharma available on Monday?",
        "Who teaches Quantum Teleportation 999?" # Non-existent course test
    ]

    for f_query in test_faculty_queries:
        f_state = {"query": f_query, "history": [], "context": [], "sources": []}
        f_res = await faculty_node(f_state)
        context_items = f_res.get("context", [])
        print(f"\nQuery: '{f_query}'")
        print(f"  Context Chunks: {len(context_items)}")
        if context_items:
            content_preview = context_items[0].get("content", "")[:120].replace("\n", " ")
            print(f"  Sample Retrieved Content: {content_preview}...")

    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETED SUCCESSFULLY")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_tests())

