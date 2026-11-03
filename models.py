import math
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import jdatetime
from .conformity import _num

# ==========================================================
# 1. مدیریت واحدها و مشتریان
# ==========================================================
class Department(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name="نام واحد سازمانی / شرکت متقاضی")
    code = models.CharField(max_length=50, blank=True, null=True, verbose_name="کد واحد")
    is_external = models.BooleanField(default=False, verbose_name="مشتری خارج از شرکت است؟")
    contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name="شخص رابط")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="شماره تماس / داخلی")
    email = models.EmailField(blank=True, null=True, verbose_name="ایمیل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        verbose_name = "واحد متقاضی / مشتری"
        verbose_name_plural = "۱. واحدها و مشتریان"

    def __str__(self):
        return self.name


# ==========================================================
# 2. دسته‌بندی و ریزآزمون‌ها
# ==========================================================
class TestCategory(models.Model):
    name = models.CharField(max_length=120, verbose_name="نام دسته اصلی آزمون")
    code = models.CharField(max_length=50, unique=True, verbose_name="کد شناسه (یکتا)")
    standard_code = models.CharField(max_length=150, blank=True, null=True, verbose_name="استاندارد مرجع اصلی")
    icon = models.CharField(max_length=50, default='bi-check2-square', verbose_name="آیکون نمایشی")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال است؟")
    is_default = models.BooleanField(default=False, verbose_name="پیش‌فرض سیستم است؟")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "دسته اصلی آزمون"
        verbose_name_plural = "۲. دسته‌های اصلی آزمون‌ها"

    def __str__(self):
        return self.name


class TestItem(models.Model):
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, related_name='items', verbose_name="دسته آزمون")
    name = models.CharField(max_length=200, verbose_name="عنوان دقیق زیرآزمون / متد / نوع نمونه")
    standard_code = models.CharField(max_length=150, blank=True, null=True, verbose_name="استاندارد اختصاصی")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    is_active = models.BooleanField(default=True, verbose_name="فعال است؟")
    is_default = models.BooleanField(default=False, verbose_name="پیش‌فرض سیستم است؟")

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "زیرآزمون / متد آزمون"
        verbose_name_plural = "۳. زیرآزمون‌ها و متدهای تخصصی"

    def __str__(self):
        return f"{self.category.name} -> {self.name}"


# ==========================================================
# 3. آزمایشگاه‌ها
# ==========================================================
class LabSection(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name="نام بخش / آزمایشگاه")
    code = models.CharField(max_length=50, unique=True, verbose_name="کد شناسه")
    icon = models.CharField(max_length=50, default='bi-box-seam', verbose_name="آیکون")
    is_external = models.BooleanField(default=False, verbose_name="واحد برون‌سپاری است؟")
    allowed_categories = models.ManyToManyField(TestCategory, blank=True, verbose_name="دسته‌های آزمون مجاز")
    allowed_items = models.ManyToManyField(TestItem, blank=True, verbose_name="ریزآزمون‌های تخصصی مجاز")
    is_active = models.BooleanField(default=True, verbose_name="فعال است؟")

    class Meta:
        verbose_name = "آزمایشگاه / برون‌سپاری"
        verbose_name_plural = "۴. آزمایشگاه‌های داخل شرکت و برون‌سپاری"

    def __str__(self):
        return self.name


# ==========================================================
# 4. پروفایل کاربران
# ==========================================================
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('requester',       'متقاضی آزمون'),
        ('reception',       'پذیرش آزمایشگاه'),
        ('lab_operator',    'کارشناس آزمایشگاه'),
        ('lab_supervisor',  'سرپرست آزمایشگاه (مدیر فنی)'),
        ('head_of_lab',     'رئیس آزمایشگاه'),
        ('quality_manager', 'مدیر کیفیت (QMS)'),
        ('outsourcing',     'کارشناس برون‌سپاری'),
        ('admin',           'مدیر سیستم'),
    ]
   

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="کاربر")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="واحد سازمانی پیش‌فرض")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='requester', verbose_name="نقش / سطح دسترسی")
    lab_section = models.ForeignKey(
        LabSection, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='operators', verbose_name="آزمایشگاه تخصصی (برای کارشناس)"
    )
    supervised_labs = models.ManyToManyField(
        LabSection, blank=True, related_name='supervisors',
        verbose_name="آزمایشگاه‌های تحت سرپرستی (برای سرپرست)"
    )
    permissions = models.JSONField(default=dict, blank=True, verbose_name="دسترسی‌های سفارشی")
    extra_categories = models.ManyToManyField(
        TestCategory, blank=True,
        verbose_name="دسته‌های اضافی مجاز"
    )
    personnel_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="کد پرسنلی")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="شماره تماس مستقیم")

    class Meta:
        verbose_name = "پروفایل کاربر"
        verbose_name_plural = "۵. پروفایل‌های کاربران"

    def __str__(self):
        dept_name = self.department.name if self.department else 'بدون واحد'
        return f"{self.user.get_full_name() or self.user.username} - {dept_name} ({self.get_role_display()})"


# ==========================================================
# 5. بانک مواد و فیلدهای داینامیک
# ==========================================================
class MaterialSuggestion(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="گرید یا جنس آلیاژ")
    standard = models.CharField(max_length=100, blank=True, null=True, verbose_name="استاندارد آلیاژ")

    class Meta:
        verbose_name = "بانک جنس و آلیاژ"
        verbose_name_plural = "۶. بانک جنس و آلیاژها"

    def __str__(self):
        return self.name


class DynamicField(models.Model):
    FIELD_TYPE_CHOICES = [
        ('text', 'متن کوتاه'),
        ('number', 'عدد'),
        ('date', 'تاریخ شمسی'),
        ('dropdown', 'لیست کشویی'),
        ('checkbox', 'چک‌باکس'),
        ('textarea', 'متن چندخطی'),
    ]

    label = models.CharField(max_length=150, verbose_name="عنوان فیلد")
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, verbose_name="نوع فیلد")
    options = models.TextField(blank=True, null=True, verbose_name="گزینه‌ها")
    is_required = models.BooleanField(default=False, verbose_name="اجباری است؟")
    display_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال باشد؟")

    class Meta:
        ordering = ['display_order']
        verbose_name = "فیلد دلخواه فرم"
        verbose_name_plural = "۷. فرم‌ساز فیلدهای دلخواه"

    def __str__(self):
        return f"{self.label} ({self.get_field_type_display()})"


# ==========================================================
# 6. درخواست آزمون
# ==========================================================
class TestRequest(models.Model):
    STATUS_CHOICES = [
        ('draft',       'پیش‌نویس'),
        ('submitted',   'ارسال شده به پذیرش'),
        ('received',    'پذیرش شد / در صف ارجاع'),
        ('assigned',    'به آزمایشگاه ارسال شد'),
        ('testing',     'در حال انجام آزمون'),
        ('outsourced',  'ارجاع به برون‌سپاری'),
        ('review',      'در انتظار تایید نهایی رئیس آزمایشگاه'),
        ('completed',   'تکمیل شده و صادر شده'),
        ('returned',    'جهت اصلاح عودت داده شد'),
        ('rejected',    'رد شده نهایی'),
    ]

    URGENCY_CHOICES = [
        ('normal', 'عادی'),
        ('urgent', 'فوری'),
        ('critical', 'خیلی فوری (توقف خط)'),
    ]

    DESTRUCTION_CHOICES = [
        ('allowed', 'تخریب کامل قطعه بلامانع است'),
        ('not_allowed', 'تخریب مجاز نیست (غیرمخرب)'),
        ('partial', 'تخریب موضعی / حداقل ضایعات'),
    ]

    SAMPLE_RETURN_CHOICES = [
        ('return_remaining', 'بازگرداندن باقیمانده'),
        ('return_all', 'بازگرداندن کامل حتی نمونه‌های شکسته'),
        ('dispose', 'ضایعات شود'),
    ]

    TEST_PRESENCE_CHOICES = [
        ('non_witnessed', 'غیرحضوری'),
        ('witnessed', 'حضوری با حضور ناظر'),
    ]

    tracking_code = models.CharField(max_length=60, unique=True, null=True, blank=True, verbose_name="کد رهگیری")

    department = models.ForeignKey(Department, on_delete=models.PROTECT, verbose_name="واحد متقاضی")
    requester = models.ForeignKey(User, on_delete=models.PROTECT, related_name='requests', verbose_name="ثبت‌کننده")

    automation_letter_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره نامه اتوماسیون")
    internal_request_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره درخواست واحد")
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='normal', verbose_name="فوریت")
    urgency_reason = models.CharField(max_length=255, blank=True, null=True, verbose_name="علت فوریت")

    sample_code = models.CharField(max_length=100, verbose_name="شناسه قطعه")
    sample_name = models.CharField(max_length=200, verbose_name="نام قطعه")
    sample_dimensions = models.CharField(max_length=150, verbose_name="ابعاد اولیه")
    order_group = models.CharField(max_length=100, blank=True, null=True, verbose_name="گروه سفارش")
    heat_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره ذوب (Heat No)")
    serial_number = models.CharField(max_length=100, blank=True, db_index=True,
                                   verbose_name="شماره سریال")
    material_grade = models.CharField(max_length=150, verbose_name="جنس / آلیاژ")
    standard_name = models.CharField(max_length=200, verbose_name="استاندارد درخواستی")

    selected_categories = models.ManyToManyField(TestCategory, blank=True, verbose_name="دسته‌های انتخاب شده")
    selected_sub_tests = models.ManyToManyField(TestItem, blank=True, verbose_name="زیرآزمون‌های انتخابی")
    impact_temperature = models.CharField(max_length=50, blank=True, null=True, verbose_name="دمای ضربه (°C)")
    other_tests_description = models.TextField(blank=True, null=True, verbose_name="سایر آزمون‌ها")

    destruction_status = models.CharField(max_length=20, choices=DESTRUCTION_CHOICES, default='allowed', verbose_name="وضعیت تخریب")
    sample_return_status = models.CharField(max_length=20, choices=SAMPLE_RETURN_CHOICES, default='dispose', verbose_name="بازگرداندن نمونه")
    test_presence_type = models.CharField(max_length=20, choices=TEST_PRESENCE_CHOICES, default='non_witnessed', verbose_name="حضور در آزمون")
    witness_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="نام ناظر")
    witness_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="تماس ناظر")

    description = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    conformity_requested = models.BooleanField(default=False, verbose_name="درخواست ارزیابی انطباق")
    conformity_statement = models.TextField(blank=True, null=True, verbose_name="بیانیه ارزیابی انطباق نهایی")
    attachment = models.FileField(upload_to='request_attachments/%Y/%m/', blank=True, null=True, verbose_name="فایل ضمیمه")
    custom_field_values = models.JSONField(default=dict, blank=True, verbose_name="فیلدهای داینامیک")

    needs_machining = models.BooleanField(default=True, verbose_name="نیاز به نمونه‌سازی / ماشین‌کاری دارد؟")
    machining_notes = models.TextField(blank=True, null=True, verbose_name="دستور کار ماشین‌کاری")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted', verbose_name="وضعیت")
    return_reason = models.TextField(blank=True, null=True, verbose_name="دلیل بازگشت / رد")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین بروزرسانی")
    received_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان پذیرش")
    sample_receipt_status = models.CharField(max_length=20, choices=[
        ('accepted', 'پذیرفته شد'), ('conditional', 'پذیرش مشروط'), ('rejected', 'عدم پذیرش')
    ], default='accepted', verbose_name='وضعیت پذیرش نمونه')
    sample_condition_at_receipt = models.TextField(blank=True, null=True, verbose_name='وضعیت نمونه هنگام تحویل')
    sample_storage_location = models.CharField(max_length=150, blank=True, null=True, verbose_name='محل نگهداری نمونه')
    sample_received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_samples', verbose_name='تحویل‌گیرنده نمونه')
    sample_received_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان تحویل نمونه')
    sample_acceptance_comment = models.TextField(blank=True, null=True, verbose_name='توضیحات پذیرش نمونه')

    class Meta:
        permissions = [("can_print_final_report", "Can print final report")]

        ordering = ['-created_at']
        verbose_name = "درخواست آزمون"
        verbose_name_plural = "۸. درخواست‌های آزمون"

    def __str__(self):
        code_str = self.tracking_code if self.tracking_code else f"پیش‌ثبت-{self.id}"
        return f"{code_str} | {self.sample_name} ({self.department.name})"

    @property
    def excel_raw_rows(self):
        """ردیف‌های خام Excel که با این درخواست لینک شده‌اند."""
        return self.raw_rows.all()

    @property
    def excel_raw_count(self):
        return self.raw_rows.count()

    @property
    def has_excel_data(self):
        return self.raw_rows.exists()

    @property
    def created_at_shamsi(self):
        if self.created_at:
            j_date = jdatetime.datetime.fromgregorian(datetime=self.created_at)
            return j_date.strftime('%Y/%m/%d - %H:%M')
        return ""

    @property
    def status_color(self):
        return {
            'draft': 'secondary', 'submitted': 'info', 'received': 'primary',
            'testing': 'warning', 'outsourced': 'dark', 'review': 'info',
            'completed': 'success', 'returned': 'danger', 'rejected': 'danger',
        }.get(self.status, 'secondary')


# ==========================================================
# 7. ارجاع تخصصی
# ==========================================================
class RequestAssignment(models.Model):
    APPROVAL_STATUS_CHOICES = [
        ('pending',            'ارسال شده به آزمایشگاه'),
        ('accepted',           'پذیرفته شده / در حال انجام آزمون'),
        ('submitted',          'نتیجه ثبت شد / در انتظار تایید سرپرست'),
        ('approved',           'تایید سرپرست'),
        ('rejected',           'عودت جهت اصلاح'),
        ('returned_by_head',   'عودت از رئیس آزمایشگاه'),
    ]

    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE, related_name='assignments', verbose_name="درخواست")
    lab_section = models.ForeignKey(LabSection, on_delete=models.CASCADE, verbose_name="آزمایشگاه")
    assigned_items = models.ManyToManyField(TestItem, blank=True, verbose_name="زیرآزمون‌های محول‌شده")
    assigned_categories = models.ManyToManyField(TestCategory, blank=True, verbose_name="دسته‌های محول‌شده")
    custom_other_tests = models.CharField(max_length=255, blank=True, null=True, verbose_name="سایر آزمون‌ها")
    instructions = models.TextField(blank=True, null=True, verbose_name="دستور کار")

    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending',
        verbose_name="وضعیت تایید"
    )
    supervisor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervised_assignments', verbose_name="سرپرست تاییدکننده"
    )
    supervisor_approved_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان تایید سرپرست")
    supervisor_comment = models.TextField(blank=True, null=True, verbose_name="نظر سرپرست")

    report_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره گزارش اختصاصی")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ارجاع")

    class Meta:
        verbose_name = "ارجاع تخصصی به آزمایشگاه"
        verbose_name_plural = "۸. ارجاعات آزمایشگاه‌ها"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.request.tracking_code} -> {self.lab_section.name}"

    @property
    def status_color(self):
        return {
            'pending': 'secondary',
            'submitted': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'returned_by_head': 'warning',
        }.get(self.approval_status, 'secondary')


# ==========================================================
# ثابت: ۲۱ عنصر ARL 3460
# ==========================================================
CHEMICAL_ELEMENTS_21 = [
    'C', 'Si', 'Mn', 'P', 'S', 'Cr', 'Ni', 'Mo', 'Cu', 'Al',
    'V', 'Ti', 'Nb', 'Co', 'W', 'Pb', 'Sn', 'As', 'B', 'Zr', 'N',
]


# ==========================================================
# 8. نتایج آزمون‌ها
# ==========================================================

class TensileTestResult(models.Model):
    PROBE_SHAPE_CHOICES = [
        ('round',        'گرد (استوانه / دمبلی)'),
        ('tube',         'لوله (Tube)'),
        ('flat',         'تخت (ورق / تسمه)'),
        ('rebar',        'میلگرد آجدار'),
        ('wire',         'سیم و مفتول'),
        ('rope',         'سیم بکسل'),
        ('profile',      'پروفیل / مقطع نامنظم'),
        ('full_section', 'مقطع کامل صنعتی (Full Section)'),
    ]
    INPUT_MODE_CHOICES = [
        ('stress', 'ورود مستقیم تنش (MPa)'),
        ('force',  'ورود نیرو (kN)'),
    ]
    YIELD_TYPE_CHOICES = [
        ('ReH',   'ReH — تنش تسلیم بالا'),
        ('ReL',   'ReL — تنش تسلیم پایین'),
        ('Rp0.2', 'Rp0.2 — تنش تسلیم ۰.۲٪'),
        ('Rt0.5', 'Rt0.5 — تنش تسلیم ۰.۵٪'),
    ]

    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='tensile_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱', verbose_name="برچسب نمونه")
    sample_index = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="اپراتور")

    probe_shape = models.CharField(max_length=20, choices=PROBE_SHAPE_CHOICES, default='round', verbose_name="شکل مقطع")
    input_mode = models.CharField(max_length=10, choices=INPUT_MODE_CHOICES, default='stress', verbose_name="حالت ورودی")
    yield_strength_type = models.CharField(max_length=10, choices=YIELD_TYPE_CHOICES, default='ReH', verbose_name="نوع تنش تسلیم")

    diameter_d0 = models.FloatField(blank=True, null=True, verbose_name="قطر اولیه d0 (mm)")
    outer_diameter = models.FloatField(blank=True, null=True, verbose_name="قطر خارجی (mm)")
    inner_diameter = models.FloatField(blank=True, null=True, verbose_name="قطر داخلی (mm)")
    wall_thickness = models.FloatField(blank=True, null=True, verbose_name="ضخامت جداره (mm)")
    width_w0 = models.FloatField(blank=True, null=True, verbose_name="عرض اولیه w0 (mm)")
    thickness_t0 = models.FloatField(blank=True, null=True, verbose_name="ضخامت اولیه t0 (mm)")
    gauge_length_l0 = models.FloatField(default=50.0, verbose_name="طول اولیه گیج L0 (mm)")

    input_yield_strength = models.FloatField(blank=True, null=True, verbose_name="تنش تسلیم ورودی (MPa)")
    input_tensile_strength = models.FloatField(blank=True, null=True, verbose_name="استحکام کششی ورودی (MPa)")

    yield_force_fy = models.FloatField(blank=True, null=True, verbose_name="نیروی تسلیم Fy (kN)")
    ultimate_force_fm = models.FloatField(blank=True, null=True, verbose_name="نیروی ماکزیمم Fm (kN)")

    final_gauge_length_lu = models.FloatField(default=50.0, verbose_name="طول نهایی Lu (mm)")
    final_diameter_du = models.FloatField(blank=True, null=True, verbose_name="قطر نهایی du (mm)")
    final_width_wu = models.FloatField(blank=True, null=True, verbose_name="عرض نهایی wu (mm)")
    final_thickness_tu = models.FloatField(blank=True, null=True, verbose_name="ضخامت نهایی tu (mm)")

    input_elongation_a = models.FloatField(blank=True, null=True, verbose_name="ازدیاد طول دستی A (%)")
    input_reduction_z = models.FloatField(blank=True, null=True, verbose_name="کاهش سطح دستی Z (%)")

    area_s0 = models.FloatField(blank=True, null=True, verbose_name="مساحت اولیه S0 (mm²)")
    yield_strength_re = models.FloatField(blank=True, null=True, verbose_name="تنش تسلیم Re (MPa)")
    tensile_strength_rm = models.FloatField(blank=True, null=True, verbose_name="استحکام کششی Rm (MPa)")
    elongation_a = models.FloatField(blank=True, null=True, verbose_name="ازدیاد طول A (%)")
    reduction_of_area_z = models.FloatField(blank=True, null=True, verbose_name="کاهش سطح Z (%)")
    ratio_rm_re = models.FloatField(blank=True, null=True, verbose_name="نسبت Rm/Re")

    fracture_location = models.CharField(max_length=120, default='داخل طول گیج', verbose_name="محل شکست")
    test_temperature = models.CharField(max_length=30, default='+23 ± 5 °C', verbose_name="دمای آزمون")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات و مشاهدات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد آزمون")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_tensiletestresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه کشش"
        verbose_name_plural = "۱۰. نتایج کشش"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

    def save(self, *args, **kwargs):
        if self.probe_shape in ('round', 'rebar', 'wire') and self.diameter_d0:
            self.area_s0 = math.pi * (self.diameter_d0 ** 2) / 4.0
        elif self.probe_shape == 'rope':
            # سیم بکسل — از قطر مؤثر استفاده می‌کنیم (کاربر در d0 وارد می‌کند)
            if self.diameter_d0:
                self.area_s0 = math.pi * (self.diameter_d0 ** 2) / 4.0
        elif self.probe_shape in ('profile', 'full_section'):
            # کاربر مساحت را مستقیم در فیلد width_w0 وارد می‌کند (به‌عنوان مساحت دستی)
            if self.width_w0:
                self.area_s0 = self.width_w0
        elif self.probe_shape == 'tube':
            od = self.outer_diameter
            id_ = self.inner_diameter
            if not id_ and od and self.wall_thickness:
                id_ = od - 2 * self.wall_thickness
                self.inner_diameter = id_
            if od and id_:
                self.area_s0 = math.pi * (od ** 2 - id_ ** 2) / 4.0
        elif self.probe_shape == 'flat' and self.width_w0 and self.thickness_t0:
            self.area_s0 = self.width_w0 * self.thickness_t0

        if self.area_s0 and self.area_s0 > 0:
            if self.input_mode == 'force':
                if self.yield_force_fy:
                    self.yield_strength_re = round(self.yield_force_fy * 1000.0 / self.area_s0, 1)
                if self.ultimate_force_fm:
                    self.tensile_strength_rm = round(self.ultimate_force_fm * 1000.0 / self.area_s0, 1)
            else:
                if self.input_yield_strength:
                    self.yield_strength_re = round(self.input_yield_strength, 1)
                    self.yield_force_fy = round(self.input_yield_strength * self.area_s0 / 1000.0, 2)
                if self.input_tensile_strength:
                    self.tensile_strength_rm = round(self.input_tensile_strength, 1)
                    self.ultimate_force_fm = round(self.input_tensile_strength * self.area_s0 / 1000.0, 2)

            if self.yield_strength_re and self.tensile_strength_rm and self.yield_strength_re > 0:
                self.ratio_rm_re = round(self.tensile_strength_rm / self.yield_strength_re, 2)

        if self.input_elongation_a is not None:
            self.elongation_a = self.input_elongation_a
        elif self.gauge_length_l0 and self.final_gauge_length_lu and self.gauge_length_l0 > 0:
            self.elongation_a = round(
                (self.final_gauge_length_lu - self.gauge_length_l0) / self.gauge_length_l0 * 100.0, 1
            )

        if self.input_reduction_z is not None:
            self.reduction_of_area_z = self.input_reduction_z
        else:
            area_su = None
            if self.probe_shape in ('round', 'rebar') and self.final_diameter_du:
                area_su = math.pi * (self.final_diameter_du ** 2) / 4.0
            elif self.probe_shape == 'flat' and self.final_width_wu and self.final_thickness_tu:
                area_su = self.final_width_wu * self.final_thickness_tu
            if self.area_s0 and area_su and self.area_s0 > 0:
                self.reduction_of_area_z = round((self.area_s0 - area_su) / self.area_s0 * 100.0, 1)

        super().save(*args, **kwargs)


