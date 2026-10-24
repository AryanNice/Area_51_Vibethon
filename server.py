"""
FastAPI Server for AI Roster MVP
Supports:
1. Employees & Skills management with pre-loaded seed data
2. Free-text AI leave parsing & Manager approval queue
3. CP-SAT weekly roster generation with conflict diagnosis
4. Absence marking and plain scoring ranked replacement assignment
"""

import sys
from unittest.mock import MagicMock
if "pandas" not in sys.modules:
    sys.modules["pandas"] = MagicMock()

import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os

from solver import RosterSolver, rank_replacements
from ai_parser import parse_leave_message

app = FastAPI(title="AI Roster & Schedule Optimization MVP")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Please check the inputs and retry."}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard shift template (7 days, Morning & Evening = 14 shifts)
STANDARD_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

DEFAULT_SHIFTS = [
    # Monday
    {"id": "mon_morn", "day": "Monday", "name": "Morning", "hours": 8, "required_skill": "Manager", "required_count": 1},
    {"id": "mon_eve", "day": "Monday", "name": "Evening", "hours": 8, "required_skill": "Barista", "required_count": 1},
    # Tuesday
    {"id": "tue_morn", "day": "Tuesday", "name": "Morning", "hours": 8, "required_skill": "Cashier", "required_count": 1},
    {"id": "tue_eve", "day": "Tuesday", "name": "Evening", "hours": 8, "required_skill": "Barista", "required_count": 1},
    # Wednesday
    {"id": "wed_morn", "day": "Wednesday", "name": "Morning", "hours": 8, "required_skill": "Cashier", "required_count": 1},
    {"id": "wed_eve", "day": "Wednesday", "name": "Evening", "hours": 8, "required_skill": "Cook", "required_count": 1},
    # Thursday
    {"id": "thu_morn", "day": "Thursday", "name": "Morning", "hours": 8, "required_skill": "Cashier", "required_count": 1},
    {"id": "thu_eve", "day": "Thursday", "name": "Evening", "hours": 8, "required_skill": "Barista", "required_count": 1},
    # Friday
    {"id": "fri_morn", "day": "Friday", "name": "Morning", "hours": 8, "required_skill": "Cashier", "required_count": 1},
    {"id": "fri_eve", "day": "Friday", "name": "Evening", "hours": 8, "required_skill": "Cook", "required_count": 1},
    # Saturday
    {"id": "sat_morn", "day": "Saturday", "name": "Morning", "hours": 8, "required_skill": "Manager", "required_count": 1},
    {"id": "sat_eve", "day": "Saturday", "name": "Evening", "hours": 8, "required_skill": "Barista", "required_count": 1},
    # Sunday
    {"id": "sun_morn", "day": "Sunday", "name": "Morning", "hours": 8, "required_skill": "Cashier", "required_count": 1},
    {"id": "sun_eve", "day": "Sunday", "name": "Evening", "hours": 8, "required_skill": "Barista", "required_count": 1},
]

AVAILABLE_SKILLS = ["Manager", "Barista", "Cashier", "Cook", "Kitchen"]

# Seed Employees
INITIAL_EMPLOYEES = [
    {"id": "emp_1", "name": "Alice Chen", "skills": ["Cashier", "Manager"], "max_hours": 40},
    {"id": "emp_2", "name": "Bob Smith", "skills": ["Barista", "Cashier"], "max_hours": 40},
    {"id": "emp_3", "name": "Charlie Davis", "skills": ["Cook", "Kitchen"], "max_hours": 32},
    {"id": "emp_4", "name": "Diana Prince", "skills": ["Barista", "Manager"], "max_hours": 24},
    {"id": "emp_5", "name": "Evan Wright", "skills": ["Cook", "Cashier"], "max_hours": 40},
    {"id": "emp_6", "name": "Fiona Gallagher", "skills": ["Cashier", "Barista"], "max_hours": 40},
]

# State store
STATE = {
    "employees": list(INITIAL_EMPLOYEES),
    "shifts": list(DEFAULT_SHIFTS),
    "leaves": [
        {
            "id": "leave_seed_1",
            "employee_id": "emp_1",
            "employee_name": "Alice Chen",
            "day": "Tuesday",
            "shift": "All Day",
            "reason": "Dentist appointment",
            "raw_text": "Hey boss, Tuesday I have a dentist appointment all day.",
            "status": "approved"
        }
    ],
    "roster": [],
    "roster_feasible": True,
    "roster_conflicts": [],
    "employee_stats": {}
}


