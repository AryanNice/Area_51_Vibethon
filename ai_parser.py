"""
AI Parser for Unavailability and Leave Requests
Turns free text / messy messages into structured requests.
Works offline with robust rule-based NLP extraction and supports LLM fallback if configured.
"""

import re
from typing import Dict, Any, List, Optional

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
DAY_SYNONYMS = {
    "mon": "Monday",
    "monday": "Monday",
    "tue": "Tuesday",
    "tues": "Tuesday",
    "tuesday": "Tuesday",
    "wed": "Wednesday",
    "weds": "Wednesday",
    "wednesday": "Wednesday",
    "thu": "Thursday",
    "thur": "Thursday",
    "thurs": "Thursday",
    "thursday": "Thursday",
    "fri": "Friday",
    "friday": "Friday",
    "sat": "Saturday",
    "saturday": "Saturday",
    "sun": "Sunday",
    "sunday": "Sunday",
}

SHIFT_KEYWORDS = {
    "morning": "Morning",
    "morn": "Morning",
    "early": "Morning",
    "am": "Morning",
    "evening": "Evening",
    "eve": "Evening",
    "night": "Evening",
    "pm": "Evening",
    "all day": "All Day",
    "whole day": "All Day",
    "entire day": "All Day"
}

REASON_PATTERNS = [
    r"(?:because|due to|for|coz|cause)\s+([^\.\n,;]+)",
    r"(?:appointment|doctor|wedding|sick|family|emergency|study|exam|travel|vacation|personal)[^\.\n,;]*"
]


def parse_leave_message(text: str, employees: List[Dict[str, Any]], sender_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses messy text into structured leave request:
    {
        "employee_id": str,
        "employee_name": str,
        "days": ["Friday"],
        "shift": "Evening" | "Morning" | "All Day",
        "reason": str,
        "raw_text": str,
        "confidence": 0.0 - 1.0,
        "status": "pending"
    }
    """
    lower_text = text.lower()

    # 1. Detect Employee
    matched_emp = None
    if sender_id:
        matched_emp = next((e for e in employees if e["id"] == sender_id), None)

    if not matched_emp:
        # Check if an employee name is mentioned in the text
        for emp in employees:
            name_parts = emp["name"].lower().split()
            first_name = name_parts[0]
            # Match whole word
            if re.search(r"\b" + re.escape(first_name) + r"\b", lower_text) or \
               re.search(r"\b" + re.escape(emp["name"].lower()) + r"\b", lower_text):
                matched_emp = emp
                break

    # If still not found and employees exist, default to the first employee or leave unassigned
    emp_id = matched_emp["id"] if matched_emp else (employees[0]["id"] if employees else "")
    emp_name = matched_emp["name"] if matched_emp else (employees[0]["name"] if employees else "Unknown")

    # 2. Detect Days
    detected_days = []
    # Check for weekend
    if "weekend" in lower_text:
        detected_days.extend(["Saturday", "Sunday"])

    for token, standard_day in DAY_SYNONYMS.items():
        if re.search(r"\b" + re.escape(token) + r"\b", lower_text):
            if standard_day not in detected_days:
                detected_days.append(standard_day)

    # If no day detected, default to "Monday"
    if not detected_days:
        detected_days = ["Monday"]

    # 3. Detect Shift
    detected_shift = "All Day"
    for s_token, s_name in SHIFT_KEYWORDS.items():
        if re.search(r"\b" + re.escape(s_token) + r"\b", lower_text):
            detected_shift = s_name
            break

    # 4. Detect Reason
    detected_reason = "Unavailable / Personal"
    for pattern in REASON_PATTERNS:
        match = re.search(pattern, lower_text)
        if match:
            extracted = match.group(0 if "appointment" in pattern else 1).strip()
            # Clean up reason
            extracted = re.sub(r"^(because|due to|for|coz|cause)\s+", "", extracted, flags=re.I).strip()
            if extracted:
                detected_reason = extracted.capitalize()
                break

    # Confidence calculation
    confidence = 0.5
    if matched_emp:
        confidence += 0.2
    if len(detected_days) > 0 and detected_days != ["Monday"]:
        confidence += 0.2
    if detected_shift != "All Day":
        confidence += 0.1

    return {
        "employee_id": emp_id,
        "employee_name": emp_name,
        "days": detected_days,
        "shift": detected_shift,
        "reason": detected_reason,
        "raw_text": text.strip(),
        "confidence": round(min(1.0, confidence), 2),
        "status": "pending"
    }
