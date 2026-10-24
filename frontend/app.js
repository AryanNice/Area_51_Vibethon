/**
 * VibeRoster Frontend Application Logic
 * Integrates CP-SAT Solver API, Natural Language AI Leave Intake,
 * Conflict Diagnosis, and Plain Scoring Replacement Ranking.
 */

// Application State
const state = {
  employees: [],
  available_skills: [],
  shifts: [],
  leaves: [],
  roster: [],
  roster_feasible: true,
  roster_conflicts: [],
  employee_stats: {},
  active_leave_filter: "pending",
  extracted_leave: null,
  active_modal_shift: null,
};

const DAYS_ORDER = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

// Document Ready
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchInitialData();
});

/**
 * Initialize all DOM event listeners
 */
function initEventListeners() {
  // Tab Switching
  document.querySelectorAll(".nav-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document
        .querySelectorAll(".nav-tab")
        .forEach((t) => t.classList.remove("active"));
      document
        .querySelectorAll(".tab-content")
        .forEach((c) => c.classList.remove("active"));

      tab.classList.add("active");
      const targetId = tab.getAttribute("data-tab");
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add("active");
    });
  });

  // Header Actions
  document
    .getElementById("btn-reset-seed")
    ?.addEventListener("click", resetToSeed);
  document
    .getElementById("btn-simulate-impossible")
    ?.addEventListener("click", simulateImpossible);
  document
    .getElementById("btn-generate-roster-top")
    ?.addEventListener("click", generateRoster);
  document
    .getElementById("btn-generate-roster")
    ?.addEventListener("click", generateRoster);

  // Leave Presets
  document.querySelectorAll(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const text = btn.getAttribute("data-preset");
      const input = document.getElementById("leave-text-input");
      if (input) {
        input.value = text;
        showToast("Preset loaded into message box", "info");
      }
    });
  });

  // AI Extraction Button
  document
    .getElementById("btn-parse-ai")
    ?.addEventListener("click", handleParseLeave);

  // Submit Extracted Leave to Manager
  document
    .getElementById("btn-submit-to-manager")
    ?.addEventListener("click", handleSubmitExtractedLeave);

  // Leave Queue Filter Tabs
  document.querySelectorAll(".btn-tab[data-queue-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".btn-tab[data-queue-filter]")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.active_leave_filter = btn.getAttribute("data-queue-filter");
      renderLeaveQueue();
    });
  });

  // Add Employee Form
  document
    .getElementById("add-employee-form")
    ?.addEventListener("submit", handleAddEmployee);

  // Modal Close
  document
    .getElementById("btn-close-modal")
    ?.addEventListener("click", closeModal);
  document
    .getElementById("replacement-modal")
    ?.addEventListener("click", (e) => {
      if (e.target.id === "replacement-modal") closeModal();
    });
}

/**
 * Fetch initial data from server
 */
async function fetchInitialData() {
  try {
    const res = await fetch("/api/data");
    if (!res.ok) throw new Error("Failed to load application data");
    const data = await res.json();

    state.employees = data.employees || [];
    state.available_skills = data.available_skills || [];
    state.shifts = data.shifts || [];
    state.leaves = data.leaves || [];
    state.roster = data.roster || [];
    state.roster_feasible = data.roster_feasible ?? true;
    state.roster_conflicts = data.roster_conflicts || [];
    state.employee_stats = data.employee_stats || {};

    renderAll();

    // Auto-generate roster on first load if empty
    if (state.roster.length === 0) {
      await generateRoster();
    }
  } catch (err) {
    showToast("Error connecting to server. Please ensure backend is running.", "error");
    console.error(err);
  }
}

/**
 * Render all views
 */
function renderAll() {
  renderStats();
  renderRoster();
  renderWorkload();
  renderLeaveQueue();
  renderEmployeeComponents();
}

/**
 * Render KPI stats
 */
