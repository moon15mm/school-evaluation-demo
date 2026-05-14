from __future__ import annotations

from pathlib import Path

from app.core.live_council import LiveAgentCouncil
from app.core.memory import SchoolMemory
from app.core.models import AnalysisRequest, EvidenceReview, ImpactRecord, LiveCouncilEvent, TaskStatusUpdate
from app.core.pipeline import EvaluationPipeline
from app.core.report_reference import build_school_report_profile


DEMO_REPORT_TEXT = """
مدرسة المستقبل الثانوية - تقرير تقويم خارجي افتراضي.
الدرجة العامة السابقة 73%، مستوى الانطلاق.
أبرز مجالات التحسين: جودة التعليم والتعلم، نواتج التعلم، التقويم الصفي، الانضباط المدرسي، الشراكة مع الأسرة.
مؤشرات تحتاج تحسين:
1-1-3 استخدام البيانات في اتخاذ القرار المدرسي.
2-1-4 توظيف استراتيجيات تعلم نشط داخل الصف.
3-1-2 رفع مستوى المهارات الأساسية في القراءة والرياضيات.
4-2-1 تحسين الانضباط والحضور الطلابي.
5-1-2 توثيق أثر برامج الشراكة المجتمعية.
نقاط قوة: وضوح الهيكل الإداري، وجود خطة تشغيلية أولية، مبادرات محدودة لدعم الطلاب.
توصية الفريق: تحويل البرامج إلى أثر قابل للقياس، وربط الشواهد بنتائج الطلاب لا بمجرد تنفيذ النشاط.
"""

DEMO_CURRENT_STATUS = """
تعمل المدرسة على الاستعداد للزيارة الثانية خلال 45 يومًا.
تم تشكيل فريق جودة مصغر، وبدأت مراجعة نتائج الاختبارات القصيرة ومؤشرات الغياب.
يوجد تحسن أولي في الانضباط من 82% إلى 91%، وتحسن في إتقان مهارات القراءة من 58% إلى 71%.
لا تزال الشواهد غير مكتملة في بعض البنود، وتحتاج المدرسة إلى ملف أثر واضح يثبت قبل وبعد.
تم تنفيذ زيارات صفية داخلية لعدد من المعلمين، لكن التغذية الراجعة لم تتحول بعد إلى خطط علاجية موثقة.
"""


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

    request = AnalysisRequest(
        school_name="مدرسة المستقبل الثانوية",
        current_status=DEMO_CURRENT_STATUS,
        team_members=[
            "مدير المدرسة",
            "وكيل الشؤون التعليمية",
            "رائد النشاط",
            "الموجه الطلابي",
            "منسق الجودة",
        ],
    )
    profile = build_school_report_profile(DEMO_REPORT_TEXT)
    visit = pipeline.run(request, DEMO_REPORT_TEXT, "demo-previous-visit.pdf", report_profile_override=profile)

    for task in visit.tasks[:2]:
        memory.update_task_status(visit.id, task.action_id, TaskStatusUpdate(status="in_progress"))
    for task in visit.tasks[2:3]:
        memory.update_task_status(visit.id, task.action_id, TaskStatusUpdate(status="done"))

    _seed_demo_evidence(memory, visit.id, evidence_dir, profile)
    _seed_demo_impact(memory, visit.id, impact_dir)

    memory.save_council_event(live_council.analysis_event(visit))
    memory.save_council_event(
        LiveCouncilEvent(
            visit_id=visit.id,
            event_type="system",
            title="تهيئة نسخة العرض التسويقي",
            summary="تم إنشاء بيانات افتراضية آمنة لعرض لوحة المتابعة والشواهد وملف الأثر دون استخدام بيانات مدرسة حقيقية.",
            recommendations=[
                "ابدأ العرض من لوحة النظرة العامة لإظهار التقدم والتأخر.",
                "انتقل إلى الشواهد لعرض التصنيف حسب بنود التقويم.",
                "اختم بملف الأثر ومحاكاة فريق التقويم لأنها أقوى نقطة تسويقية.",
            ],
            warnings=[
                "هذه بيانات افتراضية للعرض فقط ولا تمثل مدرسة حقيقية.",
            ],
            next_actions=[
                "تسجيل دخول بحساب demo للعرض الآمن.",
                "استخدام حساب admin فقط عند الحاجة لتعديل بيانات العرض.",
            ],
            severity="info",
        )
    )


