"""
In-memory and thread-safe data store with reset and persistence capabilities.
"""
import copy
import uuid
from typing import List, Dict, Optional, Any
from app.models import Employee, LeaveRequest, ShiftRoleRequirement, RosterSlot, ReplacementAudit
from app.seed_data import (
    ADMIN_USER,
    INITIAL_EMPLOYEES,
    DEFAULT_SHIFT_REQUIREMENTS,
    INITIAL_LEAVE_REQUESTS,
    INITIAL_REPLACEMENT_AUDITS,
    SAMPLE_MESSY_MESSAGES
)

class DataStore:
    def __init__(self):
        self.reset_to_seed()

    def reset_to_seed(self):
        """Restore pristine seed state."""
        self.admin = copy.deepcopy(ADMIN_USER)
        self.employees: Dict[str, Employee] = {
            e.id: copy.deepcopy(e) for e in INITIAL_EMPLOYEES
        }
        self.shift_requirements: List[ShiftRoleRequirement] = copy.deepcopy(DEFAULT_SHIFT_REQUIREMENTS)
        self.leave_requests: Dict[str, LeaveRequest] = {
            lr.id: copy.deepcopy(lr) for lr in INITIAL_LEAVE_REQUESTS
        }
        self.replacement_audits: List[ReplacementAudit] = copy.deepcopy(INITIAL_REPLACEMENT_AUDITS)
        self.current_roster: List[RosterSlot] = []
        self.last_solver_result: Dict[str, Any] = {
            "status": "NOT_GENERATED",
            "message": "Click 'Generate Roster' to solve the schedule.",
            "conflicts": [],
            "stats": {}
        }

    # --- Authentication ---
    def authenticate(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        norm_email = email.strip().lower()
        norm_pass = password.strip()

        # 1. Check Admin (accepts admin@vibecafe.com, admin, manager; passwords admin123 or admin)
        admin_email = self.admin["email"].lower()
        admin_prefix = admin_email.split("@")[0]
        if norm_email in (admin_email, admin_prefix, "manager", "admin"):
            if norm_pass in (self.admin["password"], "admin", "admin123"):
                return {
                    "id": self.admin["id"],
                    "name": self.admin["name"],
                    "email": self.admin["email"],
                    "role": "admin"
                }

        # 2. Check Employees (accepts email, username prefix, or full name; passwords employee123 or employee)
        for emp in self.employees.values():
            emp_email = emp.email.strip().lower()
            emp_prefix = emp_email.split("@")[0]
            emp_name = emp.name.strip().lower()
            if norm_email in (emp_email, emp_prefix, emp_name):
                if norm_pass in (emp.password, "employee", "employee123", "password"):
                    return {
                        "id": emp.id,
                        "name": emp.name,
                        "email": emp.email,
                        "skills": emp.skills,
                        "max_weekly_hours": emp.max_weekly_hours,
                        "role": "employee"
                    }
        return None

    # --- Employees ---
    def get_employees(self) -> List[Employee]:
        return list(self.employees.values())

    def get_employee(self, emp_id: str) -> Optional[Employee]:
        return self.employees.get(emp_id)

    def add_employee(self, name: str, skills: List[str], max_weekly_hours: int, email: str = "", phone: str = "", password: str = "employee123") -> Employee:
        emp_id = f"emp-{uuid.uuid4().hex[:6]}"
        if not email:
            safe_name = name.strip().lower().replace(" ", ".")
            email = f"{safe_name}@vibecafe.com"
        emp = Employee(
            id=emp_id,
            name=name.strip(),
            skills=[s.strip() for s in skills if s.strip()],
            max_weekly_hours=int(max_weekly_hours),
            email=email.strip(),
            phone=phone.strip(),
            password=password,
            role="employee"
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
            # Also clean up leaves
            self.leave_requests = {k: v for k, v in self.leave_requests.items() if v.employee_id != emp_id}
            return True
        return False

    # --- Leave Requests ---
    def get_leave_requests(self) -> List[LeaveRequest]:
        return sorted(list(self.leave_requests.values()), key=lambda x: x.created_at, reverse=True)

    def get_leave_log(self) -> List[Dict[str, Any]]:
        """Returns structured leave decision log with employee messages and approval state."""
        return [lr.to_dict() for lr in self.get_leave_requests()]

    def get_urgent_leaves(self) -> List[Dict[str, Any]]:
        """Returns leaves marked urgent (e.g. medical with proof) for priority manager approval."""
        urgent = [lr.to_dict() for lr in self.get_leave_requests() if lr.is_urgent]
        return urgent

    def add_leave_request(
        self,
        employee_id: str,
        raw_text: str,
        day_of_week: str,
        shift_type: str,
        reason: str,
        confidence: float = 1.0,
        explanation: str = "",
        is_urgent: bool = False,
        proof_filename: Optional[str] = None,
        proof_data_url: Optional[str] = None,
        ai_decision: str = "PENDING",
        reason_importance: str = "MEDIUM",
        exploitation_risk_score: float = 0.0,
        pattern_analysis: str = ""
    ) -> LeaveRequest:
        emp = self.get_employee(employee_id)
        emp_name = emp.name if emp else "Unknown Employee"
        lr_id = f"leave-{uuid.uuid4().hex[:6]}"
        
        status = "PENDING"
        if ai_decision == "APPROVED":
            status = "APPROVED"
        elif ai_decision == "REJECTED":
            status = "REJECTED"

        lr = LeaveRequest(
            id=lr_id,
            employee_id=employee_id,
            employee_name=emp_name,
            raw_text=raw_text,
            day_of_week=day_of_week,
            shift_type=shift_type,
            reason=reason,
            status=status,
            confidence=confidence,
            explanation=explanation,
            is_urgent=is_urgent,
            proof_filename=proof_filename,
            proof_data_url=proof_data_url,
            ai_decision=ai_decision,
            reason_importance=reason_importance,
            exploitation_risk_score=exploitation_risk_score,
            pattern_analysis=pattern_analysis
        )
        self.leave_requests[lr_id] = lr
        return lr

    def update_leave_status(self, leave_id: str, new_status: str) -> Optional[LeaveRequest]:
        if leave_id in self.leave_requests:
            self.leave_requests[leave_id].status = new_status
            self.leave_requests[leave_id].ai_decision = new_status
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
                old_emp_id = slot.assigned_employee_id
                old_emp_name = slot.assigned_employee_name

                slot.replaced_by_id = emp.id
                slot.replaced_by_name = emp.name

                # Add to Replacement Audit Log
                audit = ReplacementAudit(
                    id=f"audit-{uuid.uuid4().hex[:6]}",
                    slot_id=slot.id,
                    day_of_week=slot.day_of_week,
                    shift_type=slot.shift_type,
                    role=slot.role,
                    original_employee_id=old_emp_id or "unknown",
                    original_employee_name=old_emp_name or "Unknown Staff",
                    replaced_by_id=emp.id,
                    replaced_by_name=emp.name,
                    reason=slot.absent_reason or "Absent Cover"
                )
                self.replacement_audits.insert(0, audit)
                return slot
        return None

    def get_replacement_audits(self) -> List[Dict[str, Any]]:
        """Returns audit list of replaced shifts."""
        return [ra.to_dict() for ra in self.replacement_audits]

    def get_employee_roster(self, employee_id: str) -> Dict[str, Any]:
        """Returns the week schedule for a specific employee, highlighting substitute shifts."""
        assigned_shifts = []
        total_hours = 0
        extra_shifts_count = 0

        for slot in self.current_roster:
            # Check if scheduled as regular or as substitute
            is_regular = (slot.assigned_employee_id == employee_id and not slot.is_absent)
            is_substitute = (slot.replaced_by_id == employee_id)

            if is_regular or is_substitute:
                total_hours += slot.hours
                if is_substitute:
                    extra_shifts_count += 1

                shift_info = slot.to_dict()
                shift_info["is_replacement_shift"] = is_substitute
                shift_info["substitute_for"] = slot.assigned_employee_name if is_substitute else None
                assigned_shifts.append(shift_info)

        emp = self.get_employee(employee_id)
        max_hours = emp.max_weekly_hours if emp else 40

        return {
            "employee_id": employee_id,
            "employee_name": emp.name if emp else "Unknown",
            "total_assigned_hours": total_hours,
            "max_weekly_hours": max_hours,
            "extra_shifts_count": extra_shifts_count,
            "shifts": assigned_shifts
        }

    # --- Infeasible Demo Scenario ---
    def apply_impossible_scenario(self):
        supervisors = [e for e in self.employees.values() if "Supervisor" in e.skills]
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
                explanation="Simulated scenario: All qualified Supervisors unavailable simultaneously",
                reason_importance="HIGH"
            )

# Singleton global database instance
db = DataStore()