function renderWorkload() {
  const container = document.getElementById("workload-list");
  if (!container) return;

  if (state.employees.length === 0) {
    container.innerHTML = `<p class="text-muted text-sm">No employees configured.</p>`;
    return;
  }

  container.innerHTML = state.employees
    .map((emp) => {
      const stats = state.employee_stats[emp.id] || {
        assigned_hours: 0,
        shifts_count: 0,
      };
      const assigned = stats.assigned_hours || 0;
      const maxH = emp.max_hours || 40;
      const pct = Math.min(100, Math.round((assigned / maxH) * 100));
      const isHigh = pct >= 90;

      return `
      <div class="workload-item">
        <div class="workload-top">
          <span class="workload-name">${escapeHtml(emp.name)}</span>
          <span class="workload-hours">${assigned}h / ${maxH}h (${stats.shifts_count} shifts)</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill ${isHigh ? "warning" : ""}" style="width: ${pct}%"></div>
        </div>
      </div>
    `;
    })
    .join("");
}

function renderStats() {
  document.getElementById("stat-total-shifts").textContent =
    state.shifts.length;
  document.getElementById("stat-assigned-shifts").textContent = `${state.roster.length} / ${state.shifts.length}`;

  const coveragePct =
    state.shifts.length > 0
      ? Math.round((state.roster.length / state.shifts.length) * 100)
      : 0;
  document.getElementById("stat-coverage-pct").textContent =
    `${coveragePct}% staffed`;

  const approvedLeaves = state.leaves.filter(
    (l) => l.status === "approved",
  ).length;
  document.getElementById("stat-approved-leaves").textContent = approvedLeaves;

  const totalCap = state.employees.reduce(
    (sum, e) => sum + (e.max_hours || 40),
    0,
  );
  document.getElementById("stat-total-capacity").textContent = `${totalCap}h`;
  document.getElementById("stat-capacity-sub").textContent =
    `${state.employees.length} qualified employees`;

  // Badges
  const pendingCount = state.leaves.filter(
    (l) => l.status === "pending",
  ).length;
  const pendingBadge = document.getElementById("pending-leave-badge");
  if (pendingBadge) {
    pendingBadge.textContent = pendingCount;
    pendingBadge.style.display = pendingCount > 0 ? "inline-block" : "none";
  }

  const empBadge = document.getElementById("emp-count-badge");
  if (empBadge) empBadge.textContent = state.employees.length;
  const teamTotal = document.getElementById("team-total-count");
  if (teamTotal) teamTotal.textContent = state.employees.length;
}

/**
 * Render Roster Grid & Solver Status Banner
 */