def _seed_demo_evidence(memory: SchoolMemory, visit_id: str, evidence_dir: Path, profile) -> None:
    indicators = list(profile.improvement_priorities[:3]) if profile else []
    if not indicators:
        return

    samples = [
        (
            "تقرير_تحليل_نتائج_القراءة.pdf",
            "تحليل نتائج القراءة قبل وبعد البرنامج العلاجي",
            "الشاهد مناسب لأنه يربط البرنامج بنتيجة قابلة للقياس، ويحتاج إضافة توقيع لجنة المراجعة النهائية.",
            "suitable",
            0.91,
        ),
        (
            "محضر_مجتمع_تعلم_استراتيجيات_نشطة.pdf",
            "محضر مجتمع تعلم مهني حول التعلم النشط",
            "الشاهد مناسب مبدئيًا، ويقوى بإضافة أثر الزيارات الصفية بعد التدريب.",
            "needs_edit",
            0.78,
        ),
        (
            "استبانة_رضا_أولياء_الأمور.pdf",
            "تحليل استبانة رضا أولياء الأمور عن التواصل المدرسي",
            "الشاهد جيد للشراكة المجتمعية ويحتاج مقارنة قبل وبعد لإثبات الأثر.",
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
        review = EvidenceReview(
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
        memory.save_evidence_review(review)


def _seed_demo_impact(memory: SchoolMemory, visit_id: str, impact_dir: Path) -> None:
    records = [
        ImpactRecord(
            visit_id=visit_id,
            title="رفع إتقان مهارات القراءة",
            domain="نواتج التعلم",
            indicator="3-1-2",
            before_state="إتقان القراءة لدى عينة الصف الأول الثانوي 58%.",
            after_state="ارتفع الإتقان إلى 71% بعد برنامج علاجي من ثلاث مراحل.",
            improvement_rate=13,
            statistics="عدد الطلاب المستهدفين 84، تحسن 49 طالبًا، وانخفضت حالات التعثر الشديد من 19 إلى 8.",
            test_results="اختبار قبلي في الأسبوع الأول، واختبار بعدي في الأسبوع الخامس بنفس المهارات.",
            testimonials="شهادة معلم اللغة العربية ومنسق الجودة تؤكد ارتفاع المشاركة الصفية.",
            narrative="تم تحديد الطلاب المتعثرين، تنفيذ حصص علاجية قصيرة، ثم قياس أثر البرنامج بنتائج قبلية وبعدية.",
            impact_level="strong",
            validation_notes=["قصة أثر قوية، وتحتاج إرفاق عينة من أوراق القياس عند العرض النهائي."],
            stored_files=[],
        ),
        ImpactRecord(
            visit_id=visit_id,
            title="تحسين الانضباط والحضور الصباحي",
            domain="البيئة المدرسية",
            indicator="4-2-1",
            before_state="متوسط الحضور الصباحي 82%.",
            after_state="وصل متوسط الحضور إلى 91% بعد نظام متابعة أسبوعي ورسائل للأسرة.",
            improvement_rate=9,
            statistics="انخفض التأخر الصباحي من 37 حالة أسبوعيًا إلى 16 حالة.",
            test_results="مقارنة سجلات الحضور خلال أربعة أسابيع قبل التدخل وبعده.",
            testimonials="إفادة وكيل شؤون الطلاب وملاحظات أولياء الأمور حول وضوح التواصل.",
            narrative="ربطت المدرسة المتابعة اليومية برسائل مباشرة للأسرة وتكريم صفوف الانضباط الأعلى.",
            impact_level="strong",
            validation_notes=["الأثر واضح رقميًا، ويحتاج عينة من سجل الحضور الموثق."],
            stored_files=[],
        ),
    ]
    (impact_dir / visit_id).mkdir(parents=True, exist_ok=True)
    for record in records:
        memory.save_impact_record(record)


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
