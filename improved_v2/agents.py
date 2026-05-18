"""
Improved agents aligned with the official ETEC 4-domain framework.
All domain references use etec_reference.py instead of the old 7-domain system.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from improved_v2.etec_reference import (
    CLASSIFICATION_LEVELS,
    DEFAULT_LEVEL,
    OFFICIAL_DOMAINS,
    OfficialIndicator,
    classify_school,
    domain_label,
    get_indicators_by_domain,
    match_indicator,
)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class DomainScore:
    domain_key: str
    score: float
    label: str = field(init=False)

    def __post_init__(self):
        self.label = domain_label(self.domain_key)


@dataclass
class Weakness:
    domain_key: str
    indicator: OfficialIndicator
    score: float
    gap: float  # distance from 75% threshold
    impact: str


@dataclass
class ImprovementTarget:
    rank: int
    domain_key: str
    indicator: OfficialIndicator
    current_score: float
    target_score: float
    action: str
    evidence_required: list[str]
    missing_evidence: list[str] = field(default_factory=list)
    achieved_evidence: list[str] = field(default_factory=list)


@dataclass
class SchoolAnalysis:
    overall_score: float
    classification: str
    classification_label: str
    domain_scores: list[DomainScore]
    weaknesses: list[Weakness]
    strengths: list[DomainScore]
    improvement_targets: list[ImprovementTarget]
    prediction: dict
    simulation_questions: list[dict]
    raw_notes: str = ""


# ---------------------------------------------------------------------------
# 1. AnalyzerAgent — replaces the old keyword-counting AnalyzerAgent
# ---------------------------------------------------------------------------

class AnalyzerAgent:
    """
    Analyzes school domain scores using the official ETEC 4-domain structure.
    Scores are provided directly (from a previous report or user input) rather
    than estimated by counting keywords.
    """

    def analyze(
        self,
        domain_scores: dict[str, float],
        previous_overall: float | None = None,
        notes: str = "",
        school_level: str = DEFAULT_LEVEL,
    ) -> dict:
        """
        Args:
            domain_scores: mapping of official domain key → score (0–100).
                           Valid keys: school_management, teaching_learning,
                           learning_outcomes, school_environment
            previous_overall: overall score from the last visit (if any)
            notes: free-text notes from the current visit
        Returns:
            Analysis dict ready for downstream agents.
        """
        validated = self._validate_domains(domain_scores)
        overall = sum(validated.values()) / len(validated) if validated else 0.0
        classification = classify_school(overall)
        domain_objects = [DomainScore(k, v) for k, v in validated.items()]

        weaknesses = self._find_weaknesses(validated, notes, school_level)
        strengths = [d for d in domain_objects if d.score >= 75]

        trend = None
        if previous_overall is not None:
            trend = overall - previous_overall

        return {
            "overall_score": round(overall, 1),
            "classification": classification,
            "classification_label": classification,
            "description": CLASSIFICATION_LEVELS[classification]["description"],
            "domain_scores": domain_objects,
            "weaknesses": weaknesses,
            "strengths": strengths,
            "trend": trend,
            "notes_summary": self._summarize_notes(notes),
        }

    def _validate_domains(self, scores: dict[str, float]) -> dict[str, float]:
        valid_keys = set(OFFICIAL_DOMAINS.keys())
        result = {}
        for key, score in scores.items():
            if key in valid_keys:
                result[key] = max(0.0, min(100.0, float(score)))
            else:
                # Try fuzzy match by Arabic label
                for valid_key, info in OFFICIAL_DOMAINS.items():
                    if key in info["label"]:
                        result[valid_key] = max(0.0, min(100.0, float(score)))
                        break
        # Fill missing domains with 0 so downstream agents always have 4 domains
        for key in OFFICIAL_DOMAINS:
            if key not in result:
                result[key] = 0.0
        return result

    def _find_weaknesses(self, scores: dict[str, float], notes: str, school_level: str = DEFAULT_LEVEL) -> list[Weakness]:
        weaknesses = []
        for domain_key, score in sorted(scores.items(), key=lambda x: x[1]):
            if score < 75:
                indicators = get_indicators_by_domain(domain_key, school_level)
                # Pick the indicator most relevant to any free-text notes
                matches = match_indicator(notes, school_level) if notes.strip() else []
                relevant = matches[0][0] if matches else None
                indicator = relevant if (relevant and relevant.domain == domain_key) else (indicators[0] if indicators else None)
                if indicator:
                    gap = 75.0 - score
                    impact = self._impact_text(domain_key, score, gap)
                    weaknesses.append(Weakness(
                        domain_key=domain_key,
                        indicator=indicator,
                        score=score,
                        gap=gap,
                        impact=impact,
                    ))
        return weaknesses

    def _impact_text(self, domain_key: str, score: float, gap: float) -> str:
        label = domain_label(domain_key)
        return (
            f"مجال {label} حصل على {score:.0f}% وهو دون عتبة الانطلاق (75%). "
            f"الفجوة {gap:.0f} نقطة تعني خطرًا على التصنيف الإجمالي إذا لم تُعالج قبل الزيارة."
        )

    def _summarize_notes(self, notes: str) -> str:
        if not notes.strip():
            return "لا توجد ملاحظات مدخلة."
        sentences = re.split(r"[.،؛\n]+", notes)
        key_sentences = [s.strip() for s in sentences if len(s.strip()) > 15][:4]
        return " | ".join(key_sentences) if key_sentences else notes[:200]


# ---------------------------------------------------------------------------
# 2. PlannerAgent — replaces the old hardcoded-text PlannerAgent
# ---------------------------------------------------------------------------

class PlannerAgent:
    """
    Builds a detailed improvement plan based on weaknesses identified by
    AnalyzerAgent. Each action is tied to an official ETEC indicator with
    its full list of شواهد (evidence items) for actionable guidance.
    """

    URGENCY_WEEKS = {
        "school_management": 3,
        "teaching_learning": 4,
        "learning_outcomes": 6,
        "school_environment": 2,
    }

    # عدد الشواهد المتحققة التقديري بناءً على الدرجة المئوية للمجال
    @staticmethod
    def _estimate_achieved_evidence(score: float, total_evidence: int) -> int:
        """يُقدّر عدد الشواهد المتحققة بناءً على درجة المجال."""
        if total_evidence == 0:
            return 0
        return round(score / 100 * total_evidence)

    def build_plan(self, analysis_result: dict) -> dict:
        weaknesses: list[Weakness] = analysis_result.get("weaknesses", [])
        targets = []
        for rank, weakness in enumerate(weaknesses[:6], start=1):
            ind = weakness.indicator
            achieved = self._estimate_achieved_evidence(weakness.score, ind.evidence_count)
            # الشواهد الناقصة هي الأولى بالعمل
            missing_evidence = ind.evidence_required[achieved:] if achieved < ind.evidence_count else []
            target = ImprovementTarget(
                rank=rank,
                domain_key=weakness.domain_key,
                indicator=ind,
                current_score=weakness.score,
                target_score=min(weakness.score + 15, 100),
                action=self._action(weakness, missing_evidence),
                evidence_required=ind.evidence_required,
                missing_evidence=missing_evidence,
                achieved_evidence=ind.evidence_required[:achieved],
            )
            targets.append(target)

        total_evidence = sum(len(t.missing_evidence) for t in targets)
        return {
            "agent_name": "وكيل التخطيط (المحسَّن)",
            "targets": targets,
            "summary": self._plan_summary(targets, total_evidence),
            "critical_domains": [t.domain_key for t in targets if t.current_score < 60],
            "weeks_to_visit_estimate": self._estimate_weeks(targets),
        }

    def _action(self, weakness: Weakness, missing_evidence: list[str]) -> str:
        domain = weakness.domain_key
        indicator = weakness.indicator
        n_missing = len(missing_evidence)
        first_missing = f"«{missing_evidence[0]}»" if missing_evidence else "الشواهد المطلوبة"
        actions = {
            "school_management": (
                f"وثّق {n_missing} شاهد{'اً' if n_missing != 1 else ''} ناقص في مؤشر «{indicator.code}». "
                f"ابدأ بـ {first_missing}."
            ),
            "teaching_learning": (
                f"نظّم زيارات صفية ووثّق {n_missing} شاهد في مؤشر «{indicator.code}». "
                f"الأولوية لـ {first_missing}."
            ),
            "learning_outcomes": (
                f"حلّل نتائج الاختبارات ووفّر {n_missing} شاهد لمؤشر «{indicator.code}». "
                f"ابدأ بـ {first_missing}."
            ),
            "school_environment": (
                f"افحص {n_missing} متطلب ناقص في مؤشر «{indicator.code}». "
                f"أغلق {first_missing} قبل الزيارة."
            ),
        }
        return actions.get(domain, f"أكمل {n_missing} شاهداً ناقصاً في مؤشر «{indicator.code}».")

    def _plan_summary(self, targets: list[ImprovementTarget], total_missing: int) -> str:
        if not targets:
            return "لا توجد نقاط ضعف بارزة — ركّز على التوثيق وإكمال الشواهد."
        domains = {domain_label(t.domain_key) for t in targets}
        return (
            f"خطة التحسين تشمل {len(targets)} مؤشراً موزعاً على: {' و'.join(domains)}. "
            f"إجمالي الشواهد الناقصة: {total_missing} شاهداً. "
            "الأولوية للمؤشرات التي تقل درجتها عن 60%."
        )

    def _estimate_weeks(self, targets: list[ImprovementTarget]) -> int:
        if not targets:
            return 2
        return max(self.URGENCY_WEEKS.get(t.domain_key, 4) for t in targets)


# ---------------------------------------------------------------------------
# 3. ProgressAgent — now validates domain keys against official framework
# ---------------------------------------------------------------------------

class ProgressAgent:
    """
    Compares current domain scores with previous visit scores.
    Uses official domain keys. Flags suspicious jumps (>15 points).
    """

    MAX_REALISTIC_GAIN = 15.0

    def compare(
        self,
        current_scores: dict[str, float],
        previous_scores: dict[str, float],
    ) -> dict:
        changes = {}
        flags = []
        for domain_key in OFFICIAL_DOMAINS:
            current = current_scores.get(domain_key, 0.0)
            previous = previous_scores.get(domain_key, 0.0)
            delta = current - previous
            if abs(delta) > self.MAX_REALISTIC_GAIN:
                flags.append(
                    f"تغير غير مألوف في {domain_label(domain_key)}: {delta:+.1f} نقطة — تحقق من صحة البيانات."
                )
            changes[domain_key] = {
                "label": domain_label(domain_key),
                "previous": previous,
                "current": current,
                "delta": round(delta, 1),
                "trend": "تحسن" if delta > 0 else ("ثبات" if delta == 0 else "تراجع"),
            }

        overall_current = sum(current_scores.get(k, 0) for k in OFFICIAL_DOMAINS) / 4
        overall_previous = sum(previous_scores.get(k, 0) for k in OFFICIAL_DOMAINS) / 4

        return {
            "agent_name": "وكيل المقارنة والتقدم (المحسَّن)",
            "domain_changes": changes,
            "overall_current": round(overall_current, 1),
            "overall_previous": round(overall_previous, 1),
            "overall_delta": round(overall_current - overall_previous, 1),
            "current_classification": classify_school(overall_current),
            "previous_classification": classify_school(overall_previous),
            "flags": flags,
        }


# ---------------------------------------------------------------------------
# 4. SimulatorAgent — generates questions tied to official indicators
# ---------------------------------------------------------------------------

class SimulatorAgent:
    """
    Generates evaluation team simulation questions based on weak indicators.
    Questions are derived from official ETEC indicator titles and evidence lists.
    """

    def generate_questions(self, analysis_result: dict) -> list[dict]:
        weaknesses: list[Weakness] = analysis_result.get("weaknesses", [])
        questions = []

        for weakness in weaknesses[:8]:
            indicator = weakness.indicator
            questions.append({
                "domain": domain_label(weakness.domain_key),
                "indicator_code": indicator.code,
                "indicator_title": indicator.title,
                "question": self._question_for(indicator, weakness.score),
                "expected_evidence": indicator.evidence_required,
                "score": weakness.score,
            })

        if not questions:
            questions = self._general_questions()

        return questions

    def _question_for(self, indicator: OfficialIndicator, score: float) -> str:
        difficulty = "متقدم" if score >= 60 else "أساسي"
        return (
            f"[{difficulty}] كيف تُوثّق المدرسة أداءها في مؤشر «{indicator.title}» "
            f"(الرمز: {indicator.code})؟ وما الشواهد التي تُثبت التحسين؟"
        )

    def _general_questions(self) -> list[dict]:
        return [
            {
                "domain": "عام",
                "indicator_code": "—",
                "indicator_title": "الجاهزية العامة للزيارة",
                "question": "هل خطة التحسين المدرسية محدّثة وتعكس نتائج الزيارة السابقة؟",
                "expected_evidence": ["خطة التحسين", "محاضر الاجتماعات", "تقارير المتابعة"],
                "score": None,
            }
        ]


# ---------------------------------------------------------------------------
# 5. PredictionAgent — replaces the hardcoded confidence=0.62 agent
# ---------------------------------------------------------------------------

class PredictionAgent:
    """
    Predicts the expected overall score for the next visit based on current
    scores, improvement targets, and realistic gain estimates.
    Confidence is calculated from data quality, not hardcoded.
    """

    DOMAIN_GAIN_CEILING = {
        "school_management": 12,
        "teaching_learning": 10,
        "school_environment": 14,
        "learning_outcomes": 8,
    }

    def predict(
        self,
        current_scores: dict[str, float],
        plan_result: dict,
        weeks_available: int = 8,
    ) -> dict:
        targets: list[ImprovementTarget] = plan_result.get("targets", [])
        domain_predictions = {}
        gains = []

        for domain_key in OFFICIAL_DOMAINS:
            current = current_scores.get(domain_key, 0.0)
            ceiling = self.DOMAIN_GAIN_CEILING.get(domain_key, 10)
            target_obj = next((t for t in targets if t.domain_key == domain_key), None)

            if target_obj:
                potential_gain = min(target_obj.target_score - current, ceiling)
                weeks_ratio = min(weeks_available / 8, 1.0)
                realistic_gain = potential_gain * weeks_ratio * 0.7
            else:
                realistic_gain = 0.0

            predicted = min(current + realistic_gain, 100.0)
            domain_predictions[domain_key] = {
                "label": domain_label(domain_key),
                "current": current,
                "predicted": round(predicted, 1),
                "gain": round(realistic_gain, 1),
            }
            gains.append(realistic_gain)

        overall_current = sum(current_scores.get(k, 0) for k in OFFICIAL_DOMAINS) / 4
        overall_predicted = sum(v["predicted"] for v in domain_predictions.values()) / 4
        confidence = self._compute_confidence(current_scores, targets, weeks_available)

        return {
            "agent_name": "وكيل التنبؤ (المحسَّن)",
            "overall_current": round(overall_current, 1),
            "overall_predicted": round(overall_predicted, 1),
            "overall_gain": round(overall_predicted - overall_current, 1),
            "current_classification": classify_school(overall_current),
            "predicted_classification": classify_school(overall_predicted),
            "domain_predictions": domain_predictions,
            "confidence": confidence,
            "confidence_explanation": self._confidence_label(confidence),
            "weeks_available": weeks_available,
            "caveat": "التنبؤ تقديري ويعتمد على التزام المدرسة بتنفيذ خطة التحسين كاملًا.",
        }

    def _compute_confidence(
        self,
        scores: dict[str, float],
        targets: list[ImprovementTarget],
        weeks: int,
    ) -> float:
        base = 0.45
        # More domains with real scores → higher confidence
        filled_domains = sum(1 for v in scores.values() if v > 0)
        base += filled_domains * 0.05
        # More targets defined → better planning → higher confidence
        base += min(len(targets) * 0.03, 0.12)
        # More time → more realistic
        base += min(weeks / 40, 0.10)
        return round(min(base, 0.88), 2)

    def _confidence_label(self, confidence: float) -> str:
        if confidence >= 0.75:
            return "ثقة عالية — البيانات كاملة والخطة واضحة."
        if confidence >= 0.60:
            return "ثقة متوسطة — بعض المجالات تحتاج بيانات أوفى."
        return "ثقة منخفضة — أدخل درجات جميع المجالات لتحسين الدقة."


# ---------------------------------------------------------------------------
# 6. EvidenceMatcherAgent — new agent using official indicator codes
# ---------------------------------------------------------------------------

class EvidenceMatcherAgent:
    """
    Matches uploaded evidence files to official ETEC indicators by code and keywords.
    Replaces the keyword-heavy logic in EvidenceSecretariat with official references.
    """

    def match(self, filename: str, note: str, extracted_text: str = "", school_level: str = DEFAULT_LEVEL) -> dict:
        combined = f"{filename} {note} {extracted_text}".strip()
        matches = match_indicator(combined, school_level)
        indicator = matches[0][0] if matches else None
        if indicator:
            return {
                "matched": True,
                "indicator_code": indicator.code,
                "indicator_title": indicator.title,
                "domain": domain_label(indicator.domain),
                "required_evidence": indicator.evidence_required,
                "guidance": f"هذا الشاهد يرتبط بمؤشر «{indicator.title}» ({indicator.code}). "
                            f"تأكد من توافر: {' و'.join(indicator.evidence_required[:3])}.",
            }
        return {
            "matched": False,
            "indicator_code": None,
            "indicator_title": None,
            "domain": None,
            "required_evidence": [],
            "guidance": "لم يُطابَق الشاهد بمؤشر رسمي. أضف رمز المؤشر في اسم الملف أو الملاحظة.",
        }
