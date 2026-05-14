from __future__ import annotations

import os
from pathlib import Path

from app.core.live_council import LiveAgentCouncil
from app.core.memory import SchoolMemory
from app.core.models import AnalysisRequest, EvidenceReview, ImpactRecord, LiveCouncilEvent, TaskStatusUpdate
from app.core.pipeline import EvaluationPipeline
from app.core.report_reference import build_school_report_profile
from app.core.stage_rubrics import get_stage_rubric


STAGE_CONFIGS = {
    "secondary": {
        "school_name": "مدرسة المستقبل الثانوية",
        "stage_label": "الثانوية",
        "grade_focus": "الصف الأول الثانوي",
        "score": 73,
        "days": 45,
        "reading_before": 58,
        "reading_after": 71,
        "attendance_before": 82,
        "attendance_after": 91,
        "main_skills": "الاختبارات التحصيلية والقدرات، القراءة التحليلية، الرياضيات، والانضباط الصباحي",
        "current_focus": "بدأت المدرسة تحليل نتائج الاختبارات القصيرة ومؤشرات الغياب والزيارات الصفية.",
        "impact_title": "رفع إتقان مهارات القراءة التحليلية",
        "second_impact_title": "تحسين الانضباط والحضور الصباحي",
        "team": ["مدير المدرسة", "وكيل الشؤون التعليمية", "رائد النشاط", "الموجه الطلابي", "منسق الجودة"],
    },
    "intermediate": {
        "school_name": "مدرسة المستقبل المتوسطة",
        "stage_label": "المتوسطة",
        "grade_focus": "الصف الثاني المتوسط",
        "score": 72,
        "days": 40,
        "reading_before": 54,
        "reading_after": 69,
        "attendance_before": 84,
        "attendance_after": 92,
        "main_skills": "المهارات الأساسية في القراءة، الرياضيات، العلوم، الانضباط، والانتقال الآمن بين الحصص",
        "current_focus": "بدأت المدرسة مراجعة نتائج المهارات الأساسية وسلوك الطلاب داخل الصفوف ومؤشرات الحضور.",
        "impact_title": "رفع إتقان الفهم القرائي والمهارات العددية",
        "second_impact_title": "خفض التأخر والغياب المتكرر",
        "team": ["مدير المدرسة", "وكيل الشؤون التعليمية", "الموجه الطلابي", "رائد النشاط", "منسق الجودة"],
    },
    "primary": {
        "school_name": "مدرسة المستقبل الابتدائية",
        "stage_label": "الابتدائية",
        "grade_focus": "الصف الثالث الابتدائي",
        "score": 71,
        "days": 35,
        "reading_before": 49,
        "reading_after": 67,
        "attendance_before": 86,
        "attendance_after": 94,
        "main_skills": "القراءة الجهرية، الفهم القرائي، العمليات الحسابية الأساسية، الانضباط، ومشاركة الأسرة",
        "current_focus": "بدأت المدرسة حصر الطلاب المحتاجين للدعم في القراءة والرياضيات، وتفعيل متابعة الأسرة.",
        "impact_title": "رفع إتقان القراءة الجهرية والفهم القرائي",
        "second_impact_title": "تعزيز انتظام الحضور ومشاركة الأسرة",
        "team": ["مدير المدرسة", "وكيل المدرسة", "رائد النشاط", "الموجه الطلابي", "منسق الجودة"],
    },
}


def seed_demo_data(
    memory: SchoolMemory,
    pipeline: EvaluationPipeline,
    evidence_dir: Path,
    impact_dir: Path,
    live_council: LiveAgentCouncil,
) -> None:
    """Populate an empty online demo with believable non-sensitive school data."""
    if memory.latest_visit():
        return

    stage = os.getenv("DEMO_STAGE", "secondary").strip().lower()
    rubric = get_stage_rubric(stage)
    config = {**STAGE_CONFIGS.get(stage, STAGE_CONFIGS["secondary"]), **rubric}
    report_text = _demo_report_text(config)
    current_status = _demo_current_status(config)
    profile = build_school_report_profile(report_text)
    if profile:
        _adapt_profile(profile, config)

    request = AnalysisRequest(
        school_name=config["school_name"],
        current_status=current_status,
        team_members=list(config["team"]),
    )
    visit = pipeline.run(request, report_text, f"demo-{stage}-previous-visit.pdf", report_profile_override=profile)

    for task in visit.tasks[:2]:
        memory.update_task_status(visit.id, task.action_id, TaskStatusUpdate(status="in_progress"))
    for task in visit.tasks[2:3]:
        memory.update_task_status(visit.id, task.action_id, TaskStatusUpdate(status="done"))

    _seed_demo_evidence(memory, visit.id, evidence_dir, profile, config)
    _seed_demo_impact(memory, visit.id, impact_dir, config)
    memory.save_council_event(live_council.analysis_event(visit))
    memory.save_council_event(_system_event(visit.id, config))


