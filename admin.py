"""پیکربندی پنل ادمین برای همه مدل‌های LIMS."""
import json

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.utils.html import format_html, mark_safe

import openpyxl

from django.apps import apps as _apps

def _m(name):
    return _apps.get_model("core", name)




from .models import (
    # پایه
    Department, UserProfile, LabSection, TestCategory, TestItem,
    MaterialSuggestion, DynamicField,
    # گردش‌کار
    TestRequest, RequestAssignment, RequestHistory,
    # نتایج
    TensileTestResult, ImpactTestResult, HardnessTestResult,
    ChemicalAnalysisResult, BendTestResult, FlatteningTestResult,
    FlaringTestResult, MetallographyResult,
    ForceTestResult, CorrosionTestResult, PMIResult, GeneralTestResult,
    # استاندارد و تجهیزات
    Standard, Equipment, CalibrationLimit,
    # کالیبراسیون
    CalibrationResult, CalibrationUncertaintyComponent,
    ConformityDecision, TestUncertaintyProfile,
    # ISO 17025
    EquipmentCheck, EnvironmentalConditionLog, PersonnelCompetency, QualityControlRecord,
    # ISO 17025 — 7.9 Complaints + 7.10 Non-conforming Work
    Complaint, NonConformingWork, InternalAudit, AuditFinding,
    ManagementReview, ManagementReviewAction,
    RiskRegister, Opportunity,
    ControlledDocument, DocumentVersion, DocumentChangeLog,
    RecordRetentionPolicy,
    MethodValidation, MethodValidationParameter,
    ReferenceStandard, ReferenceStandardUsage,
    # پیام‌رسانی
    Message, Notification,
    # Excel
    ExcelImportBatch, ExcelRawRow,
    # تصاویر و حدود
    SampleImage, Specification,
    CompanyInfo,
    CertificateTemplate,
)


# ==========================================================
# اکشن: خروجی اکسل جامع از درخواست‌ها
# ==========================================================
def export_requests_to_excel(modeladmin, request, queryset):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "درخواست‌ها"
    ws.sheet_view.rightToLeft = True

    headers = [
        'کد رهگیری', 'واحد', 'ثبت‌کننده', 'نام قطعه', 'شناسه',
        'جنس', 'استاندارد', 'تعداد کشش', 'Re', 'Rm', 'A%',
        'تعداد ضربه', 'میانگین ضربه', 'کمینه ضربه',
        'میانگین سختی', 'CE', 'وضعیت', 'تاریخ',
    ]
    ws.append(headers)

    for r in queryset:
        t = r.tensile_results.first()
        i = r.impact_results.first()
        h = r.hardness_results.first()
        c = r.chemical_results.first()

        ws.append([
            r.tracking_code or '—',
            r.department.name if r.department else '',
            r.requester.get_full_name() or r.requester.username,
            r.sample_name, r.sample_code, r.material_grade, r.standard_name,
            r.tensile_results.count(),
            t.yield_strength_re if t else '-',
            t.tensile_strength_rm if t else '-',
            t.elongation_a if t else '-',
            r.impact_results.count(),
            i.average_energy if i else '-',
            i.min_energy if i else '-',
            f"{h.average_hardness} {h.scale}" if h else '-',
            c.carbon_equivalent if c else '-',
            r.get_status_display(),
            r.created_at_shamsi,
        ])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="Mechanical_Requests.xlsx"'
    wb.save(response)
    return response


export_requests_to_excel.short_description = "📥 دریافت اکسل از موارد انتخاب‌شده"


# ==========================================================
# گردش‌کار
# ==========================================================
@admin.register(TestRequest)
class TestRequestAdmin(admin.ModelAdmin):
    list_display = (
        'tracking_code_display', 'sample_name', 'department',
        'material_grade', 'urgency', 'status_colored', 'created_at_shamsi',
    )
    list_filter = ('status', 'urgency', 'department', 'needs_machining')
    search_fields = ('tracking_code', 'sample_name', 'sample_code', 'material_grade')
    readonly_fields = ('created_at', 'updated_at', 'received_at')
    actions = [export_requests_to_excel]
    filter_horizontal = ('selected_categories', 'selected_sub_tests')

    fieldsets = (
        ('شماره‌گذاری گزارش', {'fields': ('report_prefix', 'last_report_seq')}),
        ('اطلاعات اصلی', {
            'fields': ('tracking_code', 'department', 'requester', 'status',
                       'urgency', 'urgency_reason', 'automation_letter_no', 'internal_request_no')
        }),
        ('مشخصات قطعه', {
            'fields': ('sample_name', 'sample_code', 'sample_dimensions',
                       'material_grade', 'standard_name', 'heat_number', 'order_group')
        }),
        ('آزمون‌های درخواستی', {
            'fields': ('selected_categories', 'selected_sub_tests',
                       'impact_temperature', 'other_tests_description')
        }),
        ('شرایط', {
            'fields': ('destruction_status', 'sample_return_status',
                       'test_presence_type', 'witness_name', 'witness_phone')
        }),
        ('نمونه‌سازی و توضیحات', {
            'fields': ('needs_machining', 'machining_notes',
                       'description', 'attachment', 'custom_field_values', 'return_reason')
        }),
        ('تحویل و پذیرش نمونه', {
            'fields': ('sample_receipt_status', 'sample_condition_at_receipt',
                       'sample_storage_location', 'sample_received_by',
                       'sample_received_at', 'sample_acceptance_comment')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at', 'received_at'),
            'classes': ('collapse',)
        }),
    )

    def tracking_code_display(self, obj):
        return obj.tracking_code or '— در انتظار —'
    tracking_code_display.short_description = 'کد رهگیری'

    def status_colored(self, obj):
        colors = {
            'draft': '#6b7280', 'submitted': '#0891b2', 'received': '#1d4ed8',
            'testing': '#d97706', 'outsourced': '#374151', 'review': '#0891b2',
            'completed': '#16a34a', 'returned': '#dc2626', 'rejected': '#dc2626',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'


@admin.register(RequestAssignment)
class RequestAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'request', 'lab_section', 'approval_status_colored',
        'supervisor', 'supervisor_approved_at', 'created_at',
    )
    list_filter = ('approval_status', 'lab_section')
    search_fields = ('request__tracking_code', 'request__sample_name', 'lab_section__name')
    readonly_fields = ('created_at', 'supervisor_approved_at')
    filter_horizontal = ('assigned_items', 'assigned_categories')
    autocomplete_fields = ('request', 'lab_section', 'supervisor')

    def approval_status_colored(self, obj):
        colors = {
            'pending':   '#6b7280',
            'accepted':  '#0891b2',
            'submitted': '#d97706',
            'approved':  '#16a34a',
            'rejected':  '#dc2626',
        }
        color = colors.get(obj.approval_status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_approval_status_display()
        )
    approval_status_colored.short_description = 'وضعیت تایید'


@admin.register(RequestHistory)
class RequestHistoryAdmin(admin.ModelAdmin):
    list_display = ('request', 'from_status', 'to_status', 'user', 'timestamp')
    list_filter = ('from_status', 'to_status')
    search_fields = ('request__tracking_code', 'comment')
    readonly_fields = ('timestamp',)


# ==========================================================
# پایه
# ==========================================================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_external', 'contact_person', 'phone', 'created_at')
    list_filter = ('is_external',)
    search_fields = ('name', 'code', 'contact_person')


@admin.register(TestCategory)
class TestCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'standard_code', 'order', 'is_default', 'is_active')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name', 'code')


@admin.register(TestItem)
class TestItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'standard_code', 'order', 'is_default', 'is_active')
    list_filter = ('category', 'is_active', 'is_default')
    search_fields = ('name', 'standard_code')
    autocomplete_fields = ('category',)


@admin.register(LabSection)
class LabSectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_external', 'is_active')
    list_filter = ('is_external', 'is_active')
    search_fields = ('name', 'code')
    filter_horizontal = ('allowed_categories', 'allowed_items')


# ══════════════════════════════════════════════════════════════
# گروه‌بندی مجوزها برای نمایش گرافیکی
# ══════════════════════════════════════════════════════════════
PERMISSION_GROUPS = {
    '🔧 گردش‌کار اصلی': [
        'can_create_request', 'view_own_requests', 'view_reception',
        'can_accept_request', 'can_assign_tasks', 'can_reject_request',
        'can_export_excel', 'view_operator', 'can_enter_results',
        'view_supervisor', 'can_approve_results', 'view_final_review',
        'can_final_approve', 'can_print_report', 'view_all_requests',
    ],
    '⚙️ مدیریت سیستم': [
        'manage_users', 'manage_equipment', 'manage_standards',
    ],
    '📋 QMS — ISO 17025': [
        'view_complaints', 'manage_complaints',
        'view_ncr', 'manage_ncr',
        'view_audits', 'manage_audits',
        'view_reviews', 'manage_reviews',
        'view_risks', 'manage_risks',
        'view_documents', 'manage_documents',
        'view_records', 'manage_records',
        'view_validations', 'manage_validations',
        'view_references', 'manage_references',
    ],
}


