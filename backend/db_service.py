"""
db_service.py — Department Database Service Layer for AIDA.

Provides clean, modular CRUD operations for department entities:
1. Faculty
2. Students
3. Subjects
4. Timetable
5. Notices
6. Events
7. Academic Documents
8. Student Requests (Human Approval Workflow)

Uses the Supabase REST API (PostgREST) with service-role authentication,
matching the established backend architecture in main.py.
Includes graceful fallbacks to department_config and local files when Supabase
tables are being initialized.
"""

import os
import json
import uuid
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from department_config import (
    DEPARTMENT_CODE,
    DEPARTMENT_NAME,
    DEPARTMENT_COURSES,
    DEPARTMENT_LABS,
    STUDENT_SECTIONS,
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
if SUPABASE_URL.endswith("/rest/v1"):
    SUPABASE_URL = SUPABASE_URL[:-len("/rest/v1")].rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

def _is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


# ==============================================================================
# 1. FACULTY SERVICE
# ==============================================================================

_IN_MEMORY_FACULTY: Optional[List[Dict[str, Any]]] = None

def _get_in_memory_faculty(department: str = DEPARTMENT_CODE) -> List[Dict[str, Any]]:
    """Initialize or return in-memory faculty records."""
    global _IN_MEMORY_FACULTY
    if _IN_MEMORY_FACULTY is None:
        _IN_MEMORY_FACULTY = [
            {
                "id": "fac-001",
                "name": "Dr. A. Sharma",
                "designation": "Professor & Head of Department",
                "department": department,
                "email": "hod.aiml@greenfield.edu",
                "contact_info": "Cabin 401, AIML Block • Ext 4101",
                "specialization": "Machine Learning, Deep Learning, Predictive Modeling",
                "subjects_handled": ["AI401", "AI402"],
                "availability": "Mon & Wed: 2:00 PM - 4:00 PM",
                "is_active": True
            },
            {
                "id": "fac-002",
                "name": "Prof. K. Patel",
                "designation": "Associate Professor",
                "department": department,
                "email": "k.patel@greenfield.edu",
                "contact_info": "Cabin 402, AIML Block • Ext 4102",
                "specialization": "Neural Architectures, GPU Computing, Optimization",
                "subjects_handled": ["AI402"],
                "availability": "Tue & Thu: 11:00 AM - 1:00 PM",
                "is_active": True
            },
            {
                "id": "fac-003",
                "name": "Dr. R. Verma",
                "designation": "Assistant Professor",
                "department": department,
                "email": "r.verma@greenfield.edu",
                "contact_info": "Cabin 403, AIML Block • Ext 4103",
                "specialization": "Natural Language Processing, LLMs, Conversational AI",
                "subjects_handled": ["AI403"],
                "availability": "Daily: 3:00 PM - 4:30 PM",
                "is_active": True
            },
            {
                "id": "fac-004",
                "name": "Prof. S. Rao",
                "designation": "Assistant Professor",
                "department": department,
                "email": "s.rao@greenfield.edu",
                "contact_info": "Cabin 404, AIML Block • Ext 4104",
                "specialization": "Computer Vision, Edge AI, Autonomous Systems",
                "subjects_handled": ["AI404"],
                "availability": "Mon & Fri: 10:00 AM - 12:00 PM",
                "is_active": True
            },
            {
                "id": "fac-005",
                "name": "Dr. M. Gupta",
                "designation": "Assistant Professor",
                "department": department,
                "email": "m.gupta@greenfield.edu",
                "contact_info": "Cabin 405, AIML Block • Ext 4105",
                "specialization": "Reinforcement Learning, Robotics, Control Theory",
                "subjects_handled": ["AI405"],
                "availability": "Wed & Thu: 2:00 PM - 3:30 PM",
                "is_active": True
            },
            {
                "id": "fac-006",
                "name": "Prof. N. Iyer",
                "designation": "Visiting Professor",
                "department": department,
                "email": "n.iyer@greenfield.edu",
                "contact_info": "Cabin 406, AIML Block • Ext 4106",
                "specialization": "AI Ethics, Governance, Responsible AI, Data Policy",
                "subjects_handled": ["AI406"],
                "availability": "Friday: 2:00 PM - 5:00 PM",
                "is_active": True
            }
        ]
    return _IN_MEMORY_FACULTY

def get_faculty_list(department: str = DEPARTMENT_CODE) -> List[Dict[str, Any]]:
    """Fetch active faculty directory for a department."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/faculty?select=*&department=eq.{department}&is_active=eq.true&order=name.asc"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[DB Service] Error fetching faculty: {e}")

    # Fallback to in-memory faculty
    return [f for f in _get_in_memory_faculty(department) if f.get("is_active", True)]

def create_faculty(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new faculty record."""
    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    new_faculty = {
        "id": data.get("id") or f"fac-{uuid.uuid4().hex[:6]}",
        "name": data.get("name", "Faculty Member"),
        "designation": data.get("designation", "Assistant Professor"),
        "department": data.get("department", DEPARTMENT_CODE),
        "email": data.get("email", ""),
        "contact_info": data.get("contact_info", "Cabin 400, AIML Block"),
        "specialization": data.get("specialization", "Artificial Intelligence"),
        "subjects_handled": data.get("subjects_handled", []),
        "availability": data.get("availability", "By Appointment"),
        "is_active": data.get("is_active", True),
        "created_at": now_str,
        "updated_at": now_str
    }

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/faculty"
            resp = requests.post(url, headers=_HEADERS, json=new_faculty, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else new_faculty
        except Exception as e:
            print(f"[DB Service] Error creating faculty in Supabase: {e}")

    fac_list = _get_in_memory_faculty()
    fac_list.append(new_faculty)
    return new_faculty

def update_faculty(faculty_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing faculty record."""
    data["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/faculty?id=eq.{faculty_id}"
            resp = requests.patch(url, headers=_HEADERS, json=data, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else {"id": faculty_id, **data}
        except Exception as e:
            print(f"[DB Service] Error updating faculty in Supabase: {e}")

    for f in _get_in_memory_faculty():
        if str(f.get("id")) == str(faculty_id):
            f.update(data)
            return f
    return {"id": faculty_id, **data}

def delete_faculty(faculty_id: str) -> bool:
    """Soft-delete or remove a faculty record."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/faculty?id=eq.{faculty_id}"
            resp = requests.delete(url, headers=_HEADERS, timeout=5)
            if resp.status_code in (200, 204):
                return True
        except Exception as e:
            print(f"[DB Service] Error deleting faculty in Supabase: {e}")

    fac_list = _get_in_memory_faculty()
    before = len(fac_list)
    fac_list[:] = [f for f in fac_list if str(f.get("id")) != str(faculty_id)]
    return len(fac_list) < before


# ==============================================================================
# 2. STUDENTS SERVICE
# ==============================================================================

_IN_MEMORY_STUDENTS: Optional[List[Dict[str, Any]]] = None

def _get_in_memory_students(department: str = DEPARTMENT_CODE) -> List[Dict[str, Any]]:
    """Initialize or return in-memory student records."""
    global _IN_MEMORY_STUDENTS
    if _IN_MEMORY_STUDENTS is None:
        _IN_MEMORY_STUDENTS = [
            {
                "id": "std-001",
                "enrollment_no": "22AIML001",
                "full_name": "Aarav Mehta",
                "email": "aarav.m@greenfield.edu",
                "department": department,
                "semester": 6,
                "section": "AIML-A",
                "batch_year": "2023-2027",
                "contact_number": "+91 98765 43210"
            },
            {
                "id": "std-002",
                "enrollment_no": "22AIML018",
                "full_name": "Diya Roy",
                "email": "diya.r@greenfield.edu",
                "department": department,
                "semester": 6,
                "section": "AIML-A",
                "batch_year": "2023-2027",
                "contact_number": "+91 98765 43211"
            },
            {
                "id": "std-003",
                "enrollment_no": "22AIML089",
                "full_name": "Rohan Verma",
                "email": "rohan.v@greenfield.edu",
                "department": department,
                "semester": 6,
                "section": "AIML-B",
                "batch_year": "2023-2027",
                "contact_number": "+91 98765 43212"
            },
            {
                "id": "std-004",
                "enrollment_no": "22AIML055",
                "full_name": "Sneha Patel",
                "email": "sneha.p@greenfield.edu",
                "department": department,
                "semester": 6,
                "section": "AIML-A",
                "batch_year": "2023-2027",
                "contact_number": "+91 98765 43213"
            },
            {
                "id": "std-005",
                "enrollment_no": "22AIML071",
                "full_name": "Vikram Nair",
                "email": "vikram.n@greenfield.edu",
                "department": department,
                "semester": 6,
                "section": "AIML-B",
                "batch_year": "2023-2027",
                "contact_number": "+91 98765 43214"
            }
        ]
    return _IN_MEMORY_STUDENTS

def get_students_list(section: Optional[str] = None, department: str = DEPARTMENT_CODE) -> List[Dict[str, Any]]:
    """Fetch students list, optionally filtered by section."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/students?select=*&department=eq.{department}"
            if section:
                url += f"&section=eq.{section}"
            url += "&order=enrollment_no.asc"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[DB Service] Error fetching students: {e}")

    # Fallback to in-memory students
    students = _get_in_memory_students(department)
    if section and section.lower() != "all":
        students = [s for s in students if s.get("section", "").lower() == section.lower()]
    return students

def get_student_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Look up a student profile by their auth user_id."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/students?user_id=eq.{user_id}&limit=1"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200:
                records = resp.json()
                if records:
                    return records[0]
        except Exception as e:
            print(f"[DB Service] Error getting student by user_id: {e}")

    for s in _get_in_memory_students():
        if s.get("user_id") == user_id:
            return s
    return None

def create_student(data: Dict[str, Any]) -> Dict[str, Any]:
    """Register a new student record."""
    new_student = {
        "id": data.get("id") or f"std-{uuid.uuid4().hex[:6]}",
        "enrollment_no": data.get("enrollment_no", "22AIML000"),
        "full_name": data.get("full_name", "New Student"),
        "email": data.get("email", ""),
        "department": data.get("department", DEPARTMENT_CODE),
        "semester": data.get("semester", 6),
        "section": data.get("section", "AIML-A"),
        "batch_year": data.get("batch_year", "2023-2027"),
        "contact_number": data.get("contact_number")
    }

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/students"
            resp = requests.post(url, headers=_HEADERS, json=new_student, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else new_student
        except Exception as e:
            print(f"[DB Service] Error creating student in Supabase: {e}")

    students = _get_in_memory_students()
    students.append(new_student)
    return new_student

def update_student(student_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing student record."""
    data["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/students?id=eq.{student_id}"
            resp = requests.patch(url, headers=_HEADERS, json=data, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else {"id": student_id, **data}
        except Exception as e:
            print(f"[DB Service] Error updating student in Supabase: {e}")

    for s in _get_in_memory_students():
        if str(s.get("id")) == str(student_id) or str(s.get("enrollment_no")) == str(student_id):
            s.update(data)
            return s
    return {"id": student_id, **data}

def delete_student(student_id: str) -> bool:
    """Delete a student record."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/students?id=eq.{student_id}"
            resp = requests.delete(url, headers=_HEADERS, timeout=5)
            if resp.status_code in (200, 204):
                return True
        except Exception as e:
            print(f"[DB Service] Error deleting student in Supabase: {e}")

    students = _get_in_memory_students()
    before = len(students)
    students[:] = [s for s in students if str(s.get("id")) != str(student_id) and str(s.get("enrollment_no")) != str(student_id)]
    return len(students) < before


# ==============================================================================
# 3. SUBJECTS SERVICE
# ==============================================================================

_IN_MEMORY_SUBJECTS: Optional[List[Dict[str, Any]]] = None

def _get_in_memory_subjects(department: str = DEPARTMENT_CODE) -> List[Dict[str, Any]]:
    """Initialize or return in-memory subject catalog."""
    global _IN_MEMORY_SUBJECTS
    if _IN_MEMORY_SUBJECTS is None:
        _IN_MEMORY_SUBJECTS = [
            {
                "id": c["id"],
                "name": c["name"],
                "department": department,
                "semester": c["semester"],
                "credits": c["credits"],
                "description": f"Core {c['name']} curriculum for {department} students."
            }
            for c in DEPARTMENT_COURSES
        ]
    return _IN_MEMORY_SUBJECTS

def get_subjects_list(department: str = DEPARTMENT_CODE) -> List[Dict[str, Any]]:
    """Fetch department subject catalog."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/subjects?select=*&department=eq.{department}&order=id.asc"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200 and resp.json():
                return resp.json()
        except Exception as e:
            print(f"[DB Service] Error fetching subjects: {e}")

    return _get_in_memory_subjects(department)

def create_subject(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a subject in the catalog."""
    new_sub = {
        "id": data.get("id", "AI400").upper(),
        "name": data.get("name", "New Subject"),
        "department": data.get("department", DEPARTMENT_CODE),
        "semester": data.get("semester", 6),
        "credits": data.get("credits", 4),
        "description": data.get("description", "")
    }

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/subjects"
            headers = {**_HEADERS, "Prefer": "resolution=merge-duplicates,return=representation"}
            resp = requests.post(url, headers=headers, json=new_sub, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else new_sub
        except Exception as e:
            print(f"[DB Service] Error creating subject in Supabase: {e}")

    subjects = _get_in_memory_subjects()
    # Replace if exists, else append
    for idx, s in enumerate(subjects):
        if s.get("id") == new_sub["id"]:
            subjects[idx] = new_sub
            return new_sub
    subjects.append(new_sub)
    return new_sub

def update_subject(subject_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a subject record."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/subjects?id=eq.{subject_id}"
            resp = requests.patch(url, headers=_HEADERS, json=data, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else {"id": subject_id, **data}
        except Exception as e:
            print(f"[DB Service] Error updating subject in Supabase: {e}")

    for s in _get_in_memory_subjects():
        if s.get("id") == subject_id:
            s.update(data)
            return s
    return {"id": subject_id, **data}

def delete_subject(subject_id: str) -> bool:
    """Delete a subject from the catalog."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/subjects?id=eq.{subject_id}"
            resp = requests.delete(url, headers=_HEADERS, timeout=5)
            if resp.status_code in (200, 204):
                return True
        except Exception as e:
            print(f"[DB Service] Error deleting subject in Supabase: {e}")

    subjects = _get_in_memory_subjects()
    before = len(subjects)
    subjects[:] = [s for s in subjects if s.get("id") != subject_id]
    return len(subjects) < before


# ==============================================================================
# 4. EVENTS SERVICE
# ==============================================================================

_IN_MEMORY_EVENTS: Optional[List[Dict[str, Any]]] = None

def _get_in_memory_events(department: str = DEPARTMENT_CODE) -> List[Dict[str, Any]]:
    """Initialize or return in-memory events with dynamic future dates."""
    global _IN_MEMORY_EVENTS
    if _IN_MEMORY_EVENTS is None:
        now = datetime.utcnow()
        _IN_MEMORY_EVENTS = [
            {
                "id": "evt-001",
                "title": "Annual AIML Hackathon 2026",
                "description": "Inter-department 36-hour hackathon focused on Generative AI and Autonomous Agent Systems.",
                "date_time": (now + timedelta(days=4, hours=2)).strftime("%Y-%m-%dT10:00:00Z"),
                "location": "AIML Computing Labs 401-403",
                "organizer": "AIML Student Chapter",
                "department": department,
                "created_by": "00000000-0000-0000-0000-000000000001",
                "created_at": now.strftime("%Y-%m-%dT00:00:00Z"),
                "updated_at": now.strftime("%Y-%m-%dT00:00:00Z"),
            },
            {
                "id": "evt-002",
                "title": "Distinguished Industry Talk: Foundation Models in Production",
                "description": "Interactive seminar with leading AI research engineers on scaling multimodal vision-language models.",
                "date_time": (now + timedelta(days=10, hours=5)).strftime("%Y-%m-%dT14:30:00Z"),
                "location": "Seminar Hall 2, Academic Complex",
                "organizer": "Dept Industry Relations Cell",
                "department": department,
                "created_by": "00000000-0000-0000-0000-000000000001",
                "created_at": now.strftime("%Y-%m-%dT00:00:00Z"),
                "updated_at": now.strftime("%Y-%m-%dT00:00:00Z"),
            },
            {
                "id": "evt-003",
                "title": "Hands-on Workshop: Edge AI with NVIDIA Jetson",
                "description": "Practical hands-on training workshop on deploying quantized computer vision models onto edge robotics hardware.",
                "date_time": (now + timedelta(days=18, hours=1)).strftime("%Y-%m-%dT10:00:00Z"),
                "location": "Robotics & Vision Lab (Lab 402)",
                "organizer": "AIML Robotics Club",
                "department": department,
                "created_by": "00000000-0000-0000-0000-000000000002",
                "created_at": now.strftime("%Y-%m-%dT00:00:00Z"),
                "updated_at": now.strftime("%Y-%m-%dT00:00:00Z"),
            },
            {
                "id": "evt-004",
                "title": "Department Seminar: Autonomous Multi-Agent Workflows",
                "description": "Technical seminar demonstrating collaborative agent architectures and LangGraph orchestration in enterprise settings.",
                "date_time": (now + timedelta(days=25, hours=4)).strftime("%Y-%m-%dT15:00:00Z"),
                "location": "Auditorium B, Technology Wing",
                "organizer": "AIML Research Group",
                "department": department,
                "created_by": "00000000-0000-0000-0000-000000000002",
                "created_at": now.strftime("%Y-%m-%dT00:00:00Z"),
                "updated_at": now.strftime("%Y-%m-%dT00:00:00Z"),
            }
        ]
    return _IN_MEMORY_EVENTS


def get_events_list(department: str = DEPARTMENT_CODE, upcoming_only: bool = False) -> List[Dict[str, Any]]:
    """Fetch department events, workshops, seminars, and hackathons."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/events?select=*&department=eq.{department}"
            if upcoming_only:
                now_iso = datetime.utcnow().isoformat()
                url += f"&date_time=gte.{now_iso}"
            url += "&order=date_time.asc"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200 and resp.json():
                return resp.json()
        except Exception as e:
            print(f"[DB Service] Error fetching events from Supabase: {e}")

    # Fallback in-memory events
    events = [e for e in _get_in_memory_events(department) if e.get("department") == department]
    if upcoming_only:
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        events = [e for e in events if e.get("date_time", "") >= now_str]
    events.sort(key=lambda x: x.get("date_time", ""))
    return events


def get_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single department event by ID."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/events?id=eq.{event_id}&select=*"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    return results[0]
        except Exception as e:
            print(f"[DB Service] Error fetching event {event_id} from Supabase: {e}")

    # Fallback to in-memory store
    for evt in _get_in_memory_events():
        if str(evt.get("id")) == str(event_id):
            return evt
    return None


def create_event(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new department event."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/events"
            resp = requests.post(url, headers=_HEADERS, json=data, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else data
        except Exception as e:
            print(f"[DB Service] Error creating event in Supabase: {e}")

    # In-memory creation
    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    new_event = {
        "id": data.get("id") or str(uuid.uuid4()),
        "title": data.get("title", "Untitled Event"),
        "description": data.get("description", ""),
        "date_time": data.get("date_time", now_str),
        "location": data.get("location", "TBD"),
        "organizer": data.get("organizer", "AIML Department"),
        "department": data.get("department", DEPARTMENT_CODE),
        "created_by": data.get("created_by"),
        "created_at": now_str,
        "updated_at": now_str,
    }
    events = _get_in_memory_events()
    events.append(new_event)
    return new_event


def update_event(event_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update event details."""
    if _is_configured():
        try:
            data["updated_at"] = datetime.utcnow().isoformat()
            url = f"{SUPABASE_URL}/rest/v1/events?id=eq.{event_id}"
            resp = requests.patch(url, headers=_HEADERS, json=data, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else data
        except Exception as e:
            print(f"[DB Service] Error updating event in Supabase: {e}")

    # In-memory update
    events = _get_in_memory_events()
    for evt in events:
        if str(evt.get("id")) == str(event_id):
            evt.update(data)
            evt["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            return evt
    return {"id": event_id, **data}


def delete_event(event_id: str) -> bool:
    """Delete an event."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/events?id=eq.{event_id}"
            resp = requests.delete(url, headers=_HEADERS, timeout=5)
            if resp.status_code in (200, 204):
                return True
        except Exception as e:
            print(f"[DB Service] Error deleting event in Supabase: {e}")

    # In-memory deletion
    events = _get_in_memory_events()
    before_len = len(events)
    events[:] = [e for e in events if str(e.get("id")) != str(event_id)]
    return len(events) < before_len or True


# ==============================================================================
# 5. STUDENT REQUESTS SERVICE (Human Approval Workflow)
# ==============================================================================

_IN_MEMORY_REQUESTS: Optional[List[Dict[str, Any]]] = None

def _get_in_memory_requests() -> List[Dict[str, Any]]:
    """Initialize or return in-memory student requests demonstrating the human approval workflow."""
    global _IN_MEMORY_REQUESTS
    if _IN_MEMORY_REQUESTS is None:
        now = datetime.utcnow()
        t1 = (now - timedelta(days=3)).strftime("%Y-%m-%dT10:00:00Z")
        t2 = (now - timedelta(days=2)).strftime("%Y-%m-%dT14:30:00Z")
        t3 = (now - timedelta(days=1)).strftime("%Y-%m-%dT09:15:00Z")
        t4 = (now - timedelta(hours=6)).strftime("%Y-%m-%dT11:45:00Z")
        t5 = (now - timedelta(days=5)).strftime("%Y-%m-%dT16:00:00Z")

        _IN_MEMORY_REQUESTS = [
            {
                "id": "req-001",
                "student_id": "std-001",
                "user_id": "00000000-0000-0000-0000-000000000003",
                "request_type": "Lab Compute Access",
                "description": "Requesting 24GB VRAM GPU workstation access in Lab 401 for fine-tuning Vision Transformer models on medical imaging.",
                "status": "Pending",
                "assigned_to": "fac-001",
                "comments": None,
                "history": [
                    {
                        "status": "Pending",
                        "comments": "Request submitted by student.",
                        "updated_by": "Student",
                        "timestamp": t1,
                    }
                ],
                "created_at": t1,
                "updated_at": t1,
                "students": {"full_name": "Aarav Mehta", "enrollment_no": "22AIML042", "section": "AIML-A"},
                "faculty": {"name": "Dr. A. Sharma", "designation": "Professor & HOD"},
            },
            {
                "id": "req-002",
                "student_id": "std-002",
                "user_id": "00000000-0000-0000-0000-000000000003",
                "request_type": "Bonafide Certificate",
                "description": "Need official department bonafide letter signed by HOD for submission to Smart India Hackathon 2026.",
                "status": "Approved",
                "assigned_to": "fac-001",
                "comments": "Approved. Official signed certificate is ready for collection at AIML Department Office.",
                "history": [
                    {
                        "status": "Pending",
                        "comments": "Request submitted with hackathon registration details.",
                        "updated_by": "Student",
                        "timestamp": t2,
                    },
                    {
                        "status": "Approved",
                        "comments": "Approved. Official signed certificate is ready for collection at AIML Department Office.",
                        "updated_by": "Dr. A. Sharma (HOD)",
                        "timestamp": (now - timedelta(days=1)).strftime("%Y-%m-%dT16:00:00Z"),
                    }
                ],
                "created_at": t2,
                "updated_at": (now - timedelta(days=1)).strftime("%Y-%m-%dT16:00:00Z"),
                "students": {"full_name": "Diya Roy", "enrollment_no": "22AIML018", "section": "AIML-A"},
                "faculty": {"name": "Dr. A. Sharma", "designation": "Professor & HOD"},
            },
            {
                "id": "req-003",
                "student_id": "std-003",
                "user_id": "00000000-0000-0000-0000-000000000003",
                "request_type": "Attendance Condonation Request",
                "description": "Requesting condonation for 10 days missed in AI401 and AI402 due to severe viral fever and hospitalization.",
                "status": "More Information Required",
                "assigned_to": "fac-002",
                "comments": "Please upload or provide hospital discharge summary and medical fitness certificate to verify condonation eligibility.",
                "history": [
                    {
                        "status": "Pending",
                        "comments": "Condonation request submitted.",
                        "updated_by": "Student",
                        "timestamp": t3,
                    },
                    {
                        "status": "Under Review",
                        "comments": "Assigned to Prof. K. Patel for medical review.",
                        "updated_by": "Prof. K. Patel",
                        "timestamp": (now - timedelta(hours=18)).strftime("%Y-%m-%dT11:00:00Z"),
                    },
                    {
                        "status": "More Information Required",
                        "comments": "Please upload or provide hospital discharge summary and medical fitness certificate to verify condonation eligibility.",
                        "updated_by": "Prof. K. Patel",
                        "timestamp": (now - timedelta(hours=8)).strftime("%Y-%m-%dT14:20:00Z"),
                    }
                ],
                "created_at": t3,
                "updated_at": (now - timedelta(hours=8)).strftime("%Y-%m-%dT14:20:00Z"),
                "students": {"full_name": "Rohan Verma", "enrollment_no": "22AIML089", "section": "AIML-B"},
                "faculty": {"name": "Prof. K. Patel", "designation": "Associate Professor"},
            },
            {
                "id": "req-004",
                "student_id": "std-004",
                "user_id": "00000000-0000-0000-0000-000000000004",
                "request_type": "Project Guide Allocation",
                "description": "Requesting Prof. M. Rao as capstone research project guide for Autonomous Robotics and Jetson Edge AI topic.",
                "status": "Under Review",
                "assigned_to": "fac-004",
                "comments": "Under review by Department Project Review Committee.",
                "history": [
                    {
                        "status": "Pending",
                        "comments": "Project proposal and guide choice submitted.",
                        "updated_by": "Student",
                        "timestamp": t4,
                    },
                    {
                        "status": "Under Review",
                        "comments": "Under review by Department Project Review Committee.",
                        "updated_by": "Department Admin",
                        "timestamp": (now - timedelta(hours=2)).strftime("%Y-%m-%dT13:00:00Z"),
                    }
                ],
                "created_at": t4,
                "updated_at": (now - timedelta(hours=2)).strftime("%Y-%m-%dT13:00:00Z"),
                "students": {"full_name": "Sneha Patel", "enrollment_no": "22AIML055", "section": "AIML-A"},
                "faculty": {"name": "Prof. M. Rao", "designation": "Assistant Professor"},
            },
            {
                "id": "req-005",
                "student_id": "std-005",
                "user_id": "00000000-0000-0000-0000-000000000004",
                "request_type": "Course Exemption",
                "description": "Requesting exemption from on-campus AI401 practical sessions based on completion of external online certification.",
                "status": "Rejected",
                "assigned_to": "fac-001",
                "comments": "Rejected as per university academic regulations: external online certifications cannot substitute for mandatory laboratory practicals.",
                "history": [
                    {
                        "status": "Pending",
                        "comments": "Exemption request submitted.",
                        "updated_by": "Student",
                        "timestamp": t5,
                    },
                    {
                        "status": "Rejected",
                        "comments": "Rejected as per university academic regulations: external online certifications cannot substitute for mandatory laboratory practicals.",
                        "updated_by": "Dr. A. Sharma (HOD)",
                        "timestamp": (now - timedelta(days=4)).strftime("%Y-%m-%dT09:00:00Z"),
                    }
                ],
                "created_at": t5,
                "updated_at": (now - timedelta(days=4)).strftime("%Y-%m-%dT09:00:00Z"),
                "students": {"full_name": "Vikram Nair", "enrollment_no": "22AIML071", "section": "AIML-B"},
                "faculty": {"name": "Dr. A. Sharma", "designation": "Professor & HOD"},
            }
        ]
    return _IN_MEMORY_REQUESTS


def get_student_requests(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Fetch student requests for approval workflow.
    - If user_id is provided, returns requests made by that student.
    - If assigned_to is provided, returns requests routed to that faculty/admin.
    - If neither is provided (admin/faculty view), returns all requests.
    """
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/student_requests?select=*,students(full_name,enrollment_no,section),faculty(name,designation)&order=created_at.desc"
            if user_id:
                url += f"&user_id=eq.{user_id}"
            if status:
                url += f"&status=eq.{status}"
            if assigned_to:
                url += f"&assigned_to=eq.{assigned_to}"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[DB Service] Error fetching student requests: {e}")

    # Fallback in-memory requests
    all_reqs = _get_in_memory_requests()
    results = all_reqs

    if user_id:
        results = [r for r in results if str(r.get("user_id")) == str(user_id)]
    if status and status.lower() != "all":
        # Match case-insensitively and handle "Under Review" / "In Review" aliases
        target_s = status.lower()
        if target_s in ("under review", "in review"):
            results = [r for r in results if r.get("status", "").lower() in ("under review", "in review")]
        else:
            results = [r for r in results if r.get("status", "").lower() == target_s]
    if assigned_to:
        results = [r for r in results if str(r.get("assigned_to")) == str(assigned_to)]

    return results


def get_student_request_by_id(request_id: str) -> Optional[Dict[str, Any]]:
    """Fetch single student request by ID including its review history."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/student_requests?id=eq.{request_id}&select=*,students(full_name,enrollment_no,section),faculty(name,designation)"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0]
        except Exception as e:
            print(f"[DB Service] Error fetching request {request_id}: {e}")

    for r in _get_in_memory_requests():
        if str(r.get("id")) == str(request_id):
            return r
    return None


def create_student_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """Submit a new student request into the human approval pipeline."""
    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    req_id = data.get("id") or f"req-{uuid.uuid4().hex[:8]}"

    initial_history = [
        {
            "action": "Request Submitted",
            "status": "Pending",
            "to_status": "Pending",
            "comments": "Request submitted by student into human approval queue.",
            "updated_by": "Student",
            "actor_name": "Student",
            "actor_role": "Student",
            "timestamp": now_str,
        }
    ]

    new_request = {
        "id": req_id,
        "student_id": data.get("student_id"),
        "user_id": data.get("user_id"),
        "request_type": data.get("request_type", "General Academic Request"),
        "description": data.get("description", ""),
        "status": "Pending",
        "assigned_to": data.get("assigned_to"),
        "comments": None,
        "history": initial_history,
        "created_at": now_str,
        "updated_at": now_str,
        "students": data.get("students", {"full_name": "Current Student", "enrollment_no": "AIML-STD", "section": "AIML"}),
    }

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/student_requests"
            resp = requests.post(url, headers=_HEADERS, json=new_request, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else new_request
        except Exception as e:
            print(f"[DB Service] Error creating student request in Supabase: {e}")

    requests_list = _get_in_memory_requests()
    requests_list.insert(0, new_request)
    return new_request


def update_student_request_status(
    request_id: str,
    status: str,
    comments: Optional[str] = None,
    assigned_to: Optional[str] = None,
    reviewer_name: Optional[str] = None,
    actor_name: Optional[str] = None,
    actor_role: Optional[str] = None
) -> Dict[str, Any]:
    """
    Human approval decision action.
    Authorized faculty or administrator updates status:
    'Pending', 'Under Review', 'Approved', 'Rejected', or 'More Information Required'.
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Normalize In Review to Under Review
    normalized_status = "Under Review" if status == "In Review" else status
    effective_name = actor_name or reviewer_name or "Faculty / Administrator"
    effective_role = actor_role or "Staff"

    history_entry = {
        "action": f"Status changed to {normalized_status}",
        "status": normalized_status,
        "to_status": normalized_status,
        "comments": comments or f"Status changed to {normalized_status}.",
        "updated_by": effective_name,
        "actor_name": effective_name,
        "actor_role": effective_role,
        "timestamp": now_str,
    }

    payload: Dict[str, Any] = {
        "status": normalized_status,
        "updated_at": now_str,
    }
    if comments is not None:
        payload["comments"] = comments
    if assigned_to is not None:
        payload["assigned_to"] = assigned_to

    # In-memory update
    req = get_student_request_by_id(request_id)
    if req:
        req["status"] = normalized_status
        req["updated_at"] = now_str
        if comments is not None:
            req["comments"] = comments
        if assigned_to is not None:
            req["assigned_to"] = assigned_to
        if "history" not in req or not isinstance(req["history"], list):
            req["history"] = []
        req["history"].append(history_entry)
        payload["history"] = req["history"]

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/student_requests?id=eq.{request_id}"
            resp = requests.patch(url, headers=_HEADERS, json=payload, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else payload
        except Exception as e:
            print(f"[DB Service] Error updating student request in Supabase: {e}")

    return req or {"id": request_id, **payload}


def add_student_request_reply(
    request_id: str,
    user_id: str,
    additional_info: str,
    actor_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Allows a student to reply when additional information is requested.
    Transitions status back to 'Under Review' and records history.
    """
    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    req = get_student_request_by_id(request_id)

    if not req:
        raise ValueError(f"Request {request_id} not found")

    reply_history = {
        "action": "Student Provided Additional Information",
        "status": "Under Review",
        "from_status": req.get("status", "More Information Required"),
        "to_status": "Under Review",
        "comments": f"Student response provided: {additional_info}",
        "updated_by": actor_name or "Student",
        "actor_name": actor_name or "Student",
        "actor_role": "Student",
        "timestamp": now_str,
    }

    req["status"] = "Under Review"
    req["updated_at"] = now_str
    req["description"] = f"{req.get('description', '')}\n\n[Additional Information Added on {now_str[:10]}]:\n{additional_info}"
    if "history" not in req or not isinstance(req["history"], list):
        req["history"] = []
    req["history"].append(reply_history)

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/student_requests?id=eq.{request_id}"
            resp = requests.patch(url, headers=_HEADERS, json={
                "status": "Under Review",
                "description": req["description"],
                "updated_at": now_str,
                "history": req["history"]
            }, timeout=5)
            resp.raise_for_status()
        except Exception as e:
            print(f"[DB Service] Error saving student reply to Supabase: {e}")

    return req


def delete_student_request(request_id: str) -> bool:
    """Delete a student request (Admin only)."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/student_requests?id=eq.{request_id}"
            resp = requests.delete(url, headers=_HEADERS, timeout=5)
            if resp.status_code in (200, 204):
                return True
        except Exception as e:
            print(f"[DB Service] Error deleting student request in Supabase: {e}")

    reqs = _get_in_memory_requests()
    before = len(reqs)
    reqs[:] = [r for r in reqs if str(r.get("id")) != str(request_id)]
    return len(reqs) < before


# ==============================================================================
# 6. NOTICES & ACADEMIC DOCUMENTS DB HELPERS
# ==============================================================================

_IN_MEMORY_NOTICES: Optional[List[Dict[str, Any]]] = None

def _get_in_memory_notices(department: str = DEPARTMENT_CODE) -> List[Dict[str, Any]]:
    """Initialize or return in-memory notices with fallback to notices.json."""
    global _IN_MEMORY_NOTICES
    if _IN_MEMORY_NOTICES is None:
        notices_file = os.path.join(os.path.dirname(__file__), "data", "notices", "notices.json")
        loaded = []
        if os.path.exists(notices_file):
            try:
                with open(notices_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
            except Exception as e:
                print(f"[DB Service] Error loading notices.json: {e}")

        if not loaded:
            now_date = datetime.utcnow().strftime("%Y-%m-%d")
            loaded = [
                {
                    "id": "not-001",
                    "title": "AIML Annual AI Hackathon 2026 Registration Open",
                    "content": "Registration is open for the AIML Department Annual Hackathon: Generative AI and Autonomous Systems. Prize pool of $5000 and GPU credits provided.",
                    "department": department,
                    "category": "Event",
                    "date": now_date,
                    "is_pinned": True
                },
                {
                    "id": "not-002",
                    "title": "AIML Semester Exams & Lab Assessment Schedule",
                    "content": "Mid-semester theory examinations and laboratory practical evaluations for AIML batches (AIML-A and AIML-B) will commence on April 18th.",
                    "department": department,
                    "category": "Exam",
                    "date": now_date,
                    "is_pinned": True
                },
                {
                    "id": "not-003",
                    "title": "High Performance AI Lab Server Maintenance",
                    "content": "GPU cluster in Lab 401 (AIML Block) will undergo scheduled hypervisor and driver upgrades on Saturday from 10 AM to 4 PM.",
                    "department": department,
                    "category": "Lab",
                    "date": now_date,
                    "is_pinned": False
                }
            ]
        _IN_MEMORY_NOTICES = loaded
    return _IN_MEMORY_NOTICES

def get_db_notices(department: str = DEPARTMENT_CODE, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch notices from database with fallback."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/notices?select=*&or=(department.eq.{department},department.eq.General)&order=date.desc&limit={limit}"
            resp = requests.get(url, headers=_HEADERS, timeout=5)
            if resp.status_code == 200 and resp.json():
                return resp.json()
        except Exception as e:
            print(f"[DB Service] Error fetching DB notices: {e}")

    notices = _get_in_memory_notices(department)
    return notices[:limit]

def create_db_notice(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new notice in the database."""
    now_date = datetime.utcnow().strftime("%Y-%m-%d")
    new_notice = {
        "id": data.get("id") or f"not-{uuid.uuid4().hex[:6]}",
        "title": data.get("title", "Untitled Notice"),
        "content": data.get("content", ""),
        "category": data.get("category", "Academic"),
        "department": data.get("department", DEPARTMENT_CODE),
        "date": data.get("date", now_date),
        "is_pinned": data.get("is_pinned", False),
        "created_by": data.get("created_by")
    }

    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/notices"
            resp = requests.post(url, headers=_HEADERS, json=new_notice, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else new_notice
        except Exception as e:
            print(f"[DB Service] Error creating notice in Supabase: {e}")

    notices = _get_in_memory_notices()
    notices.insert(0, new_notice)
    return new_notice

def update_db_notice(notice_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing department notice."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/notices?id=eq.{notice_id}"
            resp = requests.patch(url, headers=_HEADERS, json=data, timeout=5)
            resp.raise_for_status()
            results = resp.json()
            return results[0] if results else {"id": notice_id, **data}
        except Exception as e:
            print(f"[DB Service] Error updating notice in Supabase: {e}")

    for n in _get_in_memory_notices():
        if str(n.get("id")) == str(notice_id):
            n.update(data)
            return n
    return {"id": notice_id, **data}

def delete_db_notice(notice_id: str) -> bool:
    """Delete a notice from the database."""
    if _is_configured():
        try:
            url = f"{SUPABASE_URL}/rest/v1/notices?id=eq.{notice_id}"
            resp = requests.delete(url, headers=_HEADERS, timeout=5)
            if resp.status_code in (200, 204):
                return True
        except Exception as e:
            print(f"[DB Service] Error deleting notice in Supabase: {e}")

    notices = _get_in_memory_notices()
    before = len(notices)
    notices[:] = [n for n in notices if str(n.get("id")) != str(notice_id)]
    return len(notices) < before


# ==============================================================================
# 7. DEPARTMENT OVERVIEW & ANALYTICS
# ==============================================================================

def get_department_overview_stats(department: str = DEPARTMENT_CODE) -> Dict[str, Any]:
    """Calculate aggregated telemetry and statistics for the Admin Overview."""
    students = get_students_list(department=department)
    faculty = get_faculty_list(department=department)
    notices = get_db_notices(department=department, limit=100)
    all_events = get_events_list(department=department, upcoming_only=False)
    upcoming_events = get_events_list(department=department, upcoming_only=True)
    requests_list = get_student_requests()
    subjects = get_subjects_list(department=department)

    # Document count in docs folder
    docs_count = 0
    docs_dir = os.path.join(os.path.dirname(__file__), "data", "docs")
    if os.path.exists(docs_dir):
        docs_count = len([f for f in os.listdir(docs_dir) if not f.endswith(".json") and os.path.isfile(os.path.join(docs_dir, f))])

    pending_reqs = [
        r for r in requests_list
        if r.get("status", "") in ("Pending", "Under Review", "In Review", "More Information Required")
    ]

    # Section breakdown
    section_map: Dict[str, int] = {}
    for s in students:
        sec = s.get("section", "AIML-A")
        section_map[sec] = section_map.get(sec, 0) + 1

    return {
        "department_code": department,
        "department_name": DEPARTMENT_NAME,
        "students_count": len(students),
        "faculty_count": len(faculty),
        "active_notices_count": len(notices),
        "total_events_count": len(all_events),
        "upcoming_events_count": len(upcoming_events),
        "pending_requests_count": len(pending_reqs),
        "total_requests_count": len(requests_list),
        "subjects_count": len(subjects),
        "documents_count": docs_count,
        "students_by_section": section_map,
        "upcoming_events": upcoming_events[:4],
        "recent_requests": requests_list[:5]
    }

