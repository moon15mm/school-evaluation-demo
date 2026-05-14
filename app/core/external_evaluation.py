from __future__ import annotations

from app.core.models import (
    DOMAIN_LABELS,
    DomainScore,
    ClassroomObservationScenario,
    DocumentAuditItem,
    EvaluatorProbe,
    EvaluationScheduleItem,
    ExternalEvaluationReadiness,
    ExternalReadinessDimension,
    ExternalVisitPhase,
    InterviewDrill,
    ImprovementAction,
    SchoolReportProfile,
    TriangulationCheck,
    Weakness,
)


class ExternalEvaluationAdvisor:
    """Models how an external evaluation team actually tests school readiness."""

    def build(
        self,
        domains: list[DomainScore],
        weaknesses: list[Weakness],
        plan: list[ImprovementAction],
        current_status: str,
        report_profile: SchoolReportProfile | None,
    ) -> ExternalEvaluationReadiness:
        status = current_status.lower()
        domain_map = {domain.key: domain.current_score for domain in domains}
        dimensions = [
            self._dimension(
                "غرفة البيانات المدرسية",
                self._score(domain_map.get("leadership", 70), status, ["نافس", "غياب", "تحصيلي", "استبان", "مؤشرات"]),
                "هل تعرف المدرسة أرقامها الدقيقة وتستخدمها لاتخاذ القرار؟",
                ["لوحة حضور وغياب", "تحليل نواتج التعلم", "قائمة الطلاب المتعثرين", "أثر البرامج العلاجية"],
                "القائد يتحدث بعموميات ولا يملك أرقامًا حديثة.",
                "القائد يشرح الرقم، سببه، الإجراء، والأثر خلال أقل من دقيقتين.",
                ["تحديث لوحة البيانات أسبوعيًا", "ربط كل برنامج علاجي بنسبة تحسن", "تجهيز ملخص أرقام من صفحة واحدة"],
            ),
            self._dimension(
                "جودة التعلم داخل الفصل",
                self._score(domain_map.get("teaching", 70), status, ["تعلم نشط", "تقويم", "تفكير", "مشاركة", "ناتج تعلم"]),
                "هل الطالب يتعلم بعمق أم أن الحصة شرح مباشر فقط؟",
                ["نماذج زيارات صفية", "أدوات تقويم أثناء الحصة", "أعمال طلابية", "تغذية راجعة للمعلمين"],
                "المعلم يتحدث معظم الوقت والأسئلة سطحية.",
                "الطالب يشرح، يناقش، يطبق، ويعرف هدف تعلمه.",
                ["تنفيذ جولات تعلم قصيرة يومية", "تدريب المعلمين على أسئلة التفكير العليا", "قياس نسبة مشاركة الطالب"],
            ),
            self._dimension(
                "أثر نواتج التعلم",
                self._score(domain_map.get("learning_outcomes", 65), status, ["قراءة", "رياضيات", "علوم", "متعثر", "تحسن"]),
                "هل تحسنت نتائج الطلاب فعليًا؟",
                ["تحليل قبلي/بعدي", "خطط علاج", "نتائج قصيرة", "فجوات الفصول"],
                "برامج كثيرة بلا دليل أثر رقمي.",
                "لكل فجوة برنامج وقياس قبل/بعد وتحسن ظاهر.",
                ["تحديد 20 طالبًا عالي الخطورة", "اختبار قصير أسبوعي", "إظهار منحنى تحسن لكل مهارة"],
            ),
            self._dimension(
                "مقابلات القيادة والمعلمين والطلاب",
                self._score(domain_map.get("leadership", 70), status, ["رؤية", "رسالة", "حوار", "طلاب", "معلمين"]),
                "هل يفهم الجميع الرؤية والأهداف والأدوار؟",
                ["نص مقابلة القيادة", "أسئلة تدريب الطلاب", "محاور مقابلة المعلمين", "أمثلة أثر"],
                "الإدارة وحدها تفهم التقييم وبقية الفريق يجيب إجابات محفوظة.",
                "كل فئة تقدم إجابة طبيعية مرتبطة بواقعها اليومي.",
                ["جلسات حوار قصيرة للطلاب", "بطاقة حديث موحدة للمعلمين", "محاكاة مقابلات مرتين أسبوعيًا"],
            ),
            self._dimension(
                "مصداقية الشواهد الرقمية",
                self._score(76, status, ["شاهد", "دليل", "صور", "قبل", "بعد", "توثيق"]),
                "هل الشواهد تثبت ممارسة حقيقية مستمرة؟",
                ["ملف رقمي لكل معيار", "صور قبل/بعد", "تواريخ واضحة", "روابط نتائج وإحصاءات"],
                "ملفات شكلية أو شواهد بلا تاريخ أو أثر.",
                "كل شاهد له معيار، تاريخ، مسؤول، وأثر قابل للتحقق.",
                ["استخدام سكرتارية الشواهد لكل ملف", "رفض أي شاهد بلا تاريخ", "إنشاء فهرس شواهد حسب المؤشر"],
            ),
            self._dimension(
                "الاستدامة والترابط النظامي",
                self._score(self._average([domain.current_score for domain in domains]), status, ["أسبوعي", "متابعة", "مجتمع", "استدامة", "أثر"]),
                "هل التميز نظام مستمر أم تجهيز مؤقت؟",
                ["محاضر متابعة أسبوعية", "دورة تحسين قصيرة", "ربط القيادة بالتعلم بالنتائج", "أدلة تنفيذ مستمرة"],
                "نشاط مكثف قبل الزيارة فقط دون انتظام سابق.",
                "توجد دورة متابعة أسبوعية تربط المؤشرات بالصف والطالب.",
                ["اجتماع جودة أسبوعي 25 دقيقة", "تحديث مؤشرات كل خميس", "قرار تصحيحي لكل مؤشر متأخر"],
            ),
        ]
        overall = round(self._average([item.score for item in dimensions]), 1)
        return ExternalEvaluationReadiness(
            overall_readiness=overall,
            guarantee_level=self._level(overall),
            evaluator_mindset=[
                "الفريق لا يبحث عن جمال الملفات، بل عن صدق الممارسة وأثرها.",
                "أقوى سؤال ضمني: ما الذي تغير في تعلم الطالب؟",
                "المؤشر القوي يربط بين رقم، إجراء، شاهد، وأثر.",
                "التميز يظهر عندما يجيب القائد والمعلم والطالب بالمنطق نفسه لا بالنص نفسه.",
            ],
            dimensions=dimensions,
            phases=self._phases(),
            probes=self._probes(report_profile),
            visit_schedule=self._visit_schedule(report_profile),
            classroom_observations=self._classroom_observations(report_profile),
            interview_drills=self._interview_drills(report_profile),
            document_audit=self._document_audit(report_profile),
            triangulation_checks=self._triangulation_checks(report_profile),
            top_failure_risks=self._risks(weaknesses, report_profile),
            guarantee_protocol=self._guarantee_protocol(plan),
            weekly_battle_rhythm=[
                "الأحد: تحديث غرفة البيانات وتحديد الطلاب/الفصول عالية الخطورة.",
                "الاثنين: جولات تعلم صفية مركزة على التقويم ومشاركة الطالب.",
                "الثلاثاء: علاج فجوات نواتج التعلم وقياس قبلي/بعدي مصغر.",
                "الأربعاء: مراجعة الشواهد الرقمية ورفض الشاهد غير المرتبط بأثر.",
                "الخميس: اجتماع قيادة 25 دقيقة: رقم، سبب، إجراء، أثر، قرار الأسبوع القادم.",
            ],
        )

    def _dimension(
        self,
        name: str,
        score: float,
        evaluator_question: str,
        evidence_required: list[str],
        failure_signal: str,
        excellence_signal: str,
        immediate_actions: list[str],
    ) -> ExternalReadinessDimension:
        return ExternalReadinessDimension(
            name=name,
            score=round(max(0, min(100, score)), 1),
            evaluator_question=evaluator_question,
            evidence_required=evidence_required,
            failure_signal=failure_signal,
            excellence_signal=excellence_signal,
            immediate_actions=immediate_actions,
        )

    def _score(self, base: float, status: str, keywords: list[str]) -> float:
        hits = sum(1 for keyword in keywords if keyword in status)
        return min(100, base + hits * 2.5)

    def _average(self, values: list[float]) -> float:
        return sum(values) / len(values) if values else 0

    def _level(self, score: float) -> str:
        if score >= 90:
            return "excellence_ready"
        if score >= 82:
            return "ready"
        if score >= 72:
            return "promising"
        return "high_risk"

    def _phases(self) -> list[ExternalVisitPhase]:
        return [
            ExternalVisitPhase(
                phase="ما قبل الزيارة",
                weight=0.7,
                objective="إثبات أن المدرسة تعرف واقعها وتدير التحسين قبل وصول الفريق.",
                checklist=["تقويم ذاتي صادق", "غرفة بيانات حديثة", "ملف رقمي لكل معيار", "أثر موثق للبرامج"],
                owner="قائد المدرسة ورائد الجودة",
            ),
            ExternalVisitPhase(
                phase="أثناء الزيارة",
                weight=0.25,
                objective="إثبات أن الواقع الميداني يطابق الملفات والبيانات.",
                checklist=["حصص تعلم نشط", "مقابلات طبيعية", "شواهد جاهزة", "طلاب يعرفون أهداف تعلمهم"],
                owner="فريق القيادة والمعلمون والطلاب",
            ),
            ExternalVisitPhase(
                phase="بعد الزيارة",
                weight=0.05,
                objective="إغلاق أي ملاحظة بسرعة وتثبيت التحسين المستمر.",
                checklist=["محضر ملاحظات", "إجراءات تصحيحية", "تحديث الخطة", "توثيق أثر جديد"],
                owner="مجلس الجودة",
            ),
        ]

    def _visit_schedule(self, report_profile: SchoolReportProfile | None) -> list[EvaluationScheduleItem]:
        priority = report_profile.improvement_priorities[0].title if report_profile and report_profile.improvement_priorities else "نواتج التعلم"
        return [
            EvaluationScheduleItem(
                time_window="قبل وصول الفريق بـ 30 دقيقة",
                activity="غرفة قيادة مصغرة",
                evaluator_focus="هل تعرف المدرسة ملفها وأرقامها دون بحث عشوائي؟",
                school_owner="مدير المدرسة ورائد الجودة",
                expected_outputs=["صفحة أرقام حرجة", "قائمة الشواهد الذهبية", "توزيع أدوار الاستقبال"],
            ),
            EvaluationScheduleItem(
                time_window="الساعة الأولى",
                activity="اجتماع افتتاحي وفهم السياق",
                evaluator_focus=f"لماذا اختارت المدرسة {priority} كأولوية؟ وما أثرها؟",
                school_owner="مدير المدرسة",
                expected_outputs=["عرض 5 دقائق", "ثلاثة أرقام قبل/بعد", "أهم إجراء تصحيحي"],
            ),
            EvaluationScheduleItem(
                time_window="منتصف الزيارة",
                activity="جولات صفية مفاجئة",
                evaluator_focus="مطابقة الكلام الرسمي مع تعلم الطالب داخل الفصل.",
                school_owner="وكيل الشؤون التعليمية ومنسق التعلم",
                expected_outputs=["حصص فيها هدف واضح", "تقويم أثناء التعلم", "مشاركة طلابية عالية"],
            ),
            EvaluationScheduleItem(
                time_window="بعد الجولات",
                activity="مقابلات الطلاب والمعلمين وأولياء الأمور",
                evaluator_focus="هل الثقافة مفهومة وممارسة أم محفوظة؟",
                school_owner="المرشد ورائد الجودة",
                expected_outputs=["إجابات طبيعية", "أمثلة أثر حقيقية", "شواهد قريبة بيد المسؤول"],
            ),
            EvaluationScheduleItem(
                time_window="الختام",
                activity="تتبع الأدلة والتحقق الثلاثي",
                evaluator_focus="هل كل ادعاء له ملف وميدان ونتيجة؟",
                school_owner="سكرتارية الشواهد",
                expected_outputs=["ملف الأثر", "ملف الشواهد الموحد", "قائمة ملاحظات وإغلاق سريع"],
            ),
        ]

    def _classroom_observations(self, report_profile: SchoolReportProfile | None) -> list[ClassroomObservationScenario]:
        return [
            ClassroomObservationScenario(
                subject_or_context="حصة في مادة ذات أثر على نواتج التعلم",
                evaluator_look_for=["هدف تعلم معلن بلغة الطالب", "نشاط يقيس مهارة محددة", "أسئلة تفكير عليا", "تغذية راجعة فورية"],
                likely_questions=["ما هدف الدرس اليوم؟", "كيف تعرف أنك أتقنت المهارة؟", "ماذا يفعل المعلم إذا أخطأت؟"],
                excellence_response="الطالب يشرح الهدف ومعيار النجاح، والمعلم يعرض نتيجة تقويم لحظي ويعدل التدريس بناء عليها.",
                red_flags=["المعلم يشرح فقط", "لا يوجد قياس أثناء الحصة", "الطالب لا يعرف هدف التعلم", "أوراق عمل بلا تحليل"],
                evidence_to_prepare=["بطاقة هدف الدرس", "أداة تقويم قصيرة", "نماذج أعمال طلاب", "تحليل نتيجة الخروج"],
            ),
            ClassroomObservationScenario(
                subject_or_context="حصة مهارات رقمية أو توظيف تقنية",
                evaluator_look_for=["الطالب يستخدم التقنية لإنتاج تعلم", "مصادر موثوقة", "مهمة رقمية قابلة للتقييم"],
                likely_questions=["ما المنتج الذي أنجزته؟", "كيف تحققت من صحة المصدر؟", "كيف قيّم المعلم عملك؟"],
                excellence_response="الطلاب يعرضون منتجًا رقميًا مرتبطًا بالمنهج مع Rubric مختصر ونتائج أداء.",
                red_flags=["عرض شاشة فقط", "التقنية للزينة", "لا توجد منتجات طلابية", "غياب معايير تقييم"],
                evidence_to_prepare=["منتجات رقمية", "سلم تقدير", "صور تنفيذ", "تحليل جودة المنتجات"],
            ),
            ClassroomObservationScenario(
                subject_or_context="حصة علاجية لطالب أو مجموعة متعثرة",
                evaluator_look_for=["تشخيص فجوة", "تدخل قصير", "قياس أثر", "طالب يعرف تقدمه"],
                likely_questions=["لماذا أنت في هذه المجموعة؟", "ما المهارة التي تحسنت لديك؟", "أين نتيجة قبل وبعد؟"],
                excellence_response="المعلم يربط الطالب بفجوة محددة ويعرض تحسنًا رقميًا في نفس المهارة.",
                red_flags=["مجموعة علاجية بلا تشخيص", "تكرار شرح", "لا يوجد اختبار بعدي", "الطالب لا يعرف سبب التدخل"],
                evidence_to_prepare=["قائمة الطلاب المستهدفين", "اختبار قبلي", "خطة علاج", "اختبار بعدي"],
            ),
        ]

    def _interview_drills(self, report_profile: SchoolReportProfile | None) -> list[InterviewDrill]:
        weakest = report_profile.improvement_priorities[0] if report_profile and report_profile.improvement_priorities else None
        priority_title = weakest.title if weakest else "أولوية نواتج التعلم"
        return [
            InterviewDrill(
                audience="قائد المدرسة",
                opening_question=f"ما قصة التحسن في {priority_title}؟",
                follow_up_questions=["ما الرقم قبل التدخل؟", "من الفئة المستهدفة؟", "ما الإجراء؟", "ما الأثر بعد التدخل؟", "كيف ضمنتم الاستدامة؟"],
                answer_formula=["رقم", "سبب", "إجراء", "أثر", "قرار قادم"],
                evidence_to_hold=["لوحة بيانات", "ملف أثر", "خطة تحسين", "محضر متابعة أسبوعي"],
                avoid=["التحدث بعموميات", "ذكر برامج بلا أرقام", "إحالة كل سؤال لرائد الجودة"],
            ),
            InterviewDrill(
                audience="المعلم",
                opening_question="كيف غيّرت تدريسك بناءً على نتائج الطلاب؟",
                follow_up_questions=["أين التحليل؟", "ما المهارة الأضعف؟", "كيف قست التحسن؟", "كيف تلقى الطالب تغذية راجعة؟"],
                answer_formula=["مهارة محددة", "دليل ضعف", "استراتيجية", "قياس بعدي", "مثال طالب"],
                evidence_to_hold=["تحليل مهارة", "سجل تقويم", "عينات طلاب", "تغذية راجعة"],
                avoid=["القول إن كل الطلاب ممتازون", "وصف طريقة تدريس فقط", "غياب مثال طالب"],
            ),
            InterviewDrill(
                audience="الطالب",
                opening_question="ما الشيء الذي تحسنت فيه هذا الشهر؟",
                follow_up_questions=["كيف عرفت أنك تحسنت؟", "من ساعدك؟", "ما الدليل في دفترك أو ملفك؟"],
                answer_formula=["هدف بسيط", "تدريب", "نتيجة", "شعور/ثقة"],
                evidence_to_hold=["دفتر الطالب", "ورقة خروج", "نتيجة قبل/بعد"],
                avoid=["إجابة محفوظة عن رؤية المدرسة", "عدم معرفة الهدف", "ذكر نشاط بلا تعلم"],
            ),
            InterviewDrill(
                audience="ولي الأمر",
                opening_question="ما الأثر الذي لاحظته على ابنك من برامج المدرسة؟",
                follow_up_questions=["هل وصلك تقرير واضح؟", "ما نوع التواصل؟", "هل تغير الحضور أو التحصيل؟"],
                answer_formula=["ملاحظة واقعية", "تواصل المدرسة", "تغير قابل للملاحظة"],
                evidence_to_hold=["رسالة تواصل", "استبانة رضا", "تقرير تقدم طالب"],
                avoid=["مدح عام بلا مثال", "عدم معرفة أي برنامج", "الحديث عن مبنى المدرسة فقط"],
            ),
        ]

    def _document_audit(self, report_profile: SchoolReportProfile | None) -> list[DocumentAuditItem]:
        return [
            DocumentAuditItem(
                file_name="ملف الأثر الذهبي",
                evaluator_test="هل يثبت الملف تغيرًا حقيقيًا في الطالب أو البيئة؟",
                required_artifacts=["قبل/بعد", "نسبة تحسن", "مرفق أصلي", "سردية أثر", "نتيجة اختبار أو رصد"],
                pass_condition="كل قصة أثر تجيب: ماذا كان الوضع؟ ماذا فعلنا؟ ما الذي تغير؟ ما الدليل؟",
                failure_pattern="صور كثيرة أو برامج كثيرة بلا قياس أثر.",
            ),
            DocumentAuditItem(
                file_name="ملف نواتج التعلم",
                evaluator_test="هل نتائج الطلاب تقود قرارات علاجية؟",
                required_artifacts=["تحليل نتائج", "طلاب مستهدفون", "خطة علاج", "اختبار بعدي", "منحنى تحسن"],
                pass_condition="وجود عينة واضحة وقياس متكرر لنفس المهارة.",
                failure_pattern="تحليل عام للفصل دون تدخل أو قياس بعدي.",
            ),
            DocumentAuditItem(
                file_name="ملف الزيارات الصفية",
                evaluator_test="هل الزيارة الصفية تحسن التعلم أم تقيم المعلم فقط؟",
                required_artifacts=["أداة ملاحظة", "تغذية راجعة", "خطة تحسين", "زيارة متابعة", "أثر على تعلم الطلاب"],
                pass_condition="كل زيارة لها قرار متابعة وأثر ظاهر في الحصة التالية.",
                failure_pattern="نماذج موقعة دون تحليل تعلم أو إجراء.",
            ),
            DocumentAuditItem(
                file_name="ملف البيئة والسلامة",
                evaluator_test="هل أُغلقت المخاطر فعليًا؟",
                required_artifacts=["قائمة فحص", "صور قبل", "إجراء صيانة", "صور بعد", "نسبة إغلاق"],
                pass_condition="إغلاق 90% فأكثر من الفجوات مع تاريخ ومسؤول.",
                failure_pattern="صور بعد فقط أو قائمة فحص بلا إغلاق.",
            ),
        ]

    def _triangulation_checks(self, report_profile: SchoolReportProfile | None) -> list[TriangulationCheck]:
        return [
            TriangulationCheck(
                claim="تحسنت نواتج التعلم",
                document_proof="تحليل قبلي/بعدي وخطة علاجية.",
                field_proof="طالب يشرح مهارته ودفتره يوضح تحسنًا.",
                student_or_result_proof="ارتفاع نسبة الإتقان في اختبار بعدي لنفس المهارة.",
                verdict_rule="إذا غاب أحد الأضلاع الثلاثة يتحول الادعاء إلى نشاط غير مثبت.",
            ),
            TriangulationCheck(
                claim="التعلم النشط مطبق",
                document_proof="نماذج زيارات صفية وتغذية راجعة.",
                field_proof="داخل الفصل الطالب يتحدث ويطبق أكثر من تلقيه.",
                student_or_result_proof="أعمال طلابية أو ورقة خروج تثبت تحقق الهدف.",
                verdict_rule="الحصة الجميلة بلا قياس تعلم لا تكفي.",
            ),
            TriangulationCheck(
                claim="البيئة آمنة وجاذبة",
                document_proof="قائمة فحص وإغلاق مخاطر.",
                field_proof="المرافق مطابقة عند الجولة.",
                student_or_result_proof="انضباط، حضور، ورضا طلابي أو انخفاض بلاغات.",
                verdict_rule="النظافة المؤقتة لا تعوض غياب سجل إغلاق المخاطر.",
            ),
            TriangulationCheck(
                claim="الشراكة المجتمعية مؤثرة",
                document_proof="اتفاقية وخطة تنفيذ.",
                field_proof="تنفيذ مرتبط باحتياج مدرسي واضح.",
                student_or_result_proof="تحسن حضور أو تحصيل أو رضا أو منتج طلابي.",
                verdict_rule="الشراكة التي لا تغير مؤشرًا لا تبهر فريق التقويم.",
            ),
        ]

    def _probes(self, report_profile: SchoolReportProfile | None) -> list[EvaluatorProbe]:
        priority = report_profile.improvement_priorities[0].title if report_profile and report_profile.improvement_priorities else "أولوية التحسين الأعلى"
        return [
            EvaluatorProbe(
                target="قائد المدرسة",
                question=f"ما أضعف مؤشر لديكم الآن؟ وماذا فعلتم لتحسين {priority}؟",
                what_good_answer_contains=["رقم دقيق", "سبب واضح", "إجراء محدد", "أثر قابل للقياس"],
                evidence_to_show=["لوحة البيانات", "خطة التحسين", "نتيجة قبل/بعد"],
                risk_if_weak="تظهر القيادة كأنها لا تستخدم البيانات في القرار.",
            ),
            EvaluatorProbe(
                target="المعلم",
                question="كيف تعرف داخل الحصة أن الطالب تعلم فعلًا؟",
                what_good_answer_contains=["ناتج تعلم واضح", "تقويم أثناء الحصة", "تدخل علاجي فوري", "مشاركة طلابية"],
                evidence_to_show=["أداة تقويم", "أعمال طلاب", "سجل تغذية راجعة"],
                risk_if_weak="تُحسب الحصة شرحًا لا تعلمًا.",
            ),
            EvaluatorProbe(
                target="الطالب",
                question="ماذا تتعلم اليوم؟ وكيف تعرف أنك أتقنته؟",
                what_good_answer_contains=["هدف بلغة الطالب", "نشاط تطبيقي", "معيار نجاح", "تغذية راجعة"],
                evidence_to_show=["دفتر الطالب", "مهمة أداء", "بطاقة هدف الدرس"],
                risk_if_weak="تظهر الثقافة الصفية ضعيفة حتى لو كانت الملفات جيدة.",
            ),
        ]

    def _risks(self, weaknesses: list[Weakness], report_profile: SchoolReportProfile | None) -> list[str]:
        risks = [
            "تحسين شكلي للملفات دون أثر ظاهر على تعلم الطالب.",
            "ضعف جاهزية المعلمين والطلاب للمقابلات الطبيعية.",
            "شواهد بلا تاريخ أو بلا ارتباط مباشر بالمؤشر.",
        ]
        for weakness in weaknesses[:3]:
            risks.append(f"{DOMAIN_LABELS[weakness.domain]}: {weakness.title}")
        if report_profile and report_profile.overall_score < 75:
            risks.append("الدرجة السابقة في مستوى يحتاج قفزة أثر واضحة لا مجرد تنظيم ملفات.")
        return risks[:6]

    def _guarantee_protocol(self, plan: list[ImprovementAction]) -> list[str]:
        urgent = [action.title for action in plan[:3]]
        return [
            "لا يعتمد أي شاهد إلا إذا أجاب: ما المؤشر؟ ما التاريخ؟ ما الأثر؟",
            "لا تمر أي حصة نموذجية إلا وفيها: هدف معلن، مشاركة طالب، تقويم أثناء التعلم، تغذية راجعة.",
            "كل برنامج علاجي يجب أن يملك قياسًا قبليًا وبعديًا ولو كان مصغرًا.",
            "كل عضو في المدرسة يتدرب على إجابة طبيعية تربط دوره بأثر الطالب.",
            *[f"إجراء ضمان سريع: {title}" for title in urgent],
        ]
