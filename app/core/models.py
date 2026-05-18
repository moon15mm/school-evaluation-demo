from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


DomainKey = Literal[
    # ── المجالات الأربعة الرسمية ETEC ────────────────────────
    "school_management",
    "teaching_learning",
    "learning_outcomes",
    "school_environment",
    # ── المجالات القديمة (للتوافق مع الإصدارات السابقة) ─────
    "leadership",
    "teaching",
    "student_support",
    "assessment",
    "partnership",
]


DOMAIN_LABELS: dict[str, str] = {
    # ETEC v2
    "school_management":  "الإدارة المدرسية",
    "teaching_learning":  "التعليم والتعلم",
    "learning_outcomes":  "نواتج التعلم",
    "school_environment": "البيئة المدرسية",
    # Legacy
    "leadership":   "القيادة المدرسية",
    "teaching":     "جودة التعليم والتعلم",
    "student_support": "الدعم الطلابي",
    "assessment":   "التقويم والمتابعة",
    "partnership":  "الشراكة المجتمعية",
}


class DomainScore(BaseModel):
    key: DomainKey
    label: str
    previous_score: float = Field(ge=0, le=100)
    current_score: float = Field(ge=0, le=100)
    gap: float
    evidence: list[str] = Field(default_factory=list)


class Weakness(BaseModel):
    domain: DomainKey
    title: str
    severity: Literal["high", "medium", "low"]
    evidence: str
    root_cause: str
    impact: str


class ImprovementAction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    domain: DomainKey
    priority: Literal["urgent", "high", "medium"]
    owner_role: str
    due_in_days: int = Field(ge=1, le=120)
    expected_gain: float = Field(ge=0, le=20)
    success_metric: str
    steps: list[str]


class TeamTask(BaseModel):
    action_id: str
    assignee: str
    role: str
    deliverable: str
    due_date: str
    status: Literal["new", "in_progress", "done"] = "new"


class SimulationQuestion(BaseModel):
    domain: DomainKey
    question: str
    expected_evidence: str
    risk_level: Literal["high", "medium", "low"]


