from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.core.models import EvidenceReview
from app.core.reporting import _arabic_bold_font_path, _arabic_font_path, _para, official_report_header, section_divider


def _pdf_styles():
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path = _arabic_font_path()
    if font_path:
        pdfmetrics.registerFont(TTFont("EvidenceArabic", str(font_path)))
        pdfmetrics.registerFont(TTFont("EvidenceArabicBold", str(_arabic_bold_font_path() or font_path)))
        normal_font = "EvidenceArabic"
        bold_font = "EvidenceArabicBold"
    else:
        normal_font = "Helvetica"
        bold_font = "Helvetica-Bold"

    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "EvidenceTitle",
            parent=styles["Title"],
            fontName=bold_font,
            alignment=TA_RIGHT,
            leading=22,
            wordWrap="RTL",
            spaceAfter=12,
        ),
        "heading": ParagraphStyle(
            "EvidenceHeading",
            parent=styles["Heading2"],
            fontName=bold_font,
            alignment=TA_RIGHT,
            leading=18,
            wordWrap="RTL",
            spaceBefore=8,
            spaceAfter=6,
        ),
        "normal": ParagraphStyle(
            "EvidenceNormal",
            parent=styles["Normal"],
            fontName=normal_font,
            alignment=TA_RIGHT,
            leading=16,
            wordWrap="RTL",
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "EvidenceSmall",
            parent=styles["Normal"],
            fontName=normal_font,
            alignment=TA_RIGHT,
            leading=13,
            fontSize=9,
            wordWrap="RTL",
            textColor="#52616f",
        ),
    }


def _status_label(value: str) -> str:
    return {
        "suitable": "مناسب للاعتماد",
        "needs_edit": "يحتاج تعديل قبل الاعتماد",
        "insufficient": "غير كاف للاعتماد",
    }.get(value, value)


def build_evidence_card_pdf(review: EvidenceReview, note: str, output_dir: Path) -> Path:
    path = output_dir / f"بطاقة_الشاهد_{review.id}.pdf"
    _build_review_pdf(
        path,
        "بطاقة اعتماد شاهد",
        review,
        [
            ("الملاحظة المرفقة", note or "لا توجد ملاحظة مرفقة."),
            ("التعديلات المطلوبة", _as_lines(review.required_edits) or "لا توجد تعديلات جوهرية."),
            ("إشارات المطابقة", "، ".join(review.matched_signals) or "لا توجد إشارات مطابقة كافية."),
            (
                "بروتوكول الاعتماد",
                "وضوح الملف أو الصورة. ظهور التاريخ أو مصدر الشاهد. ارتباط الشاهد بمؤشر محدد. جاهزية الشاهد للعرض أثناء زيارة التقويم.",
            ),
        ],
    )
    return path


def build_secretariat_decision_pdf(review: EvidenceReview, output_dir: Path) -> Path:
    path = output_dir / f"قرار_السكرتارية_{review.id}.pdf"
    _build_review_pdf(
        path,
        "قرار سكرتارية الشواهد",
        review,
        [
            ("القرار", _status_label(review.suitability)),
            ("مكان الحفظ الصحيح", review.destination_folder),
            ("رأي الوكلاء", review.secretariat_opinion),
            ("الإجراء التالي", _as_lines(review.required_edits) or "اعتماد الشاهد ضمن ملف الأدلة النهائي."),
        ],
    )
    return path


def build_evidence_index_pdf(reviews: list[EvidenceReview], output_path: Path, folders: list[dict] | None = None) -> Path:
    try:
        return _build_evidence_dossier_pdf(reviews, output_path, folders or [])
    except Exception:
        return _build_simple_evidence_index_pdf(reviews, output_path)