# Pydantic schemas
class EmployeeCreate(BaseModel):
    name: str
    skills: List[str]
    max_hours: int = 40

class ParseLeaveRequest(BaseModel):
    text: str
    sender_id: Optional[str] = None

class LeaveSubmitRequest(BaseModel):
    employee_id: str
    days: List[str]
    shift: str = "All Day"
    reason: str
    raw_text: str = ""

class LeaveActionRequest(BaseModel):
    action: str  # "approve" or "reject"

class MarkAbsentRequest(BaseModel):
    shift_id: str
    employee_id: str

class AssignReplacementRequest(BaseModel):
    shift_id: str
    replacement_employee_id: str


@app.get("/api/data")
def get_all_data():
    return {
        "employees": STATE["employees"],
        "available_skills": AVAILABLE_SKILLS,
        "shifts": STATE["shifts"],
        "leaves": STATE["leaves"],
        "roster": STATE["roster"],
        "roster_feasible": STATE["roster_feasible"],
        "roster_conflicts": STATE["roster_conflicts"],
        "employee_stats": STATE["employee_stats"]
    }


@app.post("/api/employees")
def add_employee(emp: EmployeeCreate):
    if not emp.name.strip():
        raise HTTPException(status_code=400, detail="Employee name cannot be empty")
    new_emp = {
        "id": f"emp_{uuid.uuid4().hex[:6]}",
        "name": emp.name.strip(),
        "skills": emp.skills,
        "max_hours": max(8, emp.max_hours)
    }
    STATE["employees"].append(new_emp)
    return {"message": "Employee added successfully", "employee": new_emp}


@app.delete("/api/employees/{emp_id}")
def delete_employee(emp_id: str):
    STATE["employees"] = [e for e in STATE["employees"] if e["id"] != emp_id]
    STATE["leaves"] = [l for l in STATE["leaves"] if l["employee_id"] != emp_id]
    return {"message": "Employee deleted"}


