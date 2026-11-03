# -*- coding: utf-8 -*-
"""
مدل‌های مرجع کالیبراسیون — بر اساس دستورالعمل کدگذاری
"""
from django.db import models


class EquipmentLocation(models.Model):
    """جدول ۲ — محل استفاده (۱ تا ۹۹)"""
    number = models.IntegerField(unique=True, verbose_name="شماره")
    name = models.CharField(max_length=150, verbose_name="نام محل")
    production_group = models.ForeignKey(
        'ProductionGroup', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='units',
        verbose_name="گروه تولیدی")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        ordering = ['number']
        verbose_name = "محل استفاده تجهیز"
        verbose_name_plural = "۱. محل‌های استفاده"

    def __str__(self):
        return f"{self.number} — {self.name}"


class EquipmentNameCode(models.Model):
    """جدول ۱ — نام تجهیز (پیشوند کد)"""
    TYPE_CHOICES = [
        ('dimensional', 'ابعادی'),
        ('welding', 'جوش و کنترل دما'),
        ('other', 'سایر'),
    ]

    code = models.CharField(max_length=10, unique=True, verbose_name="کد")
    name_fa = models.CharField(max_length=150, verbose_name="نام فارسی")
    name_en = models.CharField(max_length=150, blank=True, verbose_name="نام لاتین")
    equipment_type = models.CharField(max_length=30, choices=TYPE_CHOICES,
                                       default='dimensional', verbose_name="نوع تجهیز")
    importance_factor = models.FloatField(
        default=1.0, verbose_name="ضریب اهمیت",
        help_text="برای محاسبه درصد ارائه خدمات وزنی. مثال: کولیس=1، جوش=1.5، گونیا=0.6")

    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        ordering = ['code']
        verbose_name = "نام تجهیز (کد)"
        verbose_name_plural = "۲. نام‌های تجهیزات"

    def __str__(self):
        return f"{self.code} — {self.name_fa}"


class RangeSpec(models.Model):
    """جدول ۳ — مشخصه رنج اندازه‌گیری"""
    GROUP_CHOICES = [
        ('caliper', 'کولیس'),
        ('micrometer', 'میکرومتر'),
        ('micrometer_internal', 'میکرومتر داخلی'),
        ('indicator', 'اندیکاتور'),
    ]

    equipment_group = models.CharField(max_length=30, choices=GROUP_CHOICES,
                                        verbose_name="گروه تجهیز")
    code = models.CharField(max_length=5, verbose_name="کد رنج")
    range_text = models.CharField(max_length=50, verbose_name="رنج")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        ordering = ['equipment_group', 'code']
        unique_together = [('equipment_group', 'code')]
        verbose_name = "مشخصه رنج"
        verbose_name_plural = "۳. مشخصه‌های رنج"

    def __str__(self):
        return f"{self.get_equipment_group_display()} | {self.code} = {self.range_text}"


