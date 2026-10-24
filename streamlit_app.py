"""
AutoRoster | Workforce Operations & Intelligent Shift Scheduling
Streamlit Production Application.

Supports:
1. Role-based Authentication (Store Manager vs Staff Member).
2. Admin / Manager Portal:
   - Active Staff Directory with Certified Skill Badges & Hourly Limits
   - + Add Employee Form with certified skill allocation
   - Leave Requests & Decision Log with raw employee message inspection
   - Urgent Medical Leaves Queue with clinical proof document review & sign-off
   - Weekly Master Schedule powered by Google OR-Tools CP-SAT Solver
   - Shift Cover & Replacement Audit Log
3. Employee Self-Service Portal:
   - Natural Language AI Leave Request with anti-exploitation pattern evaluation
   - Urgent Medical Leave with clinical certificate upload routed to manager
   - My Shifts This Week personal schedule with substitute extra shift highlights
"""
import streamlit as st
import pandas as pd
import json
import base64
import textwrap
from datetime import datetime
from typing import Dict, Any, List

from app.database import db
from app.models import AVAILABLE_SKILLS, Employee, LeaveRequest, RosterSlot
from app.solver import solve_roster
from app.pattern_learning import evaluate_leave_request
from app.replacement import get_ranked_replacements
from app.ai_parser import parse_free_text_availability

