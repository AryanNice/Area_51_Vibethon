# ⏱️ AutoRoster AI: 3-Minute Hackathon Demo Script
**Role:** Member 3 Presentation Guide  
**Total Time:** Exactly 3 Minutes (180 Seconds)  
**Target Audience:** Hackathon Judges & Shift Managers  

---

### **Pre-Demo Checklist (10 seconds before starting)**
1. Terminal open: `python server.py` running at `http://localhost:8000`.
2. Browser open at `http://localhost:8000`.
3. Screen set on **Screen 1 (Staff & Skills)** with pristine seed data loaded.

---

### **Minute 0:00 – 0:45 | The Problem & Screen 1 (Staff & Skills)**
- **Speaker:**  
  > *"Every week, over 1.2 million hospitality and retail managers lose 6+ hours doing what I call the 'Sunday Roster Nightmare'. They balance sticky notes, broken Excel spreadsheets, and dozens of frantic WhatsApp messages from staff.*
  >
  > *Welcome to **AutoRoster AI**—the hard-constraint scheduling platform that turns messy human requests into mathematically guaranteed, conflict-free rosters in milliseconds."*

- **Action on Screen 1 (Staff & Skills):**
  1. Show the **Staff Directory**:
     > *"Here is our team: 8 pre-seeded employees with real-world skills like Barista, Cook, Cashier, and Supervisor, plus weekly hour caps."*
  2. Quickly demonstrate form validation:
     - Type a new employee name: `Jordan Bell`
     - Check `Barista` and set weekly cap to `32h`
     - Click **Add Employee**:
     > *"Notice that inputs are validated live, with clean error handling and immediate updates—never raw stack traces."*

---

### **Minute 0:45 – 1:30 | Screen 2: AI Availability & Leave Ingestion**
- **Speaker:**  
  > *"Staff don't submit availability through complicated forms—they send messy messages on WhatsApp."*

- **Action on Screen 2 (AI Leave & Availability):**
  1. Click **Screen 2: AI Leave & Availability**.
  2. Click the 1st Demo Preset:
     - *"Hey boss! My dentist moved my appointment to Tuesday morning, so I won't be able to come in for the morning shift. Can still do evening though!"*
  3. Click **Parse with AI**:
     > *"Watch this: our NLP parser extracts Day='Tuesday', Shift='Morning', and Reason='Dentist/Medical' with 96% confidence."*
  4. Click **Submit to Manager Queue**:
     > *"It lands in the manager's queue. The manager sees the structured card alongside the original quote and clicks **Approve**."*
  5. Click **Approve** (badge turns green).

---

### **Minute 1:30 – 2:15 | Screen 3: The Hard-Constraint Solver & Truthful Conflicts**
- **Speaker:**  
  > *"Now for the core engine: generating the master schedule."*

- **Action on Screen 3 (Weekly Roster & Solver):**
  1. Click **Screen 3: Weekly Roster & Solver**.
  2. Click **✨ Generate Weekly Roster**:
     > *"In under 5 milliseconds, our Constraint Satisfaction Solver fills all 32 shift slots across all 7 days. It strictly enforces 5 hard rules: shift coverage, approved leave, required skills, max weekly hours, and max 1 shift per day."*
  3. Show the green banner and staff hour meters (e.g., Alex: 32/40h, Bianca: 24/32h).
  4. Now reveal our **Unfair Advantage**:
     > *"Most AI schedulers hallucinate: they fake a schedule or quietly violate labor laws when constraints clash. We strictly believe in truth."*
  5. Click **⚠️ Trigger Impossible Scenario**:
     > *"Here, all qualified supervisors took Friday morning off. Watch the solver: it immediately halts, refuses to fake a schedule, and pinpoints the exact mathematical bottleneck in plain English: 'Unfillable Shift: Friday Morning (Supervisor). All qualified staff on approved leave.' It even tells the manager the remedy: renegotiate leave."*
  6. Click **🔄 Reset Seed Data** in the top bar to return to pristine state, and click **✨ Generate Weekly Roster** again.

---

### **Minute 2:15 – 3:00 | Screen 4: Absence & Ranked Replacements & The Close**
- **Speaker:**  
  > *"It's Friday afternoon. Carlos Gomez calls out sick with food poisoning. The shift starts in 2 hours. What does the manager do?"*

- **Action on Screen 4 (Absence & Replacements):**
  1. On the roster, find Carlos Gomez on Friday Evening (Cook) and click **Mark Absent**.
  2. The app jumps seamlessly into **Screen 4**:
     - Shows Vacant Shift: `Friday Evening Cook`.
     - Click **Mark Staff Absent & Find Replacements**.
  3. Explain the Ranked Candidates:
     > *"The algorithm immediately evaluates the entire team against hard constraints:
     > - Below, it explains why 6 staff are **Ineligible**: Alex is already working Friday Morning (max 1 shift/day rule), Bianca lacks Cook skills, and Ethan would exceed weekly overtime limits.
     > - At the top, it ranks **Eligible Candidates** by remaining burnout headroom and skill specialization. Dana Patel is #1 with 16h of headroom."*
  4. Click **Assign Cover**:
     > *"1 click. Dana is assigned, the roster is patched, and hours are updated. Zero panic."*

- **Speaker Closing Pitch (Final 15 seconds):**
  > *"AutoRoster AI replaces 6 hours of weekend stress with 4 deterministic clicks. No spreadsheets, no hallucinations, no overtime leaks. Thank you!"*
