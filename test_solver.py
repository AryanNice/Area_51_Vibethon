"""
Quick test for solver.py
"""
from solver import RosterSolver, rank_replacements

employees = [
    {"id": "e1", "name": "Alice Chen", "skills": ["Cashier", "Manager"], "max_hours": 40},
    {"id": "e2", "name": "Bob Smith", "skills": ["Barista", "Cashier"], "max_hours": 40},
    {"id": "e3", "name": "Charlie Davis", "skills": ["Cook", "Kitchen"], "max_hours": 32},
    {"id": "e4", "name": "Diana Prince", "skills": ["Barista", "Manager"], "max_hours": 24},
    {"id": "e5", "name": "Evan Wright", "skills": ["Cook", "Cashier"], "max_hours": 40},
    {"id": "e6", "name": "Fiona Gallagher", "skills": ["Cashier", "Barista"], "max_hours": 40},
]

# 7 days, 2 shifts per day: Morning and Evening
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
shifts = []
for d in days:
    shifts.append({
        "id": f"{d.lower()}_morning",
        "day": d,
        "name": "Morning",
        "hours": 8,
        "required_skill": "Manager" if d in ["Monday", "Saturday"] else "Cashier",
        "required_count": 1
    })
    shifts.append({
        "id": f"{d.lower()}_evening",
        "day": d,
        "name": "Evening",
        "hours": 8,
        "required_skill": "Cook" if d in ["Wednesday", "Friday"] else "Barista",
        "required_count": 1
    })

print(f"Total shifts: {len(shifts)}")

# Test 1: Feasible solve
leaves = [
    {"employee_id": "e1", "day": "Tuesday", "shift": "All", "status": "approved"}
]
solver = RosterSolver(employees, shifts, leaves)
res = solver.solve()
print("Test 1 Feasible?", res["feasible"], "Status:", res["status"])
assert res["feasible"] == True
print(f"Assignments count: {len(res['assignments'])}")

# Test 2: Impossible solve (e.g., both managers Alice and Diana on approved leave when Manager shift is required)
impossible_leaves = [
    {"employee_id": "e1", "day": "Saturday", "shift": "Morning", "status": "approved"},
    {"employee_id": "e4", "day": "Saturday", "shift": "Morning", "status": "approved"},
]
solver_imp = RosterSolver(employees, shifts, impossible_leaves)
res_imp = solver_imp.solve()
print("Test 2 Feasible?", res_imp["feasible"], "Status:", res_imp["status"])
assert res_imp["feasible"] == False
print("Detected conflicts:")
for c in res_imp["conflicts"]:
    print(" -", c)

# Test 3: Replacement ranking
absent_shift = res["assignments"][0]
print(f"\nTest 3: Absent shift: {absent_shift['day']} {absent_shift['shift_name']} ({absent_shift['required_skill']}), Absent: {absent_shift['employee_name']}")
ranked = rank_replacements(absent_shift, absent_shift["employee_id"], employees, res["assignments"], leaves)
print("Top 3 ranked replacements:")
for r in ranked[:3]:
    print(f" - {r['name']} (Score: {r['score']}, Eligible: {r['is_eligible']}) Reasons: {r['reasons']}, Warnings: {r['warnings']}")

print("\nALL SOLVER TESTS PASSED!")