class QuantitySpec(models.Model):
    """جدول ۴ — کمیت تحت اندازه‌گیری (برای جوش)"""
    code = models.CharField(max_length=5, unique=True, verbose_name="کد")
    name_fa = models.CharField(max_length=100, verbose_name="نام کمیت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        ordering = ['code']
        verbose_name = "کمیت اندازه‌گیری"
        verbose_name_plural = "۴. کمیت‌های اندازه‌گیری"

    def __str__(self):
        return f"{self.code} — {self.name_fa}"


# ═══════════════════════════════════════════════════════════
# آرشیو کالیبراسیون
# ═══════════════════════════════════════════════════════════

class CalibrationRegistry(models.Model):
    """آرشیو کالیبراسیون‌ها — از فایل‌های اکسل"""

    # ─── هویت تجهیز ───
    equipment_code = models.CharField(max_length=100, db_index=True, verbose_name="کد کامل تجهیز")
    equipment_code_base = models.CharField(max_length=80, db_index=True, blank=True, verbose_name="کد پایه")
    parameter_suffix = models.CharField(max_length=10, blank=True, verbose_name="پسوند (کمیت)")
    equipment_name = models.CharField(max_length=200, verbose_name="نام ابزار")
    equipment_spec = models.CharField(max_length=200, blank=True, verbose_name="سایر مشخصات")
    range_text = models.CharField(max_length=100, blank=True, verbose_name="رنج اندازه‌گیری")
    accuracy = models.CharField(max_length=50, blank=True, verbose_name="دقت")
    unit = models.CharField(max_length=20, blank=True, verbose_name="واحد")

    # ─── متقاضی / آزمایشگاه ───
    requester = models.CharField(max_length=200, blank=True, verbose_name="متقاضی / کارگاه")
    lab = models.CharField(max_length=200, blank=True, verbose_name="آزمایشگاه مرجع")

    # ─── گزارش ───
    report_no = models.CharField(max_length=50, db_index=True, verbose_name="شماره گزارش")
    request_no = models.CharField(max_length=50, blank=True, verbose_name="شماره درخواست")
    date_request = models.CharField(max_length=20, blank=True, verbose_name="تاریخ درخواست")
    date_report = models.CharField(max_length=20, blank=True, verbose_name="تاریخ گزارش")
    date_test_current = models.CharField(max_length=20, blank=True, verbose_name="تاریخ تست فعلی")
    date_test_next = models.CharField(max_length=20, blank=True, verbose_name="تاریخ تست بعدی")

    # ─── تجهیز مرجع ───
    reference_tool = models.CharField(max_length=200, blank=True, verbose_name="تجهیز مرجع")
    reference_code = models.CharField(max_length=100, blank=True, verbose_name="کد شناسایی مرجع")
    certificate_no = models.CharField(max_length=100, blank=True, verbose_name="شماره گواهینامه")

    # ─── استاندارد ───
    standard = models.CharField(max_length=100, blank=True, verbose_name="استاندارد")

    # ─── نقاط اندازه‌گیری ───
    # [{"ref": 100, "reading": 100, "error": 0}, ...]
    points = models.JSONField(default=list, blank=True, verbose_name="نقاط اندازه‌گیری")

    # ─── وضعیت ───
    MPE_TYPE_CHOICES = [
        ('absolute', 'مطلق (عدد ثابت)'),
        ('percent_reading', 'درصد قرائت'),
        ('percent_range', 'درصد فول اسکیل'),
        ('range_dependent', 'وابسته به رنج'),
    ]
    max_error = models.FloatField(null=True, blank=True, verbose_name="حداکثر خطا")
    tolerance = models.FloatField(null=True, blank=True, verbose_name="حد مجاز خطا")
    mpe_type = models.CharField(max_length=30, choices=MPE_TYPE_CHOICES,
                                 default='absolute', blank=True,
                                 verbose_name="نوع حد مجاز")
    tolerance_note = models.CharField(max_length=200, blank=True,
                                       verbose_name="توضیح حد مجاز")

    # ═══ عدم قطعیت (Uncertainty) ═══
    standard_uncertainty = models.FloatField(null=True, blank=True, verbose_name="عدم قطعیت استاندارد (u)")
    expanded_uncertainty = models.FloatField(null=True, blank=True, verbose_name="عدم قطعیت بسط‌یافته (U)")
    coverage_factor = models.FloatField(null=True, blank=True, default=2.0, verbose_name="ضریب پوشش (k)")
    confidence_level = models.FloatField(null=True, blank=True, default=95.0, verbose_name="سطح اطمینان (%)")
    decision_rule = models.CharField(max_length=30, blank=True, default="simple", verbose_name="قاعده تصمیم")
    guard_band = models.FloatField(null=True, blank=True, verbose_name="ناحیه حفاظتی")
    tur = models.FloatField(null=True, blank=True, verbose_name="نسبت TUR (Tolerance/U)")
    uncertainty_note = models.CharField(max_length=300, blank=True, verbose_name="توضیح عدم قطعیت")
    uncertainty_budget = models.JSONField(default=list, blank=True, verbose_name="بودجه عدم قطعیت")
    env_temperature = models.CharField(max_length=20, blank=True, verbose_name="env_temp")
    env_humidity = models.CharField(max_length=20, blank=True, verbose_name="env_humidity")
    env_pressure = models.CharField(max_length=20, blank=True, verbose_name="env_pressure")
    calibration_method = models.CharField(max_length=200, blank=True, verbose_name="cal_method")
    calibration_description = models.TextField(blank=True, verbose_name="cal_desc")
    signer_calibrator = models.CharField(max_length=100, blank=True, verbose_name="signer_cal")
    signer_supervisor = models.CharField(max_length=100, blank=True, verbose_name="signer_sup")
    signer_head = models.CharField(max_length=100, blank=True, verbose_name="signer_head")
    status = models.CharField(max_length=20, blank=True, verbose_name="وضعیت")

    # ─── یادداشت ───
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # ─── گروه تولیدی و واحد ───
    production_group = models.ForeignKey(
        'ProductionGroup', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='calibrations', verbose_name="گروه تولیدی")
    unit_code = models.CharField(max_length=20, blank=True, verbose_name="کد واحد")
    unit_name = models.CharField(max_length=200, blank=True, verbose_name="نام واحد")

    # ─── قیمت ───
    unit_price = models.IntegerField(default=0, verbose_name="هزینه واحد (ریال)")
    total_price = models.IntegerField(default=0, verbose_name="هزینه کل (ریال)")

    # ─── منبع ───
    source_file = models.CharField(max_length=100, blank=True, verbose_name="فایل منبع")

    # ─── منبع ───
    source_file = models.CharField(max_length=100, blank=True, verbose_name="فایل منبع")
    source_sheet = models.CharField(max_length=50, blank=True, verbose_name="شیت منبع")
    source_row = models.IntegerField(null=True, blank=True, verbose_name="ردیف منبع")

    # ─── Meta ───
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-report_no', '-id']
        unique_together = [('report_no', 'equipment_code')]
        verbose_name = "آرشیو کالیبراسیون"
        verbose_name_plural = "۵. آرشیو کالیبراسیون"

    def __str__(self):
        return f"{self.report_no} | {self.equipment_code}"

    def points_with_status(self):
        """برمی‌گرداند نقاط با وضعیت محاسبه‌شده (برای رکوردهای قدیمی)"""
        tol = self.tolerance
        out = []
        for p in (self.points or []):
            q = dict(p)
            if 'status' not in q or not q.get('status'):
                if tol and tol > 0 and 'error' in q:
                    try:
                        err = abs(float(q['error']))
                        q['status'] = 'accepted' if err <= tol else 'rejected'
                    except (ValueError, TypeError):
                        q['status'] = ''
                else:
                    q['status'] = ''
            # حد مجاز هر نقطه
            if not q.get('tolerance'):
                q['tolerance'] = tol
            out.append(q)
        return out

    def overall_status_display(self):
        """وضعیت کلی محاسبه‌شده"""
        if self.status in ('accepted', 'rejected'):
            return self.status
        pts = self.points_with_status()
        statuses = [p.get('status') for p in pts if p.get('status')]
        if not statuses:
            return ''
        return 'accepted' if all(s == 'accepted' for s in statuses) else 'rejected'



class CalibrationEquipment(models.Model):
    """کاتالوگ تجهیزات — از master list"""
    code = models.CharField(max_length=100, unique=True, db_index=True, verbose_name="کد تجهیز")
    code_base = models.CharField(max_length=80, db_index=True, blank=True, verbose_name="کد پایه")
    name = models.CharField(max_length=200, verbose_name="نام تجهیز")
    spec = models.CharField(max_length=200, blank=True, verbose_name="مشخصات")
    range_text = models.CharField(max_length=100, blank=True, verbose_name="رنج")
    accuracy = models.CharField(max_length=50, blank=True, verbose_name="دقت")
    location = models.CharField(max_length=200, blank=True, verbose_name="محل استفاده (متنی)")
    requester = models.CharField(max_length=200, blank=True, verbose_name="درخواست‌کننده (متنی)")

    # ═══ گروه و زیرگروه (FK) ═══
    equipment_group = models.ForeignKey(
        'EquipmentGroup', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='equipments',
        verbose_name="گروه اصلی")
    equipment_subgroup = models.ForeignKey(
        'EquipmentSubGroup', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='equipments',
        verbose_name="زیرگروه / واحد")

    production_group = models.ForeignKey(
        'ProductionGroup', on_delete=models.SET_NULL,
        null=True, blank=True, related_name="catalog_equipments",
        verbose_name="گروه تولیدی",
        help_text="از محل استفاده یا آخرین کالیبراسیون قابل بروزرسانی است")
    last_calibration = models.CharField(max_length=20, blank=True, verbose_name="تاریخ کنترل قبلی")
    next_calibration = models.CharField(max_length=20, blank=True, verbose_name="تاریخ کنترل بعدی")
    SCOPE_IO_CHOICES = [
        ('I', 'داخلی'),
        ('O', 'برون‌سپاری'),
    ]
    scope_io = models.CharField(max_length=5, choices=SCOPE_IO_CHOICES,
                                 blank=True, default='I',
                                 verbose_name="نوع خدمات")
    status = models.CharField(max_length=20, blank=True, verbose_name="وضعیت")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = "تجهیز (کاتالوگ)"
        verbose_name_plural = "۶. کاتالوگ تجهیزات"

    def __str__(self):
        return f"{self.code} — {self.name}"


class MPERule(models.Model):
    """قانون حد مجاز خطا (MPE Rule)"""
    FORMULA_CHOICES = [
        ('absolute', 'مطلق (عدد ثابت): C'),
        ('percent_reading', 'درصد قرائت: a% × R'),
        ('percent_range', 'درصد فول اسکیل: a% × FS'),
        ('percent_reading_plus_digit', 'درصد قرائت + رقم: a%R + c×d'),
        ('percent_range_plus_digit', 'درصد فول اسکیل + رقم: a%FS + c×d'),
        ('mixed', 'ترکیبی: a%R + b%FS + c×d'),
        ('custom', 'فرمول سفارشی (دستی)'),
    ]

    # ─── هویت ───
    title = models.CharField(max_length=200, verbose_name="عنوان قانون")
    description = models.CharField(max_length=300, blank=True, verbose_name="توضیح کوتاه")

    # ─── اعمال ───
    equipment_name_code = models.CharField(
        max_length=20, blank=True,
        verbose_name="نوع تجهیز (کد)",
        help_text="مثال: VC، OM، CLM — خالی بذار برای همه")
    parameter = models.CharField(max_length=50, blank=True, verbose_name="پارامتر")
    unit = models.CharField(max_length=30, blank=True, verbose_name="واحد")

    # ─── بازه‌ی رنج ───
    range_min = models.FloatField(null=True, blank=True, verbose_name="از رنج")
    range_max = models.FloatField(null=True, blank=True, verbose_name="تا رنج")

    # ─── فرمول ───
    formula_type = models.CharField(
        max_length=40, choices=FORMULA_CHOICES, default='absolute',
        verbose_name="نوع فرمول")
    coef_a = models.FloatField(
        null=True, blank=True, verbose_name="ضریب a (%)",
        help_text="برای درصد (مثلاً 0.5)")
    coef_b = models.FloatField(
        null=True, blank=True, verbose_name="ضریب b (%)",
        help_text="برای درصد فول اسکیل در فرمول ترکیبی")
    coef_c = models.FloatField(
        null=True, blank=True, verbose_name="ضریب c (تعداد رقم)",
        help_text="برای فرمول‌های + رقم (مثلاً 2)")
    absolute_value = models.FloatField(
        null=True, blank=True, verbose_name="مقدار ثابت (C)",
        help_text="برای فرمول مطلق")
    custom_formula = models.CharField(
        max_length=300, blank=True, verbose_name="فرمول سفارشی",
        help_text="مثال: 0.5%R + 2d + 0.1%FS")

    # ─── استاندارد ───
    standard = models.CharField(max_length=200, blank=True, verbose_name="استاندارد")
    source_clause = models.CharField(max_length=200, blank=True, verbose_name="بند / جدول")

    # ─── وضعیت ───
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['equipment_name_code', 'range_min', 'title']
        verbose_name = "قانون حد مجاز (MPE)"
        verbose_name_plural = "۱۲. قوانین حد مجاز (MPE)"

    def __str__(self):
        return self.title

    @property
    def formula_display(self):
        """نمایش خوانای فرمول"""
        t = self.formula_type
        a = self.coef_a or 0
        b = self.coef_b or 0
        c = self.coef_c or 0
        C = self.absolute_value or 0

        if t == 'absolute':
            return f'± {C}'
        elif t == 'percent_reading':
            return f'± {a}% × R'
        elif t == 'percent_range':
            return f'± {a}% × FS'
        elif t == 'percent_reading_plus_digit':
            return f'± ({a}% × R) + ({c} × d)'
        elif t == 'percent_range_plus_digit':
            return f'± ({a}% × FS) + ({c} × d)'
        elif t == 'mixed':
            parts = []
            if a: parts.append(f'{a}% × R')
            if b: parts.append(f'{b}% × FS')
            if c: parts.append(f'{c} × d')
            return '± ' + ' + '.join(parts) if parts else '—'
        elif t == 'custom':
            return f'± {self.custom_formula or "—"}'
        return '—'

    def compute_mpe(self, R, FS=None, digit=None):
        """محاسبه MPE برای یک مقدار قرائت"""
        t = self.formula_type
        a = self.coef_a or 0
        b = self.coef_b or 0
        c = self.coef_c or 0
        C = self.absolute_value or 0
        d = digit or 0

        try:
            if t == 'absolute':
                return C
            elif t == 'percent_reading':
                return (a / 100) * abs(R)
            elif t == 'percent_range':
                return (a / 100) * (FS or 0)
            elif t == 'percent_reading_plus_digit':
                return (a / 100) * abs(R) + c * d
            elif t == 'percent_range_plus_digit':
                return (a / 100) * (FS or 0) + c * d
            elif t == 'mixed':
                return (a / 100) * abs(R) + (b / 100) * (FS or 0) + c * d
            elif t == 'custom':
                return None  # محاسبه‌ی دستی
        except (TypeError, ValueError, ZeroDivisionError):
            return None
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'formula_type': self.formula_type,
            'formula_display': self.formula_display,
            'coef_a': self.coef_a,
            'coef_b': self.coef_b,
            'coef_c': self.coef_c,
            'absolute_value': self.absolute_value,
            'range_min': self.range_min,
            'range_max': self.range_max,
            'unit': self.unit,
            'custom_formula': self.custom_formula,
        }


