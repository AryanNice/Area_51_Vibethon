"""
Pre-loaded seed data for AutoRoster MVP.
Ensures zero-friction 1-click demos.
"""
from typing import List, Dict
from app.models import Employee, ShiftRoleRequirement, LeaveRequest

INITIAL_EMPLOYEES: List[Employee] = [
    Employee(
        id="emp-1",
        name="Alex Rivera",
        skills=["Supervisor", "Barista", "Cashier"],
        max_weekly_hours=40,
        email="alex.r@vibecafé.com",
        phone="555-0101"
    ),
    Employee(
        id="emp-2",
        name="Bianca Chen",
        skills=["Barista", "Cashier", "Server"],
        max_weekly_hours=32,
        email="bianca.c@vibecafé.com",
        phone="555-0102"
    ),
    Employee(
        id="emp-3",
        name="Carlos Gomez",
        skills=["Cook", "Server"],
        max_weekly_hours=40,
        email="carlos.g@vibecafé.com",
        phone="555-0103"
    ),
    Employee(
        id="emp-4",
        name="Dana Patel",
        skills=["Supervisor", "Cook"],
        max_weekly_hours=32,
        email="dana.p@vibecafé.com",
        phone="555-0104"
    ),
    Employee(
        id="emp-5",
        name="Ethan Wright",
        skills=["Cashier", "Server"],
        max_weekly_hours=32,
        email="ethan.w@vibecafé.com",
        phone="555-0105"
    ),
    Employee(
        id="emp-6",
        name="Fiona Gallagher",
        skills=["Barista", "Server"],
        max_weekly_hours=32,
        email="fiona.g@vibecafé.com",
        phone="555-0106"
    ),
    Employee(
        id="emp-7",
        name="George Miller",
        skills=["Cook", "Supervisor", "Cashier"],
        max_weekly_hours=40,
        email="george.m@vibecafé.com",
        phone="555-0107"
    ),
    Employee(
        id="emp-8",
        name="Hannah Abbott",
        skills=["Server", "Barista", "Cashier"],
        max_weekly_hours=32,
        email="hannah.a@vibecafé.com",
        phone="555-0108"
    ),
]

# Standard Weekly Cafe Schedule Template:
# Monday to Friday:
#   Morning (8h): Supervisor, Barista (2 staff)
#   Evening (8h): Cook, Server (2 staff)
# Saturday & Sunday:
#   Morning (8h): Supervisor, Barista, Server (3 staff)
#   Evening (8h): Cook, Cashier, Server (3 staff)
# Total = 10 shifts * 2 roles (20) + 4 shifts * 3 roles (12) = 32 slots * 8h = 256 hrs.
# Total staff capacity = 280 hrs. Feasible with balanced distribution.

DEFAULT_SHIFT_REQUIREMENTS: List[ShiftRoleRequirement] = [
    # Monday
    ShiftRoleRequirement("Monday", "Morning", "Supervisor"),
    ShiftRoleRequirement("Monday", "Morning", "Barista"),
    ShiftRoleRequirement("Monday", "Evening", "Cook"),
    ShiftRoleRequirement("Monday", "Evening", "Server"),
    # Tuesday
    ShiftRoleRequirement("Tuesday", "Morning", "Supervisor"),
    ShiftRoleRequirement("Tuesday", "Morning", "Barista"),
    ShiftRoleRequirement("Tuesday", "Evening", "Cook"),
    ShiftRoleRequirement("Tuesday", "Evening", "Cashier"),
    # Wednesday
    ShiftRoleRequirement("Wednesday", "Morning", "Supervisor"),
    ShiftRoleRequirement("Wednesday", "Morning", "Barista"),
    ShiftRoleRequirement("Wednesday", "Evening", "Cook"),
    ShiftRoleRequirement("Wednesday", "Evening", "Server"),
    # Thursday
    ShiftRoleRequirement("Thursday", "Morning", "Supervisor"),
    ShiftRoleRequirement("Thursday", "Morning", "Cashier"),
    ShiftRoleRequirement("Thursday", "Evening", "Cook"),
    ShiftRoleRequirement("Thursday", "Evening", "Server"),
    # Friday
    ShiftRoleRequirement("Friday", "Morning", "Supervisor"),
    ShiftRoleRequirement("Friday", "Morning", "Barista"),
    ShiftRoleRequirement("Friday", "Evening", "Cook"),
    ShiftRoleRequirement("Friday", "Evening", "Server"),
    # Saturday (Weekend Rush)
    ShiftRoleRequirement("Saturday", "Morning", "Supervisor"),
    ShiftRoleRequirement("Saturday", "Morning", "Barista"),
    ShiftRoleRequirement("Saturday", "Morning", "Server"),
    ShiftRoleRequirement("Saturday", "Evening", "Cook"),
    ShiftRoleRequirement("Saturday", "Evening", "Cashier"),
    ShiftRoleRequirement("Saturday", "Evening", "Server"),
    # Sunday (Weekend Rush)
    ShiftRoleRequirement("Sunday", "Morning", "Supervisor"),
    ShiftRoleRequirement("Sunday", "Morning", "Barista"),
    ShiftRoleRequirement("Sunday", "Morning", "Server"),
    ShiftRoleRequirement("Sunday", "Evening", "Cook"),
    ShiftRoleRequirement("Sunday", "Evening", "Cashier"),
    ShiftRoleRequirement("Sunday", "Evening", "Server"),
]

# Quick demo messy messages ready to insert with 1-click
SAMPLE_MESSY_MESSAGES = [
    {
        "employee_id": "emp-2",
        "employee_name": "Bianca Chen",
        "text": "Hey boss! My dentist moved my appointment to Tuesday morning, so I won't be able to come in for the morning shift. Can still do evening though!"
    },
    {
        "employee_id": "emp-1",
        "employee_name": "Alex Rivera",
        "text": "Yo! My sister is getting married out of town on Friday, so I need Friday evening off. Thanks!"
    },
    {
        "employee_id": "emp-3",
        "employee_name": "Carlos Gomez",
        "text": "Hi manager, feeling awful with flu. Doctor says bed rest this Wednesday whole day."
    },
    {
        "employee_id": "emp-4",
        "employee_name": "Dana Patel",
        "text": "Hey there, university exam schedule just released. I have an exam on Saturday morning so unavailable Saturday Morning."
    }
]

INITIAL_LEAVE_REQUESTS: List[LeaveRequest] = [
    LeaveRequest(
        id="leave-seed-1",
        employee_id="emp-2",
        employee_name="Bianca Chen",
        raw_text="Doctor appointment on Tuesday morning, cannot work morning shift.",
        day_of_week="Tuesday",
        shift_type="Morning",
        reason="Doctor appointment",
        status="APPROVED",
        confidence=0.98,
        explanation="Extracted day: Tuesday, shift: Morning, reason: Medical/Doctor"
    )
]