def _build_evidence_dossier_pdf(reviews: list[EvidenceReview], output_path: Path, folders: list[dict]) -> Path:
    from pypdf import PdfReader, PdfWriter

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = output_path.parent / f"_dossier_parts_{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    writer = PdfWriter()
    reviews_by_key: dict[str, list[EvidenceReview]] = {}
    for review in reviews:
        key = f"{review.suggested_domain}::{review.suggested_indicator_code or 'غير محدد'}"
        reviews_by_key.setdefault(key, []).append(review)

    cover = temp_dir / "00_cover.pdf"
    _build_dossier_part_pdf(
        cover,
        "ملف الشواهد الموحد",
        [
            f"عدد الشواهد: {len(reviews)}",
            f"عدد بنود/مجلدات الشواهد: {len(folders) if folders else len(reviews_by_key)}",
            "تم ترتيب الملف حسب مجلدات التقييم وبنود الشواهد، مع إدراج الشواهد داخل بندها الصحيح.",
        ],
    )
    _append_pdf(writer, cover)

    ordered_folders = folders or [
        {
            "domain": key.split("::", 1)[0],
            "indicator_code": key.split("::", 1)[1],
            "indicator_title": key.split("::", 1)[1],
            "required_evidence": "غير محدد",
            "reviews": [review.model_dump() for review in items],
        }
        for key, items in reviews_by_key.items()
    ]

    for index, folder in enumerate(ordered_folders, start=1):
        key = f"{folder.get('domain')}::{folder.get('indicator_code')}"
        folder_reviews = reviews_by_key.get(key, [])
        section_pdf = temp_dir / f"{index:03d}_section.pdf"
        _build_folder_section_pdf(section_pdf, index, folder, folder_reviews)
        _append_pdf(writer, section_pdf)
        for review in folder_reviews:
            original = Path(review.stored_path)
            if original.suffix.lower() == ".pdf" and original.exists():
                separator = temp_dir / f"{index:03d}_{review.id}_separator.pdf"
                _build_dossier_part_pdf(
                    separator,
                    f"الشاهد الأصلي: {review.original_filename}",
                    [
                        f"المجلد: {folder.get('domain')} / {folder.get('indicator_code')}",
                        "تبدأ صفحات ملف الشاهد الأصلي بعد هذه الصفحة مباشرة.",
                    ],
                )
                _append_pdf(writer, separator)
                _append_pdf(writer, original)

    with output_path.open("wb") as handle:
        writer.write(handle)

    for file in temp_dir.glob("*.pdf"):
        file.unlink(missing_ok=True)
    temp_dir.rmdir()
    return output_path


def _build_simple_evidence_index_pdf(reviews: list[EvidenceReview], output_path: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Spacer

    output_path.parent.mkdir(parents=True, exist_ok=True)
    styles = _pdf_styles()
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=146, bottomMargin=36)
    story = [section_divider("ملف الشواهد الموحد", "فهرسة الشواهد حسب مجلدات وبنود التقييم")]
    story.append(_para(f"عدد الشواهد: {len(reviews)}", styles["normal"]))
    story.append(Spacer(1, 8))
    grouped: dict[str, list[EvidenceReview]] = {}
    for review in reviews:
        key = f"{review.suggested_domain} / {review.suggested_indicator_code or 'غير محدد'}"
        grouped.setdefault(key, []).append(review)
    for group, items in grouped.items():
        story.append(Spacer(1, 10))
        story.append(section_divider(group))
        story.append(Spacer(1, 8))
        for review in items:
            story.append(_para(f"الملف: {review.original_filename}", styles["normal"]))
            story.append(_para(f"الحكم: {_status_label(review.suitability)} | الثقة: {round(review.confidence * 100)}%", styles["normal"]))
            story.append(_para(f"الرأي: {review.secretariat_opinion}", styles["normal"]))
            story.append(_para(f"المسار: {review.stored_path}", styles["small"]))
            story.append(Spacer(1, 6))
    header = official_report_header("ملف الشواهد الموحد")
    doc.build(story, onFirstPage=header, onLaterPages=header)
    return output_path