class PermissionsWidget(forms.Widget):
    """ویجت اختصاصی: نمایش مجوزها به‌صورت checkbox با تیک‌های پیش‌فرض نقش."""

    def render(self, name, value, attrs=None, renderer=None):
        from .models import ALL_PERMISSIONS, ROLE_DEFAULT_PERMISSIONS

        overrides = value if isinstance(value, dict) else {}
        role = self.attrs.get('role', '')
        role_perms = set(ROLE_DEFAULT_PERMISSIONS.get(role, []))

        overrides_json = json.dumps(overrides, ensure_ascii=False)
        role_perms_json = json.dumps(sorted(role_perms), ensure_ascii=False)

        parts = []
        parts.append(
            '<div class="perm-widget" '
            'style="background:#f8fafc;padding:16px;border-radius:10px;border:1px solid #e2e8f0;">'
        )
        parts.append(
            '<div style="margin-bottom:14px;font-size:0.85rem;color:#475569;'
            'display:flex;gap:16px;flex-wrap:wrap;">'
            f'<span>نقش فعلی: <b style="color:#1e3a8a;">{role or "تعیین نشده"}</b></span>'
            '<span style="color:#16a34a;font-weight:700;">✅ پیش‌فرض نقش</span>'
            '<span style="color:#d97706;font-weight:700;">🟡 override دستی</span>'
            '<span style="color:#94a3b8;">⬜ خارج از نقش</span>'
            '</div>'
        )
        parts.append(f'<input type="hidden" name="{name}" id="id_{name}" value="">')

        for group_name, codes in PERMISSION_GROUPS.items():
            parts.append('<div style="margin-top:16px;">')
            parts.append(
                f'<div style="font-weight:800;color:#1e3a8a;margin-bottom:8px;'
                f'font-size:0.92rem;">{group_name}</div>'
            )
            parts.append(
                  '<div style="display:grid;'
                  'grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:4px;">'
            )
            for code in codes:
                if code not in ALL_PERMISSIONS:
                    continue
                label = ALL_PERMISSIONS[code]
                in_role = code in role_perms
                is_override = code in overrides

                if is_override:
                    checked = bool(overrides[code])
                    marker, color = '🟡', '#d97706'
                elif in_role:
                    checked, marker, color = True, '✅', '#16a34a'
                else:
                    checked, marker, color = False, '⬜', '#94a3b8'

                checked_attr = 'checked' if checked else ''
                parts.append(
                     f'<label title="{label} — {code}" '
                     f'style="display:flex;align-items:center;gap:5px;'
                     f'padding:5px 7px;border-radius:5px;background:#fff;'
                     f'border:1px solid #e2e8f0;cursor:pointer;font-size:0.76rem;'
                     f'line-height:1.2;">'
                     f'<input type="checkbox" class="perm-cb" data-code="{code}" '
                     f'{checked_attr} style="flex-shrink:0;">'
                     f'<span style="color:{color};font-weight:700;flex-shrink:0;">{marker}</span>'
                     f'<span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                     f'{label}</span></label>'
                 )
            parts.append('</div></div>')

        parts.append('</div>')

        # JS: تبدیل checkboxها به JSON override
        parts.append(f'''
<script>
(function() {{
    var hidden = document.getElementById('id_{name}');
    if (!hidden) return;
    var checkboxes = document.querySelectorAll('.perm-cb');
    var rolePerms = {role_perms_json};

    function syncHidden() {{
        var result = {{}};
        checkboxes.forEach(function(cb) {{
            var code = cb.getAttribute('data-code');
            var inRole = rolePerms.indexOf(code) !== -1;
            if (cb.checked !== inRole) {{
                result[code] = cb.checked;
            }}
        }});
        hidden.value = JSON.stringify(result);
    }}

    checkboxes.forEach(function(cb) {{
        cb.addEventListener('change', syncHidden);
    }});
    syncHidden();
}})();
</script>
''')

        return mark_safe(''.join(parts))


class UserProfileForm(forms.ModelForm):
    permissions = forms.JSONField(
        required=False,
        widget=PermissionsWidget,
        label='',
        help_text='',
    )

    class Meta:
        model = UserProfile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        role = ''
        if self.instance and self.instance.pk:
            role = self.instance.role or ''
        self.fields['permissions'].widget.attrs['role'] = role


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "role":
            from .models import RoleTitle
            choices = []
            for code, default_label in db_field.get_choices(include_blank=False):
                try:
                    title_obj = RoleTitle.objects.get(code=code)
                    label = title_obj.title
                except RoleTitle.DoesNotExist:
                    label = default_label
                choices.append((code, label))
            kwargs['choices'] = choices
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    form = UserProfileForm
    list_display = ('user', 'role', 'department', 'lab_section', 'personnel_code')
    list_filter = ('role', 'department', 'lab_section')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'personnel_code')
    filter_horizontal = ('extra_categories', 'supervised_labs')
    autocomplete_fields = ('user', 'department', 'lab_section')

    fieldsets = (
        ('👤 اطلاعات کاربر', {
            'fields': ('user', 'department', 'personnel_code', 'phone')
        }),
        ('🔑 نقش و آزمایشگاه', {
            'fields': ('role', 'lab_section', 'supervised_labs', 'extra_categories'),
            'description': 'با تغییر نقش و ذخیره، مجوزهای پیش‌فرض نقش به‌طور خودکار اعمال می‌شوند.'
        }),
        ('📋 مجوزهای اختصاصی (override)', {
            'fields': ('permissions',),
            'description': (
                '✅ پیش‌فرض نقش · 🟡 دستی تغییر یافته · ⬜ خارج از نقش — '
                'هر تیکی که با پیش‌فرض نقش تفاوت داشته باشد، به‌عنوان override ذخیره می‌شود.'
            )
        }),
    )


# ══════════════════════════════════════════════════════════════
# User Admin ساده‌شده (بدون Groups و user_permissions)
# ══════════════════════════════════════════════════════════════
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """User admin ساده‌شده — بدون Groups و Permissions پیش‌فرض Django."""

    list_display = ('username', 'get_full_name', 'email', 'is_active', 'get_role')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    fieldsets = (
        ('🔐 اطلاعات ورود', {
            'fields': ('username', 'password')
        }),
        ('👤 اطلاعات شخصی', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('⚙️ دسترسی‌های سیستم', {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
            'description': (
                'برای تنظیم نقش، آزمایشگاه و مجوزها، به بخش '
                '«پروفایل کاربران» (User profiles) بروید.'
            )
        }),
        ('📅 تاریخ‌های مهم', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        ('ایجاد کاربر جدید', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2',
                       'first_name', 'last_name', 'email'),
        }),
    )

    def get_role(self, obj):
        p = getattr(obj, 'profile', None)
        if not p:
            return '—'
        return p.get_role_display()
    get_role.short_description = 'نقش'


@admin.register(MaterialSuggestion)
class MaterialSuggestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'standard')
    search_fields = ('name', 'standard')


@admin.register(DynamicField)
class DynamicFieldAdmin(admin.ModelAdmin):
    list_display = ('label', 'field_type', 'is_required', 'display_order', 'is_active')
    list_filter = ('field_type', 'is_required', 'is_active')
    search_fields = ('label', 'options')


# ==========================================================
# نتایج آزمون‌ها
# ==========================================================
@admin.register(TensileTestResult)
class TensileTestResultAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'sample_label', 'probe_shape',
        'yield_strength_re', 'tensile_strength_rm',
        'elongation_a', 'reduction_of_area_z',
    )
    list_filter = ('probe_shape', 'input_mode', 'yield_strength_type')
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(ImpactTestResult)
class ImpactTestResultAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'sample_label', 'test_temperature', 'specimen_status',
        'average_energy', 'min_energy', 'max_energy',
    )
    list_filter = ('specimen_status',)
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(HardnessTestResult)
class HardnessTestResultAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'sample_label', 'scale',
        'average_hardness', 'min_hardness', 'max_hardness',
    )
    list_filter = ('scale',)
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(ChemicalAnalysisResult)
class ChemicalAnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('request', 'sample_label', 'method_name', 'carbon_equivalent')
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(BendTestResult)
class BendTestResultAdmin(admin.ModelAdmin):
    list_display = ('request', 'sample_label', 'mandrel_diameter', 'bend_angle', 'result_status')
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(FlatteningTestResult)
class FlatteningTestResultAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'sample_label', 'initial_outer_diameter',
        'final_plate_distance', 'flatten_ratio', 'result_status',
    )
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(FlaringTestResult)
class FlaringTestResultAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'sample_label', 'initial_outer_diameter',
        'expanded_diameter', 'expansion_percent', 'result_status',
    )
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(MetallographyResult)
class MetallographyResultAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'sample_label', 'grain_size_astm',
        'microhardness_scale', 'microhardness_average',
    )
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request', 'microscope_equipment')


