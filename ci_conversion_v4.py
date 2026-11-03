"""Two-sided Student t interval inversion; no database or Django dependency."""
import math
from decimal import Decimal, InvalidOperation
from scipy.stats import t


def student_t_factor(accepted_mean_count, probability_percent):
    if (isinstance(accepted_mean_count, bool)
            or not isinstance(accepted_mean_count, int)
            or not 2 <= accepted_mean_count <= 2147483647):
        raise ValueError("Accepted mean count must be an integer of at least two.")
    if isinstance(probability_percent, bool):
        raise ValueError("Invalid confidence probability.")
    try:
        p = Decimal(str(probability_percent))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid confidence probability.")
    if not p.is_finite() or not Decimal("0") < p < Decimal("100"):
        raise ValueError("Confidence probability must be between zero and 100.")
    tail = float((Decimal("100") - p) / Decimal("200"))
    factor = float(t.isf(tail, accepted_mean_count - 1))
    if not math.isfinite(factor) or factor <= 0:
        raise ValueError("No finite positive Student t factor.")
    return Decimal(str(factor))
