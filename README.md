# AutoRoster | Intelligent Workforce Operations & Shift Scheduling

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**AutoRoster** is a production-ready workforce operations and automated shift scheduling platform designed for retail, hospitality, and healthcare teams. It eliminates the manual chaos of messy unavailability messages, call-outs, and scheduling conflicts using **Google OR-Tools CP-SAT constraint programming** and an **AI Anti-Exploitation Pattern Learning engine**.

---

## 🚀 Deployment Options

### Option 1: Deploy to Streamlit Community Cloud (Recommended • 2 Minutes)

You can deploy AutoRoster directly to **Streamlit Community Cloud** (free hosting provided by Streamlit):

1. **Sign in to Streamlit Cloud**:
   Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account (`AryanNice`).

2. **Create New Application**:
   Click the **"New app"** button in your Streamlit dashboard.

3. **Configure Deployment Settings**:
   - **Repository:** `AryanNice/Area_51_Vibethon`
   - **Branch:** `main`
   - **Main file path:** `streamlit_app.py`
   - **App URL:** (Choose your custom subdomain or use the default, e.g. `autoroster.streamlit.app`)

4. **Add Secrets (Optional for Gemini AI)**:
   Click **Advanced settings > Secrets** and paste your Gemini API key:
   ```toml
   GEMINI_API_KEY = "your-gemini-api-key"
   ```
   *(Note: AutoRoster includes a resilient local NLP engine fallback, so the app operates with 100% functionality even without an external API key).*

5. **Deploy**:
   Click **"Deploy!"**. Streamlit Cloud will install `requirements.txt` and launch your live public web application within seconds.

---

### Option 2: Run Streamlit Locally

To run the Streamlit interface on your local workstation:

```bash
# 1. Clone repository
git clone https://github.com/AryanNice/Area_51_Vibethon.git
cd Area_51_Vibethon

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch Streamlit
streamlit run streamlit_app.py
```
Your browser will open automatically at **`http://localhost:8501`**.

---

### Option 3: Run the Native REST API & Enterprise Web Portal

AutoRoster also includes a standalone Python standard library HTTP server (`server.py`) with zero framework runtime overhead:

```bash
# Start standard library HTTP server
python server.py

# Open web portal in your browser:
# http://localhost:8000
```

---

## 🔑 System Roles & Access Credentials

AutoRoster features role-based access control (RBAC). You can sign in using either full emails or quick username aliases:

| Role | Username / Email | Password | Access Capabilities |
| :--- | :--- | :--- | :--- |
| **Store Manager** | `admin` or `admin@vibecafe.com` | `admin` or `admin123` | Staff Directory, Add Team Members, Leave Decision Log, Urgent Medical Queue, CP-SAT Weekly Roster Planner, Shift Cover Audit Log |
| **Staff Member** | `alex` or `alex@vibecafe.com` | `employee` or `employee123` | Natural Language Leave Intake, Medical Certificate PDF Upload, Weekly Personal Schedule with Extra Cover Shift Badges |
| **Staff Member** | `bianca` or `bianca@vibecafe.com` | `employee` or `employee123` | Employee self-service portal |

---

## 🌟 Core System Workflows

### 1. Medical Leave & PDF Verification Workflow
- **Employee Portal**: Employees can flag a leave request as an *"Urgent medical condition requiring verification"* and upload official clinical documentation (Doctor's Note, Clinic Form, or Discharge Certificate in `.pdf`, `.png`, or `.jpg` format).
- **Manager Portal**: Emergency medical requests are routed directly to the **🚨 Urgent Medical Requests Queue**. Managers can inspect the diagnosis, view verification metadata, and click **📥 Download & Inspect Submitted PDF** to review the actual uploaded medical document before approving or rejecting.

### 2. Google OR-Tools CP-SAT Constraint Scheduler
AutoRoster models workforce scheduling as an exact Integer Programming / Constraint Satisfaction Problem (CSP) using **Google OR-Tools CP-SAT**:
- **Shift Coverage:** Guaranteed minimum staffing across Morning and Evening shifts Monday through Sunday.
- **Skill Certification:** Enforces that only qualified staff fill required roles (`Supervisor`, `Barista`, `Cook`, `Cashier`, `Server`).
- **Fair Workload Objective:** Uses an absolute-deviation fairness objective (`AddAbsEquality` around target hours) to balance work loads, preventing burnout while guaranteeing that supervisors and key personnel maintain available headroom for replacement emergencies.
- **Max Hours & Rest Limits:** Strictly caps weekly hours (16h–40h) and prevents assigning more than one shift per employee per day.

### 3. Dynamic Call-Outs & Ranked Shift Cover
When an employee calls out sick:
1. Manager marks the shift **Absent** on the weekly roster.
2. The engine evaluates all eligible replacements using multi-criteria scoring:
   - Skill qualification and certifications.
   - Remaining weekly hour headroom.
   - Fair workload balance across available staff.
3. Manager assigns the replacement in one click.
4. The shift is automatically updated, logged in the **Shift Cover Audit Trail**, and visually flagged on the covering employee's personal schedule as an extra substitute shift.

### 4. AI Pattern Learning & Anti-Exploitation Engine
Prevents scheduling abuse through historical attendance analysis:
- **Reason Taxonomy:** Categorizes requests into `CRITICAL`, `HIGH`, `MEDIUM`, and `LOW` priority.
- **Pattern Learning:** Tracks each employee's leave frequency, historical approval ratios, and suspicious clustering (e.g., repeatedly requesting Friday evenings or Monday mornings off).
- **Exploitation Scoring:** Calculates a real-time risk score ($0\% - 100\%$) and provides policy explanations for every leave decision.

---

## 🧪 Automated Test Suite

AutoRoster includes an automated integration and unit test suite covering authentication, CP-SAT solver constraints, leave auto-approval, anti-exploitation pattern rejection, urgent PDF attachments, and personal schedule rendering:

```bash
python -m unittest discover tests
```

Output:
```text
Ran 17 tests in 0.320s
OK
```

---

## 📁 Repository Structure

```
Area_51_Vibethon/
├── streamlit_app.py      # Production Streamlit application
├── requirements.txt      # Streamlit Community Cloud dependency list
├── .streamlit/
│   └── config.toml       # Streamlit enterprise theme configuration
├── server.py             # Standalone REST API server (Python standard library)
├── static/               # HTML/CSS/JS frontend assets
│   ├── index.html        # Web app HTML template
│   ├── styles.css        # Enterprise design system styles
│   └── app.js            # Frontend JavaScript application logic
├── app/
│   ├── models.py         # Data models (Employee, LeaveRequest, RosterSlot, etc.)
│   ├── database.py       # In-memory thread-safe store with reset & audit tracking
│   ├── solver.py         # Google OR-Tools CP-SAT constraint solver
│   ├── pattern_learning.py # AI anti-exploitation & reason importance engine
│   ├── replacement.py    # Ranked absence replacement matching engine
│   ├── ai_parser.py      # Natural language availability extractor
│   └── seed_data.py      # Default seed staff, shift templates, and sample records
└── tests/
    ├── test_api.py       # REST API integration tests
    ├── test_portal.py    # RBAC, leave logs, urgent proofs, and personal roster tests
    └── test_solver.py    # CP-SAT constraint validation & fairness tests
```

---

## 📄 License

This project is licensed under the MIT License.
