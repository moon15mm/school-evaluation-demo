from __future__ import annotations

from pathlib import Path

from app.core.models import ImpactRecord
from app.core.reporting import _para, official_report_header, register_arabic_fonts, section_divider


def impact_level_label(value: str) -> str:
    return {
        "limited": "أثر محدود يحتاج تقوية",
        "clear": "أثر واضح",
        "strong": "أثر قوي",
        "golden": "أثر ذهبي جاهز للعرض",
    }.get(value, value)


def build_impact_pdf(records: list[ImpactRecord], output_path: Path) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Image, PageBreak, SimpleDocTemplate, Spacer, Table, TableStyle

    output_path.parent.mkdir(parents=True, exist_ok=True)
    normal_font, bold_font = register_arabic_fonts("ImpactArabic")
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "ImpactNormal",
        parent=styles["Normal"],
        fontName=normal_font,
        alignment=TA_RIGHT,
        leading=15,
        wordWrap="RTL",
        spaceAfter=5,
    )
    heading = ParagraphStyle(
        "ImpactHeading",
        parent=styles["Heading2"],
        fontName=bold_font,
        alignment=TA_RIGHT,
        leading=18,
        wordWrap="RTL",
        spaceBefore=6,
        spaceAfter=6,
    )
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=146, bottomMargin=36)
    story = [
        section_divider("الملف الذهبي: ملف الأثر", "قبل وبعد، نسب تحسن، صور، إحصاءات، شهادات، ونتائج اختبارات"),
        Spacer(1, 10),
        _para(f"عدد قصص الأثر الموثقة: {len(records)}", normal),
        _para("يركز هذا الملف على إثبات الأثر الحقيقي لا كثرة البرامج، ويرتب كل قصة أثر بطريقة تصلح للعرض أمام فريق التقويم.", normal),
        Spacer(1, 10),
    ]

    for index, record in enumerate(records, start=1):
        if index > 1:
            story.append(PageBreak())
        story.append(section_divider(f"{index}. {record.title}", f"{record.domain} / {record.indicator}"))
        story.append(Spacer(1, 8))
        rows = [
            [_para("قبل", heading), _para(record.before_state, normal)],
            [_para("بعد", heading), _para(record.after_state, normal)],
            [_para("نسبة التحسن", heading), _para(f"{record.improvement_rate:+.1f}%", normal)],
            [_para("مستوى الأثر", heading), _para(impact_level_label(record.impact_level), normal)],
        ]
        if record.statistics:
            rows.append([_para("الإحصاءات", heading), _para(record.statistics, normal)])
        if record.test_results:
            rows.append([_para("نتائج الاختبارات", heading), _para(record.test_results, normal)])
        if record.testimonials:
            rows.append([_para("الشهادات", heading), _para(record.testimonials, normal)])
        table = Table(rows, colWidths=[110, 390], hAlign="RIGHT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4efe3")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d8c99e")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 8))
        story.append(_para("سردية الأثر", heading))
        story.append(_para(record.narrative, normal))
        if record.validation_notes:
            story.append(_para("ملاحظات التحقق", heading))
            for note in record.validation_notes:
                story.append(_para(f"- {note}", normal))
        for file_path in record.stored_files:
            path = Path(file_path)
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and path.exists():
                try:
                    image = Image(str(path))
                    ratio = min(430 / image.imageWidth, 300 / image.imageHeight, 1)
                    image.drawWidth = image.imageWidth * ratio
                    image.drawHeight = image.imageHeight * ratio
                    story.append(Spacer(1, 8))
                    story.append(image)
                except Exception:
                    story.append(_para(f"تعذر إدراج الصورة داخل PDF: {path.name}", normal))
            elif path.exists():
                story.append(_para(f"مرفق محفوظ داخل مجلد الأثر: {path.name}", normal))

    header = official_report_header("الملف الذهبي: ملف الأثر")
    doc.build(story, onFirstPage=header, onLaterPages=header)
    return output_path
