# جدول تحقق HAMS — مطابقة العرض الفني مع Desk و API

**المنتج:** Hotel Asset Management (HAMS) ضمن `omnexa_fixed_assets` + تكامل ERPGenEx  
**قاعدة استدعاء API الموحّدة:** `POST` أو `GET` حسب الجدول إلى  
`https://<اسم_الموقع>/api/method/omnexa_fixed_assets.api.<اسم_الدالة>`  
(مع ترويسة الجلسة / مفتاح API حسب إعداد الموقع).

**ملاحظة مسارات Desk:** في Frappe 15 تُفتح النماذج عادةً من مساحة العمل **Fixed assets** (`/app/fixed-assets`) أو من شريط البحث (Awesome Bar) بكتابة اسم الـ DocType أو التقرير. المسارات التالية صيغ مرجعية شائعة (قد تختلف حسب إعداد المسار في الموقع):

| نوع | صيغة مرجعية |
|-----|----------------|
| مساحة العمل | `/app/fixed-assets` |
| قائمة DocType | `/app/List/<DocType>/List` مثال: `/app/List/Hotel%20Property/List` |
| نموذج محدد | `/app/fixed-asset/<اسم_السجل>` أو فتح من القائمة |

---

## 1) شاشات الوحدات (العرض الفني)

| # | شاشة العرض الفني | مسار Desk (مرجعي) | API ذات الصلة (`omnexa_fixed_assets.api`) | الحالة | موقّع UAT | تاريخ |
|---|------------------|-------------------|-------------------------------------------|--------|-----------|-------|
| 1 | Property Master Dashboard | `Hotel Property` + لوحة ارتباطات العقار؛ مساحة `Fixed assets` | — | مكتمل (Desk) | | |
| 2 | Room Asset Mapping Screen | `Hotel Room`، `Fixed Asset` (حقول فندقية)، تقرير **Assets by Room** | `locate_asset`, `get_asset_health_payload` | مكتمل | | |
| 3 | Asset Registration Form | `Fixed Asset`, `Fixed Asset Acquisition` | `run_monthly_depreciation_batch`, `run_auto_depreciation_policy_now` (إثر مالي لاحق) | مكتمل | | |
| 4 | Asset Lifecycle Timeline | `Fixed Asset` (الحالة)، `Fixed Asset Movement Log` | `get_asset_health_payload` | جزئي (لا يوجد خط زمني مرئي مخصص) | | |
| 5 | RFID Monitoring Console | `RFID Scan Log`، تقارير **Last Seen / Unscanned / Hotel Movement History** | `scan_asset`, `locate_asset` | مكتمل | | |
| 6 | Barcode Scan Interface | تبويب تعريف الأصل في `Fixed Asset` (باركود/QR) | `get_qr_svg_data_uri` | مكتمل (Desk + API للـ QR) | | |
| 7 | Inspection Checklist Screen | `Hotel Asset Inspection` | `submit_inspection` | مكتمل | | |
| 8 | Housekeeping Monitoring Dashboard | تقرير **Hotel Operational Asset Status**؛ حقول الهاوس كيبنج على الأصل | `update_condition` | مكتمل | | |
| 9 | Engineering Asset Console | `Asset Work Order`, `Asset Failure Event`, `Asset Meter Reading`؛ تقارير EAM | `get_condition_monitoring_console`, `get_scheduler_board_payload`, `ingest_asset_meter_reading` | مكتمل | | |
| 10 | Preventive Maintenance Calendar | `Asset Work Order` (عرض تقويم List) | `get_scheduler_board_payload` | مكتمل (Desk + حمولة API) | | |
| 11 | Maintenance Ticket Screen | `Asset Work Order`, `Fixed Asset Maintenance` | `create_work_order_from_alert` | مكتمل | | |
| 12 | Asset Transfer Workflow | `Hotel Asset Transfer` | — | مكتمل (Desk) | | |
| 13 | Missing Asset Alert Center | تقرير **Missing Assets**، `Asset Alert` | `scan_asset`, `locate_asset` (اكتشاف/موقع) | مكتمل | | |
| 14 | Warranty Tracking Screen | تبويب الضمان في `Fixed Asset`، تقرير **Warranty Expiring Assets** | — (جدولة: `hotel_notifications.create_warranty_expiry_alerts`) | مكتمل | | |
| 15 | Financial Asset Dashboard | تقارير التقييم/NBV/الإهلاك؛ بطاقات ومخططات مساحة **Fixed Assets** | `run_monthly_depreciation_batch`, `run_auto_depreciation_policy_now` | مكتمل | | |
| 16 | Replacement Forecast Dashboard | تقرير **Replacement Forecast Report** | — | مكتمل (تقرير) | | |
| 17 | Inventory Integration | (عادةً `Item`, `Stock Entry` في تطبيق المخزون) | — | خارج `omnexa_fixed_assets` | | |
| 18 | Procurement Integration | (عادةً `Purchase Order` في المشتريات) | — | خارج `omnexa_fixed_assets` | | |
| 19 | BI Reporting Dashboard | التقارير المرتبطة بمساحة العمل + مخططات `workspace_analytics` | `get_reliability_analytics_workbench`, `get_asset_command_center` | جزئي (ليس Power BI) | | |
| 20 | Executive KPI Dashboard | Number Cards على مساحة **Fixed Assets**؛ مركز القيادة | `get_asset_command_center` | جزئي / مكتمل حسب التعريف | | |

