# AutoRoster AI (Area 51 Vibethon MVP)

> **Autonomous Workforce Operations MVP**  
> *From messy WhatsApp availability messages to a mathematically guaranteed, conflict-free weekly schedule in 4 clicks.*

---

## 🌟 Quickstart (Run Locally)

AutoRoster combines **Google OR-Tools CP-SAT** constraint programming with a pure Python standard library fallback. It can run in any environment:

```bash
# 1. (Optional) Install ortools for CP-SAT solver acceleration:
pip install ortools

# 2. Start the local server:
python server.py

# 2. Open your browser at:
# http://localhost:8000
```

To run the automated test suite (11/11 tests across CSP solver, NLP parser, and REST API):
```bash
python -m unittest discover tests
```

---

## 🎯 The 4 Core MVP Screens

### Screen 1: Add Employees & Skills
- Pre-loaded with realistic seed team (8 staff with varied roles: Supervisor, Barista, Cook, Cashier, Server, and weekly hour caps).
- Intuitive form to register new employees, assign skills via tag chips, and set weekly hour ceilings (16h - 40h).
- Real-time form validation with inline alerts (no raw stack traces).
- 1-click **Reset Seed Data** to instantly restore pristine state during presentations.

### Screen 2: AI Availability & Leave Ingestion
- Ingests raw, messy free-text messages (e.g., *"Sister getting married Friday evening"*, *"Dentist appointment Tuesday morning"*, *"Bed rest Wednesday all day"*).
- Includes **1-Click Messy Message Presets** for snappy live demoing.
- Intelligent NLP extraction detects: Day of Week, Shift Type (Morning, Evening, All Day), Reason category, Confidence score, and Explanation.
- Manager Approval Queue: One-click **Approve** or **Reject** actions.

### Screen 3: Weekly Master Roster & Conflict Solver
- **Google OR-Tools CP-SAT Solver (Member 1 Core):** Mathematical integer constraint programming solver enforcing all 5 non-negotiable hard constraints:
  1. Shift coverage
  2. Approved unavailability/leave
  3. Required certified skills
  4. Weekly hour limit
  5. Max one shift per day
- **Never Fakes a Result:** Solves in milliseconds with global mathematical proof.
- **Truthful Conflict Explainer:** Includes a **"Trigger Impossible Scenario"** button (simulating all supervisors on leave for Friday morning). The solver immediately pinpoints the exact mathematical bottleneck and specifies the contributing factors and recommended action.
- Interactive 7-day calendar grid (Monday through Sunday, Morning and Evening shifts).

### Screen 4: Absence & Ranked Replacements
- When an employee calls out (e.g. sick with flu), click **Mark Absent** on any shift in Screen 3.
- Instant Candidate Evaluation:
  - **Ineligible Staff Breakdown:** Explains why non-candidates cannot cover (e.g., already working another shift on the same day, missing skill, on approved leave, or exceeds weekly hour limit).
  - **Ranked Replacements:** Evaluates all eligible substitutes with transparent scoring based on burnout headroom, skill specialization, and fair utilization balance.
- 1-Click **Assign Cover** to patch the schedule and recalculate staff load.

---

## 📋 Definition of Done Verification Checklist

| Requirement | Status | How to Verify Locally |
| :--- | :--- | :--- |
| **1. Add Employee** | ✅ Passed | Go to Screen 1 -> Enter name, select skills -> click "Add Employee". Seed data is preloaded. |
| **2. Submit Messy Message** | ✅ Passed | Go to Screen 2 -> Click any quick messy preset chip -> click "Parse with AI" -> click "Submit" -> click "Approve". |
| **3. Generate Roster** | ✅ Passed | Go to Screen 3 -> Click "✨ Generate Weekly Roster". Solves in < 5ms. |
| **3b. Explain Impossible Case** | ✅ Passed | Click "⚠️ Trigger Impossible Scenario" -> Solver proves infeasibility and explains the exact supervisor shortage on Friday morning. |
| **4. Mark Absent & Replace** | ✅ Passed | Go to Screen 3, click "Mark Absent" on any slot -> In Screen 4, view ranked candidates and ineligibility reasons -> Click "Assign Cover". |
| **Zero Raw Stack Traces** | ✅ Passed | All client and server errors return user-friendly, actionable messages. |
| **Pitch & Demo Script** | ✅ Passed | See [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md), [`PITCH_DECK.md`](PITCH_DECK.md), or click the in-app "Pitch & Demo Guide" tab. |

---

## 🚫 Non-Goals (Strictly Respected)
- No CSV import
- No deployment
- No roster publishing
- No demand forecasting
- No payroll
- No mobile app
- No real WhatsApp integration

---

## 🏗️ Architecture & File Structure

```
Area_51_Vibethon/
├── app/
│   ├── __init__.py
│   ├── database.py       # In-memory thread-safe store with seed reset
│   ├── models.py         # Data models (Employee, LeaveRequest, RosterSlot, etc.)
│   ├── seed_data.py      # Seed employees, shift templates, demo messages
│   ├── ai_parser.py      # Free-text NLP availability extractor
│   ├── solver.py         # Constraint Satisfaction Problem (CSP) solver
│   └── replacement.py    # Ranked absence replacement engine
├── static/
│   ├── index.html        # Single-page UI for the 4 screens + demo guide
│   ├── styles.css        # Clean responsive styling & design system
│   └── app.js            # Frontend state, API integration, validation
├── server.py             # Python standard library REST API server
├── tests/
│   ├── test_solver.py    # Solver & NLP unit tests
│   └── test_api.py       # Full HTTP integration test suite
├── DEMO_SCRIPT.md        # 3-Minute live demo guide (Member 3)
├── PITCH_DECK.md         # Pitch outline & judge presentation (Member 3)
└── README.md             # Project documentation
```