class EquipmentCategory(models.Model):
    """دسته‌بندی تجهیزات — گروه‌بندی کدهای مشابه"""
    name = models.CharField(max_length=150, unique=True, verbose_name="نام دسته")
    description = models.CharField(max_length=300, blank=True, verbose_name="توضیحات")
    code_prefixes = models.CharField(
        max_length=500, blank=True,
        verbose_name="کدهای عضو",
        help_text="با کاما جدا کن. مثال: VC,IDC,CM"
    )
    importance_factor = models.FloatField(
        default=1.0, verbose_name="ضریب اهمیت دسته",
        help_text="اگه خالی باشه، از میانگین کدهای عضو استفاده می‌شه")
    override_factor = models.BooleanField(
        default=False, verbose_name="ضریب دستی (نادیده گرفتن میانگین)")
    icon = models.CharField(
        max_length=10, blank=True, default='📦', verbose_name="آیکن")
    display_order = models.IntegerField(default=100, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "دسته تجهیز"
        verbose_name_plural = "۱۴. دسته‌بندی تجهیزات"

    def __str__(self):
        return self.name

    @property
    def prefix_list(self):
        if not self.code_prefixes:
            return []
        return [c.strip().upper() for c in self.code_prefixes.split(',') if c.strip()]

    @property
    def member_count(self):
        """تعداد تجهیزات این دسته در کاتالوگ"""
        from .models_calib import CalibrationEquipment
        from django.db.models import Q
        prefixes = self.prefix_list
        if not prefixes:
            return 0
        q = Q()
        for p in prefixes:
            q |= Q(code__istartswith=p + '-')
        return CalibrationEquipment.objects.filter(q).count()

    def get_factor(self):
        """ضریب نهایی"""
        if self.override_factor or self.importance_factor:
            return self.importance_factor
        # میانگین از اعضا
        prefixes = self.prefix_list
        if not prefixes:
            return 1.0
        from .models_calib import EquipmentNameCode
        factors = list(EquipmentNameCode.objects.filter(
            code__in=prefixes
        ).values_list('importance_factor', flat=True))
        if factors:
            return round(sum(factors) / len(factors), 2)
        return 1.0


# ═══════════════════════════════════════════════════════════════════
# محاسبه دوره کالیبراسیون — مطابق FORM / BANK در اکسل
# ═══════════════════════════════════════════════════════════════════

# ۱۱ معیار ثابت مطابق روش اجرایی
RISK_CRITERIA = [
    {'order': 1,  'name': 'پیشنهاد و توصیه کارخانه سازنده (دفترچه راهنما)',       'weight': 8,  'is_reversed': False},
    {'order': 2,  'name': 'شدت استفاده (مدت زمان و فرکانس استفاده)',              'weight': 9,  'is_reversed': False},
    {'order': 3,  'name': 'شرایط محیطی (دما، رطوبت، ارتعاش و غیره)',              'weight': 10, 'is_reversed': False},
    {'order': 4,  'name': 'صحت مورد نظر در اندازه‌گیری (دقت، عدم قطعیت)',        'weight': 9,  'is_reversed': False},
    {'order': 5,  'name': 'نوع دستگاه (مرجع، کاری، ماموریتی)',                   'weight': 8,  'is_reversed': False},
    {'order': 6,  'name': 'روند سوابق کالیبراسیون (Drift)',                       'weight': 10, 'is_reversed': False},
    {'order': 7,  'name': 'سوابق تعمیرات (وجود تعمیرات قبلی)',                    'weight': 7,  'is_reversed': False},
    {'order': 8,  'name': 'تمایل به فرسودگی (انحراف تدریجی)',                    'weight': 10, 'is_reversed': False},
    {'order': 9,  'name': 'نتایج بازرسی‌های میان دوره‌ای',                        'weight': 8,  'is_reversed': False},
    {'order': 10, 'name': 'هزینه کالیبراسیون (هزینه در برابر ریسک)',             'weight': 6,  'is_reversed': True},
    {'order': 11, 'name': 'سایر موارد (الزامات قانونی و ریسک‌های خاص)',          'weight': 5,  'is_reversed': False},
]

RISK_LEVEL_CHOICES = [
    ('high', 'بالا'),
    ('medium_high', 'متوسط بالا'),
    ('medium_low', 'متوسط کم'),
    ('low', 'کم'),
]

RISK_LEVEL_LABEL = dict(RISK_LEVEL_CHOICES)


def score_for_risk(risk_code, weight, is_reversed=False):
    """محاسبه امتیاز یک معیار مطابق فرمول اکسل"""
    base_map = {'high': 6, 'medium_high': 18, 'medium_low': 24, 'low': 36}
    base = base_map.get(risk_code)
    if base is None:
        return 0.0
    if is_reversed:
        base = 42 - base  # 6↔36, 18↔24
    return round(base * weight / 10.0, 1)


def overall_risk_from_total(total):
    """تبدیل جمع امتیاز به سطح ریسک + دوره پیشنهادی (ماه)"""
    if total is None or total <= 0:
        return None, None, None
    if total <= 100:
        return 'critical', 'ریسک شدید', 6
    if total <= 140:
        return 'high', 'ریسک بالا', 12
    if total <= 180:
        return 'medium_high', 'ریسک متوسط رو به بالا', 18
    if total <= 220:
        return 'medium', 'ریسک متوسط', 24
    if total <= 260:
        return 'medium_low', 'ریسک متوسط رو به پائین', 30
    if total <= 300:
        return 'low', 'ریسک کم', 36
    return 'very_low', 'ریسک خیلی کم', 48


class IntervalBank(models.Model):
    """معادل شیت BANK — ارزیابی ریسک دوره کالیبراسیون"""
    # هویت تجهیز
    equipment_name = models.CharField(max_length=200, db_index=True, verbose_name="نام تجهیز")
    equipment_code = models.CharField(max_length=100, db_index=True, verbose_name="کد تجهیز")
    serial_no = models.CharField(max_length=100, blank=True, verbose_name="شماره سریال")
    location = models.CharField(max_length=200, blank=True, verbose_name="محل استفاده")

    # تاریخ‌ها
    first_setting_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ اولین تنظیم")
    purchase_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ خرید")
    first_calibration_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ اولین کالیبراسیون")

    # نتیجه نهایی
    determined_interval = models.IntegerField(null=True, blank=True, verbose_name="دوره تعیین‌شده (ماه)")

    # ۵ دوره — هر دوره: {calibration_date, risk_levels{1..11}, scores{1..11}, total, overall_risk, risk_label, suggested_interval}
    periods = models.JSONField(default=list, blank=True, verbose_name="دوره‌ها")

    # منبع (برای Import)
    source_file = models.CharField(max_length=100, blank=True)
    source_sheet = models.CharField(max_length=50, blank=True)
    source_row = models.IntegerField(null=True, blank=True)

    last_cal_date_sort = models.IntegerField(
        null=True, blank=True, db_index=True,
        verbose_name="تاریخ آخرین کالیبراسیون (مرتب‌سازی)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_cal_date_sort', 'equipment_code']
        verbose_name = "ارزیابی دوره کالیبراسیون"
        verbose_name_plural = "۱۶. بانک ارزیابی دوره کالیبراسیون"
        indexes = [
            models.Index(fields=['equipment_code', 'location']),
        ]

    def __str__(self):
        return f"{self.equipment_code} — {self.equipment_name}"

    @property
    def periods_count(self):
        return len([p for p in (self.periods or []) if p])

    @property
    def last_calibration_date(self):
        for p in reversed(self.periods or []):
            if p and p.get('calibration_date'):
                return p['calibration_date']
        return self.first_calibration_date

    def _compute_sort_date(self):
        """تبدیل تاریخ آخرین کالیبراسیون به عدد برای مرتب‌سازی"""
        d = self.last_calibration_date
        if not d:
            return None
        digits = ''.join(ch for ch in str(d) if ch.isdigit())
        if len(digits) >= 8:
            try:
                return int(digits[:8])
            except (ValueError, TypeError):
                pass
        return None

    def save(self, *args, **kwargs):
        self.last_cal_date_sort = self._compute_sort_date()
        super().save(*args, **kwargs)

    def compute(self, risk_levels_by_period):
        """
        risk_levels_by_period: dict {1..5: dict{1..11: risk_code}}
        خروجی: periods (list) آماده‌ی ذخیره
        """
        periods = []
        for p_idx in range(1, 6):
            rl = risk_levels_by_period.get(p_idx, {})
            if not rl or not any(rl.values()):
                continue
            scores = {}
            total = 0.0
            for crit in RISK_CRITERIA:
                c_order = crit['order']
                risk = rl.get(c_order, '')
                sc = score_for_risk(risk, crit['weight'], crit['is_reversed']) if risk else 0.0
                scores[str(c_order)] = sc
                total += sc
            total = round(total, 1)
            _, risk_label, suggested = overall_risk_from_total(total)
            periods.append({
                'calibration_date': rl.get('calibration_date', ''),
                'risk_levels': {str(k): v for k, v in rl.items() if k != 'calibration_date'},
                'scores': scores,
                'total': total,
                'overall_risk': risk_label,
                'suggested_interval': suggested,
            })
        return periods


class RiskCriterion(models.Model):
    """معیارهای ریسک (برای ویرایش وزن‌ها) — به صورت پیش‌فرض از RISK_CRITERIA پر می‌شود"""
    order = models.IntegerField(unique=True)
    name = models.CharField(max_length=300)
    weight = models.IntegerField(default=10)
    is_reversed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']
        verbose_name = "معیار ریسک"
        verbose_name_plural = "۱۷. معیارهای ریسک"

    def __str__(self):
        return f"{self.order}. {self.name} (w={self.weight})"


# ═══════════════════════════════════════════════════════════════════
# سیستم تعرفه + پیش‌فاکتور + گزارش درآمد
# ═══════════════════════════════════════════════════════════════════

class PricingSection(models.Model):
    """بخش‌های تعرفه — ۱۴ بخش مطابق فایل تعرفه خدمات"""
    code = models.CharField(max_length=10, unique=True, verbose_name="کد بخش")
    title = models.CharField(max_length=300, verbose_name="عنوان بخش")
    order = models.IntegerField(default=0, verbose_name="ترتیب")
    short_name = models.CharField(max_length=100, blank=True, verbose_name="نام کوتاه")

    # ستون‌های اضافی داینامیک
    extra_col1_label = models.CharField(max_length=100, blank=True, verbose_name="ستون اضافی ۱")
    extra_col2_label = models.CharField(max_length=100, blank=True, verbose_name="ستون اضافی ۲")
    extra_col3_label = models.CharField(max_length=100, blank=True, verbose_name="ستون اضافی ۳")
    extra_col4_label = models.CharField(max_length=100, blank=True, verbose_name="ستون اضافی ۴")

    # لینک به دسته‌بندی تجهیزات
    category = models.ForeignKey(
        'EquipmentCategory', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pricing_sections',
        verbose_name="دسته‌بندی مرتبط")

    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'code']
        verbose_name = "بخش تعرفه"
        verbose_name_plural = "۱۸. بخش‌های تعرفه"

    def __str__(self):
        return f"{self.code}- {self.title}"

    @property
    def items_count(self):
        return self.items.count()

    @property
    def full_label(self):
        return f"{self.code}- {self.title}"


class PricingItem(models.Model):
    """ردیف تعرفه — یک ابزار + گستره + قیمت"""
    section = models.ForeignKey(
        PricingSection, on_delete=models.CASCADE,
        related_name='items', verbose_name="بخش")

    row_no = models.IntegerField(default=1, verbose_name="ردیف")

    name = models.CharField(max_length=300, verbose_name="نام ابزار")
    range_text = models.CharField(max_length=100, blank=True, verbose_name="گستره اندازه‌گیری")

    price = models.BigIntegerField(default=0, verbose_name="قیمت واحد (ریال)")

    # ستون‌های اضافی (مقدار)
    extra_val1 = models.BigIntegerField(null=True, blank=True, verbose_name="مقدار ستون ۱")
    extra_val2 = models.BigIntegerField(null=True, blank=True, verbose_name="مقدار ستون ۲")
    extra_val3 = models.BigIntegerField(null=True, blank=True, verbose_name="مقدار ستون ۳")
    extra_val4 = models.BigIntegerField(null=True, blank=True, verbose_name="مقدار ستون ۴")

    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    # لینک به دسته‌بندی
    category = models.ForeignKey(
        'EquipmentCategory', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pricing_items',
        verbose_name="دسته‌بندی")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['section__order', 'row_no']
        verbose_name = "ردیف تعرفه"
        verbose_name_plural = "۱۹. ردیف‌های تعرفه"

    def __str__(self):
        return f"{self.section.code}-{self.row_no}: {self.name} [{self.range_text}] = {self.price:,}"

    @property
    def price_toman(self):
        return self.price // 10

    @property
    def price_display(self):
        return f"{self.price:,} ریال"


class Invoice(models.Model):
    """پیش‌فاکتور"""
    STATUS_CHOICES = [
        ('draft', 'پیش‌نویس'),
        ('sent', 'ارسال شده'),
        ('accepted', 'تایید شده'),
        ('rejected', 'رد شده'),
        ('invoiced', 'فاکتور شده'),
    ]

    number = models.CharField(max_length=30, unique=True, db_index=True, verbose_name="شماره")
    customer_name = models.CharField(max_length=300, verbose_name="نام مشتری/واحد")
    customer_contact = models.CharField(max_length=300, blank=True, verbose_name="اطلاعات تماس")
    customer_address = models.TextField(blank=True, verbose_name="آدرس")

    issue_date = models.CharField(max_length=20, verbose_name="تاریخ صدور")
    valid_until = models.CharField(max_length=20, blank=True, verbose_name="معتبر تا")

    subtotal = models.BigIntegerField(default=0, verbose_name="جمع کل (ریال)")
    discount = models.BigIntegerField(default=0, verbose_name="تخفیف (ریال)")
    tax_percent = models.IntegerField(default=0, verbose_name="درصد مالیات")
    tax_amount = models.BigIntegerField(default=0, verbose_name="مبلغ مالیات (ریال)")
    total = models.BigIntegerField(default=0, verbose_name="مبلغ نهایی (ریال)")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="وضعیت")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    created_by = models.ForeignKey(
        'auth.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_invoices')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "پیش‌فاکتور"
        verbose_name_plural = "۲۰. پیش‌فاکتورها"

    def __str__(self):
        return f"{self.number} — {self.customer_name}"

    @property
    def total_toman(self):
        return self.total // 10

    def recompute_totals(self):
        self.subtotal = sum(line.line_total for line in self.lines.all())
        self.tax_amount = (self.subtotal - self.discount) * self.tax_percent // 100
        self.total = self.subtotal - self.discount + self.tax_amount
        self.save(update_fields=['subtotal', 'tax_amount', 'total'])


