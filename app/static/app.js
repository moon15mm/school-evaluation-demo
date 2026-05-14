const form = document.querySelector("#analysisForm");
const evidenceForm = document.querySelector("#evidenceForm");
const evidenceResult = document.querySelector("#evidenceResult");
const impactForm = document.querySelector("#impactForm");
const impactResult = document.querySelector("#impactResult");
const dashboard = document.querySelector("#dashboard");
const template = document.querySelector("#dashboardTemplate");
const healthStatus = document.querySelector("#healthStatus");
const memorySummary = document.querySelector("#memorySummary");
const loginForm = document.querySelector("#loginForm");
const loginMessage = document.querySelector("#loginMessage");
const logoutBtn = document.querySelector("#logoutBtn");
const userPill = document.querySelector("#userPill");
let latestEvidenceReviews = [];
let latestEvidenceLibrary = { folders: [], total_reviews: 0 };
let latestImpactRecords = [];
let latestImpactAdvice = null;
let latestCouncilEvents = [];
let currentUser = null;

fetch("/api/health")
  .then((response) => response.json())
  .then(() => {
    healthStatus.textContent = "جاهز محليًا";
  })
  .catch(() => {
    healthStatus.textContent = "غير متصل";
  });

document.body.classList.add("locked");
initializeAuth();

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = loginForm.querySelector("button");
    button.disabled = true;
    if (loginMessage) loginMessage.textContent = "";
    try {
      const payload = Object.fromEntries(new FormData(loginForm).entries());
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "تعذر تسجيل الدخول");
      }
      const data = await response.json();
      setCurrentUser(data.user);
      loginForm.reset();
      await startAuthenticatedApp();
    } catch (error) {
      if (loginMessage) loginMessage.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
}

if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    currentUser = null;
    setCurrentUser(null);
    document.body.classList.add("locked");
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = form.querySelector("button");
  button.disabled = true;
  button.textContent = "جاري عقد جلسة الوكلاء...";

  try {
    const payload = new FormData(form);
    const response = await fetch("/api/analyze", {
      method: "POST",
      body: payload,
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "تعذر تشغيل النظام");
    }
    const data = await response.json();
    renderDashboard(data.visit, data.report_url);
    loadMemorySummary();
  } catch (error) {
    dashboard.innerHTML = `<div class="empty-state"><h2>تعذر تشغيل النظام</h2><p>${escapeHtml(error.message)}</p></div>`;
  } finally {
    button.disabled = false;
    button.textContent = "تشغيل النظام كاملًا";
  }
});

if (evidenceForm) {
  evidenceForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = evidenceForm.querySelector("button");
    button.disabled = true;
    showEvidenceResult("working", "جاري فحص الشاهد وترتيبه في ملف الزيارة...");
    button.textContent = "جاري فحص الشاهد...";

    try {
      const payload = new FormData(evidenceForm);
      const response = await fetch("/api/evidence/review", {
        method: "POST",
        body: payload,
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "تعذر فحص الشاهد");
      }
      const data = await response.json();
      latestEvidenceReviews = asArray(data.recent);
      latestEvidenceLibrary = data.library || latestEvidenceLibrary;
      latestCouncilEvents = asArray(data.council_events || latestCouncilEvents);
      showEvidenceResult("success", evidenceSummary(data.review));
      const desk = dashboard.querySelector('[data-field="evidenceDesk"]');
      const library = dashboard.querySelector('[data-field="evidenceLibrary"]');
      fillLiveCouncil(dashboard.querySelector('[data-field="liveCouncil"]'), latestCouncilEvents);
      if (library) {
        fillEvidenceLibrary(library, latestEvidenceLibrary);
      }
      activateDashboardTab("evidence");
      if (desk) {
        fillEvidenceDesk(desk, latestEvidenceReviews);
        desk.scrollIntoView({ behavior: "smooth", block: "start" });
      } else {
        await loadWorkspace();
        const loadedDesk = dashboard.querySelector('[data-field="evidenceDesk"]');
        if (loadedDesk) {
          fillEvidenceDesk(loadedDesk, latestEvidenceReviews);
        }
      }
      evidenceForm.reset();
    } catch (error) {
      showEvidenceResult("error", error.message);
      const desk = dashboard.querySelector('[data-field="evidenceDesk"]');
      if (desk) {
        desk.innerHTML = `<article class="item"><p>${escapeHtml(error.message)}</p></article>`;
      } else {
        dashboard.innerHTML = `<div class="empty-state"><h2>تعذر تشغيل سكرتارية الشواهد</h2><p>${escapeHtml(error.message)}</p></div>`;
      }
    } finally {
      button.disabled = false;
      button.textContent = "فحص الشاهد وترتيبه";
    }
  });
}

if (impactForm) {
  impactForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = impactForm.querySelector("button");
    button.disabled = true;
    showImpactResult("working", "جاري بناء قصة الأثر وحفظ مرفقاتها...");
    button.textContent = "جاري حفظ الأثر...";
    try {
      const payload = new FormData(impactForm);
      const response = await fetch("/api/impact/records", { method: "POST", body: payload });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "تعذر حفظ قصة الأثر");
      }
      const data = await response.json();
      latestImpactRecords = asArray(data.records);
      latestCouncilEvents = asArray(data.council_events || latestCouncilEvents);
      fillImpactBoard(dashboard.querySelector('[data-field="impactBoard"]'), latestImpactRecords);
      fillLiveCouncil(dashboard.querySelector('[data-field="liveCouncil"]'), latestCouncilEvents);
      activateDashboardTab("impact");
      showImpactResult("success", impactSummary(data.record));
      impactForm.reset();
    } catch (error) {
      showImpactResult("error", error.message);
    } finally {
      button.disabled = false;
      button.textContent = "حفظ قصة الأثر";
    }
  });
}

async function initializeAuth() {
  try {
    const response = await fetch("/api/auth/me");
    const data = await response.json();
    if (data.authenticated && data.user) {
      setCurrentUser(data.user);
      await startAuthenticatedApp();
    } else {
      setCurrentUser(null);
      document.body.classList.add("locked");
    }
  } catch {
    setCurrentUser(null);
    document.body.classList.add("locked");
  }
}

async function startAuthenticatedApp() {
  document.body.classList.remove("locked");
  await loadMemorySummary();
  await loadWorkspace();
}

function setCurrentUser(user) {
  currentUser = user;
  document.body.classList.toggle("can-manage-users", Boolean(user?.can_manage_users));
  if (userPill) {
    userPill.style.display = user ? "block" : "none";
    userPill.textContent = user ? `${user.display_name} | ${user.role}` : "";
  }
}

function showEvidenceResult(type, message) {
  if (!evidenceResult) return;
  evidenceResult.className = `evidence-result ${type}`;
  evidenceResult.innerHTML = `<strong>${evidenceResultTitle(type)}</strong><p>${escapeHtml(message)}</p>`;
}

function evidenceResultTitle(type) {
  return {
    working: "سكرتارية الشواهد تعمل الآن",
    success: "تم فحص الشاهد",
    error: "تعذر فحص الشاهد",
  }[type] || "سكرتارية الشواهد";
}

function evidenceSummary(review) {
  if (!review) return "تم حفظ نتيجة الشاهد في الذاكرة.";
  const status = suitabilityLabel(review.suitability);
  const indicator = review.suggested_indicator_code || "غير محدد";
  const domain = review.suggested_domain || "غير محدد";
  const confidence = Math.round(Number(review.confidence || 0) * 100);
  return `${status} | المجال: ${domain} | المؤشر: ${indicator} | الثقة: ${confidence}%`;
}

function showImpactResult(type, message) {
  if (!impactResult) return;
  impactResult.className = `evidence-result ${type}`;
  impactResult.innerHTML = `<strong>${impactResultTitle(type)}</strong><p>${escapeHtml(message)}</p>`;
}

function impactResultTitle(type) {
  return {
    working: "وكيل ملف الأثر يعمل الآن",
    success: "تم حفظ قصة الأثر",
    error: "تعذر حفظ الأثر",
  }[type] || "ملف الأثر";
}

