import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


@asynccontextmanager
async def no_lifespan(app):
    yield


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "TIMETABLE_DATA_DIR", tmp_path)
    monkeypatch.setattr(main.app.router, "lifespan_context", no_lifespan)
    main.app.dependency_overrides[main.get_current_user] = lambda: {
        "id": "test-student",
        "email": "student@example.com",
        "role": "student",
        "is_admin": False,
        "is_faculty": False,
    }
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()


def test_student_can_read_section_timetable(client, tmp_path):
    (tmp_path / "timetable.csv").write_text(
        "day,time,course_id,student_group\n"
        "Monday,08:00,AI401,AIML-A\n"
        "Monday,09:00,AI402,AIML-B\n",
        encoding="utf-8",
    )

    response = client.get("/timetable", params={"group": "AIML-A"})

    assert response.status_code == 200
    assert response.json() == [
        {"day": "Monday", "time": "08:00", "course_id": "AI401", "student_group": "AIML-A"}
    ]


def test_student_timetable_rejects_invalid_section(client):
    response = client.get("/timetable", params={"group": "../secrets"})

    assert response.status_code == 400


def test_student_can_read_deadlines_but_not_admin_deadline_management(client, tmp_path):
    (tmp_path / "deadlines.csv").write_text(
        "course_id,title,due_date\nAI401,Assignment,2026-12-01\n",
        encoding="utf-8",
    )

    response = client.get("/deadlines")
    admin_response = client.get("/admin/deadlines")

    assert response.status_code == 200
    assert response.json() == [
        {"course_id": "AI401", "title": "Assignment", "due_date": "2026-12-01"}
    ]
    assert admin_response.status_code == 403