@admin.register(ForceTestResult)
class ForceTestResultAdmin(admin.ModelAdmin):
    list_display = ('request', 'sample_label', 'test_type', 'max_force_kn', 'result_status')
    list_filter = ('test_type',)
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(CorrosionTestResult)
class CorrosionTestResultAdmin(admin.ModelAdmin):
    list_display = ('request', 'sample_label', 'test_method',
                    'duration_hours', 'evaluation', 'corrosion_rate')
    list_filter = ('test_method',)
    search_fields = ('request__tracking_code', 'sample_label')
    autocomplete_fields = ('request',)


@admin.register(PMIResult)
class PMIResultAdmin(admin.ModelAdmin):
    list_display = ('request', 'sample_label', 'device_name', 'estimated_grade', 'result_status')
    search_fields = ('request__tracking_code', 'sample_label', 'estimated_grade')
    autocomplete_fields = ('request',)


@admin.register(GeneralTestResult)
class GeneralTestResultAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'test_category', 'test_item', 'sample_label',
        'measured_value', 'unit', 'standard_uncertainty',
        'expanded_uncertainty', 'result_status',
    )
    list_filter = ('test_category', 'result_status')
    search_fields = ('request__tracking_code', 'sample_label', 'standard_ref')
    autocomplete_fields = ('request', 'test_category', 'test_item')


# ==========================================================
# استانداردها و تجهیزات
# ==========================================================
@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'year', 'revision', 'is_default', 'is_active')
    list_filter = ('is_active', 'is_default')
    search_fields = ('code', 'title')


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'model_name', 'serial_no', 'asset_no',
        'calibration_interval_months', 'calibration_status',
        'is_default', 'is_active',
    )
    list_filter = ('is_active', 'is_default', 'calibration_status')
    search_fields = ('name', 'code', 'asset_no', 'serial_no', 'model_name')


# ==========================================================
# کالیبراسیون
# ==========================================================
@admin.register(CalibrationLimit)
class CalibrationLimitAdmin(admin.ModelAdmin):
    list_display = (
        'instrument_type', 'parameter', 'unit', 'accuracy_class',
        'range_min', 'range_max', 'mpe_value', 'mpe_type',
        'decision_rule', 'is_active',
    )
    list_filter = ('mpe_type', 'decision_rule', 'is_active')
    search_fields = ('instrument_type', 'parameter', 'standard__code',
                     'standard__title', 'source_clause', 'condition')
    autocomplete_fields = ('standard',)


@admin.register(CalibrationUncertaintyComponent)
class CalibrationUncertaintyComponentAdmin(admin.ModelAdmin):
    list_display = (
        'result', 'name', 'component_type', 'distribution',
        'value', 'divisor', 'sensitivity',
        'standard_uncertainty', 'contribution', 'degrees_of_freedom',
    )
    list_filter = ('component_type', 'distribution')
    search_fields = ('name', 'result__request__tracking_code', 'source')
    autocomplete_fields = ('result',)


@admin.register(CalibrationResult)
class CalibrationResultAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'sample_label', 'equipment', 'equipment_name_free',
        'calibration_date', 'next_due_date', 'result_status',
        'range_min', 'range_max',
    )
    search_fields = ('request__tracking_code', 'sample_label', 'equipment_name_free')
    autocomplete_fields = ('request', 'equipment', 'calibration_limit')


@admin.register(ConformityDecision)
class ConformityDecisionAdmin(admin.ModelAdmin):
    list_display = (
        'request', 'parameter', 'measured_value',
        'lower_limit', 'upper_limit', 'expanded_uncertainty',
        'decision_rule', 'status', 'is_current', 'created_at',
    )
    list_filter = ('status', 'decision_rule', 'is_current')
    search_fields = ('request__tracking_code', 'parameter', 'message',
                     'standard_reference', 'standard_revision')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('request', 'calibration_result', 'specification')


@admin.register(TestUncertaintyProfile)
class TestUncertaintyProfileAdmin(admin.ModelAdmin):
    list_display = (
        'test_category', 'test_item', 'parameter', 'unit',
        'standard_uncertainty', 'expanded_uncertainty',
        'coverage_factor', 'review_date', 'is_active',
    )
    list_filter = ('test_category', 'is_active')
    search_fields = ('parameter', 'method_version', 'standard_revision', 'source_clause')
    autocomplete_fields = ('test_category', 'test_item', 'standard')


# ==========================================================
# ISO/IEC 17025 — کنترل‌های تکمیلی
# ==========================================================
@admin.register(EquipmentCheck)
class EquipmentCheckAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'check_type', 'performed_at', 'result_status', 'checked_by')
    list_filter = ('check_type', 'result_status')
    search_fields = ('equipment__name', 'equipment__code', 'standard_ref', 'certificate_no')
    autocomplete_fields = ('equipment', 'checked_by')


@admin.register(EnvironmentalConditionLog)
class EnvironmentalConditionLogAdmin(admin.ModelAdmin):
    list_display = ('lab_section', 'recorded_at', 'temperature', 'humidity', 'recorded_by')
    list_filter = ('lab_section',)
    autocomplete_fields = ('lab_section', 'recorded_by')


@admin.register(PersonnelCompetency)
class PersonnelCompetencyAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'lab_section', 'test_category',
        'competency_status', 'assessed_at', 'valid_until',
    )
    list_filter = ('lab_section', 'competency_status')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'method_standard')
    autocomplete_fields = ('user', 'lab_section', 'test_category', 'test_item', 'assessed_by')


@admin.register(QualityControlRecord)
class QualityControlRecordAdmin(admin.ModelAdmin):
    list_display = (
        'qc_type', 'test_category', 'analyte_or_parameter',
        'measured_value', 'result_status', 'performed_at', 'performed_by',
    )
    list_filter = ('qc_type', 'result_status', 'test_category')
    search_fields = ('request__tracking_code', 'analyte_or_parameter', 'standard_ref')
    autocomplete_fields = ('request', 'test_category', 'performed_by', 'equipment')


