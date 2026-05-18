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
let latestV2Data = null;   // آخر نتيجة تحليل v2 — تُستخدم لتحديث التبويبات
// ─── استعادة بيانات v2 من localStorage عند تحديث الصفحة ────────────────
try {
  const _stored = localStorage.getItem('latestV2Data');
  if (_stored) latestV2Data = JSON.parse(_stored);
} catch(_e) {}

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
  const button = form.querySelector("button[type=submit]");
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "جاري التحليل...";

  // تأكد من إرسال has_previous بشكل صحيح
  const hasPrev = document.getElementById("hasPreviousCheck")?.checked;
  const payload = new FormData(form);
  payload.set("has_previous", hasPrev ? "true" : "false");

  try {
    const response = await fetch("/api/v2/analyze", {
      method: "POST",
      body: payload,
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "تعذر تشغيل النظام");
    }
    const data = await response.json();
    latestV2Data = data;
    try { localStorage.setItem('latestV2Data', JSON.stringify(data)); } catch(_e) {}
    renderV2Result(data);
    renderV2Dashboard(data);      // عرض التبويبات الكاملة بالنظام الجديد
    await loadWorkspace();        // تحديث الشواهد وملف الأثر في الخلفية
    loadMemorySummary();
  } catch (error) {
    dashboard.innerHTML = `<div class="empty-state"><h2>تعذر تشغيل النظام</h2><p>${escapeHtml(error.message)}</p></div>`;
  } finally {
    button.disabled = false;
    button.textContent = originalText;
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
    userPill.textContent = user ? `${displayUserName(user)} | ${user.role}` : "";
  }
}

function displayUserName(user) {
  const name = String(user?.display_name || "").trim();
  if (name && !name.includes("?") && !/[طظ][\u0080-\u00ff]/.test(name)) {
    return name;
  }
  if (user?.role === "admin" || user?.can_manage_users) {
    return "مدير النظام";
  }
  if (user?.role === "demo" || user?.can_write === false) {
    return "مستخدم تجريبي";
  }
  return user?.username || "مستخدم";
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
    if (latestV2Data) {
      // هل تم عرض لوحة التبويبات مسبقاً في هذه الجلسة؟
      const libEl  = dashboard.querySelector('[data-field="evidenceLibrary"]');
      if (!libEl) {
        // ── الصفحة تحمّل من جديد (تحديث) — أعد رسم اللوحة الكاملة ──────
        renderV2Dashboard(latestV2Data);
        // بعد renderV2Dashboard يتم الاستعادة الكاملة، نخرج مبكراً
        return;
      }
      // تحديث تبويبي الشواهد والأثر فقط — بقية التبويبات مُعبّأة من v2
      const deskEl = dashboard.querySelector('[data-field="evidenceDesk"]');
      const impactEl = dashboard.querySelector('[data-field="impactBoard"]');
      const councilEl = dashboard.querySelector('[data-field="liveCouncil"]');
      fillEvidenceLibrary(libEl, v2MergeEvidenceLibrary(latestV2Data, latestEvidenceLibrary));
      if (deskEl)   fillEvidenceDesk(deskEl, latestEvidenceReviews);
      if (impactEl) fillImpactBoard(impactEl, latestImpactRecords);
      if (councilEl) fillLiveCouncil(councilEl, latestCouncilEvents);
    } else if (data.has_memory && data.active_visit) {
      // كشف نوع الزيارة: v2 تستخدم مفاتيح ETEC الأربعة
      const _V2_KEYS = new Set(["school_management","teaching_learning","learning_outcomes","school_environment"]);
      const _isV2 = (data.active_visit.domains || []).some(d => _V2_KEYS.has(d.key));
      if (_isV2) {
        // زيارة v2 — أعد بناء اللوحة من بيانات الذاكرة
        // خريطة رمز المؤشر → مجال ETEC
        const _CODE_DOMAIN = {1:"school_management",2:"teaching_learning",3:"learning_outcomes",4:"school_environment"};
        const _DOM_AR = {school_management:"الإدارة المدرسية",teaching_learning:"التعليم والتعلم",learning_outcomes:"نواتج التعلم",school_environment:"البيئة المدرسية"};
        // تطبيع المجالات إلى v2 format
        const _etecDomains = ["school_management","teaching_learning","learning_outcomes","school_environment"];
        const _domainMap = {};
        (data.active_visit.domains||[]).forEach(d => { if(_etecDomains.includes(d.key)) _domainMap[d.key]=d; });
        const _normDomains = _etecDomains.map(k => {
          const d = _domainMap[k] || {};
          const sc = d.current_score ?? 0;
          return { domain_key:k, label:_DOM_AR[k], score:sc, below_threshold: sc < 75 };
        });
        // بناء targets مع تصحيح domain_key من رمز المؤشر
        const _targets = (data.active_visit.plan||[]).map(a => {
          const code = a.success_metric?.match(/\d+-\d+-\d+-\d+/)?.[0] || "";
          const prefix = parseInt(code.split("-")[0]) || 0;
          const dk = _CODE_DOMAIN[prefix] || a.domain || "learning_outcomes";
          return { domain_key:dk, indicator_code:code, indicator_title:a.title,
            evidence_required:a.steps||[], achieved_evidence:[], missing_evidence:[] };
        });
        const _minV2 = { ...data.active_visit,
          plan: { targets: _targets, summary: "", weeks_to_visit_estimate: 8 },
          analysis: {
            domain_scores: _normDomains,
            weaknesses: data.active_visit.weaknesses || [],
            overall_score: _normDomains.reduce((s,d)=>s+d.score,0) / Math.max(_normDomains.length,1),
          },
          prediction: data.active_visit.prediction || {},
          simulation_questions: data.active_visit.simulation || [],
        };
        latestV2Data = _minV2;
        try { localStorage.setItem('latestV2Data', JSON.stringify(_minV2)); } catch(_e) {}
        renderV2Dashboard(_minV2);
      } else {
        renderDashboard(data.active_visit, data.dashboard?.report_url || `/api/reports/${data.active_visit.id}`, data.dashboard, latestEvidenceReviews, latestEvidenceLibrary, latestImpactRecords);
      }
    }
  } catch {
    // Keep the start screen if memory is not available.
  }
}