function renderRoster() {
  const banner = document.getElementById("solver-status-banner");
  const bannerTitle = document.getElementById("solver-status-title");
  const bannerDesc = document.getElementById("solver-status-desc");
  const bannerIcon = document.getElementById("solver-status-icon");
  const conflictList = document.getElementById("conflict-list");

  // Status Banner formatting
  if (!state.roster_feasible && state.roster_conflicts.length > 0) {
    banner.className = "status-banner status-banner-danger";
    bannerIcon.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
    `;
    bannerTitle.textContent =
      "No Feasible Schedule Found (Hard Constraint Conflict)";
    bannerDesc.textContent =
      "Google OR-Tools CP-SAT detected conflicting requirements that cannot be simultaneously satisfied:";
    conflictList.style.display = "flex";
    conflictList.innerHTML = state.roster_conflicts
      .map(
        (c) =>
          `<div class="conflict-item"><strong>Conflict:</strong> ${escapeHtml(c)}</div>`,
      )
      .join("");
  } else if (state.roster.length > 0) {
    banner.className = "status-banner status-banner-success";
    bannerIcon.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
    `;
    bannerTitle.textContent = "Optimal Roster Solved & Fully Staffed";
    bannerDesc.textContent = `All ${state.shifts.length} shifts matched with certified skills, approved leaves honored, and weekly hour caps satisfied.`;
    conflictList.style.display = "none";
  } else {
    banner.className = "status-banner status-banner-info";
    bannerIcon.innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2.2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
    `;
    bannerTitle.textContent = "Roster Ready to Solve";
    bannerDesc.textContent =
      'Click "Generate Weekly Roster" to run Google OR-Tools CP-SAT.';
    conflictList.style.display = "none";
  }

  // Schedule Grid (7 Days)
  const grid = document.getElementById("roster-days-grid");
  if (!grid) return;

  grid.innerHTML = DAYS_ORDER.map((day) => {
    const dayShifts = state.shifts.filter((s) => s.day === day);

    const shiftCardsHtml = dayShifts
      .map((s) => {
        const assignment = state.roster.find((a) => a.shift_id === s.id);
        const skillClass = `skill-${(s.required_skill || "").toLowerCase()}`;

        if (!assignment) {
          return `
            <div class="shift-card empty-assignment">
              <span class="shift-name-tag">${escapeHtml(s.name)}</span>
              <span class="badge skill-badge ${skillClass}">${escapeHtml(s.required_skill)}</span>
              <span>Unassigned (Infeasible)</span>
            </div>
          `;
        }

        return `
          <div class="shift-card" id="card-${s.id}">
            <div class="shift-top">
              <span class="shift-name-tag">${escapeHtml(s.name)}</span>
              <span class="shift-hours">${s.hours || 8}h</span>
            </div>
            
            <div class="flex-align-center gap-2">
              <span class="badge skill-badge ${skillClass}">${escapeHtml(s.required_skill)}</span>
            </div>

            <div class="assigned-employee" title="${escapeHtml(assignment.employee_name)}">
              ${escapeHtml(assignment.employee_name)}
            </div>

            ${
              assignment.was_replaced
                ? `<span class="replacement-badge" title="Replaced ${escapeHtml(assignment.replaced_from)}">↺ Sub for ${escapeHtml(assignment.replaced_from)}</span>`
                : ""
            }

            <div class="shift-actions">
              <button class="btn-absent" onclick="handleMarkAbsent('${s.id}', '${assignment.employee_id}')" title="Mark ${escapeHtml(assignment.employee_name)} absent for this shift and find replacements">
                Mark Absent
              </button>
            </div>
          </div>
        `;
      })
      .join("");

    return `
      <div class="roster-day-col">
        <div class="day-header">
          <span class="day-name">${day}</span>
          <span class="day-badge">${dayShifts.length} shifts</span>
        </div>
        <div class="day-shifts">
          ${shiftCardsHtml}
        </div>
      </div>
    `;
  }).join("");
}

/**
 * Generate weekly roster via CP-SAT
 */
async function generateRoster() {
  const spinner = document.getElementById("roster-spinner");
  const btnText = document.getElementById("btn-roster-text");
  if (spinner) spinner.style.display = "inline-block";
  if (btnText) btnText.textContent = "Solving CP-SAT Model...";

  try {
    const res = await fetch("/api/roster/generate", { method: "POST" });
    if (!res.ok) throw new Error("Solver request failed");
    const data = await res.json();

    state.roster_feasible = data.feasible;
    state.roster = data.assignments || [];
    state.roster_conflicts = data.conflicts || [];
    state.employee_stats = data.employee_stats || {};

    renderAll();

    if (data.feasible) {
      showToast(
        `Weekly roster successfully generated (${data.assignments_count} shifts assigned)!`,
        "success",
      );
    } else {
      showToast(
        "No feasible schedule: solver detected conflicting hard constraints.",
        "error",
      );
    }
  } catch (err) {
    showToast("Failed to run CP-SAT solver.", "error");
    console.error(err);
  } finally {
    if (spinner) spinner.style.display = "none";
    if (btnText) btnText.textContent = "⚡ Generate Weekly Roster";
  }
}

/**
 * Simulate impossible conflict scenario
 */
async function simulateImpossible() {
  try {
    showToast("Simulating conflicting constraint scenario...", "info");
    const res = await fetch("/api/roster/simulate-impossible", {
      method: "POST",
    });
    if (!res.ok) throw new Error("Simulation failed");
    const data = await res.json();

    state.roster_feasible = data.feasible;
    state.roster = data.assignments || [];
    state.roster_conflicts = data.conflicts || [];
    state.employee_stats = data.employee_stats || {};

    // Also reload leaves state
    const dataRes = await fetch("/api/data");
    const freshData = await dataRes.json();
    state.leaves = freshData.leaves || [];

    renderAll();
    showToast(
      "Impossible scenario triggered! See the detailed conflict explanation in the banner.",
      "error",
    );
  } catch (err) {
    showToast("Failed to simulate impossible case.", "error");
    console.error(err);
  }
}

/**
 * Reset to seed data
 */
async function resetToSeed() {
  if (
    !confirm(
      "Reset all employees, leaves, and schedule back to original seed data?",
    )
  )
    return;
  try {
    const res = await fetch("/api/reset", { method: "POST" });
    if (!res.ok) throw new Error("Reset failed");
    await fetchInitialData();
    showToast("Reset to pre-loaded seed data complete.", "success");
  } catch (err) {
    showToast("Failed to reset seed data.", "error");
    console.error(err);
  }
}

/**
 * AI Leave Parsing handler
 */
async function handleParseLeave() {
  const input = document.getElementById("leave-text-input");
  const text = input ? input.value.trim() : "";
  if (!text) {
    showToast("Please enter or select a message to parse.", "error");
    return;
  }

  const senderSelect = document.getElementById("leave-sender-select");
  const senderId = senderSelect ? senderSelect.value : "";

  const spinner = document.getElementById("parse-spinner");
  if (spinner) spinner.style.display = "inline-block";

  try {
    const res = await fetch("/api/leave/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, sender_id: senderId }),
    });

    if (!res.ok) throw new Error("Failed to parse message");
    const parsed = await res.json();
    state.extracted_leave = parsed;

    // Display extraction preview
    const preview = document.getElementById("ai-extraction-preview");
    document.getElementById("preview-confidence").textContent =
      `Confidence: ${Math.round((parsed.confidence || 1) * 100)}%`;
    document.getElementById("preview-emp-name").textContent =
      parsed.employee_name || "Unknown";
    document.getElementById("preview-days").textContent = (
      parsed.days || []
    ).join(", ");
    document.getElementById("preview-shift").textContent =
      parsed.shift || "All Day";
    document.getElementById("preview-reason").textContent =
      parsed.reason || "Personal";

    if (preview) preview.style.display = "block";
    showToast("Message successfully converted to structured request!", "success");
  } catch (err) {
    showToast("AI extraction error.", "error");
    console.error(err);
  } finally {
    if (spinner) spinner.style.display = "none";
  }
}

/**
 * Submit extracted leave request to manager approval queue
 */
async function handleSubmitExtractedLeave() {
  if (!state.extracted_leave) return;

  try {
    const res = await fetch("/api/leave/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        employee_id: state.extracted_leave.employee_id,
        days: state.extracted_leave.days,
        shift: state.extracted_leave.shift,
        reason: state.extracted_leave.reason,
        raw_text: state.extracted_leave.raw_text,
      }),
    });

    if (!res.ok) throw new Error("Failed to submit leave request");
    const data = await res.json();

    // Refresh leaves from server
    const dataRes = await fetch("/api/data");
    const freshData = await dataRes.json();
    state.leaves = freshData.leaves || [];

    // Clear form & preview
    state.extracted_leave = null;
    document.getElementById("ai-extraction-preview").style.display = "none";
    document.getElementById("leave-text-input").value = "";

    renderAll();
    showToast("Leave request sent to manager approval queue!", "success");
  } catch (err) {
    showToast("Failed to submit leave request.", "error");
    console.error(err);
  }
}

/**
 * Render Manager Leave Queue
 */
function renderLeaveQueue() {
  const container = document.getElementById("leave-requests-container");
  if (!container) return;

  const pending = state.leaves.filter((l) => l.status === "pending");
  const approved = state.leaves.filter((l) => l.status === "approved");

  document.getElementById("queue-pending-count").textContent = pending.length;
  document.getElementById("queue-approved-count").textContent = approved.length;

  let filtered = state.leaves;
  if (state.active_leave_filter === "pending") filtered = pending;
  else if (state.active_leave_filter === "approved") filtered = approved;

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="text-align: center; padding: 24px; color: var(--text-dim); font-size: 0.88rem;">
        No leave requests found under "${state.active_leave_filter}" filter.
      </div>
    `;
    return;
  }

  container.innerHTML = filtered
    .map((l) => {
      const statusClass = `status-${l.status}`;
      const isPending = l.status === "pending";

      return `
      <div class="request-card">
        <div class="request-top">
          <span class="request-emp">${escapeHtml(l.employee_name)}</span>
          <span class="status-chip ${statusClass}">${capitalize(l.status)}</span>
        </div>

        <div class="request-meta">
          <span>📅 <strong>${escapeHtml(l.day)}</strong> (${escapeHtml(l.shift || "All Day")})</span>
          <span>💬 ${escapeHtml(l.reason)}</span>
        </div>

        ${l.raw_text ? `<div class="request-raw">"${escapeHtml(l.raw_text)}"</div>` : ""}

        ${
          isPending
            ? `
          <div class="request-actions">
            <button class="btn btn-danger btn-xs" onclick="handleLeaveAction('${l.id}', 'reject')">
              Reject
            </button>
            <button class="btn btn-success btn-xs" onclick="handleLeaveAction('${l.id}', 'approve')">
              ✓ Approve Request
            </button>
          </div>
        `
            : ""
        }
      </div>
    `;
    })
    .join("");
}

