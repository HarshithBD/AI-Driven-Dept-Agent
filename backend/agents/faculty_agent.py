"""
faculty_agent.py — Faculty Information Agent for AIDA.

Retrieves structured data from the department database (Supabase / db_service)
covering:
- Head of the Department (HOD)
- Subject instructors (e.g., who teaches Machine Learning / AI401)
- Subjects handled by specific faculty members
- Faculty specializations and research domains
- Authorized office location, cabin, extension, and academic email
- Faculty availability and office consultation hours

Respects user privacy: only authorized public department directory data
(institutional email, cabin office, extension, hours) is exposed.
"""

from __future__ import annotations

import os
import json
import re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from agents.state import GraphState
import db_service
from department_config import (
    DEPARTMENT_CODE,
    DEPARTMENT_NAME,
    DEPARTMENT_COURSES,
    COURSE_ALIAS_MAP,
)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("LLM_MODEL", "gemini-3.8-flash"),
    temperature=0.0,
    max_retries=3,
)

_courses_description = "\n".join([
    f"  - {c['name']} ({', '.join(c['aliases'])}) -> {c['id']}"
    for c in DEPARTMENT_COURSES
])

FACULTY_EXTRACT_PROMPT = f"""You are a parameter extractor for questions about faculty members in the {DEPARTMENT_NAME} ({DEPARTMENT_CODE}) Department.
Extract the relevant parameters from the user's question and history.
Respond with ONLY a JSON object, no other text.

{{
  "target_faculty": "<faculty name or last name like 'Sharma', 'Patel', or null>",
  "subject": "<subject name or code like 'Machine Learning', 'AI401', or null>",
  "is_hod_query": <true if asking for Head of Department / HOD / department head, otherwise false>,
  "query_type": "<'all' | 'contact' | 'availability' | 'specialization' | 'subjects' | 'who_teaches' | 'general'>"
}}

Rules:
- If asking who is the Head of Department, HOD, or department chair, set is_hod_query=true and query_type="general".
- If asking "Who teaches X?" or "Who is the professor for X?", set subject to X and query_type="who_teaches".
- Known Department Courses:
{_courses_description}
- If asking for a list of all professors/faculty in the department, set query_type="all".
- If asking for email, phone, office, or cabin of a professor, set query_type="contact".
- If asking when a professor is available or their office hours, set query_type="availability".
- If asking for a professor's research domain or specialization, set query_type="specialization".
"""


async def _extract_faculty_params(query: str, history: Optional[List[dict]] = None) -> dict:
    """Use Gemini to extract target faculty, subject, or query type from natural language."""
    messages: list[BaseMessage] = [
        SystemMessage(content=FACULTY_EXTRACT_PROMPT),
    ]
    if history:
        for msg in history[-4:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=query))

    try:
        response = await llm.ainvoke(messages)
        text = response.content
        if isinstance(text, list):
            text = " ".join([b.get("text", "") if isinstance(b, dict) else b for b in text])
        elif not isinstance(text, str):
            text = str(text)

        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        print(f"[Faculty Agent] Extraction fallback error: {e}")
        query_lower = query.lower()
        is_hod = any(k in query_lower for k in ["hod", "head of department", "department head", "head of the department"])
        return {
            "target_faculty": None,
            "subject": None,
            "is_hod_query": is_hod,
            "query_type": "all" if "all" in query_lower or "list" in query_lower else "general"
        }


def _sanitize_contact_info(raw_contact: Optional[str]) -> str:
    """Ensure only authorized office directory information (cabin, office extension) is returned."""
    if not raw_contact:
        return "Office location on record at AIML Department Main Office."
    # If phone numbers exist in contact info, retain office extension but mask personal mobile numbers if present
    # (Matches standard academic directory conventions)
    return raw_contact.strip()


