"""Draft CRM certificate management through Django admin.

No approval workflow or historical immutability is claimed here.
Delete is disabled in these admin screens.
"""

from django.contrib import admin
from django.core.exceptions import ValidationError

from .crm_models import CRMCertificateVersion, CRMElementValue


CRMCertificateVersion._meta.verbose_name = "CRM certificate version"
CRMCertificateVersion._meta.verbose_name_plural = "Chemical CRM certificates"
CRMElementValue._meta.verbose_name = "CRM element value"
CRMElementValue._meta.verbose_name_plural = "Chemical CRM element values"


def uncertainty_preview(obj):
    if not obj or not obj.element:
        return "-"

    try:
        value = obj.standard_uncertainty_mass_percent()
    except (ValidationError, ArithmeticError, TypeError, ValueError):
        return "Not ready: review certificate data"

    return format(value, "f")


class CRMElementInline(admin.TabularInline):
    model = CRMElementValue
    extra = 1
    can_delete = False

    fields = (
        "element",
        "assigned_value",
        "unit",
        "value_status",
        "uncertainty_value",
        "uncertainty_kind",
        "uncertainty_basis",
        "coverage_factor",
        "coverage_probability_percent",
        "ci_method",
        "ci_accepted_mean_count",
        "ci_reviewed",
        "ci_source",
        "standard_u_mass_percent",
        "certificate_text",
        "notes",
    )

    readonly_fields = ("standard_u_mass_percent",)

    @admin.display(description="Standard u, mass percent")
    def standard_u_mass_percent(self, obj):
        return uncertainty_preview(obj)


@admin.register(CRMCertificateVersion)
class CRMCertificateVersionAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code",
        "certificate_no",
        "version",
        "producer_name",
        "matrix",
        "issue_date",
        "valid_until",
    )

    list_filter = ("matrix",)
    search_fields = (
        "reference__ref_no",
        "reference__name",
        "certificate_no",
        "producer_name",
        "lot_no",
    )

    readonly_fields = ("created_at", "updated_at", "workflow_notice")
    inlines = (CRMElementInline,)
    save_on_top = True
    list_select_related = ("reference",)

    fieldsets = (
        ("Draft data - not approved for final uncertainty reports", {
            "fields": ("workflow_notice",)
        }),
        ("Reference and certificate identity", {
            "fields": (
                "reference", "version", "certificate_no",
                "producer_name", "lot_no",
            )
        }),
        ("Matrix and certificate dates", {
            "fields": (
                "matrix", "matrix_description",
                "issue_date", "valid_until",
            )
        }),
        ("Certificate document and instructions", {
            "fields": (
                "certificate_file",
                "traceability_statement",
                "instructions",
                "notes",
            )
        }),
        ("Record timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    @admin.display(description="Reference")
    def reference_code(self, obj):
        return obj.reference.ref_no

    @admin.display(description="Workflow status")
    def workflow_notice(self, obj):
        return (
            "DRAFT DATA ONLY. Approval, version locking and study snapshots "
            "are not enabled yet. Do not treat this screen as final approval."
        )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CRMElementValue)
class CRMElementValueAdmin(admin.ModelAdmin):
    list_display = (
        "certificate",
        "element",
        "assigned_value",
        "unit",
        "value_status",
        "uncertainty_value",
        "uncertainty_kind",
        "coverage_factor",
        "standard_u_mass_percent",
    )

    list_filter = (
        "value_status",
        "uncertainty_kind",
        "unit",
        "certificate__matrix",
    )

    search_fields = (
        "element",
        "certificate__certificate_no",
        "certificate__reference__ref_no",
        "certificate__reference__name",
    )

    list_select_related = ("certificate",)
    readonly_fields = ("standard_u_mass_percent",)

    @admin.display(description="Standard u, mass percent")
    def standard_u_mass_percent(self, obj):
        return uncertainty_preview(obj)

    def has_delete_permission(self, request, obj=None):
        return False
