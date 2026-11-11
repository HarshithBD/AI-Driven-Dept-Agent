"""
supervisor.py — Supervisor Agent for intent classification.

Uses Gemini to classify the user's query into one of:
  - "rag"       → document/policy questions (search FAISS index)
  - "timetable" → class schedule questions
  - "deadline"  → assignment/exam deadline questions
  - "planner"   → study plan / schedule planning requests
  - "notices"   → department announcements / news
  - "faculty"   → faculty directory, HOD, course instructors, contact & office hours
  - "general"   → greetings, off-topic, or general conversation
"""

from __future__ import annotations

import os
from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
from agents.state import GraphState
from department_config import (
    DEPARTMENT_CODE,
    DEPARTMENT_NAME,
    STUDENT_SECTIONS,
    SECTION_TOKENS as DEPT_SECTION_TOKENS,
    SECTIONS_TEXT,
)

# Use the same Gemini model as the rest of the app
llm = ChatGoogleGenerativeAI(
    model=os.getenv("LLM_MODEL", "gemini-3.8-flash"),
    temperature=0.0,
    max_retries=3,
)

CLASSIFIER_PROMPT = f"""You are an intent classifier for AIDA – AI-Driven Department Agent, an intelligent assistant for the {DEPARTMENT_NAME} ({DEPARTMENT_CODE}) Department.

Given a student's question AND the conversation history, classify it into EXACTLY ONE of these categories:

- "rag" — Questions about university and department policies, rules, regulations, handbooks, lab manuals, project guidelines, academic policies, campus facilities, department info, academic calendar, and holidays. Anything that would be found in official department or university PDF documents.
- "timetable" — Questions about class schedules, lecture timings, rooms, what classes are on a specific day. Anything about the weekly timetable grid.
- "deadline" — Questions about assignment due dates, exam dates, project submissions, upcoming deadlines.
- "planner" — Requests to create a study plan, organize a week, plan exam preparation, or combine schedule + academic info into a plan.
- "notices" — Questions about department/campus official circulars, notice board announcements, administrative memos, campus maintenance, or administrative updates from management.
- "events" — Questions about department events, upcoming workshops, seminars, guest lectures, hackathons, symposiums, technical talks, event schedules, event dates, venues/locations (e.g., "Where is the upcoming event being held?"), organizers, or "What is the next department event?".
- "faculty" — Questions about professors, instructors, department faculty members, Head of Department (HOD), who teaches a specific subject (e.g., "Who teaches Machine Learning?"), what subjects a professor handles, faculty specializations, faculty email/cabin office contact info, and professor availability or office consultation hours.
- "requests" — Questions about student administrative requests, petitions, or applications (e.g., applying for a Bonafide Certificate, requesting Leave of Absence, On-Duty / OD attendance permission, Capstone Project Guide allocation, Lab Compute / GPU access, Course Exemptions), how the student request workflow operates, how to draft a request, required documentation for requests, whether AI can approve requests, or how to track submitted request statuses.
- "general" — Greetings (hi, hello), thanks, off-topic questions, or anything that doesn't fit the above categories.

IMPORTANT RULES:
1. Respond with ONLY the category label (one word), nothing else.
2. If a query mentions both schedule AND deadlines, classify as "planner".
3. If a query asks about a course's content/syllabus, classify as "rag" (it's in the handbook).
4. If a query asks about a course's timing/room in the weekly schedule, classify as "timetable".
5. "When is X due?" or "What are the deadlines?" → "deadline"
6. "What classes do I have on Monday?" → "timetable"
7. "What is the attendance policy?" → "rag"
8. "What dates are in the academic calendar?" or "When are the holidays?" → "rag"
9. CRITICAL: If the previous assistant message asked "Which section are you in — {SECTIONS_TEXT}?", then the user's reply (even if it's just "{STUDENT_SECTIONS[0].lower()}", "{STUDENT_SECTIONS[-1]}", "section a", "A") is ALWAYS "timetable".
10. CRITICAL: Short follow-up messages like "{STUDENT_SECTIONS[0].lower()}", "monday", "tuesday" should inherit the intent from the conversation history, not be classified as "general".
11. "Who is the Head of the Department?" or "Who is the HOD?" → "faculty"
12. "Who teaches [Subject]?" or "Who is the professor for [Subject]?" → "faculty"
13. Questions asking about a professor's contact, email, office, cabin, specialization, subjects, or office hours/availability → "faculty"
14. "What is the next department event?" or "Tell me about upcoming events" → "events"
15. Questions about workshops, seminars, guest lectures, hackathons, or event dates/locations → "events"
16. Questions about submitting student requests (bonafide certificates, medical/casual leave, on-duty/OD permissions, guide change, GPU quota, course exemptions) or checking request status → "requests"
17. If a user asks "Can you approve my leave?", "Approve my request", or "Help me draft a request for X" → "requests"

Examples:
- "What is the attendance policy?" → rag
- "Tell me about lab guidelines" → rag
- "What classes does {STUDENT_SECTIONS[0]} have on Monday?" → timetable
- "When is the AI401 assignment due?" → deadline
- "What are the upcoming deadlines?" → deadline
- "Help me plan my study week" → planner
- "How should I prepare for mid-semester exams?" → planner
- "What are the latest announcements?" → notices
- "What is the next department event?" → events
- "Are there any workshops this month?" → events
- "When is the next seminar?" → events
- "Where is the upcoming event being held?" → events
- "Tell me about the Edge AI workshop" → events
- "Who is organizing the AIML Hackathon?" → events
- "Who is the Head of the Department?" → faculty
- "Who is the HOD?" → faculty
- "Who teaches Machine Learning?" → faculty
- "What subjects does Dr. Sharma handle?" → faculty
- "What is Prof. Rao's specialization?" → faculty
- "How can I contact Dr. Verma?" → faculty
- "Where is Dr. Verma's office?" → faculty
- "Is Dr. Sharma available on Monday?" → faculty
- "List all faculty members in AIML" → faculty
- "How do I apply for a Bonafide Certificate?" → requests
- "Can you approve my leave of absence?" → requests
- "How do I submit an OD request for an external hackathon?" → requests
- "What documents are needed for medical leave?" → requests
- "Help me write a description for GPU cluster compute access" → requests
- "How can I check the status of my request?" → requests
- "What is the process to request a project guide change?" → requests
- "Hello!" → general
- "Thanks for the help" → general
- "{STUDENT_SECTIONS[0].lower()}" (after the bot asked which section) → timetable
- "{STUDENT_SECTIONS[-1]}" (after the bot asked which section) → timetable
"""