// ═══════════════════════════════════════════════════════════════════════
//  renderV2Dashboard — يُعبّئ جميع التبويبات بالبيانات الجديدة (ETEC v2)
// ═══════════════════════════════════════════════════════════════════════
function renderV2Dashboard(data) {
  const view = template.content.cloneNode(true);
  const pred = data.prediction || {};
  const analysis = data.analysis || { domain_scores: [], weaknesses: [], overall_score: 0 };
  const plan = data.plan || { targets: [], summary: "", weeks_to_visit_estimate: 8 };

  // ── المقاييس العلوية ────────────────────────────────────────────────
  view.querySelector('[data-field="expected"]').textContent    = `${pred.overall_predicted ?? 0}/100`;
  view.querySelector('[data-field="confidence"]').textContent  = `${Math.round((pred.confidence ?? 0) * 100)}%`;
  const gain = pred.overall_gain ?? 0;
  view.querySelector('[data-field="improvement"]').textContent = `${gain >= 0 ? "+" : ""}${Number(gain).toFixed(1)}`;

  // ── تبويب: النظرة العامة ────────────────────────────────────────────
  v2FillProgressBoard(view.querySelector('[data-field="progressBoard"]'), data);
  v2FillDomainList(view.querySelector('[data-field="domains"]'), data);
  v2FillWeaknesses(view.querySelector('[data-field="weaknesses"]'), analysis.weaknesses);
  fillScenarios(view.querySelector('[data-field="scenarios"]'), pred.scenarios);

  // ── تبويب: التقييم الخارجي ─────────────────────────────────────────
  v2FillExternalReadiness(view.querySelector('[data-field="externalReadiness"]'), data);
  v2FillSimulation(view.querySelector('[data-field="simulation"]'), data.simulation_questions);

  // ── تبويب: الشواهد — مزج مجلدات ETEC من بيانات v2 مع الذاكرة ────────
  const mergedLibrary = v2MergeEvidenceLibrary(data, latestEvidenceLibrary);
  fillEvidenceLibrary(view.querySelector('[data-field="evidenceLibrary"]'), mergedLibrary);
  fillEvidenceDesk(view.querySelector('[data-field="evidenceDesk"]'), latestEvidenceReviews);

  // ── تبويب: ملف الأثر (من الذاكرة) ─────────────────────────────────
  fillImpactAgent(view.querySelector('[data-field="impactAgent"]'), latestImpactAdvice);
  fillImpactBoard(view.querySelector('[data-field="impactBoard"]'), latestImpactRecords);

  // ── تبويب: الخطة والمهام ────────────────────────────────────────────
  v2FillPlan(view.querySelector('[data-field="plan"]'), plan);
  v2FillTasks(view.querySelector('[data-field="tasks"]'), plan);

  // ── تبويب: الوكلاء والبروتوكول ─────────────────────────────────────
  fillLiveCouncil(view.querySelector('[data-field="liveCouncil"]'), latestCouncilEvents);
  v2FillCouncil(view.querySelector('[data-field="council"]'), data);
  v2FillProtocol(view.querySelector('[data-field="protocol"]'), data);
  v2FillForms(view.querySelector('[data-field="forms"]'), data);
  v2FillExecution(view.querySelector('[data-field="execution"]'), data);

  // ── تبويب: التقارير والذاكرة ────────────────────────────────────────
  v2FillReportProfile(view.querySelector('[data-field="reportProfile"]'), data);
  fillLearning(
    view.querySelector('[data-field="learning"]'),
    [pred.confidence_explanation, pred.caveat],
    asArray(plan.targets).slice(0, 3).map(t => ({
      title: t.indicator_title,
      expected_gain: t.target_score - t.current_score,
      due_in_days: (plan.weeks_to_visit_estimate || 8) * 7,
    }))
  );

  // ── روابط وأزرار ────────────────────────────────────────────────────
  view.querySelector('[data-field="report"]').style.display        = "none";
  view.querySelector('[data-field="executionDownload"]').style.display = "none";
  view.querySelector('[data-field="evidenceDossier"]').style.display  = "none";
  view.querySelector('[data-field="impactPackage"]').style.display    = "none";

  dashboard.innerHTML = "";
  dashboard.dataset.visitId = data.visit_id || "";
  dashboard.appendChild(view);
  setupDashboardTabs("overview");

  // أزرار الشواهد والأثر
  const buildDossierBtn = dashboard.querySelector("#buildDossierBtn");
  if (buildDossierBtn) buildDossierBtn.addEventListener("click", buildEvidenceDossier);
  const buildImpactBtn = dashboard.querySelector("#buildImpactBtn");
  if (buildImpactBtn) buildImpactBtn.addEventListener("click", buildImpactPackage);
  const impactAgentBtn = dashboard.querySelector("#impactAgentBtn");
  if (impactAgentBtn) impactAgentBtn.addEventListener("click", loadImpactAgentAdvice);
  setupAdminControls();
}

// ── النظرة العامة: بطاقة التقدم ──────────────────────────────────────
function v2FillProgressBoard(container, data) {
  const a    = data.analysis  || {};
  const pred = data.prediction || {};
  const prog = data.progress;

  const domainScores = asArray(a.domain_scores);
  const domainChart = domainScores.map(d => {
    const below = d.below_threshold;
    const prev  = prog ? (prog.domain_changes[d.domain_key]?.previous || 0) : 0;
    const delta = prog ? (prog.domain_changes[d.domain_key]?.delta    || 0) : 0;
    const deltaHtml = prog && prev > 0
      ? `<span class="delta-pill ${delta >= 0 ? "up" : "down"}">${delta >= 0 ? "+" : ""}${Number(delta).toFixed(1)}</span>`
      : "";
    return `
      <div class="chart-row${below ? " below-threshold" : ""}">
        <strong>${escapeHtml(d.label)}</strong>
        <div class="dual-bars">
          ${prev > 0 ? `<span class="previous" style="width:${prev}%"></span>` : ""}
          <span class="current" style="width:${d.score}%"></span>
          <span class="threshold-line" style="left:75%" title="عتبة الانطلاق"></span>
        </div>
        <em>${d.score}%${below ? " ⚠" : ""}</em>
        ${deltaHtml}
      </div>`;
  }).join("");

  const flags = prog ? asArray(prog.flags).map(f =>
    `<p style="color:var(--amber);font-size:0.82rem;margin:4px 0">⚠ ${escapeHtml(f)}</p>`).join("") : "";

  const scenarioChart = asArray(pred.scenarios).map(s => `
    <div class="scenario-bar">
      <span>${escapeHtml(s.name)}</span>
      <div><i style="width:${Number(s.score || 0)}%"></i></div>
      <strong>${formatScore(s.score)}</strong>
    </div>`).join("");

  container.className = "progress-board";
  container.innerHTML = `
    <article class="progress-hero live-card">
      <div class="donut" style="--value:${a.overall_score || 0}">
        <strong>${a.overall_score || 0}%</strong>
      </div>
      <div>
        <span>${escapeHtml(a.classification_label || "")}</span>
        <p>${escapeHtml(a.description || "")}</p>
      </div>
    </article>
    <article class="progress-card live-card">
      <span>الدرجة المتوقعة</span>
      <strong>${pred.overall_predicted || 0}/100</strong>
    </article>
    <article class="progress-card live-card">
      <span>مستوى الثقة</span>
      <strong>${Math.round((pred.confidence || 0) * 100)}%</strong>
    </article>
    <article class="chart-panel">
      <div class="chart-title">
        <h3>المجالات الأربعة الرسمية</h3>
        <span>الخط الأصفر = عتبة 75%</span>
      </div>
      <div class="domain-chart">${domainChart}</div>
      ${flags}
    </article>
    <article class="chart-panel">
      <div class="chart-title"><h3>سيناريوهات الدرجة</h3><span>0-100</span></div>
      <div class="scenario-chart">${scenarioChart}</div>
    </article>`;
}