# ==========================================================
# ISO/IEC 17025 — 7.9 Complaints (شکایات)
# ==========================================================
@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        'complaint_no', 'complainant_name', 'category', 'severity',
        'status_colored', 'received_date', 'assigned_to',
    )
    list_filter = ('status', 'category', 'severity', 'source', 'is_valid')
    search_fields = ('complaint_no', 'complainant_name', 'description',
                     'request__tracking_code')
    readonly_fields = ('created_at', 'updated_at', 'acknowledged_at',
                       'resolved_at', 'closed_at')
    date_hierarchy = 'received_date'
    autocomplete_fields = ('department', 'request', 'assigned_to',
                          'handled_by', 'closed_by')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('complaint_no', 'source', 'category', 'severity',
                       'status', 'received_date')
        }),
        ('شاکی و ارتباطات', {
            'fields': ('complainant_name', 'complainant_contact',
                       'department', 'request')
        }),
        ('شرح شکایت', {
            'fields': ('description',)
        }),
        ('بررسی و اقدام', {
            'fields': ('investigation', 'root_cause',
                       'corrective_action', 'preventive_action',
                       'resolution_summary')
        }),
        ('مسئولیت‌ها', {
            'fields': ('assigned_to', 'handled_by')
        }),
        ('نتیجه', {
            'fields': ('is_valid', 'customer_satisfied',
                       'acknowledged_at', 'resolved_at',
                       'closed_at', 'closed_by')
        }),
        ('توضیحات تکمیلی', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'received':      '#6b7280',
            'investigating': '#0891b2',
            'action':        '#d97706',
            'resolved':      '#16a34a',
            'rejected':      '#dc2626',
            'closed':        '#374151',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'


# ==========================================================
# ISO/IEC 17025 — 7.10 Non-conforming Work + CAPA
# ==========================================================
@admin.register(NonConformingWork)
class NonConformingWorkAdmin(admin.ModelAdmin):
    list_display = (
        'nc_no', 'title', 'source', 'severity',
        'status_colored', 'discovered_at', 'assigned_to',
    )
    list_filter = ('status', 'severity', 'source', 'work_stopped', 'effectiveness_verified')
    search_fields = ('nc_no', 'title', 'description', 'related_request__tracking_code')
    readonly_fields = ('created_at', 'updated_at', 'discovered_at',
                       'resolved_at', 'verified_at', 'closed_at')
    date_hierarchy = 'discovered_at'
    autocomplete_fields = ('discovered_by', 'department', 'lab_section',
                          'related_request', 'related_complaint',
                          'assigned_to', 'handled_by', 'closed_by')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('nc_no', 'title', 'source', 'severity', 'status',
                       'discovered_at', 'discovered_by')
        }),
        ('ارتباطات', {
            'fields': ('department', 'lab_section',
                       'related_request', 'related_complaint')
        }),
        ('شرح و ارزیابی', {
            'fields': ('description', 'work_stopped',
                       'immediate_action', 'impact_assessment')
        }),
        ('ریشه‌یابی و اقدامات', {
            'fields': ('root_cause', 'corrective_action', 'preventive_action')
        }),
        ('بررسی اثربخشی', {
            'fields': ('effectiveness_check', 'effectiveness_verified',
                       'verified_at')
        }),
        ('مسئولیت‌ها', {
            'fields': ('assigned_to', 'handled_by', 'target_date')
        }),
        ('نتیجه', {
            'fields': ('resolved_at', 'closed_at', 'closed_by', 'notes')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'reported':      '#6b7280',
            'investigating': '#0891b2',
            'action':        '#d97706',
            'verified':      '#16a34a',
            'closed':        '#374151',
            'cancelled':     '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'


# ==========================================================
# پیام‌رسانی
# ==========================================================
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'level_colored', 'title', 'is_read', 'created_at_shamsi')
    list_filter = ('level', 'is_read')
    search_fields = ('user__username', 'title', 'message')
    actions = ['mark_as_read', 'mark_as_unread']
    autocomplete_fields = ('user',)

    def level_colored(self, obj):
        colors = {
            'info': '#0891b2', 'success': '#16a34a',
            'warning': '#d97706', 'danger': '#dc2626',
        }
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:5px;font-size:0.78rem;">{}</span>',
            colors.get(obj.level, '#6b7280'), obj.get_level_display()
        )
    level_colored.short_description = 'سطح'

    def created_at_shamsi(self, obj):
        return obj.created_at_shamsi
    created_at_shamsi.short_description = 'زمان'

    @admin.action(description="علامت‌گذاری به‌عنوان خوانده‌شده")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="علامت‌گذاری به‌عنوان خوانده‌نشده")
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'subject', 'is_read', 'created_at_shamsi')
    list_filter = ('is_read',)
    search_fields = ('subject', 'body', 'sender__username', 'recipient__username')
    readonly_fields = ('created_at', 'read_at')
    autocomplete_fields = ('sender', 'recipient', 'parent')


# ==========================================================
# Excel
# ==========================================================
@admin.register(ExcelImportBatch)
class ExcelImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        'file_name', 'sheet_name', 'total_rows', 'new_rows',
        'duplicate_rows', 'error_rows', 'status', 'created_at_shamsi',
    )
    list_filter = ('status',)
    search_fields = ('file_name', 'sheet_name')
    readonly_fields = ('created_at', 'finished_at')
    autocomplete_fields = ('uploaded_by',)


@admin.register(ExcelRawRow)
class ExcelRawRowAdmin(admin.ModelAdmin):
    list_display = ('id', 'row_number', 'tracking_code', 'report_number', 'batch', 'processed')
    list_filter = ('processed', 'batch')
    search_fields = ('tracking_code', 'report_number')
    autocomplete_fields = ('batch', 'request')


# ==========================================================
# تصاویر و حدود مجاز
# ==========================================================
@admin.register(SampleImage)
class SampleImageAdmin(admin.ModelAdmin):
    list_display = ('request', 'caption', 'stage', 'uploaded_by', 'created_at_shamsi')
    list_filter = ('stage', 'created_at')
    search_fields = ('request__tracking_code', 'caption')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('request', 'uploaded_by')


@admin.register(Specification)
class SpecificationAdmin(admin.ModelAdmin):
    list_display = (
        'product_standard', 'standard_revision', 'test_category',
        'material_grade', 'parameter', 'range_display', 'is_active',
    )
    list_filter = ('is_active', 'test_category', 'product_standard')
    search_fields = ('product_standard', 'material_grade', 'parameter', 'notes')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('test_category', 'standard', 'created_by')


# ==========================================================
# ISO/IEC 17025 — 8.8 Internal Audits (ممیزی داخلی)
# ==========================================================
class AuditFindingInline(admin.TabularInline):
    model = AuditFinding
    extra = 0
    fields = ('finding_no', 'finding_type', 'iso_clause', 'description',
              'nc_work', 'status', 'responsible', 'due_date')
    readonly_fields = ('finding_no',)
    autocomplete_fields = ('nc_work', 'responsible')
    show_change_link = True