function impactSummary(record) {
  if (!record) return "تم حفظ قصة الأثر في الذاكرة.";
  return `${impactLevelLabel(record.impact_level)} | ${record.domain} | تحسن ${Number(record.improvement_rate || 0).toFixed(1)}%`;
}

async function loadMemorySummary() {
  if (!memorySummary) return;
  try {
    const response = await fetch("/api/memory");
    const data = await response.json();
    const visits = data.visits.length;
    const success = data.learning_profile.average_plan_success;
    memorySummary.textContent = `الزيارات المخزنة: ${visits} | نجاح الخطط: ${Math.round(success * 100)}%`;
  } catch {
    memorySummary.textContent = "الذاكرة غير متاحة الآن";
  }
}

async function loadWorkspace() {
  try {
    const response = await fetch("/api/workspace");
    const data = await response.json();
    latestEvidenceReviews = asArray(data.evidence_reviews);
    latestEvidenceLibrary = data.evidence_library || latestEvidenceLibrary;
    latestImpactRecords = asArray(data.impact_records);
    latestImpactAdvice = data.impact_advice || latestImpactAdvice;
    latestCouncilEvents = asArray(data.council_events);
    const schoolInput = form?.querySelector('[name="school_name"]');
    const rememberedSchool = data.active_visit?.report_profile?.school_name || data.active_visit?.school_name || "";
    if (schoolInput && !schoolInput.value.trim() && rememberedSchool && rememberedSchool !== "Autonomous School Evaluation & Improvement System") {
      schoolInput.value = rememberedSchool;
    }
    if (data.has_memory && data.active_visit) {
      renderDashboard(data.active_visit, data.dashboard?.report_url || `/api/reports/${data.active_visit.id}`, data.dashboard, latestEvidenceReviews, latestEvidenceLibrary, latestImpactRecords);
    }
  } catch {
    // Keep the start screen if memory is not available.
  }
}

function renderDashboard(visit, reportUrl, dashboardStats = null, evidenceReviews = latestEvidenceReviews, evidenceLibrary = latestEvidenceLibrary, impactRecords = latestImpactRecords) {
  const view = template.content.cloneNode(true);
  const prediction = visit.prediction || {};
  const domains = asArray(visit.domains);
  view.querySelector('[data-field="expected"]').textContent = `${prediction.expected_score ?? 0}/100`;
  view.querySelector('[data-field="confidence"]').textContent = `${Math.round((prediction.confidence ?? 0) * 100)}%`;
  const avgGap = average(domains.map((domain) => domain.gap ?? 0));
  view.querySelector('[data-field="improvement"]').textContent = `${avgGap >= 0 ? "+" : ""}${avgGap.toFixed(1)}`;

  fillProgressBoard(view.querySelector('[data-field="progressBoard"]'), visit, dashboardStats);
  fillExternalReadiness(view.querySelector('[data-field="externalReadiness"]'), visit.external_readiness);
  fillEvidenceLibrary(view.querySelector('[data-field="evidenceLibrary"]'), evidenceLibrary);
  fillEvidenceDesk(view.querySelector('[data-field="evidenceDesk"]'), evidenceReviews);
  fillImpactAgent(view.querySelector('[data-field="impactAgent"]'), latestImpactAdvice);
  fillImpactBoard(view.querySelector('[data-field="impactBoard"]'), impactRecords);
  fillReportProfile(view.querySelector('[data-field="reportProfile"]'), visit.report_profile);
  fillDomains(view.querySelector('[data-field="domains"]'), domains);
  fillWeaknesses(view.querySelector('[data-field="weaknesses"]'), visit.weaknesses);
  fillScenarios(view.querySelector('[data-field="scenarios"]'), prediction.scenarios);
  fillPlan(view.querySelector('[data-field="plan"]'), visit.plan);
  fillLiveCouncil(view.querySelector('[data-field="liveCouncil"]'), latestCouncilEvents);
  fillCouncil(view.querySelector('[data-field="council"]'), visit.council_session);
  fillProtocol(view.querySelector('[data-field="protocol"]'), visit.excellence_protocol);
  fillForms(view.querySelector('[data-field="forms"]'), visit.operational_forms);
  fillExecution(view.querySelector('[data-field="execution"]'), visit.execution_pack);
  fillTasks(view.querySelector('[data-field="tasks"]'), visit.tasks);
  fillSimulation(view.querySelector('[data-field="simulation"]'), visit.simulation);
  fillLearning(view.querySelector('[data-field="learning"]'), prediction.learning_notes, prediction.fastest_actions);

  view.querySelector('[data-field="report"]').href = reportUrl;
  const executionLink = view.querySelector('[data-field="executionDownload"]');
  executionLink.href = visit.execution_pack?.download_url || "#";
  if (!visit.execution_pack?.download_url) {
    executionLink.style.display = "none";
  }
  const dossierLink = view.querySelector('[data-field="evidenceDossier"]');
  dossierLink.style.display = "none";
  const impactLink = view.querySelector('[data-field="impactPackage"]');
  impactLink.style.display = "none";
  dashboard.innerHTML = "";
  dashboard.dataset.visitId = visit.id;
  dashboard.appendChild(view);
  setupDashboardTabs("overview");
  const buildDossierBtn = dashboard.querySelector("#buildDossierBtn");
  if (buildDossierBtn) {
    buildDossierBtn.addEventListener("click", buildEvidenceDossier);
  }
  const buildImpactBtn = dashboard.querySelector("#buildImpactBtn");
  if (buildImpactBtn) {
    buildImpactBtn.addEventListener("click", buildImpactPackage);
  }
  const impactAgentBtn = dashboard.querySelector("#impactAgentBtn");
  if (impactAgentBtn) {
    impactAgentBtn.addEventListener("click", loadImpactAgentAdvice);
  }
  setupAdminControls();
}

function setupDashboardTabs(initialTab = "overview") {
  const tabs = dashboard.querySelectorAll("[data-dashboard-tab]");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => activateDashboardTab(tab.dataset.dashboardTab));
  });
  activateDashboardTab(initialTab);
}

function setupAdminControls() {
  const clearBtn = dashboard.querySelector("#clearDataBtn");
  if (clearBtn) {
    clearBtn.addEventListener("click", clearAllData);
  }
  const userForm = dashboard.querySelector("#userForm");
  if (userForm) {
    userForm.addEventListener("submit", createUser);
  }
  if (currentUser?.can_manage_users) {
    loadUsers();
  }
}

async function loadUsers() {
  const panel = dashboard.querySelector('[data-field="usersPanel"]');
  if (!panel) return;
  try {
    const response = await fetch("/api/auth/users");
    if (!response.ok) throw new Error("تعذر تحميل المستخدمين");
    const data = await response.json();
    fillUsersPanel(panel, data.users);
  } catch (error) {
    panel.innerHTML = `<article class="item"><p>${escapeHtml(error.message)}</p></article>`;
  }
}

function fillUsersPanel(panel, users) {
  panel.className = "users-list";
  panel.innerHTML = asArray(users)
    .map(
      (user) => `
        <article class="user-card">
          <div>
            <strong>${escapeHtml(user.display_name)}</strong>
            <small>${escapeHtml(user.username)} | ${escapeHtml(user.role)} | ${user.can_write ? "تعديل" : "عرض فقط"}${user.can_manage_users ? " | إدارة مستخدمين" : ""}${user.can_clear_data ? " | تفريغ بيانات" : ""}</small>
          </div>
          <button type="button" class="danger-btn" data-delete-user="${escapeHtml(user.username)}">حذف</button>
        </article>
      `,
    )
    .join("");
  panel.querySelectorAll("[data-delete-user]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!window.confirm("هل تريد حذف هذا المستخدم؟")) return;
      const response = await fetch(`/api/auth/users/${encodeURIComponent(button.dataset.deleteUser)}`, { method: "DELETE" });
      if (!response.ok) {
        const error = await response.json();
        window.alert(error.detail || "تعذر حذف المستخدم");
        return;
      }
      const data = await response.json();
      fillUsersPanel(panel, data.users);
    });
  });
}

