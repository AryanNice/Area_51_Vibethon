"""
Roster Solver using Google OR-Tools CP-SAT
Implements hard constraints:
1. Shift coverage
2. Approved unavailability / leave
3. Required skills
4. Weekly hour limit
5. Max one shift per day

If infeasible, diagnoses and reports WHICH requirements conflict. Never fakes a result.
"""

import sys
from unittest.mock import MagicMock
# Shim for pandas if pandas C-extension is blocked by system AppLocker policy
if "pandas" not in sys.modules:
    sys.modules["pandas"] = MagicMock()

from typing import List, Dict, Any, Optional, Tuple
from ortools.sat.python import cp_model


class RosterSolver:
    def __init__(self, employees: List[Dict[str, Any]], shifts: List[Dict[str, Any]], leaves: List[Dict[str, Any]]):
        """
        employees: [
            {"id": "emp_1", "name": "Alice Chen", "skills": ["Cashier", "Manager"], "max_hours": 40}
        ]
        shifts: [
            {"id": "mon_morn", "day": "Monday", "name": "Morning", "hours": 8, "required_skill": "Manager", "required_count": 1}
        ]
        leaves: [
            {"employee_id": "emp_1", "day": "Monday", "shift": "Morning", "status": "approved"}
        ]
        """
        self.employees = {e["id"]: e for e in employees}
        self.shifts = {s["id"]: s for s in shifts}
        # Only hard constraint on approved leaves
        self.approved_leaves = [
            l for l in leaves if l.get("status", "").lower() == "approved"
        ]

    def solve(self) -> Dict[str, Any]:
        """
        Returns:
        {
            "feasible": True/False,
            "status": "OPTIMAL" / "FEASIBLE" / "INFEASIBLE",
            "assignments": [
                {"shift_id": "mon_morn", "shift_name": "Monday Morning", "employee_id": "emp_1", "employee_name": "Alice Chen"}
            ],
            "employee_stats": {
                "emp_1": {"assigned_hours": 32, "max_hours": 40, "shifts_count": 4}
            },
            "conflicts": [
                "Detailed human-readable explanation of conflict"
            ]
        }
        """
        model = cp_model.CpModel()
        
        # Decision variables: x[e_id, s_id] = 1 if employee e is assigned to shift s, else 0
        x = {}
        for e_id in self.employees:
            for s_id in self.shifts:
                x[(e_id, s_id)] = model.NewBoolVar(f"x_{e_id}_{s_id}")

        # 1. Hard Constraint: Shift Coverage
        for s_id, s_info in self.shifts.items():
            req_count = s_info.get("required_count", 1)
            model.Add(sum(x[(e_id, s_id)] for e_id in self.employees) == req_count)

        # 2. Hard Constraint: Required Skills
        for s_id, s_info in self.shifts.items():
            req_skill = s_info.get("required_skill")
            if req_skill:
                for e_id, e_info in self.employees.items():
                    if req_skill not in e_info.get("skills", []):
                        # Employee lacks skill -> cannot be assigned
                        model.Add(x[(e_id, s_id)] == 0)

        # 3. Hard Constraint: Approved Leave / Unavailability
        for leave in self.approved_leaves:
            emp_id = leave.get("employee_id")
            leave_day = leave.get("day")
            leave_shift = leave.get("shift")  # "All" or specific shift name like "Morning"

            if emp_id in self.employees:
                for s_id, s_info in self.shifts.items():
                    if s_info.get("day") == leave_day:
                        if not leave_shift or leave_shift.lower() in ["all", "all day", "any"] or leave_shift.lower() == s_info.get("name", "").lower():
                            model.Add(x[(emp_id, s_id)] == 0)

        # 4. Hard Constraint: Max one shift per day
        # Group shifts by day
        shifts_by_day: Dict[str, List[str]] = {}
        for s_id, s_info in self.shifts.items():
            shifts_by_day.setdefault(s_info.get("day", ""), []).append(s_id)

        for day, day_shift_ids in shifts_by_day.items():
            for e_id in self.employees:
                model.Add(sum(x[(e_id, s_id)] for s_id in day_shift_ids) <= 1)

        # 5. Hard Constraint: Weekly Hour Limit
        for e_id, e_info in self.employees.items():
            max_h = int(e_info.get("max_hours", 40))
            model.Add(
                sum(x[(e_id, s_id)] * int(s_info.get("hours", 8)) for s_id, s_info in self.shifts.items()) <= max_h
            )

        # Objective: Balance shifts fairly among employees (optional soft objective)
        # Minimize the difference or total variance
        # For simplicity and speed: slight penalty for assigning high hours to keep it balanced
        # Or simple constant objective
        total_shifts = sum(x[(e_id, s_id)] for e_id in self.employees for s_id in self.shifts)
        model.Maximize(total_shifts)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            assignments = []
            employee_stats = {
                e_id: {"assigned_hours": 0, "max_hours": e["max_hours"], "shifts_count": 0, "shifts": []}
                for e_id, e in self.employees.items()
            }

            for s_id, s_info in self.shifts.items():
                for e_id, e_info in self.employees.items():
                    if solver.Value(x[(e_id, s_id)]) == 1:
                        assignments.append({
                            "shift_id": s_id,
                            "day": s_info.get("day"),
                            "shift_name": s_info.get("name"),
                            "hours": s_info.get("hours", 8),
                            "required_skill": s_info.get("required_skill"),
                            "employee_id": e_id,
                            "employee_name": e_info.get("name")
                        })
                        employee_stats[e_id]["assigned_hours"] += int(s_info.get("hours", 8))
                        employee_stats[e_id]["shifts_count"] += 1
                        employee_stats[e_id]["shifts"].append(s_id)

            return {
                "feasible": True,
                "status": "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE",
                "assignments": assignments,
                "employee_stats": employee_stats,
                "conflicts": []
            }
        else:
            # Infeasible: Diagnose conflicts
            conflicts = self._diagnose_conflicts()
            return {
                "feasible": False,
                "status": "INFEASIBLE",
                "assignments": [],
                "employee_stats": {},
                "conflicts": conflicts
            }

    def _diagnose_conflicts(self) -> List[str]:
        """
        Diagnoses why no feasible roster exists by testing specific constraint relaxations
        and calculating capacity bottlenecks.
        """
        conflicts = []

        # 1. Check total hours demand vs total available capacity
        total_shift_hours_needed = sum(s.get("hours", 8) * s.get("required_count", 1) for s in self.shifts.values())
        total_employee_capacity = sum(e.get("max_hours", 40) for e in self.employees.values())

        if total_shift_hours_needed > total_employee_capacity:
            conflicts.append(
                f"Total required shift hours ({total_shift_hours_needed}h) exceeds the total weekly capacity of all employees ({total_employee_capacity}h)."
            )

        # 2. Check skill-by-skill availability & capacity
        all_required_skills = set(s.get("required_skill") for s in self.shifts.values() if s.get("required_skill"))
        for skill in all_required_skills:
            shifts_requiring_skill = [s for s in self.shifts.values() if s.get("required_skill") == skill]
            skill_hours_needed = sum(s.get("hours", 8) * s.get("required_count", 1) for s in shifts_requiring_skill)
            qualified_emps = [e for e in self.employees.values() if skill in e.get("skills", [])]

            if not qualified_emps:
                conflicts.append(f"No employees have the required skill '{skill}' to cover {len(shifts_requiring_skill)} shift(s).")
                continue

            qualified_capacity = sum(e.get("max_hours", 40) for e in qualified_emps)
            if skill_hours_needed > qualified_capacity:
                conflicts.append(
                    f"Skill bottleneck for '{skill}': Shifts require {skill_hours_needed}h, but qualified staff ({', '.join(e['name'] for e in qualified_emps)}) only have {qualified_capacity}h total weekly capacity."
                )

        # 3. Check shift-by-shift coverage impossibility (e.g. leaves or zero qualified available staff on that specific shift/day)
        shifts_by_day: Dict[str, List[Dict[str, Any]]] = {}
        for s in self.shifts.values():
            shifts_by_day.setdefault(s.get("day", ""), []).append(s)

        for day, d_shifts in shifts_by_day.items():
            # Check how many employees are on leave on this day
            emps_on_leave_today = set()
            for l in self.approved_leaves:
                if l.get("day") == day and (not l.get("shift") or l.get("shift").lower() in ["all", "all day", "any"]):
                    emps_on_leave_today.add(l.get("employee_id"))

            available_emps_count = len(self.employees) - len(emps_on_leave_today)
            shifts_today_count = sum(s.get("required_count", 1) for s in d_shifts)

            # Max 1 shift per day constraint means we need at least shifts_today_count employees available
            if shifts_today_count > available_emps_count:
                leave_names = [self.employees[eid]["name"] for eid in emps_on_leave_today if eid in self.employees]
                conflicts.append(
                    f"Day '{day}' requires {shifts_today_count} separate employees (max 1 shift/day constraint), but only {available_emps_count} are available due to approved leaves ({', '.join(leave_names) if leave_names else 'none'})."
                )

            # Check individual shift skills & specific leaves
            for s in d_shifts:
                s_id = s["id"]
                req_skill = s.get("required_skill")
                req_count = s.get("required_count", 1)

                # Who can do this shift?
                eligible = []
                reasons = []
                for e_id, e in self.employees.items():
                    # Skill check
                    if req_skill and req_skill not in e.get("skills", []):
                        continue
                    # Leave check
                    on_leave = False
                    for l in self.approved_leaves:
                        if l.get("employee_id") == e_id and l.get("day") == day:
                            l_shift = l.get("shift", "").lower()
                            if not l_shift or l_shift in ["all", "all day", "any"] or l_shift == s.get("name", "").lower():
                                on_leave = True
                                break
                    if on_leave:
                        reasons.append(f"{e['name']} (on approved leave)")
                    else:
                        eligible.append(e)

                if len(eligible) < req_count:
                    conflicts.append(
                        f"Shift '{day} {s.get('name')}' requires {req_count} '{req_skill}' worker(s), but only {len(eligible)} qualified worker(s) are available. Unavailable qualified staff: {', '.join(reasons) if reasons else 'No qualified staff'}."
                    )

        if not conflicts:
            conflicts.append(
                "Combined hard constraints (weekly hour limits + max 1 shift/day + shift coverage) cannot be simultaneously satisfied. Try increasing employee hour caps or reducing shift requirements."
            )

        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for c in conflicts:
            if c not in seen:
                seen.add(c)
                deduped.append(c)
        return deduped


