from __future__ import annotations

import re
from datetime import date, timedelta

from app.core.models import (
    DOMAIN_LABELS,
    DomainKey,
    DomainScore,
    ImprovementAction,
    SimulationQuestion,
    TeamTask,
    Weakness,
)


POSITIVE_TERMS = [
    "متميز",
    "متقدمة",
    "مرتفع",
    "مكتمل",
    "فعال",
    "منظم",
    "موثق",
    "تحسن",
    "إنجاز",
]
NEGATIVE_TERMS = [
    "ضعف",
    "منخفض",
    "غير مكتمل",
    "غياب",
    "قصور",
    "تدني",
    "محدود",
    "غير موثق",
    "تأخر",
    "فجوة",
]

DOMAIN_KEYWORDS: dict[DomainKey, list[str]] = {
    "leadership": ["قيادة", "مدير", "حوكمة", "رؤية", "خطة تشغيلية", "اجتماع"],
    "teaching": ["تعليم", "معلم", "درس", "استراتيجيات", "تعلم نشط", "تحضير"],
    "learning_outcomes": ["نواتج", "تحصيل", "اختبار", "مهارات", "مؤشرات", "فاقد"],
    "student_support": ["طالب", "إرشاد", "دعم", "موهوب", "تعثر", "غياب"],
    "school_environment": ["بيئة", "سلامة", "مرافق", "نظافة", "انضباط", "أمن"],
    "assessment": ["تقويم", "متابعة", "أدلة", "مؤشر", "قياس", "تحليل"],
    "partnership": ["شراكة", "ولي أمر", "مجتمع", "تواصل", "مبادرة", "مجلس"],
}


def _score_text_for_domain(text: str, domain: DomainKey, base: float) -> float:
    domain_hits = sum(text.count(keyword) for keyword in DOMAIN_KEYWORDS[domain])
    positive_hits = sum(text.count(term) for term in POSITIVE_TERMS)
    negative_hits = sum(text.count(term) for term in NEGATIVE_TERMS)
    score = base + min(domain_hits * 2.3, 12) + positive_hits * 0.7 - negative_hits * 1.2
    return round(max(35, min(92, score)), 1)


def _domain_hit_count(text: str, domain: DomainKey) -> int:
    return sum(text.count(keyword) for keyword in DOMAIN_KEYWORDS[domain])


def _extract_evidence(text: str, domain: DomainKey) -> list[str]:
    sentences = re.split(r"[\n.!؟]+", text)
    evidence = []
    for sentence in sentences:
        clean = sentence.strip()
        if len(clean) < 12:
            continue
        if any(keyword in clean for keyword in DOMAIN_KEYWORDS[domain]):
            evidence.append(clean[:180])
        if len(evidence) == 3:
            break
    return evidence or ["لا توجد شواهد تفصيلية كافية؛ يلزم رفع أدلة مدرسية إضافية."]


class AnalyzerAgent:
    def analyze_previous_report(self, pdf_text: str) -> list[DomainScore]:
        domains = []
        for domain, label in DOMAIN_LABELS.items():
            score = _score_text_for_domain(pdf_text, domain, 58)
            domains.append(
                DomainScore(
                    key=domain,
                    label=label,
                    previous_score=score,
                    current_score=score,
                    gap=0,
                    evidence=_extract_evidence(pdf_text, domain),
                )
            )
        return domains


class ProgressAgent:
    def compare_current_status(self, previous_domains: list[DomainScore], current_status: str) -> list[DomainScore]:
        compared = []
        for item in previous_domains:
            if _domain_hit_count(current_status, item.key) == 0:
                current_score = item.previous_score
                evidence = item.evidence
            else:
                raw_score = _score_text_for_domain(current_status, item.key, item.previous_score)
                max_allowed = item.previous_score + 6
                min_allowed = item.previous_score - 6
                current_score = round(max(min_allowed, min(max_allowed, raw_score)), 1)
                evidence = item.evidence + _extract_evidence(current_status, item.key)[:2]
            compared.append(
                item.model_copy(
                    update={
                        "current_score": current_score,
                        "gap": round(current_score - item.previous_score, 1),
                        "evidence": evidence,
                    }
                )
            )
        return compared


class PlannerAgent:
    def detect_weaknesses(self, domains: list[DomainScore]) -> list[Weakness]:
        weaknesses = []
        for domain in sorted(domains, key=lambda item: item.current_score):
            if domain.current_score >= 78 and domain.gap >= 0:
                continue
            severity = "high" if domain.current_score < 60 or domain.gap < -5 else "medium"
            if domain.current_score > 76:
                severity = "low"
            weaknesses.append(
                Weakness(
                    domain=domain.key,
                    title=f"فجوة في {domain.label}",
                    severity=severity,
                    evidence=domain.evidence[-1],
                    root_cause=_root_cause(domain.key),
                    impact=_impact(domain.key),
                )
            )
        return weaknesses[:7]

    def build_plan(self, weaknesses: list[Weakness], learning_profile: dict) -> list[ImprovementAction]:
        failed_domains = set(learning_profile.get("failed_domains", []))
        actions = []
        for weakness in weaknesses:
            urgent_boost = weakness.domain in failed_domains
            actions.append(
                ImprovementAction(
                    title=_action_title(weakness.domain, urgent_boost),
                    domain=weakness.domain,
                    priority="urgent" if weakness.severity == "high" or urgent_boost else "high",
                    owner_role=_owner_role(weakness.domain),
                    due_in_days=10 if urgent_boost else (14 if weakness.severity == "high" else 30),
                    expected_gain=_expected_gain(weakness.severity, urgent_boost),
                    success_metric=_success_metric(weakness.domain),
                    steps=_action_steps(weakness.domain, urgent_boost),
                )
            )
        return actions