async function createUser(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.can_write = Boolean(form.elements.can_write.checked);
  payload.can_manage_users = Boolean(form.elements.can_manage_users.checked);
  payload.can_clear_data = Boolean(form.elements.can_clear_data.checked);
  payload.role = payload.can_manage_users ? "admin" : payload.can_write ? "user" : "viewer";
  const response = await fetch("/api/auth/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json();
    window.alert(error.detail || "تعذر إضافة المستخدم");
    return;
  }
  const data = await response.json();
  form.reset();
  form.elements.can_write.checked = true;
  fillUsersPanel(dashboard.querySelector('[data-field="usersPanel"]'), data.users);
}

async function clearAllData() {
  if (!window.confirm("سيتم تفريغ الزيارات والشواهد وملف الأثر والتقارير مع الإبقاء على المستخدمين. هل أنت متأكد؟")) return;
  const response = await fetch("/api/admin/clear-data", { method: "POST" });
  if (!response.ok) {
    const error = await response.json();
    window.alert(error.detail || "تعذر تفريغ البيانات");
    return;
  }
  latestEvidenceReviews = [];
  latestEvidenceLibrary = { folders: [], total_reviews: 0 };
  latestImpactRecords = [];
  latestImpactAdvice = null;
  latestCouncilEvents = [];
  dashboard.innerHTML = `<div class="empty-state"><h2>تم تفريغ البيانات</h2><p>يمكنك بدء تحليل جديد أو استخدام التقرير الافتراضي.</p></div>`;
  await loadMemorySummary();
}

function activateDashboardTab(target) {
  const tabs = dashboard.querySelectorAll("[data-dashboard-tab]");
  const pages = dashboard.querySelectorAll("[data-dashboard-page]");
  tabs.forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.dashboardTab === target);
  });
  pages.forEach((page) => {
    page.classList.toggle("active-page", page.dataset.dashboardPage === target);
  });
}

function fillProgressBoard(container, visit, stats) {
  const tasks = asArray(visit.tasks);
  const today = new Date().toISOString().slice(0, 10);
  const done = tasks.filter((task) => task.status === "done").length;
  const inProgress = tasks.filter((task) => task.status === "in_progress").length;
  const fresh = tasks.filter((task) => task.status === "new").length;
  const overdue = tasks.filter((task) => task.status !== "done" && task.due_date < today);
  const total = tasks.length;
  const completion = stats?.completion ?? (total ? Math.round((done / total) * 1000) / 10 : 0);
  const expected = visit.prediction?.expected_score ?? stats?.expected_score ?? 0;
  const domains = asArray(visit.domains);
  const scenarios = asArray(visit.prediction?.scenarios);
  const overduePercent = total ? Math.round((overdue.length / total) * 1000) / 10 : 0;
  const statusSegments = [
    { label: "منجزة", value: done, className: "done" },
    { label: "قيد التنفيذ", value: inProgress, className: "progressing" },
    { label: "لم تبدأ", value: fresh, className: "fresh" },
    { label: "متأخرة", value: overdue.length, className: "late" },
  ];
  const stacked = statusSegments
    .map((segment) => {
      const width = total ? Math.max(0, (segment.value / total) * 100) : 0;
      return `<span class="${segment.className}" style="width:${width}%"></span>`;
    })
    .join("");
  const domainChart = domains
    .map((domain) => {
      const current = Number(domain.current_score ?? 0);
      const previous = Number(domain.previous_score ?? 0);
      return `
        <div class="chart-row">
          <strong>${escapeHtml(domain.label)}</strong>
          <div class="dual-bars">
            <span class="previous" style="width:${previous}%"></span>
            <span class="current" style="width:${current}%"></span>
          </div>
          <em>${formatScore(current)}</em>
        </div>
      `;
    })
    .join("");
  const scenarioChart = scenarios
    .map(
      (scenario) => `
        <div class="scenario-bar">
          <span>${escapeHtml(scenario.name)}</span>
          <div><i style="width:${Number(scenario.score ?? 0)}%"></i></div>
          <strong>${formatScore(scenario.score)}</strong>
        </div>
      `,
    )
    .join("");
  const timeline = tasks
    .slice()
    .sort((a, b) => String(a.due_date).localeCompare(String(b.due_date)))
    .slice(0, 7)
    .map((task) => {
      const state = task.status === "done" ? "done" : task.due_date < today ? "late" : task.status === "in_progress" ? "progressing" : "fresh";
      return `
        <li class="${state}">
          <strong>${escapeHtml(task.assignee)}</strong>
          <span>${escapeHtml(task.due_date)} | ${taskStatusLabel(task.status)}</span>
        </li>
      `;
    })
    .join("");
  container.className = "progress-board";
  container.innerHTML = `
    <article class="progress-hero live-card">
      <div class="donut" style="--value:${completion}">
        <strong>${completion}%</strong>
      </div>
      <div>
        <span>جاهزية التنفيذ</span>
        <p>تتحدث مباشرة عند تغيير حالة المهام.</p>
      </div>
    </article>
    <article class="progress-card live-card">
      <span>الدرجة المتوقعة</span>
      <strong>${expected}/100</strong>
    </article>
    <article class="progress-card live-card">
      <span>مؤشر التأخر</span>
      <strong>${overduePercent}%</strong>
    </article>
    <article class="chart-panel status-panel">
      <div class="chart-title">
        <h3>حالة المهام</h3>
        <span>${done}/${total} منجزة</span>
      </div>
      <div class="stacked-bar">${stacked}</div>
      <div class="legend">
        ${statusSegments.map((segment) => `<span><i class="${segment.className}"></i>${segment.label}: ${segment.value}</span>`).join("")}
      </div>
    </article>
    <article class="chart-panel">
      <div class="chart-title">
        <h3>تقدم المجالات</h3>
        <span>السابق مقابل الحالي</span>
      </div>
      <div class="domain-chart">${domainChart}</div>
    </article>
    <article class="chart-panel">
      <div class="chart-title">
        <h3>سيناريوهات الدرجة</h3>
        <span>0-100</span>
      </div>
      <div class="scenario-chart">${scenarioChart}</div>
    </article>
    <article class="chart-panel">
      <div class="chart-title">
        <h3>خط زمني قريب</h3>
        <span>أقرب 7 مهام</span>
      </div>
      <ul class="timeline-chart">${timeline}</ul>
    </article>
  `;
}

