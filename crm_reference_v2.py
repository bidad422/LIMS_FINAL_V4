from django.contrib.auth.decorators import login_required, permission_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .crm_reference_forms_v2 import CRMReferenceForm

@login_required
@permission_required("core.add_referencestandard", raise_exception=True)
@require_http_methods(["GET", "POST"])
def crm_reference_new(request):
    form = CRMReferenceForm(
        request.POST if request.method == "POST" else None
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                reference = form.save(commit=False)
                reference.standard_type = "crm"
                reference.created_by = request.user
                reference.save()
        except IntegrityError:
            form.instance.pk = None
            form.instance._state.adding = True
            form.add_error(
                "ref_no",
                "ذخیره انجام نشد؛ احتمال تکراری‌بودن کد وجود دارد."
            )
        else:
            return redirect("uncertainty:crm_bank_new")
    return render(
        request,
        "uncertainty/crm_reference_new_v2.html",
        {"form": form},
    )