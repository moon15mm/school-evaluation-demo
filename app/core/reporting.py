from __future__ import annotations

from pathlib import Path

from app.core.models import DOMAIN_LABELS, VisitRecord


def _arabic_font_path() -> Path | None:
    for candidate in [
        Path("C:/Windows/Fonts/tahoma.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/Arial Unicode MS.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
    ]:
        if candidate.exists():
            return candidate
    return None


def _arabic_bold_font_path() -> Path | None:
    for candidate in [
        Path("C:/Windows/Fonts/tahomabd.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
    ]:
        if candidate.exists():
            return candidate
    return None


def _has_arabic(text: str) -> bool:
    return any("\u0600" <= char <= "\u06ff" or "\ufb50" <= char <= "\ufeff" for char in text)


def _rtl(text: object) -> str:
    value = str(text)
    if not _has_arabic(value):
        return value
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(value))
    except Exception:
        return value


def _para(text: object, style):
    from reportlab.platypus import Paragraph

    return Paragraph(_rtl(text), style)


def ministry_logo_path() -> Path | None:
    for candidate in [
        Path("app/static/assets/moe-logo.png"),
        Path("app/static/assets/moe-logo.jpg"),
        Path("app/static/assets/ministry-logo.png"),
        Path("app/static/assets/ministry-logo.jpg"),
    ]:
        if candidate.exists():
            return candidate
    return None


def register_arabic_fonts(prefix: str = "Arabic") -> tuple[str, str]:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    normal_name = prefix
    bold_name = f"{prefix}-Bold"
    font_path = _arabic_font_path()
    if not font_path:
        return "Helvetica", "Helvetica-Bold"
    if normal_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(normal_name, str(font_path)))
    if bold_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(bold_name, str(_arabic_bold_font_path() or font_path)))
    return normal_name, bold_name


def _draw_rtl(canvas, text: object, x: float, y: float, font: str, size: int, *, align: str = "right", color=None) -> None:
    from reportlab.lib import colors

    canvas.setFont(font, size)
    canvas.setFillColor(color or colors.white)
    value = _rtl(text)
    if align == "center":
        canvas.drawCentredString(x, y, value)
    elif align == "left":
        canvas.drawString(x, y, value)
    else:
        canvas.drawRightString(x, y, value)


def official_report_header(report_title: str, school_name: str = "مدرسة المستقبل الثانوية"):
    from reportlab.lib import colors

    normal_font, bold_font = register_arabic_fonts("HeaderArabic")
    logo_path = ministry_logo_path()

    def _header(canvas, doc):
        width, height = doc.pagesize
        teal = colors.HexColor("#238f86")
        teal_dark = colors.HexColor("#173f4b")
        gold = colors.HexColor("#b18a43")

        canvas.saveState()
        canvas.setFillColor(gold)
        canvas.rect(0, height - 4, width, 4, fill=1, stroke=0)
        canvas.setFillColor(teal)
        canvas.rect(0, height - 68, width, 64, fill=1, stroke=0)
        canvas.setFillColor(teal_dark)
        canvas.rect(0, height - 120, width, 52, fill=1, stroke=0)

        right_x = width - 34
        left_x = 34
        _draw_rtl(canvas, "المملكة العربية السعودية", right_x, height - 20, normal_font, 8)
        _draw_rtl(canvas, "وزارة التعليم", right_x, height - 35, normal_font, 8)
        _draw_rtl(canvas, "الإدارة العامة للتعليم بمنطقة جازان", right_x, height - 52, bold_font, 9)
        _draw_rtl(canvas, "العام الدراسي 1447", left_x, height - 30, normal_font, 8, align="left")
        _draw_rtl(canvas, "الفصل الدراسي الثاني", left_x, height - 46, normal_font, 8, align="left")

        center_x = width / 2
        if logo_path:
            canvas.drawImage(str(logo_path), center_x - 43, height - 62, width=86, height=45, preserveAspectRatio=True, mask="auto")
        else:
            _draw_rtl(canvas, "وزارة التعليم", center_x, height - 37, bold_font, 14, align="center")
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.white)
            canvas.drawCentredString(center_x, height - 51, "Ministry of Education")

        _draw_rtl(canvas, school_name, center_x, height - 88, bold_font, 10, align="center")
        _draw_rtl(canvas, report_title, center_x, height - 111, bold_font, 11, align="center")
        canvas.restoreState()

    return _header