function fillExternalReadiness(container, readiness) {
  if (!container) return;
  if (!readiness) {
    container.innerHTML = `<article class="item"><p>أعد تشغيل التحليل لتوليد محاكاة فريق التقييم الخارجي.</p></article>`;
    return;
  }
  const dimensions = asArray(readiness.dimensions)
    .map(
      (item) => `
        <article class="external-dimension">
          <div>
            <strong>${escapeHtml(item.name)}</strong>
            <span>${formatScore(item.score)}%</span>
          </div>
          <div class="folder-readiness"><i style="width:${Number(item.score || 0)}%"></i></div>
          <p><b>سؤال الفريق:</b> ${escapeHtml(item.evaluator_question)}</p>
          <p><b>علامة الخطر:</b> ${escapeHtml(item.failure_signal)}</p>
          <p><b>علامة التميز:</b> ${escapeHtml(item.excellence_signal)}</p>
          <ul class="steps">${asArray(item.immediate_actions).map((action) => `<li>${escapeHtml(action)}</li>`).join("")}</ul>
        </article>
      `,
    )
    .join("");
  const phases = asArray(readiness.phases)
    .map(
      (phase) => `
        <article class="visit-phase">
          <strong>${escapeHtml(phase.phase)} <span>${Math.round(Number(phase.weight || 0) * 100)}%</span></strong>
          <p>${escapeHtml(phase.objective)}</p>
          <ul class="steps">${asArray(phase.checklist).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </article>
      `,
    )
    .join("");
  const probes = asArray(readiness.probes)
    .map(
      (probe) => `
        <article class="probe-card">
          <span>${escapeHtml(probe.target)}</span>
          <h3>${escapeHtml(probe.question)}</h3>
          <p><b>الإجابة القوية:</b> ${asArray(probe.what_good_answer_contains).map(escapeHtml).join("، ")}</p>
          <p><b>الشاهد:</b> ${asArray(probe.evidence_to_show).map(escapeHtml).join("، ")}</p>
        </article>
      `,
    )
    .join("");
  const schedule = asArray(readiness.visit_schedule)
    .map(
      (item) => `
        <article class="visit-schedule-item">
          <strong>${escapeHtml(item.time_window)}</strong>
          <h3>${escapeHtml(item.activity)}</h3>
          <p><b>تركيز الفريق:</b> ${escapeHtml(item.evaluator_focus)}</p>
          <p><b>المسؤول:</b> ${escapeHtml(item.school_owner)}</p>
          <ul class="steps">${asArray(item.expected_outputs).map((output) => `<li>${escapeHtml(output)}</li>`).join("")}</ul>
        </article>
      `,
    )
    .join("");
  const classroom = asArray(readiness.classroom_observations)
    .map(
      (item) => `
        <article class="simulation-card classroom-card">
          <span>${escapeHtml(item.subject_or_context)}</span>
          <h3>ما الذي سيراقبه الفريق؟</h3>
          <ul class="steps">${asArray(item.evaluator_look_for).map((point) => `<li>${escapeHtml(point)}</li>`).join("")}</ul>
          <p><b>أسئلة محتملة:</b> ${asArray(item.likely_questions).map(escapeHtml).join("، ")}</p>
          <p><b>الاستجابة المتميزة:</b> ${escapeHtml(item.excellence_response)}</p>
          <div class="risk-strip">${asArray(item.red_flags).map((risk) => `<span>${escapeHtml(risk)}</span>`).join("")}</div>
          <div class="signal-strip">${asArray(item.evidence_to_prepare).map((evidence) => `<span>${escapeHtml(evidence)}</span>`).join("")}</div>
        </article>
      `,
    )
    .join("");
  const interviews = asArray(readiness.interview_drills)
    .map(
      (item) => `
        <article class="simulation-card interview-card">
          <span>${escapeHtml(item.audience)}</span>
          <h3>${escapeHtml(item.opening_question)}</h3>
          <p><b>أسئلة متابعة:</b> ${asArray(item.follow_up_questions).map(escapeHtml).join("، ")}</p>
          <p><b>صيغة الإجابة:</b> ${asArray(item.answer_formula).map(escapeHtml).join(" ← ")}</p>
          <div class="signal-strip">${asArray(item.evidence_to_hold).map((evidence) => `<span>${escapeHtml(evidence)}</span>`).join("")}</div>
          <div class="risk-strip">${asArray(item.avoid).map((risk) => `<span>${escapeHtml(risk)}</span>`).join("")}</div>
        </article>
      `,
    )
    .join("");
  const audit = asArray(readiness.document_audit)
    .map(
      (item) => `
        <article class="simulation-card audit-card">
          <span>${escapeHtml(item.file_name)}</span>
          <h3>${escapeHtml(item.evaluator_test)}</h3>
          <p><b>شرط النجاح:</b> ${escapeHtml(item.pass_condition)}</p>
          <p><b>نمط الفشل:</b> ${escapeHtml(item.failure_pattern)}</p>
          <div class="signal-strip">${asArray(item.required_artifacts).map((artifact) => `<span>${escapeHtml(artifact)}</span>`).join("")}</div>
        </article>
      `,
    )
    .join("");
  const triangulation = asArray(readiness.triangulation_checks)
    .map(
      (item) => `
        <article class="triangulation-card">
          <h3>${escapeHtml(item.claim)}</h3>
          <div><b>الملف</b><p>${escapeHtml(item.document_proof)}</p></div>
          <div><b>الميدان</b><p>${escapeHtml(item.field_proof)}</p></div>
          <div><b>النتيجة/الطالب</b><p>${escapeHtml(item.student_or_result_proof)}</p></div>
          <strong>${escapeHtml(item.verdict_rule)}</strong>
        </article>
      `,
    )
    .join("");
  container.className = "external-readiness";
  container.innerHTML = `
    <article class="external-hero ${escapeHtml(readiness.guarantee_level)}">
      <div class="donut" style="--value:${Number(readiness.overall_readiness || 0)}">
        <strong>${formatScore(readiness.overall_readiness)}%</strong>
      </div>
      <div>
        <span>${guaranteeLabel(readiness.guarantee_level)}</span>
        <p>${asArray(readiness.evaluator_mindset).map(escapeHtml).join(" ")}</p>
      </div>
    </article>
    <section class="external-grid">${dimensions}</section>
    <section class="phase-grid">${phases}</section>
    <div class="simulation-section-title"><h3>جدول محاكاة يوم الزيارة</h3><span>كيف يتحرك الفريق وماذا يريد أن يرى؟</span></div>
    <section class="visit-schedule-grid">${schedule}</section>
    <div class="simulation-section-title"><h3>محاكاة الجولات الصفية</h3><span>أخطر جزء في الزيارة لأنه يكشف الواقع.</span></div>
    <section class="deep-simulation-grid">${classroom}</section>
    <div class="simulation-section-title"><h3>تدريب المقابلات</h3><span>إجابات طبيعية مبنية على رقم وأثر.</span></div>
    <section class="deep-simulation-grid">${interviews}</section>
    <div class="simulation-section-title"><h3>تدقيق الوثائق والشواهد</h3><span>كيف يختبر الفريق صدق الملف؟</span></div>
    <section class="deep-simulation-grid">${audit}</section>
    <div class="simulation-section-title"><h3>التحقق الثلاثي</h3><span>كل ادعاء يجب أن يثبت في الملف والميدان والنتيجة.</span></div>
    <section class="triangulation-grid">${triangulation}</section>
    <section class="probe-grid">${probes}</section>
    <article class="item protocol-head">
      <h3>بروتوكول ضمان النجاح</h3>
      <ul class="steps">${asArray(readiness.guarantee_protocol).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </article>
    <article class="item">
      <h3>إيقاع أسبوعي يحمي المدرسة من التحضير الشكلي</h3>
      <ul class="steps">${asArray(readiness.weekly_battle_rhythm).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </article>
    <article class="item risk-box">
      <h3>أخطر نقاط السقوط المحتملة</h3>
      <ul class="steps">${asArray(readiness.top_failure_risks).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </article>
  `;
}

function fillReportProfile(container, profile) {
  container.className = "report-profile";
  if (!profile) {
    container.innerHTML = `<article class="item"><p>لم يتعرف النظام على قالب تقرير زيارة سابق محدد، وسيستخدم التحليل العام.</p></article>`;
    return;
  }
  const domainCards = asArray(profile.domains)
    .map(
      (domain) => `
        <article class="item">
          <h3>${escapeHtml(domain.name)}: ${domain.score}%</h3>
          <p>${escapeHtml(domain.level)} | ${escapeHtml(domain.interpretation)}</p>
        </article>
      `,
    )
    .join("");
  const priorities = asArray(profile.improvement_priorities)
    .slice(0, 8)
    .map(
      (item) => `
        <article class="item">
          <span class="tag ${item.priority === "critical" ? "urgent" : "high"}">${priorityText(item.priority)}</span>
          <h3>${escapeHtml(item.code)} - ${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.domain)} | الدرجة السابقة: ${item.score ?? "غير محددة"}%</p>
          <p>${escapeHtml(item.required_response)}</p>
        </article>
      `,
    )
    .join("");
  container.innerHTML = `
    <article class="item protocol-head">
      <h3>${escapeHtml(profile.school_name)} | ${escapeHtml(profile.report_year)}</h3>
      <p>الدرجة العامة السابقة: <strong>${profile.overall_score}%</strong> | المستوى: <strong>${escapeHtml(profile.overall_level)}</strong></p>
      <p>${escapeHtml(profile.strategic_reading)}</p>
    </article>
    <div class="profile-domains">${domainCards}</div>
    <div class="item-list">${priorities}</div>
  `;
}

function fillDomains(container, domains) {
  domains = asArray(domains);
  container.innerHTML = domains
    .map(
      (domain) => `
        <div class="domain-row">
          <strong>${escapeHtml(domain.label)}</strong>
          <div class="bar" title="${domain.current_score}/100"><span style="width:${domain.current_score}%"></span></div>
          <span class="domain-score">السابق ${formatScore(domain.previous_score)} | الحالي ${formatScore(domain.current_score)} | الفرق ${formatGap(domain.gap)}</span>
        </div>
      `,
    )
    .join("");
}

