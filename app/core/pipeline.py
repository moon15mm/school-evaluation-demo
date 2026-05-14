from __future__ import annotations

from pathlib import Path

from app.core.agents import AnalyzerAgent, PlannerAgent, ProgressAgent, SimulatorAgent, TaskAgent
from app.core.council import AgentCouncil
from app.core.execution_agents import ExecutionAgentTeam
from app.core.external_evaluation import ExternalEvaluationAdvisor
from app.core.memory import SchoolMemory
from app.core.models import AnalysisRequest, SchoolReportProfile, VisitRecord
from app.core.prediction import PredictionAgent
from app.core.report_reference import build_school_report_profile, domain_scores_from_report_profile
from app.core.reporting import build_pdf_report


class EvaluationPipeline:
    def __init__(self, memory: SchoolMemory, reports_dir: Path, execution_dir: Path) -> None:
        self.memory = memory
        self.reports_dir = reports_dir
        self.execution_dir = execution_dir
        self.analyzer = AnalyzerAgent()
        self.progress = ProgressAgent()
        self.planner = PlannerAgent()
        self.task_agent = TaskAgent()
        self.simulator = SimulatorAgent()
        self.predictor = PredictionAgent()
        self.council = AgentCouncil()
        self.execution_team = ExecutionAgentTeam()
        self.external_advisor = ExternalEvaluationAdvisor()

    def run(
        self,
        request: AnalysisRequest,
        pdf_text: str,
        pdf_filename: str | None,
        report_profile_override: SchoolReportProfile | None = None,
    ) -> VisitRecord:
        report_profile = report_profile_override or build_school_report_profile(pdf_text)
        previous_domains = (
            domain_scores_from_report_profile(report_profile)
            if report_profile
            else self.analyzer.analyze_previous_report(pdf_text)
        )
        domains = self.progress.compare_current_status(previous_domains, request.current_status)
        learning_profile = self.memory.learning_profile()
        weaknesses = self.planner.detect_weaknesses(domains)
        plan = self.planner.build_plan(weaknesses, learning_profile)
        tasks = self.task_agent.assign_tasks(plan, request.team_members)
        simulation = self.simulator.generate_questions(weaknesses)
        prediction = self.predictor.predict(domains, plan, learning_profile)
        council_session, operational_forms, excellence_protocol = self.council.conduct_session(
            domains,
            weaknesses,
            plan,
            tasks,
            simulation,
            prediction,
            report_profile,
        )
        external_readiness = self.external_advisor.build(domains, weaknesses, plan, request.current_status, report_profile)

        visit = VisitRecord(
            school_name=request.school_name,
            pdf_filename=pdf_filename,
            previous_report_excerpt=pdf_text[:2000],
            report_profile=report_profile,
            current_status=request.current_status,
            domains=domains,
            weaknesses=weaknesses,
            plan=plan,
            tasks=tasks,
            simulation=simulation,
            prediction=prediction,
            council_session=council_session,
            operational_forms=operational_forms,
            excellence_protocol=excellence_protocol,
            external_readiness=external_readiness,
        )
        visit.execution_pack = self.execution_team.build_pack(visit, self.execution_dir)
        report_path = build_pdf_report(visit, self.reports_dir)
        visit.report_path = str(report_path)
        return self.memory.save_visit(visit)
