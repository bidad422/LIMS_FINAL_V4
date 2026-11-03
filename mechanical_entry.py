"""Shared helpers for mechanical result entry."""
from .models import MechanicalTestOption


def get_mechanical_options():
    result = {"bend": {}, "flaring": {}, "flattening": {}}
    rows = MechanicalTestOption.objects.filter(is_active=True).order_by(
        "test_code", "field_key", "display_order", "id"
    )
    for row in rows:
        if row.test_code in result:
            result[row.test_code].setdefault(row.field_key, []).append({
                "value": row.value, "label": row.label,
            })
    return result


def normalize_status(value):
    value = str(value or "").strip()
    passed = (
        "\u0645\u0648\u0631\u062f \u062a\u0627\u06cc\u06cc\u062f "
        "(\u0628\u062f\u0648\u0646 \u062a\u0631\u06a9)"
    )
    failed = (
        "\u0631\u062f \u0634\u062f\u0647 "
        "(\u062f\u0627\u0631\u0627\u06cc \u062a\u0631\u06a9)"
    )
    if value.lower() == "pass" or value == passed:
        return "Pass"
    if value.lower() == "fail" or value == failed:
        return "Fail"
    return ""


def aggregate_status(values):
    statuses = [normalize_status(value) for value in values]
    if not statuses or any(not value for value in statuses):
        return ""
    return "Fail" if "Fail" in statuses else "Pass"


def flattening_status(soundness, ductility):
    values = [
        str(soundness or "").strip(),
        str(ductility or "").strip(),
    ]
    if any(value not in {"NO Defect", "Defect"} for value in values):
        return ""
    return "Fail" if "Defect" in values else "Pass"


def get_bend_entry_context(req_obj, assignment=None):
    qs = req_obj.bend_results.order_by("sample_index", "id")
    if assignment is not None:
        if qs.exclude(assignment__isnull=True).exists():
            qs = qs.filter(assignment=assignment)
    rows = list(qs)
    keys = (
        "section_shape", "material_group", "bend_method",
        "bend_angle", "mandrel_spec", "defect_limit_text", "standard_ref",
    )
    common = {}
    conflicts = []
    for key in keys:
        values = []
        for row in rows:
            value = getattr(row, key)
            if key == "mandrel_spec" and not value:
                if row.mandrel_diameter is not None:
                    value = f"{row.mandrel_diameter:g} mm"
            if key == "bend_angle" and value is not None:
                value = f"{value:g}"
            values.append(str(value or "").strip())
        distinct = set(values)
        common[key] = values[0] if len(distinct) == 1 else ""
        if len(distinct) > 1:
            conflicts.append(key)
    for row in rows:
        normalized = normalize_status(row.result_status)
        if normalized:
            row.result_status = normalized
    return {
        "bends": rows,
        "bend_common": common,
        "bend_common_conflicts": conflicts,
    }


def prepare_bend_submission(post):
    import re
    from django.core.exceptions import ValidationError

    if post.get("b_entry_version") != "1":
        raise ValidationError("Reload the result entry page before saving.")

    keys = (
        "section_shape", "material_group", "bend_method",
        "bend_angle", "mandrel_spec", "defect_limit_text",
    )
    common = {
        key: (post.get("b_common_" + key) or "").strip()
        for key in keys
    }
    common["standard_ref"] = (
        post.get("b_common_std_0") or ""
    ).strip()
    indices = sorted({
        int(match.group(1))
        for key in post
        if (match := re.fullmatch(r"b_label_(\d+)", key))
    })
    rows = []
    for index in indices:
        prefix = f"b_label_{index}"
        label = (post.get(prefix) or "").strip()
        dimensions = (post.get(f"b_dimensions_{index}") or "").strip()
        kind = (post.get(f"b_kind_{index}") or "").strip()
        defects = list(dict.fromkeys(
            value.strip()
            for value in post.getlist(f"b_defects_{index}")
            if value.strip()
        ))
        raw_status = (post.get(f"b_status_{index}") or "").strip()
        notes = (post.get(f"b_notes_{index}") or "").strip()
        used = (
            post.get(f"b_used_{index}") == "1"
            or bool(dimensions or kind or defects or raw_status or notes)
        )
        if not used:
            continue
        if not label:
            raise ValidationError(f"Sample {index + 1}: label is required.")
        status = normalize_status(raw_status)
        if raw_status and not status:
            raise ValidationError(f"Sample {index + 1}: invalid result.")
        if "No Crack" in defects and len(defects) > 1:
            raise ValidationError(
                f"Sample {index + 1}: No Crack cannot accompany other defects."
            )
        rows.append({
            "index": index, "label": label,
            "dimensions": dimensions, "kind": kind,
            "defects": defects, "status": status, "notes": notes,
        })
    return common, rows


def validate_bend_options(common, rows, existing):
    from django.core.exceptions import ValidationError

    active = {}
    for option in MechanicalTestOption.objects.filter(
        test_code="bend", is_active=True
    ):
        active.setdefault(option.field_key, set()).add(option.value)

    common_keys = (
        "section_shape", "material_group", "bend_method", "bend_angle",
    )
    for key in common_keys:
        value = common.get(key, "")
        previous = set()
        for obj in existing:
            old_value = getattr(obj, key)
            if key == "bend_angle" and old_value is not None:
                old_value = f"{old_value:g}"
            previous.add(str(old_value or "").strip())
        if value and value not in active.get(key, set()) | previous:
            raise ValidationError(f"Invalid option: {key}")

    by_index = {obj.sample_index: obj for obj in existing}
    for row in rows:
        obj = by_index.get(row["index"])
        previous_kind = getattr(obj, "specimen_kind", "")
        kind = row["kind"]
        if kind and kind not in active.get("specimen_kind", set()):
            if kind != previous_kind:
                raise ValidationError("Invalid specimen kind.")
        previous_defects = getattr(obj, "defects", []) or []
        allowed = active.get("defects", set()) | set(previous_defects)
        if any(value not in allowed for value in row["defects"]):
            raise ValidationError("Invalid defect option.")


