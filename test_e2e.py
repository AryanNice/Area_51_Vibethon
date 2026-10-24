"""
End-to-End Integration Test for VibeRoster MVP Definition of Done:
1. Add employee ->
2. Submit a messy message ->
3. Approve ->
4. Generate roster ->
5. Create an impossible case and see the explanation ->
6. Mark absent ->
7. Pick a replacement.
"""

import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

def post(path, data=None):
    body = json.dumps(data).encode("utf-8") if data is not None else b"{}"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def get(path):
    with urllib.request.urlopen(f"{BASE_URL}{path}") as resp:
        return json.loads(resp.read().decode("utf-8"))

print("=== Starting E2E Definition of Done Validation ===")

# Step 0: Check initial data
data = get("/api/data")
print(f"0. Initial Seed Data: {len(data['employees'])} employees, {len(data['shifts'])} shifts")
assert len(data['employees']) >= 6

# Step 1: Add employee
emp_payload = {"name": "Maya Lin", "skills": ["Barista", "Cook"], "max_hours": 36}
emp_res = post("/api/employees", emp_payload)
new_emp_id = emp_res["employee"]["id"]
print(f"1. Added Employee: {emp_res['employee']['name']} (ID: {new_emp_id}, Skills: {emp_res['employee']['skills']})")
assert emp_res["employee"]["name"] == "Maya Lin"

# Step 2: Submit a messy message & parse
messy_msg = "Hey boss, Bob here. I cannot make it this Friday evening because my cousin is getting married!"
parse_res = post("/api/leave/parse", {"text": messy_msg})
print(f"2. AI Parsed Messy Message:")
print(f"   - Identified Employee: {parse_res['employee_name']} (ID: {parse_res['employee_id']})")
print(f"   - Days: {parse_res['days']}, Shift: {parse_res['shift']}")
print(f"   - Reason: {parse_res['reason']}")
assert "Friday" in parse_res["days"]
assert parse_res["shift"] == "Evening"

# Step 3: Submit to manager queue and approve
sub_res = post("/api/leave/submit", {
    "employee_id": parse_res["employee_id"],
    "days": parse_res["days"],
    "shift": parse_res["shift"],
    "reason": parse_res["reason"],
    "raw_text": parse_res["raw_text"]
})
leave_id = sub_res["leaves"][0]["id"]
print(f"3a. Submitted Leave Request ID: {leave_id}, Status: {sub_res['leaves'][0]['status']}")

action_res = post(f"/api/leave/{leave_id}/action", {"action": "approve"})
print(f"3b. Manager Approved Leave: Status is now '{action_res['leave']['status']}'")
assert action_res["leave"]["status"] == "approved"

# Step 4: Generate weekly roster
roster_res = post("/api/roster/generate")
print(f"4. Generated Roster: Feasible={roster_res['feasible']}, Status={roster_res['status']}, Assignments={roster_res['assignments_count']}")
assert roster_res["feasible"] == True
assert roster_res["assignments_count"] == 14

# Verify Bob is NOT assigned to Friday Evening
fri_eve = next((a for a in roster_res["assignments"] if a["day"] == "Friday" and a["shift_name"] == "Evening"), None)
print(f"   - Friday Evening assigned to: {fri_eve['employee_name']} (Bob was on approved leave, constraint respected!)")
assert fri_eve["employee_id"] != parse_res["employee_id"]

# Step 5: Create an impossible case and see the explanation
imp_res = post("/api/roster/simulate-impossible")
print(f"5. Impossible Scenario Tested: Feasible={imp_res['feasible']}, Status={imp_res['status']}")
assert imp_res["feasible"] == False
print("   - Solver Conflict Explanation:")
for conflict in imp_res["conflicts"]:
    print(f"     * {conflict}")
assert len(imp_res["conflicts"]) > 0

# Step 6: Reset to seed and re-generate clean roster
post("/api/reset")
clean_roster = post("/api/roster/generate")
assert clean_roster["feasible"] == True

# Step 7: Mark someone absent
target_shift = clean_roster["assignments"][0]
print(f"6. Target Shift for Absence: {target_shift['day']} {target_shift['shift_name']} ({target_shift['required_skill']})")
print(f"   - Currently Assigned: {target_shift['employee_name']} (ID: {target_shift['employee_id']})")

absent_res = post("/api/roster/mark-absent", {
    "shift_id": target_shift["shift_id"],
    "employee_id": target_shift["employee_id"]
})
ranked = absent_res["ranked_replacements"]
print(f"   - Ranked {len(ranked)} replacements:")
for r in ranked[:3]:
    print(f"     Rank: {r['name']} | Score: {r['score']} | Eligible: {r['is_eligible']} | Reasons: {r['reasons']}")
assert len(ranked) > 0
top_eligible = next((c for c in ranked if c["is_eligible"]), None)
assert top_eligible is not None

# Step 8: Pick a replacement
assign_res = post("/api/roster/assign-replacement", {
    "shift_id": target_shift["shift_id"],
    "replacement_employee_id": top_eligible["employee_id"]
})
updated_assignment = next(a for a in assign_res["roster"] if a["shift_id"] == target_shift["shift_id"])
print(f"7. Replacement Assigned! Shift is now covered by: {updated_assignment['employee_name']}")
assert updated_assignment["employee_id"] == top_eligible["employee_id"]

print("\n>>> ALL DEFINITION OF DONE ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY! <<<")
