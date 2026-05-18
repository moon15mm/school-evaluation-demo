"""
Improved evaluation pipeline using the official ETEC 4-domain framework.
Drop-in replacement for app/core/pipeline.py — same interface, better accuracy.
"""
from __future__ import annotations

from improved_v2.agents import (
    AnalyzerAgent,
    EvidenceMatcherAgent,
    PlannerAgent,
    PredictionAgent,
    ProgressAgent,
    SimulatorAgent,
)
from improved_v2.etec_reference import DEFAULT_LEVEL, OFFICIAL_DOMAINS, classify_school, domain_label, level_indicator_count


class ImprovedEvaluationPipeline:
    """
    Orchestrates all improved agents in sequence.

    Usage:
        pipeline = ImprovedEvaluationPipeline()
        result = pipeline.run(
            domain_scores={
                "school_management": 72,
                "teaching_learning": 68,
                "learning_outcomes": 55,
                "school_environment": 80,
            },
            previous_scores={...},   # optional
            notes="...",             # optional free text
            weeks_available=8,       # weeks until next visit
        )
    """

    def __init__(self):
        self.analyzer = AnalyzerAgent()
        self.progress = ProgressAgent()
        self.planner = PlannerAgent()
        self.simulator = SimulatorAgent()
        self.predictor = PredictionAgent()
        self.evidence_matcher = EvidenceMatcherAgent()

    def run(
        self,
        domain_scores: dict[str, float],
        previous_scores: dict[str, float] | None = None,
        notes: str = "",
        weeks_available: int = 8,
        school_level: str = DEFAULT_LEVEL,
    ) -> dict:
        # Step 1: Analyze current state
        analysis = self.analyzer.analyze(domain_scores, notes=notes, school_level=school_level)

        # Step 2: Compare with previous visit (if available)
        progress = None
        if previous_scores:
            progress = self.progress.compare(domain_scores, previous_scores)
            previous_overall = progress["overall_previous"]
        else:
            previous_overall = None

        # Step 3: Build improvement plan
        plan = self.planner.build_plan(analysis)

        # Step 4: Simulate evaluation questions
        questions = self.simulator.generate_questions(analysis)

        # Step 5: Predict next visit score
        prediction = self.predictor.predict(domain_scores, plan, weeks_available)

        indicator_count = level_indicator_count(school_level)
        return {
            "framework": f"ETEC تميز — الإطار الرسمي (4 مجالات، {indicator_count} مؤشرًا | {school_level})",
            "school_level": school_level,
            "analysis": analysis,
            "progress": progress,
            "plan": plan,
            "simulation_questions": questions,
            "prediction": prediction,
            "domain_labels": {k: domain_label(k) for k in OFFICIAL_DOMAINS},
        }

    def match_evidence(self, filename: str, note: str, extracted_text: str = "", school_level: str = DEFAULT_LEVEL) -> dict:
        """Match a single uploaded file to an official ETEC indicator."""
        return self.evidence_matcher.match(filename, note, extracted_text, school_level)
