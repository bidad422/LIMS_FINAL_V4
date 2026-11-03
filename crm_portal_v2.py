from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .crm_models import CRMCertificateVersion
from .crm_portal_forms_v2 import CRMCertificateForm, CRMElementFormSet


@login_required
@permission_required(
    "uncertainty.view_crmcertificateversion",
    raise_exception=True,
)
@require_http_methods(["GET"])
def crm_list(request):
    certificates = (
        CRMCertificateVersion.objects
        .select_related("reference")
        .order_by("-created_at", "-pk")
    )

    query = request.GET.get("q", "").strip()[:200]

    if query:
        certificates = certificates.filter(
            Q(certificate_no__icontains=query)
            | Q(reference__ref_no__icontains=query)
            | Q(reference__name__icontains=query)
            | Q(producer_name__icontains=query)
        )

    page = Paginator(certificates, 30).get_page(request.GET.get("page"))

    return render(
        request,
        "uncertainty/crm_portal_list_v2.html",
        {"page_obj": page, "query": query},
    )


@login_required
@require_http_methods(["GET", "POST"])
def crm_edit(request, pk=None):
    editing = pk is not None

    if editing:
        required = (
            "uncertainty.view_crmcertificateversion",
            "uncertainty.change_crmcertificateversion",
            "uncertainty.view_crmelementvalue",
            "uncertainty.change_crmelementvalue",
            "uncertainty.add_crmelementvalue",
        )
    else:
        required = (
            "uncertainty.add_crmcertificateversion",
            "uncertainty.add_crmelementvalue",
        )

    if not request.user.has_perms(required):
        raise PermissionDenied

    certificate = (
        get_object_or_404(CRMCertificateVersion, pk=pk)
        if editing
        else CRMCertificateVersion()
    )

    data = request.POST if request.method == "POST" else None
    uploads = request.FILES if request.method == "POST" else None

    form = CRMCertificateForm(
        data,
        uploads,
        instance=certificate,
    )

    formset = CRMElementFormSet(
        data,
        uploads,
        instance=certificate,
        prefix="elements",
    )

    if request.method == "POST":
        certificate_valid = form.is_valid()
        elements_valid = formset.is_valid()

        if certificate_valid and elements_valid:
            try:
                with transaction.atomic():
                    saved = form.save()
                    formset.instance = saved
                    formset.save()

            except IntegrityError:
                form.add_error(
                    None,
                    "ذخیره انجام نشد. احتمال تکراری‌بودن نسخهٔ گواهی "
                    "یا عنصر وجود دارد. اطلاعات را بررسی کنید.",
                )

                if not editing:
                    certificate.pk = None
                    certificate._state.adding = True

            else:
                return redirect(
                    "uncertainty:crm_bank_edit",
                    pk=saved.pk,
                )

    rows = []

    for item in formset.forms:
        preview = None
        ready = False

        if request.method == "GET" and item.instance.pk:
            try:
                preview = format(
                    item.instance.standard_uncertainty_mass_percent(),
                    "f",
                )
                ready = True

            except (
                ValidationError,
                ArithmeticError,
                TypeError,
                ValueError,
            ):
                pass

        rows.append({
            "form": item,
            "preview": preview,
            "ready": ready,
        })

    return render(
        request,
        "uncertainty/crm_portal_edit_v2.html",
        {
            "form": form,
            "formset": formset,
            "rows": rows,
            "editing": editing,
        },
    )