class ImpactTestResult(models.Model):
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='impact_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱', verbose_name="برچسب")
    sample_index = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="اپراتور")

    test_temperature = models.CharField(max_length=50, default='+20 °C', verbose_name="دمای آزمون")
    notch_type = models.CharField(max_length=80, default='V-Notch 10x10', verbose_name="نوع شیار")
    specimen_status = models.CharField(
        max_length=20,
        choices=[('separated', 'کاملاً جدا شده'), ('not_separated', 'جدا نشده'), ('partial', 'نیمه جدا')],
        default='separated', verbose_name="وضعیت نمونه"
    )

    readings = models.JSONField(default=list, blank=True, verbose_name="خوانش‌های انرژی")

    average_energy = models.FloatField(blank=True, null=True, verbose_name="میانگین انرژی (J)")
    min_energy = models.FloatField(blank=True, null=True, verbose_name="کمینه انرژی (J)")
    max_energy = models.FloatField(blank=True, null=True, verbose_name="بیشینه انرژی (J)")
    separated_count = models.PositiveIntegerField(default=0, verbose_name="تعداد جدا شده‌ها")

    lateral_expansion = models.FloatField(blank=True, null=True, verbose_name="اتساع جانبی (mm)")
    shear_area_percent = models.FloatField(blank=True, null=True, verbose_name="درصد برش (%Shear)")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد آزمون")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_impacttestresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه ضربه"
        verbose_name_plural = "۱۱. نتایج ضربه"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

    def recalc(self):
        vals = [r.get('energy') for r in (self.readings or []) if r.get('energy') is not None]
        if vals:
            self.average_energy = round(sum(vals) / len(vals), 1)
            self.min_energy = round(min(vals), 1)
            self.max_energy = round(max(vals), 1)
        else:
            self.average_energy = None
            self.min_energy = None
            self.max_energy = None
        self.separated_count = sum(1 for r in (self.readings or []) if r.get('separated'))

    def save(self, *args, **kwargs):
        self.recalc()
        super().save(*args, **kwargs)


class HardnessTestResult(models.Model):
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='hardness_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱', verbose_name="برچسب")
    sample_index = models.PositiveIntegerField(default=0)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    scale = models.CharField(max_length=50, default='HRC', verbose_name="مقیاس")
    indenter_type = models.CharField(
        max_length=50, blank=True, null=True,
        verbose_name="نوع فرورونده / نیرو"
    )
    location = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="موقعیت سختی‌سنجی"
    )
    readings = models.JSONField(default=list, blank=True, verbose_name="نقاط")
    average_hardness = models.FloatField(blank=True, null=True, verbose_name="میانگین")
    min_hardness = models.FloatField(blank=True, null=True, verbose_name="کمینه")
    max_hardness = models.FloatField(blank=True, null=True, verbose_name="بیشینه")
    converted_hardness_approx = models.CharField(max_length=150, blank=True, null=True, verbose_name="تبدیل تقریبی")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد آزمون")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_hardnesstestresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه سختی"
        verbose_name_plural = "۱۲. نتایج سختی"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

    def recalc(self):
        # readings می‌تواند آرایه‌ی ساده (فرمت قدیم) یا آرایه‌ی آرایه‌ها (فرمت جدید) باشد
        vals = []
        for item in (self.readings or []):
            if isinstance(item, list):
                for v in item:
                    if v is not None and v != '':
                        try:
                            vals.append(float(v))
                        except (TypeError, ValueError):
                            pass
            elif item is not None and item != '':
                try:
                    vals.append(float(item))
                except (TypeError, ValueError):
                    pass
        if vals:
            self.average_hardness = round(sum(vals) / len(vals), 1)
            self.min_hardness = round(min(vals), 1)
            self.max_hardness = round(max(vals), 1)
        else:
            self.average_hardness = None
            self.min_hardness = None
            self.max_hardness = None

    def save(self, *args, **kwargs):
        self.recalc()
        super().save(*args, **kwargs)


class ChemicalAnalysisResult(models.Model):
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='chemical_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱')
    sample_index = models.PositiveIntegerField(default=0)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    method_name = models.CharField(max_length=100, default='کوانتومتری OES (ARL 3460)', verbose_name="روش")
    elements = models.JSONField(default=dict, blank=True, verbose_name="عناصر")
    element_uncertainty = models.JSONField(default=dict, blank=True, verbose_name='عدم قطعیت هر عنصر')
    element_lod = models.JSONField(default=dict, blank=True, verbose_name='LOD هر عنصر')
    element_loq = models.JSONField(default=dict, blank=True, verbose_name='LOQ هر عنصر')
    element_units = models.JSONField(default=dict, blank=True, verbose_name='واحد هر عنصر')
    element_status = models.JSONField(default=dict, blank=True, verbose_name='وضعیت هر عنصر')
    carbon_equivalent = models.FloatField(blank=True, null=True, verbose_name="CE")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد آزمون")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_chemicalanalysisresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه آنالیز شیمیایی"
        verbose_name_plural = "۱۳. نتایج آنالیز شیمیایی"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

    def _g(self, key):
        try:
            return float((self.elements or {}).get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def save(self, *args, **kwargs):
        c = self._g('C'); mn = self._g('Mn'); cr = self._g('Cr'); mo = self._g('Mo')
        ni = self._g('Ni'); cu = self._g('Cu'); v = self._g('V')
        self.carbon_equivalent = round(
            c + (mn / 6.0) + ((cr + mo + v) / 5.0) + ((ni + cu) / 15.0), 3
        )
        super().save(*args, **kwargs)


class BendTestResult(models.Model):

    # MECHANICAL_BEND_FIELDS_V1
    section_shape = models.CharField(max_length=100, blank=True, default='')
    material_group = models.CharField(max_length=100, blank=True, default='')
    bend_method = models.CharField(max_length=150, blank=True, default='')
    mandrel_spec = models.CharField(max_length=150, blank=True, default='')
    defect_limit_text = models.TextField(blank=True, default='')
    specimen_dimensions = models.CharField(max_length=250, blank=True, default='')
    specimen_kind = models.CharField(max_length=100, blank=True, default='')
    defects = models.JSONField(default=list, blank=True)

    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='bend_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱')
    sample_index = models.PositiveIntegerField(default=0)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    mandrel_diameter = models.FloatField(blank=True, null=True, verbose_name="قطر سنبه (mm)")
    bend_angle = models.FloatField(blank=True, null=True, verbose_name="زاویه خمش (°)")
    result_status = models.CharField(max_length=120, blank=True, null=True, verbose_name="نتیجه")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد آزمون")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_bendtestresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه خمش"
        verbose_name_plural = "۱۴. نتایج خمش"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"


class FlatteningTestResult(models.Model):

    # MECHANICAL_FLATTENING_FIELDS_V1
    test_name = models.CharField(max_length=250, blank=True, default='')
    specimen_dimensions = models.CharField(max_length=250, blank=True, default='')
    weld_position = models.CharField(max_length=100, blank=True, default='')
    soundness = models.CharField(max_length=100, blank=True, default='')
    ductility = models.CharField(max_length=100, blank=True, default='')

    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='flattening_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱')
    sample_index = models.PositiveIntegerField(default=0)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    initial_outer_diameter = models.FloatField(blank=True, null=True, verbose_name="قطر خارجی اولیه (mm)")
    initial_wall_thickness = models.FloatField(blank=True, null=True, verbose_name="ضخامت جداره (mm)")
    final_plate_distance = models.FloatField(blank=True, null=True, verbose_name="فاصله نهایی صفحات (mm)")
    flatten_ratio = models.FloatField(blank=True, null=True, verbose_name="نسبت پهن‌شدگی")
    result_status = models.CharField(max_length=120, blank=True, null=True, verbose_name="نتیجه")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد آزمون")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_flatteningtestresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه Flattening"
        verbose_name_plural = "۱۵. نتایج Flattening (پهن‌شدگی لوله)"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

    def save(self, *args, **kwargs):
        if self.initial_outer_diameter and self.final_plate_distance and self.initial_outer_diameter > 0:
            self.flatten_ratio = round(self.final_plate_distance / self.initial_outer_diameter, 3)
        super().save(*args, **kwargs)


class FlaringTestResult(models.Model):

    # MECHANICAL_FLARING_FIELDS_V1
    test_name = models.CharField(max_length=250, blank=True, default='')
    mandrel_angle_spec = models.CharField(max_length=100, blank=True, default='')
    defects = models.JSONField(default=list, blank=True)

    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='flaring_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱')
    sample_index = models.PositiveIntegerField(default=0)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    initial_outer_diameter = models.FloatField(blank=True, null=True, verbose_name="قطر خارجی اولیه (mm)")
    expanded_diameter = models.FloatField(blank=True, null=True, verbose_name="قطر دهانه گسترش‌یافته (mm)")
    expansion_percent = models.FloatField(blank=True, null=True, verbose_name="درصد گسترش")
    result_status = models.CharField(max_length=120, blank=True, null=True, verbose_name="نتیجه")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد آزمون")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_flaringtestresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه Flaring"
        verbose_name_plural = "۱۶. نتایج Flaring (گسترش دهانه لوله)"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

    def save(self, *args, **kwargs):
        if self.initial_outer_diameter and self.expanded_diameter and self.initial_outer_diameter > 0:
            self.expansion_percent = round(
                (self.expanded_diameter - self.initial_outer_diameter) / self.initial_outer_diameter * 100.0, 1
            )
        super().save(*args, **kwargs)


class MetallographyResult(models.Model):
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='metallography_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱')
    sample_index = models.PositiveIntegerField(default=0)
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    microstructure_description = models.TextField(blank=True, null=True, verbose_name="شرح ریزساختار")
    grain_size_astm = models.CharField(max_length=50, blank=True, null=True, verbose_name="اندازه دانه ASTM")
    inclusion_rating = models.CharField(max_length=100, blank=True, null=True, verbose_name="آخال ASTM E45")
    microstructure_image = models.ImageField(upload_to='micro_images/%Y/%m/', blank=True, null=True,
                                             verbose_name="تصویر")

    microhardness_scale = models.CharField(max_length=20, default='HV', verbose_name="مقیاس میکروسختی")
    microhardness_readings = models.JSONField(default=list, blank=True, verbose_name="نقاط میکروسختی")
    microhardness_average = models.FloatField(blank=True, null=True, verbose_name="میانگین میکروسختی")

    overall_conclusion = models.TextField(blank=True, null=True, verbose_name="نتیجه‌گیری")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد آزمون")
    preparation_method = models.CharField(max_length=200, blank=True, null=True, verbose_name='روش آماده‌سازی نمونه')
    etchant = models.CharField(max_length=150, blank=True, null=True, verbose_name='اچنت / محلول اچ')
    magnification = models.CharField(max_length=80, blank=True, null=True, verbose_name='بزرگنمایی')
    microscope_equipment = models.ForeignKey('Equipment', on_delete=models.SET_NULL, null=True, blank=True, related_name='metallography_results', verbose_name='میکروسکوپ')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_metallographyresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه متالوگرافی"
        verbose_name_plural = "۱۷. نتایج متالوگرافی و میکروسختی"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

    def recalc(self):
        vals = [float(v) for v in (self.microhardness_readings or []) if v not in (None, '')]
        self.microhardness_average = round(sum(vals) / len(vals), 1) if vals else None

    def save(self, *args, **kwargs):
        self.recalc()
        super().save(*args, **kwargs)


# ==========================================================
# 9. اعلان‌ها
# ==========================================================
class Notification(models.Model):
    LEVEL_CHOICES = [
        ('info',    'اطلاع'),
        ('success', 'موفقیت'),
        ('warning', 'هشدار'),
        ('danger',  'مهم'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="کاربر")
    title = models.CharField(max_length=200, verbose_name="عنوان")
    message = models.TextField(verbose_name="متن پیام")
    link = models.CharField(max_length=255, blank=True, null=True, verbose_name="لینک مقصد")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='info', verbose_name="سطح")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده؟")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "اعلان"
        verbose_name_plural = "۱۸. اعلان‌ها"

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title} → {self.user.username}"

    @property
    def created_at_shamsi(self):
        j = jdatetime.datetime.fromgregorian(datetime=self.created_at)
        return j.strftime('%Y/%m/%d %H:%M')


# ==========================================================
# 10. تاریخچه
# ==========================================================
class RequestHistory(models.Model):
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE, related_name='history', verbose_name="درخواست")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="اقدام‌کننده")
    from_status = models.CharField(max_length=60, verbose_name="از وضعیت")
    to_status = models.CharField(max_length=60, verbose_name="به وضعیت")
    comment = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان")

    class Meta:
        ordering = ['timestamp']
        verbose_name = "لاگ تغییرات"
        verbose_name_plural = "۱۹. تاریخچه گردش درخواست"

    def __str__(self):
        return f"{self.request_id}: {self.from_status} → {self.to_status}"
# ==========================================================
# 11. بانک استانداردها
# ==========================================================
class Standard(models.Model):
    code = models.CharField(max_length=100, verbose_name="کد استاندارد")
    title = models.CharField(max_length=300, verbose_name="عنوان کامل استاندارد")
    revision = models.CharField(max_length=50, blank=True, null=True, verbose_name="ریویژن")
    year = models.CharField(max_length=10, blank=True, null=True, verbose_name="سال")
    is_active = models.BooleanField(default=True, verbose_name="فعال است؟")
    is_default = models.BooleanField(default=False, verbose_name="پیش‌فرض سیستم")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code', 'year', 'revision', 'id']
        constraints = [models.UniqueConstraint(fields=['code', 'revision', 'year'], name='uniq_standard_revision') ]
        verbose_name = "استاندارد"
        verbose_name_plural = "۲۰. بانک استانداردها"

    def __str__(self):
        parts = [self.code]
        if self.year:
            parts.append(self.year)
        if self.revision:
            parts.append(f"Rev.{self.revision}")
        return " — ".join(parts)


# ==========================================================
# 12. بانک تجهیزات کالیبره‌شدنی
# ==========================================================
class Equipment(models.Model):
    name = models.CharField(max_length=150, verbose_name="نام تجهیز")
    code = models.CharField(max_length=50, blank=True, null=True, verbose_name="کد داخلی")
    asset_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره اموال")
    manufacturer = models.CharField(max_length=100, blank=True, null=True, verbose_name="سازنده")
    model_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="مدل")
    serial_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره سریال")
    measurement_range = models.CharField(max_length=150, blank=True, null=True, verbose_name="بازه اندازه‌گیری")
    resolution = models.CharField(max_length=100, blank=True, null=True, verbose_name="دقت / قدرت تفکیک")
    calibration_interval_months = models.PositiveIntegerField(default=12, verbose_name="دوره کالیبراسیون (ماه)")
    CAL_STATUS_CHOICES = [
        ('in_service', 'در سرویس'), ('due_soon', 'نزدیک به سررسید'),
        ('overdue', 'سررسید گذشته'), ('out_of_service', 'خارج از سرویس'),
        ('not_applicable', 'نامشخص / هنوز کالیبراسیون نشده'),
    ]
    calibration_status = models.CharField(max_length=20, choices=CAL_STATUS_CHOICES, default='not_applicable', verbose_name='وضعیت کالیبراسیون')
    last_calibration_date = models.CharField(max_length=20, blank=True, null=True, verbose_name='آخرین کالیبراسیون')
    next_calibration_date = models.CharField(max_length=20, blank=True, null=True, verbose_name='سررسید بعدی')
    calibration_certificate_no = models.CharField(max_length=100, blank=True, null=True, verbose_name='شماره گواهی کالیبراسیون')
    metrological_traceability = models.CharField(max_length=300, blank=True, null=True, verbose_name='ردیابی مترولوژیکی')
    is_active = models.BooleanField(default=True, verbose_name="فعال است؟")
    is_default = models.BooleanField(default=False, verbose_name="پیش‌فرض سیستم")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = "تجهیز کالیبره‌شدنی"
        verbose_name_plural = "۲۱. بانک تجهیزات کالیبراسیون"

    def __str__(self):
        parts = [self.name]
        if self.model_name:
            parts.append(self.model_name)
        if self.serial_no:
            parts.append(f"S/N: {self.serial_no}")
        return " — ".join(parts)


# ==========================================================
# 13. آزمون اعمال نیرو
# ==========================================================
class ForceTestResult(models.Model):
    TEST_TYPE_CHOICES = [
        ('compression', 'فشار (Compression)'),
        ('tension', 'کشش (Tension)'),
        ('bending', 'خمش (Bending)'),
        ('torsion', 'پیچش (Torsion)'),
        ('proof_load', 'بار اثباتی (Proof Load)'),
        ('other', 'سایر'),
    ]

    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='force_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱', verbose_name="برچسب")
    sample_index = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="اپراتور")

    test_type = models.CharField(max_length=30, choices=TEST_TYPE_CHOICES, default='compression', verbose_name="نوع آزمون")
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد مرجع")
    max_force_kn = models.FloatField(blank=True, null=True, verbose_name="حداکثر نیرو (kN)")
    displacement_mm = models.FloatField(blank=True, null=True, verbose_name="جابجایی (mm)")
    loading_rate = models.CharField(max_length=50, blank=True, null=True, verbose_name="سرعت بارگذاری")
    test_temperature = models.CharField(max_length=30, default='+23 ± 5 °C', verbose_name="دمای آزمون")
    result_status = models.CharField(max_length=150, blank=True, null=True, verbose_name="نتیجه")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_forcetestresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه اعمال نیرو"
        verbose_name_plural = "۲۲. نتایج اعمال نیرو"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"


# ==========================================================
# 14. آزمون خوردگی مرز دانه‌ای (IGC)
# ==========================================================
class CorrosionTestResult(models.Model):
    METHOD_CHOICES = [
        ('microscopic', 'ارزیابی میکروسکوپی'),
        ('weight_loss', 'افت وزن'),
        ('bend', 'خمش پس از خوردگی'),
    ]

    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='corrosion_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱', verbose_name="برچسب")
    sample_index = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="اپراتور")

    test_method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='microscopic', verbose_name="روش آزمون")
    corrosive_medium = models.CharField(max_length=200, blank=True, null=True, verbose_name="محیط خورنده")
    temperature = models.CharField(max_length=50, blank=True, null=True, verbose_name="دمای آزمون")
    duration_hours = models.FloatField(blank=True, null=True, verbose_name="مدت زمان (ساعت)")
    weight_before = models.FloatField(blank=True, null=True, verbose_name="وزن قبل (g)")
    weight_after = models.FloatField(blank=True, null=True, verbose_name="وزن بعد (g)")
    corrosion_rate = models.FloatField(blank=True, null=True, verbose_name="نرخ خوردگی")
    evaluation = models.CharField(max_length=150, blank=True, null=True, verbose_name="ارزیابی نهایی")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name='استاندارد مرجع')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_corrosiontestresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه خوردگی"
        verbose_name_plural = "۲۳. نتایج خوردگی (IGC)"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

    def save(self, *args, **kwargs):
        if self.weight_before and self.weight_after and self.weight_before > 0:
            loss = self.weight_before - self.weight_after
            self.corrosion_rate = round(loss, 4)
        super().save(*args, **kwargs)