# Keywords that signal the assistant just asked which section the student is in
_SECTION_CLARIFICATION_PHRASES = [
    "which section are you in",
    "section are you in",
    SECTIONS_TEXT.lower(),
    "cs-a or cs-b",
]

# Short tokens that a user sends as a section reply (includes dynamic department sections + fallback tokens)
_SECTION_TOKENS = set(DEPT_SECTION_TOKENS).union(
    {"cs-a", "cs-b", "csa", "csb", "section a", "section b", "group a", "group b", "a", "b"}
)


def _last_assistant_asked_for_section(history: list[dict]) -> bool:
    """Return True if the most recent assistant message asked for section clarification."""
    for msg in reversed(history):
        if msg.get("role") == "assistant":
            content = msg.get("content", "").lower()
            return any(phrase in content for phrase in _SECTION_CLARIFICATION_PHRASES)
    return False


async def supervisor_node(state: GraphState) -> dict:
    """
    Classify the user's intent using Gemini.

    Includes a deterministic pre-check: if the assistant's last message asked
    for the student's section and the current message is a section reply,
    always route to 'timetable' without an LLM call.

    Returns:
        Updated state with 'intent' field set.
    """
    query = state["query"]
    history = state.get("history", [])

    # ── DETERMINISTIC PRE-CHECK ──────────────────────────────────────────────
    # If the bot just asked for section clarification and the reply looks like a section
    # answer, skip the LLM completely.
    query_lower = query.strip().lower()
    if _last_assistant_asked_for_section(history) and query_lower in _SECTION_TOKENS:
        print(f"[Supervisor] Section follow-up detected ('{query}') -> Intent: timetable")
        return {"intent": "timetable"}

    # ── LLM CLASSIFICATION ───────────────────────────────────────────────────
    messages: list[BaseMessage] = [
        SystemMessage(content=CLASSIFIER_PROMPT),
    ]

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=f"Classify this query: \"{query}\""))

    response = await llm.ainvoke(messages)
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_content = " ".join([b.get("text", "") if isinstance(b, dict) else b for b in raw_content])
    elif not isinstance(raw_content, str):
        raw_content = str(raw_content)  # type: ignore
    intent = raw_content.strip().lower().strip('"').strip("'")

    # Validate — fall back to "general" if Gemini returns something unexpected
    valid_intents = {"rag", "timetable", "deadline", "planner", "notices", "faculty", "events", "requests", "general"}
    if intent not in valid_intents:
        print(f"[Supervisor] Unexpected intent '{intent}', defaulting to 'general'")
        intent = "general"

    print(f"[Supervisor] Query: '{query[:60]}...' -> Intent: {intent}")

    return {"intent": intent}