@admin.register(InternalAudit)
class InternalAuditAdmin(admin.ModelAdmin):
    list_display = (
        'audit_no', 'title', 'audit_type', 'status_colored',
        'scheduled_date', 'performed_date', 'lead_auditor',
        'findings_count',
    )
    list_filter = ('status', 'audit_type', 'scheduled_date')
    search_fields = ('audit_no', 'title', 'scope', 'criteria')
    readonly_fields = ('created_at', 'updated_at', 'reviewed_at', 'closed_at')
    date_hierarchy = 'scheduled_date'
    filter_horizontal = ('auditors', 'auditees', 'lab_sections')
    autocomplete_fields = ('lead_auditor', 'reviewed_by', 'closed_by')
    inlines = [AuditFindingInline]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('audit_no', 'title', 'audit_type', 'status')
        }),
        ('دامنه و معیارها', {
            'fields': ('scope', 'criteria')
        }),
        ('زمان‌بندی', {
            'fields': ('scheduled_date', 'performed_date')
        }),
        ('تیم ممیزی', {
            'fields': ('lead_auditor', 'auditors', 'auditees')
        }),
        ('یافته‌ها و نتیجه‌گیری', {
            'fields': ('findings_summary', 'conclusion', 'recommendations')
        }),
        ('گزارش', {
            'fields': ('report_file',)
        }),
        ('بازنگری و بستن', {
            'fields': ('reviewed_by', 'reviewed_at', 'closed_by', 'closed_at')
        }),
        ('توضیحات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'planned':     '#6b7280',
            'in_progress': '#0891b2',
            'completed':   '#d97706',
            'reviewed':    '#16a34a',
            'closed':      '#374151',
            'cancelled':   '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'

    def labs_display(self, obj):
        labs = list(obj.lab_sections.values_list('name', flat=True))
        return '، '.join(labs) if labs else '—'
    labs_display.short_description = 'آزمایشگاه‌ها'

    def findings_count(self, obj):
        return obj.findings.count()
    findings_count.short_description = 'تعداد یافته'


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = (
        'audit', 'finding_no', 'finding_type_colored',
        'iso_clause', 'status', 'responsible', 'due_date',
    )
    list_filter = ('finding_type', 'status', 'audit')
    search_fields = ('finding_no', 'description', 'evidence', 'iso_clause',
                     'audit__audit_no')
    readonly_fields = ('created_at', 'updated_at', 'closed_at', 'finding_no')
    autocomplete_fields = ('audit', 'nc_work', 'responsible')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('audit', 'finding_no', 'finding_type', 'iso_clause', 'status')
        }),
        ('شرح یافته', {
            'fields': ('description', 'evidence')
        }),
        ('اقدام', {
            'fields': ('corrective_action', 'responsible', 'due_date', 'nc_work')
        }),
        ('نتیجه', {
            'fields': ('closed_at',)
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def finding_type_colored(self, obj):
        colors = {
            'conformity':  '#16a34a',
            'nc_minor':    '#d97706',
            'nc_major':    '#dc2626',
            'observation': '#0891b2',
            'improvement': '#6b7280',
        }
        color = colors.get(obj.finding_type, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_finding_type_display()
        )
    finding_type_colored.short_description = 'نوع یافته'


# ==========================================================
# ISO/IEC 17025 — 8.9 Management Review (بازنگری مدیریت)
# ==========================================================
class ManagementReviewActionInline(admin.TabularInline):
    model = ManagementReviewAction
    extra = 0
    fields = ('action_no', 'action_type', 'description', 'responsible',
              'due_date', 'status')
    readonly_fields = ('action_no',)
    autocomplete_fields = ('responsible',)
    show_change_link = True


@admin.register(ManagementReview)
class ManagementReviewAdmin(admin.ModelAdmin):
    list_display = (
        'review_no', 'title', 'review_type', 'status_colored',
        'scheduled_date', 'meeting_date', 'chairperson',
        'actions_count',
    )
    list_filter = ('status', 'review_type', 'scheduled_date')
    search_fields = ('review_no', 'title', 'agenda', 'conclusions')
    readonly_fields = ('created_at', 'updated_at', 'closed_at')
    date_hierarchy = 'scheduled_date'
    filter_horizontal = ('attendees',)
    autocomplete_fields = ('chairperson', 'secretary', 'created_by', 'closed_by')
    inlines = [ManagementReviewActionInline]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('review_no', 'title', 'review_type', 'status')
        }),
        ('زمان و مکان', {
            'fields': ('scheduled_date', 'meeting_date', 'next_review_date', 'location')
        }),
        ('حضار', {
            'fields': ('chairperson', 'secretary', 'attendees')
        }),
        ('دستور جلسه', {
            'fields': ('agenda',)
        }),
        ('📥 ورودی‌های بازنگری (بند 8.9.2)', {
            'fields': (
                'changes_internal_external',
                'fulfillment_objectives',
                'suitability_policies_procedures',
                'status_actions_prev_reviews',
                'audit_results',
                'nonconformities_capa',
                'complaints_feedback',
                'resource_adequacy',
                'risk_opportunities',
                'results_interlab',
                'other_factors',
            ),
            'classes': ('collapse',)
        }),
        ('📤 خروجی‌های بازنگری (بند 8.9.3)', {
            'fields': (
                'conclusions',
                'improvement_opportunities',
                'system_changes_needed',
                'resource_needs',
            ),
            'classes': ('collapse',)
        }),
        ('صورت‌جلسه و توضیحات', {
            'fields': ('minutes_file', 'notes')
        }),
        ('وضعیت نهایی', {
            'fields': ('created_by', 'closed_by', 'closed_at'),
            'classes': ('collapse',)
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'draft':       '#6b7280',
            'scheduled':   '#0891b2',
            'in_progress': '#d97706',
            'completed':   '#16a34a',
            'closed':      '#374151',
            'cancelled':   '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'

    def actions_count(self, obj):
        return obj.actions.count()
    actions_count.short_description = 'تعداد اقدام'


@admin.register(ManagementReviewAction)
class ManagementReviewActionAdmin(admin.ModelAdmin):
    list_display = (
        'review', 'action_no', 'action_type_colored',
        'responsible', 'due_date', 'status',
    )
    list_filter = ('action_type', 'status', 'review')
    search_fields = ('action_no', 'description', 'review__review_no', 'review__title')
    readonly_fields = ('created_at', 'updated_at', 'closed_at', 'action_no')
    autocomplete_fields = ('review', 'responsible')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('review', 'action_no', 'action_type', 'status')
        }),
        ('شرح اقدام', {
            'fields': ('description', 'expected_outcome')
        }),
        ('مسئولیت و زمان', {
            'fields': ('responsible', 'due_date')
        }),
        ('پیشرفت و اثربخشی', {
            'fields': ('progress_notes', 'effectiveness_check', 'closed_at')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def action_type_colored(self, obj):
        colors = {
            'improvement': '#0891b2',
            'corrective':  '#dc2626',
            'preventive':  '#d97706',
            'resource':    '#16a34a',
            'system':      '#7c3aed',
            'other':       '#6b7280',
        }
        color = colors.get(obj.action_type, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_action_type_display()
        )
    action_type_colored.short_description = 'نوع اقدام'


# ==========================================================
# ISO/IEC 17025 — 8.5 Risk & Opportunities
# ==========================================================
@admin.register(RiskRegister)
class RiskRegisterAdmin(admin.ModelAdmin):
    list_display = (
        'risk_no', 'title', 'category', 'source',
        'risk_level_colored', 'risk_score',
        'status', 'owner', 'target_date',
    )
    list_filter = ('status', 'risk_level', 'category', 'source')
    search_fields = ('risk_no', 'title', 'description', 'mitigation_plan')
    readonly_fields = ('created_at', 'updated_at', 'closed_at',
                       'risk_score', 'risk_level', 'residual_score')
    date_hierarchy = 'identified_at'
    autocomplete_fields = ('owner', 'identified_by', 'closed_by',
                          'related_nc', 'related_complaint', 'related_review')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('risk_no', 'title', 'category', 'source', 'status')
        }),
        ('شرح ریسک', {
            'fields': ('description',)
        }),
        ('ارزیابی اولیه', {
            'fields': ('probability', 'impact', 'risk_score', 'risk_level')
        }),
        ('کنترل و کاهش', {
            'fields': ('existing_controls', 'mitigation_plan')
        }),
        ('ارزیابی باقیمانده', {
            'fields': ('residual_probability', 'residual_impact', 'residual_score')
        }),
        ('ارتباطات', {
            'fields': ('related_nc', 'related_complaint', 'related_review')
        }),
        ('مسئولیت و زمان‌بندی', {
            'fields': ('owner', 'identified_by', 'identified_at',
                       'target_date', 'review_date')
        }),
        ('بستن', {
            'fields': ('closed_at', 'closed_by', 'notes')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def risk_level_colored(self, obj):
        colors = {
            'low':      '#16a34a',
            'medium':   '#d97706',
            'high':     '#ea580c',
            'critical': '#dc2626',
        }
        color = colors.get(obj.risk_level, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{} ({})</span>',
            color, obj.get_risk_level_display(), obj.risk_score
        )
    risk_level_colored.short_description = 'سطح ریسک'


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        'opp_no', 'title', 'category',
        'opportunity_score', 'status',
        'owner', 'target_date',
    )
    list_filter = ('status', 'category')
    search_fields = ('opp_no', 'title', 'description', 'action_plan')
    readonly_fields = ('created_at', 'updated_at', 'closed_at', 'opportunity_score')
    date_hierarchy = 'identified_at'
    autocomplete_fields = ('owner', 'identified_by', 'closed_by', 'related_review')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('opp_no', 'title', 'category', 'status')
        }),
        ('شرح فرصت', {
            'fields': ('description',)
        }),
        ('ارزیابی', {
            'fields': ('benefit_potential', 'feasibility', 'opportunity_score')
        }),
        ('برنامه اقدام', {
            'fields': ('action_plan', 'expected_outcome', 'actual_outcome')
        }),
        ('ارتباطات', {
            'fields': ('related_review',)
        }),
        ('مسئولیت و زمان‌بندی', {
            'fields': ('owner', 'identified_by', 'identified_at', 'target_date')
        }),
        ('بستن', {
            'fields': ('closed_at', 'closed_by', 'notes')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ==========================================================
# ISO/IEC 17025 — 8.4 Document Control (کنترل مدارک)
# ==========================================================
class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    fields = ('version', 'change_summary', 'approved_by', 'approved_at',
              'effective_date', 'is_current')
    readonly_fields = ()
    autocomplete_fields = ('approved_by',)
    show_change_link = True


@admin.register(ControlledDocument)
class ControlledDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'doc_no', 'title', 'doc_type', 'category',
        'current_version', 'status_colored',
        'owner', 'next_review_date', 'review_status',
    )
    list_filter = ('status', 'doc_type', 'category')
    search_fields = ('doc_no', 'title', 'summary', 'scope')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'effective_date'
    filter_horizontal = ('distribution_list',)
    autocomplete_fields = ('owner', 'approved_by', 'related_standard', 'created_by')
    inlines = [DocumentVersionInline]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('doc_no', 'title', 'doc_type', 'category', 'status', 'current_version')
        }),
        ('محتوا', {
            'fields': ('summary', 'scope')
        }),
        ('مسئولیت‌ها', {
            'fields': ('owner', 'approved_by', 'approved_at')
        }),
        ('تاریخ‌ها', {
            'fields': ('effective_date', 'review_interval_months', 'next_review_date')
        }),
        ('ارتباطات', {
            'fields': ('related_standard',)
        }),
        ('توزیع', {
            'fields': ('distribution_list', 'distribution_notes')
        }),
        ('فایل سند', {
            'fields': ('file',)
        }),
        ('توضیحات', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'draft':        '#6b7280',
            'under_review': '#d97706',
            'approved':     '#16a34a',
            'effective':    '#0891b2',
            'superseded':   '#9ca3af',
            'obsolete':     '#374151',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'

    def review_status(self, obj):
        if obj.is_due_for_review:
            return format_html('<span style="color:#dc2626;font-weight:700;">⚠️ سررسید</span>')
        if obj.is_expiring_soon:
            return format_html('<span style="color:#d97706;font-weight:700;">⏰ نزدیک</span>')
        return format_html('<span style="color:#16a34a;">✅</span>')
    review_status.short_description = 'بازنگری'


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'version', 'approved_by', 'approved_at',
        'effective_date', 'superseded_date', 'is_current',
    )
    list_filter = ('is_current', 'document')
    search_fields = ('document__doc_no', 'document__title', 'version', 'change_summary')
    readonly_fields = ('created_at',)
    autocomplete_fields = ('document', 'approved_by', 'created_by')