def _build_folder_section_pdf(path: Path, index: int, folder: dict, reviews: list[EvidenceReview]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, PageBreak, SimpleDocTemplate, Spacer

    styles = _pdf_styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=146, bottomMargin=36)
    story = [
        section_divider(f"{index}. {folder.get('domain')} / {folder.get('indicator_code')}", folder.get("indicator_title")),
        Spacer(1, 10),
        _para(f"عنوان البند: {folder.get('indicator_title') or 'غير محدد'}", styles["normal"]),
        _para("المطلوب من الشواهد", styles["heading"]),
        _para(folder.get("required_evidence") or "لم يحدد المطلوب لهذا البند.", styles["normal"]),
        _para(f"عدد الشواهد المصنفة داخل هذا المجلد: {len(reviews)}", styles["normal"]),
        Spacer(1, 10),
    ]
    if not reviews:
        story.append(_para("لا توجد شواهد مرفوعة لهذا البند حتى الآن.", styles["normal"]))
    for review_index, review in enumerate(reviews, start=1):
        story.append(_para(f"الشاهد {review_index}: {review.original_filename}", styles["heading"]))
        story.append(_para(f"الحكم: {_status_label(review.suitability)} | الثقة: {round(review.confidence * 100)}%", styles["normal"]))
        story.append(_para(f"رأي السكرتارية: {review.secretariat_opinion}", styles["normal"]))
        story.append(_para(f"المسار: {review.stored_path}", styles["small"]))
        if review.required_edits:
            story.append(_para(f"التعديلات المطلوبة: {_as_lines(review.required_edits)}", styles["normal"]))
        original = Path(review.stored_path)
        if original.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and original.exists():
            try:
                img = Image(str(original))
                max_width = 15 * cm
                max_height = 12 * cm
                ratio = min(max_width / img.imageWidth, max_height / img.imageHeight, 1)
                img.drawWidth = img.imageWidth * ratio
                img.drawHeight = img.imageHeight * ratio
                story.append(Spacer(1, 6))
                story.append(img)
            except Exception:
                story.append(_para("تعذر إدراج معاينة الصورة داخل الملف، لكن الصورة محفوظة داخل الحزمة.", styles["normal"]))
        elif original.suffix.lower() == ".pdf":
            story.append(_para("ملف PDF الأصلي مدمج بعد صفحة هذا البند مباشرة في نفس ترتيب المجلد.", styles["normal"]))
        else:
            story.append(_para("الملف الأصلي محفوظ داخل الحزمة، ولا يمكن عرضه بصريًا داخل PDF الموحد.", styles["normal"]))
        story.append(Spacer(1, 8))
    story.append(PageBreak())
    header = official_report_header("ملف الشواهد الموحد")
    doc.build(story, onFirstPage=header, onLaterPages=header)


def _build_dossier_part_pdf(path: Path, title: str, lines: list[str]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Spacer

    styles = _pdf_styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=146, bottomMargin=36)
    story = [section_divider(title), Spacer(1, 8)]
    for line in lines:
        story.append(_para(line, styles["normal"]))
    header = official_report_header(title)
    doc.build(story, onFirstPage=header, onLaterPages=header)


def _append_pdf(writer, path: Path) -> None:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    for page in reader.pages:
        writer.add_page(page)


def _build_review_pdf(path: Path, title: str, review: EvidenceReview, sections: list[tuple[str, str]]) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Spacer

    path.parent.mkdir(parents=True, exist_ok=True)
    styles = _pdf_styles()
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=146, bottomMargin=36)
    story = [section_divider(title), Spacer(1, 8)]
    story.append(_para(f"اسم الملف: {review.original_filename}", styles["normal"]))
    story.append(_para(f"تاريخ الفحص: {review.created_at}", styles["normal"]))
    story.append(_para(f"المجال: {review.suggested_domain}", styles["normal"]))
    story.append(_para(f"المؤشر: {review.suggested_indicator_code or 'غير محدد'}", styles["normal"]))
    story.append(_para(f"عنوان المؤشر: {review.suggested_indicator_title or 'غير محدد'}", styles["normal"]))
    story.append(_para(f"الحالة: {_status_label(review.suitability)} | الثقة: {round(review.confidence * 100)}%", styles["normal"]))
    story.append(Spacer(1, 8))
    for heading, body in sections:
        story.append(_para(heading, styles["heading"]))
        story.append(_para(body, styles["normal"]))
    header = official_report_header(title)
    doc.build(story, onFirstPage=header, onLaterPages=header)


def _as_lines(items: list[str]) -> str:
    return " ".join(f"- {item}" for item in items)