def _demo_report_text(config: dict) -> str:
    return f"""
{config["school_name"]} - تقرير تقويم خارجي افتراضي.
المرحلة: {config["label"]}.
الدرجة العامة السابقة {config["score"]}%، مستوى الانطلاق.
أبرز مجالات التحسين: جودة التعليم والتعلم، نواتج التعلم، التقويم الصفي، الانضباط المدرسي، الشراكة مع الأسرة.
مؤشرات تحتاج تحسين:
1-1-3 استخدام البيانات في اتخاذ القرار المدرسي.
2-1-4 توظيف استراتيجيات تعلم نشط داخل الصف.
3-1-2 رفع مستوى {config["focus_summary"]}.
4-2-1 تحسين الانضباط والحضور الطلابي.
5-1-2 توثيق أثر برامج الشراكة مع الأسرة والمجتمع.
نقاط قوة: وضوح الهيكل الإداري، وجود خطة تشغيلية أولية، ومبادرات محدودة لدعم الطلاب.
توصية الفريق: تحويل البرامج إلى أثر قابل للقياس، وربط الشواهد بنتائج الطلاب لا بمجرد تنفيذ النشاط.
"""


def _demo_current_status(config: dict) -> str:
    return f"""
تعمل المدرسة على الاستعداد للزيارة الثانية خلال {config["days"]} يومًا.
{config["current_focus"]}
يوجد تحسن أولي في الانضباط من {config["attendance_before"]}% إلى {config["attendance_after"]}%.
تحسن إتقان المهارات المستهدفة من {config["reading_before"]}% إلى {config["reading_after"]}%.
لا تزال الشواهد غير مكتملة في بعض البنود، وتحتاج المدرسة إلى ملف أثر واضح يثبت قبل وبعد.
تم تنفيذ زيارات صفية داخلية لعدد من المعلمين، لكن التغذية الراجعة تحتاج إلى خطط علاجية موثقة وأثر رقمي.
"""


def _adapt_profile(profile, config: dict) -> None:
    profile.school_name = config["school_name"]
    profile.overall_score = float(config["score"])
    profile.strategic_reading = (
        f"الزيارة القادمة تستهدف نقل {config['school_name']} من مستوى الانطلاق إلى مستوى التقدم، "
        f"مع تركيز خاص على {config['focus_summary']}، وتحويل كل برنامج إلى أثر قابل للقياس."
    )
    priority_by_code = {item["code"]: item for item in config.get("critical_indicators", [])}
    priorities = list(profile.improvement_priorities)
    for index, indicator in enumerate(priorities[: len(priority_by_code)]):
        rubric_item = list(priority_by_code.values())[index]
        indicator.code = rubric_item["code"]
        indicator.domain = rubric_item["domain"]
        indicator.title = rubric_item["title"]
        indicator.required_response = rubric_item["required_evidence"]
    for indicator in [*profile.improvement_priorities, *profile.strengths]:
        indicator.title = indicator.title.replace("للمرحلة الثانوية", f"للمرحلة {config['label']}")
        indicator.required_response = indicator.required_response.replace("قدرات", "مهارات أساسية")


def _seed_demo_evidence(memory: SchoolMemory, visit_id: str, evidence_dir: Path, profile, config: dict) -> None:
    indicators = list(profile.improvement_priorities[:3]) if profile else []
    samples = [
        (
            f"تقرير_تحليل_نتائج_{config['label']}.pdf",
            f"تحليل نتائج {config['focus_summary']} قبل وبعد التدخل",
            "الشاهد مناسب لأنه يربط البرنامج بنتيجة قابلة للقياس، ويحتاج إضافة توقيع لجنة المراجعة النهائية.",
            "suitable",
            0.91,
        ),
        (
            "محضر_مجتمع_تعلم_استراتيجيات_نشطة.pdf",
            f"محضر مجتمع تعلم مهني حول التعلم النشط في المرحلة {config['label']}",
            "الشاهد مناسب مبدئيًا، ويقوى بإضافة أثر الزيارات الصفية بعد التدريب.",
            "needs_edit",
            0.78,
        ),
        (
            "استبانة_رضا_أولياء_الأمور.pdf",
            "تحليل استبانة رضا أولياء الأمور عن التواصل المدرسي",
            "الشاهد جيد للشراكة مع الأسرة ويحتاج مقارنة قبل وبعد لإثبات الأثر.",
            "needs_edit",
            0.74,
        ),
    ]

    for indicator, sample in zip(indicators, samples):
        filename, title, opinion, suitability, confidence = sample
        folder = evidence_dir / visit_id / _slug(indicator.domain) / _slug(indicator.code)
        folder.mkdir(parents=True, exist_ok=True)
        stored_path = folder / filename
        _write_demo_pdf(stored_path, title, ["ملف تجريبي للعرض التسويقي.", "يربط الشاهد بالمؤشر ويعرض أثرًا قابلًا للمراجعة."])
        memory.save_evidence_review(
            EvidenceReview(
                visit_id=visit_id,
                original_filename=filename,
                stored_path=str(stored_path),
                suggested_domain=indicator.domain,
                suggested_indicator_code=indicator.code,
                suggested_indicator_title=indicator.title,
                destination_folder=str(folder),
                suitability=suitability,  # type: ignore[arg-type]
                confidence=confidence,
                secretariat_opinion=opinion,
                required_edits=["إضافة تاريخ التنفيذ ومصدر البيانات.", "إرفاق نتيجة قبلية وبعدية عند توفرها."],
                matched_signals=["نتائج", "تحسن", "متابعة", "أثر"],
                agents=["وكيل التصنيف", "وكيل الأرشفة", "وكيل الاعتماد"],
            )
        )


