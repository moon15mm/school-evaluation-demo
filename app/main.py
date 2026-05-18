from __future__ import annotations

import shutil
import zipfile
import os
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.auth import AuthManager, User
from app.core.memory import SchoolMemory
from app.core.impact_pdf import build_impact_pdf
from app.core.models import AnalysisRequest, AnalysisResponse, ImpactRecord, OutcomeUpdate, TaskStatusUpdate
from app.core.pdf_tools import extract_pdf_text
from app.core.pipeline import EvaluationPipeline
from app.core.external_evaluation import ExternalEvaluationAdvisor
from app.core.evidence_pdf import build_evidence_index_pdf
from app.core.impact_agent import ImpactFileAgent
from app.core.performance_followup import performance_followup_reference
from app.core.report_reference import build_school_report_profile
from app.core.secretariat_agents import EvidenceSecretariat
from app.core.live_council import LiveAgentCouncil
from app.core.demo_seed import seed_demo_data
from app.routers.v2 import router as v2_router

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
REPORTS_DIR = DATA_DIR / "reports"
EXECUTION_DIR = DATA_DIR / "execution"
EVIDENCE_DIR = DATA_DIR / "evidence"
IMPACT_DIR = DATA_DIR / "impact"
MEMORY_PATH = DATA_DIR / "school_memory.json"
USERS_PATH = DATA_DIR / "users.json"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
EXECUTION_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
IMPACT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Autonomous School Evaluation & Improvement System")
app.include_router(v2_router)
auth = AuthManager(USERS_PATH)
memory = SchoolMemory(MEMORY_PATH)
pipeline = EvaluationPipeline(memory, REPORTS_DIR, EXECUTION_DIR)
secretariat = EvidenceSecretariat()
external_advisor = ExternalEvaluationAdvisor()
impact_agent = ImpactFileAgent()
live_council = LiveAgentCouncil()

DEFAULT_REPORT_TEXT = (
    "مدرسة المستقبل الثانوية - تقرير تقويم خارجي افتراضي. "
    "تقرير تقويم خارجي افتراضي مشابه لتقارير المدارس: الدرجة العامة 73%، مستوى الانطلاق، "
    "مع أولويات في نواتج التعلم، الاختبارات التحصيلية، الشراكة المجتمعية، البيئة المدرسية، "
    "الصيانة، السلامة، التقويم الصفي، والمهارات الرقمية."
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.on_event("startup")
def seed_online_demo() -> None:
    if os.getenv("DEMO_MODE", "").strip().lower() in {"1", "true", "yes", "on"}:
        seed_demo_data(memory, pipeline, EVIDENCE_DIR, IMPACT_DIR, live_council)


PUBLIC_API_PATHS = {"/api/health", "/api/auth/login", "/api/auth/me", "/api/auth/logout"}


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path not in PUBLIC_API_PATHS:
        user = auth.user_from_token(request.cookies.get("school_eval_session"))
        if not user:
            return JSONResponse({"detail": "يلزم تسجيل الدخول."}, status_code=401)
    return await call_next(request)


def current_user(request: Request) -> User:
    user = auth.user_from_token(request.cookies.get("school_eval_session"))
    if not user:
        raise HTTPException(status_code=401, detail="يلزم تسجيل الدخول.")
    return user


def require_write(user: User = Depends(current_user)) -> User:
    if not user.can_write:
        raise HTTPException(status_code=403, detail="هذا المستخدم للعرض فقط ولا يملك صلاحية التعديل.")
    return user


def require_user_admin(user: User = Depends(current_user)) -> User:
    if not user.can_manage_users:
        raise HTTPException(status_code=403, detail="إدارة المستخدمين متاحة للمدير فقط.")
    return user


def require_clear_permission(user: User = Depends(current_user)) -> User:
    if not user.can_clear_data:
        raise HTTPException(status_code=403, detail="تفريغ البيانات متاح للمدير فقط.")
    return user


@app.get("/")
def index() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "system": "Autonomous School Evaluation & Improvement System"}


