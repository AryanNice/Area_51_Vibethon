/**
 * AutoRoster Frontend Application Logic.
 * Supports:
 * 1. Role-based Authentication (Admin vs Employee).
 * 2. Dedicated Admin Portal (Staff Directory, Add Staff, Leave Log with Raw Inspection, Urgent Proofs, CP-SAT Roster, Replacement Audit).
 * 3. Dedicated Employee Portal (AI Leave Intake, Anti-Exploitation Pattern Learning, Personal Schedule with Substitute Highlights).
 * 4. Transparent Anti-Exploitation & Mathematical Constraint Verification.
 */

// Application Global State
const state = {
  currentUser: null, // { id, name, email, role, skills, max_weekly_hours }
  activeAdminTab: "tab-staff-directory",
  activeEmpTab: "tab-emp-leave",
  staff: [],
  availableSkills: ["Supervisor", "Barista", "Cook", "Cashier", "Server"],
  leavesLog: [],
  urgentLeaves: [],
  replacementAudits: [],
  roster: [],
  rosterStatus: "NOT_GENERATED",
  activeProofFile: null,
  activeProofDataUrl: null,
  activeLogFilter: "ALL"
};

// Document Ready
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  checkPersistedSession();
});

/**
 * Initialize all DOM event listeners
 */
function initEventListeners() {
  // Login Form Submission
  document.getElementById("form-login")?.addEventListener("submit", handleLogin);

  // Logout Button
  document.getElementById("btn-logout")?.addEventListener("click", handleLogout);

  // Admin Sub Navigation Tabs
  document.querySelectorAll(".tab-btn[data-admin-tab]").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-admin-tab");
      switchAdminTab(targetId);
    });
  });

  // Employee Sub Navigation Tabs
  document.querySelectorAll(".tab-btn[data-emp-tab]").forEach(btn => {
    btn.addEventListener("click", () => {
      const targetId = btn.getAttribute("data-emp-tab");
      switchEmployeeTab(targetId);
    });
  });

  // Log Filter Pills
  document.querySelectorAll("#log-filter-pills .btn-chip").forEach(pill => {
    pill.addEventListener("click", () => {
      document.querySelectorAll("#log-filter-pills .btn-chip").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      state.activeLogFilter = pill.getAttribute("data-log-filter");
      renderLeaveLog();
    });
  });

  // Admin Add Employee Form
  document.getElementById("form-admin-add-employee")?.addEventListener("submit", handleAdminAddEmployee);

  // Max Hours Display updates
  const addHoursInput = document.getElementById("add-emp-hours");
  if (addHoursInput) {
    addHoursInput.addEventListener("input", (e) => {
      const disp = document.getElementById("add-hours-display");
      if (disp) disp.textContent = `${e.target.value}h`;
    });
  }

  // Solver Button
  document.getElementById("btn-generate-roster")?.addEventListener("click", handleGenerateRoster);

  // Urgent Toggle Checkbox
  const urgentCheck = document.getElementById("emp-is-urgent-checkbox");
  if (urgentCheck) {
    urgentCheck.addEventListener("change", (e) => {
      toggleUrgentProofUpload(e.target.checked);
    });
  }

  // Proof File Upload Input
  const fileInput = document.getElementById("proof-file-input");
  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        state.activeProofFile = file.name;
        const reader = new FileReader();
        reader.onload = (loadEvent) => {
          state.activeProofDataUrl = loadEvent.target.result;
          const filenameDisp = document.getElementById("proof-filename-display");
          if (filenameDisp) filenameDisp.textContent = `Attached: ${file.name} (${Math.round(file.size / 1024)} KB)`;
        };
        reader.readAsDataURL(file);
      }
    });
  }

  // Employee Leave Form Submit
  document.getElementById("form-employee-leave")?.addEventListener("submit", handleEmployeeLeaveSubmit);
}

/**
 * Check if a session was persisted in localStorage
 */
function checkPersistedSession() {
  const savedUser = localStorage.getItem("autoroster_user");
  if (savedUser) {
    try {
      state.currentUser = JSON.parse(savedUser);
      showAppView();
      return;
    } catch (e) {
      localStorage.removeItem("autoroster_user");
    }
  }
  showLoginView();
}

/**
 * Handle Login Request
 */
async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const errorAlert = document.getElementById("login-error-alert");

  if (errorAlert) errorAlert.style.display = "none";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      if (errorAlert) {
        errorAlert.textContent = data.error || "Invalid email or password.";
        errorAlert.style.display = "block";
      }
      return;
    }

    state.currentUser = data.data;
    localStorage.setItem("autoroster_user", JSON.stringify(data.data));
    showToast(`Signed in successfully as ${state.currentUser.name}`, "success");
    showAppView();
  } catch (err) {
    showToast("Unable to connect to authentication server.", "error");
    console.error(err);
  }
}

/**
 * Handle Logout
 */
function handleLogout() {
  state.currentUser = null;
  localStorage.removeItem("autoroster_user");
  showLoginView();
  showToast("You have been signed out.", "info");
}