# ==========================================================
# 15. نتیجه عمومی آزمون‌های تخصصی (خستگی / NDT / سایر)
# ==========================================================
class GeneralTestResult(models.Model):
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE, related_name='general_results', verbose_name='درخواست')
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='ارجاع ثبت‌کننده نتیجه')
    test_category = models.ForeignKey(TestCategory, on_delete=models.PROTECT, related_name='general_results', verbose_name='دسته آزمون')
    test_item = models.ForeignKey(TestItem, on_delete=models.PROTECT, null=True, blank=True, related_name='general_results', verbose_name='زیرآزمون')
    sample_label = models.CharField(max_length=60, default='نمونه ۱', verbose_name='برچسب نمونه')
    sample_index = models.PositiveIntegerField(default=0, verbose_name='ترتیب')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='اپراتور')
    method_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='روش آزمون')
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name='استاندارد مرجع')
    measured_value = models.FloatField(blank=True, null=True, verbose_name='نتیجه عددی')
    unit = models.CharField(max_length=30, blank=True, null=True, verbose_name='واحد')
    result_status = models.CharField(max_length=200, blank=True, null=True, verbose_name='نتیجه / وضعیت')
    observations = models.JSONField(default=dict, blank=True, verbose_name='مشاهدات')
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='k')
    decision_rule = models.CharField(max_length=30, default='simple', verbose_name='قاعده تصمیم')
    notes = models.TextField(blank=True, null=True, verbose_name='توضیحات')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['test_category__order', 'sample_index', 'id']
        verbose_name = 'نتیجه آزمون تخصصی'
        verbose_name_plural = '۲۵. نتایج آزمون‌های تخصصی'
        constraints = [
            models.UniqueConstraint(fields=['request', 'test_category', 'sample_index'], name='uniq_general_result_sample')
        ]
    def save(self, *args, **kwargs):
        """ذخیره با اعمال قرارداد سامانه: U = k·u.

        - اگر فقط u داده شده → U محاسبه می‌شود.
        - اگر فقط U داده شده → u از U/k بازسازی می‌شود.
        - اگر هر دو داده شده → U مقدار گزارش‌شونده است و u از U/k بازسازی می‌شود
          (همخوان با تابع `_result_uncertainty_defaults` در views.py).
        """
        # اعتبارسنجی و اصلاح k
        k = abs(self.coverage_factor or 2.0)
        if k <= 0:
            k = 2.0
        self.coverage_factor = k

        u = self.standard_uncertainty
        U = self.expanded_uncertainty

        # مقادیر منفی نامعتبرند
        if u is not None and u < 0:
            u = abs(u)
        if U is not None and U < 0:
            U = abs(U)

        if U is None and u is not None:
            # فقط u داریم → U = k·u
            U = u * k
        elif u is None and U is not None:
            # فقط U داریم → u = U/k
            u = U / k
        elif U is not None and u is not None:
            # هر دو داریم → U مقدار گزارش‌شونده است؛ u را از U/k بازسازی می‌کنیم
            u = U / k

        self.standard_uncertainty = u
        self.expanded_uncertainty = U

        super().save(*args, **kwargs)


# ==========================================================
# 15. بانک حدود مجاز کالیبراسیون
# ==========================================================
class CalibrationLimit(models.Model):
    """
    جدول کنترل حدود مجاز کالیبراسیون.
    MPE می‌تواند مطلق، درصد قرائت یا درصد محدوده اندازه‌گیری باشد.
    """
    MPE_TYPE_CHOICES = [
        ('absolute', 'مطلق'),
        ('percent_reading', 'درصد قرائت'),
        ('percent_range', 'درصد محدوده'),
    ]
    DECISION_RULE_CHOICES = [
        ('simple', 'پذیرش ساده بدون Guard Band'),
        ('guard_band', 'پذیرش با Guard Band'),
        ('probability', 'احتمال انطباق (Pc)'),
    ]

    standard = models.ForeignKey(Standard, on_delete=models.PROTECT, null=True, blank=True,
                                 related_name='calibration_limits', verbose_name='استاندارد مرجع')
    instrument_type = models.CharField(max_length=150, verbose_name='نوع تجهیز / کمیت')
    parameter = models.CharField(max_length=100, verbose_name='پارامتر')
    unit = models.CharField(max_length=30, blank=True, null=True, verbose_name='واحد')
    accuracy_class = models.CharField(max_length=50, blank=True, null=True, verbose_name='کلاس دقت')
    range_min = models.FloatField(blank=True, null=True, verbose_name='ابتدای محدوده')
    range_max = models.FloatField(blank=True, null=True, verbose_name='انتهای محدوده')
    mpe_value = models.FloatField(verbose_name='MPE')
    mpe_type = models.CharField(max_length=30, choices=MPE_TYPE_CHOICES, default='absolute', verbose_name='نوع MPE')
    decision_rule = models.CharField(max_length=30, choices=DECISION_RULE_CHOICES, default='simple', verbose_name='قاعده تصمیم')
    guard_band_factor = models.FloatField(default=1.0, verbose_name='ضریب Guard Band نسبت به U')
    minimum_tur = models.FloatField(default=4.0, verbose_name='حداقل TUR توصیه‌شده')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    source_clause = models.CharField(max_length=120, blank=True, null=True, verbose_name='بند / جدول مرجع استاندارد')
    applicability = models.CharField(max_length=300, blank=True, null=True, verbose_name='شرایط کاربرد')
    condition = models.CharField(max_length=300, blank=True, null=True, verbose_name='شرط اعمال حد مجاز')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['instrument_type', 'parameter', 'range_min', 'id']
        verbose_name = 'حد مجاز کالیبراسیون'
        verbose_name_plural = '۲۴. جدول حدود مجاز کالیبراسیون'
        indexes = [
            models.Index(fields=['instrument_type', 'parameter', 'is_active']),
            models.Index(fields=['unit', 'is_active']),
        ]

    def __str__(self):
        std = self.standard.code if self.standard else 'بدون استاندارد'
        return f'{self.instrument_type} | {self.parameter} | {std} | MPE={self.mpe_value}'


# ==========================================================
# 16. بودجه عدم قطعیت کالیبراسیون
# ==========================================================
class CalibrationUncertaintyComponent(models.Model):
    """
    مؤلفه قابل ردیابی بودجه عدم قطعیت.
    value/divisor/sensitivity امکان بازسازی محاسبه را فراهم می‌کند.
    برای Type A می‌توان مشاهدات تکراری را در observations ذخیره کرد.
    """
    TYPE_CHOICES = [('A', 'Type A'), ('B', 'Type B')]
    DISTRIBUTION_CHOICES = [
        ('normal', 'نرمال'), ('rectangular', 'مستطیلی'), ('triangular', 'مثلثی'),
        ('u', 'U شکل'), ('other', 'سایر'),
    ]
    result = models.ForeignKey('CalibrationResult', on_delete=models.CASCADE,
                               related_name='uncertainty_components', verbose_name='نتیجه کالیبراسیون')
    name = models.CharField(max_length=200, verbose_name='منبع عدم قطعیت')
    component_type = models.CharField(max_length=1, choices=TYPE_CHOICES, default='B', verbose_name='نوع')
    distribution = models.CharField(max_length=20, choices=DISTRIBUTION_CHOICES, default='rectangular', verbose_name='توزیع')
    value = models.FloatField(default=0.0, verbose_name='مقدار ورودی / ±a')
    divisor = models.FloatField(default=1.0, verbose_name='Divisor')
    sensitivity = models.FloatField(default=1.0, verbose_name='ضریب حساسیت ci')
    degrees_of_freedom = models.FloatField(blank=True, null=True, verbose_name='درجه آزادی vi')
    observations = models.JSONField(default=list, blank=True, verbose_name='مشاهدات Type A')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد')
    correlation_group = models.CharField(max_length=80, blank=True, null=True, verbose_name='گروه همبستگی')
    correlation_coefficient = models.FloatField(blank=True, null=True, verbose_name='ضریب همبستگی ρ')
    source = models.CharField(max_length=300, blank=True, null=True, verbose_name='منبع')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    standard_uncertainty = models.FloatField(default=0.0, verbose_name='عدم قطعیت استاندارد ui')
    contribution = models.FloatField(default=0.0, verbose_name='سهم ci×ui')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'مؤلفه عدم قطعیت'
        verbose_name_plural = 'بودجه عدم قطعیت'

    def calculate(self):
        import math, statistics
        try:
            sensitivity = float(self.sensitivity if self.sensitivity is not None else 1.0)
            divisor = float(self.divisor if self.divisor is not None else 1.0)
        except (TypeError, ValueError, OverflowError):
            raise ValidationError('مقادیر مؤلفه عدم‌قطعیت نامعتبر است.')
        if not math.isfinite(sensitivity) or not math.isfinite(divisor) or divisor <= 0:
            raise ValidationError('Divisor و Sensitivity باید مقادیر متناهی باشند و Divisor بزرگ‌تر از صفر باشد.')

        ctype = (self.component_type or 'B').strip().upper()
        if ctype not in {'A', 'B'}:
            raise ValidationError('نوع مؤلفه باید A یا B باشد.')

        if ctype == 'A':
            vals = []
            for x in (self.observations or []):
                try:
                    xv = float(x)
                except (TypeError, ValueError, OverflowError):
                    raise ValidationError('یکی از مشاهدات Type A معتبر نیست.')
                if not math.isfinite(xv):
                    raise ValidationError('مشاهدات Type A باید متناهی باشند.')
                vals.append(xv)
            if len(vals) < 2:
                raise ValidationError('برای Type A حداقل دو مشاهده لازم است.')
            self.value = statistics.stdev(vals)
            self.divisor = math.sqrt(len(vals))
            self.degrees_of_freedom = len(vals) - 1
        else:
            try:
                value = float(self.value if self.value is not None else 0.0)
            except (TypeError, ValueError, OverflowError):
                raise ValidationError('Value مؤلفه Type B معتبر نیست.')
            if not math.isfinite(value):
                raise ValidationError('Value مؤلفه Type B باید متناهی باشد.')
            self.value = value

        if self.degrees_of_freedom is not None:
            try:
                df = float(self.degrees_of_freedom)
            except (TypeError, ValueError, OverflowError):
                raise ValidationError('درجه آزادی نامعتبر است.')
            if not math.isfinite(df) or df <= 0:
                raise ValidationError('درجه آزادی باید بزرگ‌تر از صفر باشد.')
            self.degrees_of_freedom = df
        elif ctype == 'B':
            self.degrees_of_freedom = 50.0

        ui = float(self.value) / float(self.divisor)
        self.standard_uncertainty = ui
        self.contribution = abs(sensitivity * ui)
        return ui

    def save(self, *args, **kwargs):
        self.calculate()
        super().save(*args, **kwargs)



# ==========================================================
# پروفایل عدم‌قطعیت آزمون
# ==========================================================
class TestUncertaintyProfile(models.Model):
    """عدم‌قطعیت روش آزمون که می‌تواند برای آزمون‌های روتین بازبینی و دوباره استفاده شود."""
    test_category = models.ForeignKey(TestCategory, on_delete=models.PROTECT, related_name='uncertainty_profiles', verbose_name='دسته آزمون')
    test_item = models.ForeignKey(TestItem, on_delete=models.PROTECT, null=True, blank=True, related_name='uncertainty_profiles', verbose_name='زیرآزمون')
    standard = models.ForeignKey(Standard, on_delete=models.PROTECT, null=True, blank=True, related_name='test_uncertainty_profiles', verbose_name='استاندارد')
    standard_revision = models.CharField(max_length=100, blank=True, null=True, verbose_name='Revision استاندارد')
    method_version = models.CharField(max_length=100, blank=True, null=True, verbose_name='نسخه روش')
    parameter = models.CharField(max_length=100, verbose_name='پارامتر')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد')
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='k')
    confidence_level = models.FloatField(default=95.0, verbose_name='سطح اطمینان (%)')
    uncertainty_budget = models.JSONField(default=list, blank=True, verbose_name='بودجه عدم‌قطعیت')
    source_clause = models.CharField(max_length=200, blank=True, null=True, verbose_name='بند/منبع')
    effective_date = models.CharField(max_length=20, blank=True, null=True, verbose_name='تاریخ اجرا')
    review_date = models.CharField(max_length=20, blank=True, null=True, verbose_name='تاریخ بازنگری')
    is_active = models.BooleanField(default=True, verbose_name='فعال')
    notes = models.TextField(blank=True, null=True, verbose_name='توضیحات')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['test_category__order', 'parameter', '-updated_at']
        verbose_name = 'پروفایل عدم‌قطعیت آزمون'
        verbose_name_plural = 'پروفایل‌های عدم‌قطعیت آزمون'
        indexes = [
            models.Index(fields=['parameter', 'is_active']),
            models.Index(fields=['test_category', 'parameter', 'is_active']),
        ]

    def save(self, *args, **kwargs):
        k = self.coverage_factor
        if k is None:
            k = 2.0
        try:
            k = float(k)
        except (TypeError, ValueError, OverflowError):
            raise ValidationError('ضریب پوشش k نامعتبر است.')
        if not math.isfinite(k) or k <= 0:
            raise ValidationError('ضریب پوشش k باید متناهی و بزرگ‌تر از صفر باشد.')
        self.coverage_factor = k

        if self.standard_uncertainty is not None:
            try:
                u = float(self.standard_uncertainty)
            except (TypeError, ValueError, OverflowError):
                raise ValidationError('عدم‌قطعیت استاندارد نامعتبر است.')
            if not math.isfinite(u) or u < 0:
                raise ValidationError('u باید متناهی و غیرمنفی باشد.')
            self.standard_uncertainty = u
        if self.expanded_uncertainty is not None:
            try:
                U = float(self.expanded_uncertainty)
            except (TypeError, ValueError, OverflowError):
                raise ValidationError('عدم‌قطعیت گسترش‌یافته نامعتبر است.')
            if not math.isfinite(U) or U < 0:
                raise ValidationError('U باید متناهی و غیرمنفی باشد.')
            self.expanded_uncertainty = U

        if self.expanded_uncertainty is None and self.standard_uncertainty is not None:
            self.expanded_uncertainty = self.standard_uncertainty * k
        elif self.expanded_uncertainty is not None:
            self.standard_uncertainty = self.expanded_uncertainty / k

        try:
            conf = float(self.confidence_level)
        except (TypeError, ValueError, OverflowError):
            raise ValidationError('سطح اطمینان نامعتبر است.')
        if not math.isfinite(conf) or not (0 < conf <= 100):
            raise ValidationError('سطح اطمینان باید در بازه 0 تا 100 درصد باشد.')
        self.confidence_level = conf
        super().save(*args, **kwargs)


# ==========================================================
# 17. سابقه تصمیم انطباق
# ==========================================================
class ConformityDecision(models.Model):
    """Snapshot قابل ردیابی از یک تصمیم انطباق؛ برای جلوگیری از تغییر گذشته."""
    STATUS_CHOICES = [('PASS','قبول'), ('FAIL','مردود'), ('NO_DECISION','بدون تصمیم')]
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE, related_name='conformity_decisions', verbose_name='درخواست')
    calibration_result = models.ForeignKey('CalibrationResult', on_delete=models.SET_NULL, null=True, blank=True, related_name='decision_snapshots', verbose_name='نتیجه کالیبراسیون')
    specification = models.ForeignKey('Specification', on_delete=models.SET_NULL, null=True, blank=True, related_name='decision_snapshots', verbose_name='مشخصه')
    parameter = models.CharField(max_length=100, blank=True, null=True, verbose_name='پارامتر')
    result_kind = models.CharField(max_length=60, blank=True, null=True, verbose_name='نوع نتیجه')
    result_id = models.PositiveBigIntegerField(blank=True, null=True, verbose_name='شناسه نتیجه')
    measured_text = models.CharField(max_length=300, blank=True, null=True, verbose_name='نتیجه متنی')
    standard_reference = models.CharField(max_length=200, blank=True, null=True, verbose_name='استاندارد مرجع')
    standard_revision = models.CharField(max_length=100, blank=True, null=True, verbose_name='Revision استاندارد')
    is_current = models.BooleanField(default=True, verbose_name='تصمیم جاری')
    measured_value = models.FloatField(blank=True, null=True, verbose_name='نتیجه')
    lower_limit = models.FloatField(blank=True, null=True, verbose_name='حد پایین')
    upper_limit = models.FloatField(blank=True, null=True, verbose_name='حد بالا')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد')
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='U')
    coverage_factor = models.FloatField(blank=True, null=True, verbose_name='k')
    decision_rule = models.CharField(max_length=30, default='simple', verbose_name='قاعده تصمیم')
    guard_band = models.FloatField(blank=True, null=True, verbose_name='Guard Band')
    probability_of_conformity = models.FloatField(blank=True, null=True, verbose_name='Pc (%)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NO_DECISION', verbose_name='وضعیت')
    message = models.CharField(max_length=500, blank=True, null=True, verbose_name='شرح تصمیم')
    calculation_trace = models.JSONField(default=dict, blank=True, verbose_name='ردپای محاسبات')
    decided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='conformity_decisions_made', verbose_name='تصمیم‌گیر')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['request', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        verbose_name = 'سابقه تصمیم انطباق'
        verbose_name_plural = 'سابقه تصمیم‌های انطباق'

    def __str__(self):
        return f'{self.request.tracking_code or self.request_id} | {self.parameter or "—"} | {self.status}'


# ==========================================================
# 18. کالیبراسیون تجهیزات
# ==========================================================
class CalibrationResult(models.Model):
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='calibration_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱', verbose_name="برچسب")
    sample_index = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="اپراتور")

    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="تجهیز")
    equipment_name_free = models.CharField(max_length=150, blank=True, null=True, verbose_name="نام تجهیز (اگر در لیست نبود)")
    asset_no = models.CharField(max_length=100, blank=True, null=True, verbose_name="شماره اموال")

    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name="استاندارد مرجع")
    calibration_limit = models.ForeignKey(CalibrationLimit, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='results', verbose_name='حد مجاز انتخاب‌شده')
    instrument_type = models.CharField(max_length=150, blank=True, null=True, verbose_name='نوع تجهیز / کمیت')
    parameter = models.CharField(max_length=100, blank=True, null=True, verbose_name='پارامتر کالیبراسیون')
    unit = models.CharField(max_length=30, blank=True, null=True, verbose_name='واحد')
    reference_unit = models.CharField(max_length=30, blank=True, null=True, verbose_name='واحد مرجع')
    reading_unit = models.CharField(max_length=30, blank=True, null=True, verbose_name='واحد قرائت')
    mpe_value = models.FloatField(blank=True, null=True, verbose_name='MPE')
    range_min = models.FloatField(blank=True, null=True, verbose_name='حد پایین محدوده تجهیز')
    range_max = models.FloatField(blank=True, null=True, verbose_name='حد بالای محدوده تجهیز')
    mpe_type = models.CharField(max_length=30, choices=CalibrationLimit.MPE_TYPE_CHOICES, default='absolute', verbose_name='نوع MPE')
    decision_rule = models.CharField(max_length=30, choices=CalibrationLimit.DECISION_RULE_CHOICES, default='simple', verbose_name='قاعده تصمیم')
    guard_band = models.FloatField(blank=True, null=True, verbose_name='Guard Band')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    confidence_level = models.FloatField(default=95.0, verbose_name='سطح اطمینان (%)')
    conformity_probability = models.FloatField(blank=True, null=True, verbose_name='احتمال انطباق Pc (%)')
    uncertainty_confidence = models.FloatField(default=95.0, verbose_name='سطح اطمینان عدم قطعیت (%)')
    effective_degrees_of_freedom = models.FloatField(blank=True, null=True, verbose_name='درجه آزادی مؤثر')
    uncertainty_method = models.CharField(max_length=30, default='budget', verbose_name='روش تعیین عدم قطعیت')
    tur = models.FloatField(blank=True, null=True, verbose_name='TUR')
    decision_summary = models.CharField(max_length=100, blank=True, null=True, verbose_name='تصمیم نهایی')
    calculation_trace = models.JSONField(default=dict, blank=True, verbose_name='جزئیات محاسبات')
    calibration_date = models.CharField(max_length=50, blank=True, null=True, verbose_name="تاریخ کالیبراسیون")
    next_due_date = models.CharField(max_length=50, blank=True, null=True, verbose_name="تاریخ انقضای بعدی")

    max_error_percent = models.FloatField(blank=True, null=True, verbose_name="حداکثر خطا (%)")
    uncertainty = models.CharField(max_length=100, blank=True, null=True, verbose_name="عدم قطعیت")
    result_status = models.CharField(max_length=150, blank=True, null=True, verbose_name="نتیجه")

    # تا ۱۰ نقطه: [{"reference": X, "reading": Y, "error": Z}, ...]
    points = models.JSONField(default=list, blank=True, verbose_name="نقاط کالیبراسیون")

    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_calibrationresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه کالیبراسیون"
        verbose_name_plural = "۲۴. نتایج کالیبراسیون"

    def __str__(self):
        eq = self.equipment.name if self.equipment else (self.equipment_name_free or 'تجهیز نامشخص')
        return f"{self.request.tracking_code or self.request.id} - {eq}"

    def recalc(self):
        """محاسبه سازگار با هسته تصمیم کالیبراسیون؛ جزئیات هر نقطه در JSON حفظ می‌شود."""
        from .calibration import calculate_calibration_points, summarize_calibration
        pts = self.points or []
        result = calculate_calibration_points(
            pts,
            mpe=self.mpe_value,
            mpe_type=self.mpe_type,
            range_min=self.range_min,
            range_max=self.range_max,
            expanded_uncertainty=self.expanded_uncertainty,
            standard_uncertainty=self.standard_uncertainty,
            coverage_factor=self.coverage_factor,
            decision_rule=self.decision_rule or 'simple',
            guard_band=self.guard_band,
            guard_band_factor=(self.calibration_limit.guard_band_factor if self.calibration_limit else 1.0),
            confidence=self.confidence_level,
        )
        self.points = result['points']
        summary = summarize_calibration(result['points'], result['u'], self.decision_rule or 'simple')
        self.max_error_percent = result['max_error_percent']
        self.standard_uncertainty = result['u']
        self.expanded_uncertainty = result['U']
        self.tur = summary.get('tur')
        self.conformity_probability = summary.get('pc')
        self.decision_summary = summary.get('decision')
        self.guard_band = result.get('guard_band')
        self.calculation_trace = {
            'mpe': self.mpe_value,
            'mpe_type': self.mpe_type,
            'range_min': self.range_min,
            'range_max': self.range_max,
            'decision_rule': self.decision_rule,
            'coverage_factor': self.coverage_factor,
            'confidence_level': self.confidence_level,
            'u': result.get('u'),
            'U': result.get('U'),
            'guard_band': result.get('guard_band'),
            'engine_status': result.get('status'),
            'engine_errors': result.get('errors') or [],
            'points': result.get('points') or [],
        }
        if self.decision_summary:
            self.result_status = self.decision_summary

    def save(self, *args, **kwargs):
        self.recalc()
        super().save(*args, **kwargs)