class InvoiceLine(models.Model):
    """خط پیش‌فاکتور"""
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE,
        related_name='lines', verbose_name="پیش‌فاکتور")

    pricing_item = models.ForeignKey(
        PricingItem, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoice_lines',
        verbose_name="ردیف تعرفه")

    # Snapshot (چون ممکنه تعرفه تغییر کنه)
    description = models.CharField(max_length=500, verbose_name="شرح")
    range_text = models.CharField(max_length=100, blank=True, verbose_name="گستره")
    quantity = models.IntegerField(default=1, verbose_name="تعداد")
    unit_price = models.BigIntegerField(default=0, verbose_name="قیمت واحد (ریال)")
    line_total = models.BigIntegerField(default=0, verbose_name="جمع ردیف (ریال)")
    notes = models.CharField(max_length=300, blank=True, verbose_name="ملاحظات")

    order = models.IntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "خط پیش‌فاکتور"
        verbose_name_plural = "خطوط پیش‌فاکتور"

    def __str__(self):
        return f"{self.description} × {self.quantity}"

    def save(self, *args, **kwargs):
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)



class CalibrationReference(models.Model):
    """تجهیزات مرجع استفاده‌شده در یک کالیبراسیون (چندتایی)"""
    calibration = models.ForeignKey(
        CalibrationRegistry, on_delete=models.CASCADE,
        related_name='references', verbose_name="کالیبراسیون")
    reference_equipment = models.ForeignKey(
        'ReferenceEquipment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='used_in',
        verbose_name="تجهیز مرجع")
    reference_code_snapshot = models.CharField(max_length=100, blank=True, verbose_name="کد مرجع")
    reference_name_snapshot = models.CharField(max_length=200, blank=True, verbose_name="نام مرجع")
    certificate_no = models.CharField(max_length=100, blank=True, verbose_name="شماره گواهینامه")
    certificate_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ گواهینامه")
    notes = models.CharField(max_length=200, blank=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
        verbose_name = "تجهیز مرجع کالیبراسیون"
        verbose_name_plural = "تجهیزات مرجع کالیبراسیون"

    def __str__(self):
        return f"{self.reference_code_snapshot or self.reference_equipment_id} → {self.calibration_id}"

class OutsourcedCalibration(models.Model):
    """کالیبراسیون برون‌سپاری شده"""
    STATUS_CHOICES = [
        ('pending', 'در انتظار'),
        ('sent', 'ارسال شده'),
        ('received', 'دریافت شده'),
        ('approved', 'تایید شده'),
        ('rejected', 'رد شده'),
    ]

    equipment = models.ForeignKey(
        'CalibrationEquipment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='outsourced',
        verbose_name="تجهیز")
    equipment_code = models.CharField(max_length=100, db_index=True, verbose_name="کد تجهیز")
    equipment_name = models.CharField(max_length=200, blank=True, verbose_name="نام تجهیز")

    calibration_lab = models.CharField(max_length=200, verbose_name="آزمایشگاه کالیبره‌کننده")
    lab_accreditation = models.CharField(max_length=200, blank=True, verbose_name="اعتباربخشی آزمایشگاه")

    date_sent = models.CharField(max_length=20, blank=True, verbose_name="تاریخ ارسال")
    calibration_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ کالیبراسیون")
    next_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ کالیبراسیون بعدی")

    certificate_no = models.CharField(max_length=100, blank=True, verbose_name="شماره گواهینامه")
    certificate_file = models.FileField(upload_to='outsourced_certs/', blank=True, null=True, verbose_name="فایل گواهینامه")
    certificate_extra_file = models.FileField(upload_to='outsourced_certs/', blank=True, null=True, verbose_name="فایل ضمیمه")

    scope = models.TextField(blank=True, verbose_name="دامنه کالیبراسیون")
    uncertainty = models.CharField(max_length=200, blank=True, verbose_name="عدم قطعیت")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='outsourced_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']
        verbose_name = "کالیبراسیون برون‌سپاری"
        verbose_name_plural = "کالیبراسیون‌های برون‌سپاری"

    def __str__(self):
        return "{} - {} ({})".format(self.equipment_code, self.calibration_lab, self.get_status_display())

