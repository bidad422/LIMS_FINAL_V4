from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .crm_models import CRMCertificateVersion, CRMElementValue
from .crm_portal_forms_v2 import CRMElementForm



class CIReviewForm(CRMElementForm):
    class Meta(CRMElementForm.Meta):
        fields = ("ci_method", "ci_accepted_mean_count", "ci_reviewed", "ci_source")

    def _update_errors(self, errors):
        if hasattr(errors, "error_dict"):
            mapped = {}
            for key, items in errors.error_dict.items():
                target = key if key in self.fields else NON_FIELD_ERRORS
                mapped.setdefault(target, []).extend(items)
            errors = ValidationError(mapped)
        super()._update_errors(errors)


@login_required
@permission_required((
    "uncertainty.view_crmcertificateversion",
    "uncertainty.change_crmcertificateversion",
    "uncertainty.view_crmelementvalue",
    "uncertainty.change_crmelementvalue",
), raise_exception=True)
@require_http_methods(["GET", "POST"])
def crm_ci_review(request, pk):
    certificate = get_object_or_404(CRMCertificateVersion, pk=pk)
    queryset = certificate.element_values.filter(uncertainty_kind="ci_half_width")
    count = queryset.count()
    Factory = inlineformset_factory(
        CRMCertificateVersion, CRMElementValue,
        form=CIReviewForm,
        fields=("ci_method", "ci_accepted_mean_count",
                "ci_reviewed", "ci_source"),
        extra=0, can_delete=False, min_num=count, validate_min=True,
        max_num=count, validate_max=True, absolute_max=max(1, count),
    )
    formset = Factory(
        request.POST if request.method == "POST" else None,
        instance=certificate, queryset=queryset, prefix="ci",
    )
    if request.method == "POST" and formset.is_valid():
        posted_ids = {form.instance.pk for form in formset.forms}
        expected_ids = set(queryset.values_list("pk", flat=True))
        if len(formset.forms) != count or posted_ids != expected_ids:
            raise ValidationError("CI row identities changed; reload the page.")
        with transaction.atomic():
            formset.save()
        return redirect("uncertainty:crm_ci_review", pk=pk)
    rows = []
    for form in formset.forms:
        value = form.instance
        u = factor = None
        if request.method == "GET":
            try:
                factor = value.ci_student_t_factor()
                u = value.standard_uncertainty_mass_percent()
            except (ValidationError, ValueError, ArithmeticError):
                pass
        rows.append(dict(form=form, value=value, factor=factor, u=u))
    return render(request, "uncertainty/crm_ci_review_v4.html", dict(
        certificate=certificate, formset=formset, rows=rows,
    ))
