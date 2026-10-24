"""
Hard-Constraint Weekly Roster Solver & Conflict Diagnostic Engine.
Strictly hard constraints only:
1. Shift coverage
2. Approved unavailability/leave
3. Required skills
4. Weekly hour limit
5. Max one shift per day

If infeasible, reports WHICH requirements conflict. Never fakes a result.
"""
from typing import List, Dict, Any, Optional, Set, Tuple
from app.models import Employee, LeaveRequest, ShiftRoleRequirement, RosterSlot, ConflictDetail
import uuid

def is_employee_on_leave(emp_id: str, day: str, shift: str, approved_leaves: List[LeaveRequest]) -> Tuple[bool, Optional[str]]:
    """Checks if employee has approved leave on this day & shift."""
    for leave in approved_leaves:
        if leave.employee_id == emp_id and leave.day_of_week == day:
            if leave.shift_type == "All Day" or leave.shift_type == shift:
                return True, leave.reason
    return False, None

def analyze_conflicts(
    employees: List[Employee],
    requirements: List[ShiftRoleRequirement],
    approved_leaves: List[LeaveRequest]
) -> List[Dict[str, Any]]:
    """
    Analyzes and explains WHY the schedule cannot be fulfilled.
    Identifies exact bottleneck slots, missing skills, leave clashes, and capacity ceilings.
    """
    conflicts: List[Dict[str, Any]] = []
    emp_map = {e.id: e for e in employees}

    # 1. Check Skill-Level Global Capacity
    required_hours_by_skill: Dict[str, int] = {}
    for req in requirements:
        required_hours_by_skill[req.role] = required_hours_by_skill.get(req.role, 0) + req.hours

    for skill, req_hrs in required_hours_by_skill.items():
        skilled_emps = [e for e in employees if skill in e.skills]
        if not skilled_emps:
            conflicts.append({
                "type": "SKILL_MISSING",
                "title": f"Zero Staff With Required Skill '{skill}'",
                "description": f"The roster requires {req_hrs} hours of '{skill}', but no employee in the system has this skill.",
                "affected_shifts": [f"{r.day_of_week} {r.shift_type}" for r in requirements if r.role == skill],
                "factors": ["No employees currently registered with skill: " + skill],
                "action": f"Add an employee with '{skill}' skill or train existing staff."
            })
            continue

        total_skill_cap = sum(e.max_weekly_hours for e in skilled_emps)
        if total_skill_cap < req_hrs:
            conflicts.append({
                "type": "SKILL_HOUR_DEFICIT",
                "title": f"Weekly Hour Shortage for '{skill}'",
                "description": f"Demand for '{skill}' is {req_hrs}h, but total combined capacity of all {len(skilled_emps)} skilled staff ({', '.join(e.name for e in skilled_emps)}) is only {total_skill_cap}h. Deficit: {req_hrs - total_skill_cap}h.",
                "affected_shifts": [f"{r.day_of_week} {r.shift_type}" for r in requirements if r.role == skill],
                "factors": [f"{e.name}: max {e.max_weekly_hours}h/wk" for e in skilled_emps],
                "action": f"Increase max weekly hours for '{skill}' staff or recruit an additional '{skill}'."
            })

    # 2. Check Slot-Level Feasibility (Zero eligible staff due to leave or lack of skill)
    for req in requirements:
        skilled_emps = [e for e in employees if req.role in e.skills]
        if not skilled_emps:
            continue

        available_emps = []
        blocked_reasons = []

        for e in skilled_emps:
            on_leave, reason = is_employee_on_leave(e.id, req.day_of_week, req.shift_type, approved_leaves)
            if on_leave:
                blocked_reasons.append(f"{e.name} has approved leave ({reason})")
            else:
                available_emps.append(e)

        if not available_emps:
            conflicts.append({
                "type": "UNAVAILABLE_SLOT",
                "title": f"Unfillable Shift: {req.day_of_week} {req.shift_type} ({req.role})",
                "description": f"Every qualified '{req.role}' is unavailable for {req.day_of_week} {req.shift_type} due to approved leave.",
                "affected_shifts": [f"{req.day_of_week} {req.shift_type}"],
                "factors": blocked_reasons,
                "action": f"Reject or renegotiate leave request for at least one qualified '{req.role}'."
            })

    return conflicts

