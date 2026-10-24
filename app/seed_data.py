"""
Pre-loaded seed data for AutoRoster.
Ensures zero-friction 1-click demos.
"""
from typing import List, Dict
from app.models import Employee, ShiftRoleRequirement, LeaveRequest, ReplacementAudit

ADMIN_USER = {
    "id": "admin-1",
    "name": "Sarah Connor (General Manager)",
    "email": "admin@vibecafe.com",
    "password": "admin123",
    "role": "admin"
}

INITIAL_EMPLOYEES: List[Employee] = [
    Employee(
        id="emp-1",
        name="Alex Rivera",
        skills=["Supervisor", "Barista", "Cashier"],
        max_weekly_hours=40,
        email="alex@vibecafe.com",
        phone="555-0101",
        password="employee123",
        role="employee"
    ),
    Employee(
        id="emp-2",
        name="Bianca Chen",
        skills=["Barista", "Cashier", "Server"],
        max_weekly_hours=32,
        email="bianca@vibecafe.com",
        phone="555-0102",
        password="employee123",
        role="employee"
    ),
    Employee(
        id="emp-3",
        name="Carlos Gomez",
        skills=["Cook", "Server"],
        max_weekly_hours=40,
        email="carlos@vibecafe.com",
        phone="555-0103",
        password="employee123",
        role="employee"
    ),
    Employee(
        id="emp-4",
        name="Dana Patel",
        skills=["Supervisor", "Cook"],
        max_weekly_hours=32,
        email="dana@vibecafe.com",
        phone="555-0104",
        password="employee123",
        role="employee"
    ),
    Employee(
        id="emp-5",
        name="Ethan Wright",
        skills=["Cashier", "Server"],
        max_weekly_hours=32,
        email="ethan@vibecafe.com",
        phone="555-0105",
        password="employee123",
        role="employee"
    ),
    Employee(
        id="emp-6",
        name="Fiona Gallagher",
        skills=["Barista", "Server"],
        max_weekly_hours=32,
        email="fiona@vibecafe.com",
        phone="555-0106",
        password="employee123",
        role="employee"
    ),
    Employee(
        id="emp-7",
        name="George Miller",
        skills=["Cook", "Supervisor", "Cashier"],
        max_weekly_hours=40,
        email="george@vibecafe.com",
        phone="555-0107",
        password="employee123",
        role="employee"
    ),
    Employee(
        id="emp-8",
        name="Hannah Abbott",
        skills=["Server", "Barista", "Cashier"],
        max_weekly_hours=32,
        email="hannah@vibecafe.com",
        phone="555-0108",
        password="employee123",
        role="employee"
    ),
]

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
    ShiftRoleRequirement("Thursday", "Evening", "Barista"),
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
        "text": "Hi manager, feeling awful with severe acute fever. Doctor ordered complete bed rest this Wednesday whole day."
    },
    {
        "employee_id": "emp-4",
        "employee_name": "Dana Patel",
        "text": "Hey there, university exam schedule just released. I have a critical midterm exam on Saturday morning so unavailable Saturday Morning."
    },
    {
        "employee_id": "emp-5",
        "employee_name": "Ethan Wright",
        "text": "Hey boss, just wanted to chill this Friday evening with the boys. Not feeling like coming in."
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
        reason="Medical / Healthcare Appointment (Doctor)",
        status="APPROVED",
        confidence=0.98,
        explanation="Extracted day: Tuesday, shift: Morning, reason: Medical/Doctor",
        reason_importance="HIGH",
        exploitation_risk_score=0.12,
        pattern_analysis="Pattern Analysis: First leave request in 30 days. No weekend-clustering pattern detected. Legitimate healthcare reason."
    ),
    LeaveRequest(
        id="leave-urgent-seed",
        employee_id="emp-3",
        employee_name="Carlos Gomez",
        raw_text="Urgent: Sudden severe food poisoning and gastroenteritis. Attached emergency clinic discharge certificate.",
        day_of_week="Wednesday",
        shift_type="All Day",
        reason="Acute Gastroenteritis & Medical Bed Rest",
        status="PENDING",
        confidence=0.99,
        explanation="Emergency medical leave submitted with verified clinical doctor proof.",
        is_urgent=True,
        proof_filename="St_Mary_Hospital_Discharge_Certificate.pdf",
        proof_data_url="data:application/pdf;base64,JVBERi0xLjQKJcTl8uXr...",
        reason_importance="CRITICAL",
        exploitation_risk_score=0.05,
        pattern_analysis="Pattern Analysis: Urgent medical emergency with uploaded proof. Low abuse risk. Routed directly to Manager approval queue."
    )
]

INITIAL_REPLACEMENT_AUDITS: List[ReplacementAudit] = [
    ReplacementAudit(
        id="rep-audit-1",
        slot_id="slot-demo-1",
        day_of_week="Tuesday",
        shift_type="Morning",
        role="Barista",
        original_employee_id="emp-2",
        original_employee_name="Bianca Chen",
        replaced_by_id="emp-6",
        replaced_by_name="Fiona Gallagher",
        reason="Covering for approved dentist appointment"
    )
]
