"""
Unit & Integration Tests for Role-Based Portal, Authentication,
AI Pattern Learning & Anti-Exploitation, Urgent Medical Proofs, and Replacement Audits.
"""
import io
import json
import unittest
from server import AutoRosterHandler
from app.database import db

class MockSocket:
    def __init__(self, data: bytes):
        self.rfile = io.BytesIO(data)
        self.buf = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if "r" in mode:
            return self.rfile
        return self.buf

    def sendall(self, data):
        self.buf.write(data)

    def send(self, data):
        self.buf.write(data)
        return len(data)

class TestPortalFeatures(unittest.TestCase):

    def setUp(self):
        db.reset_to_seed()

    def _call(self, method: str, path: str, body: dict = None):
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
        request_lines = [
            f"{method} {path} HTTP/1.1",
            "Host: localhost",
            f"Content-Length: {len(body_bytes)}",
            "Content-Type: application/json",
            "",
            ""
        ]
        raw_request = "\r\n".join(request_lines).encode("utf-8") + body_bytes
        mock_sock = MockSocket(raw_request)
        AutoRosterHandler(mock_sock, ("127.0.0.1", 8000), None)

        raw_response = mock_sock.buf.getvalue()
        parts = raw_response.split(b"\r\n\r\n", 1)
        headers = parts[0].decode("utf-8", errors="ignore")
        status_line = headers.split("\r\n")[0]
        status_code = int(status_line.split(" ")[1])

        body_data = None
        if len(parts) > 1 and parts[1]:
            try:
                body_data = json.loads(parts[1].decode("utf-8"))
            except Exception:
                body_data = parts[1].decode("utf-8")

        return status_code, body_data

    def test_01_authentication_admin_and_employee(self):
        # Admin Login
        code, admin_res = self._call("POST", "/api/auth/login", {
            "email": "admin@vibecafe.com",
            "password": "admin123"
        })
        self.assertEqual(code, 200)
        self.assertTrue(admin_res["success"])
        self.assertEqual(admin_res["data"]["role"], "admin")

        # Employee Login
        code, emp_res = self._call("POST", "/api/auth/login", {
            "email": "alex@vibecafe.com",
            "password": "employee123"
        })
        self.assertEqual(code, 200)
        self.assertTrue(emp_res["success"])
        self.assertEqual(emp_res["data"]["role"], "employee")
        self.assertEqual(emp_res["data"]["name"], "Alex Rivera")

        # Invalid Login
        code, bad_res = self._call("POST", "/api/auth/login", {
            "email": "alex@vibecafe.com",
            "password": "wrongpassword"
        })
        self.assertEqual(code, 401)
        self.assertFalse(bad_res["success"])

    def test_02_ai_leave_request_auto_approval_for_wedding(self):
        code, res = self._call("POST", "/api/employee/leave-request", {
            "employee_id": "emp-1",
            "text": "Hey boss, my sister is getting married on Friday evening, need to attend wedding ceremony.",
            "is_urgent": False
        })
        self.assertEqual(code, 201)
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["ai_decision"], "APPROVED")
        self.assertEqual(res["data"]["status"], "APPROVED")
        self.assertIn("Friday", res["data"]["day_of_week"])
        self.assertLess(res["data"]["exploitation_risk_score"], 0.40)

    def test_03_ai_leave_request_anti_exploitation_rejection(self):
        code, res = self._call("POST", "/api/employee/leave-request", {
            "employee_id": "emp-5",
            "text": "Not feeling like coming in this Friday evening, just want to chill and hangout with the boys.",
            "is_urgent": False
        })
        self.assertEqual(code, 201)
        self.assertTrue(res["success"])
        self.assertEqual(res["data"]["ai_decision"], "REJECTED")
        self.assertEqual(res["data"]["status"], "REJECTED")

    def test_04_urgent_medical_leave_with_proof_and_manager_action(self):
        code, res = self._call("POST", "/api/employee/leave-request", {
            "employee_id": "emp-3",
            "text": "Severe sudden gastroenteritis. Admitted to urgent care clinic.",
            "is_urgent": True,
            "proof_filename": "emergency_clinic_certificate.pdf",
            "proof_data_url": "data:application/pdf;base64,mockproofdata"
        })
        self.assertEqual(code, 201)
        self.assertEqual(res["data"]["ai_decision"], "PENDING_MANAGER")
        leave_id = res["data"]["id"]

        # Check urgent leaves list
        code, urg_list = self._call("GET", "/api/admin/urgent-leaves")
        self.assertEqual(code, 200)
        match = next((u for u in urg_list["data"] if u["id"] == leave_id), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["proof_filename"], "emergency_clinic_certificate.pdf")

        # Manager approves urgent leave
        code, act_res = self._call("POST", f"/api/admin/urgent-leaves/{leave_id}/action", {
            "action": "APPROVE"
        })
        self.assertEqual(code, 200)
        self.assertEqual(act_res["data"]["status"], "APPROVED")

    def test_05_leave_log_and_raw_message_inspection(self):
        code, log_res = self._call("GET", "/api/admin/leave-log")
        self.assertEqual(code, 200)
        self.assertTrue(len(log_res["data"]) >= 2)
        first = log_res["data"][0]
        self.assertIn("raw_text", first)
        self.assertIn("created_at", first)
        self.assertIn("status", first)

    def test_06_replacement_audit_and_employee_personal_roster(self):
        # 1. Generate roster
        self._call("POST", "/api/roster/generate", {})
        # 2. Mark slot-1 absent
        self._call("POST", "/api/roster/mark-absent", {"slot_id": "slot-1"})
        # 3. Get replacements
        code, repl_res = self._call("GET", "/api/roster/replacements?slot_id=slot-1")
        top_cand_id = repl_res["data"]["eligible"][0]["employee_id"]

        # 4. Assign replacement
        code, assign_res = self._call("POST", "/api/roster/assign-replacement", {
            "slot_id": "slot-1",
            "replacement_emp_id": top_cand_id
        })
        self.assertEqual(code, 200)

        # 5. Check replacement audit menu
        code, audit_res = self._call("GET", "/api/admin/replacements-audit")
        self.assertEqual(code, 200)
        self.assertTrue(len(audit_res["data"]) >= 1)
        latest_audit = audit_res["data"][0]
        self.assertEqual(latest_audit["slot_id"], "slot-1")
        self.assertEqual(latest_audit["replaced_by_id"], top_cand_id)

        # 6. Check employee personal roster
        code, my_roster = self._call("GET", f"/api/employee/my-roster?employee_id={top_cand_id}")
        self.assertEqual(code, 200)
        self.assertTrue(my_roster["data"]["extra_shifts_count"] >= 1)
        sub_shift = next((s for s in my_roster["data"]["shifts"] if s["is_replacement_shift"]), None)
        self.assertIsNotNone(sub_shift)

if __name__ == "__main__":
    unittest.main()
