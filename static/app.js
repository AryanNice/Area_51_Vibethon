/**
 * AutoRoster AI MVP Frontend Application.
 * Zero external JS dependencies.
 */

const API_BASE = "";

const app = {
  state: {
    employees: [],
    availableSkills: ["Supervisor", "Barista", "Cook", "Cashier", "Server"],
    leaveRequests: [],
    sampleMessages: [],
    currentRoster: null,
    rosterStats: null,
    selectedSlotForAbsence: null,
    leaveFilter: "ALL",
    lastParsedLeave: null
  },

  async init() {
    this.bindEvents();
    this.renderSkillChips();
    await this.loadEmployees();
    await this.loadLeaves();
    await this.loadRoster();
  },

  // --- Toast Notifications ---
  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast ${type === "error" ? "toast-error" : type === "success" ? "toast-success" : ""}`;
    const icon = type === "error" ? "⚠️" : type === "success" ? "✅" : "ℹ️";
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(10px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3800);
  },

  // --- Navigation ---
  bindEvents() {
    // Tab switching
    document.querySelectorAll(".tab-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const tabId = btn.getAttribute("data-tab");
        this.switchTab(tabId);
      });
    });

    // Pitch guide button in header
    document.getElementById("btn-open-pitch")?.addEventListener("click", () => {
      this.switchTab("tab-pitch");
    });

    // Reset seed data
    document.getElementById("btn-reset-data")?.addEventListener("click", () => {
      if (confirm("Reset all staff, leave requests, and schedules to initial seed state?")) {
        this.resetSeedData();
      }
    });

    document.getElementById("btn-quick-seed")?.addEventListener("click", () => {
      this.resetSeedData();
    });

    // Screen 1: Hours Slider Display
    const hoursInput = document.getElementById("emp-hours");
    const hoursDisplay = document.getElementById("hours-display");
    if (hoursInput && hoursDisplay) {
      hoursInput.addEventListener("input", (e) => {
        hoursDisplay.textContent = `${e.target.value}h`;
      });
    }

    // Screen 1: Add Employee Form
    const empForm = document.getElementById("form-add-employee");
    if (empForm) {
      empForm.addEventListener("submit", (e) => this.handleAddEmployee(e));
    }

    // Screen 2: AI Parse Button
    document.getElementById("btn-parse-ai")?.addEventListener("click", () => {
      this.handleParseMessage();
    });

    // Screen 2: Submit Parsed Leave
    document.getElementById("btn-submit-parsed-leave")?.addEventListener("click", () => {
      this.handleSubmitParsedLeave();
    });

    // Screen 2: Filter Leave Requests
    document.querySelectorAll(".filter-leave-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".filter-leave-btn").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        this.state.leaveFilter = btn.getAttribute("data-filter");
        this.renderLeavesList();
      });
    });

    // Screen 3: Generate Roster Button
    document.getElementById("btn-generate-roster")?.addEventListener("click", () => {
      this.generateRoster();
    });

    // Screen 3: Trigger Impossible Scenario Button
    document.getElementById("btn-trigger-impossible")?.addEventListener("click", () => {
      this.triggerImpossibleScenario();
    });

    // Screen 4: Mark Absent Action
    document.getElementById("btn-mark-absent-action")?.addEventListener("click", () => {
      this.handleMarkAbsent();
    });
  },

  switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-tab") === tabId);
    });
    document.querySelectorAll(".tab-panel").forEach(p => {
      p.classList.toggle("active", p.id === tabId);
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  },

  // ==========================================
  // SCREEN 1: STAFF & SKILLS
  // ==========================================
  renderSkillChips() {
    const container = document.getElementById("skill-chips-container");
    if (!container) return;
    container.innerHTML = "";
    this.state.availableSkills.forEach(skill => {
      const chip = document.createElement("div");
      chip.innerHTML = `
        <input type="checkbox" id="skill-${skill}" name="skills" value="${skill}" class="skill-chip-checkbox">
        <label for="skill-${skill}" class="skill-chip-label">${skill}</label>
      `;
      container.appendChild(chip);
    });
  },

  async loadEmployees() {
    const loading = document.getElementById("staff-loading");
    const empty = document.getElementById("staff-empty");
    const list = document.getElementById("staff-list");

    try {
      if (loading) loading.style.display = "block";
      if (empty) empty.style.display = "none";

      const res = await fetch(`${API_BASE}/api/employees`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      this.state.employees = data.data;
      if (data.available_skills) {
        this.state.availableSkills = data.available_skills;
      }

      // Update badge
      document.getElementById("badge-staff-count").textContent = this.state.employees.length;

      // Update employee dropdown in Screen 2
      this.populateEmployeeDropdown();

      this.renderEmployeesList();
    } catch (err) {
      this.showToast(`Unable to load staff: ${err.message}`, "error");
    } finally {
      if (loading) loading.style.display = "none";
    }
  },

  renderEmployeesList() {
    const list = document.getElementById("staff-list");
    const empty = document.getElementById("staff-empty");
    if (!list) return;

    if (this.state.employees.length === 0) {
      list.innerHTML = "";
      if (empty) empty.style.display = "block";
      return;
    }

    if (empty) empty.style.display = "none";
    list.innerHTML = "";

    this.state.employees.forEach(emp => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.margin = "0";
      card.style.padding = "0.85rem";

      const skillsBadges = emp.skills.map(s => {
        const cls = `badge-${s.toLowerCase()}`;
        return `<span class="badge ${cls}">${s}</span>`;
      }).join(" ");

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.5rem;">
          <div>
            <div style="font-weight:700; color:var(--slate-900); font-size:0.95rem;">${emp.name}</div>
            <div style="font-size:0.75rem; color:var(--slate-500);">${emp.email || 'No email registered'}</div>
          </div>
          <button class="btn btn-outline-danger btn-sm" style="padding:0.2rem 0.45rem; font-size:0.7rem;" onclick="app.deleteEmployee('${emp.id}')">
            Delete
          </button>
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:0.6rem;">
          <div style="display:flex; flex-wrap:wrap; gap:0.25rem;">
            ${skillsBadges}
          </div>
          <span class="badge" style="background:var(--slate-100); color:var(--slate-700); font-weight:700;">
            ${emp.max_weekly_hours}h/wk
          </span>
        </div>
      `;
      list.appendChild(card);
    });
  },

  async handleAddEmployee(e) {
    e.preventDefault();
    const errorBox = document.getElementById("staff-form-error");
    errorBox.style.display = "none";

    const name = document.getElementById("emp-name").value.trim();
    const max_hours = parseInt(document.getElementById("emp-hours").value, 10);
    const email = document.getElementById("emp-email").value.trim();
    const phone = document.getElementById("emp-phone").value.trim();

    const selectedSkills = Array.from(document.querySelectorAll("input[name='skills']:checked")).map(cb => cb.value);

    // Form validation
    if (!name) {
      errorBox.textContent = "Please enter the employee's full name.";
      errorBox.style.display = "block";
      return;
    }
    if (selectedSkills.length === 0) {
      errorBox.textContent = "Please select at least one qualified skill for this employee.";
      errorBox.style.display = "block";
      return;
    }

    const submitBtn = document.getElementById("btn-submit-employee");
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span class="spinner"></span> <span>Adding...</span>`;

    try {
      const res = await fetch(`${API_BASE}/api/employees`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({
          name,
          skills: selectedSkills,
          max_weekly_hours: max_hours,
          email,
          phone
        })
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      this.showToast(`Added ${name} to team!`, "success");
      // Reset form
      document.getElementById("emp-name").value = "";
      document.getElementById("emp-email").value = "";
      document.getElementById("emp-phone").value = "";
      document.querySelectorAll("input[name='skills']:checked").forEach(cb => cb.checked = false);

      await this.loadEmployees();
    } catch (err) {
      errorBox.textContent = err.message;
      errorBox.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>Add Employee</span>`;
    }
  },

  async deleteEmployee(empId) {
    if (!confirm("Are you sure you want to remove this employee?")) return;
    try {
      const res = await fetch(`${API_BASE}/api/employees/${empId}`, { method: "DELETE" });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);
      this.showToast("Employee removed.", "info");
      await this.loadEmployees();
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  async resetSeedData() {
    try {
      const res = await fetch(`${API_BASE}/api/employees/reset`, { method: "POST" });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);
      this.showToast("Restored pristine seed data!", "success");
      await this.loadEmployees();
      await this.loadLeaves();
      await this.loadRoster();
    } catch (err) {
      this.showToast(`Error resetting: ${err.message}`, "error");
    }
  },

  // ==========================================
  // SCREEN 2: AI LEAVE & AVAILABILITY
  // ==========================================
  populateEmployeeDropdown() {
    const select = document.getElementById("leave-emp-select");
    if (!select) return;
    select.innerHTML = "";
    this.state.employees.forEach(emp => {
      const opt = document.createElement("option");
      opt.value = emp.id;
      opt.textContent = `${emp.name} (${emp.skills.join(", ")})`;
      select.appendChild(opt);
    });
  },

  async loadLeaves() {
    try {
      const res = await fetch(`${API_BASE}/api/leaves`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      this.state.leaveRequests = data.data;
      if (data.sample_messages) {
        this.state.sampleMessages = data.sample_messages;
        this.renderPresetMessages();
      }

      // Update badge
      const pendingCount = this.state.leaveRequests.filter(l => l.status === "PENDING").length;
      document.getElementById("badge-leave-count").textContent = pendingCount || this.state.leaveRequests.length;

      this.renderLeavesList();
    } catch (err) {
      this.showToast(`Failed to load requests: ${err.message}`, "error");
    }
  },

  renderPresetMessages() {
    const container = document.getElementById("preset-messages-container");
    if (!container) return;
    container.innerHTML = "";

    this.state.sampleMessages.forEach(msg => {
      const chip = document.createElement("div");
      chip.className = "preset-chip";
      chip.innerHTML = `
        <div class="preset-author">${msg.employee_name}</div>
        <div style="color:var(--slate-700); font-style:italic;">"${msg.text}"</div>
      `;
      chip.addEventListener("click", () => {
        // Set employee in dropdown
        const empSelect = document.getElementById("leave-emp-select");
        if (empSelect) empSelect.value = msg.employee_id;
        // Set text
        const textarea = document.getElementById("raw-message-text");
        if (textarea) textarea.value = msg.text;
        // Auto trigger parse for snappy demo experience
        this.handleParseMessage();
      });
      container.appendChild(chip);
    });
  },

  async handleParseMessage() {
    const text = document.getElementById("raw-message-text").value.trim();
    if (!text) {
      this.showToast("Please enter an employee message to parse.", "error");
      return;
    }

    const parseBtn = document.getElementById("btn-parse-ai");
    parseBtn.disabled = true;
    parseBtn.innerHTML = `<span class="spinner"></span> <span>AI Parsing...</span>`;

    try {
      const res = await fetch(`${API_BASE}/api/leaves/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ text })
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      const parsed = data.data;
      this.state.lastParsedLeave = parsed;

      // If AI detected employee name in text, sync the dropdown
      if (parsed.detected_employee_id) {
        const empSelect = document.getElementById("leave-emp-select");
        if (empSelect) empSelect.value = parsed.detected_employee_id;
      }

      // Display Preview Card
      const preview = document.getElementById("ai-parse-result");
      preview.style.display = "block";
      document.getElementById("parse-day").textContent = parsed.day_of_week;
      document.getElementById("parse-shift").textContent = parsed.shift_type;
      document.getElementById("parse-reason").textContent = parsed.reason;
      document.getElementById("parse-confidence").textContent = `${Math.round(parsed.confidence * 100)}% Confident`;
      document.getElementById("parse-explanation").textContent = parsed.explanation;

      this.showToast("AI parsed structured request!", "success");
    } catch (err) {
      this.showToast(`AI Parsing error: ${err.message}`, "error");
    } finally {
      parseBtn.disabled = false;
      parseBtn.innerHTML = `<span>Parse with AI</span>`;
    }
  },

  async handleSubmitParsedLeave() {
    if (!this.state.lastParsedLeave) return;

    const empSelect = document.getElementById("leave-emp-select");
    const empId = empSelect.value;
    const rawText = document.getElementById("raw-message-text").value.trim();

    try {
      const res = await fetch(`${API_BASE}/api/leaves`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({
          employee_id: empId,
          raw_text: rawText,
          day_of_week: this.state.lastParsedLeave.day_of_week,
          shift_type: this.state.lastParsedLeave.shift_type,
          reason: this.state.lastParsedLeave.reason,
          confidence: this.state.lastParsedLeave.confidence,
          explanation: this.state.lastParsedLeave.explanation
        })
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      this.showToast("Leave request added to manager queue!", "success");
      // Hide parse preview & clear textarea
      document.getElementById("ai-parse-result").style.display = "none";
      document.getElementById("raw-message-text").value = "";
      this.state.lastParsedLeave = null;

      await this.loadLeaves();
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  async updateLeaveStatus(leaveId, newStatus) {
    try {
      const res = await fetch(`${API_BASE}/api/leaves/${leaveId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ status: newStatus })
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      this.showToast(`Request marked ${newStatus.toLowerCase()}!`, "success");
      await this.loadLeaves();
      // If we already had a roster generated, remind user to re-solve
      if (this.state.currentRoster && this.state.currentRoster.length > 0) {
        document.getElementById("badge-roster-status").textContent = "Re-solve needed";
      }
    } catch (err) {
      this.showToast(err.message, "error");
    }
  },

  renderLeavesList() {
    const list = document.getElementById("leave-list");
    const empty = document.getElementById("leave-empty");
    if (!list) return;

    let items = this.state.leaveRequests;
    if (this.state.leaveFilter !== "ALL") {
      items = items.filter(l => l.status === this.state.leaveFilter);
    }

    if (items.length === 0) {
      list.innerHTML = "";
      if (empty) empty.style.display = "block";
      return;
    }

    if (empty) empty.style.display = "none";
    list.innerHTML = "";

    items.forEach(item => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.margin = "0 0 0.75rem 0";
      card.style.padding = "0.85rem";

      const statusBadge = item.status === "APPROVED"
        ? `<span class="badge badge-approved">Approved</span>`
        : item.status === "REJECTED"
        ? `<span class="badge badge-rejected">Rejected</span>`
        : `<span class="badge badge-pending">Pending Review</span>`;

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:0.4rem;">
          <div>
            <div style="font-weight:700; color:var(--slate-900); font-size:0.95rem;">${item.employee_name}</div>
            <div style="font-size:0.75rem; color:var(--slate-500);">${item.created_at}</div>
          </div>
          <div>${statusBadge}</div>
        </div>

        <div style="font-size:0.85rem; margin-bottom:0.4rem;">
          <span style="font-weight:600; color:var(--primary);">${item.day_of_week} • ${item.shift_type}</span>
          <span style="color:var(--slate-600); margin-left:0.35rem;">(${item.reason})</span>
        </div>

        <div style="font-size:0.8rem; background:var(--slate-50); padding:0.4rem 0.6rem; border-radius:4px; font-style:italic; color:var(--slate-700); margin-bottom:0.6rem; border:1px solid var(--slate-200);">
          "${item.raw_text}"
        </div>

        ${item.status === "PENDING" ? `
          <div style="display:flex; gap:0.5rem; justify-content:flex-end;">
            <button class="btn btn-danger btn-sm" onclick="app.updateLeaveStatus('${item.id}', 'REJECTED')">
              Reject
            </button>
            <button class="btn btn-success btn-sm" onclick="app.updateLeaveStatus('${item.id}', 'APPROVED')">
              Approve
            </button>
          </div>
        ` : ''}
      `;
      list.appendChild(card);
    });
  },

  // ==========================================
  // SCREEN 3: WEEKLY ROSTER & SOLVER
  // ==========================================
  async loadRoster() {
    try {
      const res = await fetch(`${API_BASE}/api/roster`);
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      const rosterData = data.data;
      if (rosterData.status === "SUCCESS") {
        this.state.currentRoster = rosterData.slots;
        this.state.rosterStats = rosterData.stats;
        this.renderRosterSuccess(rosterData);
      } else if (rosterData.status === "INFEASIBLE") {
        this.renderRosterConflict(rosterData);
      } else {
        // Not generated yet
        document.getElementById("roster-empty").style.display = "block";
        document.getElementById("roster-calendar-wrapper").style.display = "none";
        document.getElementById("roster-success-banner").style.display = "none";
        document.getElementById("roster-conflict-banner").style.display = "none";
      }
    } catch (err) {
      this.showToast(`Unable to load roster: ${err.message}`, "error");
    }
  },

  async generateRoster() {
    const btn = document.getElementById("btn-generate-roster");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> <span>Solving CSP Constraints...</span>`;

    try {
      const res = await fetch(`${API_BASE}/api/roster/generate`, { method: "POST" });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      const rosterData = data.data;
      if (rosterData.status === "SUCCESS") {
        this.state.currentRoster = rosterData.slots;
        this.state.rosterStats = rosterData.stats;
        this.renderRosterSuccess(rosterData);
        this.showToast("Roster generated with zero constraint violations!", "success");
        document.getElementById("badge-roster-status").textContent = "Solved";
      } else {
        this.state.currentRoster = [];
        this.renderRosterConflict(rosterData);
        this.showToast("No feasible schedule found (conflict detected).", "error");
        document.getElementById("badge-roster-status").textContent = "Conflict";
      }

      this.populateAbsenceSlotPicker();
    } catch (err) {
      this.showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>✨ Generate Weekly Roster</span>`;
    }
  },

  async triggerImpossibleScenario() {
    const btn = document.getElementById("btn-trigger-impossible");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> <span>Injecting Conflict...</span>`;

    try {
      const res = await fetch(`${API_BASE}/api/roster/load-impossible`, { method: "POST" });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      this.showToast("Injected impossible scenario (All Supervisors on leave Friday morning)", "info");
      await this.loadLeaves();
      this.renderRosterConflict(data.data);
      document.getElementById("badge-roster-status").textContent = "Conflict";
    } catch (err) {
      this.showToast(err.message, "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>⚠️ Trigger Impossible Scenario</span>`;
    }
  },

  renderRosterSuccess(rosterData) {
    document.getElementById("roster-empty").style.display = "none";
    document.getElementById("roster-conflict-banner").style.display = "none";
    document.getElementById("roster-success-banner").style.display = "flex";
    document.getElementById("roster-calendar-wrapper").style.display = "block";

    // Staff breakdown meter
    const breakdown = document.getElementById("roster-hours-breakdown");
    breakdown.innerHTML = "";
    if (rosterData.stats && rosterData.stats.employee_hours) {
      Object.entries(rosterData.stats.employee_hours).forEach(([eid, stat]) => {
        const pill = document.createElement("div");
        pill.className = "badge";
        const isNearCap = stat.hours_worked >= stat.max_hours;
        pill.style.background = isNearCap ? "#fef3c7" : "#e0e7ff";
        pill.style.color = isNearCap ? "#b45309" : "#3730a3";
        pill.innerHTML = `<strong>${stat.name}:</strong> ${stat.hours_worked}/${stat.max_hours}h (${stat.utilization_pct}%)`;
        breakdown.appendChild(pill);
      });
    }

    // Clear calendar grid cells
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
    const shifts = ["Morning", "Evening"];
    days.forEach(d => {
      shifts.forEach(s => {
        const cell = document.getElementById(`cell-${d}-${s}`);
        if (cell) cell.innerHTML = "";
      });
    });

    // Populate slots into calendar grid
    rosterData.slots.forEach(slot => {
      const cell = document.getElementById(`cell-${slot.day_of_week}-${slot.shift_type}`);
      if (!cell) return;

      const slotEl = document.createElement("div");
      slotEl.className = `slot-card ${slot.is_absent ? (slot.replaced_by_id ? 'replaced' : 'absent') : ''}`;

      const roleBadge = `<span class="badge badge-${slot.role.toLowerCase()}">${slot.role}</span>`;

      let statusDisplay = "";
      if (slot.is_absent) {
        if (slot.replaced_by_id) {
          statusDisplay = `
            <div>
              <div style="font-size:0.75rem; text-decoration:line-through; color:var(--slate-500);">${slot.assigned_employee_name}</div>
              <div class="slot-replacement-badge">✓ Replaced by ${slot.replaced_by_name}</div>
            </div>
          `;
        } else {
          statusDisplay = `
            <div>
              <div style="font-size:0.75rem; text-decoration:line-through; color:#b91c1c;">${slot.assigned_employee_name}</div>
              <div class="slot-absent-badge">🚨 Absent (${slot.absent_reason || 'Call-out'})</div>
            </div>
          `;
        }
      } else {
        statusDisplay = `<span class="slot-emp-name">${slot.assigned_employee_name}</span>`;
      }

      slotEl.innerHTML = `
        <div class="slot-header">
          ${roleBadge}
          <span style="font-size:0.7rem; color:var(--slate-500);">${slot.hours}h</span>
        </div>
        <div style="margin-bottom:0.4rem;">
          ${statusDisplay}
        </div>
        <button class="btn btn-outline-danger btn-sm" style="width:100%; padding:0.2rem 0.4rem; font-size:0.72rem;" onclick="app.quickMarkAbsent('${slot.id}')">
          ${slot.is_absent ? 'Manage Coverage' : 'Mark Absent'}
        </button>
      `;
      cell.appendChild(slotEl);
    });

    this.populateAbsenceSlotPicker();
  },

  renderRosterConflict(rosterData) {
    document.getElementById("roster-empty").style.display = "none";
    document.getElementById("roster-success-banner").style.display = "none";
    document.getElementById("roster-conflict-banner").style.display = "flex";
    document.getElementById("roster-calendar-wrapper").style.display = "none";

    const container = document.getElementById("conflict-details-container");
    container.innerHTML = "";

    const conflicts = rosterData.conflicts || [];
    if (conflicts.length > 0) {
      document.getElementById("conflict-main-title").textContent = conflicts[0].title || "No Feasible Schedule Found";
      document.getElementById("conflict-main-desc").textContent = conflicts[0].description || "Hard constraint violations prevent schedule generation.";

      conflicts.forEach(c => {
        const item = document.createElement("div");
        item.style.marginBottom = "0.6rem";
        item.style.paddingBottom = "0.6rem";
        item.style.borderBottom = "1px solid #fee2e2";

        const factorList = (c.factors || []).map(f => `<li>${f}</li>`).join("");

        item.innerHTML = `
          <div style="font-weight:700; color:#991b1b; margin-bottom:0.2rem;">${c.title}</div>
          <div style="margin-bottom:0.35rem;">${c.description}</div>
          ${factorList ? `<ul style="padding-left:1.25rem; margin-bottom:0.35rem; color:var(--slate-700);">${factorList}</ul>` : ''}
          <div style="color:#065f46; background:#ecfdf5; padding:0.35rem 0.55rem; border-radius:4px; font-weight:600;">
            💡 Recommended Action: ${c.action || 'Adjust requirements or staff hours.'}
          </div>
        `;
        container.appendChild(item);
      });
    } else {
      container.innerHTML = `<div>No valid schedule found satisfying all 5 hard constraints.</div>`;
    }
  },

  // ==========================================
  // SCREEN 4: ABSENCE & RANKED REPLACEMENTS
  // ==========================================
  populateAbsenceSlotPicker() {
    const select = document.getElementById("absence-slot-picker");
    if (!select) return;
    select.innerHTML = "";

    if (!this.state.currentRoster || this.state.currentRoster.length === 0) {
      select.innerHTML = `<option value="">(Generate a roster first in Screen 3)</option>`;
      return;
    }

    this.state.currentRoster.forEach(slot => {
      const opt = document.createElement("option");
      opt.value = slot.id;
      const status = slot.is_absent ? (slot.replaced_by_id ? `[Replaced by ${slot.replaced_by_name}]` : `[ABSENT]`) : '';
      opt.textContent = `${slot.day_of_week} ${slot.shift_type} — ${slot.role} (${slot.assigned_employee_name}) ${status}`;
      select.appendChild(opt);
    });
  },

  quickMarkAbsent(slotId) {
    // Jump straight from Calendar to Screen 4 with this slot pre-selected
    this.switchTab("tab-replacement");
    const select = document.getElementById("absence-slot-picker");
    if (select) {
      select.value = slotId;
    }
    this.handleMarkAbsent();
  },

  async handleMarkAbsent() {
    const slotId = document.getElementById("absence-slot-picker").value;
    const reason = document.getElementById("absence-reason").value.trim() || "Unplanned Absence";

    if (!slotId) {
      this.showToast("Please select a shift slot to mark absent.", "error");
      return;
    }

    const loading = document.getElementById("replacement-loading");
    const empty = document.getElementById("replacement-empty");
    loading.style.display = "block";
    empty.style.display = "none";

    try {
      // 1. Mark absent on server
      const markRes = await fetch(`${API_BASE}/api/roster/mark-absent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({ slot_id: slotId, reason })
      });
      const markData = await markRes.json();
      if (!markData.success) throw new Error(markData.error);

      const slot = markData.data;
      this.state.selectedSlotForAbsence = slot;

      // Update Vacancy details card
      document.getElementById("active-vacancy-card").style.display = "block";
      document.getElementById("vacant-day-shift").textContent = `${slot.day_of_week} ${slot.shift_type}`;
      document.getElementById("vacant-role").textContent = slot.role;
      document.getElementById("vacant-role").className = `badge badge-${slot.role.toLowerCase()}`;
      document.getElementById("vacant-original-staff").textContent = slot.assigned_employee_name;
      document.getElementById("vacant-reason").textContent = reason;

      // 2. Fetch ranked replacements
      const replRes = await fetch(`${API_BASE}/api/roster/replacements?slot_id=${slotId}`);
      const replData = await replRes.json();
      if (!replData.success) throw new Error(replData.error);

      this.renderReplacements(replData.data);
      this.showToast(`Marked absent. Evaluated ${replData.data.eligible_count} eligible replacements.`, "info");
      document.getElementById("badge-absence-count").textContent = "1";
    } catch (err) {
      this.showToast(err.message, "error");
    } finally {
      loading.style.display = "none";
    }
  },

  renderReplacements(data) {
    const list = document.getElementById("replacement-list");
    const empty = document.getElementById("replacement-empty");
    const ineligibleCard = document.getElementById("ineligible-card");
    const ineligibleList = document.getElementById("ineligible-list");

    document.getElementById("eligible-count").textContent = data.eligible_count;
    document.getElementById("ineligible-count").textContent = data.ineligible_count;

    list.innerHTML = "";

    if (data.eligible_count === 0) {
      list.innerHTML = `
        <div class="alert alert-warning" style="margin-top:0.75rem;">
          <div>⚠️ No staff meet all 5 hard constraints to cover this shift.</div>
        </div>
      `;
    } else {
      data.eligible.forEach(cand => {
        const card = document.createElement("div");
        card.className = `candidate-card ${cand.rank === 1 ? 'top-pick' : ''}`;

        const skillsBadges = cand.skills.map(s => {
          return `<span class="badge badge-${s.toLowerCase()}">${s}</span>`;
        }).join(" ");

        card.innerHTML = `
          <div style="flex:1;">
            <div class="candidate-rank">
              <div class="rank-number">#${cand.rank}</div>
              <div>
                <div style="font-weight:700; color:var(--slate-900); font-size:0.95rem;">
                  ${cand.name}
                  ${cand.rank === 1 ? '<span class="badge badge-approved" style="margin-left:0.4rem;">Top Recommendation</span>' : ''}
                </div>
                <div style="font-size:0.75rem; color:var(--slate-500); margin-top:0.15rem;">
                  ${skillsBadges}
                </div>
              </div>
            </div>

            <div style="margin-top:0.55rem; font-size:0.8rem; color:var(--slate-700);">
              ${cand.ranking_explanation}
            </div>

            <div style="font-size:0.75rem; color:var(--slate-500); margin-top:0.25rem;">
              Weekly Load: <strong>${cand.current_hours}h</strong> ➔ <strong>${cand.new_total_hours}h / ${cand.max_hours}h</strong>
            </div>
          </div>

          <div style="text-align:right; margin-left:1rem;">
            <div class="candidate-score">Score: ${cand.score}</div>
            <button class="btn btn-success btn-sm" style="margin-top:0.5rem;" onclick="app.assignReplacement('${cand.employee_id}')">
              Assign Cover
            </button>
          </div>
        `;
        list.appendChild(card);
      });
    }

    // Ineligible list
    if (data.ineligible_count > 0) {
      ineligibleCard.style.display = "block";
      ineligibleList.innerHTML = "";
      data.ineligible.forEach(inEl => {
        const row = document.createElement("div");
        row.style.marginBottom = "0.35rem";
        row.innerHTML = `<strong>${inEl.name}:</strong> <span style="color:#b91c1c;">${inEl.reason}</span>`;
        ineligibleList.appendChild(row);
      });
    } else {
      ineligibleCard.style.display = "none";
    }
  },

  async assignReplacement(empId) {
    if (!this.state.selectedSlotForAbsence) return;
    const slotId = this.state.selectedSlotForAbsence.id;

    try {
      const res = await fetch(`${API_BASE}/api/roster/assign-replacement`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonBody({
          slot_id: slotId,
          replacement_emp_id: empId
        })
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error);

      this.showToast(`Cover assigned successfully to ${data.data.replaced_by_name}!`, "success");
      await this.loadRoster();
      // Re-trigger absence view to show replacement confirmation
      await this.handleMarkAbsent();
      document.getElementById("badge-absence-count").textContent = "0";
    } catch (err) {
      this.showToast(err.message, "error");
    }
  }
};

function jsonBody(obj) {
  return JSON.stringify(obj);
}

// Start application when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  app.init();
});
