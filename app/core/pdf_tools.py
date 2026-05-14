from __future__ import annotations

from pathlib import Path
from unicodedata import normalize


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = normalize("NFKC", "\n".join(parts).strip())
        return text or "لم يتم العثور على نص قابل للاستخراج داخل ملف PDF."
    except Exception as exc:
        return f"تعذر استخراج نص PDF تلقائيًا. السبب: {exc}"