def _seed_demo_impact(memory: SchoolMemory, visit_id: str, impact_dir: Path, config: dict) -> None:
    records = [
        ImpactRecord(
            visit_id=visit_id,
            title=config["impact_title"],
            domain="نواتج التعلم",
            indicator="3-1-2",
            before_state=f"إتقان المهارات المستهدفة لدى عينة {config['grade_focus']} {config['reading_before']}%.",
            after_state=f"ارتفع الإتقان إلى {config['reading_after']}% بعد برنامج علاجي قصير ومتابعة أسبوعية.",
            improvement_rate=float(config["reading_after"] - config["reading_before"]),
            statistics="تم تقسيم الطلاب إلى مجموعات دعم، ومتابعة التحسن باختبارات قصيرة وسجلات ملاحظة صفية.",
            test_results="اختبار قبلي في الأسبوع الأول، واختبار بعدي في الأسبوع الخامس بنفس المهارات.",
            testimonials="شهادة المعلم ومنسق الجودة تؤكد ارتفاع المشاركة الصفية وتحسن الاستجابة.",
            narrative="تم تحديد الطلاب المتعثرين، تنفيذ تدخلات قصيرة، ثم قياس أثر البرنامج بنتائج قبلية وبعدية.",
            impact_level="strong",
            validation_notes=["قصة أثر قوية، وتحتاج إرفاق عينة من أدوات القياس عند العرض النهائي."],
            stored_files=[],
        ),
        ImpactRecord(
            visit_id=visit_id,
            title=config["second_impact_title"],
            domain="البيئة المدرسية",
            indicator="4-2-1",
            before_state=f"متوسط الحضور والانضباط {config['attendance_before']}%.",
            after_state=f"وصل المتوسط إلى {config['attendance_after']}% بعد نظام متابعة أسبوعي وتواصل منظم مع الأسرة.",
            improvement_rate=float(config["attendance_after"] - config["attendance_before"]),
            statistics="انخفضت حالات التأخر والغياب المتكرر بعد متابعة أسبوعية واضحة.",
            test_results="مقارنة سجلات الحضور والانضباط خلال أربعة أسابيع قبل التدخل وبعده.",
            testimonials="إفادة وكيل شؤون الطلاب وملاحظات أولياء الأمور حول وضوح التواصل.",
            narrative="ربطت المدرسة المتابعة اليومية برسائل مباشرة للأسرة وتكريم الصفوف الأعلى التزامًا.",
            impact_level="strong",
            validation_notes=["الأثر واضح رقميًا، ويحتاج عينة من سجل الحضور أو لوحة المتابعة."],
            stored_files=[],
        ),
    ]
    (impact_dir / visit_id).mkdir(parents=True, exist_ok=True)
    for record in records:
        memory.save_impact_record(record)


def _system_event(visit_id: str, config: dict) -> LiveCouncilEvent:
    return LiveCouncilEvent(
        visit_id=visit_id,
        event_type="system",
        title=f"تهيئة نسخة عرض {config['label']}",
        summary=f"تم إنشاء بيانات افتراضية آمنة لعرض {config['school_name']} دون استخدام بيانات مدرسة حقيقية.",
        recommendations=[
            "ابدأ العرض من لوحة النظرة العامة لإظهار التقدم والتأخر.",
            f"ركز في العرض على: {config['focus_summary']}.",
            "اختم بملف الأثر ومحاكاة فريق التقويم لأنها أقوى نقطة تسويقية.",
        ],
        warnings=["هذه بيانات افتراضية للعرض فقط ولا تمثل مدرسة حقيقية.", *config.get("risk_signals", [])[:2]],
        next_actions=[
            "تسجيل دخول بحساب demo للعرض الآمن.",
            "استخدام حساب المدير فقط عند الحاجة لتعديل بيانات العرض.",
            *[f"سؤال تقويم متوقع: {question}" for question in config.get("evaluator_questions", [])[:2]],
        ],
        severity="info",
    )


def _write_demo_pdf(path: Path, title: str, lines: list[str]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawRightString(width - 48, height - 72, title)
    pdf.setFont("Helvetica", 11)
    y = height - 116
    for line in lines:
        pdf.drawRightString(width - 48, y, line)
        y -= 24
    pdf.drawRightString(width - 48, y - 18, "Demo evidence file for online presentation.")
    pdf.save()


def _slug(value: str) -> str:
    import re

    return re.sub(r"[^\w\u0600-\u06FF]+", "_", str(value), flags=re.UNICODE).strip("_") or "item"
