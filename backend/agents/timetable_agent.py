"""
timetable_agent.py — Timetable Agent for schedule and deadline questions.

Uses Gemini to extract parameters (day, group, course_id) from natural language,
then calls the Timetable MCP Server via mcp_client.
"""

from __future__ import annotations

import os
import json
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agents.state import GraphState
import mcp_client
from department_config import (
    STUDENT_SECTIONS,
    DEPARTMENT_COURSES,
    COURSE_ALIAS_MAP,
    SECTIONS_TEXT,
    DEPARTMENT_CODE,
)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("LLM_MODEL", "gemini-3.8-flash"),
    temperature=0.0,
    max_retries=3,
)

# ==================== TIMETABLE PARAMETER EXTRACTION ====================

_sections_joined = " or ".join(STUDENT_SECTIONS)
_course_mappings_str = "\n".join([
    f"  - {c['name']} / {' / '.join(c['aliases'])} → {c['id']}"
    for c in DEPARTMENT_COURSES
])

TIMETABLE_EXTRACT_PROMPT = f"""Extract the following from the user's question about a class timetable in the {DEPARTMENT_CODE} Department.
Respond with ONLY a JSON object, no other text.

{{
  "day": "<day of week or null>",
  "student_group": "<{_sections_joined} or null>"
}}

Rules:
- day must be one of: Monday, Tuesday, Wednesday, Thursday, Friday, or null if not specified.
- student_group must be one of: {', '.join(STUDENT_SECTIONS)}, or null if not specified.
- If the user says "today", resolve it to the actual day based on the conversation or leave null.
- IMPORTANT: If the user's message or ANY previous message in the conversation history mentions {', '.join(STUDENT_SECTIONS)} or Section A/B, you MUST extract that as the student_group.
- If the user asks a follow-up question, use the conversation history to fill in the missing fields.
"""

# ==================== DEADLINE PARAMETER EXTRACTION ====================

DEADLINE_EXTRACT_PROMPT = f"""Extract the course ID from the user's question about deadlines in the {DEPARTMENT_CODE} Department.
Respond with ONLY a JSON object, no other text.

{{
  "course_id": "<course code like {DEPARTMENT_COURSES[0]['id']} or null>"
}}

Rules:
- course_id should be in format like {DEPARTMENT_COURSES[0]['id']}, etc.
- If the user mentions a course name, map it to the ID:
{_course_mappings_str}
- If no specific course is mentioned, use null (returns all deadlines).
"""


async def _extract_timetable_params(query: str, history: list[dict] | None = None) -> dict:
    """Use Gemini to extract day and student_group from query."""
    messages: list[BaseMessage] = [
        SystemMessage(content=TIMETABLE_EXTRACT_PROMPT),
    ]
    if history:
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
                
    messages.append(HumanMessage(content=query))
    response = await llm.ainvoke(messages)
    try:
        text = response.content
        if isinstance(text, list):
            text = " ".join([b.get("text", "") if isinstance(b, dict) else b for b in text])
        elif not isinstance(text, str):
            text = str(text)  # type: ignore
        text = text.strip()
        # Find the first { and last } to extract JSON
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            return json.loads(json_str)
        return {"day": None, "student_group": None}
    except (json.JSONDecodeError, IndexError):
        print(f"[Timetable Agent] Failed to parse params: {response.content}")
        return {"day": None, "student_group": None}


async def _extract_deadline_params(query: str, history: list[dict] | None = None) -> dict:
    """Use Gemini to extract course_id from query."""
    messages: list[BaseMessage] = [
        SystemMessage(content=DEADLINE_EXTRACT_PROMPT),
    ]
    if history:
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
                
    messages.append(HumanMessage(content=query))
    response = await llm.ainvoke(messages)
    try:
        text = response.content
        if isinstance(text, list):
            text = " ".join([b.get("text", "") if isinstance(b, dict) else b for b in text])
        elif not isinstance(text, str):
            text = str(text)  # type: ignore
        text = text.strip()
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx != -1 and end_idx != -1:
            json_str = text[start_idx:end_idx+1]
            return json.loads(json_str)
        return {"course_id": None}
    except (json.JSONDecodeError, IndexError):
        print(f"[Timetable Agent] Failed to parse deadline params: {response.content}")
        return {"course_id": None}


async def timetable_node(state: GraphState) -> dict:
    """
    Handle timetable and deadline queries via Timetable MCP Server.

    For intent "timetable": extracts day + group → calls get_timetable()
    For intent "deadline": extracts course_id → calls get_deadlines()

    If student_group is unknown, sets a clarification context block
    so the response writer asks the user to specify their group.

    Returns:
        Updated state with 'context' and 'sources' populated.
    """
    query = state["query"]
    intent = state["intent"]
    context = list(state.get("context", []))
    sources = list(state.get("sources", []))

    try:
        if intent == "deadline":
            # ===== DEADLINE PATH =====
            params = await _extract_deadline_params(query, state.get("history", []))
            course_id = params.get("course_id")

            print(f"[Timetable Agent] Getting deadlines (course_id={course_id})")

            result_str = await mcp_client.get_deadlines(course_id or None)
            context.append({
                "tool": "get_deadlines",
                "course_id": course_id,
                "content": result_str,
            })
            sources.append({"doc": "Timetable API (Deadlines)", "page": "Live Data"})

        else:
            # ===== TIMETABLE PATH =====
            params = await _extract_timetable_params(query, state.get("history", []))
            day = params.get("day")       # May be None → will ask clarification
            group = params.get("student_group")  # May be None → MUST ask clarification

            print(f"[Timetable Agent] Extracted params: day={day}, group={group}")

            # --- CLARIFICATION GATE ---
            # If group is missing we CANNOT look up the schedule — ask the user.
            if not group:
                clarification_day = f" on {day}" if day else ""
                context.append({
                    "tool": "clarification_needed",
                    "content": (
                        f"The user asked about their lectures{clarification_day} but did not specify which class section they are in. "
                        f"Ask the user: 'Which section are you in — {SECTIONS_TEXT}?' "
                        "Do NOT attempt to answer the timetable question until the section is confirmed."
                    ),
                })
                return {"context": context, "sources": sources}

            # If day is still missing, default to a reasonable fallback
            if not day:
                day = "Monday"
                print("[Timetable Agent] Day not specified, defaulting to Monday.")

            print(f"[Timetable Agent] Getting timetable (day={day}, group={group})")

            result_str = await mcp_client.get_timetable(day, group)
            context.append({
                "tool": "get_timetable",
                "day": day,
                "student_group": group,
                "content": result_str,
            })
            sources.append({"doc": f"Timetable API ({day})", "page": "Live Data"})

    except Exception as e:
        print(f"[Timetable Agent] Error: {e}")
        context.append({
            "tool": "timetable_error",
            "content": f"Failed to fetch timetable data: {str(e)}",
        })

    return {"context": context, "sources": sources}