/**
 * View Switches
 */
function showLoginView() {
  document.getElementById("view-login").style.display = "flex";
  document.getElementById("view-app").style.display = "none";
}

function showAppView() {
  document.getElementById("view-login").style.display = "none";
  document.getElementById("view-app").style.display = "block";

  // Update header profile badge
  const avatar = document.getElementById("header-user-avatar");
  const name = document.getElementById("header-user-name");
  const role = document.getElementById("header-user-role");

  if (name) name.textContent = state.currentUser.name;
  if (role) {
    role.textContent = state.currentUser.role.toUpperCase();
    role.className = `user-role-badge ${state.currentUser.role === "admin" ? "badge-admin" : "badge-emp"}`;
  }
  if (avatar) {
    const initials = state.currentUser.name.split(" ").map(p => p[0]).join("").slice(0, 2);
    avatar.textContent = initials || "U";
  }

  // Switch to appropriate portal view
  if (state.currentUser.role === "admin") {
    document.getElementById("portal-admin").style.display = "block";
    document.getElementById("portal-employee").style.display = "none";
    initAdminPortal();
  } else {
    document.getElementById("portal-admin").style.display = "none";
    document.getElementById("portal-employee").style.display = "block";
    initEmployeePortal();
  }
}

function switchAdminTab(targetId) {
  document.querySelectorAll("#portal-admin .tab-btn").forEach(b => {
    b.classList.toggle("active", b.getAttribute("data-admin-tab") === targetId);
  });
  document.querySelectorAll("#portal-admin .tab-panel").forEach(p => {
    p.classList.toggle("active", p.id === targetId);
  });
  state.activeAdminTab = targetId;

  // Refresh tab data
  if (targetId === "tab-staff-directory") fetchStaff();
  else if (targetId === "tab-leave-log") fetchLeaveLog();
  else if (targetId === "tab-urgent-leaves") fetchUrgentLeaves();
  else if (targetId === "tab-roster") fetchRoster();
  else if (targetId === "tab-replacement-audit") fetchReplacementAudits();
}

function switchEmployeeTab(targetId) {
  document.querySelectorAll("#portal-employee .tab-btn").forEach(b => {
    b.classList.toggle("active", b.getAttribute("data-emp-tab") === targetId);
  });
  document.querySelectorAll("#portal-employee .tab-panel").forEach(p => {
    p.classList.toggle("active", p.id === targetId);
  });
  state.activeEmpTab = targetId;

  if (targetId === "tab-emp-roster") fetchEmployeePersonalRoster();
}

function toggleUrgentProofUpload(show) {
  const uploadSec = document.getElementById("urgent-proof-upload-section");
  if (uploadSec) uploadSec.style.display = show ? "block" : "none";
}

/**
 * ========================================================
 * ADMIN PORTAL LOGIC
 * ========================================================
 */
async function initAdminPortal() {
  await fetchStaff();
  renderSkillChips();
  fetchLeaveLog();
  fetchUrgentLeaves();
  fetchRoster();
  fetchReplacementAudits();
}

/**
 * Fetch and Render Staff Directory
 */
async function fetchStaff() {
  try {
    const res = await fetch("/api/employees");
    const data = await res.json();
    if (data.success) {
      state.staff = data.data || [];
      const badge = document.getElementById("badge-admin-staff-count");
      if (badge) badge.textContent = state.staff.length;
      renderStaffDirectory();
    }
  } catch (err) {
    console.error("Error fetching staff:", err);
  }
}

function renderStaffDirectory() {
  const container = document.getElementById("staff-directory-grid");
  if (!container) return;

  if (state.staff.length === 0) {
    container.innerHTML = `<p class="text-muted">No staff currently registered.</p>`;
    return;
  }

  container.innerHTML = state.staff.map(emp => {
    const skillBadges = (emp.skills || []).map(s => {
      const cls = `badge-${s.toLowerCase()}`;
      return `<span class="skill-badge ${cls}">${s}</span>`;
    }).join(" ");

    return `
      <div class="staff-card">
        <div>
          <div class="staff-top">
            <span class="staff-name">${escapeHtml(emp.name)}</span>
            <span class="skill-badge badge-supervisor">Active</span>
          </div>
          <div class="staff-email">${escapeHtml(emp.email || "No email registered")}</div>
          <div class="staff-skills-wrap">
            ${skillBadges}
          </div>
        </div>
        <div class="staff-footer">
          <span class="staff-hours">⏱️ Max ${emp.max_weekly_hours}h / wk</span>
          <button class="btn btn-outline-danger btn-sm" onclick="handleDeleteEmployee('${emp.id}')">
            🗑 Delete
          </button>
        </div>
      </div>
    `;
  }).join("");
}

function renderSkillChips() {
  const container = document.getElementById("admin-skill-chips-container");
  if (!container) return;
  container.innerHTML = state.availableSkills.map(skill => `
    <span class="skill-chip" data-skill="${skill}" onclick="toggleSkillSelection(this)">
      ${skill}
    </span>
  `).join("");
}

