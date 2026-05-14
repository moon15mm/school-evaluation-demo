from __future__ import annotations

from app.core.models import CouncilTurn, EvidenceReview, ImpactRecord, LiveCouncilEvent, TeamTask, VisitRecord


class LiveAgentCouncil:
    def analysis_event(self, visit: VisitRecord) -> LiveCouncilEvent:
        weak = sorted(visit.domains, key=lambda item: item.current_score)[:2]
        weak_text = " و ".join(f"{item.label} ({item.current_score}%)" for item in weak)
        warnings = []
        if visit.prediction.expected_score < 75:
            warnings.append("التوقع ما زال قريبًا من حد الانطلاق؛ يلزم أثر سريع لا مجرد تنظيم ملفات.")
        if visit.weaknesses:
            warnings.append(f"أول فجوة تحتاج إغلاق: {visit.weaknesses[0].title}.")
        return LiveCouncilEvent(
            visit_id=visit.id,
            event_type="analysis",
            title="افتتاح غرفة عمليات الوكلاء",
            summary=f"المجلس قرأ واقع المدرسة. أضعف نقاط الضغط الآن: {weak_text}.",
            agent_positions=[
                self._turn(1, "Analyzer Agent", "المدرسة تحتاج تركيزًا على المجالات الأقل درجة.", weak_text, "ابدأوا من فجوتين فقط لتجنب التشتت."),
                self._turn(1, "Prediction Agent", "رفع الدرجة يعتمد على أثر مقاس.", f"التوقع الحالي {visit.prediction.expected_score}/100.", "حوّلوا أسرع 3 إجراءات إلى قصص أثر."),
            ],
            recommendations=[
                "اجعلوا كل عمل جديد مرتبطًا بمؤشر تقويم واحد.",
                "لا تعتمدوا أي برنامج لا يملك قياسًا قبليًا وبعديًا.",
                "ابدأوا بملف أثر في نواتج التعلم قبل بقية الملفات.",
            ],
            warnings=warnings,
            next_actions=["استشارة وكيل ملف الأثر", "رفع شاهدين للمؤشر الأضعف", "تحديد مالك لكل فجوة حرجة"],
            severity="watch" if warnings else "info",
        )

    def evidence_event(self, visit: VisitRecord, review: EvidenceReview) -> LiveCouncilEvent:
        warnings = []
        if review.suitability != "suitable":
            warnings.extend(review.required_edits or ["الشاهد يحتاج تحسينًا قبل اعتماده."])
        if not review.suggested_indicator_code:
            warnings.append("الشاهد غير مربوط بمؤشر واضح؛ سيضعف عند سؤال فريق التقويم عن الأثر.")
        recommendations = [
            f"اربط الشاهد بسردية أثر في مجال {review.suggested_domain}.",
            "أضف تاريخًا ومصدرًا واضحين إذا لم يكونا ظاهرين داخل الملف.",
        ]
        if review.suitability == "suitable":
            recommendations.append("انقل الشاهد إلى ملف الشواهد الموحد واذكره في تدريب المقابلات.")
        return LiveCouncilEvent(
            visit_id=visit.id,
            event_type="evidence",
            title=f"مراجعة شاهد جديد: {review.original_filename}",
            summary=f"الشاهد صُنّف في {review.suggested_domain} / {review.suggested_indicator_code or 'غير محدد'} بثقة {round(review.confidence * 100)}%.",
            agent_positions=[
                self._turn(1, "Evidence Classifier Agent", "الشاهد وجد مكانه التصنيفي.", review.destination_folder, "راجع ربطه بالمؤشر قبل الزيارة."),
                self._turn(1, "Simulator Agent", "فريق التقويم قد يسأل عن أثر هذا الشاهد.", review.secretariat_opinion, "جهز جوابًا من جملة واحدة: المؤشر، الإجراء، الأثر."),
            ],
            recommendations=recommendations,
            warnings=warnings,
            next_actions=["فتح بطاقة الشاهد", "إضافة الشاهد لقصة أثر إذا كان يثبت قبل/بعد", "تحديث ملف الشواهد الموحد"],
            severity="warning" if warnings else "info",
        )

    def impact_event(self, visit: VisitRecord, record: ImpactRecord) -> LiveCouncilEvent:
        warnings = list(record.validation_notes)
        severity = "info"
        if record.impact_level in {"limited", "clear"}:
            severity = "warning"
        elif record.impact_level == "strong":
            severity = "watch"
        return LiveCouncilEvent(
            visit_id=visit.id,
            event_type="impact",
            title=f"قصة أثر جديدة: {record.title}",
            summary=f"تم تسجيل أثر في {record.domain} بنسبة تحسن {record.improvement_rate:+.1f}% ومستوى {record.impact_level}.",
            agent_positions=[
                self._turn(1, "Impact Agent", "هذه القصة مهمة لأنها تثبت تغيرًا لا نشاطًا.", record.narrative, "ارفع مرفقات قبل/بعد ونتائج اختبار."),
                self._turn(1, "Report Agent", "قصة الأثر يجب أن تظهر في الملف الذهبي.", f"المجال: {record.domain}.", "اجعل عنوانها واضحًا لفريق التقويم."),
            ],
            recommendations=[
                "اربط قصة الأثر بشاهد أو أكثر من مكتبة الشواهد.",
                "درّب مالك المجال على شرح القصة خلال دقيقة.",
                "استخدم القصة في إجابة القائد عند سؤال: ما الذي تغير؟",
            ],
            warnings=warnings,
            next_actions=["إضافة مرفقات ناقصة", "تجهيز الملف الذهبي", "إدراج القصة في محاكاة المقابلات"],
            severity=severity,
        )

    def task_event(self, visit: VisitRecord, task: TeamTask) -> LiveCouncilEvent:
        warnings = []
        if task.status == "done":
            recommendations = ["لا تغلق المهمة فعليًا حتى يرتبط إنجازها بشاهد أو قصة أثر.", "راجع هل المخرج قابل للعرض أمام فريق التقويم."]
            severity = "info"
        elif task.status == "in_progress":
            recommendations = ["حدد موعد تسليم الشاهد النهائي.", "اطلب من المالك تحديث نسبة التقدم خلال 24 ساعة."]
            severity = "watch"
        else:
            recommendations = ["المهمة عادت إلى البداية؛ حدد سبب التعثر ومالكًا واحدًا.", "اربط المهمة بأقرب مؤشر أثر."]
            warnings.append("تراجع حالة المهمة قد يرفع خطر التأخر في التنفيذ.")
            severity = "warning"
        return LiveCouncilEvent(
            visit_id=visit.id,
            event_type="task",
            title=f"تحديث مهمة: {task.assignee}",
            summary=f"تغيرت حالة مهمة {task.role} إلى {task.status}. المخرج المطلوب: {task.deliverable}",
            agent_positions=[
                self._turn(1, "Task Agent", "تغير حالة المهمة يؤثر مباشرة في جاهزية التنفيذ.", task.deliverable, "حوّل الحالة إلى شاهد ملموس."),
                self._turn(1, "Planner Agent", "المهمة بلا أثر لا تكفي لإقناع المقوم.", task.due_date, "اطلب مخرجًا مختصرًا قابلًا للقياس."),
            ],
            recommendations=recommendations,
            warnings=warnings,
            next_actions=["رفع شاهد للمهمة", "ربط المهمة بملف الأثر", "تحديث لوحة المتابعة"],
            severity=severity,
        )

    def _turn(self, round_no: int, agent: str, position: str, evidence: str, recommendation: str) -> CouncilTurn:
        return CouncilTurn(round=round_no, agent=agent, position=position, evidence=evidence, recommendation=recommendation)
