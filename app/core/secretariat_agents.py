from __future__ import annotations

import re
import shutil
from pathlib import Path

from app.core.evidence_pdf import build_evidence_card_pdf, build_secretariat_decision_pdf
from app.core.models import EvidenceReview, ReportIndicatorProfile, VisitRecord
from app.core.pdf_tools import extract_pdf_text
from app.core.performance_followup import performance_followup_reference


class EvidenceSecretariat:
    agents = [
        "Intake Secretary Agent",
        "Evidence Classifier Agent",
        "Suitability Reviewer Agent",
        "Archive Clerk Agent",
        "Improvement Notes Agent",
    ]

    def review_and_archive(
        self,
        file_path: Path,
        original_filename: str,
        note: str,
        visit: VisitRecord | None,
        evidence_root: Path,
    ) -> EvidenceReview:
        text = self._extract_text(file_path)
        searchable = self._normalize(f"{original_filename}\n{note}\n{text}")
        indicator, score, signals = self._match_indicator(searchable, visit)
        domain = indicator.domain if indicator else self._guess_domain(searchable)
        destination = self._destination_folder(evidence_root, visit, domain, indicator)
        destination.mkdir(parents=True, exist_ok=True)
        stored_path = destination / self._safe_filename(original_filename)
        if stored_path.resolve() != file_path.resolve():
            shutil.copyfile(file_path, stored_path)

        suitability, confidence, edits, opinion = self._judge(
            file_path=file_path,
            text=text,
            note=note,
            indicator=indicator,
            match_score=score,
        )
        review = EvidenceReview(
            visit_id=visit.id if visit else None,
            original_filename=original_filename,
            stored_path=str(stored_path),
            suggested_domain=domain,
            suggested_indicator_code=indicator.code if indicator else None,
            suggested_indicator_title=indicator.title if indicator else None,
            destination_folder=str(destination),
            suitability=suitability,
            confidence=confidence,
            secretariat_opinion=opinion,
            required_edits=edits,
            matched_signals=signals,
            agents=self.agents,
        )
        self._write_management_files(destination, review, note)
        return review

    def _write_management_files(self, destination: Path, review: EvidenceReview, note: str) -> None:
        index_path = destination / "فهرس_الشواهد.txt"
        status = {
            "suitable": "مناسب للاعتماد",
            "needs_edit": "يحتاج تعديل قبل الاعتماد",
            "insufficient": "غير كاف للاعتماد",
        }.get(review.suitability, review.suitability)
        if not index_path.exists():
            index_path.write_text("فهرس الشواهد\n\n", encoding="utf-8")
        with index_path.open("a", encoding="utf-8") as index:
            index.write(
                f"- {review.created_at} | {review.original_filename} | "
                f"{review.suggested_indicator_code or 'غير محدد'} | {status} | {round(review.confidence * 100)}%\n"
            )
        build_evidence_card_pdf(review, note, destination)
        build_secretariat_decision_pdf(review, destination)

    def _extract_text(self, path: Path) -> str:
        if path.suffix.lower() == ".pdf":
            return extract_pdf_text(path)[:4000]
        if path.suffix.lower() in {".txt", ".md", ".csv"}:
            return path.read_text(encoding="utf-8", errors="ignore")[:4000]
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            return self._extract_image_text(path)
        return ""

    def _extract_image_text(self, path: Path) -> str:
        parts = []
        try:
            from PIL import Image

            with Image.open(path) as image:
                width, height = image.size
                parts.append(f"صورة بعرض {width} وارتفاع {height}.")
        except Exception:
            pass
        try:
            import pytesseract

            ocr_text = pytesseract.image_to_string(str(path), lang="ara+eng")
            if ocr_text.strip():
                parts.append(f"نص مستخرج من الصورة: {ocr_text[:3000]}")
        except Exception:
            parts.append("لم تتوفر قراءة OCR عربية للصورة؛ تم الاعتماد على اسم الملف والملاحظة والتحليل الدلالي.")
        return "\n".join(parts)

    def _match_indicator(self, searchable: str, visit: VisitRecord | None) -> tuple[ReportIndicatorProfile | None, int, list[str]]:
        candidates: list[ReportIndicatorProfile] = []
        if visit and visit.report_profile:
            candidates.extend(visit.report_profile.improvement_priorities)
            candidates.extend(visit.report_profile.strengths)
        for item in performance_followup_reference()["indicators"]:
            candidates.append(
                ReportIndicatorProfile(
                    code=f"متابعة-{item['number']}",
                    title=item["question"],
                    domain=item["domain"],
                    score=None,
                    priority="high",
                    required_response=item["required_evidence"],
                )
            )

        direct = self._direct_followup_indicator(searchable)
        if direct:
            return direct, 5, [direct.code, direct.title]

        visual = self._direct_visual_indicator(searchable)
        if visual:
            return visual, 4, [visual.code, visual.title]

        best = None
        best_score = 0
        best_signals: list[str] = []
        for candidate in candidates:
            keywords = self._keywords(candidate)
            signals = [word for word in keywords if word and word in searchable]
            score = len(signals)
            if candidate.code and candidate.code.lower() in searchable:
                score += 4
                signals.append(candidate.code)
            if score > best_score:
                best = candidate
                best_score = score
                best_signals = signals[:8]
        if best_score == 0:
            return None, 0, []
        return best, best_score, best_signals

    def _keywords(self, indicator: ReportIndicatorProfile) -> list[str]:
        text = f"{indicator.title} {indicator.domain} {indicator.required_response}"
        words = re.split(r"[\s،,.؛:()/\\]+|-", text)
        return [word.strip().lower() for word in words if len(word.strip()) >= 4]

    def _direct_followup_indicator(self, searchable: str) -> ReportIndicatorProfile | None:
        rules = [
            (["\u063a\u064a\u0627\u0628", "\u0646\u0648\u0631"], 6),
            (["\u0633\u0644\u0648\u0643", "\u0645\u0634\u0643\u0644\u0629"], 7),
            (["\u0632\u064a\u0627\u0631\u0629", "\u0648\u0644\u064a"], 8),
            (["\u062f\u0639\u0648\u0629", "\u0623\u0648\u0644\u064a\u0627\u0621"], 9),
            (["\u0631\u0627\u0626\u062f", "\u0627\u0644\u0646\u0634\u0627\u0637"], 3),
            (["\u062d\u0635\u0635", "\u0627\u0644\u0646\u0634\u0627\u0637"], 4),
            (["5%", "النشاط"], 5),
            (["\u062e\u0637\u0629", "\u062a\u062d\u0633\u064a\u0646"], 1),
            (["\u062e\u0637\u0629", "\u0623\u0633\u0628\u0648\u0639\u064a\u0629"], 2),
        ]
        indicators = performance_followup_reference()["indicators"]
        for words, number in rules:
            if all(word in searchable for word in words):
                item = next((entry for entry in indicators if entry["number"] == number), None)
                if item:
                    return ReportIndicatorProfile(
                        code=f"\u0645\u062a\u0627\u0628\u0639\u0629-{item['number']}",
                        title=item["question"],
                        domain=item["domain"],
                        score=None,
                        priority="high",
                        required_response=item["required_evidence"],
                    )
        return None

    def _direct_visual_indicator(self, searchable: str) -> ReportIndicatorProfile | None:
        rules = [
            (
                ["نتي", "نتائج", "تحصيل", "اختبار", "درجات", "مهارات", "قراءه", "رياضيات", "علوم", "نافس"],
                ReportIndicatorProfile(
                    code="نواتج-تعلم",
                    title="شواهد نواتج التعلم والتحصيل",
                    domain="نواتج التعلم",
                    score=None,
                    priority="high",
                    required_response="نتائج الطلاب، تحليل الفجوات، قياس قبلي وبعدي، وخطط علاجية مرتبطة بتحسن فعلي.",
                ),
            ),
            (
                ["غياب", "نور", "حضور", "انضباط"],
                ReportIndicatorProfile(
                    code="متابعة-6",
                    title="إجراءات التعامل مع الغياب",
                    domain="التوجيه الطلابي",
                    score=None,
                    priority="high",
                    required_response="أعذار الغياب، إحصائية رصد الغياب من نظام نور، ومحاضر التواصل مع أولياء الأمور.",
                ),
            ),
            (
                ["نشاط", "حصص النشاط", "رائد النشاط", "5%"],
                ReportIndicatorProfile(
                    code="متابعة-5",
                    title="نسبة عدد حصص النشاط",
                    domain="النشاط الطلابي",
                    score=None,
                    priority="high",
                    required_response="بيان بحصص النشاط والجدول المطابق وإجمالي الحصص بما يثبت نسبة 5%.",
                ),
            ),
            (
                ["خطه", "تحسين", "تنفيذ", "توصيات"],
                ReportIndicatorProfile(
                    code="متابعة-1",
                    title="خطة التحسين والتنفيذ",
                    domain="التميز المدرسي",
                    score=None,
                    priority="high",
                    required_response="خطة تحسين المدرسة، خطة التنفيذ الزمني، التوصيات، ومؤشرات المتابعة.",
                ),
            ),
            (
                ["صيانه", "سلامه", "مختبر", "مرافق", "اخلاء"],
                ReportIndicatorProfile(
                    code="بيئة-سلامة",
                    title="شواهد البيئة المدرسية والأمن والسلامة",
                    domain="البيئة المدرسية",
                    score=None,
                    priority="high",
                    required_response="صور أو تقارير سلامة وصيانة موثقة بالتاريخ وتبين قبل/بعد أو إجراء تصحيحي.",
                ),
            ),
        ]
        for words, indicator in rules:
            if any(word in searchable for word in words):
                return indicator
        return None

    def _guess_domain(self, searchable: str) -> str:
        mapping = {
            "نواتج التعلم": ["تحصيلي", "قدرات", "اختبار", "نتائج", "معالجة", "فاقد"],
            "التعليم والتعلم": ["درس", "تقويم", "استراتيجية", "مهارات رقمية", "أداة"],
            "البيئة المدرسية": ["سلامة", "صيانة", "مرافق", "إخلاء", "مختبر"],
            "التوجيه الطلابي": ["غياب", "سلوك", "ولي", "زيارة", "نور"],
            "النشاط الطلابي": ["نشاط", "رائد النشاط", "حصص النشاط"],
            "الإدارة المدرسية": ["خطة", "تحسين", "شراكة", "رخصة", "مجتمعية"],
        }
        for domain, words in mapping.items():
            if any(word in searchable for word in words):
                return domain
        return "صندوق وارد الشواهد"

    def _judge(
        self,
        file_path: Path,
        text: str,
        note: str,
        indicator: ReportIndicatorProfile | None,
        match_score: int,
    ) -> tuple[str, float, list[str], str]:
        edits = []
        suffix = file_path.suffix.lower()
        if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".txt", ".md", ".csv"}:
            edits.append("حوّل الشاهد إلى PDF أو صورة واضحة أو ملف نصي قبل اعتماده.")
        if not indicator:
            edits.append("اكتب في الملاحظة رمز المؤشر أو المجال المرتبط بالشاهد.")
        if suffix in {".png", ".jpg", ".jpeg", ".webp"} and not note.strip():
            edits.append("أضف وصفًا للصورة: التاريخ، مصدر الشاهد، والمؤشر المرتبط بها.")
        if suffix == ".pdf" and len(text.strip()) < 60:
            edits.append("ملف PDF لا يحتوي نصًا واضحًا؛ تأكد أن الصورة/المسح واضحة وأضف وصفًا يدعمها.")
        if indicator and not self._has_date(text + " " + note + " " + file_path.name):
            edits.append("أضف تاريخ الشاهد أو اجعله ظاهرًا في الملف.")

        confidence = min(0.95, 0.35 + match_score * 0.1 + (0.15 if text.strip() else 0) + (0.1 if note.strip() else 0))
        if not indicator or len(edits) >= 3:
            suitability = "insufficient"
            opinion = "الشاهد غير كاف للاعتماد الآن؛ يحتاج تعريفًا أوضح وربطه بمؤشر محدد."
        elif edits:
            suitability = "needs_edit"
            opinion = "الشاهد في المسار الصحيح لكنه يحتاج تعديلًا قبل وضعه في ملف الأدلة النهائي."
        else:
            suitability = "suitable"
            opinion = "الشاهد مناسب مبدئيًا ويمكن وضعه في ملف الأدلة مع مراجعته النهائية قبل الزيارة."
        return suitability, round(confidence, 2), edits, opinion

    def _has_date(self, text: str) -> bool:
        return bool(re.search(r"20\d{2}|14\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", text))

    def _destination_folder(
        self,
        evidence_root: Path,
        visit: VisitRecord | None,
        domain: str,
        indicator: ReportIndicatorProfile | None,
    ) -> Path:
        visit_id = visit.id if visit else "general"
        code = indicator.code if indicator else "unclassified"
        return evidence_root / visit_id / self._slug(domain) / self._slug(code)

    def _safe_filename(self, filename: str) -> str:
        stem = Path(filename).stem
        suffix = Path(filename).suffix.lower()
        return f"{self._slug(stem)[:80]}{suffix}"

    def _slug(self, value: str) -> str:
        cleaned = re.sub(r"[^\w\u0600-\u06FF]+", "_", str(value), flags=re.UNICODE).strip("_")
        return cleaned or "item"

    def _normalize(self, value: str) -> str:
        normalized = value.lower()
        replacements = {
            "أ": "ا",
            "إ": "ا",
            "آ": "ا",
            "ى": "ي",
            "ة": "ه",
            "ـ": "",
            "_": " ",
            "-": " ",
        }
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        return normalized