def section_divider(title: str, subtitle: str | None = None):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    normal_font, bold_font = register_arabic_fonts("SectionArabic")
    title_style = ParagraphStyle(
        "SectionDividerTitle",
        fontName=bold_font,
        fontSize=16,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.white,
        wordWrap="RTL",
    )
    subtitle_style = ParagraphStyle(
        "SectionDividerSubtitle",
        fontName=normal_font,
        fontSize=9,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#d8f4ef"),
        wordWrap="RTL",
    )
    content = [Paragraph(_rtl(title), title_style)]
    if subtitle:
        content.append(Spacer(1, 4))
        content.append(Paragraph(_rtl(subtitle), subtitle_style))
    table = Table([[content]], colWidths=[500])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#173f4b")),
                ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor("#b18a43")),
                ("LEFTPADDING", (0, 0), (-1, -1), 18),
                ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                ("TOPPADDING", (0, 0), (-1, -1), 13),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 13),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def build_pdf_report(visit: VisitRecord, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"school-evaluation-report-{visit.id}.pdf"
    try:
        _build_reportlab_pdf(visit, path)
    except Exception:
        _build_plain_pdf_fallback(visit, path)
    return path


def _build_reportlab_pdf(visit: VisitRecord, path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    normal_font, bold_font = register_arabic_fonts("Arabic")

    styles = getSampleStyleSheet()
    styles["Title"].fontName = bold_font
    styles["Heading2"].fontName = bold_font
    styles["Heading3"].fontName = bold_font
    styles["Normal"].fontName = normal_font
    arabic_normal = ParagraphStyle(
        "ArabicNormal",
        parent=styles["Normal"],
        fontName=normal_font,
        alignment=TA_RIGHT,
        leading=15,
        wordWrap="RTL",
    )
    arabic_heading = ParagraphStyle(
        "ArabicHeading",
        parent=styles["Heading2"],
        fontName=bold_font,
        alignment=TA_RIGHT,
        leading=18,
        wordWrap="RTL",
        spaceAfter=8,
    )
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=36, leftMargin=36, topMargin=146, bottomMargin=36)
    story = []

    story.append(_para(f"المدرسة: {visit.school_name}", arabic_normal))
    story.append(Paragraph(f"Visit ID: {visit.id}", styles["Normal"]))
    story.append(Spacer(1, 14))

    if visit.report_profile:
        story.append(section_divider("مرجعية تقرير الزيارة السابقة", "تحليل نتائج الزيارة السابقة وبنود التحسين الحرجة"))
        story.append(Spacer(1, 10))
        story.append(
            _para(
                f"{visit.report_profile.school_name} | {visit.report_profile.report_year} | "
                f"الدرجة العامة: {visit.report_profile.overall_score}% ({visit.report_profile.overall_level})",
                arabic_normal,
            )
        )
        story.append(_para(visit.report_profile.strategic_reading, arabic_normal))
        profile_rows = [[_para("المجال", arabic_normal), "Score", _para("المستوى", arabic_normal)]]
        for domain in visit.report_profile.domains:
            profile_rows.append([_para(domain.name, arabic_normal), domain.score, _para(domain.level, arabic_normal)])
        profile_table = Table(profile_rows, hAlign="LEFT")
        profile_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, -1), normal_font),
                ]
            )
        )
        story.append(profile_table)
        story.append(_para("مؤشرات الأولوية", arabic_heading))
        for indicator in visit.report_profile.improvement_priorities[:8]:
            story.append(
                _para(
                    f"{indicator.code} - {indicator.title} | الدرجة: {indicator.score}% | الاستجابة المطلوبة: {indicator.required_response}",
                    arabic_normal,
                )
            )
        story.append(Spacer(1, 14))

    story.append(section_divider("الملخص التنفيذي", "قراءة مختصرة لحالة المدرسة والتوقع القادم"))
    story.append(Spacer(1, 10))
    story.append(
        _para(
            f"الدرجة المتوقعة في الزيارة القادمة: {visit.prediction.expected_score}/100 "
            f"(الثقة {visit.prediction.confidence:.0%}).",
            arabic_normal,
        )
    )
    story.append(Spacer(1, 10))

    domain_rows = [[_para("المجال", arabic_normal), "Previous", "Current", "Gap"]]
    for domain in visit.domains:
        domain_rows.append([_para(domain.label, arabic_normal), domain.previous_score, domain.current_score, domain.gap])
    table = Table(domain_rows, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b57")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), bold_font),
                ("FONTNAME", (0, 1), (-1, -1), normal_font),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 14))

    story.append(section_divider("نقاط الضعف", "الفجوات التي يجب إغلاقها قبل الزيارة"))
    story.append(Spacer(1, 10))
    for weakness in visit.weaknesses:
        story.append(_para(f"{DOMAIN_LABELS[weakness.domain]} - {weakness.severity}: {weakness.title}", arabic_normal))
        story.append(_para(f"السبب الجذري: {weakness.root_cause}", arabic_normal))
    story.append(Spacer(1, 10))

    story.append(section_divider("خطة التحسين الذكية", "إجراءات عملية مرتبطة بمؤشرات نجاح قابلة للقياس"))
    story.append(Spacer(1, 10))
    for index, action in enumerate(visit.plan, start=1):
        story.append(_para(f"{index}. {action.title} | المسؤول: {action.owner_role} | خلال: {action.due_in_days} يوم", arabic_normal))
        story.append(_para(f"مؤشر النجاح: {action.success_metric}", arabic_normal))
    story.append(Spacer(1, 10))

    story.append(section_divider("محاكاة فريق التقويم", "أسئلة متوقعة وشواهد يجب تجهيزها"))
    story.append(Spacer(1, 10))
    for item in visit.simulation:
        story.append(_para(f"السؤال: {item.question}", arabic_normal))
        story.append(_para(f"الشاهد المتوقع: {item.expected_evidence}", arabic_normal))

    if visit.council_session:
        story.append(Spacer(1, 14))
        story.append(section_divider("جلسة مجلس وكلاء الذكاء", "حوار الوكلاء وقراراتهم النهائية"))
        story.append(Spacer(1, 10))
        story.append(_para(visit.council_session.objective, arabic_normal))
        for turn in visit.council_session.turns:
            story.append(
                _para(
                    f"الجولة {turn.round} - {turn.agent}: {turn.position} التوصية: {turn.recommendation}",
                    arabic_normal,
                )
            )
        story.append(_para("قرارات المجلس", arabic_heading))
        for decision in visit.council_session.decisions:
            story.append(_para(f"{decision.title} | المسؤول: {decision.owner_role} | الموعد: {decision.deadline}", arabic_normal))
            story.append(_para(f"علامة النجاح: {decision.success_signal}", arabic_normal))

    if visit.operational_forms:
        story.append(Spacer(1, 14))
        story.append(section_divider("النماذج التشغيلية", "نماذج العمل التي يستخدمها فريق المدرسة"))
        story.append(Spacer(1, 10))
        for form in visit.operational_forms:
            story.append(_para(f"{form.name} - المسؤول: {form.owner_role}", arabic_normal))
            story.append(_para(f"الغرض: {form.purpose}", arabic_normal))
            story.append(_para(f"الحقول: {', '.join(form.fields)}", arabic_normal))

    if visit.excellence_protocol:
        story.append(Spacer(1, 14))
        story.append(section_divider("بروتوكول التميز", "مراحل الوصول إلى مستوى متقدم في الزيارة القادمة"))
        story.append(Spacer(1, 10))
        story.append(_para(f"الدرجة المستهدفة: {visit.excellence_protocol.target_score}/100", arabic_normal))
        for step in visit.excellence_protocol.steps:
            story.append(_para(f"{step.phase} ({step.day_range})", arabic_heading))
            story.append(_para(f"الإجراءات: {', '.join(step.actions)}", arabic_normal))
            story.append(_para(f"بوابة الانتقال: {step.gate}", arabic_normal))

    if visit.execution_pack:
        story.append(Spacer(1, 14))
        story.append(section_divider("حزمة التنفيذ العملية", "مهام الوكلاء والأدلة الناتجة عنها"))
        story.append(Spacer(1, 10))
        story.append(_para(visit.execution_pack.title, arabic_normal))
        for mission in visit.execution_pack.missions:
            story.append(_para(f"{mission.agent}: {mission.mission}", arabic_heading))
            for artifact in mission.produced_artifacts:
                story.append(_para(f"- {artifact.title} | المسؤول: {artifact.owner_role}", arabic_normal))
            story.append(_para(f"الإجراء البشري التالي: {mission.next_human_action}", arabic_normal))
    header = official_report_header("تقرير التحليل والتحسين المدرسي", visit.school_name)
    doc.build(story, onFirstPage=header, onLaterPages=header)


