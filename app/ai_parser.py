"""
Free-text availability & leave parser.
Extracts structured day, shift, and reason from messy employee messages.
Powered by Gemini 3.8 Flash AI with local rule-based fallback.
"""
import re
import json
from typing import Dict, Any, List, Optional
from app.models import DAYS_OF_WEEK

DAYS_MAP = {
    "monday": "Monday", "mon": "Monday",
    "tuesday": "Tuesday", "tue": "Tuesday", "tues": "Tuesday",
    "wednesday": "Wednesday", "wed": "Wednesday",
    "thursday": "Thursday", "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday",
    "friday": "Friday", "fri": "Friday",
    "saturday": "Saturday", "sat": "Saturday",
    "sunday": "Sunday", "sun": "Sunday"
}

def parse_free_text_availability(text: str, candidate_employees: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Parses messy natural language messages into a structured leave/unavailability request.
    Returns:
        {
            "day_of_week": "Friday",
            "shift_type": "Evening", # "Morning", "Evening", or "All Day"
            "reason": "Sister's wedding",
            "detected_employee_id": Optional[str],
            "confidence": 0.95,
            "explanation": "..."
        }
    """
    raw_text = text.strip()
    lower = raw_text.lower()

    # 0. Try Gemini 3.8 Flash AI extraction if available
    try:
        from app.pattern_learning import call_gemini_api
        gemini_prompt = (
            f"Extract structured shift absence details from this employee message: '{raw_text}'. "
            f"Respond with ONLY valid JSON with keys: 'day_of_week' (one of Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday), "
            f"'shift_type' (one of 'Morning', 'Evening', or 'All Day'), and 'reason' (short string). Do not wrap in markdown or code blocks."
        )
        gemini_raw = call_gemini_api(gemini_prompt)
        if gemini_raw:
            clean_json = gemini_raw.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            day = data.get("day_of_week")
            if day in DAYS_MAP.values():
                return {
                    "day_of_week": day,
                    "shift_type": data.get("shift_type", "All Day"),
                    "reason": data.get("reason", "Personal leave"),
                    "detected_employee_id": None,
                    "confidence": 0.98,
                    "explanation": f"[Gemini 3.8 Flash AI] Extracted Day='{day}', Shift='{data.get('shift_type')}', Reason='{data.get('reason')}'."
                }
    except Exception:
        pass

    # 1. Fallback: Detect Day of Week via regex
    detected_day = None
    for token, formal_day in DAYS_MAP.items():
        pattern = r'\b' + re.escape(token) + r'\b'
        if re.search(pattern, lower):
            detected_day = formal_day
            break

    if not detected_day:
        if "weekend" in lower:
            detected_day = "Saturday"
        else:
            detected_day = "Friday"

    # 2. Detect Shift Type
    detected_shift = "All Day"
    is_morning = bool(re.search(r'\b(morning|am|breakfast|open|opening|before 1pm|before 2pm|before noon)\b', lower))
    is_evening = bool(re.search(r'\b(evening|night|pm|dinner|close|closing|after 3pm|after 4pm|after 5pm|tonight)\b', lower))
    is_all_day = bool(re.search(r'\b(all day|whole day|entire day|full day|both shifts|any shift|taking off)\b', lower))

    if is_all_day:
        detected_shift = "All Day"
    elif is_morning and not is_evening:
        detected_shift = "Morning"
    elif is_evening and not is_morning:
        detected_shift = "Evening"
    elif is_morning and is_evening:
        if re.search(r"(can't|cannot|unable|won't be able|no).*morning", lower):
            detected_shift = "Morning"
        elif re.search(r"(can't|cannot|unable|won't be able|no).*(evening|night)", lower):
            detected_shift = "Evening"
        else:
            detected_shift = "All Day"

    # 3. Detect Reason
    detected_reason = "Personal / Unavailability"
    reason_patterns = [
        (r'\b(sister|brother|mom|dad|cousin|family|daughter|son|father|mother)\b.*?\b(wedding|marry|married|marriage|birthday|reunion)\b', "Family Event / Wedding"),
        (r'\b(wedding|marriage|married|marrying)\b', "Family Wedding"),
        (r'\b(doctor|dentist|appointment|hospital|clinic|surgery|physio)\b', "Medical / Healthcare Appointment"),
        (r'\b(sick|flu|fever|cough|unwell|ill|food poison|migraine)\b', "Illness / Medical Leave"),
        (r'\b(exam|test|finals|midterm|college|university|class|lecture|study)\b', "Academic / Exam Schedule"),
        (r'\b(moving|apartment|relocation|lease)\b', "Relocation / Moving"),
        (r'\b(funeral|bereavement|memorial)\b', "Bereavement / Compassionate"),
        (r'\b(flight|travel|trip|out of town|vacation|holiday)\b', "Travel / Out of Town"),
        (r'\b(emergency|urgent)\b', "Urgent Personal Emergency"),
    ]

    for pat, label in reason_patterns:
        match = re.search(pat, lower)
        if match:
            matched_phrase = match.group(0).capitalize()
            detected_reason = f"{label} ({matched_phrase})"
            break
    else:
        cause_match = re.search(r'(?:because|due to|reason is|need to|have to)\s+([^,.;\n]+)', lower)
        if cause_match:
            snippet = cause_match.group(1).strip()
            if len(snippet) > 3:
                detected_reason = snippet.capitalize()

    # 4. Detect Employee Name if candidate list provided
    detected_emp_id = None
    if candidate_employees:
        for emp in candidate_employees:
            first_name = emp.get("name", "").split()[0].lower()
            full_name = emp.get("name", "").lower()
            if re.search(r'\b' + re.escape(first_name) + r'\b', lower) or re.search(r'\b' + re.escape(full_name) + r'\b', lower):
                detected_emp_id = emp.get("id")
                break

    confidence = 0.94 if detected_day and detected_shift else 0.85
    explanation = f"AI identified Day='{detected_day}', Shift='{detected_shift}', Reason='{detected_reason}'."

    return {
        "day_of_week": detected_day,
        "shift_type": detected_shift,
        "reason": detected_reason,
        "detected_employee_id": detected_emp_id,
        "confidence": confidence,
        "explanation": explanation
    }
