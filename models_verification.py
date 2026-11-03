from django.db import models
from django.conf import settings


class CalibrationAcceptanceRule(models.Model):
    MPE_TYPE_CHOICES = [
        ('abs', 'مطلق'),
        ('percent', 'درصد'),
        ('ppm', 'ppm'),
    ]

    equipment_code = models.CharField(max_length=100, db_index=True)
    equipment_name = models.CharField(max_length=255, blank=True)
    category = models.CharField(max_length=120, blank=True)
    parameter = models.CharField(max_length=120, blank=True)
    unit = models.CharField(max_length=50, blank=True)
    measurement_range = models.CharField(max_length=120, blank=True)
    nominal_value = models.FloatField(null=True, blank=True)
    mpe = models.FloatField(help_text="حد مجاز خطا (MPE)")
    mpe_type = models.CharField(max_length=20, choices=MPE_TYPE_CHOICES, default='abs')
    target_uncertainty = models.FloatField(null=True, blank=True)
    standard = models.CharField(max_length=120, blank=True)
    revision = models.CharField(max_length=50, blank=True)
    applies_from = models.DateField(null=True, blank=True)
    applies_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "قاعده حدود مجاز"
        verbose_name_plural = "بانک حدود مجاز کالیبراسیون"
        indexes = [models.Index(fields=['equipment_code', 'is_active'])]

    def __str__(self):
        return f"{self.equipment_code} | {self.parameter or '-'} | MPE={self.mpe}"


class CalibrationVerification(models.Model):
    METHOD_SIMPLE = 'simple'
    METHOD_ILAC_UNC = 'ilac_uncertainty'
    METHOD_ILAC_SIMPLE = 'ilac_simple'
    METHOD_ILAC_GUARD = 'ilac_guard_band'
    METHOD_PROTECTIVE = 'protective'
    METHOD_ISO98_4 = 'iso_98_4'
    METHOD_TARGET_U = 'target_uncertainty'
    METHOD_LENIENT = 'lenient'

    METHOD_CHOICES = [
        (METHOD_SIMPLE, 'ساده (بدون عدم قطعیت)'),
        (METHOD_ILAC_UNC, 'ILAC-G8:2019 — مبتنی بر عدم قطعیت (|E|±U)'),
        (METHOD_ILAC_SIMPLE, 'ILAC-G8:09/2019 — پذیرش ساده (ریسک مشترک)'),
        (METHOD_ILAC_GUARD, 'ILAC-G8:09/2019 — گارد باند (ضریب f از MPE)'),
        (METHOD_PROTECTIVE, 'پذیرش محافظ — حد قبولی = MPE − k·U'),
        (METHOD_ISO98_4, 'ISO Guide 98-4 / JCGM 106 — احتمال انطباق'),
        (METHOD_TARGET_U, 'هدف عدم قطعیت'),
        (METHOD_LENIENT, 'پذیرش سهل‌گیرانه (|E| ≤ MPE + U)'),
    ]

    DECISION_CHOICES = [
        ('accepted', 'قابل قبول'),
        ('conditional', 'مشروط'),
        ('rejected', 'مردود'),
    ]

    report_number = models.CharField(max_length=100, unique=True)
    evaluation_date = models.DateField()
    operator = models.CharField(max_length=120, blank=True)
    asset_serial = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=120, blank=True)
    customer = models.CharField(max_length=120, blank=True)

    equipment_code = models.CharField(max_length=100, db_index=True)
    equipment_name = models.CharField(max_length=255, blank=True)
    reference_standard = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=120, blank=True)
    measurement_range = models.CharField(max_length=120, blank=True)
    mpe = models.FloatField(null=True, blank=True)

    method = models.CharField(max_length=40, choices=METHOD_CHOICES, default=METHOD_SIMPLE)
    guard_band_factor = models.FloatField(default=1.0, help_text="ضریب گارد باند f")
    coverage_factor_k = models.FloatField(default=2.0)

    threshold_accepted = models.FloatField(default=95.0)
    threshold_conditional = models.FloatField(default=75.0)

    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, blank=True)
    min_tur = models.FloatField(null=True, blank=True)

    notes = models.TextField(blank=True)
    limitations = models.TextField(blank=True)
    corrective_actions = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    technical_analysis = models.TextField(blank=True)

    equipment_deactivated = models.BooleanField(default=False)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    reactivated_at = models.DateTimeField(null=True, blank=True)

    outsourced_ref = models.CharField(max_length=100, blank=True)

    certificate_number = models.CharField(max_length=120, blank=True)
    calibration_date = models.DateField(null=True, blank=True)
    doc_code = models.CharField(max_length=50, blank=True, default='F192049')
    doc_version = models.CharField(max_length=20, blank=True, default='1')
    calibration_lab = models.CharField(max_length=255, blank=True)

    MPE_CALC_CHOICES = [
        ('abs', 'مقدار ثابت مطلق'),
        ('percent_reading', 'درصدی از قرائت'),
        ('percent_fs', 'درصدی از فول اسکیل (FS)'),
        ('formula', 'فرمول: a% × قرائت + b'),
        ('manual', 'ورود دستی برای هر نقطه'),
    ]
    mpe_calc_type = models.CharField(max_length=30, choices=MPE_CALC_CHOICES, default='abs')
    mpe_b = models.FloatField(default=0.0, help_text='عرض ثابت فرمول (b)')
    full_scale = models.FloatField(null=True, blank=True, help_text='مقدار فول اسکیل')

    checklist_answers = models.JSONField(default=list, blank=True,
        help_text='پاسخ بندهای بازرسی: [{item, yes, no, note}]')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='calibration_verifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-evaluation_date', '-id']
        indexes = [
            models.Index(fields=['equipment_code', '-evaluation_date']),
            models.Index(fields=['decision']),
        ]

    def __str__(self):
        return f"{self.report_number} | {self.equipment_code} | {self.get_decision_display()}"


class CalibrationVerificationPoint(models.Model):
    POINT_DECISION_CHOICES = [
        ('accepted', 'قابل قبول'),
        ('conditional', 'مشروط'),
        ('rejected', 'مردود'),
    ]

    verification = models.ForeignKey(
        CalibrationVerification, on_delete=models.CASCADE, related_name='points'
    )
    order = models.PositiveIntegerField(default=1)
    nominal = models.FloatField(null=True, blank=True)
    error_e = models.FloatField(help_text="خطای اندازه‌گیری E")
    abs_e = models.FloatField(help_text="|E|")
    uncertainty_u = models.FloatField(null=True, blank=True, help_text="U با k=2")
    coverage_factor_k = models.FloatField(default=2.0)
    mpe = models.FloatField(null=True, blank=True)
    tur = models.FloatField(null=True, blank=True, help_text="TUR = MPE / U")
    conformance_probability = models.FloatField(null=True, blank=True)
    decision = models.CharField(max_length=20, choices=POINT_DECISION_CHOICES, blank=True)
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"#{self.order} | {self.verification.report_number}"


class CalibrationVerificationEvent(models.Model):
    EVENT_CHOICES = [
        ('created', 'ایجاد'),
        ('decision_changed', 'تغییر تصمیم'),
        ('equipment_deactivated', 'غیرفعال‌سازی تجهیز'),
        ('equipment_reactivated', 'فعال‌سازی مجدد تجهیز'),
        ('note', 'یادداشت'),
    ]

    verification = models.ForeignKey(
        CalibrationVerification, on_delete=models.CASCADE, related_name='events'
    )
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES)
    from_value = models.CharField(max_length=100, blank=True)
    to_value = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.verification.report_number} | {self.get_event_type_display()}"
