"""
النظام المحسّن v2 — المسار الرئيسي /api/v2/
يعمل بالتوازي مع النظام القديم دون المساس به.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from improved_v2.pipeline import ImprovedEvaluationPipeline
from improved_v2.etec_reference import (
    CLASSIFICATION_LEVELS,
    DEFAULT_LEVEL,
    OFFICIAL_DOMAINS,
    SCHOOL_LEVELS,
    domain_label,
    level_indicator_count,
)

router = APIRouter(prefix="/api/v2", tags=["v2-improved"])
_pipeline = ImprovedEvaluationPipeline()


# ── صلاحيات ──────────────────────────────────────────────────────────

def _require_write(request: Request):
    from app.main import auth
    user = auth.user_from_token(request.cookies.get("school_eval_session"))
    if not user:
        raise HTTPException(status_code=401, detail="يلزم تسجيل الدخول.")
    if not user.can_write:
        raise HTTPException(status_code=403, detail="هذا المستخدم للعرض فقط ولا يملك صلاحية التعديل.")
    return user


# ── معلومات الإطار ────────────────────────────────────────────────────

@router.get("/info")
def v2_info() -> dict:
    return {
        "version": "v2",
        "framework": "ETEC تميز — الإطار الرسمي",
        "domains": {k: domain_label(k) for k in OFFICIAL_DOMAINS},
        "classification_levels": {lv: d["min_score"] for lv, d in CLASSIFICATION_LEVELS.items()},
        "school_levels": SCHOOL_LEVELS,
        "indicator_counts": {lvl: level_indicator_count(lvl) for lvl in SCHOOL_LEVELS},
    }


# ── التحليل الرئيسي ───────────────────────────────────────────────────

@router.post("/analyze")
async def v2_analyze(
    request: Request,
    school_name: str = Form("مدرسة غير مسماة"),
    school_level: str = Form(DEFAULT_LEVEL),
    school_management: float = Form(...),
    teaching_learning: float = Form(...),
    learning_outcomes: float = Form(...),
    school_environment: float = Form(...),
    prev_school_management: float = Form(0),
    prev_teaching_learning: float = Form(0),
    prev_learning_outcomes: float = Form(0),
    prev_school_environment: float = Form(0),
    has_previous: str = Form("false"),
    notes: str = Form(""),
    weeks_available: int = Form(8),
    _: object = Depends(_require_write),
) -> dict:
    # تطبيع قيمة المرحلة
    if school_level not in SCHOOL_LEVELS:
        school_level = DEFAULT_LEVEL

    domain_scores = {
        "school_management": school_management,
        "teaching_learning": teaching_learning,
        "learning_outcomes": learning_outcomes,
        "school_environment": school_environment,
    }
    previous_scores = None
    if has_previous.lower() in ("true", "1", "yes"):
        previous_scores = {
            "school_management": prev_school_management,
            "teaching_learning": prev_teaching_learning,
            "learning_outcomes": prev_learning_outcomes,
            "school_environment": prev_school_environment,
        }

    try:
        result = _pipeline.run(
            domain_scores=domain_scores,
            previous_scores=previous_scores,
            notes=notes,
            weeks_available=weeks_available,
            school_level=school_level,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"خطأ في التحليل: {exc}") from exc

    # حفظ في الذاكرة حتى تعمل الشواهد والمهام بشكل صحيح
    visit_id = _save_to_memory(school_name, school_level, domain_scores, previous_scores, notes, result)

    serialized = _serialize_result(school_name, school_level, result)
    serialized["visit_id"] = visit_id
    return serialized


# ── مطابقة الشواهد ────────────────────────────────────────────────────

@router.post("/evidence/match")
async def v2_match_evidence(
    filename: str = Form(...),
    note: str = Form(""),
    extracted_text: str = Form(""),
    _: object = Depends(_require_write),
) -> dict:
    return _pipeline.match_evidence(filename, note, extracted_text)


# ── استخراج الدرجات من PDF التقرير ───────────────────────────────────

@router.post("/parse-report")
async def v2_parse_report(
    report: UploadFile = File(...),
    _: object = Depends(_require_write),
) -> dict:
    """يستخرج اسم المدرسة ودرجات المجالات الأربعة من PDF التقرير الخارجي."""
    import re, shutil, tempfile

    if not (report.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="يرجى رفع ملف PDF فقط.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        shutil.copyfileobj(report.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        scores = _extract_etec_scores_spatial(tmp_path)
        school_name, school_level = _extract_school_name_and_level(tmp_path)

        # احتياطي: regex على النص المعاد بناؤه إذا فشل التحليل المكاني
        if len(scores) < 4:
            scores_text = _extract_etec_scores_text(tmp_path)
            for k, v in scores_text.items():
                if k not in scores:
                    scores[k] = v

        return {
            "school_name": school_name,
            "school_level": school_level,
            "scores": scores,
            "found": list(scores.keys()),
        }
    finally:
        tmp_path.unlink(missing_ok=True)


def _extract_etec_scores_spatial(pdf_path: Path) -> dict:
    """
    يستخرج الدرجات من بطاقة التقييم بالتحليل المكاني.
    تقارير ETEC تعرض المجالات الأربعة في صف أفقي RTL:
      الإدارة (أقصى يمين) ← التعليم ← نواتج ← البيئة (أقصى يسار)
    """
    import re
    try:
        import pdfplumber
    except ImportError:
        return {}

    DOMAIN_ORDER = [
        "school_management",   # أقصى اليمين
        "teaching_learning",
        "learning_outcomes",
        "school_environment",  # أقصى اليسار
    ]

    pct_re = re.compile(r"^(\d{2,3}(?:\.\d+)?)\s*%$")

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:8]:
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            # اجمع كل النسب المئوية مع مواضعها
            pcts = []
            for w in words:
                m = pct_re.match(w["text"])
                if m:
                    val = float(m.group(1))
                    if 55 <= val <= 100:
                        pcts.append((float(w["x0"]), float(w["top"]), val))

            if len(pcts) < 4:
                continue

            # ابحث عن مجموعة من 4 نسب في نطاق y ضيق (≤25 نقطة)
            pcts_sorted_y = sorted(pcts, key=lambda p: p[1])
            for i in range(len(pcts_sorted_y)):
                cluster = [pcts_sorted_y[i]]
                for j in range(i + 1, len(pcts_sorted_y)):
                    if abs(pcts_sorted_y[j][1] - pcts_sorted_y[i][1]) <= 25:
                        cluster.append(pcts_sorted_y[j])
                    else:
                        break
                # نريد بالضبط 4 نسب في نفس الصف + تمتد على عرض معقول
                if len(cluster) >= 4:
                    cluster = cluster[:4]
                    x_span = max(p[0] for p in cluster) - min(p[0] for p in cluster)
                    if x_span < 40:
                        continue
                    # رتّب من اليمين لليسار (x تنازلي) وعيّن المجالات
                    cluster_rtl = sorted(cluster, key=lambda p: -p[0])
                    return {
                        domain: round(val, 2)
                        for domain, (_, __, val) in zip(DOMAIN_ORDER, cluster_rtl)
                    }
    return {}


def _extract_school_name_and_level(pdf_path: Path) -> tuple[str, str]:
    """
    يستخرج اسم المدرسة ومرحلتها من تقرير ETEC.
    يعيد (اسم_المدرسة، المرحلة) حيث المرحلة إحدى: ثانوي، متوسط، ابتدائي.
    """
    try:
        import pdfplumber
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        return "", DEFAULT_LEVEL

    # ربط الكلمات المقلوبة في PDF بمرحلتها
    SCHOOL_TYPE_REVERSED = {
        "ﺔﻳﻮﻧﺎﺛ":   "ثانوي",    # ثانوية
        "ﺔﻴﺋﺍﺪﺘﺑﺍ": "ابتدائي",  # ابتدائية
        "ﺔﻄﺳﻮﺘﻣ":  "متوسط",    # متوسطة
        "ﺔﺳﺭﺪﻣ":   "ثانوي",    # مدرسة (افتراضي ثانوي إذا لم يُحدد)
        "ﻱﺩﺎﻌﻟﺍ":   "ثانوي",    # العادي / عادية
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx in range(min(5, len(pdf.pages))):
            page = pdf.pages[page_idx]
            words = page.extract_words(x_tolerance=3, y_tolerance=6)

            # جمّع كلمات في صفوف
            rows: dict[int, list] = {}
            for w in words:
                k = round(float(w["top"]) / 6) * 6
                rows.setdefault(k, []).append(w)

            # ابحث عن صف يحتوي على كلمة نوع مدرسة
            for row_words in sorted(rows.values(), key=lambda r: float(r[0]["top"])):
                texts = {w["text"] for w in row_words}
                matched_keys = texts & set(SCHOOL_TYPE_REVERSED.keys())
                if matched_keys:
                    detected_level = SCHOOL_TYPE_REVERSED[next(iter(matched_keys))]
                    # رتّب RTL وأعد بناء الاسم
                    row_sorted = sorted(row_words, key=lambda w: -float(w["x0"]))
                    raw = " ".join(w["text"] for w in row_sorted)
                    try:
                        reshaped = arabic_reshaper.reshape(raw)
                        display = get_display(reshaped)
                        if display.strip():
                            return display.strip(), detected_level
                    except Exception:
                        pass
    return "", DEFAULT_LEVEL


def _extract_etec_scores_text(pdf_path: Path) -> dict:
    """احتياطي: regex على النص المعاد بناؤه بـ arabic_reshaper."""
    import re
    try:
        import pdfplumber
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:
        return {}

    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:10]:
            raw = page.extract_text() or ""
            try:
                reshaped = arabic_reshaper.reshape(raw)
                full_text += get_display(reshaped) + "\n"
            except Exception:
                full_text += raw + "\n"

    PATTERNS = {
        "school_management": [
            r"الإدارة\s+المدرسية[^\d]*?(\d{2,3}(?:\.\d+)?)\s*%",
            r"القيادة\s+المدرسية[^\d]*?(\d{2,3}(?:\.\d+)?)\s*%",
        ],
        "teaching_learning": [
            r"التعليم\s+والتعلم[^\d]*?(\d{2,3}(?:\.\d+)?)\s*%",
        ],
        "learning_outcomes": [
            r"نواتج\s+التعلم[^\d]*?(\d{2,3}(?:\.\d+)?)\s*%",
        ],
        "school_environment": [
            r"البيئة\s+المدرسية[^\d]*?(\d{2,3}(?:\.\d+)?)\s*%",
        ],
    }
    scores: dict[str, float] = {}
    for domain, patterns in PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, full_text)
            if m:
                val = float(m.group(1))
                if 55 <= val <= 100:
                    scores[domain] = round(val, 1)
                    break
    return scores


# ── حفظ في الذاكرة ───────────────────────────────────────────────────

def _save_to_memory(
    school_name: str,
    school_level: str,
    domain_scores: dict,
    previous_scores: dict | None,
    notes: str,
    result: dict,
) -> str:
    """يحفظ نتيجة v2 كـ VisitRecord مبسط حتى تعمل الشواهد والمهام."""
    try:
        from app.main import memory, live_council
        from app.core.models import (
            DomainScore, ImprovementAction, PredictionResult,
            PredictionScenario, SimulationQuestion, TeamTask,
            Weakness, VisitRecord,
        )

        # المجالات الأربعة الرسمية ETEC فقط — بدون تعيين على النظام القديم
        ETEC_DOMAINS = {
            "school_management":  "الإدارة المدرسية",
            "teaching_learning":  "التعليم والتعلم",
            "learning_outcomes":  "نواتج التعلم",
            "school_environment": "البيئة المدرسية",
        }

        prev = previous_scores or domain_scores
        domains = [
            DomainScore(
                key=dk,
                label=label,
                previous_score=prev.get(dk, 0),
                current_score=domain_scores.get(dk, 0),
                gap=round(domain_scores.get(dk, 0) - prev.get(dk, 0), 1),
                evidence=[],
            )
            for dk, label in ETEC_DOMAINS.items()
        ]

        # تحويل نقاط الضعف — pipeline يُعيد كائنات Python لا قواميس
        analysis = result["analysis"]
        weaknesses = []
        severity_map = {"school_management": "high", "teaching_learning": "medium",
                        "learning_outcomes": "high", "school_environment": "medium"}
        ETEC_LABELS = {
            "school_management": "الإدارة المدرسية",
            "teaching_learning": "التعليم والتعلم",
            "learning_outcomes": "نواتج التعلم",
            "school_environment": "البيئة المدرسية",
        }
        for w in analysis.get("weaknesses", [])[:6]:
            dk = w.domain_key
            weaknesses.append(Weakness(
                domain=dk,   # مفتاح ETEC الإنجليزي
                title=w.indicator.title,
                severity=severity_map.get(dk, "medium"),
                evidence=f"الدرجة: {w.score}% — الفجوة: {w.gap} نقطة",
                root_cause="بناءً على تحليل ETEC الرسمي",
                impact=w.impact,
            ))

        # تحويل خطة التحسين
        plan_data = result["plan"]
        plan = []
        priority_map = {"learning_outcomes": "urgent", "school_management": "high",
                        "teaching_learning": "high", "school_environment": "medium"}
        _weeks = result["prediction"].get("weeks_available", 8)
        for t in plan_data.get("targets", [])[:6]:
            dk = t.domain_key
            plan.append(ImprovementAction(
                title=t.indicator.title,
                domain=dk,   # مفتاح ETEC الإنجليزي
                priority=priority_map.get(dk, "high"),
                owner_role="مدير المدرسة",
                due_in_days=min((_weeks or 8) * 7, 120),
                expected_gain=min(round(t.target_score - t.current_score, 1), 20.0),
                success_metric=f"رفع درجة المؤشر {t.indicator.code} من {t.current_score}% إلى {t.target_score}%",
                steps=(t.evidence_required[:3] if t.evidence_required else []) or ["توثيق الوضع الحالي", "تنفيذ الإجراء", "قياس الأثر"],
            ))

        # التنبؤ
        pred_data = result["prediction"]
        prediction = PredictionResult(
            expected_score=pred_data["overall_predicted"],
            confidence=pred_data["confidence"],
            scenarios=[
                PredictionScenario(name="بدون تحسين", score=pred_data["overall_current"],
                                   explanation="استمرار الوضع الحالي"),
                PredictionScenario(name="تحسين متوسط", score=pred_data["overall_predicted"],
                                   explanation="تنفيذ جزئي للخطة"),
                PredictionScenario(name="تنفيذ كامل",
                                   score=min(pred_data["overall_predicted"] + 5, 100),
                                   explanation="تنفيذ كامل وتوثيق شامل"),
            ],
            fastest_actions=plan[:3],
            learning_notes=[pred_data["confidence_explanation"]],
        )

        # أسئلة المحاكاة
        simulation = []
        for q in result.get("simulation_questions", [])[:5]:
            dk = next(
                (t.domain_key for t in plan_data.get("targets", [])
                 if t.indicator.code == q.get("indicator_code")), "learning_outcomes"
            )
            simulation.append(SimulationQuestion(
                domain=dk,   # مفتاح ETEC الإنجليزي
                question=q["question"],
                expected_evidence=", ".join(q.get("expected_evidence", [])[:2]),
                risk_level="high" if "أساسي" in q.get("question", "") else "medium",
            ))

        visit = VisitRecord(
            school_name=school_name,
            school_level=school_level,
            previous_report_excerpt=notes[:500] or "تحليل v2 — ETEC رسمي",
            current_status=notes or "تحليل مدرسي بالنظام المحسّن v2",
            domains=domains,
            weaknesses=weaknesses,
            plan=plan,
            tasks=[],
            simulation=simulation,
            prediction=prediction,
        )
        saved = memory.save_visit(visit)
        memory.save_council_event(live_council.analysis_event(saved))
        return saved.id
    except Exception as _exc:
        import traceback, logging
        logging.getLogger("v2").error("_save_to_memory failed: %s", traceback.format_exc())
        return "v2-unsaved"


# ── تسلسل النتيجة ─────────────────────────────────────────────────────

def _serialize_result(school_name: str, school_level: str, result: dict) -> dict:
    a = result["analysis"]
    plan = result["plan"]
    pred = result["prediction"]
    prog = result.get("progress")

    return {
        "school_name": school_name,
        "school_level": school_level,
        "framework": result["framework"],
        "analysis": {
            "overall_score": a["overall_score"],
            "classification": a["classification"],
            "classification_label": a["classification_label"],
            "description": a["description"],
            "domain_scores": [
                {"domain_key": d.domain_key, "label": d.label,
                 "score": d.score, "below_threshold": d.score < 75}
                for d in a["domain_scores"]
            ],
            "weaknesses": [
                {"domain_key": w.domain_key, "indicator_code": w.indicator.code,
                 "indicator_title": w.indicator.title, "score": w.score,
                 "gap": w.gap, "impact": w.impact}
                for w in a["weaknesses"]
            ],
            "notes_summary": a["notes_summary"],
        },
        "progress": {
            "overall_previous": prog["overall_previous"],
            "overall_current": prog["overall_current"],
            "overall_delta": prog["overall_delta"],
            "previous_classification": prog["previous_classification"],
            "current_classification": prog["current_classification"],
            "domain_changes": prog["domain_changes"],
            "flags": prog["flags"],
        } if prog else None,
        "plan": {
            "summary": plan["summary"],
            "critical_domains": plan["critical_domains"],
            "weeks_to_visit_estimate": plan["weeks_to_visit_estimate"],
            "targets": [
                {"rank": t.rank, "domain_key": t.domain_key,
                 "indicator_code": t.indicator.code, "indicator_title": t.indicator.title,
                 "current_score": t.current_score, "target_score": t.target_score,
                 "action": t.action,
                 "evidence_required": t.evidence_required,
                 "achieved_evidence": t.achieved_evidence,
                 "missing_evidence": t.missing_evidence}
                for t in plan["targets"]
            ],
        },
        "simulation_questions": result["simulation_questions"],
        "prediction": {
            "overall_current": pred["overall_current"],
            "overall_predicted": pred["overall_predicted"],
            "overall_gain": pred["overall_gain"],
            "current_classification": pred["current_classification"],
            "predicted_classification": pred["predicted_classification"],
            "confidence": pred["confidence"],
            "confidence_explanation": pred["confidence_explanation"],
            "weeks_available": pred["weeks_available"],
            "caveat": pred["caveat"],
            "domain_predictions": pred["domain_predictions"],
            "scenarios": _build_scenarios(pred),
        },
    }


def _build_scenarios(pred: dict) -> list:
    """يولّد ثلاثة سيناريوهات من نتيجة التنبؤ."""
    current   = pred.get("overall_current", 0)
    predicted = pred.get("overall_predicted", 0)
    gain      = predicted - current
    return [
        {
            "name": "السيناريو المتفائل",
            "score": round(min(predicted + gain * 0.3, 100), 1),
            "explanation": "تنفيذ الخطة بالكامل مع التزام مثالي من الفريق.",
        },
        {
            "name": "السيناريو الواقعي",
            "score": round(predicted, 1),
            "explanation": pred.get("confidence_explanation", "تنفيذ طبيعي للخطة."),
        },
        {
            "name": "السيناريو المتحفظ",
            "score": round(max(current + gain * 0.4, current), 1),
            "explanation": "تنفيذ جزئي للخطة أو ظروف طارئة تؤخر التنفيذ.",
        },
    ]
