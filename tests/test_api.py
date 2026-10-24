"""
Unit and Integration Tests for AutoRoster MVP HTTP Handler.
Simulates HTTP requests in-memory without OS socket permission restrictions.
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

class TestAutoRosterAPI(unittest.TestCase):

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

        # Parse response header and body
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

    def test_01_employees_endpoints(self):
        """Test listing seed employees, adding new employee, and validation."""
        code, data = self._call("GET", "/api/employees")
        self.assertEqual(code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 8)

        # Add valid employee
        code, add_res = self._call("POST", "/api/employees", {
            "name": "Jordan Bell",
            "skills": ["Barista", "Cashier"],
            "max_weekly_hours": 32,
            "email": "jordan@vibecafe.com"
        })
        self.assertEqual(code, 201)
        self.assertTrue(add_res["success"])
        self.assertEqual(add_res["data"]["name"], "Jordan Bell")

        # Test validation error (empty name)
        code, err_res = self._call("POST", "/api/employees", {
            "name": "",
            "skills": ["Cook"]
        })
        self.assertEqual(code, 400)
        self.assertFalse(err_res["success"])
        self.assertIn("cannot be empty", err_res["error"])

    def test_02_ai_parser_and_leave_workflow(self):
        """Test messy message parser, approval workflow, and rejected status."""
        text = "Hey boss, sister is getting married next week, so I cannot work Friday evening. Thanks!"
        code, parse_res = self._call("POST", "/api/leaves/parse", {"text": text})
        self.assertEqual(code, 200)
        self.assertTrue(parse_res["success"])
        self.assertEqual(parse_res["data"]["day_of_week"], "Friday")
        self.assertEqual(parse_res["data"]["shift_type"], "Evening")

        # Submit request
        code, leave_res = self._call("POST", "/api/leaves", {
            "employee_id": "emp-1",
            "raw_text": text,
            "day_of_week": parse_res["data"]["day_of_week"],
            "shift_type": parse_res["data"]["shift_type"],
            "reason": parse_res["data"]["reason"]
        })
        self.assertEqual(code, 201)
        leave_id = leave_res["data"]["id"]

        # Approve leave
        code, app_res = self._call("POST", f"/api/leaves/{leave_id}/status", {"status": "APPROVED"})
        self.assertEqual(code, 200)
        self.assertEqual(app_res["data"]["status"], "APPROVED")

    def test_03_generate_roster_and_impossible_scenario(self):
        """Test roster generation and impossible scenario conflict diagnosis."""
        code, gen_res = self._call("POST", "/api/roster/generate", {})
        self.assertEqual(code, 200)
        self.assertEqual(gen_res["data"]["status"], "SUCCESS")
        self.assertEqual(len(gen_res["data"]["slots"]), 32)

        # Trigger impossible scenario
        code, imp_res = self._call("POST", "/api/roster/load-impossible", {})
        self.assertEqual(code, 200)
        self.assertEqual(imp_res["data"]["status"], "INFEASIBLE")
        self.assertTrue(len(imp_res["data"]["conflicts"]) > 0)
        self.assertIn("Supervisor", imp_res["data"]["conflicts"][0]["title"])

    def test_04_mark_absent_and_replacements(self):
        """Test marking staff absent and getting ranked replacements."""
        # Generate roster
        self._call("POST", "/api/roster/generate", {})
        # Mark slot absent
        code, abs_res = self._call("POST", "/api/roster/mark-absent", {
            "slot_id": "slot-1",
            "reason": "Sudden migraine call-out"
        })
        self.assertEqual(code, 200)
        self.assertTrue(abs_res["data"]["is_absent"])

        # Fetch replacements
        code, repl_res = self._call("GET", "/api/roster/replacements?slot_id=slot-1")
        self.assertEqual(code, 200)
        self.assertTrue(repl_res["data"]["eligible_count"] > 0)
        top_cand = repl_res["data"]["eligible"][0]
        self.assertEqual(top_cand["rank"], 1)

        # Assign replacement
        code, assign_res = self._call("POST", "/api/roster/assign-replacement", {
            "slot_id": "slot-1",
            "replacement_emp_id": top_cand["employee_id"]
        })
        self.assertEqual(code, 200)
        self.assertEqual(assign_res["data"]["replaced_by_id"], top_cand["employee_id"])

if __name__ == "__main__":
    unittest.main()