// ── النظرة العامة: مقارنة المجالات التفصيلية ─────────────────────────
function v2FillDomainList(container, data) {
  const domainScores = asArray(data.analysis.domain_scores);
  const prog = data.progress;
  container.innerHTML = domainScores.map(d => {
    const prev  = prog ? (prog.domain_changes[d.domain_key]?.previous || 0) : 0;
    const delta = prog ? (prog.domain_changes[d.domain_key]?.delta    || 0) : 0;
    const prevLabel = prev > 0 ? `السابق ${formatScore(prev)} | ` : "";
    return `
      <div class="domain-row${d.below_threshold ? " below-threshold" : ""}">
        <strong>${escapeHtml(d.label)}</strong>
        <div class="bar" title="${d.score}/100">
          <span style="width:${d.score}%"></span>
          <span class="threshold-mark" style="left:75%"></span>
        </div>
        <span class="domain-score">${prevLabel}الحالي ${formatScore(d.score)} | ${d.below_threshold ? `<span style="color:var(--red)">⚠ دون العتبة بـ ${(75 - d.score).toFixed(1)} نقطة</span>` : `<span style="color:var(--teal)">✅ فوق العتبة</span>`}</span>
      </div>`;
  }).join("");
}

// ── النظرة العامة: نقاط الضعف ────────────────────────────────────────
function v2FillWeaknesses(container, weaknesses) {
  container.className = "item-list";
  weaknesses = asArray(weaknesses);
  if (!weaknesses.length) {
    container.innerHTML = `<article class="item"><p>✅ جميع المجالات فوق عتبة الانطلاق — لا توجد نقاط ضعف حرجة.</p></article>`;
    return;
  }
  container.innerHTML = weaknesses.map(w => `
    <article class="item">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span class="tag high">${escapeHtml(w.indicator_code || "")}</span>
        <strong style="font-size:0.88rem">${escapeHtml(w.indicator_title || "")}</strong>
      </div>
      <p style="font-size:0.8rem;color:var(--muted);margin:4px 0">
        المجال: <strong>${escapeHtml(w.domain_key || "")}</strong> |
        الدرجة: <strong style="color:var(--red)">${w.score}%</strong> |
        الفجوة: <strong style="color:var(--red)">${w.gap} نقطة</strong>
      </p>
      <p style="font-size:0.8rem">${escapeHtml(w.impact || "")}</p>
    </article>`).join("");
}

// ── تبويب التقييم الخارجي ─────────────────────────────────────────────
function v2FillExternalReadiness(container, data) {
  const a    = data.analysis   || {};
  const pred = data.prediction || {};
  const readinessPct = Math.round(pred.overall_predicted || 0);
  const guaranteeLevel = readinessPct >= 80 ? "excellence_ready"
                       : readinessPct >= 70 ? "ready"
                       : readinessPct >= 60 ? "promising"
                       : "high_risk";

  const domainScores = asArray(a.domain_scores);
  const targets = asArray(data.plan.targets);

  const dimensionsHtml = domainScores.map(d => {
    const relActions = targets.filter(t => t.domain_key === d.domain_key).slice(0, 3);
    const actionsHtml = relActions.map(t => `<li>${escapeHtml(t.action)}</li>`).join("");
    const riskText   = d.below_threshold
      ? `الدرجة ${d.score}% دون عتبة الانطلاق (75%) — خطر رفع تقرير ضعف.`
      : `الدرجة فوق العتبة — حافظ على التوثيق.`;
    const excText    = d.below_threshold ? "رفع الدرجة بتحقيق الشواهد الناقصة" : "توثيق الاستدامة وإظهار الأثر";
    return `
      <article class="external-dimension">
        <div>
          <strong>${escapeHtml(d.label)}</strong>
          <span>${formatScore(d.score)}%</span>
        </div>
        <div class="folder-readiness"><i style="width:${Number(d.score || 0)}%"></i></div>
        <p><b>علامة الخطر:</b> ${escapeHtml(riskText)}</p>
        <p><b>علامة التميز:</b> ${escapeHtml(excText)}</p>
        ${actionsHtml ? `<ul class="steps">${actionsHtml}</ul>` : ""}
      </article>`;
  }).join("");

  container.className = "external-readiness";
  container.innerHTML = `
    <article class="external-hero ${escapeHtml(guaranteeLevel)}">
      <div class="donut" style="--value:${readinessPct}">
        <strong>${readinessPct}%</strong>
      </div>
      <div>
        <span>${guaranteeLabel(guaranteeLevel)}</span>
        <p>${escapeHtml(pred.confidence_explanation || "")} | ${escapeHtml(pred.caveat || "")}</p>
      </div>
    </article>
    <section class="external-grid">${dimensionsHtml}</section>
    <article class="item protocol-head" style="margin-top:16px">
      <h3>بروتوكول ضمان النجاح</h3>
      <ul class="steps">
        <li>وثّق الشواهد الناقصة قبل الزيارة بأسبوعين على الأقل.</li>
        <li>راجع قائمة شواهد كل مؤشر ضعيف وتأكد من اكتمالها.</li>
        <li>أجرِ محاكاة داخلية بالأسئلة المتوقعة قبل يومين من الزيارة.</li>
        <li>جهّز ملف الأدلة مرتباً حسب المجال ثم المؤشر ثم الشاهد.</li>
      </ul>
    </article>`;
}

