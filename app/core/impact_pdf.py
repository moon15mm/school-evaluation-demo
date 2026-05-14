from __future__ import annotations

from pathlib import Path
import re

from app.core.models import ImpactRecord
from app.core.reporting import _para, _rtl, official_report_header, register_arabic_fonts, section_divider


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
        chart = _impact_chart(record, normal_font, bold_font)
        if chart:
            story.append(chart)
            story.append(Spacer(1, 10))
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


def _impact_chart(record: ImpactRecord, normal_font: str, bold_font: str):
    from reportlab.graphics.shapes import Drawing, Line, Rect, String
    from reportlab.lib import colors
    from reportlab.platypus import KeepTogether, Spacer

    before = _extract_percent(record.before_state)
    after = _extract_percent(record.after_state)
    if before is None and after is None:
        if record.improvement_rate == 0:
            return None
        before = max(0, min(100, 100 - abs(record.improvement_rate)))
        after = max(0, min(100, before + record.improvement_rate))
    elif before is None:
        before = max(0, min(100, (after or 0) - record.improvement_rate))
    elif after is None:
        after = max(0, min(100, before + record.improvement_rate))

    before = max(0, min(100, float(before)))
    after = max(0, min(100, float(after)))
    gain = after - before

    width = 500
    height = 170
    drawing = Drawing(width, height)
    teal_dark = colors.HexColor("#173f4b")
    teal = colors.HexColor("#238f86")
    gold = colors.HexColor("#b18a43")
    pale = colors.HexColor("#f4efe3")
    grid = colors.HexColor("#d8c99e")

    drawing.add(Rect(0, 0, width, height, fillColor=colors.white, strokeColor=grid, strokeWidth=0.7))
    drawing.add(Rect(0, height - 32, width, 32, fillColor=teal_dark, strokeColor=teal_dark))
    drawing.add(String(width / 2, height - 22, _rtl("مؤشر الأثر الرقمي"), textAnchor="middle", fontName=bold_font, fontSize=13, fillColor=colors.white))

    chart_left = 76
    chart_bottom = 38
    chart_width = 275
    chart_height = 84
    drawing.add(Line(chart_left, chart_bottom, chart_left + chart_width, chart_bottom, strokeColor=grid, strokeWidth=1))
    for tick in [0, 25, 50, 75, 100]:
        x = chart_left + (tick / 100) * chart_width
        drawing.add(Line(x, chart_bottom, x, chart_bottom + chart_height, strokeColor=colors.HexColor("#edf0ef"), strokeWidth=0.5))
        drawing.add(String(x, chart_bottom - 14, f"{tick}%", textAnchor="middle", fontName=normal_font, fontSize=7, fillColor=colors.HexColor("#52616f")))

    before_width = (before / 100) * chart_width
    after_width = (after / 100) * chart_width
    drawing.add(Rect(chart_left, chart_bottom + 52, before_width, 18, fillColor=pale, strokeColor=gold))
    drawing.add(Rect(chart_left, chart_bottom + 18, after_width, 18, fillColor=teal, strokeColor=teal))
    drawing.add(String(chart_left - 12, chart_bottom + 57, _rtl("قبل"), textAnchor="end", fontName=bold_font, fontSize=10, fillColor=teal_dark))
    drawing.add(String(chart_left - 12, chart_bottom + 23, _rtl("بعد"), textAnchor="end", fontName=bold_font, fontSize=10, fillColor=teal_dark))
    drawing.add(String(chart_left + before_width + 8, chart_bottom + 56, f"{before:.1f}%", fontName=bold_font, fontSize=9, fillColor=teal_dark))
    drawing.add(String(chart_left + after_width + 8, chart_bottom + 22, f"{after:.1f}%", fontName=bold_font, fontSize=9, fillColor=teal_dark))

    badge_x = 378
    drawing.add(Rect(badge_x, chart_bottom + 13, 100, 74, fillColor=colors.HexColor("#eef8f5"), strokeColor=teal))
    drawing.add(String(badge_x + 50, chart_bottom + 61, _rtl("نسبة التحسن"), textAnchor="middle", fontName=bold_font, fontSize=10, fillColor=teal_dark))
    drawing.add(String(badge_x + 50, chart_bottom + 34, f"{gain:+.1f}%", textAnchor="middle", fontName=bold_font, fontSize=18, fillColor=teal))
    drawing.add(String(badge_x + 50, chart_bottom + 17, _rtl(impact_level_label(record.impact_level)), textAnchor="middle", fontName=normal_font, fontSize=7, fillColor=colors.HexColor("#52616f")))

    return KeepTogether([drawing, Spacer(1, 4)])


def _extract_percent(text: str) -> float | None:
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*%", text)
    if not matches:
        return None
    return float(matches[-1])
