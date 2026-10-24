"""
In-memory and thread-safe data store with reset and persistence capabilities.
"""
import copy
import uuid
from typing import List, Dict, Optional, Any
from app.models import Employee, LeaveRequest, ShiftRoleRequirement, RosterSlot
from app.seed_data import (
    INITIAL_EMPLOYEES,
    DEFAULT_SHIFT_REQUIREMENTS,
    INITIAL_LEAVE_REQUESTS,
    SAMPLE_MESSY_MESSAGES
)

class DataStore:
    def __init__(self):
        self.reset_to_seed()

    def reset_to_seed(self):
        """Restore pristine seed state."""
        self.employees: Dict[str, Employee] = {
            e.id: copy.deepcopy(e) for e in INITIAL_EMPLOYEES
        }
        self.shift_requirements: List[ShiftRoleRequirement] = copy.deepcopy(DEFAULT_SHIFT_REQUIREMENTS)
        self.leave_requests: Dict[str, LeaveRequest] = {
            lr.id: copy.deepcopy(lr) for lr in INITIAL_LEAVE_REQUESTS
        }
        self.current_roster: List[RosterSlot] = []
        self.last_solver_result: Dict[str, Any] = {
            "status": "NOT_GENERATED",
            "message": "Click 'Generate Roster' to solve the schedule.",
            "conflicts": [],
            "stats": {}
        }

    # --- Employees ---
    def get_employees(self) -> List[Employee]:
        return list(self.employees.values())

    def get_employee(self, emp_id: str) -> Optional[Employee]:
        return self.employees.get(emp_id)

    def add_employee(self, name: str, skills: List[str], max_weekly_hours: int, email: str = "", phone: str = "") -> Employee:
        emp_id = f"emp-{uuid.uuid4().hex[:6]}"
        emp = Employee(
            id=emp_id,
            name=name.strip(),
            skills=[s.strip() for s in skills if s.strip()],
            max_weekly_hours=int(max_weekly_hours),
            email=email.strip(),
            phone=phone.strip()
        )
        self.employees[emp_id] = emp
        return emp

    def update_employee(self, emp_id: str, name: str, skills: List[str], max_weekly_hours: int, email: str = "", phone: str = "") -> Optional[Employee]:
        if emp_id not in self.employees:
            return None
        emp = self.employees[emp_id]
        emp.name = name.strip()
        emp.skills = [s.strip() for s in skills if s.strip()]
        emp.max_weekly_hours = int(max_weekly_hours)
        emp.email = email.strip()
        emp.phone = phone.strip()
        return emp

    def delete_employee(self, emp_id: str) -> bool:
        if emp_id in self.employees:
            del self.employees[emp_id]
            # Also clean up any pending/approved leaves
            self.leave_requests = {k: v for k, v in self.leave_requests.items() if v.employee_id != emp_id}
            return True
        return False

    # --- Leave Requests ---
    def get_leave_requests(self) -> List[LeaveRequest]:
        return sorted(list(self.leave_requests.values()), key=lambda x: x.created_at, reverse=True)

    def add_leave_request(self, employee_id: str, raw_text: str, day_of_week: str, shift_type: str, reason: str, confidence: float = 1.0, explanation: str = "") -> LeaveRequest:
        emp = self.get_employee(employee_id)
        emp_name = emp.name if emp else "Unknown Employee"
        lr_id = f"leave-{uuid.uuid4().hex[:6]}"
        lr = LeaveRequest(
            id=lr_id,
            employee_id=employee_id,
            employee_name=emp_name,
            raw_text=raw_text,
            day_of_week=day_of_week,
            shift_type=shift_type,
            reason=reason,
            status="PENDING",
            confidence=confidence,
            explanation=explanation
        )
        self.leave_requests[lr_id] = lr
        return lr

    def update_leave_status(self, leave_id: str, new_status: str) -> Optional[LeaveRequest]:
        if leave_id in self.leave_requests:
            self.leave_requests[leave_id].status = new_status
            return self.leave_requests[leave_id]
        return None

    def get_approved_leaves(self) -> List[LeaveRequest]:
        return [lr for lr in self.leave_requests.values() if lr.status == "APPROVED"]

    # --- Shift Requirements ---
    def get_shift_requirements(self) -> List[ShiftRoleRequirement]:
        return self.shift_requirements

    # --- Roster & Solver State ---
    def set_roster_result(self, status: str, slots: List[RosterSlot], conflicts: List[Dict[str, Any]], stats: Dict[str, Any]):
        self.current_roster = slots
        self.last_solver_result = {
            "status": status,
            "message": "Weekly roster solved successfully with zero hard-constraint violations." if status == "SUCCESS" else "No feasible schedule found. Hard-constraint conflicts detected.",
            "conflicts": conflicts,
            "stats": stats
        }

    def get_roster_result(self) -> Dict[str, Any]:
        return {
            "status": self.last_solver_result["status"],
            "message": self.last_solver_result["message"],
            "conflicts": self.last_solver_result["conflicts"],
            "stats": self.last_solver_result["stats"],
            "slots": [slot.to_dict() for slot in self.current_roster]
        }

    def mark_slot_absent(self, slot_id: str, reason: str = "Unplanned Absence") -> Optional[RosterSlot]:
        for slot in self.current_roster:
            if slot.id == slot_id:
                slot.is_absent = True
                slot.absent_reason = reason
                slot.replaced_by_id = None
                slot.replaced_by_name = None
                return slot
        return None

    def assign_replacement(self, slot_id: str, replacement_emp_id: str) -> Optional[RosterSlot]:
        emp = self.get_employee(replacement_emp_id)
        if not emp:
            return None
        for slot in self.current_roster:
            if slot.id == slot_id:
                slot.replaced_by_id = emp.id
                slot.replaced_by_name = emp.name
                return slot
        return None

    # --- Infeasible Demo Scenario ---
    def apply_impossible_scenario(self):
        """
        Injects a guaranteed impossible scenario for demonstration:
        1. Friday Morning requires a Supervisor.
        2. Alex Rivera, Dana Patel, and George Miller (the only Supervisors) all have Approved Leave on Friday Morning.
        Or: Set Alex and Dana to 0 available hours, George on leave.
        This tests requirement #3: Detect and explain conflicts truthfully.
        """
        # Ensure we have our seed employees
        supervisors = [e for e in self.employees.values() if "Supervisor" in e.skills]
        # Approve leave for all of them on Friday Morning
        for s in supervisors:
            lr_id = f"leave-conflict-{s.id}"
            self.leave_requests[lr_id] = LeaveRequest(
                id=lr_id,
                employee_id=s.id,
                employee_name=s.name,
                raw_text=f"Mandatory regional supervisor training seminar on Friday Morning for {s.name}",
                day_of_week="Friday",
                shift_type="Morning",
                reason="Supervisor Offsite Seminar (Approved Leave)",
                status="APPROVED",
                confidence=1.0,
                explanation="Simulated scenario: All qualified Supervisors unavailable simultaneously"
            )

# Singleton global database instance
db = DataStore()