function fillWeaknesses(container, weaknesses) {
  container.className = "item-list";
  weaknesses = asArray(weaknesses);
  container.innerHTML = weaknesses
    .map(
      (item) => `
        <article class="item">
          <span class="tag ${item.severity}">${severityLabel(item.severity)}</span>
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.root_cause)}</p>
        </article>
      `,
    )
    .join("");
}

function fillScenarios(container, scenarios) {
  container.className = "item-list";
  scenarios = asArray(scenarios);
  container.innerHTML = scenarios
    .map(
      (item) => `
        <article class="item">
          <h3>${escapeHtml(item.name)}: ${item.score}/100</h3>
          <p>${escapeHtml(item.explanation)}</p>
        </article>
      `,
    )
    .join("");
}

function fillPlan(container, plan) {
  container.className = "item-list";
  plan = asArray(plan);
  container.innerHTML = plan
    .map(
      (item) => `
        <article class="item">
          <span class="tag ${item.priority}">${priorityLabel(item.priority)}</span>
          <h3>${escapeHtml(item.title)}</h3>
          <p><strong>${escapeHtml(item.owner_role)}</strong> | خلال ${item.due_in_days} يوم | أثر متوقع ${item.expected_gain}</p>
          <p>${escapeHtml(item.success_metric)}</p>
          <ol class="steps">${asArray(item.steps).map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>
        </article>
      `,
    )
    .join("");
}

function fillLiveCouncil(container, events) {
  if (!container) return;
  events = asArray(events);
  container.className = "live-council";
  if (!events.length) {
    container.innerHTML = `
      <article class="item">
        <h3>غرفة العمليات بانتظار أول حدث</h3>
        <p>عند رفع شاهد، حفظ قصة أثر، أو تغيير مهمة سيعقد الوكلاء مداخلة جديدة بتوصيات وتحذيرات.</p>
      </article>
    `;
    return;
  }
  const latest = events.slice().reverse().slice(0, 12);
  container.innerHTML = `
    <article class="live-council-head">
      <div>
        <span>حوار مستمر</span>
        <strong>${events.length} مداخلة وكالة</strong>
      </div>
      <p>كل حدث جديد يدخل النظام يتحول إلى قراءة جماعية: ماذا يعني؟ ما الخطر؟ ما الخطوة التالية؟</p>
    </article>
    <section class="live-council-feed">
      ${latest
        .map((event) => {
          const turns = asArray(event.agent_positions)
            .map(
              (turn) => `
                <div class="live-agent-turn">
                  <strong>${escapeHtml(agentLabel(turn.agent))}</strong>
                  <p>${escapeHtml(turn.position)}</p>
                  <small>${escapeHtml(turn.recommendation)}</small>
                </div>
              `,
            )
            .join("");
          return `
            <article class="live-council-event ${escapeHtml(event.severity)}">
              <div class="event-head">
                <span>${eventTypeLabel(event.event_type)}</span>
                <small>${escapeHtml(event.created_at || "")}</small>
              </div>
              <h3>${escapeHtml(event.title)}</h3>
              <p>${escapeHtml(event.summary)}</p>
              <div class="live-agent-grid">${turns}</div>
              ${renderEventList("التوصيات", event.recommendations, "recommend")}
              ${renderEventList("التحذيرات", event.warnings, "warn")}
              ${renderEventList("الخطوات التالية", event.next_actions, "next")}
            </article>
          `;
        })
        .join("")}
    </section>
  `;
}

function renderEventList(title, items, className) {
  items = asArray(items);
  if (!items.length) return "";
  return `
    <div class="event-list ${className}">
      <strong>${title}</strong>
      <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
  `;
}

function fillCouncil(container, council) {
  container.className = "council-layout";
  if (!council) {
    container.innerHTML = `<article class="item"><p>لم يتم إنشاء جلسة وكلاء لهذه الزيارة.</p></article>`;
    return;
  }
  const turns = asArray(council.turns)
    .map(
      (turn) => `
        <article class="dialogue-turn">
          <div>
            <span class="round">الجولة ${turn.round}</span>
            <strong>${escapeHtml(turn.agent)}</strong>
          </div>
          <h3>${escapeHtml(turn.position)}</h3>
          <p>${escapeHtml(turn.evidence)}</p>
          <p><strong>التوصية:</strong> ${escapeHtml(turn.recommendation)}</p>
        </article>
      `,
    )
    .join("");
  const decisions = asArray(council.decisions)
    .map(
      (decision) => `
        <article class="item">
          <h3>${escapeHtml(decision.title)}</h3>
          <p>${escapeHtml(decision.rationale)}</p>
          <p><strong>${escapeHtml(decision.owner_role)}</strong> | ${escapeHtml(decision.deadline)}</p>
          <p>${escapeHtml(decision.success_signal)}</p>
        </article>
      `,
    )
    .join("");
  container.innerHTML = `
    <article class="item council-summary">
      <h3>${escapeHtml(council.session_title)}</h3>
      <p>${escapeHtml(council.objective)}</p>
      <p><strong>الاتفاق النهائي:</strong> ${escapeHtml(council.final_consensus)}</p>
    </article>
    <div class="dialogue-list">${turns}</div>
    <div class="item-list">${decisions}</div>
  `;
}

function fillProtocol(container, protocol) {
  container.className = "protocol-grid";
  if (!protocol) {
    container.innerHTML = `<article class="item"><p>لم يتم إنشاء بروتوكول لهذه الزيارة.</p></article>`;
    return;
  }
  const principles = asArray(protocol.operating_principles).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const steps = asArray(protocol.steps)
    .map(
      (step) => `
        <article class="item">
          <span class="tag high-priority">${escapeHtml(step.day_range)}</span>
          <h3>${escapeHtml(step.phase)}</h3>
          <ol class="steps">${asArray(step.actions).map((action) => `<li>${escapeHtml(action)}</li>`).join("")}</ol>
          <p><strong>بوابة الانتقال:</strong> ${escapeHtml(step.gate)}</p>
        </article>
      `,
    )
    .join("");
  container.innerHTML = `
    <article class="item protocol-head">
      <h3>${escapeHtml(protocol.title)}</h3>
      <p>الدرجة المستهدفة: <strong>${protocol.target_score}/100</strong></p>
      <ul class="steps">${principles}</ul>
    </article>
    ${steps}
    <article class="item">
      <h3>الطقس اليومي</h3>
      <ul class="steps">${asArray(protocol.daily_ritual).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </article>
    <article class="item">
      <h3>يوم الزيارة</h3>
      <ul class="steps">${asArray(protocol.visit_day_protocol).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </article>
  `;
}

function fillForms(container, forms) {
  container.className = "forms-grid";
  forms = asArray(forms);
  if (!forms.length) {
    container.innerHTML = `<article class="item"><p>لم تُنشأ نماذج تشغيلية لهذه الزيارة بعد.</p></article>`;
    return;
  }
  container.innerHTML = forms
    .map(
      (form) => `
        <article class="item">
          <h3>${escapeHtml(form.name)}</h3>
          <p>${escapeHtml(form.purpose)}</p>
          <p><strong>${escapeHtml(form.owner_role)}</strong> | ${escapeHtml(form.review_frequency)}</p>
          <ul class="steps">${asArray(form.fields).map((field) => `<li>${escapeHtml(field)}</li>`).join("")}</ul>
          <p><strong>قاعدة الإكمال:</strong> ${escapeHtml(form.completion_rule)}</p>
        </article>
      `,
    )
    .join("");
}