@app.post("/api/auth/login")
async def login(request: Request, response: Response) -> dict:
    payload = await request.json()
    user = auth.authenticate(str(payload.get("username", "")), str(payload.get("password", "")))
    if not user:
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة.")
    token = auth.create_session(user.username)
    response.set_cookie("school_eval_session", token, httponly=True, samesite="lax")
    return {"user": user.public()}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    auth.logout(request.cookies.get("school_eval_session"))
    response.delete_cookie("school_eval_session")
    return {"ok": True}


@app.get("/api/auth/me")
def me(request: Request) -> dict:
    user = auth.user_from_token(request.cookies.get("school_eval_session"))
    return {"authenticated": bool(user), "user": user.public() if user else None}


@app.get("/api/auth/users")
def list_users(_: User = Depends(require_user_admin)) -> dict:
    return {"users": auth.list_users()}


@app.post("/api/auth/users")
async def create_user(request: Request, _: User = Depends(require_user_admin)) -> dict:
    payload = await request.json()
    try:
        user = auth.add_user(
            username=str(payload.get("username", "")),
            password=str(payload.get("password", "")),
            display_name=str(payload.get("display_name", "")),
            role=str(payload.get("role", "user")),
            can_write=bool(payload.get("can_write", True)),
            can_manage_users=bool(payload.get("can_manage_users", False)),
            can_clear_data=bool(payload.get("can_clear_data", False)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user": user.public(), "users": auth.list_users()}


@app.delete("/api/auth/users/{username}")
def delete_user(username: str, _: User = Depends(require_user_admin)) -> dict:
    try:
        auth.delete_user(username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": username, "users": auth.list_users()}


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(
    current_status: str = Form(...),
    school_name: str = Form(""),
    team_members: str = Form(""),
    use_default_report: bool = Form(False),
    previous_report: UploadFile | None = File(None),
    _: User = Depends(require_write),
) -> AnalysisResponse:
    latest = memory.latest_visit()
    report_profile_override = None
    safe_name = None
    if previous_report and previous_report.filename:
        if not previous_report.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="يرجى رفع ملف PDF فقط.")
        safe_name = Path(previous_report.filename).name
        upload_path = UPLOADS_DIR / safe_name
        with upload_path.open("wb") as buffer:
            shutil.copyfileobj(previous_report.file, buffer)
        pdf_text = extract_pdf_text(upload_path)
        extracted_profile = build_school_report_profile(pdf_text)
        if not school_name.strip() and extracted_profile:
            school_name = extracted_profile.school_name
    else:
        if use_default_report:
            pdf_text = DEFAULT_REPORT_TEXT
            safe_name = "default-similar-previous-visit.pdf"
            report_profile_override = build_school_report_profile(DEFAULT_REPORT_TEXT)
            if not school_name.strip() and report_profile_override:
                school_name = report_profile_override.school_name
        elif latest and latest.report_profile:
            pdf_text = latest.previous_report_excerpt
            safe_name = latest.pdf_filename
            report_profile_override = latest.report_profile
            if not school_name.strip():
                school_name = latest.report_profile.school_name
        else:
            raise HTTPException(status_code=400, detail="ارفع تقرير الزيارة السابقة أول مرة، وبعدها سيحفظه النظام في الذاكرة.")
    if not school_name.strip():
        school_name = "مدرسة غير مسماة"
    team = [item.strip() for item in team_members.replace("\n", ",").split(",") if item.strip()]
    request = AnalysisRequest(school_name=school_name.strip(), current_status=current_status, team_members=team)
    visit = pipeline.run(request, pdf_text, safe_name, report_profile_override=report_profile_override)
    memory.save_council_event(live_council.analysis_event(visit))
    return AnalysisResponse(visit=visit, report_url=f"/api/reports/{visit.id}")


@app.get("/api/visits")
def visits() -> dict:
    items = memory.all_visits()
    return {"visits": [item.model_dump() for item in items]}


@app.get("/api/visits/{visit_id}")
def visit_detail(visit_id: str) -> dict:
    for visit in memory.all_visits():
        if visit.id == visit_id:
            return visit.model_dump()
    raise HTTPException(status_code=404, detail="Visit not found")


@app.post("/api/visits/{visit_id}/outcome")
def update_outcome(visit_id: str, outcome: OutcomeUpdate, _: User = Depends(require_write)) -> dict:
    visit = memory.update_outcome(visit_id, outcome)
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")
    return {"visit": visit.model_dump(), "learning_profile": memory.learning_profile()}


@app.get("/api/memory")
def memory_profile() -> dict:
    return {"learning_profile": memory.learning_profile(), "visits": [item.model_dump() for item in memory.latest_visits(10)]}


def _visit_dashboard(visit) -> dict:
    today = date.today().isoformat()
    tasks = visit.tasks
    total = len(tasks)
    done = len([task for task in tasks if task.status == "done"])
    in_progress = len([task for task in tasks if task.status == "in_progress"])
    new = len([task for task in tasks if task.status == "new"])
    overdue = [
        task for task in tasks
        if task.status != "done" and task.due_date < today
    ]
    completion = round((done / total) * 100, 1) if total else 0
    domains = [
        {
            "label": domain.label,
            "previous": domain.previous_score,
            "current": domain.current_score,
            "gap": domain.gap,
        }
        for domain in visit.domains
    ]
    return {
        "visit_id": visit.id,
        "school_name": visit.school_name,
        "created_at": visit.created_at,
        "expected_score": visit.prediction.expected_score,
        "task_total": total,
        "task_done": done,
        "task_in_progress": in_progress,
        "task_new": new,
        "task_overdue": len(overdue),
        "completion": completion,
        "domains": domains,
        "overdue_tasks": [task.model_dump() for task in overdue],
        "report_url": f"/api/reports/{visit.id}" if visit.report_path else None,
        "execution_url": visit.execution_pack.download_url if visit.execution_pack else None,
    }


def _evidence_library(visit=None) -> dict:
    visit_id = visit.id if visit else None
    reviews = memory.latest_evidence_reviews(300)
    if visit_id:
        reviews = [review for review in reviews if review.visit_id == visit_id]
    folders: dict[str, dict] = {}
    if visit:
        _seed_required_evidence_folders(folders, visit)
    for review in reviews:
        key = f"{review.suggested_domain}::{review.suggested_indicator_code or 'unclassified'}"
        folder = folders.setdefault(
            key,
            {
                "domain": review.suggested_domain,
                "indicator_code": review.suggested_indicator_code or "غير محدد",
                "indicator_title": review.suggested_indicator_title or "غير محدد",
                "required_evidence": "اربط الشاهد بالمؤشر واكتب ملاحظة واضحة عن التاريخ والمصدر والأثر.",
                "destination_folder": review.destination_folder,
                "total": 0,
                "suitable": 0,
                "needs_edit": 0,
                "insufficient": 0,
                "reviews": [],
            },
        )
        folder["total"] += 1
        folder[review.suitability] = folder.get(review.suitability, 0) + 1
        folder["reviews"].append(review.model_dump())
    # رتّب: المجالات الرسمية الأربعة أولاً، ثم متابعة الأداء، ثم البقية
    _DOMAIN_ORDER = {
        "الإدارة المدرسية": 0, "التعليم والتعلم": 1,
        "نواتج التعلم": 2, "البيئة المدرسية": 3,
        "متابعة الأداء الأسبوعي": 4,
    }
    ordered = sorted(
        folders.values(),
        key=lambda f: (_DOMAIN_ORDER.get(f["domain"], 9), f["indicator_code"])
    )
    return {"folders": ordered, "total_reviews": len(reviews)}


def _seed_required_evidence_folders(folders: dict[str, dict], visit) -> None:
    """
    يملأ المكتبة بالمجلدات المطلوبة:
    • زيارات v2 (school_level محدد): مؤشرات ETEC الرسمية من خطة التحسين
    • زيارات قديمة: مؤشرات تقرير الزيارة + مؤشرات متابعة الأداء الأسبوعي
    • دائماً: قسم متابعة الأداء الأسبوعي كمرجع منفصل
    """
    school_level = getattr(visit, "school_level", None) or ""

    if school_level:
        # ── زيارة v2: أنشئ مجلدات من خطة التحسين ETEC ───────────────
        _seed_etec_evidence_folders(folders, visit)
    else:
        # ── زيارة قديمة: مؤشرات تقرير الزيارة ───────────────────────
        if visit.report_profile:
            for indicator in [*visit.report_profile.improvement_priorities,
                               *visit.report_profile.strengths]:
                key = f"{indicator.domain}::{indicator.code}"
                folders.setdefault(key, {
                    "domain": indicator.domain,
                    "indicator_code": indicator.code,
                    "indicator_title": indicator.title,
                    "required_evidence": indicator.required_response,
                    "destination_folder": str(EVIDENCE_DIR / visit.id / _slug(indicator.domain) / _slug(indicator.code)),
                    "total": 0, "suitable": 0, "needs_edit": 0,
                    "insufficient": 0, "reviews": [],
                })

    # ── مؤشرات متابعة الأداء الأسبوعي — للزيارات القديمة فقط (v1) ───
    if not school_level:
        for item in performance_followup_reference()["indicators"]:
            code = f"متابعة-{item['number']}"
            domain_label = "متابعة الأداء الأسبوعي"
            key = f"{domain_label}::{code}"
            folders.setdefault(key, {
                "domain": domain_label,
                "indicator_code": code,
                "indicator_title": item["question"],
                "required_evidence": item["required_evidence"],
                "destination_folder": str(EVIDENCE_DIR / visit.id / "متابعة_الأداء" / _slug(code)),
                "total": 0, "suitable": 0, "needs_edit": 0,
                "insufficient": 0, "reviews": [],
            })


def _seed_etec_evidence_folders(folders: dict[str, dict], visit) -> None:
    """يملأ المجلدات من مؤشرات ETEC الرسمية — يستخرج رمز المؤشر مباشرةً من success_metric."""
    import re as _re
    try:
        from improved_v2.etec_reference import (
            get_indicator_by_code,
            get_indicators_for_level,
            DEFAULT_LEVEL,
        )
        _ETEC_OK = True
    except ImportError:
        _ETEC_OK = False

    _DOMAIN_AR = {
        "school_management":  "الإدارة المدرسية",
        "teaching_learning":  "التعليم والتعلم",
        "learning_outcomes":  "نواتج التعلم",
        "school_environment": "البيئة المدرسية",
    }
    school_level = getattr(visit, "school_level", DEFAULT_LEVEL if _ETEC_OK else "ثانوي") or "ثانوي"

    _CODE_RE = _re.compile(r'\d+-\d+-\d+-\d+')

    if _ETEC_OK:
        for action in visit.plan:
            # ابحث عن رمز المؤشر في success_metric أو title
            code_match = _CODE_RE.search(action.success_metric or "") \
                      or _CODE_RE.search(action.title or "")
            if code_match:
                ind = get_indicator_by_code(code_match.group(), school_level)
            else:
                ind = None

            # احتياطي: مطابقة بالعنوان
            if ind is None:
                all_ind = get_indicators_for_level(school_level)
                ind = next(
                    (i for i in all_ind if i.title == action.title),
                    None
                )
            if ind is None:
                continue

            domain_ar = _DOMAIN_AR.get(ind.domain, ind.domain)
            key = f"{domain_ar}::{ind.code}"
            evidence_text = "\n".join(
                f"{i+1}. {ev}" for i, ev in enumerate(ind.evidence_required)
            )
            folders.setdefault(key, {
                "domain": domain_ar,
                "indicator_code": ind.code,
                "indicator_title": ind.title,
                "required_evidence": evidence_text or action.success_metric,
                "destination_folder": str(EVIDENCE_DIR / visit.id / _slug(domain_ar) / _slug(ind.code)),
                "total": 0, "suitable": 0, "needs_edit": 0,
                "insufficient": 0, "reviews": [],
                "evidence_items": list(ind.evidence_required),
            })

    # إذا لم تتوفر ETEC أو لا توجد مؤشرات بعد — ابنِ مجلداً لكل مجال رسمي
    if not [f for f in folders if any(v in f for v in _DOMAIN_AR.values())]:
        for domain_ar in _DOMAIN_AR.values():
            key = f"{domain_ar}::عام"
            folders.setdefault(key, {
                "domain": domain_ar,
                "indicator_code": "—",
                "indicator_title": f"شواهد مجال {domain_ar}",
                "required_evidence": "ارفع الشواهد المرتبطة بهذا المجال.",
                "destination_folder": str(EVIDENCE_DIR / visit.id / _slug(domain_ar) / "عام"),
                "total": 0, "suitable": 0, "needs_edit": 0,
                "insufficient": 0, "reviews": [],
            })


def _slug(value: str) -> str:
    import re

    return re.sub(r"[^\w\u0600-\u06FF]+", "_", str(value), flags=re.UNICODE).strip("_") or "item"


def _clear_directory_contents(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    base = path.resolve()
    for item in path.iterdir():
        resolved = item.resolve()
        if base not in [resolved, *resolved.parents]:
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink(missing_ok=True)


@app.post("/api/admin/clear-data")
def clear_data(_: User = Depends(require_clear_permission)) -> dict:
    memory.clear_operational_data()
    for folder in [UPLOADS_DIR, REPORTS_DIR, EXECUTION_DIR, EVIDENCE_DIR, IMPACT_DIR]:
        _clear_directory_contents(folder)
    return {"ok": True, "message": "تم تفريغ بيانات الزيارات والشواهد والأثر والتقارير مع الإبقاء على المستخدمين."}


def _impact_level(rate: float, files_count: int, statistics: str, test_results: str, testimonials: str) -> str:
    score = 0
    if rate >= 20:
        score += 2
    elif rate >= 8:
        score += 1
    if files_count:
        score += 1
    if statistics.strip():
        score += 1
    if test_results.strip():
        score += 1
    if testimonials.strip():
        score += 1
    if score >= 5:
        return "golden"
    if score >= 3:
        return "strong"
    if score >= 1:
        return "clear"
    return "limited"


def _impact_validation_notes(record: ImpactRecord) -> list[str]:
    notes = []
    if not record.stored_files:
        notes.append("أضف صورة أو ملف PDF يدعم قصة الأثر.")
    if not record.statistics.strip():
        notes.append("أضف إحصاءات رقمية واضحة حتى لا يبدو الأثر وصفياً فقط.")
    if not record.test_results.strip():
        notes.append("اربط الأثر بنتيجة اختبار أو قياس قبلي/بعدي.")
    if record.improvement_rate < 8:
        notes.append("نسبة التحسن محدودة؛ يحتاج الملف إلى مدة متابعة أو عينة أوضح.")
    if not notes:
        notes.append("قصة الأثر مكتملة العناصر وجاهزة للعرض بعد المراجعة النهائية.")
    return notes


def _impact_records_for_visit(visit_id: str | None, limit: int = 200) -> list[ImpactRecord]:
    records = memory.latest_impact_records(limit)
    if visit_id:
        records = [record for record in records if record.visit_id == visit_id]
    return records


def _build_impact_package(visit_id: str) -> Path:
    records = _impact_records_for_visit(visit_id, 500)
    if not records:
        raise HTTPException(status_code=404, detail="لا توجد قصص أثر محفوظة لبناء الملف الذهبي.")
    root = IMPACT_DIR / visit_id
    root.mkdir(parents=True, exist_ok=True)
    build_impact_pdf(records, root / "الملف_الذهبي_ملف_الأثر.pdf")
    zip_path = IMPACT_DIR / f"golden-impact-file-{visit_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        pdf_path = root / "الملف_الذهبي_ملف_الأثر.pdf"
        archive.write(pdf_path, arcname=pdf_path.name)
        for record in records:
            for file_path in record.stored_files:
                file = Path(file_path)
                if file.exists() and file.is_file():
                    archive.write(file, arcname=Path("مرفقات_الأثر") / _slug(record.title) / file.name)
    return zip_path


def _build_evidence_dossier(visit_id: str) -> Path:
    root = EVIDENCE_DIR / visit_id
    if not root.exists():
        raise HTTPException(status_code=404, detail="لا توجد شواهد مؤرشفة لهذه الزيارة.")
    relevant = [review for review in memory.latest_evidence_reviews(500) if review.visit_id == visit_id]
    if not relevant:
        raise HTTPException(status_code=404, detail="لا توجد شواهد محفوظة لبناء الملف الموحد.")
    visit = next((item for item in memory.all_visits() if item.id == visit_id), None)
    folders = _evidence_library(visit).get("folders", []) if visit else []
    build_evidence_index_pdf(relevant, root / "ملف_الشواهد_الموحد.pdf", folders=folders)
    zip_path = EVIDENCE_DIR / f"evidence-dossier-{visit_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in root.rglob("*"):
            relative_path = file.relative_to(root)
            if relative_path.name == "evidence_dossier_unified.pdf":
                continue
            if any(part.startswith("_dossier_parts_") for part in relative_path.parts):
                continue
            if file.is_file():
                archive.write(file, arcname=relative_path)
    return zip_path


@app.get("/api/workspace")
def workspace() -> dict:
    latest = memory.latest_visit()
    active_visit = latest.model_dump() if latest else None
    if latest and not latest.external_readiness:
        active_visit["external_readiness"] = external_advisor.build(
            latest.domains,
            latest.weaknesses,
            latest.plan,
            latest.current_status,
            latest.report_profile,
        ).model_dump()
    return {
        "has_memory": latest is not None,
        "active_visit": active_visit,
        "dashboard": _visit_dashboard(latest) if latest else None,
        "learning_profile": memory.learning_profile(),
        "evidence_reviews": [item.model_dump() for item in memory.latest_evidence_reviews(12)],
        "evidence_library": _evidence_library(latest),
        "impact_records": [item.model_dump() for item in _impact_records_for_visit(latest.id if latest else None, 30)],
        "impact_advice": impact_agent.advise(latest, len(_impact_records_for_visit(latest.id, 200))) if latest else None,
        "council_events": [item.model_dump() for item in memory.latest_council_events(latest.id if latest else None, 30)],
    }


@app.get("/api/evidence/reviews")
def evidence_reviews() -> dict:
    return {"reviews": [item.model_dump() for item in memory.latest_evidence_reviews(30)]}


@app.get("/api/council/events")
def council_events() -> dict:
    latest = memory.latest_visit()
    return {"events": [item.model_dump() for item in memory.latest_council_events(latest.id if latest else None, 50)]}


@app.get("/api/evidence/library")
def evidence_library() -> dict:
    latest = memory.latest_visit()
    return _evidence_library(latest)


@app.post("/api/evidence/review")
async def review_evidence(
    note: str = Form(""),
    evidence_file: UploadFile = File(...),
    _: User = Depends(require_write),
) -> dict:
    latest = memory.latest_visit()
    if not latest:
        raise HTTPException(
            status_code=400,
            detail="شغّل التحليل أو ارفع تقرير الزيارة السابقة أولًا حتى يعرف النظام أين يضع الشاهد.",
        )
    if not evidence_file.filename:
        raise HTTPException(status_code=400, detail="اختر ملف شاهد أو صورة قبل الإرسال.")

    safe_name = Path(evidence_file.filename).name
    inbox = EVIDENCE_DIR / "_inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    incoming = inbox / safe_name
    with incoming.open("wb") as buffer:
        shutil.copyfileobj(evidence_file.file, buffer)

    # استخدام مرحلة المدرسة إن وُجدت في الزيارة
    _school_level = getattr(latest, "school_level", "ثانوي") or "ثانوي"
    review = secretariat.review_and_archive(incoming, safe_name, note, latest, EVIDENCE_DIR, _school_level)
    memory.save_evidence_review(review)
    event = memory.save_council_event(live_council.evidence_event(latest, review))
    return {
        "review": review.model_dump(),
        "recent": [item.model_dump() for item in memory.latest_evidence_reviews(12)],
        "library": _evidence_library(latest),
        "council_event": event.model_dump(),
        "council_events": [item.model_dump() for item in memory.latest_council_events(latest.id, 30)],
    }


@app.post("/api/evidence/dossier/build")
def build_evidence_dossier(_: User = Depends(require_write)) -> dict:
    latest = memory.latest_visit()
    if not latest:
        raise HTTPException(status_code=400, detail="لا توجد زيارة نشطة لبناء ملف الشواهد.")
    path = _build_evidence_dossier(latest.id)
    return {"download_url": f"/api/evidence/dossier/{latest.id}/download", "filename": path.name}


@app.get("/api/evidence/dossier/{visit_id}/download")
def evidence_dossier_download(visit_id: str) -> FileResponse:
    zip_path = _build_evidence_dossier(visit_id)
    return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)


@app.get("/api/evidence/file/{review_id}")
def evidence_file(review_id: str) -> FileResponse:
    for review in memory.latest_evidence_reviews(200):
        if review.id == review_id:
            path = Path(review.stored_path)
            if path.exists():
                return FileResponse(path, filename=path.name)
            break
    raise HTTPException(status_code=404, detail="Evidence file not found")


@app.get("/api/evidence/review/{review_id}/card")
def evidence_card(review_id: str) -> FileResponse:
    for review in memory.latest_evidence_reviews(500):
        if review.id == review_id:
            path = Path(review.destination_folder) / f"بطاقة_الشاهد_{review.id}.pdf"
            from app.core.evidence_pdf import build_evidence_card_pdf

            build_evidence_card_pdf(review, "", Path(review.destination_folder))
            if path.exists():
                return FileResponse(path, media_type="application/pdf", filename=path.name)
            break
    raise HTTPException(status_code=404, detail="Evidence card not found")


@app.get("/api/evidence/review/{review_id}/decision")
def evidence_decision(review_id: str) -> FileResponse:
    for review in memory.latest_evidence_reviews(500):
        if review.id == review_id:
            path = Path(review.destination_folder) / f"قرار_السكرتارية_{review.id}.pdf"
            from app.core.evidence_pdf import build_secretariat_decision_pdf

            build_secretariat_decision_pdf(review, Path(review.destination_folder))
            if path.exists():
                return FileResponse(path, media_type="application/pdf", filename=path.name)
            break
    raise HTTPException(status_code=404, detail="Evidence decision not found")


@app.delete("/api/evidence/review/{review_id}")
def delete_evidence_review(review_id: str, _: User = Depends(require_write)) -> dict:
    review = memory.delete_evidence_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="الشاهد غير موجود.")
    stored_path = Path(review.stored_path)
    if stored_path.exists():
        stored_path.unlink()
    folder = Path(review.destination_folder)
    for generated in folder.glob(f"*{review.id}.pdf"):
        generated.unlink(missing_ok=True)
    latest = memory.latest_visit()
    return {
        "deleted": review_id,
        "recent": [item.model_dump() for item in memory.latest_evidence_reviews(12)],
        "library": _evidence_library(latest),
    }


@app.get("/api/impact/records")
def impact_records() -> dict:
    latest = memory.latest_visit()
    return {"records": [item.model_dump() for item in _impact_records_for_visit(latest.id if latest else None, 50)]}


@app.get("/api/impact/agent")
def impact_agent_advice() -> dict:
    latest = memory.latest_visit()
    if not latest:
        raise HTTPException(status_code=400, detail="شغّل التحليل أولًا حتى يفهم وكيل الأثر حقيقة المدرسة.")
    records = _impact_records_for_visit(latest.id, 200)
    return impact_agent.advise(latest, len(records))


@app.post("/api/impact/records")
async def create_impact_record(
    title: str = Form(...),
    domain: str = Form(...),
    indicator: str = Form("عام"),
    before_state: str = Form(...),
    after_state: str = Form(...),
    improvement_rate: float = Form(0),
    statistics: str = Form(""),
    test_results: str = Form(""),
    testimonials: str = Form(""),
    narrative: str = Form(""),
    impact_files: list[UploadFile] | None = File(None),
    _: User = Depends(require_write),
) -> dict:
    latest = memory.latest_visit()
    if not latest:
        raise HTTPException(status_code=400, detail="شغّل التحليل أولًا حتى يرتبط ملف الأثر بزيارة نشطة.")
    folder = IMPACT_DIR / latest.id / _slug(domain) / _slug(title)
    folder.mkdir(parents=True, exist_ok=True)
    stored_files = []
    for upload in impact_files or []:
        if not upload.filename:
            continue
        safe_name = Path(upload.filename).name
        destination = folder / safe_name
        with destination.open("wb") as buffer:
            shutil.copyfileobj(upload.file, buffer)
        stored_files.append(str(destination))
    narrative_text = narrative.strip() or (
        f"انتقلت المدرسة في {title} من: {before_state} إلى: {after_state}. "
        f"نسبة التحسن الموثقة {improvement_rate:+.1f}%، ويجب عرضها أمام فريق التقويم كأثر لا كبرنامج منفذ فقط."
    )
    record = ImpactRecord(
        visit_id=latest.id,
        title=title,
        domain=domain,
        indicator=indicator,
        before_state=before_state,
        after_state=after_state,
        improvement_rate=improvement_rate,
        statistics=statistics,
        test_results=test_results,
        testimonials=testimonials,
        narrative=narrative_text,
        impact_level=_impact_level(improvement_rate, len(stored_files), statistics, test_results, testimonials),
        stored_files=stored_files,
    )
    record.validation_notes = _impact_validation_notes(record)
    memory.save_impact_record(record)
    event = memory.save_council_event(live_council.impact_event(latest, record))
    return {
        "record": record.model_dump(),
        "records": [item.model_dump() for item in _impact_records_for_visit(latest.id, 50)],
        "council_event": event.model_dump(),
        "council_events": [item.model_dump() for item in memory.latest_council_events(latest.id, 30)],
    }


@app.delete("/api/impact/records/{record_id}")
def delete_impact_record(record_id: str, _: User = Depends(require_write)) -> dict:
    record = memory.delete_impact_record(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="قصة الأثر غير موجودة.")
    for file_path in record.stored_files:
        path = Path(file_path)
        if path.exists():
            path.unlink()
    latest = memory.latest_visit()
    return {"deleted": record_id, "records": [item.model_dump() for item in _impact_records_for_visit(latest.id if latest else None, 50)]}


@app.post("/api/impact/package/build")
def build_impact_package(_: User = Depends(require_write)) -> dict:
    latest = memory.latest_visit()
    if not latest:
        raise HTTPException(status_code=400, detail="لا توجد زيارة نشطة لبناء الملف الذهبي.")
    path = _build_impact_package(latest.id)
    return {"download_url": f"/api/impact/package/{latest.id}/download", "filename": path.name}


@app.get("/api/impact/package/{visit_id}/download")
def impact_package_download(visit_id: str) -> FileResponse:
    zip_path = _build_impact_package(visit_id)
    return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)


