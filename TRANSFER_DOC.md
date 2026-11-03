﻿# سند انتقال پروژه LIMS_FINAL_Deep

**نسخه:** بعد از فاز جستجوی عمومی و مدیریت گواهینامه‌های برون‌سپاری

---

## خلاصه کلی پروژه

سامانه LIMS آزمایشگاه مرکزی ماشین‌سازی اراک، شامل ۵ بخش:
- مکانیک
- متالوگرافی
- آنالیز شیمیایی
- کالیبراسیون
- PMI

مطابق با ISO/IEC 17025:2017

---
## فازهای انجام‌شده

### فاز ۱: تمیزکاری اولیه
- حذف فایل‌های دیباگ و تست
- مرتب‌سازی scripts به ۳ زیرپوشه (setup, import, maintenance)
- آرشیو checkpoint های قدیمی

### فاز ۲: رفع encoding
- رفع UnicodeEncodeError در lims_preflight.py
- UTF-8 BOM برای base.html
- افزودن PYTHONIOENCODING=utf-8 به start.ps1

### فاز ۳: کالیبراسیون — اصلاحات
- حذف منوی تکراری کالیبراسیون
- MPE قابل ویرایش دستی
- وضعیت هر نقطه + وضعیت کلی

### فاز ۴: تجهیزات مرجع چندتایی
- مدل CalibrationReference
- انتخاب از لیست + پر شدن خودکار

### فاز ۵: عدم قطعیت
- فیلدهای u, U, k, confidence
- محاسبه خودکار U = u × k

### فاز ۶: برون‌سپاری
- مدل OutsourcedCalibration
- مدل OutsourcedCertificateFile
- CRUD کامل + آپلود چند فایل
- بایگانی و برگردان

### فاز ۷: Permissions
- ۸ permission جدید کالیبراسیون
- بروزرسانی ۳۰ پروفایل

### فاز ۸: گزارش‌ساز گواهی (GrapesJS)
- مدل CertificateTemplate
- صفحه Builder با drag and drop
- ۳ قالب آماده

### فاز ۹: CompanyInfo
- مدل Singleton قابل ویرایش از ادمین

### فاز ۱۰: اطلاعات محیطی + امضاها
- env_temperature, env_humidity, env_pressure
- signer_calibrator, signer_supervisor, signer_head

### فاز ۱۱: جستجوی عمومی
- دکمه جستجو در صفحه لاگین (بدون auth)
- جستجوی تکی + جستجوی واحد
- کارت اطلاعات + دکمه مشاهده گواهی
- گالری تصاویر چندصفحه‌ای

### فاز ۱۲: Import از فایل‌سیستم
- کامپرس ۱۷۰۰ MB به ۲۰۶ MB
- ورود ۱۰۸۲ فایل گواهینامه برای ۴۶۹ تجهیز

### فاز ۱۳: Import Master List
- تابع _import_master_list
- تابع _sync_all_equipment_status

---
## Migrations مهم

| # | نام | موضوع |
|---|-----|-------|
| 0057 | calibrationreference | تجهیزات مرجع چندتایی |
| 0058 | calibrationregistry_uncertainty | عدم قطعیت |
| 0059 | alter_confidence_level | اصلاح فیلدها |
| 0060 | outsourcedcalibration | مدل برون‌سپاری |
| 0061 | outsourcedcertificatefile | فایل‌های چندتایی |
| 0062 | env_signers | محیط + امضاها |
| 0063 | alter_calibrationregistry | اصلاح فیلدها |
| 0064 | companyinfo | اطلاعات شرکت |
| 0065 | certificatetemplate | قالب گواهی |
| 0066 | archive | بایگانی فایل‌ها |

---

## URL های مهم

### عمومی (بدون لاگین)
- /login/                          صفحه ورود + جستجو
- /public/outsourced/<pk>/         جزئیات برون‌سپاری
- /public/outsourced/<pk>/gallery/ گالری تصاویر
- /public/cert-file/<pk>/view/     فایل گواهینامه
- /public/certificate/<pk>/        گواهی داخلی

### داخلی (نیاز به لاگین)
- /calibration/                    آرشیو کالیبراسیون
- /calibration/master-list/        مستر لیست تجهیزات
- /calibration/register/new/       ثبت کالیبراسیون جدید
- /calibration/outsourced/         لیست برون‌سپاری
- /calibration/certificate-builder/ قالب‌ساز گواهی
- /calibration/mpe-rules/          قوانین MPE
- /calibration/interval/           دوره‌های کالیبراسیون
- /calibration/import/             Import از Excel
- /calibration/sync-master/        سینک Master List

---
## مدل‌های اصلی

### CalibrationEquipment (مستر لیست)
- code, name, spec, range_text, accuracy
- location, requester, scope_io
- last_calibration, next_calibration

### CalibrationRegistry
- equipment_code, report_no, request_no
- date_request, date_report, date_test_current, date_test_next
- points (JSON), max_error, tolerance, mpe_type, status
- env_temperature, env_humidity, env_pressure
- calibration_method, calibration_description
- standard_uncertainty, expanded_uncertainty, coverage_factor
- signer_calibrator, signer_supervisor, signer_head

### CalibrationReference
- calibration (FK), reference_equipment (FK)
- reference_code_snapshot, reference_name_snapshot
- certificate_no, certificate_date, notes

### OutsourcedCalibration
- equipment (FK), equipment_code, equipment_name
- calibration_lab, lab_accreditation
- date_sent, calibration_date, next_date
- certificate_no, uncertainty, scope, notes, status

### OutsourcedCertificateFile
- outsourced (FK), file, title, page_order
- is_archived, archived_at

