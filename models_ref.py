# -*- coding: utf-8 -*-
"""
مدل‌های تجهیزات مرجع کالیبراسیون
"""
from django.db import models
from django.contrib.auth.models import User


class ReferenceEquipment(models.Model):
    """تجهیز مرجع کالیبراسیون"""

    SCOPE_CHOICES = [
        ('dimensional', 'ابعادی'),
        ('welding', 'جوش و کنترل دما'),
        ('both', 'هر دو'),
        ('other', 'سایر'),
    ]

    STATUS_CHOICES = [
        ('active', 'فعال'),
        ('inactive', 'غیرفعال'),
        ('scrapped', 'اسقاط'),
    ]

    # ─── هویت تجهیز ───
    name = models.CharField(max_length=200, verbose_name="نام تجهیز مرجع")
    code = models.CharField(max_length=100, unique=True, db_index=True,
                            verbose_name="کد شناسایی")
    serial_no = models.CharField(max_length=100, blank=True, verbose_name="شماره سریال")
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name="سازنده / برند")
    model_name = models.CharField(max_length=200, blank=True, verbose_name="مدل")
    asset_no = models.CharField(max_length=100, blank=True, verbose_name="شماره اموال")

    # ─── مشخصات فنی ───
    range_text = models.CharField(max_length=100, blank=True, verbose_name="رنج اندازه‌گیری")
    accuracy = models.CharField(max_length=100, blank=True, verbose_name="دقت")
    unit = models.CharField(max_length=30, blank=True, verbose_name="واحد")

    # ─── دامنه کاربرد ───
    scope = models.CharField(max_length=30, choices=SCOPE_CHOICES,
                             default='dimensional', verbose_name="دامنه کاربرد")

    # ─── وضعیت ───
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='active', verbose_name="وضعیت")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    # ─── محل نگهداری ───
    storage_location = models.CharField(max_length=200, blank=True,
                                         verbose_name="محل نگهداری")

    # ─── یادداشت ───
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # ─── تاریخ ───
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name='created_references',
                                    verbose_name="ایجادکننده")

    class Meta:
        ordering = ['code']
        verbose_name = "تجهیز مرجع"
        verbose_name_plural = "۷. تجهیزات مرجع"

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def current_certificate(self):
        """گواهی جاری (جدیدترین فعال)"""
        return self.certificates.filter(is_current=True).first()

    @property
    def certificate_count(self):
        return self.certificates.count()


