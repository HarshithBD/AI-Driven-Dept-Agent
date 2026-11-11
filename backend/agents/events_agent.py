"""
events_agent.py — Event Information Agent for AIDA.

Retrieves structured data from the department database (Supabase / db_service)
covering:
- Next department event
- Workshops and practical sessions (e.g. Edge AI, Jetson)
- Seminars, technical talks, and guest lectures
- Hackathons and coding symposiums
- Event venues, locations, and timings
- Event organizers and department coordinators

Zero hallucination: only official department events on record are retrieved.
"""

from __future__ import annotations

import os
import re
import json
from datetime import datetime, timedelta
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
)

llm = ChatGoogleGenerativeAI(
    model=os.getenv("LLM_MODEL", "gemini-3.8-flash"),
    temperature=0.0,
    max_retries=3,
)

EVENTS_EXTRACT_PROMPT = f"""You are a query parameter extractor for department events, workshops, seminars, and hackathons in the {DEPARTMENT_NAME} ({DEPARTMENT_CODE}) Department.
Extract the relevant query parameters from the user's question and history.
Respond with ONLY a JSON object, no other text.

{{
  "event_type": "<'workshop' | 'seminar' | 'hackathon' | 'talk' | 'all'>",
  "timeframe": "<'next' | 'this_month' | 'upcoming' | 'all'>",
  "query_target": "<'location' | 'date' | 'organizer' | 'details' | 'all'>",
  "topic": "<specific topic keyword like 'Edge AI', 'Jetson', 'Foundation Models', or null>"
}}

Rules:
- "What is the next department event?" -> event_type="all", timeframe="next", query_target="details", topic=null
- "Are there any workshops this month?" -> event_type="workshop", timeframe="this_month", query_target="details", topic=null
- "When is the next seminar?" -> event_type="seminar", timeframe="next", query_target="date", topic=null
- "Where is the upcoming event being held?" -> event_type="all", timeframe="next", query_target="location", topic=null
- If asking specifically about venue, room, or location, set query_target="location".
- If asking specifically when, time, or date, set query_target="date".
- If asking who is organizing or in charge, set query_target="organizer".
"""