# ==========================================================
# 16. PMI (XRF)
# ==========================================================
PMI_ELEMENTS_10 = ['Cr', 'Mn', 'Ni', 'Mo', 'V', 'Ti', 'Co', 'W', 'Cu', 'Al']


class PMIResult(models.Model):
    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='pmi_results', verbose_name="درخواست")
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="ارجاع ثبت‌کننده نتیجه")
    sample_label = models.CharField(max_length=60, default='نمونه ۱', verbose_name="برچسب")
    sample_index = models.PositiveIntegerField(default=0, verbose_name="ترتیب")
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="اپراتور")

    device_name = models.CharField(max_length=100, default='XRF Portable', verbose_name="دستگاه")
    elements = models.JSONField(default=dict, blank=True, verbose_name="عناصر")
    element_uncertainty = models.JSONField(default=dict, blank=True, verbose_name='عدم قطعیت هر عنصر')
    element_lod = models.JSONField(default=dict, blank=True, verbose_name='LOD هر عنصر')
    element_loq = models.JSONField(default=dict, blank=True, verbose_name='LOQ هر عنصر')
    element_units = models.JSONField(default=dict, blank=True, verbose_name='واحد هر عنصر')
    element_status = models.JSONField(default=dict, blank=True, verbose_name='وضعیت هر عنصر')
    estimated_grade = models.CharField(max_length=100, blank=True, null=True, verbose_name="گرید تخمینی")
    result_status = models.CharField(max_length=150, blank=True, null=True, verbose_name="نتیجه")
    notes = models.TextField(blank=True, null=True, verbose_name="توضیحات")
    standard_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت استاندارد u')
    expanded_uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت گسترش‌یافته U')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['request', 'sample_index'], name='uniq_pmiresult_sample')
        ]
        ordering = ['sample_index', 'id']
        verbose_name = "نتیجه PMI"
        verbose_name_plural = "۲۵. نتایج PMI (XRF)"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.sample_label}"

# ==========================================================
# ثابت‌های دسترسی سفارشی
# ==========================================================
ALL_PERMISSIONS = {
    'can_create_request':   'ثبت درخواست جدید',
    'view_own_requests':    'مشاهده درخواست‌های خودش',
    'view_reception':       'کارتابل پذیرش',
    'can_accept_request':   'صدور کد رهگیری',
    'can_assign_tasks':     'ارجاع به آزمایشگاه‌ها',
    'can_reject_request':   'رد یا عودت درخواست',
    'can_export_excel':     'خروجی اکسل',
    'view_operator':        'کارتابل کارشناس آزمایشگاه',
    'can_enter_results':    'ثبت نتایج آزمون',
    'view_supervisor':      'کارتابل سرپرست آزمایشگاه',
    'can_approve_results':  'تایید نتایج کارشناس',
    'view_final_review':    'کارتابل رئیس آزمایشگاه',
    'can_final_approve':    'تایید نهایی درخواست',
    'can_print_report':     'چاپ / دانلود گزارش نهایی',
    'manage_users':         'مدیریت کاربران',
    'manage_equipment':     'مدیریت تجهیزات کالیبراسیون',
    'manage_standards':     'مدیریت استانداردها',
    'view_all_requests':    'مشاهده همه‌ی درخواست‌ها',
    # ISO/IEC 17025 — QMS
    'view_complaints':      'مشاهده شکایات (ISO 17025 — 7.9)',
    'manage_complaints':    'مدیریت شکایات (ISO 17025 — 7.9)',
    'view_ncr':             'مشاهده کارهای غیرمنطبق (ISO 17025 — 7.10)',
        'manage_ncr':           'مدیریت NC و CAPA (ISO 17025 — 7.10)',
    'view_audits':          'مشاهده ممیزی‌های داخلی (ISO 17025 — 8.8)',
    'manage_audits':        'مدیریت ممیزی‌های داخلی (ISO 17025 — 8.8)',
    'view_reviews':         'مشاهده بازنگری‌های مدیریت (ISO 17025 — 8.9)',
    'manage_reviews':       'مدیریت بازنگری‌های مدیریت (ISO 17025 — 8.9)',
    'view_risks':           'مشاهده ریسک‌ها و فرصت‌ها (ISO 17025 — 8.5)',
    'manage_risks':         'مدیریت ریسک‌ها و فرصت‌ها (ISO 17025 — 8.5)',
    'view_documents':       'مشاهده اسناد کنترل‌شده (ISO 17025 — 8.4)',
        'manage_documents':     'مدیریت اسناد کنترل‌شده (ISO 17025 — 8.4)',
    'view_records':         'مشاهده سوابق و پالیسی‌های نگهداری (ISO 17025 — 8.3)',
        'manage_records':       'مدیریت سوابق و پالیسی‌های نگهداری (ISO 17025 — 8.3)',
    'view_validations':     'مشاهده اعتبارسنجی روش‌ها (ISO 17025 — 7.2)',
        'manage_validations':   'مدیریت اعتبارسنجی روش‌ها (ISO 17025 — 7.2)',
    'view_references':      'مشاهده استانداردهای مرجع (ISO 17025 — 6.5)',
    'manage_references':    'مدیریت استانداردهای مرجع (ISO 17025 — 6.5)',
    # کالیبراسیون
    'view_calibration':     'مشاهده کالیبراسیون',
    'manage_calibration':   'مدیریت کالیبراسیون (ثبت، ویرایش، حذف)',
    'manage_mpe':           'مدیریت قوانین حد مجاز (MPE)',
    'manage_reference_equipment': 'مدیریت تجهیزات مرجع',
    'manage_uncertainty':   'مدیریت عدم قطعیت',
    'manage_intervals':     'مدیریت دوره‌های کالیبراسیون',
    'manage_calibration_categories': 'مدیریت دسته‌بندی تجهیزات',
    'manage_outsourced_calibration': 'مدیریت کالیبراسیون برون‌سپاری',
}

ROLE_DEFAULT_PERMISSIONS = {
    'requester':       ['can_create_request', 'view_own_requests'],
    'reception':       ['view_reception', 'can_accept_request', 'can_assign_tasks',
                        'can_reject_request', 'can_export_excel',
                        'view_complaints', 'view_ncr'],
    'lab_operator':    ['view_operator', 'can_enter_results'],
    'lab_supervisor':  ['view_supervisor', 'can_approve_results',
                        'manage_equipment', 'manage_standards',
                        'view_complaints',
                        'view_ncr',
                        'view_audits',
                        'view_reviews',
                        'view_risks',
                        'view_documents',
                        'view_records',
                        'view_validations',
                        'view_references',
                        # کالیبراسیون
                        'view_calibration', 'manage_calibration',
                        'manage_mpe', 'manage_reference_equipment',
                        'manage_uncertainty', 'manage_intervals',
                        'manage_calibration_categories'],
    'head_of_lab':     ['view_final_review', 'can_final_approve', 'can_print_report',
                        'manage_users', 'manage_equipment', 'manage_standards',
                        'view_all_requests',
                        'view_complaints', 'manage_complaints',
                        'view_ncr', 'manage_ncr',
                        'view_audits', 'manage_audits',
                        'view_reviews', 'manage_reviews',
                        'view_risks', 'manage_risks',
                        'view_documents', 'manage_documents',
                        'view_records', 'manage_records',
                        'view_validations', 'manage_validations',
                        'view_references', 'manage_references',
                        # کالیبراسیون
                        'view_calibration', 'manage_calibration',
                        'manage_mpe', 'manage_reference_equipment',
                        'manage_uncertainty', 'manage_intervals',
                        'manage_calibration_categories',
                        'manage_outsourced_calibration'],
    'quality_manager': ['view_reception', 'view_supervisor', 'view_final_review',
                        'can_print_report', 'manage_standards', 'manage_equipment',
                        'view_all_requests',
                        'view_complaints', 'manage_complaints',
                        'view_ncr', 'manage_ncr',
                        'view_audits', 'manage_audits',
                        'view_reviews', 'manage_reviews',
                        'view_risks', 'manage_risks',
                        'view_documents', 'manage_documents',
                        'view_records', 'manage_records',
                        'view_validations', 'manage_validations',
                        'view_references', 'manage_references',
                        # کالیبراسیون
                        'view_calibration', 'manage_calibration',
                        'manage_mpe', 'manage_reference_equipment',
                        'manage_uncertainty', 'manage_intervals',
                        'manage_calibration_categories',
                        'manage_outsourced_calibration'],
    'outsourcing':     ['view_operator', 'can_enter_results'],
    'admin':           list(ALL_PERMISSIONS.keys()),
}


def get_default_permissions(role):
    """پیش‌فرض دسترسی‌ها بر اساس نقش."""
    return ROLE_DEFAULT_PERMISSIONS.get(role, [])


# ==========================================================
# پیام‌رسانی داخلی
# ==========================================================
class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='sent_messages', verbose_name="فرستنده")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE,
                                  related_name='received_messages', verbose_name="گیرنده")
    subject = models.CharField(max_length=250, blank=True, null=True, verbose_name="موضوع")
    body = models.TextField(verbose_name="متن پیام")
    is_read = models.BooleanField(default=False, verbose_name="خوانده شده؟")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان خواندن")
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                               related_name='replies', verbose_name="پاسخ به")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ارسال")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "پیام"
        verbose_name_plural = "۲۶. پیام‌های داخلی"

    def __str__(self):
        return f"{self.sender.username} → {self.recipient.username}: {self.subject or self.body[:30]}"

    @property
    def created_at_shamsi(self):
        import jdatetime
        j = jdatetime.datetime.fromgregorian(datetime=self.created_at)
        return j.strftime('%Y/%m/%d %H:%M')

    @property
    def preview(self):
        return (self.body or '')[:80]


# قوانین: چه کسی می‌تونه به کی پیام بده
def can_message(sender_profile, recipient_profile):
    """بررسی مجوز ارسال پیام."""
    if not sender_profile or not recipient_profile:
        return False
    if sender_profile.user_id == recipient_profile.user_id:
        return False

    s_role = sender_profile.role
    r_role = recipient_profile.role

    # admin → همه
    if s_role == 'admin':
        return True

    # هیچ‌کس → admin
    if r_role == 'admin':
        return False

    # requester → فقط reception
    if s_role == 'requester':
        return r_role == 'reception'

    # نقش‌های مدیریتی → همه به‌جز admin
    if s_role in ('reception', 'head_of_lab', 'quality_manager'):
        return r_role in ('requester', 'reception', 'lab_operator',
                          'lab_supervisor', 'head_of_lab', 'quality_manager',
                          'outsourcing')

    # lab_supervisor → reception + سایر سرپرست‌ها + کارشناسان + مدیران
    if s_role == 'lab_supervisor':
        return r_role in ('reception', 'lab_supervisor', 'lab_operator',
                          'head_of_lab', 'quality_manager', 'outsourcing')

    # lab_operator → reception + سرپرست + سایر کارشناسان + مدیران
    if s_role == 'lab_operator':
        return r_role in ('reception', 'lab_supervisor', 'lab_operator',
                          'head_of_lab', 'quality_manager', 'outsourcing')

    # outsourcing → مثل کارشناس
    if s_role == 'outsourcing':
        return r_role in ('reception', 'lab_supervisor', 'head_of_lab',
                          'lab_operator', 'quality_manager')

    return False


def allowed_recipients(sender_profile):
    """لیست کاربرانی که این کاربر می‌تونه به‌شون پیام بده.

    بهینه‌شده: فیلتر بر اساس نقش در سطح دیتابیس، سپس چک نهایی.
    """
    if not sender_profile:
        return User.objects.none()

    s_role = sender_profile.role
    base = User.objects.filter(is_active=True).select_related('profile').exclude(id=sender_profile.user_id)

    # ─── admin → همه ───
    if s_role == 'admin':
        return base

    # ─── نگاشت نقش فرستنده به نقش‌های مجاز گیرنده ───
    role_map = {
        'requester':      ['reception'],
        'reception':      ['requester', 'lab_operator', 'lab_supervisor',
                           'head_of_lab', 'outsourcing', 'quality_manager'],
        'head_of_lab':    ['requester', 'reception', 'lab_operator',
                           'lab_supervisor', 'outsourcing', 'quality_manager'],
        'quality_manager':['requester', 'reception', 'lab_operator',
                           'lab_supervisor', 'head_of_lab', 'outsourcing'],
        'lab_supervisor': ['reception', 'lab_supervisor', 'lab_operator',
                           'head_of_lab', 'quality_manager', 'outsourcing'],
        'lab_operator':   ['reception', 'lab_supervisor', 'lab_operator',
                           'head_of_lab', 'quality_manager', 'outsourcing'],
        'outsourcing':    ['reception', 'lab_supervisor', 'head_of_lab',
                           'lab_operator', 'quality_manager'],
    }

    allowed_roles = role_map.get(s_role, [])
    if not allowed_roles:
        return User.objects.none()

    return base.filter(profile__role__in=allowed_roles)

# ==========================================================
# تصاویر نمونه‌ها
# ==========================================================

# ==========================================================
# کنترل‌های تکمیلی ISO/IEC 17025
# ==========================================================
class EquipmentCheck(models.Model):
    CHECK_CHOICES = [
        ('intermediate', 'کنترل بین‌دوره‌ای'), ('zero', 'کنترل صفر'),
        ('function', 'کنترل عملکرد'), ('verification', 'راستی‌آزمایی'), ('other', 'سایر'),
    ]
    RESULT_CHOICES = [('pass', 'قبول'), ('fail', 'مردود'), ('no_decision', 'بدون تصمیم')]
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name='checks', verbose_name='تجهیز')
    check_type = models.CharField(max_length=20, choices=CHECK_CHOICES, default='intermediate', verbose_name='نوع کنترل')
    performed_at = models.DateTimeField(default=timezone.now, verbose_name='زمان کنترل')
    checked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='انجام‌دهنده')
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name='مرجع')
    certificate_no = models.CharField(max_length=100, blank=True, null=True, verbose_name='شماره گواهی')
    reference_value = models.FloatField(blank=True, null=True, verbose_name='مقدار مرجع')
    observed_value = models.FloatField(blank=True, null=True, verbose_name='مقدار مشاهده‌شده')
    error = models.FloatField(blank=True, null=True, verbose_name='خطا')
    uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت')
    mpe = models.FloatField(blank=True, null=True, verbose_name='MPE')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد')
    result_status = models.CharField(max_length=20, choices=RESULT_CHOICES, default='no_decision', verbose_name='نتیجه')
    notes = models.TextField(blank=True, null=True, verbose_name='توضیحات')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at', '-id']
        verbose_name = 'کنترل بین‌دوره‌ای تجهیز'
        verbose_name_plural = 'کنترل‌های بین‌دوره‌ای تجهیزات'


class EnvironmentalConditionLog(models.Model):
    lab_section = models.ForeignKey(LabSection, on_delete=models.PROTECT, related_name='environment_logs', verbose_name='آزمایشگاه')
    recorded_at = models.DateTimeField(default=timezone.now, verbose_name='زمان')
    temperature = models.FloatField(blank=True, null=True, verbose_name='دما °C')
    humidity = models.FloatField(blank=True, null=True, verbose_name='رطوبت نسبی %')
    pressure = models.FloatField(blank=True, null=True, verbose_name='فشار')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد فشار')
    condition_text = models.CharField(max_length=300, blank=True, null=True, verbose_name='سایر شرایط')
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='ثبت‌کننده')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at', '-id']
        verbose_name = 'ثبت شرایط محیطی'
        verbose_name_plural = 'ثبت شرایط محیطی'


class PersonnelCompetency(models.Model):
    STATUS_CHOICES = [('authorized', 'مجاز'), ('conditional', 'مجاز مشروط'), ('suspended', 'معلق')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='competencies', verbose_name='کاربر')
    lab_section = models.ForeignKey(LabSection, on_delete=models.PROTECT, verbose_name='آزمایشگاه')
    test_category = models.ForeignKey(TestCategory, on_delete=models.PROTECT, null=True, blank=True, verbose_name='حوزه فنی')
    test_item = models.ForeignKey(TestItem, on_delete=models.PROTECT, null=True, blank=True, verbose_name='زیرآزمون')
    method_standard = models.CharField(max_length=200, blank=True, null=True, verbose_name='روش/استاندارد')
    competency_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='authorized', verbose_name='وضعیت صلاحیت')
    assessed_at = models.DateField(verbose_name='تاریخ ارزیابی')
    valid_until = models.DateField(blank=True, null=True, verbose_name='اعتبار تا')
    assessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='competency_assessments', verbose_name='ارزیاب')
    evidence_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name='مرجع شواهد')
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-assessed_at', '-id']
        verbose_name = 'صلاحیت پرسنل'
        verbose_name_plural = 'سوابق صلاحیت پرسنل'


class QualityControlRecord(models.Model):
    TYPE_CHOICES = [
        ('crm', 'CRM / ماده مرجع'), ('blank', 'Blank'), ('duplicate', 'Duplicate'),
        ('control', 'نمونه کنترل'), ('reference', 'نمونه مرجع'), ('pt', 'PT/ILC'),
    ]
    STATUS_CHOICES = [('pass', 'قبول'), ('fail', 'مردود'), ('no_decision', 'بدون تصمیم')]
    request = models.ForeignKey(TestRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='qc_records', verbose_name='درخواست')
    test_category = models.ForeignKey(TestCategory, on_delete=models.PROTECT, null=True, blank=True, verbose_name='حوزه آزمون')
    result_kind = models.CharField(max_length=60, blank=True, null=True, verbose_name='نوع نتیجه مرتبط')
    result_id = models.PositiveBigIntegerField(blank=True, null=True, verbose_name='شناسه نتیجه مرتبط')
    qc_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='نوع QC')
    analyte_or_parameter = models.CharField(max_length=100, blank=True, null=True, verbose_name='عنصر/پارامتر')
    target_value = models.FloatField(blank=True, null=True, verbose_name='مقدار هدف')
    measured_value = models.FloatField(blank=True, null=True, verbose_name='مقدار اندازه‌گیری')
    uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم قطعیت')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد')
    acceptance_criteria = models.CharField(max_length=300, blank=True, null=True, verbose_name='معیار پذیرش')
    result_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='no_decision', verbose_name='نتیجه QC')
    standard_ref = models.CharField(max_length=200, blank=True, null=True, verbose_name='استاندارد')
    performed_at = models.DateTimeField(default=timezone.now, verbose_name='زمان انجام')
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='انجام‌دهنده')
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='تجهیز')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-performed_at', '-id']
        verbose_name = 'رکورد کنترل کیفیت'
        verbose_name_plural = 'رکوردهای کنترل کیفیت'


class SampleImage(models.Model):
    STAGE_CHOICES = [
        ('reception',   'پذیرش نمونه'),
        ('preparation', 'نمونه‌سازی / کارگاه'),
        ('testing',     'حین آزمون'),
        ('post_test',   'پس از آزمون'),
        ('other',       'سایر'),
    ]

    request = models.ForeignKey(TestRequest, on_delete=models.CASCADE,
                                related_name='sample_images', verbose_name="درخواست")
    image = models.ImageField(upload_to='sample_images/%Y/%m/', verbose_name="تصویر")
    caption = models.CharField(max_length=250, blank=True, null=True, verbose_name="توضیح تصویر")
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='reception',
                             verbose_name="مرحله")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                    related_name='uploaded_sample_images',
                                    verbose_name="آپلودکننده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان آپلود")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "تصویر نمونه"
        verbose_name_plural = "۲۸. تصاویر نمونه‌ها"

    def __str__(self):
        return f"{self.request.tracking_code or self.request.id} - {self.caption or 'بدون توضیح'}"

    @property
    def created_at_shamsi(self):
        import jdatetime
        j = jdatetime.datetime.fromgregorian(datetime=self.created_at)
        return j.strftime('%Y/%m/%d %H:%M')

    def delete(self, *args, **kwargs):
        # حذف فایل فیزیکی هم
        try:
            if self.image:
                self.image.delete(save=False)
        except Exception:
            pass
        super().delete(*args, **kwargs)