function toggleSkillSelection(elem) {
  elem.classList.toggle("selected");
}

async function handleAdminAddEmployee(e) {
  e.preventDefault();
  const name = document.getElementById("add-emp-name").value.trim();
  const email = document.getElementById("add-emp-email").value.trim();
  const hours = parseInt(document.getElementById("add-emp-hours").value, 10);
  const selectedSkills = Array.from(document.querySelectorAll("#admin-skill-chips-container .skill-chip.selected"))
                              .map(c => c.getAttribute("data-skill"));

  const errorAlert = document.getElementById("add-emp-error");
  if (errorAlert) errorAlert.style.display = "none";

  if (!name) {
    showToast("Please enter employee name.", "error");
    return;
  }
  if (selectedSkills.length === 0) {
    showToast("Please select at least one skill.", "error");
    return;
  }

  try {
    const res = await fetch("/api/employees", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, max_weekly_hours: hours, skills: selectedSkills })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      if (errorAlert) {
        errorAlert.textContent = data.error || "Failed to register employee.";
        errorAlert.style.display = "block";
      }
      return;
    }

    showToast(`Employee ${name} registered successfully!`, "success");
    document.getElementById("form-admin-add-employee").reset();
    document.querySelectorAll("#admin-skill-chips-container .skill-chip").forEach(c => c.classList.remove("selected"));
    await fetchStaff();
    switchAdminTab("tab-staff-directory");
  } catch (err) {
    showToast("Error adding employee.", "error");
  }
}

