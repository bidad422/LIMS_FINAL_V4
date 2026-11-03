"""Single-element, single-CRM, one-factor random-effects precision.

Groups represent operator/run conditions, not different CRM concentrations.
Method-of-moments variance components; supports unequal group sizes.
No automatic outlier removal. This is not a complete uncertainty budget.
"""

import math
from statistics import mean, variance
from .qc_spectro_v2 import parse_mass_percent

def analyze_precision(groups, *, mean_replicates=1):
    if (
        isinstance(mean_replicates, bool)
        or not isinstance(mean_replicates, int)
        or mean_replicates < 1
    ):
        raise ValueError("mean_replicates must be a positive integer.")

    if not isinstance(groups, dict) or not groups:
        raise ValueError("Provide a mapping of group IDs to readings.")

    records = []
    used_labels = set()

    for label, readings in groups.items():
        name = str(label).strip()

        if not name or name in used_labels:
            raise ValueError("Group IDs must be nonempty and unique.")

        used_labels.add(name)

        if isinstance(readings, (str, bytes, dict)):
            raise ValueError("Each group must contain a sequence of readings.")

        numbers = [parse_mass_percent(value) for value in readings]

        if len(numbers) < 2:
            raise ValueError("Each group requires at least two readings.")

        average = mean(numbers)

        records.append({
            "group": name,
            "n": len(numbers),
            "mean": average,
            "sample_sd": math.sqrt(variance(numbers)),
            "values": numbers,
        })

    k = len(records)
    total = sum(row["n"] for row in records)
    grand = math.fsum(
        row["n"] * row["mean"] for row in records
    ) / total

    ss_within = math.fsum(
        (value - row["mean"]) ** 2
        for row in records
        for value in row["values"]
    )

    df_within = total - k
    ms_within = ss_within / df_within
    repeatability_sd = math.sqrt(ms_within)

    warnings = [
        "One-factor random-effects model requires representative groups.",
        "Independence, residual distribution and variance homogeneity "
        "require review.",
        "Operator effects cannot be separated from confounded day/run effects.",
        "Outlier decisions must be documented before final calculations.",
        "This result is precision only, not a complete uncertainty budget.",
    ]

    result = {
        "schema_version": 1,
        "method": "one_way_random_effects_method_of_moments",
        "status": "computed_requires_review",
        "groups": records,
        "group_count": k,
        "total_readings": total,
        "balanced": len({row["n"] for row in records}) == 1,
        "grand_mean": grand,
        "mean_replicates": mean_replicates,
        "repeatability_sd": repeatability_sd,
        "repeatability_u_for_mean": (
            repeatability_sd / math.sqrt(mean_replicates)
        ),
        "anova": {
            "ss_within": ss_within,
            "df_within": df_within,
            "ms_within": ms_within,
        },
        "between_group_variance_raw": None,
        "between_group_sd": None,
        "intermediate_sd_single": None,
        "precision_u_for_group_mean": None,
        "study_grand_mean_u_precision": None,
        "variance_shares_for_group_mean": None,
        "warnings": warnings,
    }

    if k < 2:
        result["status"] = "repeatability_only"
        warnings.append("Between-group precision was not evaluated.")
        return result

    ss_between = math.fsum(
        row["n"] * (row["mean"] - grand) ** 2
        for row in records
    )

    df_between = k - 1
    ms_between = ss_between / df_between

    n_effective = (
        total - math.fsum(row["n"] ** 2 for row in records) / total
    ) / df_between

    between_raw = (ms_between - ms_within) / n_effective
    between_variance = max(0.0, between_raw)

    if between_raw < 0:
        warnings.append(
            "Negative raw between-group variance truncated to zero; "
            "this does not prove absence of a group effect."
        )

    if k < 3:
        warnings.append(
            "Only two groups: between-group variance has limited information."
        )

    within_for_mean = ms_within / mean_replicates
    combined_for_mean = between_variance + within_for_mean

    weights_squared = math.fsum(
        (row["n"] / total) ** 2 for row in records
    )

    study_mean_variance = (
        between_variance * weights_squared + ms_within / total
    )

    result["anova"].update({
        "ss_between": ss_between,
        "df_between": df_between,
        "ms_between": ms_between,
        "n_effective": n_effective,
    })

    result.update({
        "between_group_variance_raw": between_raw,
        "between_group_sd": math.sqrt(between_variance),
        "intermediate_sd_single": math.sqrt(
            between_variance + ms_within
        ),
        "precision_u_for_group_mean": math.sqrt(combined_for_mean),
        "study_grand_mean_u_precision": math.sqrt(study_mean_variance),
        "variance_shares_for_group_mean": {
            "repeatability_percent": (
                100 * within_for_mean / combined_for_mean
                if combined_for_mean else None
            ),
            "between_group_percent": (
                100 * between_variance / combined_for_mean
                if combined_for_mean else None
            ),
        },
    })

    return result