// ── تبويب التقييم الخارجي: أسئلة المحاكاة ───────────────────────────
function v2FillSimulation(container, questions) {
  container.className = "item-list";
  questions = asArray(questions);
  if (!questions.length) {
    container.innerHTML = `<article class="item"><p>لا توجد أسئلة محاكاة لهذه الزيارة.</p></article>`;
    return;
  }
  container.innerHTML = questions.map(q => {
    const evHtml = asArray(q.expected_evidence).map(e => `<span>${escapeHtml(e)}</span>`).join("");
    return `
      <article class="item">
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:6px">
          <span class="v2-indicator-code" style="background:var(--blue)">${escapeHtml(q.indicator_code || "—")}</span>
          <span style="font-size:0.78rem;color:var(--muted)">${escapeHtml(q.domain || "")}</span>
        </div>
        <h3 style="font-size:0.88rem;margin:4px 0">${escapeHtml(q.question)}</h3>
        ${evHtml ? `<div class="signal-strip" style="margin-top:8px">${evHtml}</div>` : ""}
      </article>`;
  }).join("");
}

// ── تبويب الخطة: أهداف التحسين مع الشواهد ───────────────────────────
function v2FillPlan(container, plan) {
  container.className = "item-list";
  const targets = asArray(plan.targets);
  if (!targets.length) {
    container.innerHTML = `<article class="item"><p>لا توجد أهداف تحسين.</p></article>`;
    return;
  }
  const summaryHtml = `
    <article class="item protocol-head">
      <h3>${escapeHtml(plan.summary || "")}</h3>
      <p>المهلة المقدرة: <strong>${plan.weeks_to_visit_estimate || 8} أسابيع</strong></p>
    </article>`;
  const targetsHtml = targets.map(t => {
    const achieved = asArray(t.achieved_evidence);
    const missing  = asArray(t.missing_evidence);
    const total    = achieved.length + missing.length;
    const pct      = total ? Math.round(achieved.length / total * 100) : 0;
    const priorityCls = t.domain_key === "learning_outcomes" ? "urgent"
                      : t.domain_key === "school_management"  ? "high" : "medium";
    const checklistHtml = total > 0 ? `
      <details class="v2-evidence-checklist">
        <summary>
          <span class="ev-summary-text">الشواهد: ${achieved.length}/${total} متحقق</span>
          <div class="ev-mini-bar"><div class="ev-mini-fill" style="width:${pct}%"></div></div>
        </summary>
        <ul class="v2-evidence-list">
          ${achieved.map(e => `<li class="ev-achieved"><span class="ev-check">✅</span>${escapeHtml(e)}</li>`).join("")}
          ${missing.map(e  => `<li class="ev-missing"><span class="ev-check">❌</span>${escapeHtml(e)}</li>`).join("")}
        </ul>
      </details>` : "";
    return `
      <article class="item">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px">
          <span class="tag ${escapeHtml(priorityCls)}">#${t.rank}</span>
          <span class="v2-indicator-code">${escapeHtml(t.indicator_code)}</span>
          <strong style="font-size:0.88rem">${escapeHtml(t.indicator_title)}</strong>
        </div>
        <div class="v2-score-arrow" style="margin:6px 0">${t.current_score}% ← ${t.target_score}%</div>
        <p style="font-size:0.82rem;margin:4px 0">${escapeHtml(t.action)}</p>
        ${checklistHtml}
      </article>`;
  }).join("");
  container.innerHTML = summaryHtml + targetsHtml;
}

// ── تبويب الخطة: توزيع المهام ────────────────────────────────────────
function v2FillTasks(container, plan) {
  container.className = "item-list";
  const targets = asArray(plan.targets);
  if (!targets.length) {
    container.innerHTML = `<article class="item"><p>المهام تُولَّد بعد تعيين مسؤولين لكل مؤشر.</p></article>`;
    return;
  }
  const weeks = plan.weeks_to_visit_estimate || 8;
  const today = new Date();
  container.innerHTML = targets.slice(0, 6).map((t, i) => {
    const dueDate = new Date(today);
    dueDate.setDate(today.getDate() + Math.ceil(weeks / targets.length) * (i + 1) * 7);
    const dueDateStr = dueDate.toISOString().slice(0, 10);
    const missing = asArray(t.missing_evidence).slice(0, 3);
    return `
      <article class="item task-item">
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <span class="v2-indicator-code">${escapeHtml(t.indicator_code)}</span>
          <strong style="font-size:0.88rem">${escapeHtml(t.indicator_title)}</strong>
        </div>
        <p style="font-size:0.8rem;color:var(--muted);margin:4px 0">
          مدير المدرسة | موعد التنفيذ: ${dueDateStr} | التحسين المستهدف: +${(t.target_score - t.current_score).toFixed(1)}%
        </p>
        ${missing.length ? `<ul class="steps" style="font-size:0.78rem;margin:6px 0">${missing.map(e => `<li>${escapeHtml(e)}</li>`).join("")}</ul>` : ""}
        <div class="task-actions" style="opacity:0.6">
          <button type="button" disabled>لم تبدأ</button>
          <button type="button" disabled>قيد التنفيذ</button>
          <button type="button" disabled>منجزة</button>
        </div>
      </article>`;
  }).join("");
}

