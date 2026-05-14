from __future__ import annotations

from app.core.models import DomainScore, ReportDomainProfile, ReportIndicatorProfile, SchoolReportProfile


def build_school_report_profile(pdf_text: str) -> SchoolReportProfile | None:
    if not any(marker in pdf_text for marker in ["مدرسة المستقبل الثانوية", "تقرير تقويم خارجي افتراضي"]):
        return None

    return SchoolReportProfile(
        report_year="1446هـ - 2025م",
        school_name="مدرسة المستقبل الثانوية",
        evaluation_date="2024/12/11",
        overall_score=73.0,
        overall_level="الانطلاق",
        level_bands=[
            "التميز: 90 فأعلى، ويتطلب استدامة التميز والابتكار.",
            "التقدم: من 75 إلى أقل من 90، ويتطلب استمرار المتابعة للتحسين والتطوير.",
            "الانطلاق: من 50 إلى أقل من 75، ويتطلب تحسينات كبيرة في بعض المجالات.",
            "التهيئة: أقل من 50، ويتطلب تدخلات جوهرية في معظم المجالات.",
        ],
        visit_mechanism=[
            "التقرير صادر ضمن برنامج التقويم والتصنيف والاعتماد المدرسي.",
            "جمع البيانات يتم عبر منصة تميز الرقمية وبمشاركة فرق التقويم المدرسي.",
            "التقويم يستند إلى أربعة مجالات: الإدارة المدرسية، التعليم والتعلم، نواتج التعلم، البيئة المدرسية.",
            "الأدوات تتضمن تحليل البيانات، نموذج الجاهزية، الاستبانات، نتائج الاختبارات، ووصف الأداء التفصيلي للمؤشرات.",
            "التحسين المقبول في الزيارة القادمة يجب أن يظهر في المؤشرات ذات الدرجات المنخفضة مع شواهد أثر قابلة للتحقق.",
        ],
        domains=[
            ReportDomainProfile(
                name="الإدارة المدرسية",
                score=77.25,
                level="التقدم",
                interpretation="المجال فوق حد الانطلاق، لكن يحتاج رفع التخطيط والتطوير المؤسسي والشراكة المجتمعية.",
            ),
            ReportDomainProfile(
                name="التعليم والتعلم",
                score=74.75,
                level="الانطلاق",
                interpretation="قريب من التقدم، وأسرع رفع يكون عبر التدريس، التقويم، المهارات الرقمية، ودافعية التعلم.",
            ),
            ReportDomainProfile(
                name="نواتج التعلم",
                score=67.25,
                level="الانطلاق",
                interpretation="أكبر مجال ضاغط على الدرجة العامة بسبب التحصيل والقدرات.",
            ),
            ReportDomainProfile(
                name="البيئة المدرسية",
                score=71.75,
                level="الانطلاق",
                interpretation="يتأثر بالمرافق والخدمات المساندة والأمن والسلامة والصيانة.",
            ),
        ],
        strengths=[
            ReportIndicatorProfile(
                code="1-1-2-3",
                title="يظهر المتعلمون الاعتزاز بالقيم والهوية الوطنية",
                domain="نواتج التعلم",
                score=97.0,
                priority="medium",
                required_response="استدامة البرامج والشواهد وربطها بالمناسبات الوطنية والثقافية.",
            ),
            ReportIndicatorProfile(
                code="7-1-2-3",
                title="يظهر المتعلمون اعتزازًا بثقافتهم واحترامًا للتنوع الثقافي في المجتمع",
                domain="نواتج التعلم",
                score=94.0,
                priority="medium",
                required_response="حفظ الشواهد كنقاط قوة تستخدم في المقابلات والتقرير النهائي.",
            ),
            ReportIndicatorProfile(
                code="1-1-2-1",
                title="تعزز المدرسة القيم الإسلامية والهوية الوطنية",
                domain="الإدارة المدرسية",
                score=89.0,
                priority="medium",
                required_response="إظهار الاستدامة والابتكار لا مجرد التنفيذ.",
            ),
            ReportIndicatorProfile(
                code="2-1-2-1",
                title="تلتزم المدرسة بقيم مهنة التعليم وأخلاقياتها",
                domain="الإدارة المدرسية",
                score=87.5,
                priority="medium",
                required_response="توثيق الممارسات المهنية وأثرها على المناخ المدرسي.",
            ),
        ],
        improvement_priorities=[
            ReportIndicatorProfile(
                code="1-1-1-3",
                title="يحقق المتعلمون نتائج متقدمة في الاختبارات التحصيلية للمرحلة الثانوية",
                domain="نواتج التعلم",
                score=60.25,
                priority="critical",
                required_response="خطة رفع تحصيلي مبنية على تحليل نتائج، مجموعات علاجية، اختبارات قصيرة، وقياس أثر أسبوعي.",
            ),
            ReportIndicatorProfile(
                code="3-1-3-1",
                title="تعزز المدرسة الشراكة المجتمعية لدعم التعلم والتأثير الإيجابي في المجتمع المحلي",
                domain="الإدارة المدرسية",
                score=62.25,
                priority="critical",
                required_response="شراكات مرتبطة بالتعلم أو الانضباط أو الإرشاد مع أثر قابل للقياس وليس نشاطًا عامًا.",
            ),
            ReportIndicatorProfile(
                code="3-1-1-4",
                title="تلبي المرافق والخدمات المساندة احتياجات المتعلمين بمن فيهم ذوو الإعاقة",
                domain="البيئة المدرسية",
                score=62.5,
                priority="critical",
                required_response="قائمة فجوات مرافق وخدمات مساندة، إجراءات إغلاق، صور قبل/بعد، ونسبة إنجاز.",
            ),
            ReportIndicatorProfile(
                code="2-1-2-4",
                title="تعمل المدرسة على صيانة جميع مرافق المبنى وتجهيزاته بانتظام",
                domain="البيئة المدرسية",
                score=63.75,
                priority="critical",
                required_response="سجل صيانة دوري، أوامر تنفيذ، إغلاق مخاطر، وتقرير جاهزية قبل الزيارة.",
            ),
            ReportIndicatorProfile(
                code="1-1-4-1",
                title="تشجع المدرسة منسوبيها للحصول على الرخصة المهنية",
                domain="الإدارة المدرسية",
                score=65.25,
                priority="high",
                required_response="خطة دعم للرخصة، حصر المستهدفين، لقاءات تدريبية، ومتابعة تقدم كل معلم.",
            ),
            ReportIndicatorProfile(
                code="9-1-1-2",
                title="تنمي المدرسة المهارات الرقمية لدى المتعلمين",
                domain="التعليم والتعلم",
                score=66.25,
                priority="high",
                required_response="مهام رقمية صفية، منتجات طلابية، استخدام مصادر موثوقة، وشواهد مشاركة الطلاب.",
            ),
            ReportIndicatorProfile(
                code="1-1-2-2",
                title="تقوّم المدرسة أداء المتعلمين باستخدام أساليب وأدوات تقويم متنوعة وفاعلة",
                domain="التعليم والتعلم",
                score=67.25,
                priority="high",
                required_response="نماذج تقويم تشخيصي وتكويني وختامي، تحليل نتائج، وتغذية راجعة موثقة.",
            ),
            ReportIndicatorProfile(
                code="6-1-2-1",
                title="توفر المدرسة برامج وأنشطة إثرائية غير صفية لتطوير مواهب المتعلمين وتهيئتهم للمستقبل",
                domain="الإدارة المدرسية",
                score=67.5,
                priority="high",
                required_response="برنامج موهبة ومسابقات ومخرجات طلابية مرتبطة باحتياجات مستقبلية.",
            ),
            ReportIndicatorProfile(
                code="2-1-1-3",
                title="يحقق المتعلمون نتائج متقدمة في اختبارات القدرات العامة للمرحلة الثانوية",
                domain="نواتج التعلم",
                score=67.71,
                priority="high",
                required_response="خطة قدرات أسبوعية، تدريب على مهارات الاستدلال والقياس، ومتابعة تقدم.",
            ),
            ReportIndicatorProfile(
                code="1-1-2-4",
                title="تتوافر في فصول المدرسة ومعاملها وجميع مرافقها متطلبات الأمن والسلامة",
                domain="البيئة المدرسية",
                score=68.25,
                priority="high",
                required_response="قائمة فحص سلامة، تدريب إخلاء، إغلاق مخاطر، وشواهد توعية.",
            ),
            ReportIndicatorProfile(
                code="3-1-1-2",
                title="تنوع المدرسة في إستراتيجيات التدريس لتلبية احتياجات المتعلمين ودعم تعلمهم",
                domain="التعليم والتعلم",
                score=70.0,
                priority="high",
                required_response="زيارات صفية مركزة، نماذج دروس متنوعة، وتحليل أثر الاستراتيجية على تعلم الطلاب.",
            ),
        ],
        strategic_reading=(
            "الزيارة القادمة يجب أن تستهدف الانتقال من 73% في مستوى الانطلاق إلى 75% فأعلى أولًا، "
            "ثم بناء مسار تميز نحو 90%. أسرع طريق عملي هو رفع نواتج التعلم والبيئة المدرسية، "
            "مع تحويل الشراكات والتقويم الصفي والمهارات الرقمية إلى شواهد أثر واضحة."
        ),
    )


def domain_scores_from_report_profile(profile: SchoolReportProfile) -> list[DomainScore]:
    mapping = [
        ("الإدارة المدرسية", "leadership"),
        ("التعليم والتعلم", "teaching"),
        ("نواتج التعلم", "learning_outcomes"),
        ("البيئة المدرسية", "school_environment"),
    ]
    by_name = {item.name: item for item in profile.domains}
    domains = []
    for label, key in mapping:
        item = by_name.get(label)
        if not item:
            continue
        domains.append(
            DomainScore(
                key=key,
                label=label,
                previous_score=item.score,
                current_score=item.score,
                gap=0,
                evidence=[
                    f"درجة المجال في تقرير الزيارة السابقة: {item.score}%.",
                    item.interpretation,
                ],
            )
        )
    return domains