class OutsourcedCertificateFile(models.Model):
    """فایل‌های گواهینامه برون‌سپاری (چندتایی)"""
    outsourced = models.ForeignKey(
        OutsourcedCalibration, on_delete=models.CASCADE,
        related_name='certificate_files', verbose_name="برون‌سپاری")
    file = models.FileField(upload_to='outsourced_certs/', verbose_name="فایل")
    title = models.CharField(max_length=200, blank=True, verbose_name="عنوان")
    page_order = models.IntegerField(default=0, verbose_name="ترتیب صفحه")
    is_archived = models.BooleanField(default=False, verbose_name="بایگانی شده")
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان بایگانی")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['page_order', 'id']
        verbose_name = "فایل گواهینامه برون‌سپاری"
        verbose_name_plural = "فایل‌های گواهینامه برون‌سپاری"

    def __str__(self):
        return "{} - {}".format(self.outsourced_id, self.title or self.file.name)

# ═══════════════════════════════════════════════════════════
# گروه‌ها و زیرگروه‌های تجهیزات (مدیریت مستقل)
# ═══════════════════════════════════════════════════════════

class EquipmentGroup(models.Model):
    """گروه اصلی تجهیزات (مثل: ساخت تجهیزات، ماشین و مونتاژ، متالورژی)"""
    name = models.CharField(max_length=150, unique=True, verbose_name="نام گروه")
    code = models.CharField(max_length=30, blank=True, verbose_name="کد گروه")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = "گروه تجهیزات"
        verbose_name_plural = "گروه‌های تجهیزات"

    def __str__(self):
        return self.name