from django.db import transaction


@transaction.atomic
def save_bend_entry(req_obj, assignment, user, post, uncertainty_defaults):
    from django.core.exceptions import ValidationError
    from .models import TestRequest, BendTestResult, MechanicalTestSummary

    if assignment is None or assignment.request_id != req_obj.pk:
        raise ValidationError("A matching request assignment is required.")

    TestRequest.objects.select_for_update().get(pk=req_obj.pk)
    all_rows = list(
        req_obj.bend_results.select_for_update().order_by("sample_index")
    )
    linked = any(obj.assignment_id is not None for obj in all_rows)
    existing = [
        obj for obj in all_rows
        if not linked or obj.assignment_id == assignment.pk
    ]
    common, rows = prepare_bend_submission(post)
    validate_bend_options(common, rows, existing)
    if not rows:
        raise ValidationError("At least one used sample is required.")
    indices = {row["index"] for row in rows}
    owned_ids = {obj.pk for obj in existing}
    if any(
        obj.sample_index in indices and obj.pk not in owned_ids
        for obj in all_rows
    ):
        raise ValidationError("Sample index belongs to another assignment.")
    context = get_bend_entry_context(req_obj, assignment)
    conflicts = context["bend_common_conflicts"]
    if conflicts:
        if post.get("b_confirm_shared") != "1":
            raise ValidationError("Confirm the common-value changes first.")
        if any(not common.get(key) for key in conflicts):
            raise ValidationError("Resolve all conflicting common fields.")

    summary = MechanicalTestSummary.objects.filter(
        assignment=assignment, test_code="bend"
    ).first()

    by_index = {obj.sample_index: obj for obj in existing}
    for row in rows:
        obj = by_index.get(row["index"])
        if obj is None:
            obj = BendTestResult(
                request=req_obj, assignment=assignment,
                sample_index=row["index"],
            )
        obj.sample_label = row["label"]
        obj.operator = user
        obj.specimen_dimensions = row["dimensions"]
        obj.specimen_kind = row["kind"]
        obj.defects = row["defects"]
        obj.result_status = row["status"]
        obj.notes = row["notes"]
        for key in (
            "section_shape", "material_group", "bend_method",
            "defect_limit_text", "standard_ref",
        ):
            value = common[key]
            if value:
                setattr(obj, key, value)
        if common["bend_angle"]:
            obj.bend_angle = float(common["bend_angle"])
        if common["mandrel_spec"]:
            import re
            obj.mandrel_spec = common["mandrel_spec"]
            match = re.fullmatch(
                r"([0-9]+(?:\.[0-9]+)?)\s*(?:mm)?",
                obj.mandrel_spec, flags=re.I,
            )
            obj.mandrel_diameter = (
                float(match.group(1)) if match else None
            )
        values = uncertainty_defaults(
            post, row["index"]
        )
        for key, value in values.items():
            setattr(obj, key, value)
        obj.full_clean()
        obj.save()
    obsolete_ids = [
        obj.pk for obj in existing if obj.sample_index not in indices
    ]
    if obsolete_ids:
        BendTestResult.objects.filter(pk__in=obsolete_ids).delete()

    automatic = aggregate_status([row["status"] for row in rows])
    # BEND_OVERRIDE_CONNECTED_V1
    final, overridden, reason = read_mechanical_override(post, automatic)
    if summary is None:
        summary = MechanicalTestSummary(
            request=req_obj, assignment=assignment, test_code="bend"
        )
    summary.automatic_status = automatic
    summary.final_status = final
    summary.is_overridden = overridden
    summary.override_reason = reason
    summary.common_data = common
    summary.updated_by = user
    summary.full_clean()
    summary.save()
    return summary


def incomplete_mechanical_samples(rows, test_code):
    incomplete = []
    for row in rows:
        status = normalize_status(row.result_status)
        if test_code == "flattening":
            soundness = getattr(row, "soundness", "") or ""
            ductility = getattr(row, "ductility", "") or ""
            if soundness or ductility:
                status = flattening_status(soundness, ductility)
        if not status:
            incomplete.append(row.sample_label)
    return incomplete


def read_mechanical_override(post, automatic):
    from django.core.exceptions import ValidationError

    if post.get("mechanical_summary_version") != "1":
        raise ValidationError("Reload the result entry page before saving.")
    overridden = post.get("mechanical_override") == "1"
    if not overridden:
        return automatic, False, ""

    final = (post.get("mechanical_final") or "").strip()
    reason = (post.get("mechanical_reason") or "").strip()
    if automatic not in ("Pass", "Fail"):
        raise ValidationError("Complete sample results before overriding.")
    if final not in ("Pass", "Fail"):
        raise ValidationError("Select Pass or Fail for the final result.")
    if not reason:
        raise ValidationError("A reason is required for a manual override.")
    return final, True, reason