class ReferenceCertificate(models.Model):
    """گواهی کالیبراسیون یک تجهیز مرجع (تاریخچه)"""

    STATUS_CHOICES = [
        ('current', 'جاری'),
        ('expired', 'منقضی'),
        ('archived', 'بایگانی'),
    ]

    reference = models.ForeignKey(ReferenceEquipment, on_delete=models.CASCADE,
                                   related_name='certificates',
                                   verbose_name="تجهیز مرجع")

    # ─── اطلاعات گواهی ───
    certificate_no = models.CharField(max_length=100, verbose_name="شماره گواهینامه")
    calibration_date = models.CharField(max_length=20, verbose_name="تاریخ کالیبراسیون")
    expiry_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ انقضاء")
    next_due_date = models.CharField(max_length=20, blank=True, verbose_name="تاریخ سررسید بعدی")

    calibrated_by = models.CharField(max_length=200, blank=True,
                                      verbose_name="شرکت/آزمایشگاه کالیبره‌کننده")

    # ─── نتایج ───
    uncertainty = models.CharField(max_length=100, blank=True,
                                    verbose_name="عدم‌قطعیت (U)")
    coverage_factor = models.FloatField(null=True, blank=True, verbose_name="ضریب پوشش (k)")

    # ─── فایل گواهی ───
    certificate_file = models.FileField(upload_to='reference_certificates/%Y/%m/',
                                         blank=True, null=True,
                                         verbose_name="فایل گواهی (PDF/تصویر)")

    # ─── وضعیت ───
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='current', verbose_name="وضعیت")
    is_current = models.BooleanField(default=True, verbose_name="گواهی جاری؟")

    # ─── یادداشت ───
    notes = models.TextField(blank=True, verbose_name="ملاحظات")

    # ─── تاریخ ───
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    blank=True, related_name='created_certificates',
                                    verbose_name="ایجادکننده")

    class Meta:
        ordering = ['-is_current', '-id']
        verbose_name = "گواهی تجهیز مرجع"
        verbose_name_plural = "۸. گواهی‌های تجهیزات مرجع"

    # ═══ هشدار اعتبار ═══
    @property
    def days_until_expiry(self):
        """تعداد روزهای باقی‌مانده تا انقضا (منفی = منقضی)"""
        import jdatetime
        target = (self.next_due_date or self.expiry_date or '').strip()
        if not target:
            return None
        try:
            parts = target.replace('-', '/').split('/')
            if len(parts) < 3:
                return None
            target_date = jdatetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
            today = jdatetime.date.today()
            return (target_date - today).days
        except (ValueError, TypeError):
            return None

    @property
    def expiry_status(self):
        """وضعیت اعتبار: valid / soon / urgent / critical / expired / unknown"""
        d = self.days_until_expiry
        if d is None:
            return 'unknown'
        if d < 0:
            return 'expired'
        if d < 7:
            return 'critical'
        if d < 30:
            return 'urgent'
        if d < 90:
            return 'soon'
        return 'valid'

    @property
    def expiry_label(self):
        d = self.days_until_expiry
        s = self.expiry_status
        if s == 'expired':
            return '⛔ منقضی ({} روز پیش)'.format(abs(d))
        if s == 'critical':
            return '🔴 بحرانی ({} روز مونده)'.format(d)
        if s == 'urgent':
            return '🟠 فوری ({} روز مونده)'.format(d)
        if s == 'soon':
            return '🟡 نزدیک انقضا ({} روز)'.format(d)
        if s == 'valid':
            return '✅ معتبر ({} روز)'.format(d)
        return '—'

    @property
    def expiry_color(self):
        colors = {
            'valid': '#16a34a',
            'soon': '#d97706',
            'urgent': '#ea580c',
            'critical': '#dc2626',
            'expired': '#991b1b',
            'unknown': '#94a3b8',
        }
        return colors.get(self.expiry_status, '#94a3b8')

    @property
    def expiry_bg(self):
        bgs = {
            'valid': '#dcfce7',
            'soon': '#fef3c7',
            'urgent': '#fed7aa',
            'critical': '#fee2e2',
            'expired': '#fecaca',
            'unknown': '#f1f5f9',
        }
        return bgs.get(self.expiry_status, '#f1f5f9')

    def __str__(self):
        return f"{self.reference.code} / {self.certificate_no}"

    def save(self, *args, **kwargs):
        # وقتی این گواهی جاری شد، بقیه رو آرشیو کن
        if self.is_current and self.reference_id:
            ReferenceCertificate.objects.filter(
                reference_id=self.reference_id, is_current=True
            ).exclude(pk=self.pk).update(is_current=False, status='archived')
        super().save(*args, **kwargs)


class ReferenceCertificateFile(models.Model):
    """فایل‌های پیوست گواهی (چند صفحه)"""
    certificate = models.ForeignKey(
        ReferenceCertificate, on_delete=models.CASCADE,
        related_name='files', verbose_name="گواهی"
    )
    file = models.FileField(
        upload_to='reference_certificates/%Y/%m/',
        verbose_name="فایل"
    )
    title = models.CharField(max_length=200, blank=True, verbose_name="عنوان فایل")
    page_order = models.IntegerField(default=1, verbose_name="ترتیب صفحه")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['page_order', 'id']
        verbose_name = "فایل گواهی"
        verbose_name_plural = "۹. فایل‌های گواهی"

    def __str__(self):
        return f"{self.certificate.certificate_no} — {self.title or self.file.name}"

    @property
    def is_image(self):
        name = (self.file.name or '').lower()
        return name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.tif', '.tiff'))

    @property
    def is_pdf(self):
        return (self.file.name or '').lower().endswith('.pdf')