class EquipmentSubGroup(models.Model):
    """زیرگروه / واحد (مثل: مخازن، کارگاه ماشین، آهنگری)"""
    group = models.ForeignKey(
        EquipmentGroup, on_delete=models.CASCADE,
        related_name='subgroups', verbose_name="گروه اصلی")
    name = models.CharField(max_length=200, verbose_name="نام زیرگروه")
    code = models.CharField(max_length=30, blank=True, verbose_name="کد")
    order = models.IntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['group__order', 'order', 'name']
        unique_together = [('group', 'name')]
        verbose_name = "زیرگروه / واحد"
        verbose_name_plural = "زیرگروه‌ها / واحدها"

    def __str__(self):
        return '{} → {}'.format(self.group.name, self.name)

# ═══════════════════════════════════════════════════════════
# تنظیمات اعلان کالیبراسیون
# ═══════════════════════════════════════════════════════════

class CalibrationAlertSettings(models.Model):
    """تنظیمات اعلان موعد کالیبراسیون (Singleton)"""
    is_active = models.BooleanField(
        default=True, verbose_name="فعال بودن اعلان‌ها",
        help_text="اگر غیرفعال باشه، هیچ اعلان خودکاری ساخته نمی‌شه.")

    include_calibration_section = models.BooleanField(
        default=True, verbose_name="ارسال به همه اعضای آزمایشگاه کالیبراسیون",
        help_text="اگه فعال باشه، همه کارشناسان و سرپرستان آزمایشگاه کالیبراسیون اعلان می‌گیرن.")

    include_superuser = models.BooleanField(
        default=True, verbose_name="ارسال به مدیر سیستم (Superuser)")

    recipients = models.ManyToManyField(
        'auth.User', blank=True, related_name='calibration_alerts',
        verbose_name="کاربران اضافی (اختیاری)",
        help_text="کاربرانی که مستقل از نقش/بخش، اعلان دریافت می‌کنن.")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات اعلان کالیبراسیون"
        verbose_name_plural = "تنظیمات اعلان کالیبراسیون"

    def __str__(self):
        return "تنظیمات اعلان کالیبراسیون"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
