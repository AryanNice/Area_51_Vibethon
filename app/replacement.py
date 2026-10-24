"""
Ranked Replacement Engine for Unplanned Absences.
Evaluates all employees against hard constraints and ranks eligible substitutes transparently.
"""
from typing import List, Dict, Any, Optional
from app.models import Employee, RosterSlot, LeaveRequest
from app.solver import is_employee_on_leave

def get_ranked_replacements(
    slot: RosterSlot,
    employees: List[Employee],
    current_roster: List[RosterSlot],
    approved_leaves: List[LeaveRequest]
) -> Dict[str, Any]:
    """
    Finds and ranks replacement staff for an absent slot.
    Returns:
        {
            "eligible": [...],
            "ineligible": [...]
        }
    """
    # Calculate current weekly hours worked for each employee in active roster
    # Note: If someone was marked absent on a slot, they don't count for those hours if replaced
    hours_by_emp: Dict[str, int] = {e.id: 0 for e in employees}
    shifts_by_day_and_emp: Dict[str, Dict[str, str]] = {e.id: {} for e in employees}

    for s in current_roster:
        # If this is the current vacant slot, ignore its original assignment
        if s.id == slot.id:
            continue

        assigned_id = s.replaced_by_id if s.replaced_by_id else (None if s.is_absent else s.assigned_employee_id)
        if assigned_id and assigned_id in hours_by_emp:
            hours_by_emp[assigned_id] += s.hours
            shifts_by_day_and_emp[assigned_id][s.day_of_week] = s.shift_type

    eligible: List[Dict[str, Any]] = []
    ineligible: List[Dict[str, Any]] = []

    for emp in employees:
        # Don't suggest the original absent employee
        if emp.id == slot.assigned_employee_id:
            ineligible.append({
                "employee_id": emp.id,
                "name": emp.name,
                "reason": "Currently marked absent for this shift",
                "skills": emp.skills
            })
            continue

        # Hard Constraint 1: Required Skill
        if slot.role not in emp.skills:
            ineligible.append({
                "employee_id": emp.id,
                "name": emp.name,
                "reason": f"Lacks required skill '{slot.role}' (Has: {', '.join(emp.skills)})",
                "skills": emp.skills
            })
            continue

        # Hard Constraint 2: Approved Leave
        on_leave, leave_reason = is_employee_on_leave(emp.id, slot.day_of_week, slot.shift_type, approved_leaves)
        if on_leave:
            ineligible.append({
                "employee_id": emp.id,
                "name": emp.name,
                "reason": f"Approved leave on {slot.day_of_week} ({leave_reason})",
                "skills": emp.skills
            })
            continue

        # Hard Constraint 3: Max one shift per day
        worked_shift_today = shifts_by_day_and_emp[emp.id].get(slot.day_of_week)
        if worked_shift_today:
            ineligible.append({
                "employee_id": emp.id,
                "name": emp.name,
                "reason": f"Already scheduled for {slot.day_of_week} {worked_shift_today} shift (Violates max 1 shift/day)",
                "skills": emp.skills
            })
            continue

        # Hard Constraint 4: Weekly Hour Limit
        current_hrs = hours_by_emp[emp.id]
        if current_hrs + slot.hours > emp.max_weekly_hours:
            ineligible.append({
                "employee_id": emp.id,
                "name": emp.name,
                "reason": f"Exceeds weekly cap ({current_hrs}h + {slot.hours}h > {emp.max_weekly_hours}h max)",
                "skills": emp.skills
            })
            continue

        # Candidate is 100% ELIGIBLE! Now compute transparent ranking score
        remaining_hrs = emp.max_weekly_hours - current_hrs
        # Score component 1: Remaining hour headroom (up to 40 pts)
        headroom_score = min(40.0, (remaining_hrs / max(1, emp.max_weekly_hours)) * 40.0)

        # Score component 2: Skill match priority (up to 30 pts)
        # If role is employee's primary skill (first listed) -> 30 pts, otherwise 20 pts
        skill_priority_score = 30.0 if emp.skills and emp.skills[0] == slot.role else 20.0

        # Score component 3: Load balance / Low burnout (up to 30 pts)
        burnout_factor = 1.0 - (current_hrs / max(1, emp.max_weekly_hours))
        balance_score = burnout_factor * 30.0

        total_score = round(headroom_score + skill_priority_score + balance_score, 1)

        ranking_reasons = []
        if emp.skills and emp.skills[0] == slot.role:
            ranking_reasons.append(f"Primary specialist in {slot.role}")
        else:
            ranking_reasons.append(f"Cross-trained in {slot.role}")
        ranking_reasons.append(f"{remaining_hrs}h remaining under weekly cap")
        ranking_reasons.append(f"Current load: {current_hrs}/{emp.max_weekly_hours}h ({round((current_hrs/emp.max_weekly_hours)*100)}%)")

        eligible.append({
            "employee_id": emp.id,
            "name": emp.name,
            "score": total_score,
            "skills": emp.skills,
            "current_hours": current_hrs,
            "max_hours": emp.max_weekly_hours,
            "remaining_hours": remaining_hrs,
            "new_total_hours": current_hrs + slot.hours,
            "ranking_explanation": " • ".join(ranking_reasons)
        })

    # Sort eligible candidates by score descending
    eligible.sort(key=lambda x: x["score"], reverse=True)

    # Assign rank indices
    for idx, cand in enumerate(eligible):
        cand["rank"] = idx + 1

    return {
        "slot": slot.to_dict(),
        "eligible": eligible,
        "ineligible": ineligible,
        "eligible_count": len(eligible),
        "ineligible_count": len(ineligible)
    }