// ── تبويب الوكلاء: مجلس الوكلاء ─────────────────────────────────────
function v2FillCouncil(container, data) {
  container.className = "council-layout";
  const weaknesses = asArray(data.analysis.weaknesses);
  const targets    = asArray(data.plan.targets);
  const turnsHtml  = weaknesses.slice(0, 4).map((w, i) => `
    <article class="dialogue-turn">
      <div>
        <span class="round">مؤشر ${i + 1}</span>
        <strong>${escapeHtml(w.indicator_code || "")} — وكيل التحليل</strong>
      </div>
      <h3>${escapeHtml(w.indicator_title || "")}</h3>
      <p>${escapeHtml(w.impact || "")}</p>
      <p><strong>التوصية:</strong> رفع الدرجة من ${w.score}% إلى ${Math.min(w.score + 15, 100)}% بتحقيق الشواهد الناقصة.</p>
    </article>`).join("");
  const decisionsHtml = targets.slice(0, 3).map(t => `
    <article class="item">
      <h3>${escapeHtml(t.indicator_title)}</h3>
      <p>${escapeHtml(t.action)}</p>
      <p><strong>المسؤول:</strong> مدير المدرسة | <strong>الهدف:</strong> ${t.target_score}%</p>
      <p><strong>علامة النجاح:</strong> تحقيق ${asArray(t.missing_evidence).length} شاهد ناقص</p>
    </article>`).join("");
  container.innerHTML = `
    <article class="item council-summary">
      <h3>جلسة وكلاء ETEC</h3>
      <p>تحليل ${asArray(data.analysis.domain_scores).length} مجالات رسمية — ${escapeHtml(data.framework || "")}</p>
      <p><strong>الاتفاق النهائي:</strong> ${escapeHtml(data.plan.summary || "")}</p>
    </article>
    <div class="dialogue-list">${turnsHtml}</div>
    <div class="item-list">${decisionsHtml}</div>`;
}

// ── تبويب الوكلاء: بروتوكول التميز ──────────────────────────────────
function v2FillProtocol(container, data) {
  container.className = "protocol-grid";
  const targets  = asArray(data.plan.targets);
  const weeks    = data.plan.weeks_to_visit_estimate || 8;
  const pred     = data.prediction || {};
  const stepsHtml = targets.slice(0, 4).map((t, i) => {
    const phase = ["الأسبوع 1–2", "الأسبوع 2–4", "الأسبوع 4–6", "الأسبوع 6–8"][i] || `الأسبوع ${i * 2}–${i * 2 + 2}`;
    const missingItems = asArray(t.missing_evidence).slice(0, 5).map(e => `<li>${escapeHtml(e)}</li>`).join("");
    return `
      <article class="item">
        <span class="tag high-priority">${phase}</span>
        <h3>${escapeHtml(t.indicator_code)} — ${escapeHtml(t.indicator_title)}</h3>
        <ol class="steps">${missingItems}</ol>
        <p><strong>بوابة الانتقال:</strong> إغلاق ${asArray(t.missing_evidence).length} شاهد ناقص</p>
      </article>`;
  }).join("");
  container.innerHTML = `
    <article class="item protocol-head">
      <h3>بروتوكول التميز للزيارة القادمة</h3>
      <p>الدرجة المستهدفة: <strong>${pred.overall_predicted || 0}/100</strong> | الوقت المتاح: ${weeks} أسابيع</p>
      <ul class="steps">
        <li>الالتزام بتحقيق جميع الشواهد الناقصة في كل مؤشر ضعيف.</li>
        <li>توثيق التحسين بأدلة ملموسة: أرقام، صور، نتائج.</li>
        <li>إشراك جميع منسوبي المدرسة في خطة التحسين.</li>
        <li>مراجعة أسبوعية للتقدم على كل مؤشر.</li>
      </ul>
    </article>
    ${stepsHtml}`;
}

// ── تبويب الوكلاء: النماذج التشغيلية ────────────────────────────────
function v2FillForms(container, data) {
  container.className = "forms-grid";
  const targets = asArray(data.plan.targets).slice(0, 4);
  container.innerHTML = targets.map(t => `
    <article class="item">
      <h3>نموذج متابعة: ${escapeHtml(t.indicator_code)}</h3>
      <p>${escapeHtml(t.indicator_title)}</p>
      <p><strong>مدير المدرسة</strong> | مراجعة أسبوعية</p>
      <ul class="steps">
        ${asArray(t.missing_evidence).slice(0, 4).map(e => `<li>${escapeHtml(e)}</li>`).join("")}
      </ul>
      <p><strong>قاعدة الإكمال:</strong> تحقيق جميع الشواهد المدرجة قبل موعد الزيارة.</p>
    </article>`).join("") ||
    `<article class="item"><p>النماذج التشغيلية تُولَّد عند تفعيل وكلاء التنفيذ.</p></article>`;
}

// ── تبويب الوكلاء: حزمة التنفيذ ─────────────────────────────────────
function v2FillExecution(container, data) {
  container.className = "execution-grid";
  const targets = asArray(data.plan.targets);
  const cycle = [
    "رصد الدرجة الحالية لكل مؤشر وتوثيقها.",
    "تحديد الشواهد الناقصة وتعيين مسؤول لكل شاهد.",
    "تنفيذ الإجراءات التصحيحية وجمع الأدلة.",
    "مراجعة أسبوعية وتحديث قائمة الشواهد.",
    "جلسة مراجعة نهائية قبل الزيارة بأسبوع.",
  ].map(item => `<li>${item}</li>`).join("");
  const missionsHtml = targets.slice(0, 3).map(t => {
    const artifacts = asArray(t.missing_evidence).slice(0, 3).map(e =>
      `<li><strong>${escapeHtml(e)}</strong><span>شاهد مطلوب للمؤشر ${escapeHtml(t.indicator_code)}</span></li>`
    ).join("");
    return `
      <article class="item">
        <span class="tag high-priority">وكيل التنفيذ</span>
        <h3>${escapeHtml(t.indicator_title)}</h3>
        <ul class="artifact-list">${artifacts}</ul>
        <p><strong>الخطوة البشرية التالية:</strong> ${escapeHtml(t.action)}</p>
      </article>`;
  }).join("");
  container.innerHTML = `
    <article class="item protocol-head"><h3>حزمة التنفيذ</h3>
      <p>مبنية على ${targets.length} مؤشر بأولوية تحسين.</p>
    </article>
    <article class="item"><h3>دورة التشغيل</h3><ul class="steps">${cycle}</ul></article>
    ${missionsHtml}`;
}

