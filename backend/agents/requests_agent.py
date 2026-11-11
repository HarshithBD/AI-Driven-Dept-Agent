"""
requests_agent.py — Student Request Assistance Tool & Agent for AIDA.

Assists students with:
1. Request Types & Guidelines (Bonafide, Leave, On-Duty/OD, Project Guide, GPU Access, Course Exemption).
2. Submission Workflows & Required Documentation.
3. Drafting clear, professional request descriptions.
4. Explaining the Human Approval & Review Workflow.
5. Tracking personal request statuses via the department database.

CRITICAL GOVERNANCE RULE:
AIDA may help explain procedures and draft descriptions, but CANNOT approve or reject requests.
All decisions must be rendered exclusively by authorized human faculty members or administrators.
"""

from __future__ import annotations

import os
import re
import json
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

REQUEST_TYPES_INFO = {
    "Bonafide Certificate": {
        "purpose": "Issued for visa applications, passport processing, educational bank loans, external internships, bus/rail concession passes, or scholarship applications.",
        "documents": "Copy of student college ID, enrollment verification, or external offer/application letter.",
        "sla": "1 to 2 working days",
        "reviewer": "Department Administrative Office / Faculty Advisor"
    },
    "Leave of Absence": {
        "purpose": "Official leave for medical sickness, family emergency, or personal obligations.",
        "documents": "Doctor's medical certificate (for medical leaves exceeding 2 consecutive days) and parent/guardian consent.",
        "sla": "1 to 2 working days",
        "reviewer": "Class In-Charge / Faculty Advisor"
    },
    "On-Duty (OD) Permission": {
        "purpose": "Attendance exemption when representing Greenfield Institute in external hackathons, research conferences, sports competitions, or tech symposiums.",
        "documents": "Formal invitation letter, hackathon registration confirmation, or faculty mentor endorsement.",
        "sla": "1 working day (submit at least 48 hours prior to the event)",
        "reviewer": "HOD / Faculty Activity Coordinator"
    },
    "Project Guide Allocation": {
        "purpose": "Registration or change of faculty guide for Capstone Projects (AI701/AI801) and domain-specific research thesis.",
        "documents": "Project synopsis (1-2 pages), team member enrollment numbers, and proposed research domain.",
        "sla": "3 working days",
        "reviewer": "Department Project Coordinator / HOD"
    },
    "Lab Compute / GPU Access": {
        "purpose": "High-memory GPU workstation allocation (NVIDIA RTX 4090 / Jetson Orin / SLURM cluster quota) for deep learning training.",
        "documents": "Project proposal detailing compute requirements, dataset size, and faculty sponsor endorsement.",
        "sla": "2 working days",
        "reviewer": "AIML Lab In-Charge (Prof. Rao / Dr. Sharma)"
    },
    "Course Exemption / Credit Transfer": {
        "purpose": "Waiver or credit transfer for approved NPTEL / Coursera / SWAYAM certifications or student exchange courses.",
        "documents": "Official grade sheet / certificate with verified proctored exam score and course syllabus match.",
        "sla": "5 working days",
        "reviewer": "Department Academic Committee"
    }
}

REQUESTS_EXTRACT_PROMPT = f"""You are a parameter extractor for student administrative requests in the {DEPARTMENT_NAME} ({DEPARTMENT_CODE}) Department.
Extract the relevant query intent and parameters from the user's question and history.
Respond with ONLY a JSON object, no other text.

{{
  "request_type": "<'Bonafide Certificate' | 'Leave of Absence' | 'On-Duty (OD) Permission' | 'Project Guide Allocation' | 'Lab Compute / GPU Access' | 'Course Exemption / Credit Transfer' | 'general_workflow' | null>",
  "action": "<'inquire_process' | 'draft_request' | 'track_status' | 'human_policy_check' | 'general'>",
  "can_ai_approve_asked": <true if user asks if AI / AIDA can approve/reject/grant the request, otherwise false>
}}

Rules:
- If user asks 'Can you approve my leave?' or 'Approve my request', set can_ai_approve_asked=true and action='human_policy_check'.
- If user asks how to apply or what documents are needed, set action='inquire_process'.
- If user wants help writing, drafting, or formatting a request description, set action='draft_request'.
- If user asks where or how to check the status of their request, set action='track_status'.
"""