# ==========================================================
# حدود مجاز استاندارد (Specification)
# ==========================================================
SPEC_PARAMETERS = {
    'tensile': [
        ('Re',     'تنش تسلیم (Re)',           'MPa'),
        ('Rm',     'استحکام کششی (Rm)',         'MPa'),
        ('A',      'ازدیاد طول (A)',            '%'),
        ('Z',      'کاهش سطح مقطع (Z)',         '%'),
        ('ratio',  'نسبت Rm/Re',                ''),
    ],
    'impact': [
        ('E_avg',  'میانگین انرژی ضربه',         'J'),
        ('E_min',  'کمینه انرژی ضربه',           'J'),
        ('LE',     'اتساع جانبی (Lateral Exp.)', 'mm'),
        ('Shear',  'درصد سطح برش',              '%'),
    ],
    'hardness': [
        ('HRC',    'سختی راکول C',              'HRC'),
        ('HRB',    'سختی راکول B',              'HRB'),
        ('HB',     'سختی برینل (HB)',           'HB'),
        ('HBW',    'سختی برینل',                'HBW'),
        ('HV',     'سختی ویکرز',                'HV'),
    ],
    'chemical': [
        ('C',      'کربن',                     '%'),
        ('Si',     'سیلیسیم',                  '%'),
        ('Mn',     'منگنز',                    '%'),
        ('P',      'فسفر',                     '%'),
        ('S',      'گوگرد',                    '%'),
        ('Cr',     'کروم',                     '%'),
        ('Ni',     'نیکل',                     '%'),
        ('Mo',     'مولیبدن',                  '%'),
        ('Cu',     'مس',                       '%'),
        ('V',      'وانادیم',                  '%'),
        ('Ti',     'تیتانیم',                  '%'),
        ('Nb',     'نیوبیم',                   '%'),
        ('Co',     'کبالت',                    '%'),
        ('W',      'تنگستن',                   '%'),
        ('Pb',     'سرب',                      '%'),
        ('Sn',     'قلع',                      '%'),
        ('As',     'آرسنیک',                   '%'),
        ('B',      'بور',                      '%'),
        ('Zr',     'زیرکونیم',                 '%'),
        ('N',      'نیتروژن',                  '%'),
        ('Al',     'آلومینیم',                 '%'),
        ('CE',     'کربن معادل (CE)',           '%'),
    ],
    'bend': [
        ('status', 'نتیجه خمش',                 'کیفی'),
    ],
    'flattening': [
        ('ratio', 'نسبت Flattening', ''),
        ('status', 'نتیجه Flattening', 'کیفی'),
    ],
    'flaring': [
        ('expansion', 'درصد گسترش دهانه', '%'),
        ('status', 'نتیجه Flaring', 'کیفی'),
    ],
    'force': [
        ('Fmax', 'حداکثر نیرو', 'kN'),
        ('displacement', 'جابجایی', 'mm'),
        ('status', 'نتیجه اعمال نیرو', 'کیفی'),
    ],
    'metallography': [
        ('microhardness', 'میکروسختی', 'HV/HK'),
        ('grain_size', 'اندازه دانه', 'کیفی/شماره'),
        ('inclusion', 'آخال', 'کیفی/رتبه'),
        ('status', 'نتیجه متالوگرافی', 'کیفی'),
    ],
    'corrosion': [
        ('corrosion_rate', 'نرخ خوردگی', 'مطابق روش'),
        ('status', 'نتیجه خوردگی', 'کیفی'),
    ],
    'pmi': [
        ('status', 'نتیجه PMI', 'کیفی'),
    ],
    'general': [
        ('result', 'نتیجه آزمون تخصصی', ''),
    ],
}


class Specification(models.Model):
    """مشخصه‌ی قبول/رد برای یک پارامتر آزمون."""

    # مرجع
    product_standard = models.CharField(max_length=200,
        verbose_name="استاندارد محصول",
        help_text="مثال: ASTM A615 / ASTM A370 / ISIRI 3132")
    standard_revision = models.CharField(max_length=50, blank=True, null=True,
        verbose_name="نسخه / سال استاندارد",
        help_text="مثال: Rev.22 / 2022")
    standard = models.ForeignKey(Standard, on_delete=models.PROTECT, null=True, blank=True,
        related_name='specifications', verbose_name='رکورد استاندارد در بانک')
    lower_inclusive = models.BooleanField(default=True, verbose_name='حد پایین شامل باشد')
    upper_inclusive = models.BooleanField(default=True, verbose_name='حد بالا شامل باشد')
    decision_rule = models.CharField(max_length=30, choices=[
        ('simple', 'قبول مستقیم'), ('guard_band', 'Guard Band'), ('probability', 'احتمال انطباق')],
        default='simple', verbose_name='قاعده تصمیم')
    guard_band = models.FloatField(blank=True, null=True, verbose_name='Guard Band')
    uncertainty_required = models.BooleanField(default=False, verbose_name='عدم قطعیت در تصمیم الزامی است؟')

    # اعمال
    test_category = models.ForeignKey(TestCategory, on_delete=models.CASCADE,
        related_name='specifications', verbose_name="دسته آزمون")
    material_grade = models.CharField(max_length=150, blank=True, null=True,
        verbose_name="جنس / گرید (خالی = همه)",
        help_text="مثال: A615 Gr.60 / CK45 / ST37 — خالی بذار اگه برای همه‌ست")
    condition = models.CharField(max_length=250, blank=True, null=True,
        verbose_name="شرط اعمال",
        help_text="مثال: قطر ≥ 16mm یا دمای 20-°C یا ضخامت ≤ 10mm")
    condition_parameter = models.CharField(max_length=60, blank=True, null=True, verbose_name="پارامتر شرط")
    condition_min = models.FloatField(blank=True, null=True, verbose_name="حد پایین شرط")
    condition_max = models.FloatField(blank=True, null=True, verbose_name="حد بالای شرط")
    condition_unit = models.CharField(max_length=20, blank=True, null=True, verbose_name="واحد شرط")

    # پارامتر
    parameter = models.CharField(max_length=30, verbose_name="پارامتر",
        help_text="کد پارامتر (Re, Rm, E_avg, ...)")
    unit = models.CharField(max_length=20, blank=True, null=True, verbose_name="واحد")

    # حدود عددی
    min_value = models.FloatField(blank=True, null=True, verbose_name="حد پایین")
    max_value = models.FloatField(blank=True, null=True, verbose_name="حد بالا")
    target_value = models.FloatField(blank=True, null=True, verbose_name="مقدار هدف (اختیاری)")

    # کیفی
    is_qualitative = models.BooleanField(default=False, verbose_name="کیفی است (بدون عدد)")
    accepted_values = models.CharField(max_length=300, blank=True, null=True,
        verbose_name="مقادیر قبول (با کاما جدا کن)",
        help_text="مثال: مورد تایید, قابل قبول")

    # وضعیت
    revision = models.CharField(max_length=20, blank=True, null=True,
        verbose_name="ریویژن داخلی",
        help_text="Rev.01 / Rev.02 — برای پیگیری تغییرات")
    is_active = models.BooleanField(default=True, verbose_name="فعال؟")
    notes = models.TextField(blank=True, null=True, verbose_name="یادداشت / توضیح")

    # متادیتا
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
        related_name='created_specifications', verbose_name="ایجادکننده")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "حد مجاز استاندارد"
        verbose_name_plural = "۲۹. حدود مجاز استانداردها"

    def __str__(self):
        grade = self.material_grade or 'همه'
        return f"{self.product_standard} — {self.test_category.name} — {self.parameter} ({grade})"

    @property
    def range_display(self):
        if self.is_qualitative:
            return f"کیفی: {self.accepted_values or '—'}"
        parts = []
        if self.min_value is not None:
            parts.append(f"≥ {self.min_value}")
        if self.max_value is not None:
            parts.append(f"≤ {self.max_value}")
        if not parts:
            return "—"
        u = f" {self.unit}" if self.unit else ""
        return " و ".join(parts) + u


def check_spec(test_category_code, parameter, value, material_grade='', standard='',
               standard_revision='', uncertainty=None, uncertainty_coverage_factor=None,
               decision_rule_override=None, guard_band_override=None,
               confidence=95.0, condition_value=None, unit='', condition_unit=''):
    """انتخاب و ارزیابی سروری Specification با تطابق دقیق مرجع/Revision و واحد."""
    from .conformity import decide
    from .units import convert as convert_unit

    def _norm_text(v):
        return ' '.join(str(v or '').strip().lower().split())

    def _unit_equal(a, b):
        return _norm_text(a).replace(' ', '') == _norm_text(b).replace(' ', '')

    qs = Specification.objects.filter(
        is_active=True, test_category__code=test_category_code, parameter=parameter
    ).select_related('standard')
    candidates = list(qs)
    if not candidates:
        return 'no_spec', '', None

    # Standard: وقتی ورودی صریح است، تطابق باید دقیق باشد؛ از انتخاب "نزدیک" خودکار جلوگیری می‌شود.
    std_l = _norm_text(standard)
    if std_l:
        exact = [sp for sp in candidates if _norm_text(sp.product_standard) == std_l]
        exact_fk = [sp for sp in candidates if sp.standard and _norm_text(sp.standard.code) == std_l]
        candidates = exact or exact_fk
        if not candidates:
            return 'no_spec', f'Specification برای استاندارد «{standard}» یافت نشد.', None

    # Revision صریح نیز باید دقیقاً منطبق باشد؛ عدم تطابق باعث fallback به Revision دیگر نمی‌شود.
    rev_l = _norm_text(standard_revision)
    if rev_l:
        exact_rev = [sp for sp in candidates if _norm_text(sp.standard_revision) == rev_l]
        exact_fk_rev = [sp for sp in candidates if sp.standard and _norm_text(sp.standard.revision) == rev_l]
        candidates = exact_rev or exact_fk_rev
        if not candidates:
            return 'no_spec', f'Specification با Revision «{standard_revision}» یافت نشد.', None

    # گرید دقیق بر Specification عمومی اولویت دارد.
    mg_l = _norm_text(material_grade)
    if mg_l:
        exact_grade = [sp for sp in candidates if _norm_text(sp.material_grade) == mg_l]
        generic_grade = [sp for sp in candidates if not _norm_text(sp.material_grade)]
        candidates = exact_grade or generic_grade
    else:
        generic_grade = [sp for sp in candidates if not _norm_text(sp.material_grade)]
        if generic_grade:
            candidates = generic_grade

    def condition_ok(sp):
        if sp.condition_min is None and sp.condition_max is None:
            return True
        if condition_value is None:
            return False
        cv = _num(condition_value)
        if cv is None:
            return False
        from_u = condition_unit or ''
        to_u = sp.condition_unit or ''
        if from_u and to_u and not _unit_equal(from_u, to_u):
            try:
                cv = convert_unit(cv, from_u, to_u)
            except (TypeError, ValueError, OverflowError):
                return False
        if sp.condition_min is not None and cv < sp.condition_min:
            return False
        if sp.condition_max is not None and cv > sp.condition_max:
            return False
        return True

    candidates = [sp for sp in candidates if condition_ok(sp)]
    if not candidates:
        return 'no_decision', 'شرط اعمال Specification احراز نشده است.', None
    if len(candidates) > 1:
        return 'no_decision', 'بیش از یک Specification فعال با شرایط یکسان/همپوشان یافت شد؛ انتخاب خودکار مجاز نیست.', None
    spec = candidates[0]

    rule = (decision_rule_override or spec.decision_rule or 'simple').strip().lower()
    gb = guard_band_override if guard_band_override is not None else spec.guard_band

    if spec.is_qualitative:
        accepted = {_norm_text(v) for v in (spec.accepted_values or '').split(',') if _norm_text(v)}
        actual = _norm_text(value)
        ok = actual in accepted
        return ('pass' if ok else 'fail',
                f"{'✅ قابل قبول' if ok else '❌ مردود'} — {spec.range_display}", spec)

    # مقدار نتیجه قبل از تصمیم باید در واحد Specification باشد.
    value_num = _num(value)
    if value_num is None:
        return 'no_decision', 'مقدار نتیجه عددی معتبر نیست.', spec
    normalized_value = value_num
    if spec.unit and unit and not _unit_equal(spec.unit, unit):
        try:
            normalized_value = convert_unit(value_num, unit, spec.unit)
        except (TypeError, ValueError, OverflowError):
            return 'no_decision', f'تبدیل واحد «{unit}» به «{spec.unit}» پشتیبانی نمی‌شود.', spec
    elif spec.unit and not unit:
        return 'no_decision', f'واحد نتیجه برای Specification «{spec.unit}» مشخص نشده است.', spec

    coverage_k = _num(uncertainty_coverage_factor)
    if coverage_k is None:
        coverage_k = 2.0
    if coverage_k <= 0:
        return 'no_decision', 'ضریب پوشش k باید بزرگ‌تر از صفر باشد.', spec

    # در قرارداد سامانه، uncertainty ورودی این تابع = U (expanded uncertainty) است.
    U = _num(uncertainty)
    result = decide(
        normalized_value, spec.min_value, spec.max_value,
        U=U, k=coverage_k, rule=rule, guard_band=gb, confidence=confidence,
        lower_inclusive=spec.lower_inclusive, upper_inclusive=spec.upper_inclusive,
        uncertainty_required=bool(spec.uncertainty_required),
    )

    status_map = {'PASS': 'pass', 'FAIL': 'fail', 'NO_DECISION': 'no_decision'}
    status = status_map[result['status']]
    extra = ''
    if result.get('pc') is not None:
        extra += f" | Pc={result['pc']:.3f}%"
    if U is not None:
        extra += f" | U={U}"
    if spec.unit and unit and not _unit_equal(spec.unit, unit):
        extra += f" | نرمال‌سازی: {value_num:g} {unit} → {normalized_value:g} {spec.unit}"
    return status, result.get('message', '') + extra + f' — {spec.range_display}', spec


# ==========================================================
# لایه‌ی RAW: ذخیره‌ی وفادار Excel
# ==========================================================
class ExcelImportBatch(models.Model):
    """هر بار آپلود فایل Excel = یک Batch."""
    STATUS_CHOICES = [
        ('processing', 'در حال پردازش'),
        ('done',       'تمام شد'),
        ('failed',     'خطا'),
    ]

    file_name = models.CharField(max_length=300, verbose_name="نام فایل")
    file_size_kb = models.FloatField(default=0, verbose_name="اندازه (KB)")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
        related_name='excel_batches', verbose_name="آپلودکننده")
    sheet_name = models.CharField(max_length=100, default='بانک اطلاعاتی',
        verbose_name="نام شیت")
    total_rows = models.PositiveIntegerField(default=0, verbose_name="کل ردیف‌ها")
    new_rows = models.PositiveIntegerField(default=0, verbose_name="ردیف‌های جدید")
    duplicate_rows = models.PositiveIntegerField(default=0, verbose_name="ردیف‌های تکراری")
    error_rows = models.PositiveIntegerField(default=0, verbose_name="ردیف‌های خطا")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
        default='processing', verbose_name="وضعیت")
    log = models.TextField(blank=True, null=True, verbose_name="گزارش")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان آپلود")
    finished_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان پایان")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "دسته‌ی ورود Excel"
        verbose_name_plural = "۳۰. دسته‌های ورود Excel"

    def __str__(self):
        return f"{self.file_name} — {self.created_at}"

    @property
    def created_at_shamsi(self):
        import jdatetime
        j = jdatetime.datetime.fromgregorian(datetime=self.created_at)
        return j.strftime('%Y/%m/%d %H:%M')


class ExcelRawRow(models.Model):
    """هر ردیف Excel = یک رکورد خام (JSON کامل)."""
    batch = models.ForeignKey(ExcelImportBatch, on_delete=models.CASCADE,
        related_name='rows', verbose_name="دسته")
    row_number = models.PositiveIntegerField(verbose_name="شماره ردیف در فایل")
    tracking_code = models.CharField(max_length=100, blank=True, null=True,
        db_index=True, verbose_name="کد رهگیری")
    report_number = models.CharField(max_length=100, blank=True, null=True,
        db_index=True, verbose_name="شماره گزارش")
    raw_data = models.JSONField(default=dict, verbose_name="داده‌ی کامل")
    processed = models.BooleanField(default=False, verbose_name="پردازش شده؟")
    request = models.ForeignKey('TestRequest', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='raw_rows',
        verbose_name="درخواست لینک‌شده")
    error = models.TextField(blank=True, null=True, verbose_name="خطا")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-id']
        verbose_name = "ردیف خام Excel"
        verbose_name_plural = "۳۱. ردیف‌های خام Excel"
        indexes = [
            models.Index(fields=['tracking_code']),
            models.Index(fields=['report_number']),
        ]

    def __str__(self):
        return f"ردیف {self.row_number} — {self.tracking_code or '—'}"