// ── تبويب التقارير: ملخص الزيارة ────────────────────────────────────
function v2FillReportProfile(container, data) {
  container.className = "report-profile";
  const a = data.analysis || {};
  const domainCardsHtml = asArray(a.domain_scores).map(d => `
    <article class="item">
      <h3>${escapeHtml(d.label)}: ${d.score}%</h3>
      <p>${d.below_threshold ? "دون العتبة" : "فوق العتبة"} | ${d.below_threshold ? "يحتاج تحسين" : "جيد"}</p>
    </article>`).join("");
  const prioritiesHtml = asArray(data.plan.targets).slice(0, 6).map(t => `
    <article class="item">
      <span class="tag ${t.current_score < 60 ? "urgent" : "high"}">${t.current_score < 60 ? "حرج" : "مرتفع"}</span>
      <h3>${escapeHtml(t.indicator_code)} - ${escapeHtml(t.indicator_title)}</h3>
      <p>${escapeHtml(t.domain_key || "")} | الدرجة الحالية: ${t.current_score}%</p>
      <p>${escapeHtml(t.action)}</p>
    </article>`).join("");
  container.innerHTML = `
    <article class="item protocol-head">
      <h3>${escapeHtml(data.school_name || "المدرسة")} | ${escapeHtml(data.school_level || "ثانوي")}</h3>
      <p>الدرجة الكلية: <strong>${a.overall_score || 0}%</strong> | التصنيف: <strong>${escapeHtml(a.classification_label || "")}</strong></p>
      <p>${escapeHtml(a.description || "")}</p>
      <p style="font-size:0.8rem;color:var(--muted)">${escapeHtml(data.framework || "")}</p>
    </article>
    <div class="profile-domains">${domainCardsHtml}</div>
    <div class="item-list">${prioritiesHtml}</div>`;
}

// ═══════════════════════════════════════════════════════════════════════
//  v2MergeEvidenceLibrary — يدمج مجلدات ETEC (من بيانات v2) مع الذاكرة
// ═══════════════════════════════════════════════════════════════════════
function v2MergeEvidenceLibrary(v2data, memLibrary) {
  const _DOMAIN_LABEL = {
    school_management:  "الإدارة المدرسية",
    teaching_learning:  "التعليم والتعلم",
    learning_outcomes:  "نواتج التعلم",
    school_environment: "البيئة المدرسية",
  };
  const _DOMAIN_ORDER = {
    "الإدارة المدرسية": 0, "التعليم والتعلم": 1,
    "نواتج التعلم": 2,     "البيئة المدرسية": 3,
    "متابعة الأداء الأسبوعي": 4,
  };

  // ── بناء مجلدات ETEC من خطة v2 ───────────────────────────────────────
  const v2Folders = {};
  const targets = asArray((v2data.plan || {}).targets);
  targets.forEach(t => {
    const domainAr = _DOMAIN_LABEL[t.domain_key] || t.domain_key;
    const key = `${domainAr}::${t.indicator_code}`;

    // اجمع الشواهد: المحققة ثم الناقصة ثم الكاملة كاحتياطي
    const achieved = asArray(t.achieved_evidence);
    const missing  = asArray(t.missing_evidence);
    const required = asArray(t.evidence_required);
    // استخدم القائمة الأكثر بيانات
    let evidenceItems;
    if (achieved.length + missing.length > 0) {
      evidenceItems = achieved.concat(missing);
    } else if (required.length > 0) {
      evidenceItems = required;
    } else {
      evidenceItems = [];
    }
    // بناء نص الشواهد المرقّم
    const reqText = evidenceItems.map((e, i) => `${i + 1}. ${e}`).join("\n");

    v2Folders[key] = {
      domain: domainAr,
      indicator_code: t.indicator_code || "—",
      indicator_title: t.indicator_title || "",
      required_evidence: reqText,
      evidence_items: evidenceItems,
      achieved_evidence: achieved,
      missing_evidence: missing,
      destination_folder: `app/data/evidence/{visit_id}/${domainAr}/${t.indicator_code}`,
      total: 0, suitable: 0, needs_edit: 0, insufficient: 0, reviews: [],
      _v2: true,
    };
  });

  // ── دمج الشواهد المحفوظة في الذاكرة داخل مجلدات ETEC ────────────────
  const memFolders = {};
  asArray((memLibrary || {}).folders).forEach(f => {
    const k = `${f.domain}::${f.indicator_code}`;
    memFolders[k] = f;
  });

  // دمج: مجلدات v2 + مجلدات الذاكرة (مع نقل شواهد المراجعات إلى المجلد الصح)
  const merged = { ...v2Folders };
  Object.entries(memFolders).forEach(([k, f]) => {
    // تجاهل مجلدات "متابعة الأداء" — لا علاقة لها بنظام ETEC v2
    if ((f.domain || "").includes("متابعة")) return;
    if (merged[k]) {
      // نقل الإحصاءات والمراجعات إلى المجلد المبني من v2
      merged[k].total       = f.total;
      merged[k].suitable    = f.suitable;
      merged[k].needs_edit  = f.needs_edit;
      merged[k].insufficient = f.insufficient;
      merged[k].reviews     = f.reviews || [];
      merged[k].destination_folder = f.destination_folder || merged[k].destination_folder;
    } else {
      merged[k] = f;   // مجلد ETEC من الذاكرة غير موجود في v2 حالياً
    }
  });

  // ── ضمان وجود مجلد لكل مجال ETEC الأربعة دائماً ───────────────────────
  const _etecDomainAr = ["الإدارة المدرسية","التعليم والتعلم","نواتج التعلم","البيئة المدرسية"];
  const _etecKeyMap   = {school_management:"الإدارة المدرسية",teaching_learning:"التعليم والتعلم",
                          learning_outcomes:"نواتج التعلم",school_environment:"البيئة المدرسية"};
  // بناء خريطة مجال → درجة من domain_scores
  const _domainScoreMap = {};
  asArray((v2data.analysis || {}).domain_scores).forEach(d => {
    const ar = _etecKeyMap[d.domain_key] || d.label;
    if (ar) _domainScoreMap[ar] = d.score || 0;
  });
  // أضف مجلداً عاماً لكل مجال غير موجود بعد
  _etecDomainAr.forEach(domainAr => {
    const hasFolder = Object.values(merged).some(f => f.domain === domainAr);
    if (!hasFolder) {
      const score = _domainScoreMap[domainAr];
      const scoreNote = score !== undefined ? ` — الدرجة الحالية: ${score}%` : "";
      merged[`${domainAr}::عام`] = {
        domain: domainAr, indicator_code: "—",
        indicator_title: `شواهد مجال ${domainAr}`,
        required_evidence: `ارفع الشواهد المرتبطة بهذا المجال${scoreNote}.`,
        evidence_items: [], achieved_evidence: [], missing_evidence: [],
        destination_folder: "", total: 0, suitable: 0, needs_edit: 0, insufficient: 0, reviews: [],
      };
    }
  });

  // ── ترتيب: المجالات الرسمية أولاً ────────────────────────────────────
  const sorted = Object.values(merged).sort((a, b) => {
    const oa = _DOMAIN_ORDER[a.domain] ?? 9;
    const ob = _DOMAIN_ORDER[b.domain] ?? 9;
    if (oa !== ob) return oa - ob;
    return (a.indicator_code || "").localeCompare(b.indicator_code || "");
  });

  return {
    folders: sorted,
    total_reviews: (memLibrary || {}).total_reviews || 0,
  };
}