/**
 * Approve or Reject Leave Request
 */
async function handleLeaveAction(leaveId, action) {
  try {
    const res = await fetch(`/api/leave/${leaveId}/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });

    if (!res.ok) throw new Error("Action failed");

    // Refresh state
    const dataRes = await fetch("/api/data");
    const freshData = await dataRes.json();
    state.leaves = freshData.leaves || [];

    renderAll();
    showToast(
      `Leave request ${action}d! It will ${action === "approve" ? "now be enforced as a hard constraint" : "not affect the schedule"}.`,
      action === "approve" ? "success" : "info",
    );
  } catch (err) {
    showToast(`Failed to ${action} leave.`, "error");
    console.error(err);
  }
}

/**
 * Render Employee Components (Form, Checkboxes, Team List)
 */
function renderEmployeeComponents() {
  // Skills checkboxes in Add Form
  const cbGroup = document.getElementById("skills-checkbox-group");
  if (cbGroup && cbGroup.children.length === 0) {
    cbGroup.innerHTML = state.available_skills
      .map(
        (skill) => `
        <label class="checkbox-chip">
          <input type="checkbox" name="emp-skill" value="${escapeHtml(skill)}">
          <span>${escapeHtml(skill)}</span>
        </label>
      `,
      )
      .join("");
  }

  // Sender select in AI leave intake
  const senderSelect = document.getElementById("leave-sender-select");
  if (senderSelect) {
    const currVal = senderSelect.value;
    senderSelect.innerHTML =
      `<option value="">-- Auto-detect from message text --</option>` +
      state.employees
        .map(
          (e) =>
            `<option value="${e.id}" ${e.id === currVal ? "selected" : ""}>${escapeHtml(e.name)}</option>`,
        )
        .join("");
  }

  // Active Team Members Grid
  const empGrid = document.getElementById("employees-grid");
  if (!empGrid) return;

  empGrid.innerHTML = state.employees
    .map(
      (emp) => `
    <div class="employee-card">
      <div class="emp-info">
        <h4>${escapeHtml(emp.name)}</h4>
        <div class="emp-skills">
          ${(emp.skills || [])
            .map((s) => {
              const sClass = `skill-${s.toLowerCase()}`;
              return `<span class="badge skill-badge ${sClass}">${escapeHtml(s)}</span>`;
            })
            .join("")}
        </div>
      </div>
      <div style="display: flex; align-items: center; gap: 12px;">
        <div class="emp-cap">
          <div>Cap: <strong>${emp.max_hours || 40}h</strong></div>
          <div style="font-size: 0.72rem; color: var(--text-dim);">weekly max</div>
        </div>
        <button class="btn btn-secondary btn-xs" onclick="handleDeleteEmployee('${emp.id}')" title="Delete employee">
          🗑
        </button>
      </div>
    </div>
  `,
    )
    .join("");
}

/**
 * Handle Add Employee Form Submission
 */
async function handleAddEmployee(e) {
  e.preventDefault();
  const nameInput = document.getElementById("emp-name-input");
  const hoursInput = document.getElementById("emp-hours-input");
  const checkedSkills = Array.from(
    document.querySelectorAll("input[name='emp-skill']:checked"),
  ).map((cb) => cb.value);

  const name = nameInput ? nameInput.value.trim() : "";
  const max_hours = hoursInput ? parseInt(hoursInput.value, 10) : 40;

  if (!name) {
    showToast("Employee name is required.", "error");
    return;
  }
  if (checkedSkills.length === 0) {
    showToast("Please select at least one skill.", "error");
    return;
  }

  try {
    const res = await fetch("/api/employees", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, skills: checkedSkills, max_hours }),
    });

    if (!res.ok) throw new Error("Failed to add employee");
    const data = await res.json();

    state.employees.push(data.employee);

    // Reset form
    nameInput.value = "";
    document
      .querySelectorAll("input[name='emp-skill']")
      .forEach((cb) => (cb.checked = false));

    renderAll();
    showToast(
      `Employee ${data.employee.name} added with ${checkedSkills.join(", ")}!`,
      "success",
    );
  } catch (err) {
    showToast("Failed to add employee.", "error");
    console.error(err);
  }
}

/**
 * Delete Employee
 */
async function handleDeleteEmployee(empId) {
  const emp = state.employees.find((e) => e.id === empId);
  if (
    !confirm(
      `Remove ${emp ? emp.name : "employee"} from team and clear assignments?`,
    )
  )
    return;

  try {
    const res = await fetch(`/api/employees/${empId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete employee");

    state.employees = state.employees.filter((e) => e.id !== empId);
    state.leaves = state.leaves.filter((l) => l.employee_id !== empId);

    renderAll();
    showToast("Employee removed from team.", "info");
  } catch (err) {
    showToast("Failed to delete employee.", "error");
    console.error(err);
  }
}

/**
 * Mark Absent and Open Replacement Ranking Modal
 */
async function handleMarkAbsent(shiftId, employeeId) {
  try {
    const res = await fetch("/api/roster/mark-absent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ shift_id: shiftId, employee_id: employeeId }),
    });

    if (!res.ok) throw new Error("Failed to compute replacement rankings");
    const data = await res.json();

    state.active_modal_shift = data.shift;

    // Populate modal
    document.getElementById("modal-shift-title").textContent =
      `Absent: ${escapeHtml(data.absent_employee_name)}`;
    document.getElementById("modal-shift-subtitle").textContent =
      `Shift: ${data.shift.day} ${data.shift.shift_name} (${data.shift.hours}h) | Required Skill: ${data.shift.required_skill}`;

    const skillClass = `skill-${(data.shift.required_skill || "").toLowerCase()}`;
    document.getElementById("target-shift-card").innerHTML = `
      <div>
        <div style="font-size: 0.82rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Target Shift</div>
        <div style="font-size: 1.05rem; font-weight: 800; color: #fff;">${data.shift.day} ${data.shift.shift_name}</div>
      </div>
      <div>
        <span class="badge skill-badge ${skillClass}">${escapeHtml(data.shift.required_skill)} Required</span>
      </div>
    `;

    renderRankedCandidates(shiftId, data.ranked_replacements);

    // Show modal
    document.getElementById("replacement-modal").style.display = "flex";
  } catch (err) {
    showToast("Failed to process absence.", "error");
    console.error(err);
  }
}

/**
 * Render Ranked Replacement Candidates in Modal
 */
function renderRankedCandidates(shiftId, candidates) {
  const container = document.getElementById("ranked-candidates-list");
  if (!container) return;

  if (candidates.length === 0) {
    container.innerHTML = `<p class="text-muted text-sm">No alternative candidates in the system.</p>`;
    return;
  }

  container.innerHTML = candidates
    .map((c, idx) => {
      const isTop = idx === 0 && c.is_eligible;
      const cardClass = c.is_eligible ? "eligible" : "ineligible";
      const scoreClass = c.score >= 80 ? "score-high" : "score-low";

      return `
      <div class="candidate-card ${cardClass}">
        <div class="candidate-top">
          <div class="candidate-rank-wrap">
            <span class="rank-badge ${isTop ? "top-pick" : ""}">
              ${isTop ? "★ Top Pick" : `#${idx + 1}`}
            </span>
            <span class="candidate-name">${escapeHtml(c.name)}</span>
          </div>
          <div class="flex-align-center gap-2">
            <span class="score-badge ${scoreClass}">Score: ${c.score} pts</span>
            <span class="status-chip ${c.is_eligible ? "status-approved" : "status-rejected"}">
              ${c.is_eligible ? "Eligible" : "Ineligible"}
            </span>
          </div>
        </div>

        <div class="candidate-reasons">
          ${(c.reasons || [])
            .map(
              (r) =>
                `<span class="reason-bullet"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> ${escapeHtml(r)}</span>`,
            )
            .join("")}
          ${(c.warnings || [])
            .map(
              (w) =>
                `<span class="warning-bullet"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg> ${escapeHtml(w)}</span>`,
            )
            .join("")}
        </div>

        ${
          c.is_eligible
            ? `
          <div class="candidate-action">
            <button class="btn btn-primary btn-sm" onclick="handleAssignReplacement('${shiftId}', '${c.employee_id}')">
              Assign Replacement
            </button>
          </div>
        `
            : ""
        }
      </div>
    `;
    })
    .join("");
}

/**
 * Assign Replacement to Shift
 */
async function handleAssignReplacement(shiftId, replacementEmpId) {
  try {
    const res = await fetch("/api/roster/assign-replacement", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        shift_id: shiftId,
        replacement_employee_id: replacementEmpId,
      }),
    });

    if (!res.ok) throw new Error("Replacement assignment failed");
    const data = await res.json();

    state.roster = data.roster;
    state.employee_stats = data.employee_stats;

    closeModal();
    renderAll();
    showToast(data.message, "success");
  } catch (err) {
    showToast("Failed to assign replacement.", "error");
    console.error(err);
  }
}

/**
 * Close modal
 */
function closeModal() {
  const modal = document.getElementById("replacement-modal");
  if (modal) modal.style.display = "none";
}

/**
 * UI Toast notification helper
 */
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

/**
 * Helper: Escape HTML strings to prevent XSS
 */
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// Global scope binding for inline onclicks
window.handleMarkAbsent = handleMarkAbsent;
window.handleLeaveAction = handleLeaveAction;
window.handleDeleteEmployee = handleDeleteEmployee;
window.handleAssignReplacement = handleAssignReplacement;