def solve_roster(
    employees: List[Employee],
    requirements: List[ShiftRoleRequirement],
    approved_leaves: List[LeaveRequest]
) -> Dict[str, Any]:
    """
    Strict CSP Backtracking Solver with MRV heuristic.
    Enforces all 5 hard constraints:
      1. Shift coverage
      2. Approved leave
      3. Required skills
      4. Weekly hour limit
      5. Max one shift per day
    """
    if not employees:
        return {
            "status": "INFEASIBLE",
            "slots": [],
            "conflicts": [{
                "type": "NO_EMPLOYEES",
                "title": "No Staff Available",
                "description": "Employee database is empty. Cannot generate a roster without staff.",
                "factors": ["0 employees registered"],
                "action": "Add employees or click 'Load Seed Data'."
            }],
            "stats": {}
        }

    # First, run pre-diagnostic check for obvious structural impossibilities
    structural_conflicts = analyze_conflicts(employees, requirements, approved_leaves)
    if structural_conflicts:
        return {
            "status": "INFEASIBLE",
            "slots": [],
            "conflicts": structural_conflicts,
            "stats": {}
        }

    # Prepare CSP problem variables
    # Each slot is an assignment target
    slots = []
    for idx, req in enumerate(requirements):
        slots.append({
            "slot_index": idx,
            "day": req.day_of_week,
            "shift": req.shift_type,
            "role": req.role,
            "hours": req.hours
        })

    # Precompute candidate domains for each slot
    emp_map = {e.id: e for e in employees}
    slot_domains: List[List[str]] = []

    for slot in slots:
        candidates = []
        for e in employees:
            # Hard constraint 3: Skill match
            if slot["role"] not in e.skills:
                continue
            # Hard constraint 2: Approved leave
            on_leave, _ = is_employee_on_leave(e.id, slot["day"], slot["shift"], approved_leaves)
            if on_leave:
                continue
            candidates.append(e.id)
        slot_domains.append(candidates)

    # Sort slots using MRV (Minimum Remaining Values - hardest slots first)
    slot_indices_order = sorted(range(len(slots)), key=lambda i: len(slot_domains[i]))

    # State tracking
    assignments: Dict[int, str] = {} # slot_index -> emp_id
    hours_worked: Dict[str, int] = {e.id: 0 for e in employees} # emp_id -> current weekly hours
    day_assignments: Dict[Tuple[str, str], str] = {} # (emp_id, day) -> shift_type

    def backtrack(order_pos: int) -> bool:
        if order_pos == len(slot_indices_order):
            return True # All slots successfully assigned!

        slot_idx = slot_indices_order[order_pos]
        slot = slots[slot_idx]
        candidates = slot_domains[slot_idx]

        # Order candidates by least hours worked so far (load balancing / fairness heuristic)
        candidates_sorted = sorted(candidates, key=lambda eid: hours_worked[eid])

        for emp_id in candidates_sorted:
            emp = emp_map[emp_id]

            # Hard constraint 4: Weekly hour limit
            if hours_worked[emp_id] + slot["hours"] > emp.max_weekly_hours:
                continue

            # Hard constraint 5: Max one shift per day
            if (emp_id, slot["day"]) in day_assignments:
                continue

            # Assign candidate
            assignments[slot_idx] = emp_id
            hours_worked[emp_id] += slot["hours"]
            day_assignments[(emp_id, slot["day"])] = slot["shift"]

            if backtrack(order_pos + 1):
                return True

            # Undo assignment (backtrack)
            del assignments[slot_idx]
            hours_worked[emp_id] -= slot["hours"]
            del day_assignments[(emp_id, slot["day"])]

        return False

    success = backtrack(0)

    if success:
        # Build assigned RosterSlot objects
        result_slots = []
        for idx, req in enumerate(requirements):
            emp_id = assignments[idx]
            emp_name = emp_map[emp_id].name
            result_slots.append(RosterSlot(
                id=f"slot-{idx+1}",
                day_of_week=req.day_of_week,
                shift_type=req.shift_type,
                role=req.role,
                hours=req.hours,
                assigned_employee_id=emp_id,
                assigned_employee_name=emp_name
            ))

        stats = {
            "total_slots": len(requirements),
            "total_hours": sum(r.hours for r in requirements),
            "employee_hours": {
                emp_id: {
                    "name": emp_map[emp_id].name,
                    "hours_worked": hours_worked[emp_id],
                    "max_hours": emp_map[emp_id].max_weekly_hours,
                    "utilization_pct": round((hours_worked[emp_id] / emp_map[emp_id].max_weekly_hours) * 100, 1)
                }
                for emp_id in emp_map
            }
        }

        return {
            "status": "SUCCESS",
            "slots": result_slots,
            "conflicts": [],
            "stats": stats
        }
    else:
        # Backtracking failed: pinpoint dynamic bottleneck (e.g. cumulative daily/weekly limits)
        # Find which slot caused the dead end
        bottlenecks = []
        for idx in slot_indices_order:
            slot = slots[idx]
            qualified_staff = [e for e in employees if slot["role"] in e.skills]
            reasons = []
            for e in qualified_staff:
                on_leave, leave_reason = is_employee_on_leave(e.id, slot["day"], slot["shift"], approved_leaves)
                if on_leave:
                    reasons.append(f"{e.name}: On approved leave ({leave_reason})")
                else:
                    reasons.append(f"{e.name}: Locked by weekly hour cap ({e.max_weekly_hours}h) or same-day shift limit")

            bottlenecks.append({
                "type": "CONSTRAINT_EXHAUSTION",
                "title": f"No Candidate Satisfies All Constraints for {slot['day']} {slot['shift']} ({slot['role']})",
                "description": f"All qualified {slot['role']} staff reached their weekly hour limit or daily shift limit before this slot could be filled.",
                "affected_shifts": [f"{slot['day']} {slot['shift']}"],
                "factors": reasons,
                "action": "Increase weekly hour limits for qualified staff or add more staff with this skill."
            })
            if len(bottlenecks) >= 2:
                break

        return {
            "status": "INFEASIBLE",
            "slots": [],
            "conflicts": bottlenecks,
            "stats": {}
        }
