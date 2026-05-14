from __future__ import annotations

import json
from pathlib import Path

from app.core.models import EvidenceReview, ImpactRecord, LiveCouncilEvent, OutcomeUpdate, TaskStatusUpdate, VisitRecord


class SchoolMemory:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps({"visits": [], "evidence_reviews": [], "impact_records": [], "council_events": []}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8-sig"))

    def _write(self, payload: dict) -> None:
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def clear_operational_data(self) -> None:
        self._write({"visits": [], "evidence_reviews": [], "impact_records": [], "council_events": []})

    def all_visits(self) -> list[VisitRecord]:
        return [VisitRecord(**item) for item in self._read().get("visits", [])]

    def latest_visits(self, limit: int = 5) -> list[VisitRecord]:
        return self.all_visits()[-limit:]

    def latest_visit(self) -> VisitRecord | None:
        visits = self.all_visits()
        return visits[-1] if visits else None

    def save_visit(self, visit: VisitRecord) -> VisitRecord:
        data = self._read()
        data.setdefault("visits", []).append(visit.model_dump())
        self._write(data)
        return visit

    def save_evidence_review(self, review: EvidenceReview) -> EvidenceReview:
        data = self._read()
        data.setdefault("evidence_reviews", []).append(review.model_dump())
        self._write(data)
        return review

    def latest_evidence_reviews(self, limit: int = 20) -> list[EvidenceReview]:
        return [EvidenceReview(**item) for item in self._read().get("evidence_reviews", [])][-limit:]

    def save_impact_record(self, record: ImpactRecord) -> ImpactRecord:
        data = self._read()
        data.setdefault("impact_records", []).append(record.model_dump())
        self._write(data)
        return record

    def latest_impact_records(self, limit: int = 50) -> list[ImpactRecord]:
        return [ImpactRecord(**item) for item in self._read().get("impact_records", [])][-limit:]

    def delete_impact_record(self, record_id: str) -> ImpactRecord | None:
        data = self._read()
        remaining = []
        deleted = None
        for item in data.get("impact_records", []):
            if item.get("id") == record_id:
                deleted = ImpactRecord(**item)
            else:
                remaining.append(item)
        if deleted:
            data["impact_records"] = remaining
            self._write(data)
        return deleted

    def save_council_event(self, event: LiveCouncilEvent) -> LiveCouncilEvent:
        data = self._read()
        data.setdefault("council_events", []).append(event.model_dump())
        self._write(data)
        return event

    def latest_council_events(self, visit_id: str | None = None, limit: int = 30) -> list[LiveCouncilEvent]:
        events = [LiveCouncilEvent(**item) for item in self._read().get("council_events", [])]
        if visit_id:
            events = [event for event in events if event.visit_id == visit_id]
        return events[-limit:]

    def delete_evidence_review(self, review_id: str) -> EvidenceReview | None:
        data = self._read()
        remaining = []
        deleted = None
        for item in data.get("evidence_reviews", []):
            if item.get("id") == review_id:
                deleted = EvidenceReview(**item)
            else:
                remaining.append(item)
        if deleted:
            data["evidence_reviews"] = remaining
            self._write(data)
        return deleted

    def update_outcome(self, visit_id: str, outcome: OutcomeUpdate) -> VisitRecord | None:
        data = self._read()
        for index, item in enumerate(data.get("visits", [])):
            if item["id"] == visit_id:
                item["actual_score"] = outcome.actual_score
                item["plan_success_rate"] = outcome.plan_success_rate
                data["visits"][index] = item
                self._write(data)
                return VisitRecord(**item)
        return None

    def update_task_status(self, visit_id: str, action_id: str, update: TaskStatusUpdate) -> VisitRecord | None:
        data = self._read()
        for visit_index, visit in enumerate(data.get("visits", [])):
            if visit["id"] != visit_id:
                continue
            for task_index, task in enumerate(visit.get("tasks", [])):
                if task.get("action_id") == action_id:
                    task["status"] = update.status
                    visit["tasks"][task_index] = task
                    data["visits"][visit_index] = visit
                    self._write(data)
                    return VisitRecord(**visit)
            return None
        return None

    def learning_profile(self) -> dict:
        visits = [visit for visit in self.all_visits() if visit.actual_score is not None]
        if not visits:
            return {
                "prediction_bias": 0.0,
                "average_plan_success": 0.55,
                "failed_domains": [],
                "notes": ["لا توجد نتائج زيارات سابقة مؤكدة بعد؛ سيتم استخدام نموذج تقديري محافظ."],
            }

        prediction_errors = [visit.actual_score - visit.prediction.expected_score for visit in visits]
        avg_bias = sum(prediction_errors) / len(prediction_errors)
        success_values = [visit.plan_success_rate for visit in visits if visit.plan_success_rate is not None]
        avg_success = sum(success_values) / len(success_values) if success_values else 0.55

        failed_domains: dict[str, int] = {}
        for visit in visits:
            if visit.plan_success_rate is not None and visit.plan_success_rate < 0.55:
                for weakness in visit.weaknesses:
                    failed_domains[weakness.domain] = failed_domains.get(weakness.domain, 0) + 1

        ordered_failed = sorted(failed_domains, key=failed_domains.get, reverse=True)
        return {
            "prediction_bias": round(avg_bias, 2),
            "average_plan_success": round(avg_success, 2),
            "failed_domains": ordered_failed[:3],
            "notes": [
                f"انحراف التوقع التاريخي: {avg_bias:+.1f} درجة.",
                f"متوسط نجاح تنفيذ الخطط السابقة: {avg_success:.0%}.",
            ],
        }