function fillExecution(container, pack) {
  container.className = "execution-grid";
  if (!pack) {
    container.innerHTML = `<article class="item"><p>لم تُنشأ حزمة تنفيذ لهذه الزيارة بعد.</p></article>`;
    return;
  }
  const cycle = asArray(pack.operating_cycle).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const checkpoints = asArray(pack.readiness_checkpoints).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const missions = asArray(pack.missions)
    .map((mission) => {
      const artifacts = asArray(mission.produced_artifacts)
        .map(
          (artifact) => `
            <li>
              <strong>${escapeHtml(artifact.title)}</strong>
              <span>${escapeHtml(artifact.purpose)}</span>
            </li>
          `,
        )
        .join("");
      return `
        <article class="item">
          <span class="tag high-priority">${escapeHtml(mission.agent)}</span>
          <h3>${escapeHtml(mission.mission)}</h3>
          <ul class="artifact-list">${artifacts}</ul>
          <p><strong>الخطوة البشرية التالية:</strong> ${escapeHtml(mission.next_human_action)}</p>
        </article>
      `;
    })
    .join("");
  container.innerHTML = `
    <article class="item protocol-head">
      <h3>${escapeHtml(pack.title)}</h3>
      <p>تم إنشاء ملفات العمل داخل النظام ويمكن تنزيلها كحزمة واحدة.</p>
    </article>
    <article class="item">
      <h3>دورة التشغيل</h3>
      <ul class="steps">${cycle}</ul>
    </article>
    <article class="item">
      <h3>نقاط الجاهزية</h3>
      <ul class="steps">${checkpoints}</ul>
    </article>
    ${missions}
  `;
}