class PredictionScenario(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    explanation: str


class PredictionResult(BaseModel):
    expected_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    scenarios: list[PredictionScenario]
    fastest_actions: list[ImprovementAction]
    learning_notes: list[str]


class ReportDomainProfile(BaseModel):
    name: str
    score: float
    level: str
    interpretation: str


class ReportIndicatorProfile(BaseModel):
    code: str
    title: str
    domain: str
    score: float | None = None
    priority: Literal["critical", "high", "medium"]
    required_response: str


class SchoolReportProfile(BaseModel):
    report_year: str
    school_name: str
    evaluation_date: str
    overall_score: float
    overall_level: str
    level_bands: list[str]
    visit_mechanism: list[str]
    domains: list[ReportDomainProfile]
    strengths: list[ReportIndicatorProfile]
    improvement_priorities: list[ReportIndicatorProfile]
    strategic_reading: str


class CouncilTurn(BaseModel):
    round: int
    agent: str
    position: str
    evidence: str
    recommendation: str


class CouncilDecision(BaseModel):
    title: str
    rationale: str
    owner_role: str
    deadline: str
    success_signal: str


class AgentCouncilSession(BaseModel):
    session_title: str
    objective: str
    turns: list[CouncilTurn]
    disagreements: list[str]
    decisions: list[CouncilDecision]
    final_consensus: str


class LiveCouncilEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    visit_id: str | None = None
    event_type: Literal["analysis", "evidence", "impact", "task", "outcome", "system"]
    title: str
    summary: str
    agent_positions: list[CouncilTurn] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    severity: Literal["info", "watch", "warning", "critical"] = "info"


class OperationalForm(BaseModel):
    name: str
    purpose: str
    owner_role: str
    fields: list[str]
    review_frequency: str
    completion_rule: str


class ProtocolStep(BaseModel):
    phase: str
    day_range: str
    actions: list[str]
    required_evidence: list[str]
    gate: str


class ExcellenceProtocol(BaseModel):
    title: str
    target_score: float = Field(ge=0, le=100)
    operating_principles: list[str]
    steps: list[ProtocolStep]
    daily_ritual: list[str]
    escalation_rules: list[str]
    visit_day_protocol: list[str]


class ExternalReadinessDimension(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    evaluator_question: str
    evidence_required: list[str]
    failure_signal: str
    excellence_signal: str
    immediate_actions: list[str]


class ExternalVisitPhase(BaseModel):
    phase: str
    weight: float = Field(ge=0, le=1)
    objective: str
    checklist: list[str]
    owner: str


class EvaluatorProbe(BaseModel):
    target: str
    question: str
    what_good_answer_contains: list[str]
    evidence_to_show: list[str]
    risk_if_weak: str


class EvaluationScheduleItem(BaseModel):
    time_window: str
    activity: str
    evaluator_focus: str
    school_owner: str
    expected_outputs: list[str]


class ClassroomObservationScenario(BaseModel):
    subject_or_context: str
    evaluator_look_for: list[str]
    likely_questions: list[str]
    excellence_response: str
    red_flags: list[str]
    evidence_to_prepare: list[str]


class InterviewDrill(BaseModel):
    audience: str
    opening_question: str
    follow_up_questions: list[str]
    answer_formula: list[str]
    evidence_to_hold: list[str]
    avoid: list[str]


class DocumentAuditItem(BaseModel):
    file_name: str
    evaluator_test: str
    required_artifacts: list[str]
    pass_condition: str
    failure_pattern: str


class TriangulationCheck(BaseModel):
    claim: str
    document_proof: str
    field_proof: str
    student_or_result_proof: str
    verdict_rule: str


class ExternalEvaluationReadiness(BaseModel):
    overall_readiness: float = Field(ge=0, le=100)
    guarantee_level: Literal["high_risk", "promising", "ready", "excellence_ready"]
    evaluator_mindset: list[str]
    dimensions: list[ExternalReadinessDimension]
    phases: list[ExternalVisitPhase]
    probes: list[EvaluatorProbe]
    visit_schedule: list[EvaluationScheduleItem] = Field(default_factory=list)
    classroom_observations: list[ClassroomObservationScenario] = Field(default_factory=list)
    interview_drills: list[InterviewDrill] = Field(default_factory=list)
    document_audit: list[DocumentAuditItem] = Field(default_factory=list)
    triangulation_checks: list[TriangulationCheck] = Field(default_factory=list)
    top_failure_risks: list[str]
    guarantee_protocol: list[str]
    weekly_battle_rhythm: list[str]


class ExecutionArtifact(BaseModel):
    title: str
    artifact_type: Literal["evidence_file", "checklist", "weekly_plan", "interview_script", "tracking_sheet", "brief"]
    owner_role: str
    purpose: str
    file_path: str | None = None
    content: str


class ExecutionMission(BaseModel):
    agent: str
    mission: str
    produced_artifacts: list[ExecutionArtifact]
    next_human_action: str


class ExecutionPack(BaseModel):
    title: str
    folder_path: str | None = None
    download_url: str | None = None
    missions: list[ExecutionMission]
    operating_cycle: list[str]
    readiness_checkpoints: list[str]


class AnalysisRequest(BaseModel):
    school_name: str = ""
    current_status: str
    team_members: list[str] = Field(default_factory=list)


class VisitRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    school_name: str
    school_level: str = "ثانوي"
    pdf_filename: str | None = None
    previous_report_excerpt: str
    report_profile: SchoolReportProfile | None = None
    current_status: str
    domains: list[DomainScore]
    weaknesses: list[Weakness]
    plan: list[ImprovementAction]
    tasks: list[TeamTask]
    simulation: list[SimulationQuestion]
    prediction: PredictionResult
    council_session: AgentCouncilSession | None = None
    operational_forms: list[OperationalForm] = Field(default_factory=list)
    excellence_protocol: ExcellenceProtocol | None = None
    external_readiness: ExternalEvaluationReadiness | None = None
    execution_pack: ExecutionPack | None = None
    report_path: str | None = None
    actual_score: float | None = None
    plan_success_rate: float | None = None


class AnalysisResponse(BaseModel):
    visit: VisitRecord
    report_url: str


class OutcomeUpdate(BaseModel):
    actual_score: float = Field(ge=0, le=100)
    plan_success_rate: float = Field(ge=0, le=1)


class TaskStatusUpdate(BaseModel):
    status: Literal["new", "in_progress", "done"]


class EvidenceReview(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    visit_id: str | None = None
    original_filename: str
    stored_path: str
    suggested_domain: str
    suggested_indicator_code: str | None = None
    suggested_indicator_title: str | None = None
    destination_folder: str
    suitability: Literal["suitable", "needs_edit", "insufficient"]
    confidence: float = Field(ge=0, le=1)
    secretariat_opinion: str
    required_edits: list[str] = Field(default_factory=list)
    matched_signals: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)


class ImpactRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    visit_id: str | None = None
    title: str
    domain: str
    indicator: str
    before_state: str
    after_state: str
    improvement_rate: float = Field(ge=-100, le=100)
    statistics: str = ""
    test_results: str = ""
    testimonials: str = ""
    narrative: str
    impact_level: Literal["limited", "clear", "strong", "golden"]
    validation_notes: list[str] = Field(default_factory=list)
    stored_files: list[str] = Field(default_factory=list)