// ═══════════════════════════════════════════════════════════════════════
//  renderDashboard — النظام القديم (للزيارات المحفوظة بدون v2)
// ═══════════════════════════════════════════════════════════════════════
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
            <strong>${escapeHtml(displayUserName(user))}</strong>
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
      const current  = Number(domain.current_score  ?? 0);
      const previous = Number(domain.previous_score ?? 0);
      const delta    = current - previous;
      const belowThreshold = current < 75;
      const deltaLabel = previous > 0
        ? `<span class="delta-pill ${delta >= 0 ? "up" : "down"}">${delta >= 0 ? "+" : ""}${delta.toFixed(1)}</span>`
        : "";
      return `
        <div class="chart-row${belowThreshold ? " below-threshold" : ""}">
          <strong>${escapeHtml(domain.label)}</strong>
          <div class="dual-bars">
            ${previous > 0 ? `<span class="previous" style="width:${previous}%"></span>` : ""}
            <span class="current" style="width:${current}%"></span>
            <span class="threshold-line" style="left:75%" title="عتبة الانطلاق 75%"></span>
          </div>
          <em>${formatScore(current)}%${belowThreshold ? " ⚠" : ""}</em>
          ${deltaLabel}
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
      <details class="folder-details" open>
        <summary>المطلوب من الشواهد (${
          asArray(folder.evidence_items).length ||
          (folder.required_evidence || "").split("\n").filter(l => l.trim()).length || 1
        } بند)</summary>
        <div class="folder-evidence-required">
          ${(() => {
            const achieved = asArray(folder.achieved_evidence);
            const missing  = asArray(folder.missing_evidence);
            const items    = asArray(folder.evidence_items);
            if (achieved.length + missing.length > 0) {
              // عرض مع ✅/❌ للمحقق والناقص
              return achieved.map((e, i) =>
                `<p class="ev-required-item ev-item-achieved"><span class="ev-check-badge">✅</span><span class="ev-num">${i+1}</span>${escapeHtml(e)}</p>`
              ).join("") + missing.map((e, i) =>
                `<p class="ev-required-item ev-item-missing"><span class="ev-check-badge">❌</span><span class="ev-num">${achieved.length+i+1}</span>${escapeHtml(e)}</p>`
              ).join("");
            } else if (items.length > 0) {
              return items.map((e, i) =>
                `<p class="ev-required-item"><span class="ev-num">${i+1}</span>${escapeHtml(e)}</p>`
              ).join("");
            } else {
              return (folder.required_evidence || "لم يحدد المطلوب لهذا البند.")
                .split("\n").filter(l => l.trim())
                .map(l => `<p class="ev-required-item">${escapeHtml(l.trim())}</p>`)
                .join("") || `<p>${escapeHtml(folder.required_evidence || "")}</p>`;
            }
          })()}
        </div>
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

// ── رفع تقرير الزيارة السابقة ───────────────────────────────────────
async function readReportPdf() {
  const input  = document.getElementById("reportPdfInput");
  const status = document.getElementById("pdfReadStatus");
  const btn    = document.getElementById("pdfReadBtn");
  if (!input || !input.files || !input.files[0]) return;

  btn.disabled = true;
  btn.innerHTML = '<span class="pdf-upload-icon">⏳</span> جاري القراءة...';
  status.textContent = "";
  status.className = "pdf-read-status";

  try {
    const payload = new FormData();
    payload.append("report", input.files[0]);
    const res = await fetch("/api/v2/parse-report", { method: "POST", body: payload });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "خطأ في القراءة");
    }
    const data = await res.json();
    const scores = data.scores || {};
    const found  = data.found  || [];

    // تعبئة اسم المدرسة
    if (data.school_name) {
      const nameInput = form.querySelector("[name=school_name]");
      if (nameInput) nameInput.value = data.school_name;
    }

    // تعيين المرحلة الدراسية تلقائياً
    if (data.school_level) {
      const levelSelect = document.getElementById("schoolLevelSelect");
      if (levelSelect) {
        levelSelect.value = data.school_level;
        updateLevelBadge();
      }
    }

    // تعبئة درجات المجالات
    const fieldMap = {
      school_management: "school_management",
      teaching_learning: "teaching_learning",
      learning_outcomes: "learning_outcomes",
      school_environment: "school_environment",
    };
    let filled = 0;
    for (const [key, fieldName] of Object.entries(fieldMap)) {
      if (scores[key] !== undefined) {
        const inp = form.querySelector(`[name=${fieldName}]`);
        if (inp) { inp.value = scores[key]; filled++; }
      }
    }

    const levelLabel = data.school_level ? ` | مرحلة: ${data.school_level}` : "";
    if (filled > 0) {
      status.innerHTML = `✅ تم استخراج <strong>${filled}</strong> مجال من التقرير وتعبئتها تلقائيًا${levelLabel}. راجعها قبل الإرسال.`;
      status.className = "pdf-read-status success";
    } else {
      status.innerHTML = "⚠️ لم يُعثر على درجات صريحة في التقرير. أدخل الأرقام يدويًا.";
      status.className = "pdf-read-status warn";
    }
  } catch (e) {
    status.textContent = "❌ " + e.message;
    status.className = "pdf-read-status error";
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="pdf-upload-icon">📄</span> رفع تقرير الزيارة السابقة';
    input.value = ""; // reset so same file can be re-selected
  }
}

function togglePreviousScores(checkbox) {
  const group  = document.getElementById("previousScoresGroup");
  const hidden = document.getElementById("hasPreviousHidden");
  if (group) group.style.display = checkbox.checked ? "" : "none";
  if (hidden) hidden.value = checkbox.checked ? "true" : "false";
}

function updateLevelBadge() {
  const select = document.getElementById("schoolLevelSelect");
  const badge  = document.getElementById("v2Badge");
  if (!select || !badge) return;
  const counts = { "ثانوي": 43, "متوسط": 49, "ابتدائي": 49 };
  const level  = select.value;
  const count  = counts[level] || 43;
  badge.textContent = `نظام التقييم المدرسي — 4 مجالات رسمية ETEC · ${count} مؤشراً | ${level}`;
}

function renderV2Result(data) {
  const existing = document.getElementById("v2ResultContainer");
  if (existing) existing.remove();

  const a    = data.analysis;
  const plan = data.plan;
  const pred = data.prediction;
  const prog = data.progress;

  const domainBars = a.domain_scores.map(d => `
    <div class="v2-domain-bar-row">
      <span class="v2-domain-name">${d.label}</span>
      <div class="v2-bar-track">
        <div class="v2-bar-fill ${d.below_threshold ? "below" : ""}" style="width:${d.score}%"></div>
      </div>
      <span class="v2-score-num">${d.score}%${d.below_threshold ? " ⚠" : ""}</span>
    </div>`).join("");

  const targetCards = plan.targets.map(t => {
    const achieved = asArray(t.achieved_evidence);
    const missing  = asArray(t.missing_evidence);
    const total    = achieved.length + missing.length;
    const pct      = total ? Math.round(achieved.length / total * 100) : 0;
    const achievedHtml = achieved.map(e =>
      `<li class="ev-achieved"><span class="ev-check">✅</span>${escapeHtml(e)}</li>`).join("");
    const missingHtml  = missing.map(e =>
      `<li class="ev-missing"><span class="ev-check">❌</span>${escapeHtml(e)}</li>`).join("");
    const checklistHtml = total > 0 ? `
      <details class="v2-evidence-checklist">
        <summary>
          <span class="ev-summary-text">الشواهد: ${achieved.length}/${total} متحقق</span>
          <div class="ev-mini-bar"><div class="ev-mini-fill" style="width:${pct}%"></div></div>
        </summary>
        <ul class="v2-evidence-list">${achievedHtml}${missingHtml}</ul>
      </details>` : "";
    return `
      <div class="v2-target-card">
        <div class="v2-target-header">
          <span class="v2-indicator-code">${t.indicator_code}</span>
          <span>${t.indicator_title}</span>
        </div>
        <div class="v2-score-arrow">${t.current_score}% → ${t.target_score}%</div>
        <div class="v2-target-action">${t.action}</div>
        ${checklistHtml}
      </div>`;
  }).join("");

  let progressHtml = "";
  if (prog) {
    const changes = Object.values(prog.domain_changes).map(v => `
      <div class="v2-domain-bar-row">
        <span class="v2-domain-name">${v.label}</span>
        <span class="v2-score-num" style="width:auto;color:${v.delta >= 0 ? "var(--teal)" : "var(--red)"}">
          ${v.delta >= 0 ? "+" : ""}${v.delta}
        </span>
        <span style="font-size:0.8rem;color:var(--muted)">${v.previous}% → ${v.current}% [${v.trend}]</span>
      </div>`).join("");
    const flags = (prog.flags || []).map(f =>
      `<p style="color:var(--amber);font-size:0.83rem">⚠ ${f}</p>`).join("");
    progressHtml = `<div class="v2-section-title">المقارنة مع الزيارة السابقة</div>${changes}${flags}`;
  }

  const simHtml = (data.simulation_questions || []).slice(0, 4).map(q => `
    <div class="v2-target-card" style="border-right-color:var(--blue)">
      <div class="v2-target-header">
        <span class="v2-indicator-code" style="background:var(--blue)">${q.indicator_code}</span>
        <span style="font-size:0.82rem">${q.question}</span>
      </div>
    </div>`).join("");

  const container = document.createElement("div");
  container.id = "v2ResultContainer";
  container.className = "v2-result-card";
  container.innerHTML = `
    <div class="v2-classification-banner">
      <div>
        <div class="v2-classification-label">${a.classification_label}</div>
        <div class="v2-overall-score">الدرجة الكلية: ${a.overall_score}%</div>
        <div style="font-size:0.8rem;color:var(--muted);margin-top:4px">${a.description}</div>
        ${data.school_name ? `<div style="font-size:0.82rem;font-weight:600;margin-top:6px">${data.school_name}${data.school_level ? ` · ${data.school_level}` : ""}</div>` : ""}
      </div>
      <div style="margin-right:auto;font-size:0.75rem;color:var(--muted);text-align:center">
        ${data.framework || "ETEC رسمي · 4 مجالات"}
      </div>
    </div>

    <div class="v2-section-title">درجات المجالات الأربعة الرسمية</div>
    ${domainBars}
    ${progressHtml}

    <div class="v2-section-title">خطة التحسين — ${plan.targets.length} أهداف بمؤشرات ETEC</div>
    ${targetCards}

    <div class="v2-section-title">أسئلة محاكاة فريق التقويم</div>
    ${simHtml}

    <div class="v2-section-title">التنبؤ بالزيارة القادمة</div>
    <div class="v2-prediction-box">
      <div class="v2-pred-item">
        <div class="v2-pred-value">${pred.overall_current}%</div>
        <div class="v2-pred-label">الحالية</div>
      </div>
      <div class="v2-pred-item">
        <div class="v2-pred-value" style="color:var(--teal)">${pred.overall_predicted}%</div>
        <div class="v2-pred-label">المتوقعة</div>
      </div>
      <div class="v2-pred-item">
        <div class="v2-pred-value" style="color:var(--blue)">${Math.round(pred.confidence * 100)}%</div>
        <div class="v2-pred-label">مستوى الثقة</div>
        <div class="v2-confidence-bar">
          <div class="v2-confidence-fill" style="width:${Math.round(pred.confidence * 100)}%"></div>
        </div>
      </div>
      <div class="v2-pred-item" style="flex:2;text-align:right">
        <div style="font-size:0.82rem;color:var(--muted)">${pred.confidence_explanation}</div>
        <div style="font-size:0.78rem;color:var(--muted);margin-top:4px">${pred.caveat}</div>
      </div>
    </div>
  `;

  form.insertAdjacentElement("afterend", container);
  container.scrollIntoView({ behavior: "smooth", block: "start" });
}
