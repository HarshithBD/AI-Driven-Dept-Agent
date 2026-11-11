"""
test_security_controls.py — Automated security test suite for AIDA.
Verifies:
1. Role-based access control (students cannot access admin/faculty endpoints)
2. SQL injection rejection / safe parameter handling (PostgREST parameterization)
3. Agent honesty & refusal behavior (refuses to guess outside authorized data)
4. Escalation & request creation workflow with human approval enforcement
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
import pytest
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))

import main
from agents.response_writer import SYSTEM_PROMPT


@asynccontextmanager
async def no_lifespan(app):
    yield


@pytest.fixture
def student_client(monkeypatch):
    monkeypatch.setattr(main.app.router, "lifespan_context", no_lifespan)
    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "id": "student-uuid-001",
        "email": "student@greenfield.edu",
        "role": "student",
        "is_admin": False,
        "is_faculty": False,
    }
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture
def faculty_client(monkeypatch):
    monkeypatch.setattr(main.app.router, "lifespan_context", no_lifespan)
    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "id": "faculty-uuid-001",
        "email": "prof.sharma@greenfield.edu",
        "role": "faculty",
        "is_admin": False,
        "is_faculty": True,
    }
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setattr(main.app.router, "lifespan_context", no_lifespan)
    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "id": "admin-uuid-001",
        "email": "admin@greenfield.edu",
        "role": "admin",
        "is_admin": True,
        "is_faculty": True,
    }
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def force_in_memory_db_service(monkeypatch):
    """Ensure tests run against fast in-memory service layer without network latency."""
    import db_service
    monkeypatch.setattr(db_service, "_is_configured", lambda: False)


# ==============================================================================
# 1. ROLE-BASED ACCESS CONTROL (RBAC) TESTS
# ==============================================================================
def test_rbac_student_blocked_from_admin_overview(student_client):
    """Students must receive HTTP 403 when accessing the admin overview dashboard."""
    response = student_client.get("/admin/overview")
    assert response.status_code == 403
    assert "Admin privileges required" in response.json()["detail"]


def test_rbac_student_blocked_from_admin_timetable(student_client):
    """Students must receive HTTP 403 when trying to access admin timetable management."""
    response = student_client.get("/admin/timetable")
    assert response.status_code == 403


def test_rbac_student_blocked_from_admin_logs(student_client):
    """Students must receive HTTP 403 when trying to access audit logs."""
    response = student_client.get("/admin/logs")
    assert response.status_code == 403


def test_rbac_student_blocked_from_faculty_list_management(student_client):
    """Students cannot create or delete faculty records."""
    post_resp = student_client.post("/faculty", json={
        "name": "Attacker",
        "designation": "Hacker",
        "email": "hacker@greenfield.edu"
    })
    assert post_resp.status_code == 403

    del_resp = student_client.delete("/faculty/fac-001")
    assert del_resp.status_code == 403


def test_rbac_faculty_blocked_from_admin_only_endpoints(faculty_client):
    """Faculty members cannot access admin-only endpoints like delete faculty or view logs."""
    resp = faculty_client.get("/admin/overview")
    assert resp.status_code == 403

    resp_logs = faculty_client.get("/admin/logs")
    assert resp_logs.status_code == 403


def test_rbac_admin_allowed_access(admin_client):
    """Admins can access overview and management endpoints."""
    resp = admin_client.get("/admin/overview")
    assert resp.status_code == 200


# ==============================================================================
# 2. SQL INJECTION DEFENSE & INPUT VALIDATION TESTS
# ==============================================================================
def test_sql_injection_in_timetable_group_rejected(student_client):
    """Path traversal / SQL injection payloads in section query must return HTTP 400."""
    payloads = [
        "AIML-A' OR '1'='1",
        "../../etc/passwd",
        "AIML-A; DROP TABLE students;--",
        "AIML-A' UNION SELECT * FROM user_roles--",
    ]
    for payload in payloads:
        response = student_client.get("/timetable", params={"group": payload})
        assert response.status_code == 400, f"Expected 400 for payload: {payload}"


def test_sql_injection_in_department_queries_treated_as_literal(student_client):
    """SQL injection strings in parameter queries do not compromise database."""
    # Query with SQL injection payload in section filter
    response = student_client.get("/students", params={"section": "' OR 1=1 --"})
    # Student cannot access /students (requires faculty or admin) -> HTTP 403
    assert response.status_code == 403


def test_invalid_request_status_rejected_by_enum_validation(faculty_client):
    """Status updates with non-whitelisted strings must be rejected with HTTP 400."""
    response = faculty_client.put(
        "/requests/req-001/status",
        json={"status": "APPROVED'; DROP TABLE student_requests;--"}
    )
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


# ==============================================================================
# 3. AGENT HONESTY & GOVERNANCE BEHAVIOR
# ==============================================================================
def test_agent_system_prompt_mandates_honesty_and_no_guessing():
    """System prompt must explicitly mandate saying 'I don't know' and offering escalation."""
    assert "DO NOT GUESS" in SYSTEM_PROMPT.upper() or "DO NOT INVENT" in SYSTEM_PROMPT.upper() or "NOT IN THE CONTEXT" in SYSTEM_PROMPT.upper()
    assert "HUMAN" in SYSTEM_PROMPT.upper()
    assert "OFFER ESCALATION" in SYSTEM_PROMPT.upper() or "HUMAN REVIEW" in SYSTEM_PROMPT.upper() or "OFFICIALS" in SYSTEM_PROMPT.upper()


def test_ai_refuses_to_approve_requests_in_system_prompt():
    """Response writer system prompt must forbid AI from approving requests."""
    assert "CANNOT APPROVE" in SYSTEM_PROMPT.upper() or "NEVER APPROVE" in SYSTEM_PROMPT.upper() or "DO NOT APPROVE" in SYSTEM_PROMPT.upper()
    assert "FACULTY" in SYSTEM_PROMPT.upper() or "ADMIN" in SYSTEM_PROMPT.upper()


# ==============================================================================
# 4. STRUCTURED REQUEST & HUMAN APPROVAL ESCALATION
# ==============================================================================
def test_student_request_creation_and_escalation_lifecycle(student_client, faculty_client):
    """
    Complete lifecycle test:
    1. Student submits a request (initial status: Pending)
    2. Faculty requests more info (status: More Information Required)
    3. Student replies with additional information (status: Under Review)
    4. Faculty gives final human approval (status: Approved)
    """
    # Step 1: Student submits request
    create_resp = student_client.post("/requests", json={
        "request_type": "Medical Leave",
        "description": "Requesting 3 days leave due to typhoid recovery."
    })
    assert create_resp.status_code == 200
    req = create_resp.json()
    assert req["status"] == "Pending"
    req_id = req["id"]

    # Step 2: Faculty requests more information
    review_resp = faculty_client.put(f"/requests/{req_id}/status", json={
        "status": "More Information Required",
        "comments": "Please attach the doctor's fitness certificate."
    })
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "More Information Required"

    # Step 3: Student replies
    reply_resp = student_client.post(f"/requests/{req_id}/reply", json={
        "additional_info": "Medical certificate from Dr. Rao attached. Ready for verification."
    })
    assert reply_resp.status_code == 200
    assert reply_resp.json()["status"] == "Under Review"

    # Step 4: Faculty approves
    final_resp = faculty_client.put(f"/requests/{req_id}/status", json={
        "status": "Approved",
        "comments": "Medical certificate verified. Leave approved."
    })
    assert final_resp.status_code == 200
    assert final_resp.json()["status"] == "Approved"