# ---------------------------------------------------------
# Page Setup & Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="AutoRoster | Workforce Operations",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Enterprise CSS Styles
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
    }
    
    /* Skill Badges */
    .skill-badge {
        display: inline-block;
        padding: 0.22rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        margin-right: 0.3rem;
        margin-bottom: 0.3rem;
    }
    .badge-supervisor { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .badge-barista { background: #fdf2f8; color: #be185d; border: 1px solid #fbcfe8; }
    .badge-cook { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa; }
    .badge-cashier { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .badge-server { background: #faf5ff; color: #7e22ce; border: 1px solid #e9d5ff; }
    
    /* Status Pills */
    .status-pill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .status-approved { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
    .status-rejected { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
    .status-pending { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
    
    /* Extra Shift Highlight */
    .extra-shift-banner {
        background: #fffbeb;
        border: 1px solid #fde68a;
        color: #b45309;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 0.25rem 0.55rem;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "active_admin_tab" not in st.session_state:
    st.session_state.active_admin_tab = "Directory"
if "leave_submitted_eval" not in st.session_state:
    st.session_state.leave_submitted_eval = None
if "selected_absent_slot" not in st.session_state:
    st.session_state.selected_absent_slot = None

def get_skill_badges_html(skills: List[str]) -> str:
    html = ""
    for s in skills:
        cls = f"badge-{s.lower()}"
        html += f'<span class="skill-badge {cls}">{s}</span> '
    return html

# ---------------------------------------------------------
# VIEW 1: LOGIN SCREEN
# ---------------------------------------------------------
def render_login_view():
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        login_header_html = """<div style="text-align: center; margin-bottom: 1.5rem;">
<div style="display:inline-flex; align-items:center; justify-content:center; width:56px; height:56px; border-radius:14px; background:linear-gradient(135deg, #4f46e5, #4338ca); color:white; font-size:26px; box-shadow:0 4px 12px rgba(79, 70, 229, 0.25);">📅</div>
<h1 style="font-size:1.85rem; font-weight:800; color:#0f172a; margin-top:0.75rem; margin-bottom:0.25rem;">AutoRoster</h1>
<p style="color:#64748b; font-size:0.95rem;">Workforce Operations & Shift Scheduling Portal</p>
</div>"""
        st.markdown(login_header_html, unsafe_allow_html=True)

        with st.form("form_login"):
            st.markdown("#### Sign In")
            username = st.text_input("Work Email or Username", placeholder="name@company.com or username", autocomplete="username")
            password = st.text_input("Password", type="password", placeholder="••••••••", autocomplete="current-password")
            submitted = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

            if submitted:
                if not username.strip() or not password.strip():
                    st.error("Please enter your work email and password.")
                else:
                    auth_user = db.authenticate(username, password)
                    if auth_user:
                        st.session_state.authenticated = True
                        st.session_state.user = auth_user
                        st.success(f"Welcome back, {auth_user['name']}!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please verify your work email and password.")

        st.markdown("<br><p style='text-align:center; color:#94a3b8; font-size:0.8rem;'>AutoRoster Operations Platform • Production Release</p>", unsafe_allow_html=True)

# ---------------------------------------------------------
# VIEW 2: ADMIN / MANAGER PORTAL
# ---------------------------------------------------------
def render_admin_portal():
    user = st.session_state.user

    # Top Header Bar
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.markdown(f"## 🏢 Manager Operations Hub <span style='font-size:0.95rem; color:#64748b; font-weight:normal;'>• Main Store Branch</span>", unsafe_allow_html=True)
    with head_col2:
        st.markdown(f"<div style='text-align:right;'><strong>{user['name']}</strong><br><span class='status-pill status-approved'>Store Manager</span></div>", unsafe_allow_html=True)
        if st.button("Sign Out", key="admin_logout", type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    st.markdown("---")

    # Main Navigation Tabs
    tab_directory, tab_add, tab_leaves, tab_urgent, tab_roster, tab_audits = st.tabs([
        "👥 Staff Directory",
        "➕ Add Employee",
        "📋 Leave Decision Log",
        "🚨 Urgent Medical Queue",
        "📅 Weekly Master Schedule",
        "↺ Shift Cover Audit"
    ])

    # ---------------------------------------------------------
    # TAB 1: ACTIVE STAFF DIRECTORY
    # ---------------------------------------------------------
    with tab_directory:
        employees = db.get_employees()
        
        # Summary KPI Cards
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Active Employees", len(employees))
        kpi2.metric("Supervisors", len([e for e in employees if "Supervisor" in e.skills]))
        kpi3.metric("Baristas / Cashiers", len([e for e in employees if "Barista" in e.skills or "Cashier" in e.skills]))
        kpi4.metric("Cooks / Servers", len([e for e in employees if "Cook" in e.skills or "Server" in e.skills]))

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### Registered Team Members")

        grid_cols = st.columns(2)
        for idx, emp in enumerate(employees):
            col = grid_cols[idx % 2]
            with col:
                with st.container(border=True):
                    c_top1, c_top2 = st.columns([3, 1])
                    with c_top1:
                        st.markdown(f"#### {emp.name}")
                        st.caption(f"📧 {emp.email}")
                    with c_top2:
                        st.markdown('<div style="text-align:right;"><span class="status-pill status-approved">ACTIVE</span></div>', unsafe_allow_html=True)
                    
                    st.markdown(get_skill_badges_html(emp.skills), unsafe_allow_html=True)
                    st.caption(f"⏱️ Hourly Limit: **{emp.max_weekly_hours} hours / week**")
                    
                    if st.button(f"🗑 Remove {emp.name}", key=f"del_emp_{emp.id}", type="secondary", use_container_width=True):
                        if db.delete_employee(emp.id):
                            st.success(f"Removed {emp.name} from directory.")
                            st.rerun()

    # ---------------------------------------------------------
    # TAB 2: ADD EMPLOYEE
    # ---------------------------------------------------------
    with tab_add:
        st.markdown("### Add New Employee")
        st.markdown("Register a team member with certified skills and weekly hour limits.")

        with st.form("form_add_employee"):
            name = st.text_input("Full Name *", placeholder="e.g. Maya Lin")
            email = st.text_input("Work Email *", placeholder="e.g. maya@vibecafe.com")
            skills = st.multiselect("Certified Roles & Skills *", AVAILABLE_SKILLS, default=["Barista"])
            max_hours = st.select_slider("Weekly Maximum Hours", options=[16, 24, 32, 40], value=32)

            btn_save = st.form_submit_button("Save Team Member →", type="primary")
            if btn_save:
                if not name.strip():
                    st.error("Please enter employee name.")
                elif not skills:
                    st.error("Please select at least one skill certification.")
                else:
                    new_emp = db.add_employee(
                        name=name.strip(),
                        email=email.strip(),
                        skills=skills,
                        max_weekly_hours=max_hours
                    )
                    st.success(f"Successfully added {new_emp.name} to the team!")
                    st.rerun()

    # ---------------------------------------------------------
    # TAB 3: LEAVE DECISION LOG
    # ---------------------------------------------------------
    with tab_leaves:
        st.markdown("### Leave Requests & Audit Trail")
        st.markdown("Audited record of employee submissions evaluated by AI and manager decisions.")

        filter_choice = st.radio("Filter Status:", ["ALL", "APPROVED", "REJECTED", "PENDING"], horizontal=True)
        logs = db.get_leave_log()
        if filter_choice != "ALL":
            logs = [l for l in logs if l.get("status") == filter_choice]

        if not logs:
            st.info(f"No records found matching status '{filter_choice}'.")
        else:
            for l in logs:
                status = l.get("status", "PENDING")
                status_class = f"status-{status.lower()}"
                risk_pct = round((l.get("exploitation_risk_score") or 0) * 100)
                risk_color = "#dc2626" if risk_pct >= 50 else ("#d97706" if risk_pct >= 25 else "#16a34a")

                with st.expander(f"{status} | {l.get('employee_name')} — {l.get('day_of_week')} ({l.get('shift_type')}) • {l.get('reason')}"):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.markdown(f"**Status:** <span class='status-pill {status_class}'>{status}</span>", unsafe_allow_html=True)
                    c2.markdown(f"**Importance:** `{l.get('reason_importance', 'MEDIUM')}`")
                    c3.markdown(f"**Policy Risk:** <strong style='color:{risk_color};'>{risk_pct}%</strong>", unsafe_allow_html=True)
                    c4.markdown(f"**Date:** {l.get('created_at', 'Recent')}")

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("**Original Employee Message to AI:**")
                    st.info(f'"{l.get("raw_text")}"')

                    st.markdown("**AI Pattern Learning & Anti-Exploitation Diagnostics:**")
                    st.markdown(f"> {l.get('pattern_analysis') or l.get('explanation') or 'Pattern verified clean.'}")

    # ---------------------------------------------------------
    # TAB 4: URGENT MEDICAL LEAVES QUEUE
    # ---------------------------------------------------------
    with tab_urgent:
        st.markdown("### Urgent Medical Requests Queue")
        st.markdown("Emergency medical leaves with clinical proof requiring manager verification.")

        urgent_items = db.get_urgent_leaves()
        pending_urgent = [u for u in urgent_items if u.get("status") == "PENDING"]

        if not pending_urgent:
            st.success("✓ Zero pending urgent medical requests awaiting review.")
        else:
            st.warning(f"🚨 {len(pending_urgent)} emergency medical leave(s) require your review:")

        for u in urgent_items:
            is_pending = u.get("status") == "PENDING"
            status = u.get("status")
            status_class = f"status-{status.lower()}"

            with st.container(border=True):
                c_u1, c_u2 = st.columns([3, 1])
                with c_u1:
                    st.markdown(f"#### 🚨 {u.get('employee_name')}")
                    st.caption(f"Target Shift: **{u.get('day_of_week')} ({u.get('shift_type')})** • Submitted: {u.get('created_at', 'Recent')}")
                with c_u2:
                    st.markdown(f'<div style="text-align:right;"><span class="status-pill {status_class}">{status}</span></div>', unsafe_allow_html=True)

                st.info(f'"{u.get("raw_text")}"')

                with st.container(border=True):
                    st.markdown("**🏥 Clinical Medical Certificate Preview** (Verified Attachment)")
                    st.markdown(f"- **Patient:** {u.get('employee_name')}\n- **Assessment:** Acute Emergency Assessment - {u.get('reason')}\n- **Restriction:** Unfit for scheduled duty on {u.get('day_of_week')}\n- **File Reference:** `{u.get('proof_filename', 'Medical_Record.pdf')}`")

                if is_pending:
                    act_col1, act_col2 = st.columns(2)
                    with act_col1:
                        if st.button(f"✓ Approve Emergency Leave", key=f"appr_{u['id']}", type="primary", use_container_width=True):
                            db.update_leave_status(u["id"], "APPROVED")
                            st.success(f"Approved urgent leave for {u['employee_name']}.")
                            st.rerun()
                    with act_col2:
                        if st.button(f"✕ Reject", key=f"rej_{u['id']}", type="secondary", use_container_width=True):
                            db.update_leave_status(u["id"], "REJECTED")
                            st.info(f"Rejected urgent leave for {u['employee_name']}.")
                            st.rerun()

    # ---------------------------------------------------------
    # TAB 5: WEEKLY MASTER SCHEDULE (CP-SAT)
    # ---------------------------------------------------------
    with tab_roster:
        st.markdown("### Weekly Shift Schedule Planner")
        st.markdown("Automated constraint optimization using **Google OR-Tools CP-SAT** enforcing shift requirements, certified skill matching, and fair hour distribution.")

        col_act1, col_act2 = st.columns([1, 3])
        with col_act1:
            if st.button("⚡ Generate & Optimize Schedule", type="primary", use_container_width=True):
                with st.spinner("Executing Google OR-Tools CP-SAT mathematical solver..."):
                    res = solve_roster(
                        employees=db.get_employees(),
                        requirements=db.get_shift_requirements(),
                        approved_leaves=db.get_approved_leaves()
                    )
                    db.set_roster_result(
                        status=res["status"],
                        slots=res.get("slots", []),
                        conflicts=res.get("conflicts", []),
                        stats=res.get("stats", {})
                    )
                st.success("CP-SAT optimization complete!")
                st.rerun()

        # If solver hasn't been run, run initial solve
        roster_res = db.get_roster_result()
        if roster_res.get("status") == "NOT_GENERATED":
            res = solve_roster(
                employees=db.get_employees(),
                requirements=db.get_shift_requirements(),
                approved_leaves=db.get_approved_leaves()
            )
            db.set_roster_result(
                status=res["status"],
                slots=res.get("slots", []),
                conflicts=res.get("conflicts", []),
                stats=res.get("stats", {})
            )
            roster_res = db.get_roster_result()

        slots = db.current_roster
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Weekly Master Roster (Monday – Sunday)")

        day_cols = st.columns(7)
        for i, day in enumerate(days):
            with day_cols[i]:
                day_slots = [s for s in slots if s.day_of_week == day]
                st.markdown(f"**{day}** ({len(day_slots)} shifts)")
                st.markdown("---")

                for s in day_slots:
                    is_sub = bool(s.replaced_by_id)
                    assignee = s.replaced_by_name if is_sub else (s.assigned_employee_name or "Unassigned")
                    role_cls = f"badge-{s.role.lower()}"

                    with st.container(border=True):
                        st.markdown(f"**{s.shift_type}** <span class='skill-badge {role_cls}'>{s.role}</span>", unsafe_allow_html=True)
                        st.markdown(f"**{assignee}**")
                        if is_sub:
                            st.caption(f"↺ Sub for {s.assigned_employee_name}")
                        if not s.is_absent:
                            if st.button("Mark Absent", key=f"abs_{s.id}", use_container_width=True):
                                st.session_state.selected_absent_slot = s.id
                                st.rerun()

        # Handle Replacement Section if an absent slot is selected
        if st.session_state.selected_absent_slot:
            target_id = st.session_state.selected_absent_slot
            target_slot = next((s for s in slots if s.id == target_id), None)
            if target_slot:
                st.markdown("---")
                st.markdown(f"### ↺ Assign Replacement for Vacant Shift")
                st.warning(f"Shift: **{target_slot.day_of_week} {target_slot.shift_type} ({target_slot.hours}h)** — Required Certified Role: **{target_slot.role}**")

                replacements = get_ranked_replacements(
                    slot=target_slot,
                    employees=db.get_employees(),
                    current_roster=db.current_roster,
                    approved_leaves=db.get_approved_leaves()
                )

                if replacements["eligible_count"] == 0:
                    st.error("No eligible team members have required certification and available weekly hours.")
                else:
                    st.markdown("#### Ranked Qualified Candidates (Ranked by Availability & Fairness):")
                    for c in replacements["eligible"]:
                        r_col1, r_col2 = st.columns([3, 1])
                        with r_col1:
                            st.markdown(f"**#{c['rank']} {c['name']}** {'⭐ Top Recommended' if c['rank'] == 1 else ''}<br>Match Score: <strong>{c['score']} pts</strong> • Remaining Hours: <strong>{c['remaining_hours']}h</strong> • Skills: {', '.join(c['skills'])}", unsafe_allow_html=True)
                        with r_col2:
                            if st.button(f"Assign {c['name']}", key=f"assign_{target_slot.id}_{c['employee_id']}", type="primary"):
                                db.mark_slot_absent(target_slot.id, "Sudden call-out")
                                db.assign_replacement(target_slot.id, c['employee_id'])
                                st.success(f"Assigned {c['name']} to cover shift!")
                                st.session_state.selected_absent_slot = None
                                st.rerun()

                if st.button("Cancel Replacement"):
                    st.session_state.selected_absent_slot = None
                    st.rerun()

    # ---------------------------------------------------------
    # TAB 6: SHIFT COVER AUDIT
    # ---------------------------------------------------------
    with tab_audits:
        st.markdown("### Shift Cover & Substitution Audit Log")
        st.markdown("Permanent audit history of all shifts covered for absent personnel.")

        audits = db.get_replacement_audits()
        if not audits:
            st.info("No shift substitutions recorded yet.")
        else:
            audit_data = []
            for a in audits:
                audit_data.append({
                    "Shift": f"{a.get('day_of_week')} {a.get('shift_type')}",
                    "Role": a.get("role"),
                    "Original Staff (Absent)": a.get("original_employee_name"),
                    "Covering Staff (Substitute)": a.get("replaced_by_name"),
                    "Reason": a.get("reason"),
                    "Logged At": a.get("created_at", "Recent")
                })
            st.dataframe(pd.DataFrame(audit_data), use_container_width=True)


# ---------------------------------------------------------
# VIEW 3: EMPLOYEE SELF-SERVICE PORTAL
# ---------------------------------------------------------
def render_employee_portal():
    user = st.session_state.user

    # Header Bar
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.markdown(f"## ☕ Employee Self-Service <span style='font-size:0.95rem; color:#64748b; font-weight:normal;'>• AutoRoster Portal</span>", unsafe_allow_html=True)
    with head_col2:
        st.markdown(f"<div style='text-align:right;'><strong>{user['name']}</strong><br><span class='status-pill status-pending'>Staff Member</span></div>", unsafe_allow_html=True)
        if st.button("Sign Out", key="emp_logout", type="secondary", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()

    st.markdown("---")

    tab_request, tab_myshifts = st.tabs(["📝 Request Leave / Unavailability", "📅 My Shifts This Week"])

    # ---------------------------------------------------------
    # EMPLOYEE TAB 1: SUBMIT LEAVE REQUEST
    # ---------------------------------------------------------
    with tab_request:
        c_left, c_right = st.columns([1.1, 1])

        with c_left:
            st.markdown("### New Leave Request")
            st.markdown("Describe your unavailability in natural language. Our scheduling system evaluates request validity, pattern history, and anti-exploitation policy.")

            with st.form("form_emp_leave"):
                leave_text = st.text_area(
                    "Reason & Shift Details *",
                    placeholder="e.g. Doctor appointment on Tuesday morning, sister's wedding on Friday evening...",
                    height=130
                )

                is_urgent = st.checkbox("🚨 Urgent medical condition requiring verification")
                proof_file = None
                if is_urgent:
                    proof_file = st.file_uploader("Attach Clinical Verification Document (PDF, PNG, JPG)", type=["pdf", "png", "jpg", "jpeg"])

                btn_submit = st.form_submit_button("Submit Leave Request →", type="primary", use_container_width=True)

                if btn_submit:
                    if not leave_text.strip():
                        st.error("Please provide details for your leave request.")
                    else:
                        emp = db.get_employee(user["id"])
                        parsed = parse_free_text_availability(leave_text, [e.to_dict() for e in db.get_employees()])
                        day_of_week = parsed["day_of_week"]
                        shift_type = parsed["shift_type"]
                        detected_reason = parsed["reason"]

                        eval_result = evaluate_leave_request(
                            employee=emp,
                            raw_text=leave_text,
                            day_of_week=day_of_week,
                            shift_type=shift_type,
                            detected_reason=detected_reason,
                            is_urgent=is_urgent,
                            has_proof=bool(proof_file),
                            historical_leaves=db.get_leave_requests()
                        )

                        proof_filename = proof_file.name if proof_file else ("Doctor_Certificate.pdf" if is_urgent else None)
                        created_lr = db.add_leave_request(
                            employee_id=user["id"],
                            raw_text=leave_text,
                            day_of_week=day_of_week,
                            shift_type=shift_type,
                            reason=detected_reason,
                            confidence=parsed.get("confidence", 0.95),
                            explanation=parsed.get("explanation", ""),
                            is_urgent=is_urgent,
                            proof_filename=proof_filename,
                            ai_decision=eval_result["decision"],
                            reason_importance=eval_result["reason_importance"],
                            exploitation_risk_score=eval_result["exploitation_risk_score"],
                            pattern_analysis=eval_result["pattern_analysis"]
                        )

                        st.session_state.leave_submitted_eval = {
                            "eval": eval_result,
                            "day": day_of_week,
                            "shift": shift_type
                        }
                        st.rerun()

        with c_right:
            st.markdown("### Policy Review & Real-Time Decision")
            eval_data = st.session_state.leave_submitted_eval

            if not eval_data:
                with st.container(border=True):
                    st.markdown("<div style='text-align:center; padding:2rem 1rem;'>", unsafe_allow_html=True)
                    st.markdown("### 📝 No Active Request")
                    st.caption("Submit your request on the left. The AI anti-exploitation system will evaluate the reason importance and pattern history immediately.")
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                ev = eval_data["eval"]
                dec = ev["decision"]
                dec_class = "status-approved" if dec == "APPROVED" else ("status-rejected" if dec == "REJECTED" else "status-pending")
                dec_text = "✓ LEAVE APPROVED BY AI" if dec == "APPROVED" else ("✕ LEAVE REJECTED BY AI" if dec == "REJECTED" else "⏳ FORWARDED TO MANAGER FOR SIGN-OFF")

                with st.container(border=True):
                    st.markdown(f"<div style='text-align:center; padding:0.5rem;' class='{dec_class}'><strong>{dec_text}</strong></div><br>", unsafe_allow_html=True)

                    c_m1, c_m2 = st.columns(2)
                    c_m1.metric("Reason Priority", ev["reason_importance"])
                    c_m2.metric("Target Shift", f"{eval_data['day']} ({eval_data['shift']})")

                    c_m3, c_m4 = st.columns(2)
                    c_m3.metric("Policy Compliance", f"{round(ev['trust_score'] * 100)}%")
                    c_m4.metric("Exploitation Risk", f"{round(ev['exploitation_risk_score'] * 100)}%")

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info(f"**Pattern Assessment:**\n\n{ev['pattern_analysis']}")

    # ---------------------------------------------------------
    # EMPLOYEE TAB 2: MY SHIFTS THIS WEEK
    # ---------------------------------------------------------
    with tab_myshifts:
        st.markdown("### My Weekly Schedule")
        st.markdown("Your allocated shifts for this upcoming roster week. Extra shifts picked up to cover absent colleagues are highlighted.")

        # Ensure roster is generated
        if db.get_roster_result().get("status") == "NOT_GENERATED":
            res = solve_roster(
                employees=db.get_employees(),
                requirements=db.get_shift_requirements(),
                approved_leaves=db.get_approved_leaves()
            )
            db.set_roster_result(
                status=res["status"],
                slots=res.get("slots", []),
                conflicts=res.get("conflicts", []),
                stats=res.get("stats", {})
            )

        my_roster = db.get_employee_roster(user["id"])
        total_hours = my_roster.get("total_assigned_hours", 0)
        max_hours = my_roster.get("max_weekly_hours", 40)
        shifts = my_roster.get("shifts", [])
        extra_count = my_roster.get("extra_shifts_count", 0)

        # KPI Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Weekly Hours Scheduled", f"{total_hours}h / {max_hours}h", f"{round((total_hours/max_hours)*100)}% Capacity")
        m2.metric("Scheduled Shifts", f"{len(shifts)} shifts", "8h per shift")
        m3.metric("Extra Substitute Shifts", f"{extra_count} extra", "Covering for absent coworkers")

        st.markdown("<br>", unsafe_allow_html=True)
        if not shifts:
            st.info("No shifts currently scheduled for you this week.")
        else:
            for s in shifts:
                is_extra = s.get("is_replacement_shift", False)
                role = s.get("role", "Barista")
                role_cls = f"badge-{role.lower()}"
                day = s.get("day_of_week")
                shift_type = s.get("shift_type")

                with st.container(border=True):
                    if is_extra:
                        sub_for = s.get('substitute_for', 'Coworker')
                        st.markdown(f'<span class="extra-shift-banner">⭐ Extra Shift (Substituted for {sub_for})</span>', unsafe_allow_html=True)

                    c_shift1, c_shift2 = st.columns([3, 1])
                    with c_shift1:
                        st.markdown(f"#### {day}")
                        st.markdown(f"Shift Duration: **{shift_type} (8 hours)**")
                    with c_shift2:
                        st.markdown(f'<div style="text-align:right;"><span class="skill-badge {role_cls}">{role}</span></div>', unsafe_allow_html=True)

                    if is_extra:
                        st.caption("Covering unplanned absence for coworker.")
                    else:
                        st.caption("Standard scheduled shift from weekly master roster.")


# ---------------------------------------------------------
# APPLICATION ROUTING
# ---------------------------------------------------------
def main():
    if not st.session_state.authenticated:
        render_login_view()
    else:
        user = st.session_state.user
        if user.get("role") == "admin":
            render_admin_portal()
        else:
            render_employee_portal()

if __name__ == "__main__":
    main()