async def _extract_event_params(query: str, history: Optional[List[dict]] = None) -> dict:
    """Extract event category, timeframe, topic, and target from natural language using Gemini."""
    messages: list[BaseMessage] = [
        SystemMessage(content=EVENTS_EXTRACT_PROMPT),
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
        print(f"[Event Agent] LLM extraction fallback error: {e}")
        # Deterministic heuristic fallback
        return _heuristic_param_extraction(query)


def _heuristic_param_extraction(query: str) -> dict:
    """Heuristic fallback parser for event queries when LLM is offline or in testing."""
    q = query.lower()

    # Event type
    if "workshop" in q or "hands-on" in q:
        event_type = "workshop"
    elif "seminar" in q or "talk" in q or "lecture" in q:
        event_type = "seminar"
    elif "hackathon" in q or "competition" in q or "contest" in q:
        event_type = "hackathon"
    else:
        event_type = "all"

    # Timeframe
    if "next" in q or "upcoming" in q or "closest" in q:
        timeframe = "next"
    elif "this month" in q or "current month" in q:
        timeframe = "this_month"
    else:
        timeframe = "upcoming"

    # Query target
    if "where" in q or "location" in q or "venue" in q or "room" in q or "hall" in q or "place" in q:
        query_target = "location"
    elif "when" in q or "date" in q or "time" in q:
        query_target = "date"
    elif "who is organizing" in q or "organizer" in q:
        query_target = "organizer"
    else:
        query_target = "details"

    # Topic keyword
    topic = None
    for kw in ["edge ai", "jetson", "foundation models", "generative ai", "multi-agent", "robotics"]:
        if kw in q:
            topic = kw
            break

    return {
        "event_type": event_type,
        "timeframe": timeframe,
        "query_target": query_target,
        "topic": topic,
    }


def _parse_event_datetime(dt_str: str) -> Optional[datetime]:
    """Parse ISO datetime string safely."""
    if not dt_str:
        return None
    try:
        clean_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_str)
    except Exception:
        try:
            return datetime.strptime(dt_str[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return None


def _format_event_record(event: Dict[str, Any], query_target: str = "details") -> str:
    """Format single event into clear structured markdown."""
    title = event.get("title", "Untitled Department Event")
    description = event.get("description", "No description provided.")
    location = event.get("location", "TBD")
    organizer = event.get("organizer", "AIML Department")
    raw_date = event.get("date_time", "")

    dt = _parse_event_datetime(raw_date)
    if dt:
        formatted_dt = dt.strftime("%A, %B %d, %Y at %I:%M %p UTC")
    else:
        formatted_dt = raw_date or "Date TBD"

    lines = [
        f"### {title}",
        f"- **Date & Time:** {formatted_dt}",
        f"- **Location / Venue:** **{location}**",
        f"- **Organizer:** {organizer}",
        f"- **Department:** {DEPARTMENT_NAME} ({DEPARTMENT_CODE})",
        f"- **Description:** {description}",
    ]

    if query_target == "location":
        lines.append(f"\n> 📍 **Venue Location:** This event is taking place at **{location}**.")
    elif query_target == "date":
        lines.append(f"\n> 🗓️ **Scheduled Time:** Marked for **{formatted_dt}**.")
    elif query_target == "organizer":
        lines.append(f"\n> 👥 **Organized by:** Coordinated by **{organizer}**.")

    return "\n".join(lines)


async def events_node(state: GraphState) -> dict:
    """
    Event Specialist Node:
    Extracts event query parameters, queries the department database for events,
    and returns verified event schedule context.
    """
    query = state["query"]
    history = state.get("history", [])
    context = list(state.get("context", []))
    sources = list(state.get("sources", []))

    print(f"[Event Agent] Processing event query: '{query[:60]}...'")

    # 1. Parameter extraction
    params = await _extract_event_params(query, history)
    event_type = params.get("event_type", "all")
    timeframe = params.get("timeframe", "upcoming")
    query_target = params.get("query_target", "details")
    topic = params.get("topic")

    print(f"[Event Agent] Extracted params: type='{event_type}', timeframe='{timeframe}', target='{query_target}', topic='{topic}'")

    # 2. Fetch department events from database
    all_events = db_service.get_events_list(department=DEPARTMENT_CODE, upcoming_only=False)

    # 3. Sort all events chronologically
    now = datetime.utcnow()
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def sort_key(e: Dict[str, Any]) -> str:
        return e.get("date_time", "")

    all_events.sort(key=sort_key)

    # 4. Filter events
    matched_events: List[Dict[str, Any]] = []

    for evt in all_events:
        evt_title = evt.get("title", "").lower()
        evt_desc = evt.get("description", "").lower()
        combined_text = f"{evt_title} {evt_desc}"
        evt_dt_str = evt.get("date_time", "")
        evt_dt = _parse_event_datetime(evt_dt_str)

        # Topic filter
        if topic and topic.lower() not in combined_text:
            continue

        # Event type filter
        if event_type == "workshop" and ("workshop" not in combined_text and "hands-on" not in combined_text):
            continue
        elif event_type == "seminar" and ("seminar" not in combined_text and "talk" not in combined_text and "lecture" not in combined_text):
            continue
        elif event_type == "hackathon" and ("hackathon" not in combined_text and "competition" not in combined_text):
            continue

        # Timeframe filter
        if timeframe in ("next", "upcoming"):
            # Include only future events
            if evt_dt_str < now_iso:
                continue
        elif timeframe == "this_month":
            # Check within next 30 days or same month/year
            if evt_dt:
                in_same_month = (evt_dt.year == now.year and evt_dt.month == now.month)
                in_next_30_days = (now <= evt_dt <= now + timedelta(days=31))
                if not (in_same_month or in_next_30_days):
                    continue
            else:
                if evt_dt_str < now_iso:
                    continue

        matched_events.append(evt)

    # If "next" timeframe requested, choose the single earliest upcoming event (or first matched)
    if timeframe == "next" and matched_events:
        matched_events = [matched_events[0]]

    # Fallback if specific upcoming filter found none, but upcoming was requested and events exist
    if not matched_events and timeframe == "next" and all_events:
        # If no future events exist in database, return the next scheduled entry
        future_candidates = [e for e in all_events if e.get("date_time", "") >= now_iso]
        if future_candidates:
            matched_events = [future_candidates[0]]
        else:
            matched_events = [all_events[-1]]

    # 5. Assemble context output
    if matched_events:
        formatted_blocks = [_format_event_record(e, query_target) for e in matched_events]
        content_str = "\n\n---\n\n".join(formatted_blocks)
        context.append({
            "tool": "get_events_info",
            "source": f"{DEPARTMENT_CODE} Event Calendar",
            "content": content_str,
        })
        sources.append({
            "doc": f"{DEPARTMENT_NAME} Event Calendar",
            "page": "Department Events Database",
        })
        print(f"[Event Agent] Found {len(matched_events)} matching event records.")
    else:
        # Informative empty state
        search_desc = f"{event_type} events" if event_type != "all" else "events"
        if topic:
            search_desc += f" on '{topic}'"
        no_info_msg = (
            f"No scheduled {search_desc} were found in the {DEPARTMENT_NAME} ({DEPARTMENT_CODE}) database. "
            f"Please check the department notice board or consult the AIML Student Chapter for upcoming event registrations."
        )
        context.append({
            "tool": "get_events_info",
            "source": f"{DEPARTMENT_CODE} Event Calendar",
            "content": no_info_msg,
        })
        print(f"[Event Agent] No matching events found for query.")

    return {"context": context, "sources": sources}

