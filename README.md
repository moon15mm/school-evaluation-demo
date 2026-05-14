# School Evaluation Demo

نسخة عرض على الإنترنت لنظام:

**Autonomous School Evaluation & Improvement System**

هذه النسخة مخصصة للتسويق والعرض، وتعمل بوضع بيانات افتراضية آمنة.

## حساب العرض

- username: `demo`
- password: `demo123`

حساب العرض للقراءة فقط ولا يملك صلاحية تعديل البيانات.

## التشغيل المحلي

```bash
pip install -r requirements.txt
set DEMO_MODE=true
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

ثم افتح:

```text
http://127.0.0.1:8000
```

## النشر على Render

المستودع يحتوي على ملف `render.yaml`.

1. افتح Render.
2. اختر `New`.
3. اختر `Blueprint`.
4. اربط هذا المستودع.
5. تأكد أن متغير البيئة `DEMO_MODE=true`.
6. بعد اكتمال النشر استخدم حساب `demo / demo123`.

## ملاحظة

هذه نسخة Demo. لا تستخدمها لحفظ بيانات مدرسة حقيقية على استضافة مجانية دون تخزين دائم أو قاعدة بيانات.

## نسخ المراحل

يمكن تشغيل نفس المستودع كثلاث نسخ مختلفة عبر متغير البيئة:

- `DEMO_STAGE=secondary` للمرحلة الثانوية.
- `DEMO_STAGE=intermediate` للمرحلة المتوسطة.
- `DEMO_STAGE=primary` للمرحلة الابتدائية.

أنشئ Web Service جديدًا في Render من نفس المستودع، ثم غيّر قيمة `DEMO_STAGE` واسم الخدمة فقط.

أسماء مقترحة للخدمات:

- `school-evaluation-secondary-demo` مع `DEMO_STAGE=secondary`.
- `school-evaluation-intermediate-demo` مع `DEMO_STAGE=intermediate`.
- `school-evaluation-primary-demo` مع `DEMO_STAGE=primary`.

كل نسخة ستنشئ ذاكرة افتراضية مختلفة عند أول تشغيل، لذلك لا تستخدم نفس خدمة Render لتبديل المرحلة بعد أن تكون البيانات قد تولدت. الأفضل إنشاء خدمة مستقلة لكل مرحلة.
