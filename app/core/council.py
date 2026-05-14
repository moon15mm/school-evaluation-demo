from __future__ import annotations

from app.core.models import (
    AgentCouncilSession,
    CouncilDecision,
    CouncilTurn,
    DOMAIN_LABELS,
    DomainScore,
    ExcellenceProtocol,
    ImprovementAction,
    OperationalForm,
    PredictionResult,
    ProtocolStep,
    SchoolReportProfile,
    SimulationQuestion,
    TeamTask,
    Weakness,
)


class AgentCouncil:
    agents = [
        "Analyzer Agent",
        "Progress Agent",
        "Planner Agent",
        "Task Agent",
        "Simulator Agent",
        "Prediction Agent",
        "Report Agent",
    ]

    def conduct_session(
        self,
        domains: list[DomainScore],
        weaknesses: list[Weakness],
        plan: list[ImprovementAction],
        tasks: list[TeamTask],
        simulation: list[SimulationQuestion],
        prediction: PredictionResult,
        report_profile: SchoolReportProfile | None = None,
    ) -> tuple[AgentCouncilSession, list[OperationalForm], ExcellenceProtocol]:
        weakest = sorted(domains, key=lambda item: item.current_score)[:3]
        fastest = prediction.fastest_actions
        turns = self._build_dialogue_turns(weakest, weaknesses, plan, simulation, prediction, report_profile)
        decisions = self._build_decisions(fastest, tasks)
        forms = self._build_forms(weaknesses, report_profile)
        protocol = self._build_protocol(prediction, fastest, report_profile)
        session = AgentCouncilSession(
            session_title="جلسة مجلس وكلاء الذكاء لتحقيق التميز في الزيارة القادمة",
            objective="تحويل التحليل إلى بروتوكول تنفيذ يومي قابل للقياس قبل زيارة التقويم الثانية.",
            turns=turns,
            disagreements=[
                "وكيل التخطيط يفضل إجراءات كثيرة، بينما وكيل التنبؤ يوصي بتقليل العدد والتركيز على أعلى أثر.",
                "وكيل المحاكاة يطلب شواهد مقابلة وملاحظة صفية، بينما وكيل المهام يطلب نماذج قصيرة لا تثقل الفريق.",
                "وكيل التقرير يرى أن أي إجراء بلا شاهد قابل للطباعة لا يحسب كتحسن حقيقي في يوم الزيارة.",
            ],
            decisions=decisions,
            final_consensus=(
                "يتفق المجلس على أن طريق التميز ليس زيادة الأعمال، بل إغلاق فجوات قليلة حرجة "
                "بشواهد حديثة، مالك واضح، ومراجعة يومية قصيرة حتى يوم الزيارة."
            ),
        )
        return session, forms, protocol

    def _build_dialogue_turns(
        self,
        weakest: list[DomainScore],
        weaknesses: list[Weakness],
        plan: list[ImprovementAction],
        simulation: list[SimulationQuestion],
        prediction: PredictionResult,
        report_profile: SchoolReportProfile | None,
    ) -> list[CouncilTurn]:
        weakest_labels = "، ".join(item.label for item in weakest)
        top_action = plan[0].title if plan else "إجراء تحسين مركز"
        top_question = simulation[0].question if simulation else "ما الدليل على التحسن؟"
        report_context = ""
        if report_profile:
            priorities = "، ".join(f"{item.code} ({item.score}%)" for item in report_profile.improvement_priorities[:3])
            report_context = f" التقرير السابق حدد درجة عامة {report_profile.overall_score}% في مستوى {report_profile.overall_level}، وأول مؤشرات الضغط: {priorities}."
        return [
            CouncilTurn(
                round=1,
                agent="Analyzer Agent",
                position="المخاطر الأساسية تقع في المجالات الأقل درجة والأضعف توثيقًا.",
                evidence=f"أضعف المجالات الحالية: {weakest_labels}.{report_context}",
                recommendation="ابدأوا من الشواهد الناقصة لا من كتابة خطة طويلة.",
            ),
            CouncilTurn(
                round=1,
                agent="Progress Agent",
                position="التحسن المقبول يجب أن يظهر كفرق واضح بين الزيارة السابقة والوضع الحالي.",
                evidence="الفجوة تحسب من الدرجة الحالية مقارنة بالسابقة لكل مجال.",
                recommendation="اعتمدوا جدول مقارنة قبل/بعد لكل مؤشر حرج.",
            ),
            CouncilTurn(
                round=2,
                agent="Planner Agent",
                position="الخطة يجب أن تتحول إلى حزمة إنقاذ قصيرة ومقاسة.",
                evidence=f"أعلى إجراء مقترح: {top_action}.",
                recommendation="اجعلوا لكل إجراء مخرجًا واحدًا، موعدًا قريبًا، وشاهدًا نهائيًا.",
            ),
            CouncilTurn(
                round=2,
                agent="Task Agent",
                position="الخطر التنفيذي هو ضياع الملكية بين أعضاء الفريق.",
                evidence="كل مهمة تحتاج مالكًا واحدًا وليس لجنة عامة.",
                recommendation="اعقدوا اجتماع متابعة يومي من 15 دقيقة لتحديث حالة المهام.",
            ),
            CouncilTurn(
                round=3,
                agent="Simulator Agent",
                position="فريق التقويم سيختبر صدق الشواهد بالأسئلة والمقابلات.",
                evidence=f"سؤال محاكاة مرجح: {top_question}",
                recommendation="درّبوا كل مالك مجال على جواب قصير مدعوم بشاهدين.",
            ),
            CouncilTurn(
                round=3,
                agent="Prediction Agent",
                position="أسرع رفع للدرجة يأتي من تنفيذ الإجراءات الأعلى أثرًا لا من توزيع الجهد بالتساوي.",
                evidence=f"التوقع الحالي {prediction.expected_score}/100 مع ثقة {prediction.confidence:.0%}.",
                recommendation="ركزوا أول 10 أيام على أسرع 3 إجراءات فقط، ثم وسعوا التنفيذ.",
            ),
            CouncilTurn(
                round=4,
                agent="Report Agent",
                position="لا يكتمل أي تحسين حتى يدخل في ملف أدلة رسمي قابل للطباعة.",
                evidence="التقرير النهائي يحتاج شواهد منظمة حسب المجال والمؤشر والمالك.",
                recommendation="استخدموا نماذج موحدة للأدلة والمتابعة والمحاكاة قبل إصدار التقرير.",
            ),
        ]

    def _build_decisions(self, fastest: list[ImprovementAction], tasks: list[TeamTask]) -> list[CouncilDecision]:
        task_by_action = {task.action_id: task for task in tasks}
        decisions = []
        for action in fastest:
            task = task_by_action.get(action.id)
            decisions.append(
                CouncilDecision(
                    title=f"اعتماد إجراء أولوية: {action.title}",
                    rationale=f"الأثر المتوقع {action.expected_gain} درجة خلال {action.due_in_days} يوم.",
                    owner_role=task.role if task else action.owner_role,
                    deadline=task.due_date if task else f"خلال {action.due_in_days} يوم",
                    success_signal=action.success_metric,
                )
            )
        decisions.append(
            CouncilDecision(
                title="إغلاق ملف الأدلة قبل الزيارة",
                rationale="التميز في الزيارة يعتمد على شواهد منظمة وحديثة وسهلة التحقق.",
                owner_role="رائد الجودة",
                deadline="قبل الزيارة بـ 48 ساعة",
                success_signal="ملف PDF نهائي وفهرس أدلة حسب المجالات.",
            )
        )
        return decisions

    def _build_forms(self, weaknesses: list[Weakness], report_profile: SchoolReportProfile | None) -> list[OperationalForm]:
        critical_domains = [DOMAIN_LABELS[item.domain] for item in weaknesses[:3]]
        if report_profile:
            critical_domains = [item.domain for item in report_profile.improvement_priorities[:5]]
        domain_hint = "، ".join(critical_domains) or "جميع المجالات"
        return [
            OperationalForm(
                name="نموذج سجل فجوة وتحسين",
                purpose="تحويل كل نقطة ضعف إلى إجراء قابل للإغلاق.",
                owner_role="رائد الجودة",
                fields=["المجال", "رمز المؤشر", "درجة الزيارة السابقة", "الفجوة", "سبب الفجوة", "الإجراء", "الشاهد", "نسبة الإغلاق"],
                review_frequency="يوميًا حتى يوم الزيارة",
                completion_rule="لا يغلق النموذج إلا بوجود شاهد وتوقيع مالك المجال.",
            ),
            OperationalForm(
                name="نموذج ملف الشواهد الذكي",
                purpose=f"تنظيم شواهد المجالات الحرجة: {domain_hint}.",
                owner_role="منسق التقويم",
                fields=["اسم الشاهد", "المجال", "المؤشر", "تاريخ الشاهد", "مصدر الشاهد", "رابط/مكان الحفظ"],
                review_frequency="كل يومين",
                completion_rule="كل مؤشر حرج يحتاج شاهدين حديثين على الأقل.",
            ),
            OperationalForm(
                name="نموذج بروفة مقابلة التقويم",
                purpose="تدريب الفريق على إجابات قصيرة مدعومة بالأدلة.",
                owner_role="مدير المدرسة",
                fields=["السؤال المتوقع", "المجيب", "الإجابة المختصرة", "الشاهد الأول", "الشاهد الثاني", "ملاحظات التحسين"],
                review_frequency="مرتين أسبوعيًا",
                completion_rule="يعاد التدريب إذا كانت الإجابة بلا رقم أو شاهد.",
            ),
            OperationalForm(
                name="نموذج متابعة أثر الإجراء",
                purpose="إثبات أن التحسين أحدث أثرًا وليس نشاطًا شكليًا.",
                owner_role="مالك المجال",
                fields=["الإجراء", "خط الأساس", "نتيجة بعد التنفيذ", "نسبة التحسن", "تحليل مختصر", "قرار الاستمرار"],
                review_frequency="أسبوعيًا",
                completion_rule="لا يعتمد الإجراء حتى يظهر فرق رقمي أو شاهد نوعي موثق.",
            ),
        ]

    def _build_protocol(
        self,
        prediction: PredictionResult,
        fastest: list[ImprovementAction],
        report_profile: SchoolReportProfile | None,
    ) -> ExcellenceProtocol:
        target = min(100, max(prediction.expected_score + 8, prediction.scenarios[-1].score if prediction.scenarios else 85))
        first_actions = [action.title for action in fastest] or ["إغلاق الفجوات الحرجة"]
        if report_profile:
            target = max(target, 90.0)
            first_actions = [
                f"{item.code}: {item.title} - {item.required_response}" for item in report_profile.improvement_priorities[:3]
            ]
            stabilization_actions = [
                f"{item.code}: {item.title}" for item in report_profile.improvement_priorities[3:7]
            ]
        else:
            stabilization_actions = [
                "تصنيف الأدلة حسب المجال والمؤشر.",
                "إجراء بروفة مقابلات لفريق المدرسة.",
                "مراجعة التناسق بين الخطة والشواهد والأرقام.",
            ]
        return ExcellenceProtocol(
            title="بروتوكول التميز للزيارة التقويمية القادمة",
            target_score=round(target, 1),
            operating_principles=[
                "كل تحسين يجب أن يملك شاهدًا حديثًا ومؤشر أثر.",
                "الأولوية للإجراءات السريعة عالية الأثر قبل الأعمال الواسعة.",
                "كل مجال له مالك واحد مسؤول عن الجواب والشواهد.",
                "الاستعداد للزيارة يتم بالبروفة والمراجعة وليس بتجميع ملفات متأخر.",
            ],
            steps=[
                ProtocolStep(
                    phase="مرحلة الإنقاذ السريع",
                    day_range="اليوم 1-10",
                    actions=first_actions,
                    required_evidence=["سجل فجوة وتحسين", "شاهدان حديثان لكل إجراء", "قياس خط أساس سريع"],
                    gate="لا تنتقل المدرسة للمرحلة التالية حتى تغلق أسرع 3 إجراءات بنسبة 80%.",
                ),
                ProtocolStep(
                    phase="مرحلة تثبيت الشواهد",
                    day_range="اليوم 11-20",
                    actions=stabilization_actions,
                    required_evidence=["فهرس أدلة", "محضر بروفة", "لوحة مؤشرات محدثة"],
                    gate="أي مؤشر بلا شاهد حديث يعود للمرحلة الأولى.",
                ),
                ProtocolStep(
                    phase="مرحلة محاكاة الزيارة",
                    day_range="آخر 7 أيام",
                    actions=[
                        "تنفيذ محاكاة كاملة لأسئلة فريق التقويم.",
                        "اختبار قدرة كل مالك مجال على عرض الشاهد خلال دقيقة.",
                        "إصدار التقرير النهائي القابل للطباعة.",
                    ],
                    required_evidence=["نتائج المحاكاة", "قائمة فجوات مغلقة", "تقرير PDF نهائي"],
                    gate="جاهزية الزيارة لا تعتمد إلا إذا تجاوزت المحاكاة 85%.",
                ),
            ],
            daily_ritual=[
                "اجتماع 15 دقيقة: ماذا أُغلق؟ ماذا تعطل؟ ما الشاهد؟",
                "تحديث لوحة المهام ونسبة إغلاق الشواهد.",
                "تدريب شخص واحد يوميًا على سؤال تقويم متوقع.",
            ],
            escalation_rules=[
                "أي مهمة تتأخر يومين تنتقل مباشرة لمدير المدرسة.",
                "أي شاهد غير قابل للتحقق يستبدل خلال 24 ساعة.",
                "أي مجال أقل من 60 يعامل كمسار إنقاذ حتى يرتفع مؤشره.",
            ],
            visit_day_protocol=[
                "تجهيز ملف أدلة مختصر حسب المجالات لا حسب الأشخاص.",
                "تحديد متحدث أساسي وبديل لكل مجال.",
                "الإجابة على كل سؤال بصيغة: واقع سابق، إجراء، شاهد، أثر.",
                "تسجيل ملاحظات فريق التقويم فورًا وتحويلها إلى إجراءات بعد الزيارة.",
            ],
        )
