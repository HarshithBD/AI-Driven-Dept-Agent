"""
test_student_requests_unit.py — Comprehensive Unit Tests for Student Request Management & Human Approval System.

Tests:
1. Student Request Creation with initial status 'Pending' and initial audit history.
2. Status queries and user-specific retrieval.
3. Faculty / Admin status updates:
   - 'Under Review'
   - 'More Information Required'
   - 'Approved'
   - 'Rejected'
4. Student reply loop for 'More Information Required':
   - Adds reply
   - Transitions back to 'Under Review'
   - Appends audit history record
5. Request history timeline audit trail verification.
6. AI guardrail verification in response_writer.py ensuring AI assistant never approves/rejects requests.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock

# Mock external network and LLM modules if not in test runtime environment
for mod_name in [
    "requests", "langchain", "langchain.schema", "langchain_core", "langchain_core.messages",
    "langchain_core.documents", "langchain_google_genai", "langgraph", "langgraph.graph",
    "langchain_text_splitters", "langchain_huggingface", "langchain_community",
    "langchain_community.embeddings", "langchain_community.embeddings.fastembed",
    "fastmcp", "fastmcp.client", "mcp", "mcp.client", "mcp.client.stdio", "mcp_client",
    "pdfplumber", "docx", "qdrant_client", "rank_bm25", "flashrank",
    "fastembed", "rag", "rag.embeddings", "rag.vectorstore", "rag.pipeline"
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import db_service
from agents.response_writer import SYSTEM_PROMPT


class TestStudentRequestApprovalWorkflow(unittest.TestCase):
    def setUp(self):
        # Sample student payload
        self.test_payload = {
            "user_id": "test-student-uid-999",
            "request_type": "Lab Compute Access",
            "description": "Requesting 40 hours of A100 GPU compute access for Deep Learning Capstone project."
        }

    def test_01_create_student_request(self):
        """Verify request creation produces Pending status and initializes history."""
        created = db_service.create_student_request(self.test_payload)
        self.assertIsNotNone(created)
        self.assertIn("id", created)
        self.assertEqual(created["status"], "Pending")
        self.assertEqual(created["request_type"], "Lab Compute Access")
        self.assertEqual(created["user_id"], "test-student-uid-999")
        
        # Verify initial history
        history = created.get("history", [])
        self.assertTrue(len(history) >= 1)
        self.assertEqual(history[0]["action"], "Request Submitted")
        self.assertEqual(history[0]["to_status"], "Pending")

    def test_02_get_student_requests(self):
        """Verify fetching user requests and all requests."""
        # Create a request
        created = db_service.create_student_request(self.test_payload)
        req_id = created["id"]

        # Fetch for this user
        my_reqs = db_service.get_student_requests(user_id="test-student-uid-999")
        ids = [r["id"] for r in my_reqs]
        self.assertIn(req_id, ids)

        # Fetch by ID
        single = db_service.get_student_request_by_id(req_id)
        self.assertIsNotNone(single)
        self.assertEqual(single["id"], req_id)

    def test_03_faculty_review_more_info_required(self):
        """Verify faculty can move status to 'More Information Required' with comments."""
        created = db_service.create_student_request(self.test_payload)
        req_id = created["id"]

        updated = db_service.update_student_request_status(
            request_id=req_id,
            status="More Information Required",
            comments="Please attach your project proposal and faculty mentor sign-off.",
            actor_name="Dr. Suresh Kumar",
            actor_role="Faculty"
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated["status"], "More Information Required")
        self.assertEqual(updated["comments"], "Please attach your project proposal and faculty mentor sign-off.")
        
        # Verify history appended
        history = updated.get("history", [])
        self.assertEqual(len(history), 2)
        latest = history[-1]
        self.assertEqual(latest["to_status"], "More Information Required")
        self.assertEqual(latest["actor_name"], "Dr. Suresh Kumar")
        self.assertIn("Please attach your project proposal", latest["comments"])

    def test_04_student_reply_transitions_back_to_under_review(self):
        """Verify student replying to 'More Information Required' transitions request to 'Under Review'."""
        created = db_service.create_student_request(self.test_payload)
        req_id = created["id"]

        # 1. Faculty requests more info
        db_service.update_student_request_status(
            request_id=req_id,
            status="More Information Required",
            comments="Please provide the dataset size and GPU hours estimate.",
            actor_name="Dr. Suresh Kumar",
            actor_role="Faculty"
        )

        # 2. Student replies
        replied = db_service.add_student_request_reply(
            request_id=req_id,
            user_id="test-student-uid-999",
            additional_info="Dataset is 50GB ImageNet subset, estimated at 35 GPU hours total.",
            actor_name="Aditya Verma"
        )

        self.assertIsNotNone(replied)
        self.assertEqual(replied["status"], "Under Review")
        
        # Verify history contains the student reply record
        history = replied.get("history", [])
        self.assertEqual(len(history), 3)
        student_action = history[-1]
        self.assertEqual(student_action["action"], "Student Provided Additional Information")
        self.assertEqual(student_action["from_status"], "More Information Required")
        self.assertEqual(student_action["to_status"], "Under Review")
        self.assertIn("50GB ImageNet subset", student_action["comments"])

    def test_05_faculty_final_approval(self):
        """Verify human approval sets status to 'Approved' with audit remarks."""
        created = db_service.create_student_request(self.test_payload)
        req_id = created["id"]

        approved = db_service.update_student_request_status(
            request_id=req_id,
            status="Approved",
            comments="Granted 40 hours access on Node-GPU-02. Credentials dispatched to university email.",
            actor_name="Dr. Suresh Kumar",
            actor_role="Faculty"
        )

        self.assertEqual(approved["status"], "Approved")
        history = approved.get("history", [])
        self.assertEqual(history[-1]["to_status"], "Approved")
        self.assertEqual(history[-1]["action"], "Status changed to Approved")

    def test_06_human_rejection(self):
        """Verify human rejection sets status to 'Rejected' with reason."""
        created = db_service.create_student_request(self.test_payload)
        req_id = created["id"]

        rejected = db_service.update_student_request_status(
            request_id=req_id,
            status="Rejected",
            comments="Requested resource quota exceeds lab semester allocation.",
            actor_name="Admin Office",
            actor_role="Administrator"
        )

        self.assertEqual(rejected["status"], "Rejected")
        history = rejected.get("history", [])
        self.assertEqual(history[-1]["to_status"], "Rejected")
        self.assertEqual(history[-1]["actor_role"], "Administrator")

    def test_07_ai_guardrail_prevents_automatic_decisions(self):
        """
        CRITICAL REQUIREMENT:
        The AI assistant may help a student understand the request process or help draft a request,
        but the AI must never automatically approve or reject a sensitive request.
        Only an authorized human faculty member or administrator can make the final decision.
        """
        prompt_lower = SYSTEM_PROMPT.lower()
        self.assertIn("human approval", prompt_lower)
        self.assertIn("must never approve, reject", prompt_lower)
        self.assertIn("faculty members or department administrators", prompt_lower)


if __name__ == "__main__":
    unittest.main()
