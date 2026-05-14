from __future__ import annotations

from app.core.models import DOMAIN_LABELS, VisitRecord


class ImpactFileAgent:
    def advise(self, visit: VisitRecord, existing_count: int = 0) -> dict:
        priorities = self._priority_indicators(visit)
        targets = [self._target_from_priority(item, index) for index, item in enumerate(priorities[:6], start=1)]
        if len(targets) < 6:
            targets.extend(self._targets_from_weaknesses(visit, start=len(targets) + 1))
        targets = targets[:6]
        return {
            "agent_name": "وكيل ملف الأثر",
            "school_truth": self._school_truth(visit),
            "current_impact_count": existing_count,
            "completion_level": self._completion_level(existing_count),
            "measurable_targets": targets,
            "golden_rules": [
                "لا تُقبل قصة أثر بلا قياس قبلي وبعدي.",
                "كل أثر يجب أن يرتبط بمؤشر تقويم محدد لا بعنوان برنامج عام.",
                "أفضل قصة أثر تجمع رقمًا وصورة وشهادة ونتيجة اختبار.",
                "الأثر الأقوى هو الذي يوضح تغير الطالب أو المعلم أو البيئة، وليس مجرد تنفيذ نشاط.",
            ],
            "minimum_package": [
                "3 قصص أثر في نواتج التعلم.",
                "قصة أثر في جودة التعليم والتعلم.",
                "قصة أثر في البيئة المدرسية أو السلامة.",
                "قصة أثر في الشراكة أو الدعم الطلابي إذا كانت مرتبطة بنتيجة قابلة للقياس.",
            ],
        }

    def _school_truth(self, visit: VisitRecord) -> str:
        if visit.report_profile:
            low_domains = sorted(visit.report_profile.domains, key=lambda item: item.score)[:2]
            names = " و ".join(f"{item.name} ({item.score}%)" for item in low_domains)
            return (
                f"حقيقة المدرسة من الزيارة السابقة: الدرجة العامة {visit.report_profile.overall_score}%، "
                f"وأكثر ما يحتاج ملف أثر مقاس هو {names}. لذلك يجب أن يثبت الملف تغيرًا رقميًا في تعلم الطلاب "
                "أو جاهزية البيئة، لا كثرة برامج منفذة."
            )
        weakest = sorted(visit.domains, key=lambda item: item.current_score)[:2]
        names = " و ".join(f"{item.label} ({item.current_score}%)" for item in weakest)
        return f"حقيقة المدرسة الحالية تشير إلى أن الأولوية في ملف الأثر هي {names} مع قياس قبل/بعد واضح."

    def _priority_indicators(self, visit: VisitRecord) -> list:
        if not visit.report_profile:
            return []
        return sorted(
            visit.report_profile.improvement_priorities,
            key=lambda item: ({"critical": 0, "high": 1, "medium": 2}.get(item.priority, 3), item.score or 100),
        )

    def _target_from_priority(self, indicator, index: int) -> dict:
        before_metric, after_metric, evidence = self._metric_recipe(indicator.domain, indicator.title)
        return {
            "rank": index,
            "title": f"أثر تحسين: {indicator.title}",
            "domain": indicator.domain,
            "indicator": indicator.code,
            "why_this": f"المؤشر درجته {indicator.score}% وأولويته {indicator.priority}؛ أي تحسن موثق فيه سيرفع مصداقية الزيارة القادمة.",
            "before_metric": before_metric,
            "after_metric": after_metric,
            "measurement_method": "اختبار/رصد قبلي ثم تدخل قصير ثم قياس بعدي بنفس الأداة أو أداة مكافئة.",
            "required_files": evidence,
            "suggested_narrative": (
                f"استهدفت المدرسة مؤشر {indicator.code} عبر تدخل قصير مرتبط بالميدان. "
                f"تم توثيق الوضع القبلي، تنفيذ الإجراء، ثم قياس الوضع البعدي لإثبات الأثر."
            ),
            "success_threshold": self._threshold(indicator.domain),
        }

    def _targets_from_weaknesses(self, visit: VisitRecord, start: int) -> list[dict]:
        targets = []
        for offset, weakness in enumerate(visit.weaknesses[:6], start=start):
            domain = DOMAIN_LABELS.get(weakness.domain, weakness.domain)
            before_metric, after_metric, evidence = self._metric_recipe(domain, weakness.title)
            targets.append(
                {
                    "rank": offset,
                    "title": f"أثر إغلاق فجوة: {domain}",
                    "domain": domain,
                    "indicator": weakness.title,
                    "why_this": weakness.impact,
                    "before_metric": before_metric,
                    "after_metric": after_metric,
                    "measurement_method": "قائمة رصد أو اختبار قصير قبل/بعد مع عينة واضحة وتاريخ محدد.",
                    "required_files": evidence,
                    "suggested_narrative": f"تم اختيار فجوة {domain} لأنها مؤثرة في حكم فريق التقويم، ثم قياس أثر إجراء محدد عليها.",
                    "success_threshold": self._threshold(domain),
                }
            )
        return targets

    def _metric_recipe(self, domain: str, title: str) -> tuple[str, str, list[str]]:
        text = f"{domain} {title}"
        if "نواتج" in text or "اختبار" in text or "تحصيل" in text or "قدرات" in text:
            return (
                "نسبة الإتقان أو متوسط الدرجة في اختبار قبلي محدد لعينة طلابية.",
                "نسبة الإتقان أو متوسط الدرجة في اختبار بعدي لنفس المهارة والعينة.",
                ["تحليل اختبار قبلي", "خطة علاجية", "تحليل اختبار بعدي", "رسم بياني للتحسن", "عينات أعمال طلاب"],
            )
        if "تعليم" in text or "تدريس" in text or "تقويم" in text or "رقمية" in text:
            return (
                "نسبة تحقق ممارسات التعلم النشط/التقويم أثناء الحصة في زيارة صفية قبلية.",
                "نسبة تحقق الممارسات بعد التدريب أو المجتمع المهني.",
                ["استمارة زيارة قبلية", "خطة تحسين درس", "استمارة زيارة بعدية", "صور منتجات طلابية", "تغذية راجعة للمعلم"],
            )
        if "بيئة" in text or "سلامة" in text or "مرافق" in text or "صيانة" in text:
            return (
                "عدد فجوات السلامة أو الصيانة المفتوحة ونسبة الجاهزية قبل التدخل.",
                "نسبة إغلاق الفجوات وجاهزية المرافق بعد التدخل.",
                ["صور قبل", "قائمة فحص", "أوامر صيانة", "صور بعد", "محضر إغلاق الفجوات"],
            )
        if "شراكة" in text or "مجتمعية" in text:
            return (
                "حاجة محددة في التعلم أو الانضباط قبل الشراكة.",
                "نتيجة قابلة للقياس بعد الشراكة، مثل حضور أو إتقان أو رضا مستفيدين.",
                ["اتفاقية/خطاب شراكة", "خطة تنفيذ", "بيانات قبل/بعد", "استبانة رضا", "صور تنفيذ"],
            )
        return (
            "وصف رقمي للوضع قبل التدخل.",
            "وصف رقمي للوضع بعد التدخل.",
            ["شاهد قبل", "خطة تدخل", "شاهد بعد", "ملخص أثر رقمي"],
        )

    def _threshold(self, domain: str) -> str:
        if "نواتج" in domain:
            return "تحسن لا يقل عن 10 نقاط مئوية أو انتقال 60% من الطلاب المستهدفين إلى مستوى الإتقان."
        if "بيئة" in domain or "سلامة" in domain:
            return "إغلاق 90% فأكثر من الفجوات المفتوحة قبل الزيارة."
        if "تعليم" in domain:
            return "تحسن لا يقل عن 20% في تحقق الممارسة الصفية المستهدفة."
        return "تحسن رقمي واضح مع شاهد قبل/بعد وشهادة تحقق."

    def _completion_level(self, existing_count: int) -> str:
        if existing_count >= 6:
            return "ملف الأثر متقدم؛ راجع جودة القياسات والمرفقات."
        if existing_count >= 3:
            return "ملف الأثر جيد؛ يحتاج إكمال المجالات الناقصة."
        if existing_count >= 1:
            return "بداية جيدة؛ يلزم بناء قصص أثر إضافية."
        return "لم يبدأ ملف الأثر بعد؛ ابدأ بالأهداف الأعلى أثرًا."
