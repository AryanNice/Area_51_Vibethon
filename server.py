"""
AutoRoster MVP REST API Server.
Built with Python standard library http.server.
Zero external dependencies. Never leaks raw stack traces.
"""
import http.server
import socketserver
import json
import urllib.parse
import os
import sys
from typing import Dict, Any

from app.database import db
from app.solver import solve_roster
from app.ai_parser import parse_free_text_availability
from app.replacement import get_ranked_replacements
from app.seed_data import SAMPLE_MESSY_MESSAGES
from app.models import AVAILABLE_SKILLS

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
PORT = 8000

class AutoRosterHandler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        # Clean formatted logging without raw clutter
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def _send_json(self, data: Any, status: int = 200):
        try:
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            # Safe fallback if connection dropped
            pass

    def _send_error(self, message: str, status: int = 400):
        # Friendly error payload - NEVER a raw stack trace
        self._send_json({
            "success": False,
            "error": message
        }, status=status)

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError("Malformed JSON body submitted.")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        # Static assets
        if path == "/" or path == "/index.html":
            self._serve_static_file("index.html", "text/html; charset=utf-8")
            return
        elif path == "/styles.css":
            self._serve_static_file("styles.css", "text/css; charset=utf-8")
            return
        elif path == "/app.js":
            self._serve_static_file("app.js", "application/javascript; charset=utf-8")
            return

        # API Routes
        try:
            if path == "/api/employees":
                employees = [e.to_dict() for e in db.get_employees()]
                self._send_json({
                    "success": True,
                    "data": employees,
                    "available_skills": AVAILABLE_SKILLS
                })
            elif path == "/api/leaves":
                leaves = [lr.to_dict() for lr in db.get_leave_requests()]
                self._send_json({
                    "success": True,
                    "data": leaves,
                    "sample_messages": SAMPLE_MESSY_MESSAGES
                })
            elif path == "/api/roster":
                result = db.get_roster_result()
                self._send_json({
                    "success": True,
                    "data": result
                })
            elif path == "/api/roster/replacements":
                slot_id = query.get("slot_id", [None])[0]
                if not slot_id:
                    self._send_error("Missing required query parameter: slot_id")
                    return
                # Find slot
                target_slot = None
                for s in db.current_roster:
                    if s.id == slot_id:
                        target_slot = s
                        break
                if not target_slot:
                    self._send_error(f"Slot with ID '{slot_id}' not found in active roster.", 404)
                    return

                res = get_ranked_replacements(
                    slot=target_slot,
                    employees=db.get_employees(),
                    current_roster=db.current_roster,
                    approved_leaves=db.get_approved_leaves()
                )
                self._send_json({
                    "success": True,
                    "data": res
                })
            elif path == "/api/health":
                self._send_json({"status": "ok", "app": "AutoRoster MVP", "version": "1.0.0"})
            else:
                self._send_error(f"Endpoint not found: {path}", 404)
        except Exception as e:
            self._send_error(f"Unable to process request: {str(e)}", 500)

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        try:
            body = self._read_json_body()

            if path == "/api/employees":
                name = body.get("name", "").strip()
                skills = body.get("skills", [])
                max_hours = body.get("max_weekly_hours", 40)
                if not name:
                    self._send_error("Employee name cannot be empty.")
                    return
                if not skills:
                    self._send_error("Please select at least one skill.")
                    return
                emp = db.add_employee(
                    name=name,
                    skills=skills,
                    max_weekly_hours=max_hours,
                    email=body.get("email", ""),
                    phone=body.get("phone", "")
                )
                self._send_json({"success": True, "data": emp.to_dict()}, 201)

            elif path == "/api/employees/reset":
                db.reset_to_seed()
                self._send_json({
                    "success": True,
                    "message": "Reset all employees, requests, and schedules to initial seed data."
                })

            elif path == "/api/leaves/parse":
                text = body.get("text", "").strip()
                if not text:
                    self._send_error("Message text is required for AI parsing.")
                    return
                emp_list = [e.to_dict() for e in db.get_employees()]
                parsed = parse_free_text_availability(text, emp_list)
                self._send_json({"success": True, "data": parsed})

            elif path == "/api/leaves":
                emp_id = body.get("employee_id")
                raw_text = body.get("raw_text", "")
                day = body.get("day_of_week")
                shift = body.get("shift_type", "All Day")
                reason = body.get("reason", "Personal Leave")
                confidence = float(body.get("confidence", 1.0))
                explanation = body.get("explanation", "")

                if not emp_id:
                    self._send_error("Please select an employee.")
                    return
                if not day:
                    self._send_error("Please specify a day of the week.")
                    return

                lr = db.add_leave_request(
                    employee_id=emp_id,
                    raw_text=raw_text,
                    day_of_week=day,
                    shift_type=shift,
                    reason=reason,
                    confidence=confidence,
                    explanation=explanation
                )
                self._send_json({"success": True, "data": lr.to_dict()}, 201)

            elif path.startswith("/api/leaves/") and path.endswith("/status"):
                parts = path.split("/")
                leave_id = parts[3]
                status = body.get("status", "").upper()
                if status not in ["APPROVED", "REJECTED", "PENDING"]:
                    self._send_error("Invalid status. Must be APPROVED, REJECTED, or PENDING.")
                    return
                updated = db.update_leave_status(leave_id, status)
                if not updated:
                    self._send_error("Leave request not found.", 404)
                    return
                self._send_json({"success": True, "data": updated.to_dict()})

            elif path == "/api/roster/generate":
                result = solve_roster(
                    employees=db.get_employees(),
                    requirements=db.get_shift_requirements(),
                    approved_leaves=db.get_approved_leaves()
                )
                db.set_roster_result(
                    status=result["status"],
                    slots=result.get("slots", []),
                    conflicts=result.get("conflicts", []),
                    stats=result.get("stats", {})
                )
                self._send_json({"success": True, "data": db.get_roster_result()})

            elif path == "/api/roster/load-impossible":
                db.apply_impossible_scenario()
                # Run solver immediately so conflict is shown right away
                result = solve_roster(
                    employees=db.get_employees(),
                    requirements=db.get_shift_requirements(),
                    approved_leaves=db.get_approved_leaves()
                )
                db.set_roster_result(
                    status=result["status"],
                    slots=result.get("slots", []),
                    conflicts=result.get("conflicts", []),
                    stats=result.get("stats", {})
                )
                self._send_json({
                    "success": True,
                    "message": "Impossible scenario injected (All Supervisors on approved leave for Friday Morning).",
                    "data": db.get_roster_result()
                })

            elif path == "/api/roster/mark-absent":
                slot_id = body.get("slot_id")
                reason = body.get("reason", "Call-out / Unplanned absence")
                if not slot_id:
                    self._send_error("Missing slot_id.")
                    return
                updated_slot = db.mark_slot_absent(slot_id, reason)
                if not updated_slot:
                    self._send_error("Slot not found in active roster.", 404)
                    return
                self._send_json({"success": True, "data": updated_slot.to_dict()})

            elif path == "/api/roster/assign-replacement":
                slot_id = body.get("slot_id")
                replacement_emp_id = body.get("replacement_emp_id")
                if not slot_id or not replacement_emp_id:
                    self._send_error("Both slot_id and replacement_emp_id are required.")
                    return
                updated_slot = db.assign_replacement(slot_id, replacement_emp_id)
                if not updated_slot:
                    self._send_error("Unable to assign replacement.", 400)
                    return
                self._send_json({"success": True, "data": updated_slot.to_dict()})

            else:
                self._send_error(f"Endpoint not found: {path}", 404)

        except ValueError as ve:
            self._send_error(str(ve), 400)
        except Exception as e:
            self._send_error(f"Server error: {str(e)}", 500)

    def do_DELETE(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        if path.startswith("/api/employees/"):
            emp_id = path.split("/")[3]
            deleted = db.delete_employee(emp_id)
            if deleted:
                self._send_json({"success": True, "message": f"Employee {emp_id} deleted."})
            else:
                self._send_error(f"Employee {emp_id} not found.", 404)
        else:
            self._send_error(f"Cannot DELETE endpoint: {path}", 404)

    def _serve_static_file(self, filename: str, content_type: str):
        filepath = os.path.join(STATIC_DIR, filename)
        if not os.path.exists(filepath):
            self.send_error(404, f"File {filename} not found.")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

def run_server(port: int = PORT):
    os.makedirs(STATIC_DIR, exist_ok=True)
    server_address = ("", port)
    # Enable SO_REUSEADDR for rapid restarts during development
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, AutoRosterHandler) as httpd:
        print(f"AutoRoster MVP Server running at http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", PORT))
    run_server(port)