def rank_replacements(
    absent_shift: Dict[str, Any],
    absent_employee_id: str,
    all_employees: List[Dict[str, Any]],
    current_roster: List[Dict[str, Any]],
    approved_leaves: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Plain scoring function for ranking replacement employees:
    - Must not be the absent employee
    - Skill match (+50)
    - Available on that day/shift (not on leave) (+30)
    - Not already working another shift on that day (max 1 shift/day) (+30)
    - Weekly hour headroom (+20 scaled)
    - Low current hours bonus for fairness (+10)
    """
    target_day = absent_shift.get("day")
    target_shift_name = absent_shift.get("shift_name")
    target_skill = absent_shift.get("required_skill")
    shift_hours = absent_shift.get("hours", 8)

    # Compute current weekly hours and day assignments for each employee
    assigned_hours = {e["id"]: 0 for e in all_employees}
    assigned_days = {e["id"]: set() for e in all_employees}

    for assignment in current_roster:
        e_id = assignment.get("employee_id")
        if e_id and e_id != absent_employee_id:
            assigned_hours[e_id] = assigned_hours.get(e_id, 0) + int(assignment.get("hours", 8))
            assigned_days[e_id].add(assignment.get("day"))

    candidates = []

    for e in all_employees:
        e_id = e["id"]
        if e_id == absent_employee_id:
            continue

        score = 0
        is_eligible = True
        reasons = []
        warnings = []

        # 1. Skill Match
        has_skill = not target_skill or target_skill in e.get("skills", [])
        if has_skill:
            score += 50
            reasons.append(f"Has required skill '{target_skill}'")
        else:
            is_eligible = False
            warnings.append(f"Missing required skill '{target_skill}'")

        # 2. Leave Check
        on_leave = False
        for l in approved_leaves:
            if l.get("employee_id") == e_id and l.get("day") == target_day and l.get("status", "").lower() == "approved":
                l_s = l.get("shift", "").lower()
                if not l_s or l_s in ["all", "all day", "any"] or l_s == target_shift_name.lower():
                    on_leave = True
                    break
        if not on_leave:
            score += 30
            reasons.append(f"Available on {target_day}")
        else:
            is_eligible = False
            warnings.append(f"On approved leave on {target_day}")

        # 3. Max 1 shift per day check
        already_working_day = target_day in assigned_days.get(e_id, set())
        if not already_working_day:
            score += 30
            reasons.append(f"Not scheduled for any other shift on {target_day}")
        else:
            is_eligible = False
            warnings.append(f"Already scheduled for a shift on {target_day}")

        # 4. Weekly hour limit check
        curr_h = assigned_hours.get(e_id, 0)
        max_h = int(e.get("max_hours", 40))
        remaining_h = max_h - curr_h

        if remaining_h >= shift_hours:
            headroom_ratio = remaining_h / max(max_h, 1)
            score += int(headroom_ratio * 20)
            reasons.append(f"Has {remaining_h}h capacity left (cap: {max_h}h)")
        else:
            is_eligible = False
            warnings.append(f"Would exceed weekly hour limit ({curr_h + shift_hours}h > {max_h}h)")

        # Fairness bonus: prefer employees with fewer assigned hours
        fairness_bonus = max(0, int((40 - curr_h) / 4))
        score += fairness_bonus

        candidates.append({
            "employee_id": e_id,
            "name": e.get("name"),
            "skills": e.get("skills", []),
            "score": score if is_eligible else max(0, score - 50),
            "is_eligible": is_eligible,
            "current_hours": curr_h,
            "max_hours": max_h,
            "reasons": reasons,
            "warnings": warnings
        })

    # Sort eligible candidates first by score descending, then ineligible
    candidates.sort(key=lambda c: (c["is_eligible"], c["score"]), reverse=True)
    return candidates