def _build_plain_pdf_fallback(visit: VisitRecord, path: Path) -> None:
    lines = [
        "Autonomous School Evaluation & Improvement System",
        f"School: {visit.school_name}",
        f"Expected score: {visit.prediction.expected_score}/100",
        "",
        "Domains:",
    ]
    for domain in visit.domains:
        lines.append(f"- {domain.label}: previous {domain.previous_score}, current {domain.current_score}, gap {domain.gap}")
    lines.append("")
    lines.append("Improvement Plan:")
    for action in visit.plan:
        lines.append(f"- {action.title}: {action.success_metric}")
    if visit.report_profile:
        lines.append("")
        lines.append("Previous Visit Reference:")
        lines.append(f"{visit.report_profile.overall_score}% - {visit.report_profile.overall_level}")
        for indicator in visit.report_profile.improvement_priorities[:5]:
            lines.append(f"- {indicator.code}: {indicator.title}")
    if visit.council_session:
        lines.append("")
        lines.append("AI Agent Council:")
        lines.append(visit.council_session.final_consensus)
    if visit.excellence_protocol:
        lines.append("")
        lines.append("Excellence Protocol:")
        lines.append(f"Target score: {visit.excellence_protocol.target_score}/100")
    if visit.execution_pack:
        lines.append("")
        lines.append("Execution Pack:")
        for mission in visit.execution_pack.missions:
            lines.append(f"- {mission.agent}: {mission.mission}")

    content = "\\n".join(lines).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 40 800 Td ({content[:3000]}) Tj ET"
    pdf = (
        "%PDF-1.4\n"
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        f"5 0 obj << /Length {len(stream)} >> stream\n{stream}\nendstream endobj\n"
        "xref\n0 6\n0000000000 65535 f \n"
        "trailer << /Root 1 0 R /Size 6 >>\nstartxref\n0\n%%EOF"
    )
    path.write_bytes(pdf.encode("latin-1", errors="ignore"))