# ==========================================================
# ISO/IEC 17025 — 7.9 Complaints (شکایات)
# ==========================================================
class Complaint(models.Model):
    """شکایت مشتری/متقاضی مطابق بند 7.9 ISO/IEC 17025:2017."""
    SOURCE_CHOICES = [
        ('customer', 'مشتری خارجی'),
        ('internal', 'واحد داخلی سازمان'),
        ('other', 'سایر'),
    ]
    CATEGORY_CHOICES = [
        ('technical', 'فنی — نتیجه آزمون/کالیبراسیون'),
        ('quality', 'کیفی — عدم انطباق فرآیند'),
        ('service', 'خدمات — زمان‌بندی/برخورد'),
        ('other', 'سایر'),
    ]
    SEVERITY_CHOICES = [
        ('low', 'کم'),
        ('medium', 'متوسط'),
        ('high', 'بالا'),
        ('critical', 'بحرانی'),
    ]
    STATUS_CHOICES = [
        ('received', 'دریافت شده'),
        ('investigating', 'در حال بررسی'),
        ('action', 'اقدام اصلاحی در جریان'),
        ('resolved', 'حل شده'),
        ('rejected', 'رد شده (ناموجه)'),
        ('closed', 'بسته شده'),
    ]

    complaint_no = models.CharField(max_length=50, unique=True, blank=True, verbose_name='شماره شکایت')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='customer', verbose_name='منبع')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='technical', verbose_name='دسته')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium', verbose_name='شدت')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received', verbose_name='وضعیت')

    complainant_name = models.CharField(max_length=150, verbose_name='نام شاکی')
    complainant_contact = models.CharField(max_length=200, blank=True, null=True, verbose_name='اطلاعات تماس')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='complaints', verbose_name='واحد مرتبط')
    request = models.ForeignKey(TestRequest, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='complaints', verbose_name='درخواست مرتبط')

    received_date = models.DateField(verbose_name='تاریخ دریافت')
    description = models.TextField(verbose_name='شرح شکایت')
    investigation = models.TextField(blank=True, null=True, verbose_name='بررسی و ریشه‌یابی')
    root_cause = models.TextField(blank=True, null=True, verbose_name='علت ریشه‌ای')
    corrective_action = models.TextField(blank=True, null=True, verbose_name='اقدام اصلاحی')
    preventive_action = models.TextField(blank=True, null=True, verbose_name='اقدام پیشگیرانه')
    resolution_summary = models.TextField(blank=True, null=True, verbose_name='خلاصه‌ی حل')

    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_complaints', verbose_name='مسئول پیگیری')
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='handled_complaints', verbose_name='رسیدگی‌کننده')

    acknowledged_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان تایید دریافت')
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان حل')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بستن')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='closed_complaints', verbose_name='بستن‌کننده')

    is_valid = models.BooleanField(default=True, verbose_name='شکایت موجه است؟')
    customer_satisfied = models.BooleanField(default=False, verbose_name='مشتری اعلام رضایت کرد؟')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['-received_date', '-id']
        verbose_name = 'شکایت'
        verbose_name_plural = '۳۲. شکایات (ISO 17025 — 7.9)'
        indexes = [
            models.Index(fields=['status', 'received_date']),
            models.Index(fields=['complaint_no']),
        ]

    def __str__(self):
        return f'{self.complaint_no} — {self.complainant_name} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        """تولید خودکار شماره شکایت در صورت خالی بودن."""
        if not self.complaint_no:
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f'CMP-{year}-'
            last = Complaint.objects.filter(complaint_no__startswith=prefix).order_by('-id').first()
            if last and last.complaint_no:
                try:
                    num = int(last.complaint_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.complaint_no = f'{prefix}{num:04d}'
        super().save(*args, **kwargs)


# ==========================================================
# ISO/IEC 17025 — 7.10 Non-conforming Work + CAPA
# ==========================================================
class NonConformingWork(models.Model):
    """کار غیرمنطبق مطابق بند 7.10 ISO/IEC 17025:2017."""
    SEVERITY_CHOICES = [
        ('low', 'کم'),
        ('medium', 'متوسط'),
        ('high', 'بالا'),
        ('critical', 'بحرانی'),
    ]
    STATUS_CHOICES = [
        ('reported', 'ثبت شده'),
        ('investigating', 'در حال بررسی'),
        ('action', 'اقدام اصلاحی در جریان'),
        ('verified', 'اثربخشی تایید شده'),
        ('closed', 'بسته شده'),
        ('cancelled', 'لغو شده'),
    ]
    SOURCE_CHOICES = [
        ('complaint', 'شکایت مشتری'),
        ('audit', 'ممیزی داخلی/خارجی'),
        ('qc', 'کنترل کیفیت'),
        ('equipment', 'خرابی تجهیز'),
        ('personnel', 'خطای پرسنل'),
        ('method', 'مشکل روش آزمون'),
        ('environment', 'شرایط محیطی'),
        ('sample', 'مشکل نمونه'),
        ('report', 'خطای گزارش'),
        ('other', 'سایر'),
    ]

    nc_no = models.CharField(max_length=50, unique=True, blank=True, verbose_name='شماره NC')
    title = models.CharField(max_length=250, verbose_name='عنوان')
    description = models.TextField(verbose_name='شرح عدم‌انطباق')

    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium', verbose_name='شدت')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported', verbose_name='وضعیت')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='other', verbose_name='منبع کشف')

    discovered_at = models.DateTimeField(default=timezone.now, verbose_name='زمان کشف')
    discovered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='discovered_nc', verbose_name='کاشف')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='nc_works', verbose_name='واحد مرتبط')
    lab_section = models.ForeignKey(LabSection, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='nc_works', verbose_name='آزمایشگاه مرتبط')

    related_request = models.ForeignKey(TestRequest, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='nc_works', verbose_name='درخواست مرتبط')
    related_complaint = models.ForeignKey('Complaint', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='nc_works', verbose_name='شکایت مرتبط')

    immediate_action = models.TextField(blank=True, null=True, verbose_name='اقدام فوری')
    work_stopped = models.BooleanField(default=False, verbose_name='کار متوقف شد؟')
    impact_assessment = models.TextField(blank=True, null=True, verbose_name='ارزیابی اثر بر نتایج قبلی')
    root_cause = models.TextField(blank=True, null=True, verbose_name='علت ریشه‌ای')
    corrective_action = models.TextField(blank=True, null=True, verbose_name='اقدام اصلاحی')
    preventive_action = models.TextField(blank=True, null=True, verbose_name='اقدام پیشگیرانه')
    effectiveness_check = models.TextField(blank=True, null=True, verbose_name='بررسی اثربخشی')
    effectiveness_verified = models.BooleanField(default=False, verbose_name='اثربخشی تایید شد؟')

    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_nc', verbose_name='مسئول پیگیری')
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='handled_nc', verbose_name='رسیدگی‌کننده')

    target_date = models.DateField(blank=True, null=True, verbose_name='مهلت هدف')
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان حل')
    verified_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان تایید اثربخشی')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بستن')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='closed_nc', verbose_name='بستن‌کننده')

    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['-discovered_at', '-id']
        verbose_name = 'کار غیرمنطبق (NC)'
        verbose_name_plural = '۳۳. کارهای غیرمنطبق (ISO 17025 — 7.10)'
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['nc_no']),
        ]

    def __str__(self):
        return f'{self.nc_no} — {self.title} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        if not self.nc_no:
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f'NC-{year}-'
            last = NonConformingWork.objects.filter(nc_no__startswith=prefix).order_by('-id').first()
            if last and last.nc_no:
                try:
                    num = int(last.nc_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.nc_no = f'{prefix}{num:04d}'
        super().save(*args, **kwargs)


# ==========================================================
# ISO/IEC 17025 — 8.8 Internal Audits (ممیزی داخلی)
# ==========================================================
class InternalAudit(models.Model):
    """ممیزی داخلی مطابق بند 8.8 ISO/IEC 17025:2017."""
    STATUS_CHOICES = [
        ('planned',               'برنامه‌ریزی شده'),
        ('in_progress',           'در حال انجام'),
        ('completed',             'منتظر پاسخ سرپرست'),
        ('supervisor_responded',  'منتظر تایید مدیر کیفیت/رئیس'),
        ('reviewed',              'تایید شده — آماده بستن'),
        ('closed',                'بسته شده'),
        ('cancelled',             'لغو شده'),
    ]
    AUDIT_TYPE_CHOICES = [
        ('internal',   'ممیزی داخلی'),
        ('external',   'ممیزی خارجی (مراجع)'),
        ('surveillance', 'ممیزی نظارتی'),
        ('follow_up',  'ممیزی پیگیری'),
    ]

    audit_no = models.CharField(max_length=50, unique=True, blank=True, verbose_name='شماره ممیزی')
    title = models.CharField(max_length=250, verbose_name='عنوان ممیزی')
    audit_type = models.CharField(max_length=20, choices=AUDIT_TYPE_CHOICES, default='internal', verbose_name='نوع ممیزی')
    scope = models.TextField(verbose_name='دامنه ممیزی')
    criteria = models.TextField(blank=True, null=True, verbose_name='معیارهای ممیزی (استانداردها/مقررات)')

    scheduled_date = models.DateField(verbose_name='تاریخ برنامه‌ریزی‌شده')
    performed_date = models.DateField(blank=True, null=True, verbose_name='تاریخ انجام')

    lead_auditor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='led_audits', verbose_name='سرپرست تیم ممیزی')
    auditors = models.ManyToManyField(User, blank=True, related_name='audits_as_auditor',
                                      verbose_name='تیم ممیزی')
    auditees = models.ManyToManyField(User, blank=True, related_name='audits_as_auditee',
                                      verbose_name='ممیزی‌شوندگان')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name='وضعیت')
    lab_sections = models.ManyToManyField(
        LabSection, blank=True, related_name='internal_audits',
        verbose_name='آزمایشگاه(های) ممیزی‌شده',
        help_text='پیش‌فرض: یک آزمایشگاه. در صورت لزوم چند آزمایشگاه قابل انتخاب است.',
    )

    response_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_responses',
        verbose_name='پاسخ‌دهنده سرپرست',
    )
    response_at = models.DateTimeField(
        blank=True, null=True,
        verbose_name='زمان پاسخ سرپرست',
    )
    response_text = models.TextField(
        blank=True, null=True,
        verbose_name='پاسخ سرپرست',
    )

    findings_summary = models.TextField(blank=True, null=True, verbose_name='خلاصه یافته‌ها')
    conclusion = models.TextField(blank=True, null=True, verbose_name='نتیجه‌گیری')
    recommendations = models.TextField(blank=True, null=True, verbose_name='توصیه‌ها')

    report_file = models.FileField(upload_to='audit_reports/%Y/%m/', blank=True, null=True,
                                    verbose_name='فایل گزارش ممیزی')

    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='reviewed_audits', verbose_name='بازبین')
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بازنگری')

    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='closed_audits', verbose_name='بستن‌کننده')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بستن')

    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['-scheduled_date', '-id']
        verbose_name = 'ممیزی داخلی'
        verbose_name_plural = '۳۴. ممیزی‌های داخلی (ISO 17025 — 8.8)'
        indexes = [
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['audit_no']),
        ]

    def __str__(self):
        return f'{self.audit_no} — {self.title} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        if not self.audit_no:
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f'IA-{year}-'
            last = InternalAudit.objects.filter(audit_no__startswith=prefix).order_by('-id').first()
            if last and last.audit_no:
                try:
                    num = int(last.audit_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.audit_no = f'{prefix}{num:04d}'
        super().save(*args, **kwargs)


class AuditFinding(models.Model):
    """یافته‌ی ممیزی (انطباق / عدم‌انطباق / مشاهده / فرصت بهبود)."""
    FINDING_TYPE_CHOICES = [
        ('conformity',    'انطباق'),
        ('nc_minor',      'عدم‌انطباق جزئی'),
        ('nc_major',      'عدم‌انطباق عمده'),
        ('observation',   'مشاهده'),
        ('improvement',   'فرصت بهبود'),
    ]
    STATUS_CHOICES = [
        ('open',        'باز'),
        ('in_action',   'در حال اقدام'),
        ('verified',    'اثربخشی تایید شده'),
        ('closed',      'بسته شده'),
    ]

    audit = models.ForeignKey(InternalAudit, on_delete=models.CASCADE,
                              related_name='findings', verbose_name='ممیزی')
    finding_no = models.CharField(max_length=50, blank=True, verbose_name='شماره یافته')
    finding_type = models.CharField(max_length=20, choices=FINDING_TYPE_CHOICES,
                                     default='observation', verbose_name='نوع یافته')
    iso_clause = models.CharField(max_length=50, blank=True, null=True,
                                   verbose_name='بند ISO مرتبط')
    description = models.TextField(verbose_name='شرح یافته')
    evidence = models.TextField(blank=True, null=True, verbose_name='شواهد')

    nc_work = models.ForeignKey('NonConformingWork', on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='audit_findings',
                                 verbose_name='NC مرتبط')
    corrective_action = models.TextField(blank=True, null=True, verbose_name='اقدام اصلاحی')
    due_date = models.DateField(blank=True, null=True, verbose_name='مهلت اقدام')
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='responsible_findings', verbose_name='مسئول اقدام')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name='وضعیت')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بستن')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['audit', 'id']
        verbose_name = 'یافته ممیزی'
        verbose_name_plural = 'یافته‌های ممیزی'
        indexes = [
            models.Index(fields=['finding_type', 'status']),
        ]

    def __str__(self):
        return f'{self.audit.audit_no}/{self.finding_no or self.id} — {self.get_finding_type_display()}'

    def save(self, *args, **kwargs):
        if not self.finding_no and self.audit_id:
            last = AuditFinding.objects.filter(audit=self.audit).order_by('-id').first()
            if last and last.finding_no:
                try:
                    num = int(last.finding_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.finding_no = f'F-{num:03d}'
        super().save(*args, **kwargs)


# ==========================================================
# ISO/IEC 17025 — 8.9 Management Review (بازنگری مدیریت)
# ==========================================================
class ManagementReview(models.Model):
    """بازنگری مدیریت مطابق بند 8.9 ISO/IEC 17025:2017."""
    REVIEW_TYPE_CHOICES = [
        ('initial',      'اولیه'),
        ('periodic',     'دوره‌ای'),
        ('extraordinary','فوق‌العاده'),
    ]
    STATUS_CHOICES = [
        ('draft',        'پیش‌نویس'),
        ('scheduled',    'برنامه‌ریزی شده'),
        ('in_progress',  'در حال برگزاری'),
        ('completed',    'برگزار شده'),
        ('closed',       'بسته شده'),
        ('cancelled',    'لغو شده'),
    ]

    review_no = models.CharField(max_length=50, unique=True, blank=True, verbose_name='شماره بازنگری')
    title = models.CharField(max_length=250, verbose_name='عنوان جلسه')
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPE_CHOICES,
                                    default='periodic', verbose_name='نوع بازنگری')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                               default='draft', verbose_name='وضعیت')

    scheduled_date = models.DateField(verbose_name='تاریخ برنامه‌ریزی‌شده')
    meeting_date = models.DateField(blank=True, null=True, verbose_name='تاریخ برگزاری')
    next_review_date = models.DateField(blank=True, null=True, verbose_name='تاریخ بازنگری بعدی')
    location = models.CharField(max_length=200, blank=True, null=True, verbose_name='محل برگزاری')

    chairperson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='chaired_reviews', verbose_name='رئیس جلسه')
    attendees = models.ManyToManyField(User, blank=True, related_name='management_reviews',
                                        verbose_name='شرکت‌کنندگان')
    secretary = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='secretary_reviews', verbose_name='دبیر جلسه')

    agenda = models.TextField(blank=True, null=True, verbose_name='دستور جلسه')

    # ─── ورودی‌های بازنگری (بند 8.9.2) ───
    changes_internal_external = models.TextField(blank=True, null=True,
        verbose_name='تغییرات داخلی و خارجی مرتبط با سیستم مدیریت')
    fulfillment_objectives = models.TextField(blank=True, null=True,
        verbose_name='تحقق اهداف')
    suitability_policies_procedures = models.TextField(blank=True, null=True,
        verbose_name='مناسب بودن سیاست‌ها و رویه‌ها')
    status_actions_prev_reviews = models.TextField(blank=True, null=True,
        verbose_name='وضعیت اقدامات بازنگری‌های قبلی')
    audit_results = models.TextField(blank=True, null=True,
        verbose_name='نتایج ممیزی‌های داخلی و خارجی')
    nonconformities_capa = models.TextField(blank=True, null=True,
        verbose_name='عدم‌انطباق‌ها و اقدامات اصلاحی')
    complaints_feedback = models.TextField(blank=True, null=True,
        verbose_name='شکایات و بازخورد مشتریان')
    resource_adequacy = models.TextField(blank=True, null=True,
        verbose_name='کفایت منابع')
    risk_opportunities = models.TextField(blank=True, null=True,
        verbose_name='ریسک‌ها و فرصت‌ها')
    results_interlab = models.TextField(blank=True, null=True,
        verbose_name='نتایج PT / ILC / مقایسات بین‌آزمایشگاهی')
    other_factors = models.TextField(blank=True, null=True,
        verbose_name='سایر عوامل مرتبط (توصیه‌ها، تغییرات استاندارد و ...)')

    # ─── خروجی‌های بازنگری (بند 8.9.3) ───
    conclusions = models.TextField(blank=True, null=True, verbose_name='نتیجه‌گیری‌ها')
    improvement_opportunities = models.TextField(blank=True, null=True,
        verbose_name='فرصت‌های بهبود')
    system_changes_needed = models.TextField(blank=True, null=True,
        verbose_name='نیاز به تغییرات در سیستم مدیریت')
    resource_needs = models.TextField(blank=True, null=True,
        verbose_name='نیازهای منابع')

    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    minutes_file = models.FileField(upload_to='mgmt_reviews/%Y/%m/', blank=True, null=True,
                                     verbose_name='فایل صورت‌جلسه')

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='created_reviews', verbose_name='ایجادکننده')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='closed_reviews', verbose_name='بستن‌کننده')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بستن')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['-scheduled_date', '-id']
        verbose_name = 'بازنگری مدیریت'
        verbose_name_plural = '۳۵. بازنگری‌های مدیریت (ISO 17025 — 8.9)'
        indexes = [
            models.Index(fields=['status', 'scheduled_date']),
            models.Index(fields=['review_no']),
        ]

    def __str__(self):
        return f'{self.review_no} — {self.title} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        if not self.review_no:
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f'MR-{year}-'
            last = ManagementReview.objects.filter(review_no__startswith=prefix).order_by('-id').first()
            if last and last.review_no:
                try:
                    num = int(last.review_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.review_no = f'{prefix}{num:04d}'
        super().save(*args, **kwargs)


class ManagementReviewAction(models.Model):
    """اقدام ناشی از بازنگری مدیریت."""
    STATUS_CHOICES = [
        ('open',       'باز'),
        ('in_action',  'در حال اقدام'),
        ('verified',   'اثربخشی تایید شده'),
        ('closed',     'بسته شده'),
    ]
    ACTION_TYPE_CHOICES = [
        ('improvement', 'فرصت بهبود'),
        ('corrective',  'اقدام اصلاحی'),
        ('preventive',  'اقدام پیشگیرانه'),
        ('resource',    'تخصیص منابع'),
        ('system',      'تغییر سیستم'),
        ('other',       'سایر'),
    ]

    review = models.ForeignKey(ManagementReview, on_delete=models.CASCADE,
                                related_name='actions', verbose_name='بازنگری')
    action_no = models.CharField(max_length=50, blank=True, verbose_name='شماره اقدام')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPE_CHOICES,
                                    default='improvement', verbose_name='نوع اقدام')
    description = models.TextField(verbose_name='شرح اقدام')

    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='review_actions', verbose_name='مسئول اقدام')
    due_date = models.DateField(blank=True, null=True, verbose_name='مهلت اقدام')

    expected_outcome = models.TextField(blank=True, null=True, verbose_name='نتیجه مورد انتظار')
    progress_notes = models.TextField(blank=True, null=True, verbose_name='یادداشت پیشرفت')
    effectiveness_check = models.TextField(blank=True, null=True, verbose_name='بررسی اثربخشی')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name='وضعیت')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بستن')

    class Meta:
        ordering = ['review', 'id']
        verbose_name = 'اقدام بازنگری مدیریت'
        verbose_name_plural = 'اقدامات بازنگری مدیریت'

    def __str__(self):
        return f'{self.review.review_no}/{self.action_no or self.id} — {self.get_action_type_display()}'

    def save(self, *args, **kwargs):
        if not self.action_no and self.review_id:
            last = ManagementReviewAction.objects.filter(review=self.review).order_by('-id').first()
            if last and last.action_no:
                try:
                    num = int(last.action_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.action_no = f'A-{num:03d}'
        super().save(*args, **kwargs)


# ==========================================================
# ISO/IEC 17025 — 8.5 Risk & Opportunities (ریسک و فرصت)
# ==========================================================
class RiskRegister(models.Model):
    """ریسک مرتبط با فعالیت‌های آزمایشگاهی مطابق بند 8.5 ISO/IEC 17025:2017."""
    CATEGORY_CHOICES = [
        ('technical',     'فنی — روش آزمون/کالیبراسیون'),
        ('quality',       'کیفی — عدم انطباق فرآیند'),
        ('personnel',     'منابع انسانی — صلاحیت/کفایت'),
        ('equipment',     'تجهیزات — کالیبراسیون/خرابی'),
        ('environmental', 'محیطی — شرایط فیزیکی'),
        ('supplier',      'تأمین‌کننده — مواد/خدمات'),
        ('financial',     'مالی — بودجه/منابع'),
        ('safety',        'ایمنی — HSE'),
        ('it',            'فناوری اطلاعات — داده/نرم‌افزار'),
        ('legal',         'قانونی — انطباق با مقررات'),
        ('other',         'سایر'),
    ]
    SOURCE_CHOICES = [
        ('audit',          'ممیزی داخلی/خارجی'),
        ('complaint',      'شکایت مشتری'),
        ('nc',             'عدم‌انطباق (NC)'),
        ('management_review','بازنگری مدیریت'),
        ('quality_control','کنترل کیفیت'),
        ('interlaboratory','PT / ILC'),
        ('customer',       'بازخورد مشتری'),
        ('routine',        'پایش روزمره'),
        ('change',         'تغییرات داخلی/خارجی'),
        ('other',          'سایر'),
    ]
    LEVEL_CHOICES = [
        ('low',      'کم'),
        ('medium',   'متوسط'),
        ('high',     'بالا'),
        ('critical', 'بحرانی'),
    ]
    STATUS_CHOICES = [
        ('identified',  'شناسایی شده'),
        ('analyzing',   'در حال تحلیل'),
        ('action',      'در حال اقدام'),
        ('mitigated',   'کاهش‌یافته'),
        ('accepted',    'پذیرفته شده (بدون اقدام)'),
        ('closed',      'بسته شده'),
    ]

    risk_no = models.CharField(max_length=50, unique=True, blank=True, verbose_name='شماره ریسک')
    title = models.CharField(max_length=250, verbose_name='عنوان ریسک')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='technical', verbose_name='دسته‌بندی')
    source = models.CharField(max_length=25, choices=SOURCE_CHOICES, default='routine', verbose_name='منبع شناسایی')
    description = models.TextField(verbose_name='شرح ریسک')

    # ارزیابی اولیه
    probability = models.PositiveSmallIntegerField(default=3, verbose_name='احتمال (1-5)',
        help_text='1 = بسیار کم، 5 = بسیار بالا')
    impact = models.PositiveSmallIntegerField(default=3, verbose_name='شدت اثر (1-5)',
        help_text='1 = ناچیز، 5 = بحرانی')
    risk_score = models.PositiveSmallIntegerField(default=9, verbose_name='امتیاز ریسک (خودکار)')
    risk_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='medium', verbose_name='سطح ریسک')

    # کنترل و کاهش
    existing_controls = models.TextField(blank=True, null=True, verbose_name='کنترل‌های موجود')
    mitigation_plan = models.TextField(blank=True, null=True, verbose_name='برنامه کاهش ریسک')

    # ارزیابی باقیمانده (بعد از اقدام)
    residual_probability = models.PositiveSmallIntegerField(blank=True, null=True,
        verbose_name='احتمال باقیمانده (1-5)')
    residual_impact = models.PositiveSmallIntegerField(blank=True, null=True,
        verbose_name='اثر باقیمانده (1-5)')
    residual_score = models.PositiveSmallIntegerField(blank=True, null=True,
        verbose_name='امتیاز باقیمانده (خودکار)')

    # ارتباطات
    related_nc = models.ForeignKey('NonConformingWork', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='related_risks', verbose_name='NC مرتبط')
    related_complaint = models.ForeignKey('Complaint', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='related_risks', verbose_name='شکایت مرتبط')
    related_review = models.ForeignKey('ManagementReview', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='related_risks', verbose_name='بازنگری مدیریت مرتبط')

    # مسئولیت
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='owned_risks', verbose_name='مالک ریسک')
    identified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='identified_risks', verbose_name='شناسایی‌کننده')
    identified_at = models.DateField(blank=True, null=True, verbose_name='تاریخ شناسایی')
    target_date = models.DateField(blank=True, null=True, verbose_name='تاریخ هدف کاهش')
    review_date = models.DateField(blank=True, null=True, verbose_name='تاریخ بازنگری بعدی')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='identified', verbose_name='وضعیت')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بستن')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='closed_risks', verbose_name='بستن‌کننده')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['-risk_score', '-id']
        verbose_name = 'ریسک'
        verbose_name_plural = '۳۶. ریسک‌ها (ISO 17025 — 8.5)'
        indexes = [
            models.Index(fields=['status', 'risk_level']),
            models.Index(fields=['risk_no']),
        ]

    def __str__(self):
        return f'{self.risk_no} — {self.title} [{self.get_risk_level_display()}]'

    def save(self, *args, **kwargs):
        # تولید شماره خودکار
        if not self.risk_no:
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f'RSK-{year}-'
            last = RiskRegister.objects.filter(risk_no__startswith=prefix).order_by('-id').first()
            if last and last.risk_no:
                try:
                    num = int(last.risk_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.risk_no = f'{prefix}{num:04d}'

        # محدودسازی احتمال و اثر
        p = max(1, min(5, int(self.probability or 3)))
        i = max(1, min(5, int(self.impact or 3)))
        self.probability = p
        self.impact = i
        self.risk_score = p * i

        # تعیین سطح بر اساس امتیاز
        score = self.risk_score
        if score >= 20:
            self.risk_level = 'critical'
        elif score >= 12:
            self.risk_level = 'high'
        elif score >= 6:
            self.risk_level = 'medium'
        else:
            self.risk_level = 'low'

        # امتیاز باقیمانده
        if self.residual_probability and self.residual_impact:
            rp = max(1, min(5, int(self.residual_probability)))
            ri = max(1, min(5, int(self.residual_impact)))
            self.residual_probability = rp
            self.residual_impact = ri
            self.residual_score = rp * ri
        else:
            self.residual_score = None

        super().save(*args, **kwargs)


class Opportunity(models.Model):
    """فرصت بهبود مطابق بند 8.5 ISO/IEC 17025:2017."""
    CATEGORY_CHOICES = [
        ('process',     'بهبود فرآیند'),
        ('technology',  'فناوری و تجهیزات'),
        ('training',    'آموزش و توانمندسازی'),
        ('scope',       'گسترش دامنه'),
        ('customer',    'رضایت مشتری'),
        ('efficiency',  'بهره‌وری و کاهش هزینه'),
        ('quality',     'بهبود کیفیت'),
        ('safety',      'بهبود ایمنی'),
        ('other',       'سایر'),
    ]
    STATUS_CHOICES = [
        ('identified',  'شناسایی شده'),
        ('evaluating',  'در حال ارزیابی'),
        ('action',      'در حال اقدام'),
        ('realized',    'بهره‌برداری شده'),
        ('rejected',    'رد شده'),
        ('closed',      'بسته شده'),
    ]

    opp_no = models.CharField(max_length=50, unique=True, blank=True, verbose_name='شماره فرصت')
    title = models.CharField(max_length=250, verbose_name='عنوان فرصت')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='process', verbose_name='دسته‌بندی')
    description = models.TextField(verbose_name='شرح فرصت')

    benefit_potential = models.PositiveSmallIntegerField(default=3, verbose_name='پتانسیل سود (1-5)',
        help_text='1 = ناچیز، 5 = بسیار بالا')
    feasibility = models.PositiveSmallIntegerField(default=3, verbose_name='امکان‌سنجی (1-5)',
        help_text='1 = بسیار دشوار، 5 = بسیار آسان')
    opportunity_score = models.PositiveSmallIntegerField(default=9, verbose_name='امتیاز فرصت (خودکار)')

    action_plan = models.TextField(blank=True, null=True, verbose_name='برنامه اقدام')
    expected_outcome = models.TextField(blank=True, null=True, verbose_name='نتیجه مورد انتظار')
    actual_outcome = models.TextField(blank=True, null=True, verbose_name='نتیجه واقعی')

    related_review = models.ForeignKey('ManagementReview', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='related_opportunities', verbose_name='بازنگری مدیریت مرتبط')

    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='owned_opportunities', verbose_name='مسئول')
    identified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='identified_opportunities', verbose_name='شناسایی‌کننده')
    identified_at = models.DateField(blank=True, null=True, verbose_name='تاریخ شناسایی')
    target_date = models.DateField(blank=True, null=True, verbose_name='تاریخ هدف')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='identified', verbose_name='وضعیت')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='زمان بستن')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='closed_opportunities', verbose_name='بستن‌کننده')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['-opportunity_score', '-id']
        verbose_name = 'فرصت بهبود'
        verbose_name_plural = '۳۷. فرصت‌های بهبود (ISO 17025 — 8.5)'
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['opp_no']),
        ]

    def __str__(self):
        return f'{self.opp_no} — {self.title} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        if not self.opp_no:
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f'OPP-{year}-'
            last = Opportunity.objects.filter(opp_no__startswith=prefix).order_by('-id').first()
            if last and last.opp_no:
                try:
                    num = int(last.opp_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.opp_no = f'{prefix}{num:04d}'

        # محدودسازی مقادیر
        b = max(1, min(5, int(self.benefit_potential or 3)))
        f = max(1, min(5, int(self.feasibility or 3)))
        self.benefit_potential = b
        self.feasibility = f
        self.opportunity_score = b * f

        super().save(*args, **kwargs)


# ==========================================================
# ISO/IEC 17025 — 8.4 Document Control (کنترل مدارک)
# ==========================================================
class ControlledDocument(models.Model):
    """سند کنترل‌شده مطابق بند 8.4 ISO/IEC 17025:2017."""
    DOC_TYPE_CHOICES = [
        ('policy',      'سیاست / خط‌مشی'),
        ('procedure',   'رویه (Procedure)'),
        ('instruction', 'دستورالعمل کار (WI)'),
        ('method',      'روش آزمون/کالیبراسیون'),
        ('form',        'فرم / Template'),
        ('manual',      'دستور کار / Manual'),
        ('spec',        'مشخصه / Specification'),
        ('record',      'فرم سابقه (Record Form)'),
        ('external',    'سند خارجی (استاندارد/مقررات)'),
        ('other',       'سایر'),
    ]
    CATEGORY_CHOICES = [
        ('qms',         'سیستم مدیریت کیفیت'),
        ('technical',   'فنی'),
        ('safety',      'ایمنی (HSE)'),
        ('hr',          'منابع انسانی'),
        ('it',          'فناوری اطلاعات'),
        ('administrative','اداری'),
        ('other',       'سایر'),
    ]
    STATUS_CHOICES = [
        ('draft',         'پیش‌نویس'),
        ('under_review',  'در حال بازنگری'),
        ('approved',      'تصویب‌شده'),
        ('effective',     'در حال اجرا'),
        ('superseded',    'منسوخ (نسخه قدیمی)'),
        ('obsolete',      'منسوخ شده'),
    ]

    doc_no = models.CharField(max_length=50, unique=True, verbose_name='شماره سند',
        help_text='مثال: QP-001 یا WI-TEN-03')
    title = models.CharField(max_length=300, verbose_name='عنوان سند')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES,
        default='procedure', verbose_name='نوع سند')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES,
        default='qms', verbose_name='دسته‌بندی')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
        default='draft', verbose_name='وضعیت')

    current_version = models.CharField(max_length=30, default='Rev.00',
        verbose_name='نسخه جاری')
    summary = models.TextField(blank=True, null=True, verbose_name='خلاصه / هدف سند')
    scope = models.TextField(blank=True, null=True, verbose_name='دامنه کاربرد')

    # مسئولیت‌ها
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='owned_documents', verbose_name='مالک سند')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_documents', verbose_name='تصویب‌کننده')
    approved_at = models.DateField(blank=True, null=True, verbose_name='تاریخ تصویب')

    # تاریخ‌ها
    effective_date = models.DateField(blank=True, null=True, verbose_name='تاریخ اجرا')
    review_interval_months = models.PositiveSmallIntegerField(default=12,
        verbose_name='دوره بازنگری (ماه)')
    next_review_date = models.DateField(blank=True, null=True, verbose_name='تاریخ بازنگری بعدی')

    # ارتباطات
    related_standard = models.ForeignKey(Standard, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents', verbose_name='استاندارد مرتبط')

    # توزیع
    distribution_list = models.ManyToManyField(User, blank=True,
        related_name='received_documents', verbose_name='لیست توزیع')
    distribution_notes = models.TextField(blank=True, null=True, verbose_name='یادداشت توزیع')

    # فایل
    file = models.FileField(upload_to='controlled_docs/%Y/%m/', blank=True, null=True,
        verbose_name='فایل سند')

    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_documents', verbose_name='ایجادکننده')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['doc_no', '-id']
        verbose_name = 'سند کنترل‌شده'
        verbose_name_plural = '۳۸. اسناد کنترل‌شده (ISO 17025 — 8.4)'
        indexes = [
            models.Index(fields=['status', 'doc_type']),
            models.Index(fields=['doc_no']),
            models.Index(fields=['next_review_date']),
        ]

    def __str__(self):
        return f'{self.doc_no} — {self.title} [{self.current_version}]'

    @property
    def is_due_for_review(self):
        """آیا سند برای بازنگری سررسید شده؟"""
        if not self.next_review_date:
            return False
        from django.utils import timezone as _tz
        return self.next_review_date <= _tz.now().date()

    @property
    def is_expiring_soon(self):
        """آیا تا ۳۰ روز آینده سررسید بازنگری دارد؟"""
        if not self.next_review_date:
            return False
        from datetime import timedelta
        from django.utils import timezone as _tz
        return self.next_review_date <= (_tz.now().date() + timedelta(days=30))


class DocumentVersion(models.Model):
    """نسخه‌های تاریخی یک سند کنترل‌شده."""
    document = models.ForeignKey(ControlledDocument, on_delete=models.CASCADE,
        related_name='versions', verbose_name='سند')
    version = models.CharField(max_length=30, verbose_name='شماره نسخه',
        help_text='مثال: Rev.01')
    change_summary = models.TextField(blank=True, null=True, verbose_name='خلاصه تغییرات')
    file = models.FileField(upload_to='controlled_docs/versions/%Y/%m/', blank=True, null=True,
        verbose_name='فایل این نسخه')

    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_versions', verbose_name='تصویب‌کننده')
    approved_at = models.DateField(blank=True, null=True, verbose_name='تاریخ تصویب')
    effective_date = models.DateField(blank=True, null=True, verbose_name='تاریخ اجرا')
    superseded_date = models.DateField(blank=True, null=True, verbose_name='تاریخ منسوخ شدن')

    is_current = models.BooleanField(default=False, verbose_name='نسخه جاری؟')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_versions', verbose_name='ایجادکننده')

    class Meta:
        ordering = ['document', '-id']
        verbose_name = 'نسخه سند'
        verbose_name_plural = 'نسخه‌های اسناد'

    def __str__(self):
        return f'{self.document.doc_no} — {self.version}'


class DocumentChangeLog(models.Model):
    """لاگ تغییرات اسناد (مطابق الزام 8.4.2 — شناسایی تغییرات)."""
    CHANGE_TYPE_CHOICES = [
        ('create',    'ایجاد سند'),
        ('revise',    'بازنگری'),
        ('approve',   'تصویب'),
        ('distribute','توزیع'),
        ('supersede', 'منسوخ کردن نسخه قبلی'),
        ('obsolete',  'منسوخ کردن سند'),
        ('withdraw',  'پس گرفتن از توزیع'),
        ('other',     'سایر'),
    ]

    document = models.ForeignKey(ControlledDocument, on_delete=models.CASCADE,
        related_name='change_logs', verbose_name='سند')
    change_type = models.CharField(max_length=20, choices=CHANGE_TYPE_CHOICES,
        default='revise', verbose_name='نوع تغییر')
    from_version = models.CharField(max_length=30, blank=True, null=True,
        verbose_name='از نسخه')
    to_version = models.CharField(max_length=30, blank=True, null=True,
        verbose_name='به نسخه')
    description = models.TextField(verbose_name='شرح تغییر')
    reason = models.TextField(blank=True, null=True, verbose_name='دلیل تغییر')

    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='document_changes', verbose_name='تغییردهنده')
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان تغییر')

    class Meta:
        ordering = ['-changed_at']
        verbose_name = 'لاگ تغییر سند'
        verbose_name_plural = 'لاگ‌های تغییرات اسناد'

    def __str__(self):
        return f'{self.document.doc_no}: {self.get_change_type_display()} — {self.changed_at}'