@app.post("/api/visits/{visit_id}/tasks/{action_id}/status")
def update_task_status(visit_id: str, action_id: str, update: TaskStatusUpdate, _: User = Depends(require_write)) -> dict:
    visit = memory.update_task_status(visit_id, action_id, update)
    if not visit:
        raise HTTPException(status_code=404, detail="Task not found")
    task = next((item for item in visit.tasks if item.action_id == action_id), None)
    event = memory.save_council_event(live_council.task_event(visit, task)) if task else None
    return {
        "visit": visit.model_dump(),
        "dashboard": _visit_dashboard(visit),
        "council_event": event.model_dump() if event else None,
        "council_events": [item.model_dump() for item in memory.latest_council_events(visit.id, 30)],
    }


@app.get("/api/reports/{visit_id}")
def report(visit_id: str) -> FileResponse:
    for visit in memory.all_visits():
        if visit.id == visit_id:
            path = build_pdf_report(visit, REPORTS_DIR)
            return FileResponse(path, media_type="application/pdf", filename=path.name)
    raise HTTPException(status_code=404, detail="Report not found")


@app.get("/api/execution/{visit_id}/download")
def execution_download(visit_id: str) -> FileResponse:
    for visit in memory.all_visits():
        if visit.id == visit_id and visit.execution_pack and visit.execution_pack.folder_path:
            folder = Path(visit.execution_pack.folder_path)
            if not folder.exists():
                break
            zip_path = EXECUTION_DIR / f"execution-pack-{visit_id}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for file in folder.glob("*.md"):
                    archive.write(file, arcname=file.name)
            return FileResponse(zip_path, media_type="application/zip", filename=zip_path.name)
    raise HTTPException(status_code=404, detail="Execution pack not found")