@admin.register(DocumentChangeLog)
class DocumentChangeLogAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'change_type', 'from_version', 'to_version',
        'changed_by', 'changed_at',
    )
    list_filter = ('change_type', 'document')
    search_fields = ('document__doc_no', 'document__title', 'description', 'reason')
    readonly_fields = ('changed_at',)
    autocomplete_fields = ('document', 'changed_by')


# ==========================================================
# ISO/IEC 17025 — 8.3 Records Control (کنترل سوابق)
# ==========================================================
@admin.register(RecordRetentionPolicy)
class RecordRetentionPolicyAdmin(admin.ModelAdmin):
    list_display = (
        'record_type_colored', 'retention_years', 'access_level',
        'storage_location', 'responsible', 'is_active',
    )
    list_filter = ('access_level', 'is_active', 'disposal_method')
    search_fields = ('record_type', 'title', 'description', 'storage_location')
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('responsible', 'created_by')

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('record_type', 'title', 'description', 'is_active')
        }),
        ('مدت نگهداری', {
            'fields': ('retention_years', 'retention_notes')
        }),
        ('محل و قالب نگهداری', {
            'fields': ('storage_location', 'storage_format', 'backup_frequency')
        }),
        ('دسترسی', {
            'fields': ('access_level', 'access_notes')
        }),
        ('امحا', {
            'fields': ('disposal_method', 'disposal_notes')
        }),
        ('مسئولیت', {
            'fields': ('responsible', 'created_by')
        }),
        ('الزامات قانونی', {
            'fields': ('legal_requirements',)
        }),
        ('بازنگری', {
            'fields': ('last_reviewed_at', 'next_review_at')
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def record_type_colored(self, obj):
        return format_html(
            '<strong>{}</strong>',
            obj.get_record_type_display()
        )
    record_type_colored.short_description = 'نوع سابقه'


# ==========================================================
# ISO/IEC 17025 — 7.2 Method Validation
# ==========================================================
class MethodValidationParameterInline(admin.TabularInline):
    model = MethodValidationParameter
    extra = 0
    fields = ('param_no', 'parameter_type', 'parameter_name', 'value',
              'unit', 'acceptance_criteria', 'meets_criteria')
    readonly_fields = ('param_no',)
    show_change_link = True


@admin.register(MethodValidation)
class MethodValidationAdmin(admin.ModelAdmin):
    list_display = (
        'validation_no', 'method_name', 'validation_type',
        'status_colored', 'test_category', 'standard',
        'is_fit_for_purpose', 'next_review_at', 'review_status',
    )
    list_filter = ('status', 'validation_type', 'is_fit_for_purpose', 'test_category')
    search_fields = ('validation_no', 'method_name', 'title',
                     'method_reference', 'scope')
    readonly_fields = ('created_at', 'updated_at', 'validation_no')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('test_category', 'test_item', 'standard',
                          'responsible', 'performed_by', 'approved_by', 'created_by')
    inlines = [MethodValidationParameterInline]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('validation_no', 'title', 'method_name', 'method_version',
                       'method_reference', 'validation_type', 'status')
        }),
        ('ارتباطات', {
            'fields': ('test_category', 'test_item', 'standard',
                       'scope', 'purpose')
        }),
        ('حوزه اندازه‌گیری', {
            'fields': ('range_min', 'range_max', 'unit')
        }),
        ('صحت (Trueness / Accuracy)', {
            'fields': ('trueness', 'trueness_unit', 'accuracy',
                       'accuracy_notes'),
            'classes': ('collapse',)
        }),
        ('دقت (Precision)', {
            'fields': ('repeatability', 'repeatability_unit', 'repeatability_conditions',
                       'reproducibility', 'reproducibility_unit', 'reproducibility_conditions'),
            'classes': ('collapse',)
        }),
        ('LOD / LOQ', {
            'fields': ('lod', 'lod_unit', 'loq', 'loq_unit'),
            'classes': ('collapse',)
        }),
        ('انتخاب‌پذیری', {
            'fields': ('selectivity',),
            'classes': ('collapse',)
        }),
        ('خطی بودن', {
            'fields': ('linearity_r2', 'linearity_equation', 'linearity_points'),
            'classes': ('collapse',)
        }),
        ('مقاومت', {
            'fields': ('robustness',),
            'classes': ('collapse',)
        }),
        ('عدم‌قطعیت', {
            'fields': ('uncertainty', 'uncertainty_unit', 'coverage_factor'),
            'classes': ('collapse',)
        }),
        ('نتیجه‌گیری', {
            'fields': ('validation_conclusion', 'is_fit_for_purpose',
                       'limitations', 'recommendations')
        }),
        ('مسئولیت‌ها', {
            'fields': ('responsible', 'performed_by', 'approved_by', 'approved_at')
        }),
        ('زمان‌بندی', {
            'fields': ('started_at', 'completed_at', 'next_review_at')
        }),
        ('فایل‌ها', {
            'fields': ('protocol_file', 'report_file')
        }),
        ('توضیحات', {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'draft':       '#6b7280',
            'in_progress': '#d97706',
            'completed':   '#16a34a',
            'approved':    '#0891b2',
            'rejected':    '#dc2626',
            'obsolete':    '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'

    def review_status(self, obj):
        if obj.is_due_for_review:
            return format_html('<span style="color:#dc2626;font-weight:700;">⚠️ سررسید</span>')
        if obj.is_expiring_soon:
            return format_html('<span style="color:#d97706;font-weight:700;">⏰ نزدیک</span>')
        return format_html('<span style="color:#16a34a;">✅</span>')
    review_status.short_description = 'بازنگری'


@admin.register(MethodValidationParameter)
class MethodValidationParameterAdmin(admin.ModelAdmin):
    list_display = (
        'validation', 'param_no', 'parameter_type', 'parameter_name',
        'value', 'unit', 'meets_criteria',
    )
    list_filter = ('parameter_type', 'meets_criteria', 'validation')
    search_fields = ('validation__validation_no', 'parameter_name',
                     'acceptance_criteria', 'method_used')
    readonly_fields = ('created_at', 'param_no')
    autocomplete_fields = ('validation',)


# ==========================================================
# ISO/IEC 17025 — 6.5 Traceability / Reference Standards
# ==========================================================
class ReferenceStandardUsageInline(admin.TabularInline):
    model = ReferenceStandardUsage
    extra = 0
    fields = ('usage_no', 'usage_type', 'used_at', 'used_by',
              'related_equipment', 'amount_used')
    readonly_fields = ('usage_no',)
    autocomplete_fields = ('used_by', 'related_request', 'related_equipment')
    show_change_link = True


@admin.register(ReferenceStandard)
class ReferenceStandardAdmin(admin.ModelAdmin):
    list_display = (
        'ref_no', 'name', 'standard_type', 'manufacturer',
        'status_colored', 'expiry_date', 'days_left_display', 'responsible',
    )
    list_filter = ('status', 'standard_type', 'traceability_type', 'is_active')
    search_fields = ('ref_no', 'name', 'manufacturer', 'catalog_no',
                     'lot_no', 'serial_no', 'certificate_no', 'assigned_value')
    readonly_fields = ('created_at', 'updated_at', 'ref_no')
    date_hierarchy = 'expiry_date'
    autocomplete_fields = ('responsible', 'created_by')
    inlines = [ReferenceStandardUsageInline]

    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('ref_no', 'name', 'standard_type', 'status', 'is_active')
        }),
        ('تولیدکننده و شناسه‌ها', {
            'fields': ('manufacturer', 'catalog_no', 'lot_no', 'serial_no', 'asset_no')
        }),
        ('گواهی', {
            'fields': ('certificate_no', 'certificate_issue_date', 'certificate_file')
        }),
        ('مقدار و عدم‌قطعیت', {
            'fields': ('assigned_value', 'uncertainty', 'unit',
                       'coverage_factor', 'measurement_range')
        }),
        ('ردیابی اندازه‌شناسی', {
            'fields': ('traceability_type', 'traceability_chain', 'accredited_by')
        }),
        ('تاریخ‌ها', {
            'fields': ('received_date', 'opened_date', 'expiry_date')
        }),
        ('نگهداری و استفاده', {
            'fields': ('storage_conditions', 'storage_location', 'usage_instructions')
        }),
        ('مسئولیت‌ها', {
            'fields': ('responsible', 'created_by')
        }),
        ('توضیحات', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('زمان‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def status_colored(self, obj):
        colors = {
            'active':         '#16a34a',
            'expiring_soon':  '#d97706',
            'expired':        '#dc2626',
            'depleted':       '#6b7280',
            'out_of_service': '#374151',
            'obsolete':       '#9ca3af',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:6px;font-weight:700;font-size:0.8rem;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'وضعیت'

    def days_left_display(self, obj):
        d = obj.days_to_expiry
        if d is None:
            return '—'
        if d < 0:
            return format_html('<span style="color:#dc2626;font-weight:700;">{} روز گذشته</span>', abs(d))
        if d <= 60:
            return format_html('<span style="color:#d97706;font-weight:700;">{} روز</span>', d)
        return format_html('<span style="color:#16a34a;">{} روز</span>', d)
    days_left_display.short_description = 'مانده تا انقضا'


@admin.register(ReferenceStandardUsage)
class ReferenceStandardUsageAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'usage_no', 'usage_type', 'used_at', 'used_by',
        'related_equipment', 'amount_used',
    )
    list_filter = ('usage_type', 'used_at', 'reference')
    search_fields = ('reference__ref_no', 'reference__name', 'purpose',
                     'usage_no')
    readonly_fields = ('created_at', 'usage_no')
    autocomplete_fields = ('reference', 'used_by', 'related_request', 'related_equipment')

# ═══ کالیبراسیون (models_calib) ═══
CalibrationRegistry = _m("CalibrationRegistry")
CalibrationEquipment = _m("CalibrationEquipment")
CalibrationReference = _m("CalibrationReference")
MPERule = _m("MPERule")
IntervalBank = _m("IntervalBank")
EquipmentCategory = _m("EquipmentCategory")
EquipmentLocation = _m("EquipmentLocation")
EquipmentNameCode = _m("EquipmentNameCode")
CalibrationPricing = _m("CalibrationPricing")
ReferenceEquipment = _m("ReferenceEquipment")
ReferenceCertificate = _m("ReferenceCertificate")
ReferenceCertificateFile = _m("ReferenceCertificateFile")
ProductionGroup = _m("ProductionGroup")


try:
    admin.site.register(CalibrationRegistry)
except Exception:
    pass
# CalibrationEquipment با admin پیشرفته ثبت می‌شود (پایین‌تر)
# try:
#     admin.site.register(CalibrationEquipment)
# except Exception:
#     pass
try:
    admin.site.register(CalibrationReference)
except Exception:
    pass
try:
    admin.site.register(MPERule)
except Exception:
    pass
try:
    admin.site.register(IntervalBank)
except Exception:
    pass
try:
    admin.site.register(EquipmentCategory)
except Exception:
    pass
try:
    admin.site.register(EquipmentLocation)
except Exception:
    pass
try:
    admin.site.register(EquipmentNameCode)
except Exception:
    pass
try:
    admin.site.register(CalibrationPricing)
except Exception:
    pass
try:
    admin.site.register(ReferenceEquipment)
except Exception:
    pass
try:
    admin.site.register(ReferenceCertificate)
except Exception:
    pass
try:
    admin.site.register(ReferenceCertificateFile)
except Exception:
    pass
try:
    admin.site.register(ProductionGroup)
except Exception:
    pass

try:
    OutsourcedCalibration = _m("OutsourcedCalibration")
    admin.site.register(OutsourcedCalibration)
except Exception:
    pass

@admin.register(CompanyInfo)
class CompanyInfoAdmin(admin.ModelAdmin):
    """اطلاعات شرکت — فقط یک رکورد"""
    def has_add_permission(self, request):
        return not CompanyInfo.objects.exists()
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'is_active', 'updated_at')
    list_filter = ('is_default', 'is_active')
    search_fields = ('name', 'description')

# ═══════════════════════════════════════════════════════════
# CalibrationEquipment — Admin پیشرفته برای ویرایش سریع
# ═══════════════════════════════════════════════════════════

@admin.register(CalibrationEquipment)
class CalibrationEquipmentAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'equipment_group', 'equipment_subgroup', 'location', 'requester', 'scope_io',
                    'last_calibration', 'next_calibration', 'get_status_badge')
    list_display_links = ('code', 'name')
    list_editable = ('equipment_group', 'equipment_subgroup', 'scope_io')
    list_filter = ('location', 'scope_io')
    search_fields = ('code', 'name', 'location', 'requester', 'spec', 'range_text')
    ordering = ('location', 'requester', 'code')
    list_per_page = 50
    save_on_top = True

    fieldsets = (
        ('شناسایی', {
            'fields': ('code', 'code_base', 'name', 'spec', 'range_text', 'accuracy', 'unit')
        }),
        ('موقعیت و واحد', {
            'fields': ('location', 'requester', 'production_group', 'scope_io'),
            'description': 'گروه اصلی (location) و واحد (requester). مثال: location="ساخت تجهیزات" — requester="مخازن"'
        }),
        ('وضعیت کالیبراسیون', {
            'fields': ('last_calibration', 'next_calibration', 'status'),
            'description': 'تاریخ‌ها را به فرمت شمسی وارد کنید (مثال: 1405/06/15)'
        }),
        ('یادداشت', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    def get_status_badge(self, obj):
        from django.utils.html import format_html
        nc = (obj.next_calibration or '').strip()
        if not nc or nc in ('اسقاط', 'عدم نیاز', 'عدم استفاده', 'بی‌استفاده', 'نامشخص', '-', '—', '_'):
            return format_html('<span style="color:#94a3b8;">—</span>')
        try:
            import jdatetime
            parts = nc.split('/')
            if len(parts) >= 3:
                j = jdatetime.date(int(parts[0]), int(parts[1]), int(parts[2]))
                today = jdatetime.date.today()
                days = (j - today).days
                if days < 0:
                    return format_html(
                        '<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:8px;font-size:.75rem;font-weight:700;">منقضی ({} روز)</span>',
                        abs(days))
                elif days <= 30:
                    return format_html(
                        '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:8px;font-size:.75rem;font-weight:700;">{} روز مونده</span>',
                        days)
                elif days <= 90:
                    return format_html(
                        '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:8px;font-size:.75rem;">{} روز</span>',
                        days)
                else:
                    return format_html(
                        '<span style="color:#16a34a;font-size:.75rem;">{} روز</span>',
                        days)
        except Exception:
            return format_html('<span style="color:#94a3b8;">{}</span>', nc)
        return format_html('<span style="color:#94a3b8;">—</span>')
    get_status_badge.short_description = 'وضعیت'

    # ═══ Actions ═══
    actions = ['action_clean_anbar', 'action_set_scope_internal', 'action_set_scope_outsourced']

    def action_clean_anbar(self, request, queryset):
        """حذف 'انبار' از ابتدای واحد"""
        count = 0
        for eq in queryset:
            req = (eq.requester or '').strip()
            if req.startswith('انبار '):
                eq.requester = req[6:].strip()
                eq.save(update_fields=['requester'])
                count += 1
        self.message_user(request, '{} رکورد اصلاح شد.'.format(count))
    action_clean_anbar.short_description = "🧹 حذف 'انبار' از ابتدای واحد"

    def action_set_scope_internal(self, request, queryset):
        count = queryset.update(scope_io='I')
        self.message_user(request, '{} رکورد به داخلی تغییر یافت.'.format(count))
    action_set_scope_internal.short_description = '🏠 تنظیم به عنوان داخلی'

    def action_set_scope_outsourced(self, request, queryset):
        count = queryset.update(scope_io='O')
        self.message_user(request, '{} رکورد به برون‌سپاری تغییر یافت.'.format(count))
    action_set_scope_outsourced.short_description = '🌐 تنظیم به عنوان برون‌سپاری'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        # اضافه کردن لینک به لیست گروه‌ها
        extra_context['groups_url'] = '/calibration/monthly-due/'
        return super().changelist_view(request, extra_context=extra_context)

# ═══════════════════════════════════════════════════════════
# گروه‌ها و زیرگروه‌های تجهیزات
# ═══════════════════════════════════════════════════════════

from .models_calib import EquipmentGroup, EquipmentSubGroup


class EquipmentSubGroupInline(admin.TabularInline):
    model = EquipmentSubGroup
    extra = 1
    fields = ('name', 'code', 'order', 'is_active')
    ordering = ('order', 'name')
    show_change_link = True


@admin.register(EquipmentGroup)
class EquipmentGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order', 'get_subgroups_count', 'is_active')
    list_display_links = ('name',)
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('is_active',)
    ordering = ('order', 'name')
    inlines = [EquipmentSubGroupInline]

    fieldsets = (
        ('اطلاعات گروه', {
            'fields': ('name', 'code', 'order', 'is_active', 'description')
        }),
    )

    def get_subgroups_count(self, obj):
        from django.utils.html import format_html
        cnt = obj.subgroups.count()
        if cnt == 0:
            return format_html('<span style="color:#94a3b8;">0</span>')
        return format_html(
            '<span style="background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:8px;font-size:.75rem;font-weight:700;">{}</span>',
            cnt)
    get_subgroups_count.short_description = 'تعداد زیرگروه'

    def has_delete_permission(self, request, obj=None):
        # اجازه حذف فقط اگه زیرگروه نداره
        if obj and obj.subgroups.exists():
            return True  # هشدار داده می‌شود
        return True


@admin.register(EquipmentSubGroup)
class EquipmentSubGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'group', 'code', 'order', 'is_active')
    list_display_links = ('name',)
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'code', 'group__name')
    list_filter = ('is_active', 'group')
    ordering = ('group__order', 'order', 'name')

    list_per_page = 50
    save_on_top = True