async def requests_node(state: GraphState) -> dict:
    """
    Handle student request inquiries, workflow guidance, drafting assistance,
    and personal status tracking with strict human-in-the-loop governance.
    """
    query = state["query"]
    history = state.get("history", [])
    user_role = state.get("user_role", "student")
    user_id = state.get("user_id")

    context = list(state.get("context", []))
    sources = list(state.get("sources", []))

    print(f"[Request Assistance Tool] Processing inquiry: '{query[:60]}...' (Role: {user_role})")

    # Extract parameters via LLM
    params = {}
    try:
        messages = [
            SystemMessage(content=REQUESTS_EXTRACT_PROMPT),
        ]
        for msg in history[-4:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=f"Extract parameters for: \"{query}\""))

        res = await llm.ainvoke(messages)
        raw_text = res.content
        if isinstance(raw_text, list):
            raw_text = " ".join([b.get("text", "") if isinstance(b, dict) else str(b) for b in raw_text])
        raw_text = re.sub(r"```json\s*", "", str(raw_text))
        raw_text = re.sub(r"```", "", raw_text).strip()
        params = json.loads(raw_text)
    except Exception as e:
        print(f"[Request Assistance Tool] Extraction error: {e}")
        params = {"request_type": "general_workflow", "action": "inquire_process", "can_ai_approve_asked": False}

    req_type = params.get("request_type")
    action = params.get("action", "inquire_process")
    can_ai_approve = params.get("can_ai_approve_asked", False)

    # 1. Critical Governance Context (Always Included)
    governance_notice = (
        "### AIDA Human Approval Governance Rule\n"
        "- **AI Restriction**: AIDA is an automated advisory assistant. It is strictly forbidden from directly approving, rejecting, or changing the status of any student request.\n"
        "- **Human Authority**: All formal student requests (Bonafide certificates, leaves, OD permissions, lab compute, and exemptions) require manual evaluation and digital sign-off by authorized department Faculty Advisors or Administrators.\n"
        "- **Portal Access**: Students submit and track requests at the Student Portal (`/student/requests`). Faculty review and approve requests at the Faculty Portal (`/faculty/dashboard` or `/admin`)."
    )

    # 2. Check personal request tracking if requested
    tracked_requests_text = ""
    if action == "track_status" and user_id:
        try:
            user_reqs = db_service.get_student_requests(student_id=str(user_id))
            if user_reqs:
                tracked_requests_text = "### Your Active Department Requests on Record:\n"
                for r in user_reqs[:4]:
                    tracked_requests_text += (
                        f"- **Request ID**: `{r.get('id')}`\n"
                        f"  - **Type**: {r.get('request_type')}\n"
                        f"  - **Status**: **{r.get('status')}**\n"
                        f"  - **Description**: {r.get('description', '')[:100]}...\n"
                        f"  - **Reviewer**: {r.get('assigned_reviewer_name') or 'Pending Faculty Assignment'}\n"
                        f"  - **Remarks**: {r.get('remarks') or 'None yet'}\n"
                    )
            else:
                tracked_requests_text = "You currently have no active requests recorded under your user profile. You can submit one on the `/student/requests` page."
        except Exception as e:
            print(f"[Request Assistance Tool] Error querying user requests: {e}")

    # 3. Assemble Specific Request Type Guidelines
    type_details_text = ""
    if req_type and req_type in REQUEST_TYPES_INFO:
        info = REQUEST_TYPES_INFO[req_type]
        type_details_text = (
            f"### Official Department Guidelines: {req_type}\n"
            f"- **Purpose**: {info['purpose']}\n"
            f"- **Required Enclosures & Proof**: {info['documents']}\n"
            f"- **Standard Processing SLA**: {info['sla']}\n"
            f"- **Authorized Reviewing Authority**: {info['reviewer']}\n"
        )
    else:
        # General list of available request types
        type_details_text = "### Available Department Student Request Categories:\n"
        for t_name, t_info in REQUEST_TYPES_INFO.items():
            type_details_text += f"- **{t_name}**: {t_info['purpose']} (Required: {t_info['documents']}; Reviewer: {t_info['reviewer']})\n"

    # 4. Submission & Drafting Instructions
    workflow_steps = (
        "### Standard Submission Workflow:\n"
        "1. **Navigate**: Go to the **Student Requests Portal** (`/student/requests`).\n"
        "2. **Select Category**: Pick the appropriate request category from the dropdown.\n"
        "3. **Provide Details**: Enter a clear, detailed justification including dates, reason, and course/lab affected.\n"
        "4. **Attach Documentation**: Bring or upload required physical/digital proof (e.g. event invite, medical slip).\n"
        "5. **Submit & Track**: Your request enters `Pending` status and is assigned to your faculty advisor. You will receive real-time status updates (`Under Review`, `Approved`, `Rejected`, or `More Information Required`)."
    )

    drafting_template = (
        "### Sample Drafting Template for Student Requests:\n"
        "```text\n"
        "Subject: Request for [Request Type] - [Student Name] ([Enrollment No])\n\n"
        "Respected [Faculty Advisor / Head of Department],\n\n"
        "I am writing to formally request [Request Type] for the following purpose: [State Reason].\n"
        "- Relevant Dates: [Start Date] to [End Date]\n"
        "- Affected Course(s) / Lab: [e.g. AI401 Machine Learning / AI Lab 401]\n"
        "- Justification: [Clear explanation of why this request is necessary]\n"
        "- Enclosed Documents: [Medical certificate / Event invitation letter / Project Synopsis]\n\n"
        "I assure that I will make up for any missed coursework and adhere to department regulations.\n\n"
        "Sincerely,\n"
        "[Student Full Name] - [Roll / Enrollment No]\n"
        "[Department & Section]\n"
        "```"
    )

    # Combine content chunks
    full_content = f"{governance_notice}\n\n{type_details_text}\n\n{workflow_steps}"
    if action == "draft_request":
        full_content += f"\n\n{drafting_template}"
    if tracked_requests_text:
        full_content += f"\n\n{tracked_requests_text}"

    context.append({
        "tool": "request_assistance_tool",
        "source": "AIDA Department Student Request Governance System",
        "action": action,
        "request_type": req_type,
        "can_ai_approve_asked": can_ai_approve,
        "content": full_content
    })

    sources.append({
        "doc": "Student Request Governance & Workflow",
        "page": "Department Portal (/student/requests)"
    })

    return {"context": context, "sources": sources}

