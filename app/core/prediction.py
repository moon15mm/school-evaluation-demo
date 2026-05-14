from __future__ import annotations

from app.core.models import DomainScore, ImprovementAction, PredictionResult, PredictionScenario


class PredictionAgent:
    def predict(
        self,
        domains: list[DomainScore],
        plan: list[ImprovementAction],
        learning_profile: dict,
    ) -> PredictionResult:
        current_average = sum(item.current_score for item in domains) / len(domains)
        total_gain = sum(item.expected_gain for item in plan)
        success_factor = float(learning_profile.get("average_plan_success", 0.55))
        bias = float(learning_profile.get("prediction_bias", 0.0)) * 0.35

        no_improvement = _clamp(current_average + bias)
        medium = _clamp(current_average + total_gain * 0.35 * success_factor + bias)
        full = _clamp(current_average + total_gain * 0.72 * max(success_factor, 0.65) + bias)
        expected = round((medium * 0.55) + (full * 0.3) + (no_improvement * 0.15), 1)

        confidence = 0.62 if learning_profile.get("prediction_bias", 0.0) == 0 else 0.74
        fastest = sorted(plan, key=lambda item: (-item.expected_gain, item.due_in_days))[:3]
        return PredictionResult(
            expected_score=expected,
            confidence=confidence,
            scenarios=[
                PredictionScenario(
                    name="بدون تحسين",
                    score=round(no_improvement, 1),
                    explanation="استمرار الوضع الحالي دون إغلاق فجوات مؤثرة.",
                ),
                PredictionScenario(
                    name="تحسين متوسط",
                    score=round(medium, 1),
                    explanation="تنفيذ جزئي للإجراءات ذات الأولوية وتحسن محدود في الشواهد.",
                ),
                PredictionScenario(
                    name="تنفيذ كامل للخطة",
                    score=round(full, 1),
                    explanation="إغلاق الفجوات الحرجة وتقديم أدلة حديثة قابلة للتحقق.",
                ),
            ],
            fastest_actions=fastest,
            learning_notes=learning_profile.get("notes", []),
        )


def _clamp(value: float) -> float:
    return max(0, min(100, value))
