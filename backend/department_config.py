"""
department_config.py — Centralized Configuration for AIDA Department Operations.

Configures department identity, courses, sections, laboratories, and document categories.
Designed to be modular: swapping the environment variables or configuration values allows
the system to instantly support any other academic department (e.g., ECE, CSE, Mech, Civil)
without modifying core agent graph or retrieval code.
"""

import os
from typing import List, Dict, Any

# ==================== DEPARTMENT CORE IDENTITY ====================
DEPARTMENT_CODE = os.getenv("DEPARTMENT_CODE", "AIML").upper()
DEPARTMENT_NAME = os.getenv("DEPARTMENT_NAME", "Artificial Intelligence & Machine Learning")
DEPARTMENT_ACRONYM = os.getenv("DEPARTMENT_ACRONYM", "AIML")
INSTITUTION_NAME = os.getenv("INSTITUTION_NAME", "Department of AIML")

# ==================== STUDENT SECTIONS / GROUPS ====================
# Default sections for the department (e.g. AIML-A, AIML-B)
_sections_env = os.getenv("STUDENT_SECTIONS", "AIML-A,AIML-B")
STUDENT_SECTIONS: List[str] = [s.strip().upper() for s in _sections_env.split(",") if s.strip()]

# Section tokens for fuzzy routing/clarification heuristic
SECTION_TOKENS = set()
for sec in STUDENT_SECTIONS:
    sec_lower = sec.lower()
    SECTION_TOKENS.add(sec_lower)                         # "aiml-a"
    SECTION_TOKENS.add(sec_lower.replace("-", " "))       # "aiml a"
    SECTION_TOKENS.add(sec_lower.replace("-", ""))        # "aimla"
    # Suffix tokens like "a", "b", "section a", "group a"
    sec_suffix = sec.split("-")[-1].lower() if "-" in sec else sec_lower
    SECTION_TOKENS.add(sec_suffix)
    SECTION_TOKENS.add(f"section {sec_suffix}")
    SECTION_TOKENS.add(f"group {sec_suffix}")

# Build dynamic clarification phrase for response writer and prompt
SECTIONS_DISPLAY = " or ".join([f"**{s}**" for s in STUDENT_SECTIONS])
SECTIONS_TEXT = " or ".join(STUDENT_SECTIONS)

# ==================== DEPARTMENT COURSES / SUBJECTS ====================
# Generic course catalog (no hardcoded personal faculty data)
DEPARTMENT_COURSES: List[Dict[str, Any]] = [
    {
        "id": "AI401",
        "name": "Machine Learning Foundations",
        "aliases": ["Machine Learning", "ML", "AI401"],
        "semester": 6,
        "credits": 4
    },
    {
        "id": "AI402",
        "name": "Deep Learning & Neural Networks",
        "aliases": ["Deep Learning", "DL", "Neural Networks", "AI402"],
        "semester": 6,
        "credits": 4
    },
    {
        "id": "AI403",
        "name": "Natural Language Processing",
        "aliases": ["Natural Language Processing", "NLP", "AI403"],
        "semester": 6,
        "credits": 3
    },
    {
        "id": "AI404",
        "name": "Computer Vision",
        "aliases": ["Computer Vision", "CV", "Vision", "AI404"],
        "semester": 6,
        "credits": 3
    },
    {
        "id": "AI405",
        "name": "Reinforcement Learning & Robotics",
        "aliases": ["Reinforcement Learning", "RL", "Robotics", "AI405"],
        "semester": 6,
        "credits": 3
    },
    {
        "id": "AI406",
        "name": "AI Ethics & Governance",
        "aliases": ["AI Ethics", "Ethics", "Governance", "AI406"],
        "semester": 6,
        "credits": 2
    }
]

# Quick lookup by course id or alias
COURSE_ALIAS_MAP: Dict[str, str] = {}
for course in DEPARTMENT_COURSES:
    COURSE_ALIAS_MAP[course["id"].lower()] = course["id"]
    for alias in course["aliases"]:
        COURSE_ALIAS_MAP[alias.lower()] = course["id"]

# ==================== DEPARTMENT LABORATORIES ====================
DEPARTMENT_LABS: List[Dict[str, Any]] = [
    {
        "id": "LAB-AIML-01",
        "name": "High Performance AI & Deep Learning Lab",
        "room": "Lab 401, AIML Block",
        "in_charge_title": "Faculty Lab In-Charge (Deep Learning)",
        "equipment": "NVIDIA GPU Workstations, Cloud Compute Nodes"
    },
    {
        "id": "LAB-AIML-02",
        "name": "Computer Vision & Robotics Lab",
        "room": "Lab 402, AIML Block",
        "in_charge_title": "Faculty Lab In-Charge (Robotics)",
        "equipment": "Edge AI Kits, Robotic Arms, Stereo Cameras"
    },
    {
        "id": "LAB-AIML-03",
        "name": "Natural Language & Speech Systems Lab",
        "room": "Lab 403, AIML Block",
        "in_charge_title": "Faculty Lab In-Charge (NLP)",
        "equipment": "Audio Processing Consoles, Dedicated Server Nodes"
    }
]

# ==================== DEPARTMENT DOCUMENT TAGS & CATEGORIES ====================
DEPARTMENT_DOC_CATEGORIES = [
    "Curriculum & Syllabus",
    "Lab Manuals",
    "Capstone Project Guidelines",
    "Academic Regulations & Evaluation",
    "Faculty Directory & Office Hours",
    "Department Circulars & Policies"
]

def get_department_metadata() -> Dict[str, Any]:
    """Return dictionary representation of department configuration for API and clients."""
    return {
        "code": DEPARTMENT_CODE,
        "name": DEPARTMENT_NAME,
        "acronym": DEPARTMENT_ACRONYM,
        "institution": INSTITUTION_NAME,
        "sections": STUDENT_SECTIONS,
        "courses": DEPARTMENT_COURSES,
        "labs": DEPARTMENT_LABS,
        "document_categories": DEPARTMENT_DOC_CATEGORIES
    }

