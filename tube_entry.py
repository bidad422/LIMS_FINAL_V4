"""Validated entry for flaring and flattening results."""
import math
import re

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    TestRequest, FlaringTestResult, FlatteningTestResult,
    MechanicalTestOption, MechanicalTestSummary,
)
from .mechanical_entry import (
    normalize_status, aggregate_status,
    flattening_status, read_mechanical_override,
)

CONFIG = {
    "flaring": {
        "prefix": "fr",
        "model": FlaringTestResult,
        "relation": "flaring_results",
        "choices": {
            "test_name": "name",
            "mandrel_angle_spec": "angle",
        },
        "numbers": {
            "initial_outer_diameter": "od",
            "expanded_diameter": "exp",
        },
    },
    "flattening": {
        "prefix": "fl",
        "model": FlatteningTestResult,
        "relation": "flattening_results",
        "choices": {
            "test_name": "name",
            "weld_position": "weld",
            "soundness": "soundness",
            "ductility": "ductility",
        },
        "numbers": {
            "initial_outer_diameter": "od",
            "initial_wall_thickness": "wall",
            "final_plate_distance": "plate",
        },
    },
}


def parse_number(value, field):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        result = float(text)
    except ValueError:
        raise ValidationError("Invalid number: " + field)
    if not math.isfinite(result):
        raise ValidationError("Non-finite number: " + field)
    return result


def prepare_tube_rows(code, post, existing):
    if code not in CONFIG:
        raise ValidationError("Unsupported tube test.")
    if post.get("tube_entry_version") != "1":
        raise ValidationError("Reload the result entry page before saving.")

    cfg = CONFIG[code]
    prefix = cfg["prefix"]
    pattern = re.compile(rf"^{prefix}_label_(\d+)$")
    indices = sorted({
        int(match.group(1)) for key in post
        if (match := pattern.fullmatch(key))
    })
    active = {}
    for option in MechanicalTestOption.objects.filter(
        test_code=code, is_active=True
    ):
        active.setdefault(option.field_key, set()).add(option.value)

    previous = {obj.sample_index: obj for obj in existing}
    prepared = []
    for index in indices:
        old = previous.get(index)
        label = (post.get(f"{prefix}_label_{index}") or "").strip()
        if not label:
            raise ValidationError(f"Sample {index + 1}: label is required.")
        values = {
            "sample_label": label,
            "standard_ref": (
                post.get(f"{prefix}_std_{index}") or ""
            ).strip(),
            "notes": (post.get(f"{prefix}_notes_{index}") or "").strip(),
        }

        for field, suffix in cfg["choices"].items():
            value = (post.get(f"{prefix}_{suffix}_{index}") or "").strip()
            old_value = getattr(old, field, "") or ""
            if value and value not in active.get(field, set()):
                if value != old_value:
                    raise ValidationError("Invalid option: " + field)
            values[field] = value

        for field, suffix in cfg["numbers"].items():
            values[field] = parse_number(
                post.get(f"{prefix}_{suffix}_{index}"), field
            )

        if code == "flaring":
            defects = list(dict.fromkeys(
                value.strip()
                for value in post.getlist(f"fr_defects_{index}")
                if value.strip()
            ))
            allowed = active.get("defects", set()) | set(
                getattr(old, "defects", []) or []
            )
            if any(value not in allowed for value in defects):
                raise ValidationError("Invalid flaring defect.")
            if "No Crack" in defects and len(defects) > 1:
                raise ValidationError(
                    "No Crack cannot accompany other defects."
                )
            raw = (post.get(f"fr_status_{index}") or "").strip()
            status = normalize_status(raw)
            if raw and not status:
                raise ValidationError("Invalid flaring result.")
            values.update(defects=defects, result_status=status)
        else:
            values["specimen_dimensions"] = (
                post.get(f"fl_dimensions_{index}") or ""
            ).strip()
            status = flattening_status(
                values["soundness"], values["ductility"]
            )
            if old is not None and not (
                values["soundness"] or values["ductility"]
                or old.soundness or old.ductility
            ):
                status = normalize_status(old.result_status)
            values["result_status"] = status

        prepared.append((index, values))

    if not prepared:
        raise ValidationError("At least one sample is required.")
    return prepared


@transaction.atomic
def save_tube_entry(
    code, req_obj, assignment, user, post, uncertainty_defaults
):
    if code not in CONFIG:
        raise ValidationError("Unsupported tube test.")
    if assignment is None or assignment.request_id != req_obj.pk:
        raise ValidationError("A matching request assignment is required.")

    cfg = CONFIG[code]
    TestRequest.objects.select_for_update().get(pk=req_obj.pk)
    all_rows = list(
        getattr(req_obj, cfg["relation"]).select_for_update().order_by(
            "sample_index"
        )
    )
    linked = any(obj.assignment_id is not None for obj in all_rows)
    existing = [
        obj for obj in all_rows
        if not linked or obj.assignment_id == assignment.pk
    ]
    prepared = prepare_tube_rows(code, post, existing)
    indices = {index for index, values in prepared}
    owned_ids = {obj.pk for obj in existing}
    if any(
        obj.sample_index in indices and obj.pk not in owned_ids
        for obj in all_rows
    ):
        raise ValidationError("Sample index belongs to another assignment.")

    automatic = aggregate_status([
        values["result_status"] for index, values in prepared
    ])
    final, overridden, reason = read_mechanical_override(post, automatic)
    previous = {obj.sample_index: obj for obj in existing}

    for index, values in prepared:
        obj = previous.get(index)
        if obj is None:
            obj = cfg["model"](
                request=req_obj, assignment=assignment, sample_index=index
            )
        obj.operator = user
        for field, value in values.items():
            setattr(obj, field, value)
        for field, value in uncertainty_defaults(post, index).items():
            setattr(obj, field, value)

        if code == "flaring":
            obj.expansion_percent = None
        else:
            obj.flatten_ratio = None

        obj.full_clean()
        obj.save()

    obsolete = [
        obj.pk for obj in existing if obj.sample_index not in indices
    ]
    if obsolete:
        cfg["model"].objects.filter(pk__in=obsolete).delete()

    summary = MechanicalTestSummary.objects.filter(
        assignment=assignment, test_code=code
    ).first()
    if summary is None:
        summary = MechanicalTestSummary(
            request=req_obj, assignment=assignment, test_code=code
        )
    summary.automatic_status = automatic
    summary.final_status = final
    summary.is_overridden = overridden
    summary.override_reason = reason
    summary.common_data = {"sample_count": len(prepared)}
    summary.updated_by = user
    summary.full_clean()
    summary.save()
    return summary


def get_tube_entry_context(req_obj, assignment=None):
    result = {}
    for code, cfg in CONFIG.items():
        qs = getattr(req_obj, cfg["relation"]).order_by("sample_index", "id")
        if assignment is not None:
            if qs.exclude(assignment__isnull=True).exists():
                qs = qs.filter(assignment=assignment)
        rows = list(qs)
        for row in rows:
            status = normalize_status(row.result_status)
            if code == "flattening" and (row.soundness or row.ductility):
                status = flattening_status(row.soundness, row.ductility)
            if status:
                row.result_status = status
        result["flarings" if code == "flaring" else "flattenings"] = rows
        result[code + "_summary"] = (
            MechanicalTestSummary.objects.filter(
                request=req_obj, assignment=assignment, test_code=code
            ).first()
            if assignment is not None else None
        )
    return result