class TaskAgent:
    def assign_tasks(self, plan: list[ImprovementAction], team_members: list[str]) -> list[TeamTask]:
        fallback = ["مدير المدرسة", "وكيل المدرسة", "رائد الجودة", "منسق التقويم", "قائد المجال"]
        members = [item.strip() for item in team_members if item.strip()] or fallback
        tasks = []
        for index, action in enumerate(plan):
            due_date = (date.today() + timedelta(days=action.due_in_days)).isoformat()
            tasks.append(
                TeamTask(
                    action_id=action.id,
                    assignee=members[index % len(members)],
                    role=action.owner_role,
                    deliverable=action.success_metric,
                    due_date=due_date,
                )
            )
        return tasks


class SimulatorAgent:
    def generate_questions(self, weaknesses: list[Weakness]) -> list[SimulationQuestion]:
        questions = []
        for weakness in weaknesses:
            questions.append(
                SimulationQuestion(
                    domain=weakness.domain,
                    question=_simulation_question(weakness.domain),
                    expected_evidence=_success_metric(weakness.domain),
                    risk_level=weakness.severity,
                )
            )
        return questions


def _root_cause(domain: DomainKey) -> str:
    mapping = {
        "leadership": "عدم تحويل مؤشرات التقويم إلى متابعة أسبوعية موثقة.",
        "teaching": "تفاوت تطبيق استراتيجيات التعلم النشط وتحليل أثرها.",
        "learning_outcomes": "ضعف الربط بين نتائج الاختبارات وخطط معالجة الفاقد.",
        "student_support": "عدم كفاية تتبع حالات التعثر والغياب بإجراءات مغلقة.",
        "school_environment": "وجود مؤشرات سلامة وانضباط لا يتم قياسها دوريًا.",
        "assessment": "الأدلة متفرقة ولا توجد لوحة مؤشرات موحدة.",
        "partnership": "الشراكات موجودة لكنها لا ترتبط بمؤشرات أثر قابلة للقياس.",
    }
    return mapping[domain]


def _impact(domain: DomainKey) -> str:
    return f"قد يخفض مجال {DOMAIN_LABELS[domain]} الدرجة الكلية إذا لم تظهر شواهد تحسن حديثة ومقاسة."


def _action_title(domain: DomainKey, urgent_boost: bool) -> str:
    prefix = "مسار إنقاذ سريع" if urgent_boost else "تحسين مركز"
    return f"{prefix}: {DOMAIN_LABELS[domain]}"


def _owner_role(domain: DomainKey) -> str:
    mapping = {
        "leadership": "مدير المدرسة",
        "teaching": "مشرف/منسق التعلم",
        "learning_outcomes": "منسق نواتج التعلم",
        "student_support": "المرشد الطلابي",
        "school_environment": "مسؤول السلامة والانضباط",
        "assessment": "رائد الجودة",
        "partnership": "منسق الشراكة المجتمعية",
    }
    return mapping[domain]


def _expected_gain(severity: str, urgent_boost: bool) -> float:
    base = {"high": 8.0, "medium": 5.0, "low": 2.5}[severity]
    return base + (2.0 if urgent_boost else 0.0)


def _success_metric(domain: DomainKey) -> str:
    mapping = {
        "leadership": "محضر متابعة أسبوعي ولوحة مؤشرات تنفيذ محدثة.",
        "teaching": "زيارات صفية قصيرة وتحليل أثر لاستراتيجيتين على الأقل.",
        "learning_outcomes": "خطة علاجية مرتبطة بنتائج الطلاب وتحسن موثق.",
        "student_support": "سجل حالات التعثر والغياب مع إجراءات مغلقة.",
        "school_environment": "قائمة فحص سلامة وانضباط بنسبة إغلاق لا تقل عن 90%.",
        "assessment": "ملف أدلة رقمي مصنف حسب المجالات والمؤشرات.",
        "partnership": "مبادرتان بشواهد أثر وقياس رضا المستفيدين.",
    }
    return mapping[domain]


def _action_steps(domain: DomainKey, urgent_boost: bool) -> list[str]:
    base = [
        "تجميع الشواهد الحالية وتصنيفها حسب مؤشر التقويم.",
        "تحديد فجوة واحدة قابلة للإغلاق خلال أسبوعين.",
        "تنفيذ إجراء قصير وقياس أثره قبل الزيارة.",
        "توثيق النتيجة في ملف أدلة موحد.",
    ]
    if urgent_boost:
        base.insert(1, "عقد اجتماع تصحيح عاجل وتعيين مالك واحد للمؤشر.")
    return base


def _simulation_question(domain: DomainKey) -> str:
    mapping = {
        "leadership": "كيف تتابع قيادة المدرسة مؤشرات التحسين أسبوعيًا، وما آخر قرار اتخذ بناءً على البيانات؟",
        "teaching": "ما الدليل على أن استراتيجيات التدريس حسنت تعلم الطلاب فعليًا؟",
        "learning_outcomes": "كيف عالجت المدرسة الفاقد التعليمي، وما نسبة التحسن بعد المعالجة؟",
        "student_support": "اعرضوا حالة طالب متعثر: ما الإجراء، ومن تابعه، وما النتيجة؟",
        "school_environment": "ما آخر خطر أو مخالفة بيئية تم إغلاقها، وما الشاهد؟",
        "assessment": "كيف تضمن المدرسة أن الأدلة حديثة ومطابقة لمؤشرات التقويم؟",
        "partnership": "ما أثر الشراكات على تعلم الطلاب أو الانضباط أو الرضا؟",
    }
    return mapping[domain]