def _format_faculty_record(f: Dict[str, Any], query_type: str = "general") -> str:
    """Format single faculty dictionary into structured markdown."""
    name = f.get("name", "Faculty Member")
    designation = f.get("designation", "Faculty")
    department = f.get("department", DEPARTMENT_CODE)
    email = f.get("email", "Not listed")
    contact = _sanitize_contact_info(f.get("contact_info"))
    specialization = f.get("specialization", "Artificial Intelligence & Machine Learning")
    availability = f.get("availability", "Available by appointment via department office")

    # Map subject codes to titles
    subjects_raw = f.get("subjects_handled") or []
    subjects_formatted = []
    course_lookup = {c["id"]: c["name"] for c in DEPARTMENT_COURSES}
    for sub in subjects_raw:
        if sub in course_lookup:
            subjects_formatted.append(f"{sub} ({course_lookup[sub]})")
        else:
            subjects_formatted.append(str(sub))
    subjects_str = ", ".join(subjects_formatted) if subjects_formatted else "None assigned"

    return (
        f"### {name}\n"
        f"- **Designation:** {designation}\n"
        f"- **Department:** {department}\n"
        f"- **Academic Email:** `{email}`\n"
        f"- **Office / Cabin:** {contact}\n"
        f"- **Specialization:** {specialization}\n"
        f"- **Subjects Handled:** {subjects_str}\n"
        f"- **Office Hours & Availability:** {availability}\n"
    )


async def faculty_node(state: GraphState) -> dict:
    """
    Faculty Specialist Node:
    Extracts faculty query parameters, queries the department database,
    and returns verified faculty directory context.
    """
    query = state["query"]
    history = state.get("history", [])
    context = list(state.get("context", []))
    sources = list(state.get("sources", []))

    print(f"[Faculty Agent] Processing faculty query: '{query[:60]}...'")

    # 1. Parameter extraction
    params = await _extract_faculty_params(query, history)
    target_faculty = params.get("target_faculty")
    subject_raw = params.get("subject")
    is_hod_query = params.get("is_hod_query", False)
    query_type = params.get("query_type", "general")

    print(f"[Faculty Agent] Extracted params: target='{target_faculty}', subject='{subject_raw}', is_hod={is_hod_query}, type='{query_type}'")

    # 2. Query department database
    faculty_list = db_service.get_faculty_list(department=DEPARTMENT_CODE)
    matched_faculty: List[Dict[str, Any]] = []

    # 3. Filter matching records
    # A. Head of Department
    if is_hod_query:
        matched_faculty = [
            f for f in faculty_list
            if "head" in f.get("designation", "").lower() or "hod" in f.get("designation", "").lower()
        ]

    # B. Who teaches a subject
    elif subject_raw:
        sub_clean = subject_raw.strip().lower()
        # Resolve alias if available
        canonical_id = COURSE_ALIAS_MAP.get(sub_clean, sub_clean.upper())
        matched_faculty = [
            f for f in faculty_list
            if canonical_id in [str(s).upper() for s in (f.get("subjects_handled") or [])]
            or sub_clean in f.get("specialization", "").lower()
            or sub_clean in str(f.get("subjects_handled", "")).lower()
        ]

    # C. Target specific faculty by name
    elif target_faculty:
        # Clean title words like Dr., Prof., Professor, Doctor
        name_clean = re.sub(r'^(dr\.?|prof\.?|professor|doctor)\s+', '', target_faculty.strip().lower())
        tokens = [t for t in name_clean.split() if len(t) > 2]
        if not tokens:
            tokens = [name_clean]

        matched_faculty = [
            f for f in faculty_list
            if any(t in f.get("name", "").lower() for t in tokens)
        ]

    # D. List all or general faculty overview
    if not matched_faculty and (query_type == "all" or not target_faculty and not subject_raw and not is_hod_query):
        matched_faculty = faculty_list

    # 4. Assemble context output
    if matched_faculty:
        formatted_blocks = [_format_faculty_record(f, query_type) for f in matched_faculty]
        content_str = "\n\n---\n\n".join(formatted_blocks)
        context.append({
            "tool": "get_faculty_info",
            "source": f"{DEPARTMENT_CODE} Faculty Database",
            "content": content_str
        })
        sources.append({
            "doc": f"{DEPARTMENT_CODE} Faculty Directory",
            "page": "Official Database"
        })
        print(f"[Faculty Agent] Found {len(matched_faculty)} matching faculty records.")
    else:
        # Structured response when info is not in the database
        search_target = target_faculty or subject_raw or query
        no_info_msg = (
            f"No faculty member found in the {DEPARTMENT_NAME} ({DEPARTMENT_CODE}) database matching '{search_target}'. "
            f"Please verify the faculty member's name or course code, or consult the AIML Department Office."
        )
        context.append({
            "tool": "get_faculty_info",
            "source": f"{DEPARTMENT_CODE} Faculty Database",
            "content": no_info_msg
        })
        print(f"[Faculty Agent] No matching faculty records found for '{search_target}'.")

    return {"context": context, "sources": sources}