async function handleDeleteEmployee(empId) {
  const emp = state.staff.find(e => e.id === empId);
  const empName = emp ? emp.name : "employee";
  if (!confirm(`Are you sure you want to remove ${empName} from the team?`)) return;

  try {
    const res = await fetch(`/api/employees/${empId}`, { method: "DELETE" });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Removed ${empName}.`, "info");
      await fetchStaff();
    } else {
      showToast(data.error || "Failed to delete employee", "error");
    }
  } catch (err) {
    showToast("Error deleting employee.", "error");
  }
}

/**
 * Fetch and Render Leave Decision Log
 */
async function fetchLeaveLog() {
  try {
    const res = await fetch("/api/admin/leave-log");
    const data = await res.json();
    if (data.success) {
      state.leavesLog = data.data || [];
      const badge = document.getElementById("badge-admin-log-count");
      if (badge) badge.textContent = state.leavesLog.length;
      renderLeaveLog();
    }
  } catch (err) {
    console.error("Error fetching leave log:", err);
  }
}

function renderLeaveLog() {
  const tbody = document.getElementById("leave-log-tbody");
  if (!tbody) return;

  let filtered = state.leavesLog;
  if (state.activeLogFilter !== "ALL") {
    filtered = filtered.filter(l => l.status === state.activeLogFilter);
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted py-4">No leave requests match filter "${state.activeLogFilter}".</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(l => {
    const statusCls = `status-${l.status.toLowerCase()}`;
    const riskPct = Math.round((l.exploitation_risk_score || 0) * 100);
    const riskBadgeCls = riskPct >= 50 ? "badge-cook" : (riskPct >= 25 ? "badge-barista" : "badge-cashier");

    return `
      <tr style="cursor: pointer;" onclick="openLeaveDetailModal('${l.id}')" title="Click to view full message and AI pattern breakdown">
        <td><span class="status-pill ${statusCls}">${l.status}</span></td>
        <td><strong>${escapeHtml(l.created_at || "Recent")}</strong></td>
        <td><strong>${escapeHtml(l.employee_name)}</strong></td>
        <td>${escapeHtml(l.day_of_week)} (${escapeHtml(l.shift_type)})</td>
        <td>${escapeHtml(l.reason || "-")}</td>
        <td><span class="skill-badge badge-server">${escapeHtml(l.reason_importance || "MEDIUM")}</span></td>
        <td><span class="skill-badge ${riskBadgeCls}">${riskPct}% Risk</span></td>
        <td>
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); openLeaveDetailModal('${l.id}')">
            🔍 Inspect Message
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function openLeaveDetailModal(leaveId) {
  const leave = state.leavesLog.find(l => l.id === leaveId);
  if (!leave) return;

  const modalBody = document.getElementById("modal-leave-detail-body");
  if (!modalBody) return;

  modalBody.innerHTML = `
    <div style="margin-bottom: 1.25rem;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
        <h4 style="font-size:1.1rem; font-weight:800; color:var(--slate-900);">${escapeHtml(leave.employee_name)}</h4>
        <span class="status-pill status-${leave.status.toLowerCase()}">${leave.status}</span>
      </div>
      <p style="font-size:0.8rem; color:var(--slate-500);">Submitted on: ${escapeHtml(leave.created_at || "Recent")} • Target: ${leave.day_of_week} ${leave.shift_type}</p>
    </div>

    <div style="background:var(--slate-50); border:1px solid var(--slate-200); border-radius:8px; padding:1rem; margin-bottom:1.25rem;">
      <h5 style="font-size:0.75rem; font-weight:700; text-transform:uppercase; color:var(--slate-500); margin-bottom:0.4rem;">Original Message Sent by Employee:</h5>
      <p style="font-size:0.92rem; font-style:italic; color:var(--slate-800); line-height:1.6;">"${escapeHtml(leave.raw_text)}"</p>
    </div>

    <div class="ai-metrics-grid" style="margin-bottom:1.25rem;">
      <div class="ai-metric-item">
        <span class="metric-label">Extracted Reason</span>
        <span class="metric-value" style="font-size:0.85rem;">${escapeHtml(leave.reason)}</span>
      </div>
      <div class="ai-metric-item">
        <span class="metric-label">Reason Importance</span>
        <span class="metric-value">${escapeHtml(leave.reason_importance || "MEDIUM")}</span>
      </div>
      <div class="ai-metric-item">
        <span class="metric-label">Exploitation Risk</span>
        <span class="metric-value">${Math.round((leave.exploitation_risk_score || 0) * 100)}%</span>
      </div>
      <div class="ai-metric-item">
        <span class="metric-label">AI Recommendation</span>
        <span class="metric-value">${escapeHtml(leave.ai_decision || leave.status)}</span>
      </div>
    </div>

    <div class="ai-analysis-box" style="margin-bottom:1.25rem;">
      <h4>Pattern Learning & Anti-Exploitation Diagnostics:</h4>
      <p>${escapeHtml(leave.pattern_analysis || leave.explanation || "Pattern verified clean.")}</p>
    </div>

    ${leave.is_urgent && leave.proof_filename ? `
      <div style="background:#fffbeb; border:1px solid #fed7aa; border-radius:8px; padding:0.85rem; display:flex; justify-content:space-between; align-items:center;">
        <div>
          <span style="font-size:0.75rem; font-weight:700; color:#c2410c; text-transform:uppercase;">Attached Medical Proof:</span>
          <div style="font-weight:700; color:#9a3412;">📄 ${escapeHtml(leave.proof_filename)}</div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="openProofModal('${leave.id}')">View Certificate</button>
      </div>
    ` : ""}
  `;

  openModal("modal-leave-detail");
}

/**
 * Fetch and Render Urgent Leaves
 */
async function fetchUrgentLeaves() {
  try {
    const res = await fetch("/api/admin/urgent-leaves");
    const data = await res.json();
    if (data.success) {
      state.urgentLeaves = data.data || [];
      const badge = document.getElementById("badge-admin-urgent-count");
      if (badge) {
        const pendingCount = state.urgentLeaves.filter(u => u.status === "PENDING").length;
        badge.textContent = `${pendingCount} Urgent`;
      }
      renderUrgentLeaves();
    }
  } catch (err) {
    console.error("Error fetching urgent leaves:", err);
  }
}

function renderUrgentLeaves() {
  const container = document.getElementById("urgent-leaves-container");
  if (!container) return;

  if (state.urgentLeaves.length === 0) {
    container.innerHTML = `<p class="text-muted">No urgent medical leaves submitted.</p>`;
    return;
  }

  container.innerHTML = state.urgentLeaves.map(u => {
    const isPending = u.status === "PENDING";
    return `
      <div class="urgent-card">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.5rem;">
          <div>
            <span class="urgent-badge">🚨 Urgent Medical</span>
            <h3 style="font-size:1.1rem; font-weight:800; margin-top:0.35rem;">${escapeHtml(u.employee_name)}</h3>
          </div>
          <span class="status-pill status-${u.status.toLowerCase()}">${u.status}</span>
        </div>

        <p style="font-size:0.8rem; color:var(--slate-500); margin-bottom:0.75rem;">
          📅 Requested: <strong>${escapeHtml(u.day_of_week)} (${escapeHtml(u.shift_type)})</strong>
        </p>

        <p style="font-size:0.85rem; color:var(--slate-800); margin-bottom:0.75rem; line-height:1.5;">
          💬 "${escapeHtml(u.raw_text)}"
        </p>

        <div class="urgent-proof-attachment">
          <div style="display:flex; align-items:center; gap:0.5rem;">
            <span style="font-size:1.4rem;">📄</span>
            <div>
              <div style="font-size:0.8rem; font-weight:700;">${escapeHtml(u.proof_filename || "Medical_Certificate.pdf")}</div>
              <div style="font-size:0.7rem; color:var(--slate-500);">Verified Document Attachment</div>
            </div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="openProofModal('${u.id}')">Inspect</button>
        </div>

        ${isPending ? `
          <div style="display:flex; gap:0.5rem; margin-top:1rem;">
            <button class="btn btn-success btn-sm btn-block" onclick="handleUrgentAction('${u.id}', 'APPROVE')">
              ✓ Approve Urgent Leave
            </button>
            <button class="btn btn-outline-danger btn-sm" onclick="handleUrgentAction('${u.id}', 'REJECT')">
              ✕ Reject
            </button>
          </div>
        ` : `
          <div style="font-size:0.75rem; color:var(--slate-500); text-align:center; padding-top:0.5rem;">
            Decision recorded as: <strong>${u.status}</strong>
          </div>
        `}
      </div>
    `;
  }).join("");
}

async function handleUrgentAction(leaveId, action) {
  try {
    const res = await fetch(`/api/admin/urgent-leaves/${leaveId}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message, action === "APPROVE" ? "success" : "info");
      await fetchUrgentLeaves();
      await fetchLeaveLog();
    } else {
      showToast(data.error || "Action failed", "error");
    }
  } catch (err) {
    showToast("Error processing urgent action.", "error");
  }
}

function openProofModal(leaveId) {
  const leave = state.urgentLeaves.find(u => u.id === leaveId) || state.leavesLog.find(l => l.id === leaveId);
  const modalBody = document.getElementById("modal-proof-body");
  if (!modalBody || !leave) return;

  modalBody.innerHTML = `
    <div style="border:2px solid #fed7aa; background:#fffbf5; border-radius:10px; padding:1.5rem; margin-bottom:1.25rem;">
      <div style="display:flex; justify-content:space-between; border-bottom:1px solid #fed7aa; padding-bottom:0.75rem; margin-bottom:1rem;">
        <div>
          <h4 style="font-weight:800; color:#9a3412; font-size:1.1rem;">Clinical Medical Certificate</h4>
          <span style="font-size:0.75rem; color:#b45309;">Verified Emergency Department Document</span>
        </div>
        <span style="font-size:1.5rem;">🏥</span>
      </div>

      <div style="font-size:0.85rem; line-height:1.6; color:#431407;">
        <p><strong>Patient Name:</strong> ${escapeHtml(leave.employee_name)}</p>
        <p><strong>Medical Diagnosis:</strong> Acute Emergency Assessment - ${escapeHtml(leave.reason)}</p>
        <p><strong>Work Restriction:</strong> Unfit for all physical duties on ${escapeHtml(leave.day_of_week)}</p>
        <p><strong>Document Reference:</strong> ${escapeHtml(leave.proof_filename || "Hospital_Clinical_Record.pdf")}</p>
      </div>

      <div style="margin-top:1.25rem; padding-top:0.75rem; border-top:1px dashed #fed7aa; display:flex; justify-content:space-between; font-size:0.72rem; color:#9a3412;">
        <span>Physician Signature: Dr. M. Vance, MD</span>
        <span>Stamp: St. Mary Medical Center</span>
      </div>
    </div>

    <div style="display:flex; justify-content:space-between; align-items:center;">
      ${leave.proof_data_url ? `
        <a href="${leave.proof_data_url}" download="${escapeHtml(leave.proof_filename || 'Medical_Certificate.pdf')}" class="btn btn-primary btn-sm">
          📥 Download Attached Document
        </a>
      ` : `<span></span>`}
      <button class="btn btn-secondary" onclick="closeModal('modal-proof-preview')">Close Preview</button>
    </div>
  `;

  openModal("modal-proof-preview");
}

/**
 * Fetch and Render Master Roster (CP-SAT)
 */
async function fetchRoster() {
  try {
    const res = await fetch("/api/roster");
    const data = await res.json();
    if (data.success) {
      state.roster = data.data.slots || [];
      state.rosterStatus = data.data.status;
      renderMasterRoster(data.data);
    }
  } catch (err) {
    console.error("Error fetching roster:", err);
  }
}

function renderMasterRoster(rosterData) {
  const container = document.getElementById("admin-roster-grid");
  const conflictBox = document.getElementById("conflict-panel");
  const statusBadge = document.getElementById("badge-roster-status");

  if (statusBadge) {
    statusBadge.textContent = rosterData.status === "SUCCESS" ? "CP-SAT Solved" : (rosterData.status === "INFEASIBLE" ? "Conflicts Detected" : "Ready");
    statusBadge.className = `tab-badge ${rosterData.status === "SUCCESS" ? "badge-supervisor" : (rosterData.status === "INFEASIBLE" ? "badge-warning" : "")}`;
  }

  // Conflict box
  if (rosterData.status === "INFEASIBLE" && rosterData.conflicts && rosterData.conflicts.length > 0) {
    conflictBox.style.display = "block";
    conflictBox.innerHTML = `
      <div style="background:#fef2f2; border:1px solid #fca5a5; border-radius:8px; padding:1rem; color:#991b1b;">
        <h4 style="font-weight:800; font-size:1rem; margin-bottom:0.4rem;">⚠️ No Feasible Schedule Found (Hard-Constraint Conflict)</h4>
        <p style="font-size:0.85rem; margin-bottom:0.75rem;">Google OR-Tools CP-SAT proved that all required shifts cannot be satisfied under existing rules:</p>
        ${rosterData.conflicts.map(c => `
          <div style="background:white; border-left:3px solid #ef4444; padding:0.6rem 0.85rem; margin-bottom:0.5rem; border-radius:0 6px 6px 0;">
            <strong>${escapeHtml(c.title)}:</strong> ${escapeHtml(c.description)}
            <div style="font-size:0.75rem; color:#b91c1c; margin-top:0.25rem;">Suggested Action: ${escapeHtml(c.action)}</div>
          </div>
        `).join("")}
      </div>
    `;
  } else {
    conflictBox.style.display = "none";
  }

  if (!container) return;

  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  container.innerHTML = days.map(day => {
    const daySlots = state.roster.filter(s => s.day_of_week === day);
    return `
      <div class="day-column">
        <div class="day-col-header">
          <div class="day-col-title">${day}</div>
          <div style="font-size:0.7rem; color:var(--slate-500);">${daySlots.length} shifts</div>
        </div>
        <div class="day-shifts-container">
          ${daySlots.map(slot => {
            const isReplaced = !!slot.replaced_by_id;
            const assigneeName = slot.replaced_by_name || slot.assigned_employee_name || "Unassigned";
            const roleClass = `badge-${slot.role.toLowerCase()}`;

            return `
              <div class="slot-card ${isReplaced ? "slot-replaced" : ""}">
                <div class="slot-top">
                  <span class="slot-shift-type">${slot.shift_type} (8h)</span>
                  <span class="skill-badge ${roleClass}">${slot.role}</span>
                </div>
                <div class="slot-assignee">
                  ${escapeHtml(assigneeName)}
                </div>
                ${isReplaced ? `
                  <span class="slot-replaced-badge">↺ Sub for ${escapeHtml(slot.assigned_employee_name)}</span>
                ` : ""}
                ${!slot.is_absent ? `
                  <button class="btn-absent-trigger" onclick="handleMarkAbsent('${slot.id}')">
                    Mark Absent
                  </button>
                ` : `
                  <span style="font-size:0.68rem; color:#b91c1c; font-weight:700;">Absent Reported</span>
                `}
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }).join("");
}

async function handleGenerateRoster() {
  try {
    showToast("Running Google OR-Tools CP-SAT solver...", "info");
    const res = await fetch("/api/roster/generate", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      state.roster = data.data.slots || [];
      state.rosterStatus = data.data.status;
      renderMasterRoster(data.data);
      if (data.data.status === "SUCCESS") {
        showToast("Weekly roster generated successfully!", "success");
      } else {
        showToast("Infeasible constraints detected.", "error");
      }
    }
  } catch (err) {
    showToast("Error generating roster.", "error");
  }
}

/**
 * Handle Marking Absent & Replacement Selection
 */
async function handleMarkAbsent(slotId) {
  try {
    const res = await fetch("/api/roster/mark-absent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slot_id: slotId, reason: "Sudden absence / call-out" })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast(data.error || "Failed to mark absent", "error");
      return;
    }

    // Open ranked replacements modal
    await openReplacementModal(slotId);
  } catch (err) {
    showToast("Error marking shift absent.", "error");
  }
}

async function openReplacementModal(slotId) {
  try {
    const res = await fetch(`/api/roster/replacements?slot_id=${slotId}`);
    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast(data.error || "Failed to fetch replacements", "error");
      return;
    }

    const replData = data.data;
    const targetSlot = replData.slot;
    const targetInfo = document.getElementById("replacement-target-info");
    const candidatesContainer = document.getElementById("replacement-candidates-container");

    if (targetInfo) {
      targetInfo.innerHTML = `
        <div style="background:var(--slate-50); border:1px solid var(--slate-200); border-radius:8px; padding:0.85rem; display:flex; justify-content:space-between; align-items:center;">
          <div>
            <span style="font-size:0.75rem; font-weight:700; color:var(--slate-500); text-transform:uppercase;">Vacant Shift</span>
            <div style="font-size:1.1rem; font-weight:800; color:var(--slate-900);">${targetSlot.day_of_week} ${targetSlot.shift_type} (${targetSlot.hours}h)</div>
          </div>
          <div>
            <span class="skill-badge badge-${targetSlot.role.toLowerCase()}">${targetSlot.role} Required</span>
          </div>
        </div>
      `;
    }

    if (candidatesContainer) {
      if (replData.eligible_count === 0) {
        candidatesContainer.innerHTML = `
          <div class="alert alert-danger">No eligible replacements have the required skill and available capacity.</div>
        `;
      } else {
        candidatesContainer.innerHTML = replData.eligible.map(c => `
          <div class="candidate-row ${c.rank === 1 ? "top-match" : ""}">
            <div>
              <div style="display:flex; align-items:center; gap:0.5rem;">
                <strong style="font-size:0.95rem;">#${c.rank} ${escapeHtml(c.name)}</strong>
                ${c.rank === 1 ? `<span class="badge badge-supervisor">★ Top Recommended</span>` : ""}
              </div>
              <div style="font-size:0.75rem; color:var(--slate-500); margin-top:0.2rem;">
                Match Score: <strong>${c.score} pts</strong> • Headroom: <strong>${c.remaining_hours}h left</strong> • Skills: ${c.skills.join(", ")}
              </div>
            </div>
            <button class="btn btn-primary btn-sm" onclick="handleAssignReplacement('${targetSlot.id}', '${c.employee_id}')">
              Assign Cover
            </button>
          </div>
        `).join("");
      }
    }

    openModal("modal-replacement");
  } catch (err) {
    showToast("Error opening replacement modal.", "error");
  }
}

async function handleAssignReplacement(slotId, replacementEmpId) {
  try {
    const res = await fetch("/api/roster/assign-replacement", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slot_id: slotId, replacement_emp_id: replacementEmpId })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message, "success");
      closeModal("modal-replacement");
      await fetchRoster();
      await fetchReplacementAudits();
    } else {
      showToast(data.error || "Failed to assign replacement", "error");
    }
  } catch (err) {
    showToast("Error assigning replacement.", "error");
  }
}

/**
 * Fetch and Render Replacement Audit Log
 */
async function fetchReplacementAudits() {
  try {
    const res = await fetch("/api/admin/replacements-audit");
    const data = await res.json();
    if (data.success) {
      state.replacementAudits = data.data || [];
      const badge = document.getElementById("badge-admin-audit-count");
      if (badge) badge.textContent = state.replacementAudits.length;
      renderReplacementAudit();
    }
  } catch (err) {
    console.error("Error fetching replacement audits:", err);
  }
}

function renderReplacementAudit() {
  const tbody = document.getElementById("replacement-audit-tbody");
  if (!tbody) return;

  if (state.replacementAudits.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No staff replacements recorded yet.</td></tr>`;
    return;
  }

  tbody.innerHTML = state.replacementAudits.map(a => `
    <tr>
      <td><strong>${escapeHtml(a.day_of_week)} ${escapeHtml(a.shift_type)}</strong></td>
      <td><span class="skill-badge badge-${a.role.toLowerCase()}">${escapeHtml(a.role)}</span></td>
      <td><span style="color:#b91c1c; font-weight:700;">${escapeHtml(a.original_employee_name)}</span> (Called Out)</td>
      <td><span style="color:#15803d; font-weight:700;">${escapeHtml(a.replaced_by_name)}</span> (Covering)</td>
      <td>${escapeHtml(a.reason)}</td>
      <td><span style="font-size:0.75rem; color:var(--slate-500);">${escapeHtml(a.created_at || "Recent")}</span></td>
    </tr>
  `).join("");
}

/**
 * ========================================================
 * EMPLOYEE PORTAL LOGIC
 * ========================================================
 */
function initEmployeePortal() {
  const shiftsBadge = document.getElementById("badge-emp-shifts-count");
  fetchEmployeePersonalRoster();
}

async function handleEmployeeLeaveSubmit(e) {
  e.preventDefault();
  const text = document.getElementById("emp-leave-text").value.trim();
  const isUrgent = document.getElementById("emp-is-urgent-checkbox").checked;
  const submitBtn = document.getElementById("btn-submit-emp-leave");

  if (!text) {
    showToast("Please describe your leave request reason.", "error");
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = "AI Evaluating Patterns...";
  }

  try {
    const payload = {
      employee_id: state.currentUser.id,
      text: text,
      is_urgent: isUrgent,
      proof_filename: state.activeProofFile,
      proof_data_url: state.activeProofDataUrl
    };

    const res = await fetch("/api/employee/leave-request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      showToast(data.error || "Failed to evaluate leave request.", "error");
      return;
    }

    const evalRes = data.evaluation;
    renderAiEvaluationResult(evalRes, data.data);
    showToast(data.message, evalRes.decision === "APPROVED" ? "success" : (evalRes.decision === "REJECTED" ? "error" : "info"));

    // Reset form
    document.getElementById("form-employee-leave").reset();
    toggleUrgentProofUpload(false);
    state.activeProofFile = null;
    state.activeProofDataUrl = null;
    const filenameDisp = document.getElementById("proof-filename-display");
    if (filenameDisp) filenameDisp.textContent = "Click or drag & drop proof document here (PDF, PNG, JPG)";
  } catch (err) {
    showToast("Error processing leave with AI assistant.", "error");
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = "<span>Submit Leave Request →</span>";
    }
  }
}

function renderAiEvaluationResult(evalRes, leaveData) {
  const placeholder = document.getElementById("ai-evaluation-placeholder");
  const resultCard = document.getElementById("ai-evaluation-result");
  const decisionBanner = document.getElementById("ai-decision-banner");
  const decisionText = document.getElementById("ai-decision-text");
  const importanceEl = document.getElementById("ai-metric-importance");
  const targetEl = document.getElementById("ai-metric-target");
  const riskEl = document.getElementById("ai-metric-risk");
  const trustEl = document.getElementById("ai-metric-trust");
  const explanationEl = document.getElementById("ai-analysis-explanation");

  if (placeholder) placeholder.style.display = "none";
  if (resultCard) resultCard.style.display = "block";

  if (decisionBanner && decisionText) {
    decisionBanner.className = `ai-decision-badge ${evalRes.decision.toLowerCase()}`;
    decisionText.textContent = evalRes.decision === "APPROVED" ? "✓ LEAVE APPROVED BY AI" : (evalRes.decision === "REJECTED" ? "✕ LEAVE REJECTED BY AI" : "⏳ FORWARDED TO MANAGER");
  }

  if (importanceEl) importanceEl.textContent = evalRes.reason_importance;
  if (targetEl) targetEl.textContent = `${leaveData.day_of_week} (${leaveData.shift_type})`;
  if (riskEl) riskEl.textContent = `${Math.round(evalRes.exploitation_risk_score * 100)}%`;
  if (trustEl) trustEl.textContent = `${Math.round(evalRes.trust_score * 100)}%`;
  if (explanationEl) explanationEl.textContent = evalRes.pattern_analysis;
}

/**
 * Fetch and Render Employee Personal Schedule
 */
async function fetchEmployeePersonalRoster() {
  if (!state.currentUser || !state.currentUser.id) return;
  try {
    const res = await fetch(`/api/employee/my-roster?employee_id=${state.currentUser.id}`);
    const data = await res.json();
    if (data.success) {
      renderEmployeePersonalRoster(data.data);
    }
  } catch (err) {
    console.error("Error fetching personal roster:", err);
  }
}

function renderEmployeePersonalRoster(rosterData) {
  const hoursEl = document.getElementById("emp-kpi-hours");
  const barEl = document.getElementById("emp-kpi-bar");
  const shiftsEl = document.getElementById("emp-kpi-shifts");
  const extrasEl = document.getElementById("emp-kpi-extras");
  const container = document.getElementById("emp-shifts-container");
  const badge = document.getElementById("badge-emp-shifts-count");

  const totalHours = rosterData.total_assigned_hours || 0;
  const maxHours = rosterData.max_weekly_hours || 40;
  const pct = Math.min(100, Math.round((totalHours / maxHours) * 100));

  if (hoursEl) hoursEl.textContent = `${totalHours}h / ${maxHours}h`;
  if (barEl) barEl.style.width = `${pct}%`;
  if (shiftsEl) shiftsEl.textContent = `${rosterData.shifts.length} shifts`;
  if (extrasEl) extrasEl.textContent = `${rosterData.extra_shifts_count} extra`;
  if (badge) badge.textContent = `${rosterData.shifts.length} Shifts`;

  if (!container) return;

  if (rosterData.shifts.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align:center; padding:3rem 1rem; color:var(--slate-500);">
        <p style="font-size:1.1rem; font-weight:700;">No shifts scheduled for this week yet.</p>
        <p style="font-size:0.85rem;">Check back after the weekly master roster is generated by your manager.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = rosterData.shifts.map(s => {
    const isExtra = s.is_replacement_shift;
    return `
      <div class="emp-shift-card ${isExtra ? "extra-shift" : ""}">
        <div>
          ${isExtra ? `
            <span class="extra-shift-banner">⭐ Extra Shift (Substituted for ${escapeHtml(s.substitute_for)})</span>
          ` : ""}
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
            <strong style="font-size:1.05rem; color:var(--slate-900);">${escapeHtml(s.day_of_week)}</strong>
            <span class="skill-badge badge-${s.role.toLowerCase()}">${escapeHtml(s.role)}</span>
          </div>
          <div style="font-size:0.85rem; color:var(--slate-600); margin-bottom:0.5rem;">
            Shift: <strong>${escapeHtml(s.shift_type)} (8 hours)</strong>
          </div>
        </div>
        <div style="padding-top:0.5rem; border-top:1px solid var(--slate-100); font-size:0.75rem; color:var(--slate-500);">
          ${isExtra ? `Covering unplanned absence for coworker.` : `Regular scheduled roster shift.`}
        </div>
      </div>
    `;
  }).join("");
}

/**
 * Handle Reset to Seed Data
 */
async function handleResetSeed() {
  if (!confirm("Reset all employees, requests, rosters, and audits back to clean seed data?")) return;
  try {
    const res = await fetch("/api/employees/reset", { method: "POST" });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message, "success");
      if (state.currentUser.role === "admin") {
        await initAdminPortal();
      } else {
        await fetchEmployeePersonalRoster();
      }
    }
  } catch (err) {
    showToast("Failed to reset seed data.", "error");
  }
}

/**
 * Modal Helpers
 */
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "flex";
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.style.display = "none";
}

// Global modal bindings
window.openModal = openModal;
window.closeModal = closeModal;
window.switchAdminTab = switchAdminTab;
window.switchEmployeeTab = switchEmployeeTab;
window.toggleSkillSelection = toggleSkillSelection;
window.handleDeleteEmployee = handleDeleteEmployee;
window.openLeaveDetailModal = openLeaveDetailModal;
window.handleUrgentAction = handleUrgentAction;
window.openProofModal = openProofModal;
window.handleMarkAbsent = handleMarkAbsent;
window.handleAssignReplacement = handleAssignReplacement;

/**
 * UI Toast notification helper
 */
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