### CompanyInfo (Singleton)
- company_name_fa/en, lab_name_fa/en
- address_fa, phone, fax, website, email
- form_code, form_revision, form_issue_date
- iso_standard

### CertificateTemplate
- name, html, css, is_default, is_active

---
## نکات مهم

### کامپرس گواهینامه‌ها
- Source: F:\کالیبراسیون\calibration\مستندات...\گواهینامه کالیبراسیون
- Compressed: ...\گواهینامه کالیبراسیون_compressed
- تنظیمات: MAX_DIM=1400, JPEG_QUALITY=65
- کاهش: 88 درصد

### مسیر شبکه Excel
- \\qnas\msa\Projects\QA\Lab\Calibration\
- FORM TEST.xlsm
- Calibration Data Bank.xlsm

### اولویت Master List
1. FORM TEST.xlsm / master list
2. Calibration Data Bank.xlsm / master list

---

## کارهای باقی‌مانده

### اولویت بالا
- [ ] به‌روزرسانی PROJECT_CONTEXT.md
- [ ] بازنویسی README_FA.md
- [ ] رفع encoding models_calib.py و urls.py

### اولویت متوسط
- [ ] شکستن views.py به پکیج
- [ ] شکستن models.py به پکیج
- [ ] اضافه کردن تست‌های خودکار

### اولویت پایین
- [ ] API REST
- [ ] گزارش‌های تحلیلی
- [ ] بهبود UI/UX

---

## اطلاعات فنی

- Python: 3.14.3
- Django: 5.2.17
- Database: SQLite
- Migration آخر: 0066

---

## آمار پروژه

- Equipment: 3891
- Registry: 39131
- Outsourced: 469
- CertificateFile: 1082
- Users: 30
- TestRequests: 7619

---

## امضا

این سند به‌صورت خودکار به‌روزرسانی شده است.

---

## فاز جدید — تکمیل کالیبراسیون و مدیریت تجهیزات مرجع (2026-10-14 12:57)

### منوی کاربری بازطراحی‌شده
- ۵ گروه کشویی: کارتابل‌ها / گزارش و آمار / کیفیت (QMS) / کالیبراسیون / استاندارد و حدود
- گروه مدیریت جداگانه (فقط admin): کاربران، بکاپ، ورود Excel، لینک‌ها، پنل ادمین

### داشبورد تحلیلی
- نمودار خطی ماهانه (Chart.js)
- آمار بر اساس واحد متقاضی
- آمار بر اساس نوع آزمون
- فیلتر بازه تاریخ شمسی + واحد + دسته آزمون
- خروجی Excel

### گزارش ماهانه موعد کالیبراسیون
- مسیر: /calibration/monthly-due/
- سورت: گروه → واحد → نام → کد → تاریخ
- گروه‌بندی بصری + کارت‌های آماری
- دکمه ارسال اعلان برای کاربران

### اعلان خودکار ماهانه کالیبراسیون
- مدل `CalibrationAlertSettings` (Singleton)
- قابل تنظیم از ادمین: نقش‌ها + کاربران دستی
- ارسال خودکار در dashboard_redirect
- صفحه اعلان‌ها: /notifications/ با فیلتر + Pagination
- Management Command: `python manage.py check_monthly_alerts`

### گروه‌ها و زیرگروه‌های تجهیزات
- مدل `EquipmentGroup` (۱۱ گروه)
- مدل `EquipmentSubGroup` (۸۲ زیرگروه)
- FK از `CalibrationEquipment.equipment_group` و `equipment_subgroup` (۳۸۹۱ رکورد)
- Admin با inline برای ویرایش سریع
- پشتیبانی در جستجو، master list، API

### مدیریت تجهیزات مرجع
- آپلود چند فایل همزمان با پیش‌نمایش
- دکمه‌های حذف/جابجایی فایل
- افزودن فایل به گواهی موجود (Ajax)
- نمایش فایل در مرورگر (نه دانلود)
- شماره گواهینامه LTR
- هشدار اعتبار گواهی (۵ سطح: معتبر/نزدیک/فوری/بحرانی/منقضی)
- کارت‌های آماری در لیست تجهیزات مرجع
- محدودیت حذف: فقط admin + فقط بایگانی

### صفحه تاریخچه تجهیز کالیبراسیون
- از Master List + Registry + Outsourced
- مشخصات کامل + ۲ کارت آماری + ۲ جدول
- مسیر: /calibration/equipment/<code>/

### طراحی جدید گواهی کالیبراسیون
- هدر گرادیانت با حباب‌های تزئینی
- کارت‌های رنگی (آبی/سبز/بنفش/زرد)
- عدم قطعیت پایین نتایج
- امضاها + فوتر گرادیانت
- مناسب چاپ A4 تک‌صفحه

### رفع باگ‌ها
- view `calibration_master_print` از بکاپ بازیابی شد
- `_public_unit_equipment` با FK جدید هماهنگ شد
- `ref_certificate_upload` با import `ReferenceCertificateFile`
- منوی «تجهیزات» قدیمی حذف شد (۰ رکورد)

### Migrations جدید
- 0067: equipment_groups
- 0068: calibrationalertsettings
- 0069: calibration_equipment_fk

### آمار فعلی
- CalibrationEquipment: ۳۸۹۱ (همه با FK)
- EquipmentGroup: ۱۱
- EquipmentSubGroup: ۸۲
- OutsourcedCalibration: ۴۶۹
- OutsourcedCertificateFile: ۱۰۸۲
- CalibrationRegistry: ۳۹۱۳۱
- TestRequest: ۷۶۱۹
- Notification: ~۷۰