# ==========================================================
# ISO/IEC 17025 — 8.3 Records Control (کنترل سوابق)
# ==========================================================
class RecordRetentionPolicy(models.Model):
    """پالیسی نگهداری سوابق مطابق بند 8.3 ISO/IEC 17025:2017."""
    RECORD_TYPE_CHOICES = [
        ('test_results',        'نتایج آزمون'),
        ('calibration_results', 'نتایج کالیبراسیون'),
        ('test_requests',       'درخواست‌های آزمون'),
        ('complaints',          'شکایات'),
        ('nc_works',            'کارهای غیرمنطبق (NC)'),
        ('internal_audits',     'ممیزی‌های داخلی'),
        ('management_reviews',  'بازنگری‌های مدیریت'),
        ('risks',               'ریسک‌ها و فرصت‌ها'),
        ('controlled_docs',     'اسناد کنترل‌شده'),
        ('personnel_records',   'سوابق پرسنلی'),
        ('equipment_records',   'سوابق تجهیزات'),
        ('qc_records',          'رکوردهای کنترل کیفیت'),
        ('environmental_logs',  'سوابق شرایط محیطی'),
        ('excel_raw_data',      'داده‌های خام Excel'),
        ('messages',            'پیام‌های داخلی'),
        ('other',               'سایر'),
    ]
    ACCESS_LEVEL_CHOICES = [
        ('public',      'عمومی (همه کاربران)'),
        ('internal',    'داخلی (کاربران احراز هویت‌شده)'),
        ('restricted',  'محدود (نقش‌های مشخص)'),
        ('confidential','محرمانه (فقط مدیران)'),
    ]
    DISPOSAL_CHOICES = [
        ('shred',       'خرد کردن'),
        ('delete',      'حذف دیجیتال'),
        ('archive',     'بایگانی'),
        ('return',      'بازگرداندن به مشتری'),
        ('other',       'سایر'),
    ]

    record_type = models.CharField(max_length=30, choices=RECORD_TYPE_CHOICES,
        unique=True, verbose_name='نوع سابقه')
    title = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='عنوان (اختیاری)')
    description = models.TextField(blank=True, null=True, verbose_name='توضیحات')

    retention_years = models.PositiveSmallIntegerField(default=5,
        verbose_name='مدت نگهداری (سال)',
        help_text='حداقل ۵ سال طبق ISO 17025 — قابل تنظیم بر اساس الزامات')
    retention_notes = models.TextField(blank=True, null=True,
        verbose_name='یادداشت مدت نگهداری')

    storage_location = models.CharField(max_length=250, blank=True, null=True,
        verbose_name='محل نگهداری',
        help_text='مثال: سرور داخلی / آرشیو فیزیکی / NAS')
    storage_format = models.CharField(max_length=150, blank=True, null=True,
        verbose_name='قالب نگهداری',
        help_text='مثال: SQLite / PDF / Excel / کاغذ')

    access_level = models.CharField(max_length=20, choices=ACCESS_LEVEL_CHOICES,
        default='internal', verbose_name='سطح دسترسی')
    access_notes = models.TextField(blank=True, null=True, verbose_name='یادداشت دسترسی')

    backup_frequency = models.CharField(max_length=100, blank=True, null=True,
        verbose_name='دوره پشتیبان‌گیری',
        help_text='مثال: روزانه / هفتگی')

    disposal_method = models.CharField(max_length=20, choices=DISPOSAL_CHOICES,
        default='archive', verbose_name='روش امحا')
    disposal_notes = models.TextField(blank=True, null=True, verbose_name='یادداشت امحا')

    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='retention_policies', verbose_name='مسئول نگهداری')

    legal_requirements = models.TextField(blank=True, null=True,
        verbose_name='الزامات قانونی/مقرراتی')

    is_active = models.BooleanField(default=True, verbose_name='فعال؟')
    last_reviewed_at = models.DateField(blank=True, null=True, verbose_name='آخرین بازنگری')
    next_review_at = models.DateField(blank=True, null=True, verbose_name='بازنگری بعدی')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_policies', verbose_name='ایجادکننده')

    class Meta:
        ordering = ['record_type']
        verbose_name = 'پالیسی نگهداری سابقه'
        verbose_name_plural = '۳۹. پالیسی‌های نگهداری سوابق (ISO 17025 — 8.3)'
        indexes = [
            models.Index(fields=['record_type', 'is_active']),
        ]

    def __str__(self):
        return f'{self.get_record_type_display()} — {self.retention_years} سال'