function fillTasks(container, tasks) {
  container.className = "item-list";
  tasks = asArray(tasks);
  container.innerHTML = tasks
    .map(
      (item) => `
        <article class="item task-item">
          <h3>${escapeHtml(item.assignee)}</h3>
          <p>${escapeHtml(item.role)} | ${escapeHtml(item.due_date)}</p>
          <p>${escapeHtml(item.deliverable)}</p>
          <div class="task-actions">
            <button type="button" data-task-status="${escapeHtml(item.action_id)}" data-status="new" class="${item.status === "new" ? "active" : ""}">لم تبدأ</button>
            <button type="button" data-task-status="${escapeHtml(item.action_id)}" data-status="in_progress" class="${item.status === "in_progress" ? "active" : ""}">قيد التنفيذ</button>
            <button type="button" data-task-status="${escapeHtml(item.action_id)}" data-status="done" class="${item.status === "done" ? "active" : ""}">منجزة</button>
          </div>
        </article>
      `,
    )
    .join("");
  container.querySelectorAll("[data-task-status]").forEach((button) => {
    button.addEventListener("click", async () => {
      const visitId = dashboard.dataset.visitId;
      if (!visitId) return;
      const actionId = button.dataset.taskStatus;
      const status = button.dataset.status;
      const response = await fetch(`/api/visits/${visitId}/tasks/${actionId}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      const data = await response.json();
      latestCouncilEvents = asArray(data.council_events || latestCouncilEvents);
      renderDashboard(data.visit, `/api/reports/${data.visit.id}`, data.dashboard, latestEvidenceReviews, latestEvidenceLibrary, latestImpactRecords);
    });
  });
}

function fillEvidenceDesk(container, reviews) {
  reviews = asArray(reviews);
  container.className = "evidence-desk";
  if (!reviews.length) {
    container.innerHTML = `
      <article class="item evidence-empty">
        <h3>لم تصل شواهد بعد</h3>
        <p>ارفع ملف PDF أو صورة أو ملف نصي من لوحة السكرتارية، وسيتم تصنيفه وربطه بالمجال والمؤشر المناسب.</p>
      </article>
    `;
    return;
  }
  container.innerHTML = reviews
    .slice()
    .reverse()
    .map((review) => {
      const edits = asArray(review.required_edits).map((item) => `<li>${escapeHtml(item)}</li>`).join("");
      const signals = asArray(review.matched_signals).map((item) => `<span>${escapeHtml(item)}</span>`).join("");
      const agents = asArray(review.agents).map((item) => `<span>${escapeHtml(agentLabel(item))}</span>`).join("");
      const fileUrl = `/api/evidence/file/${encodeURIComponent(review.id)}`;
      const cardUrl = `/api/evidence/review/${encodeURIComponent(review.id)}/card`;
      const decisionUrl = `/api/evidence/review/${encodeURIComponent(review.id)}/decision`;
      return `
        <article class="evidence-card ${escapeHtml(review.suitability)}">
          <div class="evidence-card-head">
            <div>
              <strong>${escapeHtml(review.original_filename)}</strong>
              <span>${escapeHtml(review.created_at || "")}</span>
            </div>
            <em class="suitability ${escapeHtml(review.suitability)}">${suitabilityLabel(review.suitability)}</em>
          </div>
          <div class="evidence-meta">
            <span>المجال: <strong>${escapeHtml(review.suggested_domain)}</strong></span>
            <span>المؤشر: <strong>${escapeHtml(review.suggested_indicator_code || "غير محدد")}</strong></span>
            <span>الثقة: <strong>${Math.round(Number(review.confidence || 0) * 100)}%</strong></span>
          </div>
          <p class="folder-line">مجلد الحفظ: ${escapeHtml(review.destination_folder || "")}</p>
          <p>${escapeHtml(review.secretariat_opinion)}</p>
          ${review.suggested_indicator_title ? `<p class="muted-line">${escapeHtml(review.suggested_indicator_title)}</p>` : ""}
          ${edits ? `<div class="evidence-edits"><strong>التعديلات المطلوبة</strong><ul>${edits}</ul></div>` : ""}
          ${signals ? `<div class="signal-strip">${signals}</div>` : ""}
          <div class="agent-strip">${agents}</div>
          <div class="evidence-actions">
            <a class="mini-link" href="${fileUrl}" target="_blank">فتح الشاهد الأصلي</a>
            <a class="mini-link" href="${cardUrl}" target="_blank">بطاقة PDF</a>
            <a class="mini-link" href="${decisionUrl}" target="_blank">قرار PDF</a>
            <button type="button" data-delete-evidence="${escapeHtml(review.id)}">حذف</button>
          </div>
          <a class="mini-link" href="${fileUrl}" target="_blank">فتح الشاهد المؤرشف</a>
        </article>
      `;
    })
    .join("");
  container.querySelectorAll("[data-delete-evidence]").forEach((button) => {
    button.addEventListener("click", async () => {
      await deleteEvidenceReview(button.dataset.deleteEvidence);
    });
  });
}

function fillEvidenceLibrary(container, library) {
  if (!container) return;
  const folders = asArray(library?.folders);
  container.className = "evidence-library";
  if (!folders.length) {
    container.innerHTML = `
      <article class="library-empty">
        <strong>مكتبة الشواهد لم تُبن بعد</strong>
        <span>كل شاهد جديد سيُحفظ داخل مجلد الزيارة ثم المجال ثم المؤشر، مع بطاقة اعتماد وفهرس تلقائي.</span>
      </article>
    `;
    return;
  }
  container.innerHTML = folders.map(renderEvidenceFolder).join("");
  container.querySelectorAll("[data-delete-evidence]").forEach((button) => {
    button.addEventListener("click", async () => {
      await deleteEvidenceReview(button.dataset.deleteEvidence);
    });
  });
  return;
  container.innerHTML = folders
    .map((folder) => {
      const readiness = folder.total ? Math.round((Number(folder.suitable || 0) / Number(folder.total || 1)) * 100) : 0;
      return `
        <article class="library-folder">
          <div class="folder-head">
            <strong>${escapeHtml(folder.domain)}</strong>
            <span>${escapeHtml(folder.indicator_code)} | ${folder.total} شاهد</span>
          </div>
          <p>${escapeHtml(folder.indicator_title)}</p>
          <div class="folder-stats">
            <span class="ok">مناسب: ${folder.suitable || 0}</span>
            <span class="warn">يحتاج تعديل: ${folder.needs_edit || 0}</span>
            <span class="bad">غير كاف: ${folder.insufficient || 0}</span>
          </div>
          <div class="folder-readiness"><i style="width:${readiness}%"></i></div>
          <small>${escapeHtml(folder.destination_folder)}</small>
        </article>
      `;
    })
    .join("");
}

function renderEvidenceFolder(folder) {
  const readiness = folder.total ? Math.round((Number(folder.suitable || 0) / Number(folder.total || 1)) * 100) : 0;
  const reviews = asArray(folder.reviews)
    .map((review) => {
      const fileUrl = `/api/evidence/file/${encodeURIComponent(review.id)}`;
      const cardUrl = `/api/evidence/review/${encodeURIComponent(review.id)}/card`;
      const decisionUrl = `/api/evidence/review/${encodeURIComponent(review.id)}/decision`;
      return `
        <li>
          <strong>${escapeHtml(review.original_filename)}</strong>
          <span>${suitabilityLabel(review.suitability)} | ${Math.round(Number(review.confidence || 0) * 100)}%</span>
          <div class="folder-evidence-actions">
            <a href="${fileUrl}" target="_blank">الأصل</a>
            <a href="${cardUrl}" target="_blank">بطاقة PDF</a>
            <a href="${decisionUrl}" target="_blank">قرار PDF</a>
            <button type="button" data-delete-evidence="${escapeHtml(review.id)}">حذف</button>
          </div>
        </li>
      `;
    })
    .join("");
  return `
    <article class="library-folder ${folder.total ? "has-evidence" : "empty-folder"}">
      <div class="folder-head">
        <div class="folder-title">
          <i class="folder-icon" aria-hidden="true"></i>
          <strong>${escapeHtml(folder.domain)}</strong>
        </div>
        <span>${escapeHtml(folder.indicator_code)} | ${folder.total} شاهد</span>
      </div>
      <p class="folder-indicator">${escapeHtml(folder.indicator_title)}</p>
      <details class="folder-details">
        <summary>المطلوب من الشواهد</summary>
        <p>${escapeHtml(folder.required_evidence || "لم يحدد المطلوب لهذا البند.")}</p>
      </details>
      <div class="folder-stats">
        <span class="ok">مناسب: ${folder.suitable || 0}</span>
        <span class="warn">يحتاج تعديل: ${folder.needs_edit || 0}</span>
        <span class="bad">غير كاف: ${folder.insufficient || 0}</span>
      </div>
      <div class="folder-readiness"><i style="width:${readiness}%"></i></div>
      <details class="folder-contents" ${folder.total ? "" : "open"}>
        <summary>الشواهد داخل هذا المجلد (${folder.total})</summary>
        ${reviews ? `<ul>${reviews}</ul>` : `<p class="empty-folder-note">لا توجد شواهد محفوظة لهذا البند بعد.</p>`}
      </details>
      <small>${escapeHtml(folder.destination_folder)}</small>
    </article>
  `;
}

async function buildEvidenceDossier() {
  const button = dashboard.querySelector("#buildDossierBtn");
  const link = dashboard.querySelector('[data-field="evidenceDossier"]');
  if (!button) return;
  button.disabled = true;
  button.textContent = "جاري تجهيز الحزمة...";
  try {
    const response = await fetch("/api/evidence/dossier/build", { method: "POST" });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "تعذر تجهيز ملف الشواهد");
    }
    const data = await response.json();
    if (link) {
      link.href = data.download_url;
      link.style.display = "inline-block";
    }
    showEvidenceResult("success", `تم تجهيز حزمة الشواهد: ${data.filename}`);
  } catch (error) {
    showEvidenceResult("error", error.message);
  } finally {
    button.disabled = false;
    button.textContent = "تجهيز ملف الشواهد الموحد";
  }
}

async function deleteEvidenceReview(reviewId) {
  if (!reviewId) return;
  const confirmed = window.confirm("هل تريد حذف هذا الشاهد من المكتبة والذاكرة؟");
  if (!confirmed) return;
  try {
    const response = await fetch(`/api/evidence/review/${encodeURIComponent(reviewId)}`, { method: "DELETE" });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "تعذر حذف الشاهد");
    }
    const data = await response.json();
    latestEvidenceReviews = asArray(data.recent);
    latestEvidenceLibrary = data.library || latestEvidenceLibrary;
    fillEvidenceDesk(dashboard.querySelector('[data-field="evidenceDesk"]'), latestEvidenceReviews);
    fillEvidenceLibrary(dashboard.querySelector('[data-field="evidenceLibrary"]'), latestEvidenceLibrary);
    showEvidenceResult("success", "تم حذف الشاهد وتحديث مكتبة الشواهد.");
  } catch (error) {
    showEvidenceResult("error", error.message);
  }
}

function fillImpactAgent(container, advice) {
  if (!container) return;
  container.className = "impact-agent";
  if (!advice) {
    container.innerHTML = `
      <article class="item">
        <h3>وكيل ملف الأثر</h3>
        <p>اضغط استشارة وكيل الأثر ليقترح أهدافًا قابلة للقياس بناءً على حقيقة المدرسة.</p>
      </article>
    `;
    return;
  }
  const targets = asArray(advice.measurable_targets)
    .map(
      (target, index) => `
        <article class="impact-target">
          <span>أولوية ${target.rank || index + 1}</span>
          <h3>${escapeHtml(target.title)}</h3>
          <p>${escapeHtml(target.why_this)}</p>
          <div class="before-after">
            <div><b>قياس قبلي</b><p>${escapeHtml(target.before_metric)}</p></div>
            <div><b>قياس بعدي</b><p>${escapeHtml(target.after_metric)}</p></div>
          </div>
          <p><b>طريقة القياس:</b> ${escapeHtml(target.measurement_method)}</p>
          <p><b>حد النجاح:</b> ${escapeHtml(target.success_threshold)}</p>
          <div class="signal-strip">${asArray(target.required_files).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>
          <button type="button" class="mini-action" data-impact-target="${index}">استخدام هذا الهدف</button>
        </article>
      `,
    )
    .join("");
  container.innerHTML = `
    <article class="impact-agent-hero">
      <strong>${escapeHtml(advice.agent_name || "وكيل ملف الأثر")}</strong>
      <p>${escapeHtml(advice.school_truth || "")}</p>
      <span>${escapeHtml(advice.completion_level || "")}</span>
    </article>
    <section class="impact-rules">
      ${asArray(advice.golden_rules).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}
    </section>
    <section class="impact-target-grid">${targets}</section>
  `;
  container.querySelectorAll("[data-impact-target]").forEach((button) => {
    button.addEventListener("click", () => {
      const target = asArray(advice.measurable_targets)[Number(button.dataset.impactTarget)];
      applyImpactTarget(target);
    });
  });
}

function applyImpactTarget(target) {
  if (!impactForm || !target) return;
  impactForm.elements.title.value = target.title || "";
  impactForm.elements.domain.value = target.domain || "";
  impactForm.elements.indicator.value = target.indicator || "";
  impactForm.elements.before_state.value = target.before_metric || "";
  impactForm.elements.after_state.value = target.after_metric || "";
  impactForm.elements.statistics.value = `طريقة القياس: ${target.measurement_method || ""}\nحد النجاح: ${target.success_threshold || ""}`;
  impactForm.elements.narrative.value = target.suggested_narrative || "";
  impactForm.scrollIntoView({ behavior: "smooth", block: "start" });
  showImpactResult("working", "تم ملء النموذج بهدف قابل للقياس. أضف الأرقام الفعلية والمرفقات ثم احفظ قصة الأثر.");
}

async function loadImpactAgentAdvice() {
  const button = dashboard.querySelector("#impactAgentBtn");
  if (button) {
    button.disabled = true;
    button.textContent = "جاري فهم المدرسة...";
  }
  try {
    const response = await fetch("/api/impact/agent");
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "تعذر تشغيل وكيل الأثر");
    }
    latestImpactAdvice = await response.json();
    fillImpactAgent(dashboard.querySelector('[data-field="impactAgent"]'), latestImpactAdvice);
    activateDashboardTab("impact");
  } catch (error) {
    showImpactResult("error", error.message);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = "استشارة وكيل الأثر";
    }
  }
}

function fillImpactBoard(container, records) {
  if (!container) return;
  records = asArray(records);
  container.className = "impact-board";
  if (!records.length) {
    container.innerHTML = `
      <article class="item evidence-empty">
        <h3>لا توجد قصص أثر بعد</h3>
        <p>ابدأ بإدخال حالة قبل/بعد مع نسبة تحسن ومرفقات. المدارس المتميزة لا تعرض كثرة البرامج، بل تعرض أثرًا موثقًا.</p>
      </article>
    `;
    return;
  }
  const averageImpact = average(records.map((record) => Number(record.improvement_rate || 0)));
  const golden = records.filter((record) => record.impact_level === "golden").length;
  const cards = records
    .slice()
    .reverse()
    .map((record) => {
      const notes = asArray(record.validation_notes).map((note) => `<li>${escapeHtml(note)}</li>`).join("");
      const files = asArray(record.stored_files).map((path) => `<span>${escapeHtml(String(path).split(/[\\\\/]/).pop())}</span>`).join("");
      return `
        <article class="impact-card ${escapeHtml(record.impact_level)}">
          <div class="impact-head">
            <div>
              <strong>${escapeHtml(record.title)}</strong>
              <span>${escapeHtml(record.domain)} / ${escapeHtml(record.indicator || "عام")}</span>
            </div>
            <em>${impactLevelLabel(record.impact_level)}</em>
          </div>
          <div class="before-after">
            <div><b>قبل</b><p>${escapeHtml(record.before_state)}</p></div>
            <div><b>بعد</b><p>${escapeHtml(record.after_state)}</p></div>
          </div>
          <div class="impact-meter">
            <span>نسبة التحسن</span>
            <strong>${Number(record.improvement_rate || 0).toFixed(1)}%</strong>
            <i style="width:${Math.max(0, Math.min(100, Number(record.improvement_rate || 0)))}%"></i>
          </div>
          ${record.statistics ? `<p><b>الإحصاءات:</b> ${escapeHtml(record.statistics)}</p>` : ""}
          ${record.narrative ? `<p>${escapeHtml(record.narrative)}</p>` : ""}
          ${files ? `<div class="signal-strip">${files}</div>` : ""}
          <div class="evidence-edits"><strong>ملاحظات اكتمال ملف الأثر</strong><ul>${notes}</ul></div>
          <div class="evidence-actions">
            <button type="button" data-delete-impact="${escapeHtml(record.id)}">حذف</button>
          </div>
        </article>
      `;
    })
    .join("");
  container.innerHTML = `
    <section class="impact-summary">
      <article><span>قصص الأثر</span><strong>${records.length}</strong></article>
      <article><span>متوسط التحسن</span><strong>${averageImpact.toFixed(1)}%</strong></article>
      <article><span>أثر ذهبي</span><strong>${golden}</strong></article>
    </section>
    <section class="impact-grid">${cards}</section>
  `;
  container.querySelectorAll("[data-delete-impact]").forEach((button) => {
    button.addEventListener("click", async () => {
      await deleteImpactRecord(button.dataset.deleteImpact);
    });
  });
}

async function buildImpactPackage() {
  const button = dashboard.querySelector("#buildImpactBtn");
  const link = dashboard.querySelector('[data-field="impactPackage"]');
  if (!button) return;
  button.disabled = true;
  button.textContent = "جاري تجهيز الملف الذهبي...";
  try {
    const response = await fetch("/api/impact/package/build", { method: "POST" });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "تعذر تجهيز الملف الذهبي");
    }
    const data = await response.json();
    if (link) {
      link.href = data.download_url;
      link.style.display = "inline-block";
    }
    showImpactResult("success", `تم تجهيز الملف الذهبي: ${data.filename}`);
  } catch (error) {
    showImpactResult("error", error.message);
  } finally {
    button.disabled = false;
    button.textContent = "تجهيز الملف الذهبي";
  }
}

async function deleteImpactRecord(recordId) {
  if (!recordId) return;
  const confirmed = window.confirm("هل تريد حذف قصة الأثر من الملف الذهبي؟");
  if (!confirmed) return;
  try {
    const response = await fetch(`/api/impact/records/${encodeURIComponent(recordId)}`, { method: "DELETE" });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "تعذر حذف قصة الأثر");
    }
    const data = await response.json();
    latestImpactRecords = asArray(data.records);
    fillImpactBoard(dashboard.querySelector('[data-field="impactBoard"]'), latestImpactRecords);
    showImpactResult("success", "تم حذف قصة الأثر وتحديث الملف الذهبي.");
  } catch (error) {
    showImpactResult("error", error.message);
  }
}

function fillSimulation(container, simulation) {
  container.className = "item-list";
  simulation = asArray(simulation);
  container.innerHTML = simulation
    .map(
      (item) => `
        <article class="item">
          <span class="tag ${item.risk_level}">${severityLabel(item.risk_level)}</span>
          <h3>${escapeHtml(item.question)}</h3>
          <p>${escapeHtml(item.expected_evidence)}</p>
        </article>
      `,
    )
    .join("");
}

function fillLearning(container, notes, fastestActions) {
  container.className = "learning-grid";
  const notesHtml = asArray(notes).map((note) => `<li>${escapeHtml(note)}</li>`).join("");
  const actionsHtml = asArray(fastestActions)
    .map((action) => `<li>${escapeHtml(action.title)}: +${action.expected_gain} خلال ${action.due_in_days} يوم</li>`)
    .join("");
  container.innerHTML = `
    <article class="item">
      <h3>ملاحظات الذاكرة</h3>
      <ul class="steps">${notesHtml}</ul>
    </article>
    <article class="item">
      <h3>أسرع 3 إجراءات لرفع الدرجة</h3>
      <ul class="steps">${actionsHtml}</ul>
    </article>
  `;
}

function average(values) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function severityLabel(value) {
  return { high: "حرج", medium: "متوسط", low: "منخفض" }[value] || value;
}

function priorityLabel(value) {
  return { urgent: "عاجل", high: "مرتفع", medium: "متوسط" }[value] || value;
}

function priorityText(value) {
  return { critical: "حرج", high: "مرتفع", medium: "متوسط" }[value] || value;
}

function taskStatusLabel(value) {
  return { new: "لم تبدأ", in_progress: "قيد التنفيذ", done: "منجزة" }[value] || value;
}

function suitabilityLabel(value) {
  return {
    suitable: "مناسب",
    needs_edit: "يحتاج تعديل",
    insufficient: "غير كاف",
  }[value] || value;
}

function impactLevelLabel(value) {
  return {
    limited: "أثر محدود",
    clear: "أثر واضح",
    strong: "أثر قوي",
    golden: "أثر ذهبي",
  }[value] || value;
}

function agentLabel(value) {
  return {
    "Intake Secretary Agent": "وكيل الاستقبال",
    "Evidence Classifier Agent": "وكيل التصنيف",
    "Suitability Reviewer Agent": "وكيل الملاءمة",
    "Archive Clerk Agent": "وكيل الأرشفة",
    "Improvement Notes Agent": "وكيل التحسين",
    "Analyzer Agent": "وكيل التحليل",
    "Progress Agent": "وكيل التقدم",
    "Planner Agent": "وكيل التخطيط",
    "Task Agent": "وكيل المهام",
    "Simulator Agent": "وكيل المحاكاة",
    "Prediction Agent": "وكيل التنبؤ",
    "Report Agent": "وكيل التقرير",
    "Impact Agent": "وكيل الأثر",
  }[value] || value;
}

function eventTypeLabel(value) {
  return {
    analysis: "تحليل",
    evidence: "شاهد",
    impact: "أثر",
    task: "مهمة",
    outcome: "نتيجة",
    system: "نظام",
  }[value] || value;
}

function guaranteeLabel(value) {
  return {
    high_risk: "خطر عال: لا تعتمد الملفات قبل ظهور أثر حقيقي",
    promising: "واعد: يحتاج ضبط الأدلة والميدان أسبوعيًا",
    ready: "جاهز: ركز على المقابلات والحصص المفاجئة",
    excellence_ready: "جاهز للتميز: حافظ على الاستدامة والأثر",
  }[value] || value;
}

function formatScore(value) {
  return Number(value ?? 0).toFixed(2).replace(/\.00$/, "");
}

function formatGap(value) {
  const number = Number(value ?? 0);
  return `${number >= 0 ? "+" : ""}${number.toFixed(1)}`;
}
