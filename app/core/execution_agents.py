from __future__ import annotations

import re
from pathlib import Path

from app.core.models import (
    ExecutionArtifact,
    ExecutionMission,
    ExecutionPack,
    ImprovementAction,
    OperationalForm,
    SchoolReportProfile,
    TeamTask,
    VisitRecord,
)
from app.core.performance_followup import performance_followup_reference


class ExecutionAgentTeam:
    def build_pack(self, visit: VisitRecord, output_root: Path) -> ExecutionPack:
        folder = output_root / visit.id
        folder.mkdir(parents=True, exist_ok=True)

        missions = [
            self._evidence_agent(visit),
            self._performance_followup_agent(visit),
            self._achievement_agent(visit),
            self._environment_agent(visit),
            self._teaching_agent(visit),
            self._interview_agent(visit),
            self._followup_agent(visit),
        ]

        for mission in missions:
            for artifact in mission.produced_artifacts:
                filename = f"{_slug(artifact.title)}.md"
                path = folder / filename
                path.write_text(artifact.content, encoding="utf-8")
                artifact.file_path = str(path)

        index = self._build_index(visit, missions)
        index_path = folder / "00_execution_pack_index.md"
        index_path.write_text(index, encoding="utf-8")

        return ExecutionPack(
            title="حزمة التنفيذ العملية للتميز في الزيارة القادمة",
            folder_path=str(folder),
            download_url=f"/api/execution/{visit.id}/download",
            missions=missions,
            operating_cycle=[
                "اجتماع يومي 15 دقيقة: تحديث حالة كل شاهد ومؤشر.",
                "تسليم ملفين عمليين يوميًا على الأقل من الحزمة.",
                "مراجعة أسبوعية للدرجات الأربع: الإدارة، التعليم والتعلم، نواتج التعلم، البيئة.",
                "بروفة مقابلة قصيرة كل يومين مع مالك مجال مختلف.",
            ],
            readiness_checkpoints=[
                "كل مؤشر حرج له شاهدان حديثان على الأقل.",
                "كل إجراء في الخطة له مالك وموعد ومخرج محفوظ.",
                "ملف الأدلة مرتب حسب المجال ثم رمز المؤشر.",
                "الفريق يستطيع الإجابة بصيغة: سابق، إجراء، شاهد، أثر.",
            ],
        )

    def _evidence_agent(self, visit: VisitRecord) -> ExecutionMission:
        profile = visit.report_profile
        priorities = profile.improvement_priorities[:8] if profile else []
        rows = [
            "| رمز المؤشر | المجال | الدرجة السابقة | الشاهد المطلوب | حالة الإنجاز | رابط/مكان الحفظ |",
            "|---|---|---:|---|---|---|",
        ]
        for item in priorities:
            rows.append(
                f"| {item.code} | {item.domain} | {item.score or ''} | {item.required_response} | جديد |  |"
            )
        content = _doc(
            "ملف الأدلة التنفيذي",
            [
                "الغرض: تحويل مؤشرات التقرير السابق إلى ملف أدلة قابل للمراجعة قبل الزيارة.",
                "طريقة الاستخدام: لا تغلق أي خانة إلا بعد رفع شاهد واضح وحديث.",
                "\n".join(rows),
            ],
        )
        artifact = ExecutionArtifact(
            title="ملف الأدلة التنفيذي حسب مؤشرات التقرير",
            artifact_type="evidence_file",
            owner_role="رائد الجودة",
            purpose="تنظيم الشواهد حسب رمز المؤشر والدرجة السابقة.",
            content=content,
        )
        return ExecutionMission(
            agent="Evidence Builder Agent",
            mission="بناء ملف أدلة عملي لكل مؤشرات التحسين ذات الأولوية.",
            produced_artifacts=[artifact],
            next_human_action="تعبئة مكان حفظ الشاهد وإرفاق صورة أو رابط لكل مؤشر.",
        )

    def _performance_followup_agent(self, visit: VisitRecord) -> ExecutionMission:
        reference = performance_followup_reference()
        rows = [
            "| رقم | المجال | المؤشر | الشاهد المطلوب | المسؤول | حالة الأسبوع السابق | مكان الحفظ |",
            "|---:|---|---|---|---|---|---|",
        ]
        for item in reference["indicators"]:
            rows.append(
                f"| {item['number']} | {item['domain']} | {item['question']} | {item['required_evidence']} | {item['owner_role']} | جديد |  |"
            )
        content = _doc(
            "سجل متابعة الأداء والالتزام الأسبوعي",
            [
                "الغرض: تجهيز المدرسة لأي استمارة متابعة أداء والتزام ترسلها إدارة التعليم أو وزارة التعليم.",
                "قاعدة مهمة: الشاهد المطلوب يكون للأسبوع السابق، ويراجع خلال يومي عمل كحد أقصى عند طلبه.",
                "تعليمات التشغيل:",
                "\n".join(f"- {rule}" for rule in reference["submission_rules"]),
                "\n".join(rows),
            ],
        )
        briefing = _doc(
            "بروتوكول جاهزية عينة متابعة الأداء",
            [
                "1. كل يوم خميس تحفظ نسخة أسبوعية من: الخطة الأسبوعية، الغياب، السلوك، الزيارات، النشاط.",
                "2. كل شاهد يسمى بهذا النمط: الرقم الوزاري - الأسبوع - المؤشر - التاريخ.",
                "3. يراجع مدير المدرسة ورائد الجودة اكتمال الشواهد قبل نهاية الأسبوع.",
                "4. عند وصول الاستمارة لا يبدأ الفريق من الصفر؛ يستخدم سجل الأسبوع السابق ويرفع الشواهد مباشرة.",
                "5. أي مؤشر بلا شاهد أسبوعي يعد مخاطرة تشغيلية يجب تصعيدها في اجتماع الأحد.",
            ],
        )
        return ExecutionMission(
            agent="Performance Compliance Agent",
            mission="تحويل عرض متابعة الأداء والالتزام إلى سجل أسبوعي جاهز للرفع.",
            produced_artifacts=[
                ExecutionArtifact(
                    title="سجل متابعة الأداء والالتزام الأسبوعي",
                    artifact_type="tracking_sheet",
                    owner_role="مدير المدرسة",
                    purpose="تجهيز شواهد مؤشرات الأداء والالتزام التسعة أسبوعيًا.",
                    content=content,
                ),
                ExecutionArtifact(
                    title="بروتوكول جاهزية عينة متابعة الأداء",
                    artifact_type="brief",
                    owner_role="رائد الجودة",
                    purpose="تعليمات تشغيل مختصرة عند اختيار المدرسة ضمن عينة المتابعة.",
                    content=briefing,
                ),
            ],
            next_human_action="تحديد مجلد أسبوعي للشواهد وتعبئة حالة كل مؤشر قبل نهاية الأسبوع.",
        )

    def _achievement_agent(self, visit: VisitRecord) -> ExecutionMission:
        content = _doc(
            "خطة رفع التحصيلي والقدرات",
            [
                "المؤشرات المستهدفة: 1-1-1-3 التحصيلي، 2-1-1-3 القدرات.",
                "الأسبوع 1: اختبار تشخيصي قصير وتحليل الطلاب حسب المهارة.",
                "الأسبوع 2: مجموعات علاجية حسب المهارات الأقل أداء.",
                "الأسبوع 3: اختبار قصير بعدي وقياس فرق التحسن.",
                "الأسبوع 4: تقرير أثر مختصر يربط التدخل بنتائج الطلاب.",
                "الشواهد المطلوبة: تحليل نتائج، كشوف مجموعات، نماذج اختبار، رسم تحسن، صور تنفيذ.",
            ],
        )
        tracker = _tracking_table(
            "متابعة نواتج التعلم",
            ["المهارة", "خط الأساس", "إجراء المعالجة", "نتيجة بعدية", "نسبة التحسن", "المعلم المسؤول"],
        )
        return ExecutionMission(
            agent="Achievement Intervention Agent",
            mission="تنفيذ مسار عملي لرفع التحصيلي والقدرات.",
            produced_artifacts=[
                ExecutionArtifact(
                    title="خطة رفع التحصيلي والقدرات",
                    artifact_type="weekly_plan",
                    owner_role="منسق نواتج التعلم",
                    purpose="تحويل ضعف نواتج التعلم إلى تدخل أسبوعي قابل للقياس.",
                    content=content,
                ),
                ExecutionArtifact(
                    title="سجل متابعة نواتج التعلم",
                    artifact_type="tracking_sheet",
                    owner_role="منسق نواتج التعلم",
                    purpose="قياس أثر المعالجة قبل الزيارة.",
                    content=tracker,
                ),
            ],
            next_human_action="إدخال نتائج اختبار تشخيصي حقيقي ثم تحديث السجل أسبوعيًا.",
        )

    def _environment_agent(self, visit: VisitRecord) -> ExecutionMission:
        content = _doc(
            "قائمة فحص البيئة المدرسية والسلامة",
            [
                "المؤشرات المستهدفة: الخدمات المساندة، الأمن والسلامة، الصيانة.",
                "- المرافق والخدمات المساندة مناسبة للطلاب وذوي الإعاقة.",
                "- مخارج الطوارئ واضحة وخالية من العوائق.",
                "- طفايات الحريق ولوحات السلامة محدثة.",
                "- سجل الصيانة يحتوي على بلاغ، إجراء، تاريخ إغلاق، وصورة بعد التنفيذ.",
                "- المختبرات والفصول تحقق متطلبات السلامة.",
                "قاعدة الإغلاق: صورة قبل/بعد + توقيع مسؤول السلامة + تاريخ.",
            ],
        )
        return ExecutionMission(
            agent="Environment Readiness Agent",
            mission="تحويل مؤشرات البيئة إلى قائمة جاهزية يومية.",
            produced_artifacts=[
                ExecutionArtifact(
                    title="قائمة فحص البيئة المدرسية والسلامة",
                    artifact_type="checklist",
                    owner_role="مسؤول السلامة والانضباط",
                    purpose="إغلاق فجوات الصيانة والسلامة قبل الزيارة.",
                    content=content,
                )
            ],
            next_human_action="تصوير الفجوات الحالية وإغلاقها ثم إرفاق صور بعد التنفيذ.",
        )

    def _teaching_agent(self, visit: VisitRecord) -> ExecutionMission:
        content = _doc(
            "نموذج تحسين التدريس والتقويم الصفي",
            [
                "المؤشرات المستهدفة: تنويع استراتيجيات التدريس، التقويم المتنوع، المهارات الرقمية.",
                "لكل معلم مختار: درس واحد، استراتيجية واحدة، أداة تقويم واحدة، منتج رقمي واحد.",
                "الشاهد القوي: خطة درس مختصرة + أداة تقويم + عينة أعمال طلاب + تحليل أثر.",
                _tracking_table(
                    "زيارات صفية قصيرة",
                    ["المعلم", "المادة", "الاستراتيجية", "أداة التقويم", "الشاهد", "الأثر المرصود"],
                ),
            ],
        )
        return ExecutionMission(
            agent="Teaching Practice Agent",
            mission="إنتاج نماذج عمل صفية تثبت تحسين التعليم والتعلم.",
            produced_artifacts=[
                ExecutionArtifact(
                    title="نموذج تحسين التدريس والتقويم الصفي",
                    artifact_type="tracking_sheet",
                    owner_role="منسق التعليم والتعلم",
                    purpose="جمع شواهد صفية عملية مرتبطة بالمؤشرات.",
                    content=content,
                )
            ],
            next_human_action="اختيار 5 معلمين وتنفيذ زيارات قصيرة موثقة خلال أسبوع.",
        )

    def _interview_agent(self, visit: VisitRecord) -> ExecutionMission:
        questions = []
        for item in visit.simulation:
            questions.append(
                f"## سؤال\n{item.question}\n\n### الإجابة المختصرة\n- الواقع السابق:\n- الإجراء المنفذ:\n- الشاهد:\n- الأثر:\n"
            )
        content = _doc(
            "بروفة مقابلة فريق التقويم",
            [
                "قاعدة الإجابة: لا جواب بلا رقم أو شاهد.",
                "كل مالك مجال يتدرب على إجابة لا تتجاوز دقيقة.",
                "\n".join(questions),
            ],
        )
        return ExecutionMission(
            agent="Visit Simulation Agent",
            mission="تجهيز نص بروفة مقابلات لفريق المدرسة.",
            produced_artifacts=[
                ExecutionArtifact(
                    title="بروفة مقابلة فريق التقويم",
                    artifact_type="interview_script",
                    owner_role="مدير المدرسة",
                    purpose="تدريب الفريق على أسئلة الزيارة القادمة.",
                    content=content,
                )
            ],
            next_human_action="تنفيذ بروفة مع الفريق وتعبئة الإجابات المختصرة.",
        )

    def _followup_agent(self, visit: VisitRecord) -> ExecutionMission:
        action_rows = [
            "| الإجراء | المالك | الموعد | الشاهد | الحالة | ملاحظة التصعيد |",
            "|---|---|---|---|---|---|",
        ]
        task_by_action = {task.action_id: task for task in visit.tasks}
        for action in visit.plan:
            task = task_by_action.get(action.id)
            action_rows.append(
                f"| {action.title} | {(task.assignee if task else action.owner_role)} | {(task.due_date if task else action.due_in_days)} | {action.success_metric} | جديد |  |"
            )
        content = _doc(
            "لوحة متابعة التنفيذ اليومية",
            [
                "تستخدم في اجتماع 15 دقيقة اليومي.",
                "أي مهمة تبقى في حالة جديد أكثر من يومين تنتقل إلى المدير.",
                "\n".join(action_rows),
            ],
        )
        return ExecutionMission(
            agent="Execution Follow-up Agent",
            mission="بناء لوحة متابعة يومية لتحويل الخطة إلى إنجاز.",
            produced_artifacts=[
                ExecutionArtifact(
                    title="لوحة متابعة التنفيذ اليومية",
                    artifact_type="tracking_sheet",
                    owner_role="مدير المدرسة",
                    purpose="متابعة تنفيذ الخطة وتصعيد التعثر.",
                    content=content,
                )
            ],
            next_human_action="تحديث الحالة يوميًا: جديد، جار، مغلق بشاهد.",
        )

    def _build_index(self, visit: VisitRecord, missions: list[ExecutionMission]) -> str:
        lines = [
            "# حزمة التنفيذ العملية",
            "",
            f"المدرسة: {visit.school_name}",
            f"رقم الزيارة داخل النظام: {visit.id}",
            "",
            "## الوكلاء والملفات",
        ]
        for mission in missions:
            lines.append(f"### {mission.agent}")
            lines.append(mission.mission)
            for artifact in mission.produced_artifacts:
                lines.append(f"- {artifact.title}: {Path(artifact.file_path or '').name}")
            lines.append(f"الإجراء البشري التالي: {mission.next_human_action}")
            lines.append("")
        return "\n".join(lines)


def _tracking_table(title: str, columns: list[str]) -> str:
    header = " | ".join(columns)
    separator = " | ".join(["---"] * len(columns))
    empty = " | ".join([""] * len(columns))
    return f"## {title}\n\n| {header} |\n| {separator} |\n| {empty} |\n| {empty} |\n| {empty} |\n"


def _doc(title: str, blocks: list[str]) -> str:
    return "\n\n".join([f"# {title}", *blocks]).strip() + "\n"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^\w\u0600-\u06FF]+", "_", value, flags=re.UNICODE).strip("_")
    return cleaned[:80] or "artifact"