# ==========================================================
# ISO/IEC 17025 — 7.2 Method Validation (اعتبارسنجی روش)
# ==========================================================
class MethodValidation(models.Model):
    """اعتبارسنجی روش آزمون/کالیبراسیون مطابق بند 7.2 ISO/IEC 17025:2017."""
    STATUS_CHOICES = [
        ('draft',         'پیش‌نویس'),
        ('in_progress',   'در حال اجرا'),
        ('completed',     'انجام شده'),
        ('approved',      'تصویب شده'),
        ('rejected',      'رد شده'),
        ('obsolete',      'منسوخ'),
    ]
    VALIDATION_TYPE_CHOICES = [
        ('full',          'اعتبارسنجی کامل'),
        ('partial',       'اعتبارسنجی جزئی'),
        ('verification',  'راستی‌آزمایی روش استاندارد'),
        ('revalidation',  'اعتبارسنجی مجدد'),
        ('transfer',      'انتقال روش'),
    ]
    FIT_CHOICES = [
        ('yes',      'مناسب برای هدف'),
        ('no',       'نامناسب'),
        ('conditional', 'مناسب مشروط'),
    ]

    validation_no = models.CharField(max_length=50, unique=True, blank=True,
        verbose_name='شماره اعتبارسنجی')
    title = models.CharField(max_length=250, verbose_name='عنوان')

    method_name = models.CharField(max_length=250, verbose_name='نام روش')
    method_version = models.CharField(max_length=50, blank=True, null=True,
        verbose_name='نسخه روش')
    method_reference = models.CharField(max_length=250, blank=True, null=True,
        verbose_name='مرجع روش')

    validation_type = models.CharField(max_length=20, choices=VALIDATION_TYPE_CHOICES,
        default='full', verbose_name='نوع اعتبارسنجی')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
        default='draft', verbose_name='وضعیت')

    test_category = models.ForeignKey(TestCategory, on_delete=models.PROTECT,
        null=True, blank=True, related_name='method_validations',
        verbose_name='دسته آزمون')
    test_item = models.ForeignKey(TestItem, on_delete=models.PROTECT,
        null=True, blank=True, related_name='method_validations',
        verbose_name='زیرآزمون')
    standard = models.ForeignKey(Standard, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='method_validations',
        verbose_name='استاندارد مرجع')

    scope = models.TextField(blank=True, null=True, verbose_name='حوزه کاربرد')
    purpose = models.TextField(blank=True, null=True, verbose_name='هدف اعتبارسنجی')

    # ─── پارامترهای عملکردی (بند 7.2.2) ───
    # حوزه اندازه‌گیری
    range_min = models.FloatField(blank=True, null=True, verbose_name='حد پایین دامنه')
    range_max = models.FloatField(blank=True, null=True, verbose_name='حد بالای دامنه')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد')

    # صحت
    trueness = models.FloatField(blank=True, null=True, verbose_name='صحت (Trueness)')
    trueness_unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد صحت')
    accuracy = models.FloatField(blank=True, null=True, verbose_name='دقت کل (Accuracy)')
    accuracy_notes = models.TextField(blank=True, null=True, verbose_name='یادداشت دقت')

    # دقت — تکرارپذیری
    repeatability = models.FloatField(blank=True, null=True, verbose_name='تکرارپذیری (Repeatability)')
    repeatability_unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد تکرارپذیری')
    repeatability_conditions = models.TextField(blank=True, null=True, verbose_name='شرایط تکرارپذیری')

    # دقت — بازتولیدپذیری
    reproducibility = models.FloatField(blank=True, null=True, verbose_name='بازتولیدپذیری (Reproducibility)')
    reproducibility_unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد بازتولیدپذیری')
    reproducibility_conditions = models.TextField(blank=True, null=True, verbose_name='شرایط بازتولیدپذیری')

    # حد تشخیص و کمی‌سازی
    lod = models.FloatField(blank=True, null=True, verbose_name='حد تشخیص (LOD)')
    lod_unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد LOD')
    loq = models.FloatField(blank=True, null=True, verbose_name='حد کمی‌سازی (LOQ)')
    loq_unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد LOQ')

    # انتخاب‌پذیری
    selectivity = models.TextField(blank=True, null=True, verbose_name='انتخاب‌پذیری / ویژگی')

    # خطی بودن
    linearity_r2 = models.FloatField(blank=True, null=True, verbose_name='ضریب تعیین (R²)')
    linearity_equation = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='معادله خطی')
    linearity_points = models.JSONField(default=list, blank=True,
        verbose_name='نقاط خطی‌سازی')

    # مقاومت
    robustness = models.TextField(blank=True, null=True, verbose_name='مقاومت (Robustness)')

    # عدم‌قطعیت
    uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم‌قطعیت (U)')
    uncertainty_unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد عدم‌قطعیت')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')

    # نتیجه‌گیری
    validation_conclusion = models.TextField(blank=True, null=True, verbose_name='نتیجه‌گیری اعتبارسنجی')
    is_fit_for_purpose = models.CharField(max_length=20, choices=FIT_CHOICES,
        default='yes', verbose_name='مناسب بودن برای هدف')
    limitations = models.TextField(blank=True, null=True, verbose_name='محدودیت‌ها')
    recommendations = models.TextField(blank=True, null=True, verbose_name='توصیه‌ها')

    # مسئولیت‌ها
    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='responsible_validations', verbose_name='مسئول اعتبارسنجی')
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='performed_validations', verbose_name='انجام‌دهنده')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_validations', verbose_name='تصویب‌کننده')
    approved_at = models.DateField(blank=True, null=True, verbose_name='تاریخ تصویب')

    # زمان‌ها
    started_at = models.DateField(blank=True, null=True, verbose_name='تاریخ شروع')
    completed_at = models.DateField(blank=True, null=True, verbose_name='تاریخ پایان')
    next_review_at = models.DateField(blank=True, null=True, verbose_name='تاریخ بازنگری بعدی')

    # فایل‌ها و گزارش
    protocol_file = models.FileField(upload_to='method_validations/protocols/%Y/%m/',
        blank=True, null=True, verbose_name='فایل پروتکل اعتبارسنجی')
    report_file = models.FileField(upload_to='method_validations/reports/%Y/%m/',
        blank=True, null=True, verbose_name='فایل گزارش اعتبارسنجی')

    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_validations', verbose_name='ایجادکننده')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'اعتبارسنجی روش'
        verbose_name_plural = '۴۰. اعتبارسنجی روش‌ها (ISO 17025 — 7.2)'
        indexes = [
            models.Index(fields=['status', 'validation_type']),
            models.Index(fields=['validation_no']),
            models.Index(fields=['next_review_at']),
        ]

    def __str__(self):
        return f'{self.validation_no} — {self.method_name} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        if not self.validation_no:
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f'MV-{year}-'
            last = MethodValidation.objects.filter(validation_no__startswith=prefix).order_by('-id').first()
            if last and last.validation_no:
                try:
                    num = int(last.validation_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.validation_no = f'{prefix}{num:04d}'
        super().save(*args, **kwargs)

    @property
    def is_due_for_review(self):
        if not self.next_review_at:
            return False
        from django.utils import timezone as _tz
        return self.next_review_at <= _tz.now().date()

    @property
    def is_expiring_soon(self):
        if not self.next_review_at:
            return False
        from datetime import timedelta
        from django.utils import timezone as _tz
        return self.next_review_at <= (_tz.now().date() + timedelta(days=60))


class MethodValidationParameter(models.Model):
    """پارامتر اندازه‌گیری‌شده در یک اعتبارسنجی (Repeatability/Reproducibility/...)."""
    PARAM_TYPE_CHOICES = [
        ('repeatability',    'تکرارپذیری'),
        ('reproducibility',  'بازتولیدپذیری'),
        ('trueness',         'صحت'),
        ('accuracy',         'دقت کل'),
        ('lod',              'حد تشخیص'),
        ('loq',              'حد کمی‌سازی'),
        ('linearity',        'خطی بودن'),
        ('selectivity',      'انتخاب‌پذیری'),
        ('robustness',       'مقاومت'),
        ('uncertainty',      'عدم‌قطعیت'),
        ('other',            'سایر'),
    ]

    validation = models.ForeignKey(MethodValidation, on_delete=models.CASCADE,
        related_name='parameters', verbose_name='اعتبارسنجی')
    param_no = models.CharField(max_length=50, blank=True, verbose_name='شماره پارامتر')
    parameter_type = models.CharField(max_length=20, choices=PARAM_TYPE_CHOICES,
        verbose_name='نوع پارامتر')
    parameter_name = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='نام پارامتر (اختیاری)')

    # نتایج
    value = models.FloatField(blank=True, null=True, verbose_name='مقدار')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد')
    acceptance_criteria = models.CharField(max_length=250, blank=True, null=True,
        verbose_name='معیار پذیرش')
    meets_criteria = models.BooleanField(default=True, verbose_name='مطابقت دارد؟')
    method_used = models.CharField(max_length=250, blank=True, null=True,
        verbose_name='روش/مرجع')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    raw_data = models.JSONField(default=dict, blank=True, verbose_name='داده خام')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['validation', 'id']
        verbose_name = 'پارامتر اعتبارسنجی'
        verbose_name_plural = 'پارامترهای اعتبارسنجی'

    def __str__(self):
        return f'{self.validation.validation_no} — {self.get_parameter_type_display()}'

    def save(self, *args, **kwargs):
        if not self.param_no and self.validation_id:
            last = MethodValidationParameter.objects.filter(validation=self.validation).order_by('-id').first()
            if last and last.param_no:
                try:
                    num = int(last.param_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.param_no = f'P-{num:03d}'
        super().save(*args, **kwargs)


# ==========================================================
# ISO/IEC 17025 — 6.5 Traceability / Reference Standards
# ==========================================================
class ReferenceStandard(models.Model):
    """استاندارد مرجع برای ردیابی اندازه‌شناسی مطابق بند 6.5 ISO/IEC 17025:2017."""
    STANDARD_TYPE_CHOICES = [
        ('crm',              'مواد مرجع گواهی‌شده (CRM)'),
        ('rm',               'مواد مرجع (RM)'),
        ('calibration_std',  'استاندارد کالیبراسیون'),
        ('reference_method', 'روش مرجع'),
        ('working_std',      'استاندارد کاری (Working Std)'),
        ('check_std',        'استاندارد کنترلی'),
        ('other',            'سایر'),
    ]
    STATUS_CHOICES = [
        ('active',        'فعال'),
        ('expiring_soon', 'نزدیک به انقضا'),
        ('expired',       'منقضی'),
        ('depleted',      'تمام‌شده'),
        ('out_of_service','خارج از سرویس'),
        ('obsolete',      'منسوخ'),
    ]
    TRACEABILITY_CHOICES = [
        ('si',          'یکای SI'),
        ('nmi',         'مؤسسه ملی اندازه‌شناسی (NMI)'),
        ('crm',         'مواد مرجع گواهی‌شده'),
        ('reference_method', 'روش مرجع'),
        ('consensus',   'استاندارد توافقی'),
        ('ilac',        'زنجیره ILAC'),
        ('other',       'سایر'),
    ]

    ref_no = models.CharField(max_length=50, unique=True, blank=True,
        verbose_name='شماره استاندارد مرجع')
    name = models.CharField(max_length=250, verbose_name='نام استاندارد')
    standard_type = models.CharField(max_length=25, choices=STANDARD_TYPE_CHOICES,
        default='calibration_std', verbose_name='نوع استاندارد')

    manufacturer = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='تولیدکننده / تأمین‌کننده')
    catalog_no = models.CharField(max_length=100, blank=True, null=True, verbose_name='کاتالوگ')
    lot_no = models.CharField(max_length=100, blank=True, null=True, verbose_name='شماره لات (Lot)')
    serial_no = models.CharField(max_length=100, blank=True, null=True, verbose_name='شماره سریال')
    asset_no = models.CharField(max_length=100, blank=True, null=True, verbose_name='شماره اموال')

    certificate_no = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='شماره گواهی')
    certificate_file = models.FileField(upload_to='reference_standards/certs/%Y/%m/',
        blank=True, null=True, verbose_name='فایل گواهی')
    certificate_issue_date = models.DateField(blank=True, null=True,
        verbose_name='تاریخ صدور گواهی')

    # مقدار و عدم‌قطعیت
    assigned_value = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='مقدار تخصیص‌یافته',
        help_text='مثال: 100.00 یا ترکیب چند عنصر')
    uncertainty = models.FloatField(blank=True, null=True, verbose_name='عدم‌قطعیت (U)')
    unit = models.CharField(max_length=40, blank=True, null=True, verbose_name='واحد')
    coverage_factor = models.FloatField(default=2.0, verbose_name='ضریب پوشش k')
    measurement_range = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='دامنه اندازه‌گیری')

    # ردیابی
    traceability_type = models.CharField(max_length=25, choices=TRACEABILITY_CHOICES,
        default='nmi', verbose_name='نوع ردیابی')
    traceability_chain = models.TextField(blank=True, null=True,
        verbose_name='زنجیره ردیابی',
        help_text='مثال: NIST → PTB → آزمایشگاه X → این استاندارد')
    accredited_by = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='تأییدشده توسط',
        help_text='مثال: NIST، PTB، NMI، ILAC-MRA')

    # تاریخ‌ها
    received_date = models.DateField(blank=True, null=True, verbose_name='تاریخ دریافت')
    opened_date = models.DateField(blank=True, null=True, verbose_name='تاریخ بازکردن')
    expiry_date = models.DateField(blank=True, null=True, verbose_name='تاریخ انقضا')

    # نگهداری
    storage_conditions = models.TextField(blank=True, null=True,
        verbose_name='شرایط نگهداری',
        help_text='مثال: دمای 2-8 °C، دور از نور')
    storage_location = models.CharField(max_length=200, blank=True, null=True,
        verbose_name='محل نگهداری')
    usage_instructions = models.TextField(blank=True, null=True,
        verbose_name='دستورالعمل استفاده')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
        default='active', verbose_name='وضعیت')
    is_active = models.BooleanField(default=True, verbose_name='در چرخه بهره‌برداری؟')

    responsible = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='responsible_refs', verbose_name='مسئول نگهداری')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_refs', verbose_name='ایجادکننده')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = 'استاندارد مرجع'
        verbose_name_plural = '۴۱. استانداردهای مرجع (ISO 17025 — 6.5)'
        indexes = [
            models.Index(fields=['status', 'standard_type']),
            models.Index(fields=['ref_no']),
            models.Index(fields=['expiry_date']),
        ]

    def __str__(self):
        return f'{self.ref_no} — {self.name}'

    def save(self, *args, **kwargs):
        if not self.ref_no:
            from django.utils import timezone as _tz
            year = _tz.now().year
            prefix = f'REF-{year}-'
            last = ReferenceStandard.objects.filter(ref_no__startswith=prefix).order_by('-id').first()
            if last and last.ref_no:
                try:
                    num = int(last.ref_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.ref_no = f'{prefix}{num:04d}'

        # بروزرسانی خودکار status بر اساس تاریخ انقضا
        if self.expiry_date:
            from django.utils import timezone as _tz
            from datetime import timedelta
            today = _tz.now().date()
            if self.expiry_date < today:
                if self.status not in ('depleted', 'out_of_service', 'obsolete'):
                    self.status = 'expired'
            elif self.expiry_date <= today + timedelta(days=60):
                if self.status not in ('depleted', 'out_of_service', 'obsolete'):
                    self.status = 'expiring_soon'

        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        if not self.expiry_date:
            return False
        from django.utils import timezone as _tz
        return self.expiry_date < _tz.now().date()

    @property
    def is_expiring_soon(self):
        if not self.expiry_date:
            return False
        from django.utils import timezone as _tz
        from datetime import timedelta
        return self.expiry_date <= (_tz.now().date() + timedelta(days=60))

    @property
    def days_to_expiry(self):
        if not self.expiry_date:
            return None
        from django.utils import timezone as _tz
        return (self.expiry_date - _tz.now().date()).days


class ReferenceStandardUsage(models.Model):
    """ثبت استفاده از یک استاندارد مرجع."""
    USAGE_TYPE_CHOICES = [
        ('calibration',  'کالیبراسیون تجهیز'),
        ('test',         'آزمون'),
        ('verification', 'راستی‌آزمایی'),
        ('training',     'آموزش'),
        ('check',        'کنترل دوره‌ای'),
        ('other',        'سایر'),
    ]

    reference = models.ForeignKey(ReferenceStandard, on_delete=models.CASCADE,
        related_name='usages', verbose_name='استاندارد مرجع')
    usage_no = models.CharField(max_length=50, blank=True, verbose_name='شماره استفاده')
    usage_type = models.CharField(max_length=20, choices=USAGE_TYPE_CHOICES,
        default='test', verbose_name='نوع استفاده')

    used_at = models.DateField(default=None, null=True, blank=True, verbose_name='تاریخ استفاده')
    used_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ref_usages', verbose_name='استفاده‌کننده')

    related_request = models.ForeignKey('TestRequest', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ref_standard_usages',
        verbose_name='درخواست مرتبط')
    related_equipment = models.ForeignKey('Equipment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='ref_standard_usages',
        verbose_name='تجهیز مرتبط')

    amount_used = models.CharField(max_length=100, blank=True, null=True,
        verbose_name='مقدار مصرفی')
    purpose = models.TextField(blank=True, null=True, verbose_name='هدف استفاده')
    notes = models.TextField(blank=True, null=True, verbose_name='یادداشت')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان ثبت')

    class Meta:
        ordering = ['-used_at', '-id']
        verbose_name = 'استفاده از استاندارد مرجع'
        verbose_name_plural = 'استفاده‌های استانداردهای مرجع'

    def __str__(self):
        return f'{self.reference.ref_no} — {self.get_usage_type_display()} ({self.used_at})'

    def save(self, *args, **kwargs):
        if not self.usage_no and self.reference_id:
            last = ReferenceStandardUsage.objects.filter(reference=self.reference).order_by('-id').first()
            if last and last.usage_no:
                try:
                    num = int(last.usage_no.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    num = 1
            else:
                num = 1
            self.usage_no = f'U-{num:03d}'
        if not self.used_at:
            from django.utils import timezone as _tz
            self.used_at = _tz.now().date()
        super().save(*args, **kwargs)


# ═══════════════════════════════════════════════════════════
# مدل‌های کالیبراسیون
# ═══════════════════════════════════════════════════════════
from .models_calib import (
    EquipmentLocation, EquipmentNameCode, RangeSpec,
    QuantitySpec, CalibrationRegistry, CalibrationEquipment, MPERule,
    EquipmentCategory,
    IntervalBank, RiskCriterion,
    PricingSection, PricingItem, Invoice, InvoiceLine,
)



# ═══════════════════════════════════════════════════════════
# تجهیزات مرجع کالیبراسیون
# ═══════════════════════════════════════════════════════════
from .models_ref import ReferenceEquipment, ReferenceCertificate, ReferenceCertificateFile



# ═══════════════════════════════════════════════════════════
# گروه‌های تولیدی و قیمت‌گذاری
# ═══════════════════════════════════════════════════════════
from .models_group import ProductionGroup, CalibrationPricing


# ─── Re-export از models_calib (برای دسترسی از views.py) ───
from .models_calib import (
    RISK_CRITERIA,
    RISK_LEVEL_CHOICES,
    RISK_LEVEL_LABEL,
    score_for_risk,
    overall_risk_from_total,
    IntervalBank,
    RiskCriterion,
)

# ═══════════════════════════════════════════════════════════
# اطلاعات شرکت (Singleton) — قابل ویرایش از ادمین
# ═══════════════════════════════════════════════════════════
class CompanyInfo(models.Model):
    """اطلاعات شرکت و آزمایشگاه برای گواهی‌ها و گزارش‌ها"""
    company_name_fa = models.CharField(max_length=200, default='ماشین سازی اراک', verbose_name="نام شرکت (فارسی)")
    company_name_en = models.CharField(max_length=200, blank=True, default='Machine Sazi Arak', verbose_name="نام شرکت (انگلیسی)")
    lab_name_fa = models.CharField(max_length=200, default='آزمایشگاه مرکزی', verbose_name="نام آزمایشگاه")
    lab_subtitle_fa = models.CharField(max_length=200, default='آزمایشگاه کالیبراسیون', verbose_name="زیرعنوان آزمایشگاه")
    lab_name_en = models.CharField(max_length=200, blank=True, default='Central Laboratory - Calibration', verbose_name="نام آزمایشگاه (انگلیسی)")

    address_fa = models.CharField(max_length=300, blank=True, default='کیلومتر 5 جاده اراک - تهران به میدان صنعت، ماشین سازی اراک', verbose_name="آدرس")
    phone = models.CharField(max_length=100, blank=True, default='086-34500000', verbose_name="تلفن")
    fax = models.CharField(max_length=100, blank=True, default='086-34500001', verbose_name="فکس")
    website = models.CharField(max_length=100, blank=True, default='www.msa.ir', verbose_name="وب‌سایت")
    email = models.EmailField(blank=True, default='calibration@msa.ir', verbose_name="ایمیل")

    form_code = models.CharField(max_length=50, blank=True, default='F-CAL-01', verbose_name="کد فرم")
    form_revision = models.CharField(max_length=20, blank=True, default='01', verbose_name="ویرایش فرم")
    form_issue_date = models.CharField(max_length=20, blank=True, default='1405/07/20', verbose_name="تاریخ صدور فرم")

    iso_standard = models.CharField(max_length=100, blank=True, default='ISO/IEC 17025:2017', verbose_name="استاندارد")

    logo_company = models.CharField(max_length=200, blank=True, default='img/logo.png', verbose_name="لوگو شرکت")
    logo_lab = models.CharField(max_length=200, blank=True, default='img/LAB.png', verbose_name="لوگو آزمایشگاه")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "اطلاعات شرکت"
        verbose_name_plural = "اطلاعات شرکت"

    def __str__(self):
        return self.company_name_fa

    def save(self, *args, **kwargs):
        # Singleton: فقط یک رکورد
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

# ═══════════════════════════════════════════════════════════
# قالب‌های گواهی کالیبراسیون (Builder)
# ═══════════════════════════════════════════════════════════
class CertificateTemplate(models.Model):
    """قالب گواهی کالیبراسیون - قابل ویرایش با GrapesJS"""
    name = models.CharField(max_length=200, verbose_name="نام قالب")
    html = models.TextField(blank=True, verbose_name="HTML")
    css = models.TextField(blank=True, verbose_name="CSS")
    is_default = models.BooleanField(default=False, verbose_name="پیش‌فرض")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    description = models.CharField(max_length=300, blank=True, verbose_name="توضیحات")
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-updated_at']
        verbose_name = "قالب گواهی"
        verbose_name_plural = "قالب‌های گواهی"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # فقط یک قالب پیش‌فرض
        if self.is_default:
            CertificateTemplate.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

from .models_verification import *

from .models_verification_settings import *


class RoleTitle(models.Model):
    """عنوان نمایشی نقش‌ها (قابل ویرایش در ادمین)"""
    code = models.CharField(max_length=50, unique=True, verbose_name="کد سیستم")
    title = models.CharField(max_length=100, verbose_name="عنوان نمایشی")

    class Meta:
        verbose_name = "عنوان نقش"
        verbose_name_plural = "عناوین نقش‌ها (مانند مدیر فنی، رئیس...)"

    def __str__(self):
        return f"{self.title} ({self.code})"


# MECHANICAL_OPTIONS_V1
class MechanicalTestOption(models.Model):
    TEST_CHOICES = [
        ('bend', 'Bend'),
        ('flaring', 'Flaring'),
        ('flattening', 'Flattening'),
    ]
    test_code = models.CharField(max_length=20, choices=TEST_CHOICES)
    field_key = models.CharField(max_length=80)
    value = models.CharField(max_length=250)
    label = models.CharField(max_length=250)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['test_code', 'field_key', 'display_order', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['test_code', 'field_key', 'value'],
                name='uniq_mech_option_value',
            ),
        ]
        verbose_name = 'Mechanical test option'
        verbose_name_plural = 'Mechanical test dropdown options'

    def __str__(self):
        return f"{self.test_code} / {self.field_key}: {self.label}"


# MECHANICAL_SUMMARY_V1
class MechanicalTestSummary(models.Model):
    TEST_CHOICES = [
        ('bend', 'Bend'), ('flaring', 'Flaring'),
        ('flattening', 'Flattening'),
    ]
    STATUS_CHOICES = [('', 'Incomplete'), ('Pass', 'Pass'), ('Fail', 'Fail')]
    request = models.ForeignKey(
        TestRequest, on_delete=models.CASCADE,
        related_name='mechanical_test_summaries',
    )
    assignment = models.ForeignKey(
        RequestAssignment, on_delete=models.CASCADE,
        related_name='mechanical_test_summaries',
    )
    test_code = models.CharField(max_length=20, choices=TEST_CHOICES)
    automatic_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, blank=True, default='',
    )
    final_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, blank=True, default='',
    )
    is_overridden = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True, default='')
    common_data = models.JSONField(default=dict, blank=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='updated_mechanical_test_summaries',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['assignment', 'test_code'],
                name='uniq_mech_summary_assignment',
            ),
        ]
        verbose_name = 'Mechanical test summary'
        verbose_name_plural = 'Mechanical test summaries'

    def __str__(self):
        return f"{self.request_id} / {self.test_code}: {self.final_status}"

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        errors = {}
        if self.assignment_id and self.request_id:
            if self.assignment.request_id != self.request_id:
                errors['assignment'] = 'Assignment belongs to another request.'
        if self.is_overridden:
            if not (self.override_reason or '').strip():
                errors['override_reason'] = 'An override reason is required.'
            if not self.automatic_status or not self.final_status:
                errors['final_status'] = 'Incomplete results cannot be overridden.'
        elif self.final_status != self.automatic_status:
            errors['final_status'] = 'Final and automatic results must match.'
        if errors:
            raise ValidationError(errors)