@app.post("/api/leave/parse")
def parse_leave(req: ParseLeaveRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Message text is required")
    parsed = parse_leave_message(req.text, STATE["employees"], req.sender_id)
    return parsed


@app.post("/api/leave/submit")
def submit_leave(req: LeaveSubmitRequest):
    emp = next((e for e in STATE["employees"] if e["id"] == req.employee_id), None)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    created_leaves = []
    # If multiple days, create a record per day for clean solver constraints
    for day in req.days:
        leave_entry = {
            "id": f"leave_{uuid.uuid4().hex[:6]}",
            "employee_id": req.employee_id,
            "employee_name": emp["name"],
            "day": day,
            "shift": req.shift,
            "reason": req.reason,
            "raw_text": req.raw_text,
            "status": "pending"
        }
        STATE["leaves"].append(leave_entry)
        created_leaves.append(leave_entry)

    return {"message": "Leave request submitted for approval", "leaves": created_leaves}


@app.post("/api/leave/{leave_id}/action")
def take_leave_action(leave_id: str, req: LeaveActionRequest):
    leave = next((l for l in STATE["leaves"] if l["id"] == leave_id), None)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")

    action = req.action.lower()
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    leave["status"] = "approved" if action == "approve" else "rejected"
    return {"message": f"Leave request {leave['status']}", "leave": leave}


@app.post("/api/roster/generate")
def generate_roster():
    solver = RosterSolver(STATE["employees"], STATE["shifts"], STATE["leaves"])
    result = solver.solve()

    STATE["roster_feasible"] = result["feasible"]
    STATE["roster"] = result["assignments"]
    STATE["roster_conflicts"] = result["conflicts"]
    STATE["employee_stats"] = result.get("employee_stats", {})

    return {
        "feasible": result["feasible"],
        "status": result["status"],
        "assignments_count": len(result["assignments"]),
        "conflicts": result["conflicts"],
        "assignments": result["assignments"],
        "employee_stats": result.get("employee_stats", {})
    }


@app.post("/api/roster/simulate-impossible")
def simulate_impossible():
    """
    Creates an impossible conflict scenario to demonstrate conflict detection:
    Approved leaves for ALL managers on Saturday Morning shift.
    """
    managers = [e for e in STATE["employees"] if "Manager" in e.get("skills", [])]
    for m in managers:
        # Check if already has leave on Saturday
        has_leave = any(
            l["employee_id"] == m["id"] and l["day"] == "Saturday" and l["shift"] in ["Morning", "All Day"]
            for l in STATE["leaves"]
        )
        if not has_leave:
            STATE["leaves"].append({
                "id": f"leave_imp_{uuid.uuid4().hex[:6]}",
                "employee_id": m["id"],
                "employee_name": m["name"],
                "day": "Saturday",
                "shift": "Morning",
                "reason": "Simulated Leave (Wedding / Conference)",
                "raw_text": f"Simulated leave: {m['name']} unavailable Saturday Morning",
                "status": "approved"
            })

    # Run solver immediately
    return generate_roster()


@app.post("/api/roster/mark-absent")
def mark_absent(req: MarkAbsentRequest):
    # Find the shift assignment
    assignment = next(
        (a for a in STATE["roster"] if a["shift_id"] == req.shift_id and a["employee_id"] == req.employee_id),
        None
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found in current roster")

    shift_info = next((s for s in STATE["shifts"] if s["id"] == req.shift_id), None)
    if not shift_info:
        raise HTTPException(status_code=404, detail="Shift not found")

    target_shift = {
        "shift_id": req.shift_id,
        "day": shift_info["day"],
        "shift_name": shift_info["name"],
        "hours": shift_info.get("hours", 8),
        "required_skill": shift_info.get("required_skill")
    }

    # Run ranking
    ranked = rank_replacements(
        target_shift,
        req.employee_id,
        STATE["employees"],
        STATE["roster"],
        STATE["leaves"]
    )

    return {
        "absent_employee_id": req.employee_id,
        "absent_employee_name": assignment["employee_name"],
        "shift": target_shift,
        "ranked_replacements": ranked
    }


@app.post("/api/roster/assign-replacement")
def assign_replacement(req: AssignReplacementRequest):
    # Find assignment
    assignment = next((a for a in STATE["roster"] if a["shift_id"] == req.shift_id), None)
    if not assignment:
        raise HTTPException(status_code=404, detail="Shift assignment not found")

    replacement_emp = next((e for e in STATE["employees"] if e["id"] == req.replacement_employee_id), None)
    if not replacement_emp:
        raise HTTPException(status_code=404, detail="Replacement employee not found")

    old_emp_name = assignment["employee_name"]
    assignment["employee_id"] = replacement_emp["id"]
    assignment["employee_name"] = replacement_emp["name"]
    assignment["was_replaced"] = True
    assignment["replaced_from"] = old_emp_name

    # Recalculate stats
    stats = {
        e["id"]: {"assigned_hours": 0, "max_hours": e["max_hours"], "shifts_count": 0, "shifts": []}
        for e in STATE["employees"]
    }
    for a in STATE["roster"]:
        eid = a["employee_id"]
        if eid in stats:
            stats[eid]["assigned_hours"] += int(a.get("hours", 8))
            stats[eid]["shifts_count"] += 1
            stats[eid]["shifts"].append(a["shift_id"])

    STATE["employee_stats"] = stats

    return {
        "message": f"Successfully replaced {old_emp_name} with {replacement_emp['name']}",
        "roster": STATE["roster"],
        "employee_stats": STATE["employee_stats"]
    }


@app.post("/api/reset")
def reset_to_seed():
    STATE["employees"] = [dict(e) for e in INITIAL_EMPLOYEES]
    STATE["shifts"] = [dict(s) for s in DEFAULT_SHIFTS]
    STATE["leaves"] = [
        {
            "id": "leave_seed_1",
            "employee_id": "emp_1",
            "employee_name": "Alice Chen",
            "day": "Tuesday",
            "shift": "All Day",
            "reason": "Dentist appointment",
            "raw_text": "Hey boss, Tuesday I have a dentist appointment all day.",
            "status": "approved"
        }
    ]
    STATE["roster"] = []
    STATE["roster_feasible"] = True
    STATE["roster_conflicts"] = []
    STATE["employee_stats"] = {}
    return {"message": "Reset to seed data complete"}


# Mount static files
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"status": "Backend running. Frontend index.html not yet created."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
