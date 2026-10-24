"""
Unit tests for the 5 Hard Constraints and Conflict Detection.
"""
import unittest
from app.models import Employee, ShiftRoleRequirement, LeaveRequest
from app.solver import solve_roster, analyze_conflicts
from app.replacement import get_ranked_replacements
from app.ai_parser import parse_free_text_availability
from app.seed_data import INITIAL_EMPLOYEES, DEFAULT_SHIFT_REQUIREMENTS

class TestSolverConstraints(unittest.TestCase):

    def test_feasible_seed_schedule(self):
        """Standard seed employees and default shifts must solve cleanly."""
        res = solve_roster(INITIAL_EMPLOYEES, DEFAULT_SHIFT_REQUIREMENTS, [])
        self.assertEqual(res["status"], "SUCCESS")
        self.assertEqual(len(res["slots"]), len(DEFAULT_SHIFT_REQUIREMENTS))

        # Check constraint 4: No employee exceeds max_weekly_hours
        emp_hours = {}
        for s in res["slots"]:
            eid = s.assigned_employee_id
            emp_hours[eid] = emp_hours.get(eid, 0) + s.hours

        for emp in INITIAL_EMPLOYEES:
            hrs = emp_hours.get(emp.id, 0)
            self.assertLessEqual(hrs, emp.max_weekly_hours)

    def test_hard_constraint_leave(self):
        """Approved leave MUST prevent employee from being scheduled on that day/shift."""
        # Bianca Chen (emp-2) has approved leave on Tuesday Morning
        leave = [LeaveRequest(
            id="l1",
            employee_id="emp-2",
            employee_name="Bianca Chen",
            raw_text="Doctor",
            day_of_week="Tuesday",
            shift_type="Morning",
            reason="Doctor",
            status="APPROVED"
        )]
        res = solve_roster(INITIAL_EMPLOYEES, DEFAULT_SHIFT_REQUIREMENTS, leave)
        self.assertEqual(res["status"], "SUCCESS")
        for s in res["slots"]:
            if s.day_of_week == "Tuesday" and s.shift_type == "Morning":
                self.assertNotEqual(s.assigned_employee_id, "emp-2")

    def test_hard_constraint_max_one_shift_per_day(self):
        """No employee can work more than one shift on the same calendar day."""
        res = solve_roster(INITIAL_EMPLOYEES, DEFAULT_SHIFT_REQUIREMENTS, [])
        self.assertEqual(res["status"], "SUCCESS")

        daily_work = {}
        for s in res["slots"]:
            key = (s.assigned_employee_id, s.day_of_week)
            self.assertNotIn(key, daily_work, f"Employee {s.assigned_employee_name} assigned twice on {s.day_of_week}")
            daily_work[key] = s.shift_type

    def test_infeasible_conflict_explanation_zero_skill(self):
        """If a required skill has no available staff, report the exact conflict."""
        reqs = [
            ShiftRoleRequirement("Monday", "Morning", "Astronaut", 8)
        ]
        res = solve_roster(INITIAL_EMPLOYEES, reqs, [])
        self.assertEqual(res["status"], "INFEASIBLE")
        self.assertTrue(len(res["conflicts"]) > 0)
        self.assertIn("Astronaut", res["conflicts"][0]["title"])

    def test_infeasible_conflict_leave_lockout(self):
        """If all qualified staff for a shift are on leave, explain the exact bottleneck."""
        supervisors = [e for e in INITIAL_EMPLOYEES if "Supervisor" in e.skills]
        leaves = [
            LeaveRequest(
                id=f"l-{s.id}",
                employee_id=s.id,
                employee_name=s.name,
                raw_text="Vacation",
                day_of_week="Friday",
                shift_type="Morning",
                reason="Vacation",
                status="APPROVED"
            )
            for s in supervisors
        ]
        res = solve_roster(INITIAL_EMPLOYEES, DEFAULT_SHIFT_REQUIREMENTS, leaves)
        self.assertEqual(res["status"], "INFEASIBLE")
        self.assertTrue(any("Friday Morning" in c["title"] for c in res["conflicts"]))

    def test_ai_free_text_parser(self):
        """Messy real-world texts must extract day, shift, and reason."""
        msg1 = "Hey boss! My sister is getting married next week, so I cannot work Friday evening. Thanks!"
        p1 = parse_free_text_availability(msg1)
        self.assertEqual(p1["day_of_week"], "Friday")
        self.assertEqual(p1["shift_type"], "Evening")
        self.assertIn("Wedding", p1["reason"])

        msg2 = "Doctor appointment on Tuesday morning, unable to work the morning shift."
        p2 = parse_free_text_availability(msg2)
        self.assertEqual(p2["day_of_week"], "Tuesday")
        self.assertEqual(p2["shift_type"], "Morning")
        self.assertIn("Doctor", p2["reason"])

    def test_ranked_replacement(self):
        """Replacement engine returns ranked eligible candidates and ineligible reasons."""
        res = solve_roster(INITIAL_EMPLOYEES, DEFAULT_SHIFT_REQUIREMENTS, [])
        self.assertEqual(res["status"], "SUCCESS")

        slot_to_replace = res["slots"][0] # Monday Morning Supervisor
        replacements = get_ranked_replacements(slot_to_replace, INITIAL_EMPLOYEES, res["slots"], [])

        self.assertTrue(replacements["eligible_count"] > 0)
        # Check that top replacement has Supervisor skill
        top_cand = replacements["eligible"][0]
        self.assertIn("Supervisor", top_cand["skills"])
        self.assertGreater(top_cand["remaining_hours"], 0)

if __name__ == "__main__":
    unittest.main()
