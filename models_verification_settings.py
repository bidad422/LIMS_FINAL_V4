from django.db import models


class CalibrationVerificationSettings(models.Model):
    """تنظیمات سراسری فرم تصدیق کالیبراسیون (Singleton)"""
    # هدر
    default_doc_code = models.CharField(max_length=50, default='F192049', verbose_name='کد سند پیش‌فرض')
    default_doc_version = models.CharField(max_length=20, default='1', verbose_name='نسخه پیش‌فرض')
    default_lab_name = models.CharField(max_length=255, blank=True,
                                        verbose_name='نام آزمایشگاه مرجع پیش‌فرض')

    # روش و پارامترها
    default_method = models.CharField(max_length=40, default='simple', verbose_name='روش پیش‌فرض')
    default_k = models.FloatField(default=2.0, verbose_name='ضریب پوشش k پیش‌فرض')
    default_guard_band_factor = models.FloatField(default=1.0, verbose_name='ضریب گارد باند f پیش‌فرض')
    default_threshold_accepted = models.FloatField(default=95.0, verbose_name='آستانه قبول پیش‌فرض (٪)')
    default_threshold_conditional = models.FloatField(default=75.0, verbose_name='آستانه مشروط پیش‌فرض (٪)')

    # MPE
    default_mpe_calc_type = models.CharField(max_length=30, default='abs',
                                             verbose_name='نوع MPE پیش‌فرض',
                                             choices=[
        ('abs', 'مقدار ثابت مطلق'),
        ('percent_reading', 'درصدی از قرائت'),
        ('percent_fs', 'درصدی از فول اسکیل'),
        ('formula', 'فرمول: a% × قرائت + b'),
        ('manual', 'ورود دستی'),
    ])

    # Checklist (JSON ساده: خط‌به‌خط)
    checklist_items = models.TextField(
        blank=True,
        verbose_name='بندهای بازرسی (هر خط، یک بند)',
        help_text='هر بند در یک خط. مثال:\nآیا کالیبراسیون در زمان مقرر انجام گرفته است؟\nآیا آزمایشگاه دارای تایید صلاحیت ISO/IEC 17025 است؟'
    )

    # متن‌های پیش‌فرض
    default_limitations = models.TextField(blank=True, verbose_name='متن پیش‌فرض محدودیت‌ها')
    default_corrective_actions = models.TextField(blank=True, verbose_name='متن پیش‌فرض اقدامات اصلاحی')
    default_notes = models.TextField(blank=True, verbose_name='متن پیش‌فرض یادداشت')

    # شماره گزارش
    report_number_prefix = models.CharField(max_length=20, default='CV', verbose_name='پیشوند شماره گزارش')
    auto_number_from_serial = models.BooleanField(default=True,
        verbose_name='شماره گزارش از سریال', help_text='اگر فعال باشد، شماره گزارش = پیشوند + سریال')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'تنظیمات تصدیق کالیبراسیون'
        verbose_name_plural = 'تنظیمات تصدیق کالیبراسیون'

    def __str__(self):
        return 'تنظیمات تصدیق کالیبراسیون'

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    def checklist_list(self):
        if not self.checklist_items:
            return []
        return [l.strip() for l in self.checklist_items.splitlines() if l.strip()]