# ═══════════════════════════════════════════════════════════
# تنظیمات اعلان کالیبراسیون
# ═══════════════════════════════════════════════════════════

from .models_calib import CalibrationAlertSettings


@admin.register(CalibrationAlertSettings)
class CalibrationAlertSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('وضعیت کلی', {
            'fields': ('is_active',),
            'description': 'اگه غیرفعال باشه، هیچ اعلان خودکاری برای موعد کالیبراسیون ساخته نمی‌شه.'
        }),
        ('دریافت‌کنندگان خودکار', {
            'fields': ('include_calibration_section', 'include_superuser'),
            'description': 'اعضای آزمایشگاه کالیبراسیون (کارشناسان و سرپرستان) + اختیاری مدیر سیستم.'
        }),
        ('کاربران اضافی', {
            'fields': ('recipients',),
            'description': 'کاربرانی که مستقل از نقش، اعلان دریافت کنن.',
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return not CalibrationAlertSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # هدایت به فرم ویرایش Singleton
        from django.shortcuts import redirect
        obj = CalibrationAlertSettings.get_solo()
        return redirect('/admin/core/calibrationalertsettings/%d/change/' % obj.pk)

# ===== Verification Admin =====
from .models_verification import (
    CalibrationAcceptanceRule,
    CalibrationVerification,
    CalibrationVerificationPoint,
    CalibrationVerificationEvent,
)


class CalibrationVerificationPointInline(admin.TabularInline):
    model = CalibrationVerificationPoint
    extra = 1
    can_delete = True
    show_change_link = True
    fields = ('order', 'nominal', 'error_e', 'abs_e', 'uncertainty_u',
              'coverage_factor_k', 'mpe', 'tur', 'conformance_probability',
              'decision', 'explanation')
    readonly_fields = ('abs_e', 'tur', 'conformance_probability')


class CalibrationVerificationEventInline(admin.TabularInline):
    model = CalibrationVerificationEvent
    extra = 0
    can_delete = False
    fields = ('created_at', 'event_type', 'from_value', 'to_value', 'user', 'description')
    readonly_fields = ('created_at', 'event_type', 'from_value', 'to_value', 'user', 'description')


@admin.register(CalibrationAcceptanceRule)
class CalibrationAcceptanceRuleAdmin(admin.ModelAdmin):
    list_display = ('equipment_code', 'equipment_name', 'parameter', 'unit',
                    'measurement_range', 'mpe', 'mpe_type', 'standard', 'is_active')
    list_filter = ('is_active', 'mpe_type', 'category', 'standard')
    search_fields = ('equipment_code', 'equipment_name', 'parameter', 'standard')
    list_editable = ('is_active',)


@admin.register(CalibrationVerification)
class CalibrationVerificationAdmin(admin.ModelAdmin):
    list_display = ('report_number', 'evaluation_date', 'equipment_code',
                    'equipment_name', 'method', 'mpe_calc_type', 'decision', 'min_tur',
                    'equipment_deactivated', 'created_at')
    list_filter = ('decision', 'method', 'equipment_deactivated', 'evaluation_date')
    search_fields = ('report_number', 'equipment_code', 'equipment_name', 'asset_serial')
    date_hierarchy = 'evaluation_date'
    readonly_fields = ('created_at', 'updated_at', 'deactivated_at', 'reactivated_at')
    inlines = [CalibrationVerificationPointInline, CalibrationVerificationEventInline]
    fieldsets = (
        ('هدر گزارش', {
            'fields': ('report_number', 'doc_code', 'doc_version',
                       'evaluation_date', 'operator',
                       'asset_serial', 'department', 'customer')
        }),
        ('تجهیز', {
            'fields': ('equipment_code', 'equipment_name', 'reference_standard',
                       'category', 'measurement_range')
        }),
        ('حد مجاز خطا (MPE)', {
            'fields': ('mpe_calc_type', 'mpe', 'mpe_b', 'full_scale'),
            'description': 'نوع محاسبه MPE را انتخاب کنید. اگر دستی را انتخاب کنید، مقدار هر نقطه در جدول پایین وارد می‌شود.'
        }),
        ('گواهی و آزمایشگاه مرجع', {
            'fields': ('certificate_number', 'calibration_date', 'calibration_lab')
        }),
        ('روش و پارامترها', {
            'fields': ('method', 'guard_band_factor', 'coverage_factor_k',
                       'threshold_accepted', 'threshold_conditional')
        }),
        ('نتیجه', {
            'fields': ('decision', 'min_tur')
        }),
        ('متن گزارش', {
            'fields': ('notes', 'limitations', 'corrective_actions',
                       'follow_up_date', 'technical_analysis')
        }),
        ('وضعیت تجهیز', {
            'fields': ('equipment_deactivated', 'deactivated_at', 'reactivated_at')
        }),
        ('متادیتا', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )


@admin.register(CalibrationVerificationEvent)
class CalibrationVerificationEventAdmin(admin.ModelAdmin):
    list_display = ('verification', 'event_type', 'from_value', 'to_value',
                    'user', 'created_at')
    list_filter = ('event_type', 'created_at')
    search_fields = ('verification__report_number', 'description')

# ===== Verification Settings Admin (Singleton) =====
from .models_verification_settings import CalibrationVerificationSettings


@admin.register(CalibrationVerificationSettings)
class CalibrationVerificationSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('هدر گزارش', {
            'fields': ('default_doc_code', 'default_doc_version', 'default_lab_name')
        }),
        ('روش و پارامترها', {
            'fields': ('default_method', 'default_k', 'default_guard_band_factor',
                       'default_threshold_accepted', 'default_threshold_conditional')
        }),
        ('حد مجاز خطا (MPE)', {
            'fields': ('default_mpe_calc_type',)
        }),
        ('بندهای بازرسی', {
            'fields': ('checklist_items',),
            'description': 'هر بند در یک خط جدید.'
        }),
        ('متن‌های پیش‌فرض', {
            'fields': ('default_limitations', 'default_corrective_actions', 'default_notes')
        }),
        ('شماره گزارش', {
            'fields': ('report_number_prefix', 'auto_number_from_serial')
        }),
    )

    def has_add_permission(self, request):
        return not CalibrationVerificationSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ===== مدیریت عناوین نقش‌ها =====
from .models import RoleTitle

@admin.register(RoleTitle)
class RoleTitleAdmin(admin.ModelAdmin):
    list_display = ('code', 'title')
    search_fields = ('code', 'title')
    list_editable = ('title',)


# MECHANICAL_OPTIONS_ADMIN_V1
from .models import MechanicalTestOption

@admin.register(MechanicalTestOption)
class MechanicalTestOptionAdmin(admin.ModelAdmin):
    list_display = (
        'test_code', 'field_key', 'label', 'value',
        'display_order', 'is_active',
    )
    list_filter = ('test_code', 'field_key', 'is_active')
    search_fields = ('label', 'value', 'field_key')
    list_editable = ('label', 'display_order', 'is_active')

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ('test_code', 'field_key', 'value')
        return ()
