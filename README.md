# Nexus Financial Analytics

داشبورد مالي تفاعلي مبني بـ Streamlit، بيحلل الإيرادات والمصروفات، يحسب الهوامش (Gross/Net Margin)، ويكشف المعاملات الشاذة تلقائيًا (Anomaly Detection).

## المميزات
- عرض بيانات تجريبية جاهزة أو رفع ملف CSV خاص بيك
- فلاتر بالتاريخ والفئة
- تبويب Trend Overview لعرض الإيرادات/المصروفات شهريًا
- تبويب Breakdown لتوزيع المصادر (Pie Charts)
- تبويب AI Flagging لاكتشاف المعاملات غير الطبيعية (Z-score)
- إعدادات COGS قابلة للتخصيص لحساب هامش الربح الإجمالي

## تشغيل المشروع محليًا
```bash
pip install -r requirements.txt
streamlit run financial_analyzer_ultra_dark.py
```

## تنسيق ملف CSV المطلوب
لازم يحتوي على الأعمدة التالية بالظبط (حروف صغيرة):

| date       | type    | category      | amount |
|------------|---------|---------------|--------|
| 2025-01-05 | Revenue | Product Sales | 1200.5 |
| 2025-01-06 | Expense | Rent          | 500    |

- `type`: لازم تكون Revenue أو Expense بس
- `date`: أي تنسيق تاريخ مفهوم (مثلاً YYYY-MM-DD)
- `amount`: رقم

جرّب بملف `sample_financial_data.csv` المرفق.

## النشر على Streamlit Community Cloud
1. ادخل على https://share.streamlit.io
2. سجل دخول بحساب GitHub
3. اختار "New app"
4. حدد الـ repository والـ branch وملف `financial_analyzer_ultra_dark.py`
5. اضغط Deploy
