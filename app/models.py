"""
Data models for AutoRoster MVP.
Strictly hard constraints only.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import uuid
import datetime

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SHIFT_TYPES = ["Morning", "Evening"]
SHIFT_HOURS = {"Morning": 8, "Evening": 8}
AVAILABLE_SKILLS = ["Supervisor", "Barista", "Cook", "Cashier", "Server"]

@dataclass
class Employee:
    id: str
    name: str
    skills: List[str]
    max_weekly_hours: int = 40
    email: str = ""
    phone: str = ""
    password: str = "employee123"
    role: str = "employee"  # "admin" or "employee"

    def to_dict(self):
        return asdict(self)

@dataclass
class LeaveRequest:
    id: str
    employee_id: str
    employee_name: str
    raw_text: str
    day_of_week: str  # Monday - Sunday
    shift_type: str   # Morning, Evening, or All Day
    reason: str
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    confidence: float = 1.0
    explanation: str = ""
    created_at: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    is_urgent: bool = False
    proof_filename: Optional[str] = None
    proof_data_url: Optional[str] = None
    ai_decision: Optional[str] = "PENDING"  # APPROVED, REJECTED, PENDING_MANAGER
    reason_importance: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW
    exploitation_risk_score: float = 0.0
    pattern_analysis: str = ""

    def to_dict(self):
        return asdict(self)

@dataclass
class ShiftRoleRequirement:
    day_of_week: str
    shift_type: str
    role: str
    hours: int = 8

    def to_dict(self):
        return asdict(self)

@dataclass
class RosterSlot:
    id: str
    day_of_week: str
    shift_type: str
    role: str
    hours: int
    assigned_employee_id: Optional[str] = None
    assigned_employee_name: Optional[str] = None
    is_absent: bool = False
    absent_reason: Optional[str] = None
    replaced_by_id: Optional[str] = None
    replaced_by_name: Optional[str] = None

    def to_dict(self):
        return asdict(self)

@dataclass
class ConflictDetail:
    day_of_week: str
    shift_type: str
    role: str
    reason: str
    contributing_factors: List[str]
    suggested_action: str

    def to_dict(self):
        return asdict(self)

@dataclass
class ReplacementAudit:
    id: str
    slot_id: str
    day_of_week: str
    shift_type: str
    role: str
    original_employee_id: str
    original_employee_name: str
    replaced_by_id: str
    replaced_by_name: str
    reason: str = "Unplanned Absence"
    created_at: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self):
        return asdict(self)