---

## 2) تطبيق Flutter (العرض الفني)

| # | شاشة | Desk/API في `omnexa_fixed_assets` | الحالة |
|---|------|-------------------------------------|--------|
| F1 | Login / Session | نفس آلية Frappe (`/api/method/login` …) | خارج نطاق التطبيق (عميل موبايل) |
| F2 | Mobile Dashboard | `get_asset_command_center`, `get_eam_feature_flags` | API جاهزة؛ واجهة Flutter غير موجودة هنا |
| F3 | Asset Scan Screen | `scan_asset`, `locate_asset` | API جاهزة |
| F4 | Inspection Form | `submit_inspection` | API جاهزة |
| F5 | Maintenance Request | `create_work_order_from_alert` أو إنشاء `Asset Work Order` عبر REST القياسي | جزئي (تخصيص مسار موبايل) |

---

## 3) سيناريوهات العرض الفني الإدارية

| # | خطوة السيناريو | Desk | API |
|---|----------------|------|-----|
| S1 | Purchase Order Entry | تطبيق المحاسبة/المشتريات | — |
| S1 | Goods Receipt | المخزون | — |
| S1 | Asset Registration | `Fixed Asset` / `Fixed Asset Acquisition` | — |
| S1 | Tag Assignment | `Fixed Asset` (RFID/Barcode) | `scan_asset` (تسجيل مسح) |
| S1 | Asset Approval Workflow | سير عمل DocType حسب الإعداد | — |
| S1 | Asset Allocation | `Fixed Asset` حقول فندقية + `Hotel Asset Transfer` | `locate_asset` |
| S2 | Inspection cycle (إشعار/ميدان) | `Hotel Asset Inspection` | `submit_inspection` |
| S3 | Missing asset | التقارير + `Asset Alert` | `scan_asset`, `locate_asset` |
| S4 | Maintenance lifecycle | `Asset Work Order` | `create_work_order_from_alert`, `get_scheduler_board_payload` |

---

## 4) فهرس دوال API (`omnexa_fixed_assets.api`)

| الدالة | الغرض المختصر |
|--------|----------------|
| `run_monthly_depreciation_batch` | دفعة إهلاك شهرية |
| `run_auto_depreciation_policy_now` | تشغيل سياسة الإهلاك الآلي |
| `ingest_asset_meter_reading` | استقبال قراءة عدّاد |
| `get_asset_health_payload` | بيانات صحة الأصل للعرض الخارجي |
| `run_asset_reliability_recompute` | إعادة حساب الموثوقية/الصحة |
| `get_eam_feature_flags` | أعلام الميزات (بما فيها الفندق) |
| `seed_hotel_demo_assets_from_company` | بذرة تجريبية (System Manager) |
| `scan_asset` | تسجيل مسح RFID فندقي |
| `locate_asset` | آخر موقع/غرفة للأصل |
| `get_qr_svg_data_uri` | توليد QR كـ data-uri |
| `update_condition` | تحديث هندسة/هاوس كيبنج على الأصل |
| `submit_inspection` | إنشاء `Hotel Asset Inspection` |
| `get_asset_command_center` | حمولة KPI/تنبيهات/أصول حرجة |
| `get_reliability_analytics_workbench` | اتجاهات الموثوقية + باريتو الأعطال |
| `get_scheduler_board_payload` | أوامر العمل للتقويم/اللوحة |
| `get_condition_monitoring_console` | قراءات العداد + تنبيهات |
| `create_work_order_from_alert` | أمر عمل من تنبيه |

---

## 5) تعليمات التوقيع

1. يملأ فريق **الأعمال (UAT)** عمودي **موقّع UAT** و**التاريخ** بعد التحقق على بيئة الاختبار.  
2. **جزئي** يعني: الوظيفة موجودة لكن تختلف عن العرض الفني (مثلاً لا يوجد Waterfall/Flutter).  
3. **خارج النطاق** يتطلب تطبيقاً آخر أو مشروع عميل منفصل.

---

*آخر تحديث تلقائي للمطابقة مع الكود: وثيقة مولَّدة من مستودع `omnexa_fixed_assets`.*
