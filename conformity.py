"""موتور مستقل و یکنواخت تصمیم انطباق LIMS.

این ماژول هیچ وابستگی به Django ندارد و برای تمام تصمیم‌های عددی سامانه
(آزمون و کالیبراسیون) یک قرارداد مشترک ارائه می‌کند.
"""
import math


VALID_RULES = {'simple', 'guard_band', 'probability'}


def _num(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def decide(value, lower=None, upper=None, u=None, U=None, k=2.0,
           rule='simple', guard_band=None, confidence=95.0,
           lower_inclusive=True, upper_inclusive=True,
           uncertainty_required=False):
    """تصمیم انطباق یک مقدار نسبت به حدود مشخصه.

    قرارداد عدم‌قطعیت:
      u = standard uncertainty
      U = expanded uncertainty
      k = coverage factor

    در rule='probability' فرض توزیع نرمال برای کمیت اندازه‌گیری‌شده است.
    """
    value = _num(value)
    lower = _num(lower)
    upper = _num(upper)
    u = _num(u)
    U = _num(U)
    k = _num(k)
    confidence = _num(confidence)
    gb = _num(guard_band)

    if value is None:
        return {'status': 'NO_DECISION', 'message': 'مقدار نتیجه عددی معتبر نیست.'}
    if lower is None and upper is None:
        return {'status': 'NO_DECISION', 'message': 'حد مشخصه تعریف نشده است.'}
    if lower is not None and upper is not None and lower > upper:
        return {'status': 'NO_DECISION', 'message': 'حد پایین Specification از حد بالا بزرگ‌تر است.'}
    if k is None or k <= 0:
        return {'status': 'NO_DECISION', 'message': 'ضریب پوشش k باید بزرگ‌تر از صفر باشد.'}
    if confidence is None or not (0.0 < confidence <= 100.0):
        return {'status': 'NO_DECISION', 'message': 'سطح اطمینان باید در بازه 0 تا 100 درصد باشد.'}
    if u is not None and u < 0:
        return {'status': 'NO_DECISION', 'message': 'عدم‌قطعیت استاندارد u نمی‌تواند منفی باشد.'}
    if U is not None and U < 0:
        return {'status': 'NO_DECISION', 'message': 'عدم‌قطعیت گسترش‌یافته U نمی‌تواند منفی باشد.'}
    if gb is not None and gb < 0:
        return {'status': 'NO_DECISION', 'message': 'Guard Band نمی‌تواند منفی باشد.'}

    if U is None and u is not None:
        U = u * k
    elif U is not None:
        # U منبع اصلی گزارش است؛ در صورت ارائه همزمان u و U، قرارداد U=k·u را اعمال می‌کنیم.
        u = U / k
    if uncertainty_required and U is None and u is None:
        return {'status': 'NO_DECISION', 'message': 'عدم‌قطعیت برای این Specification الزامی است.'}

    rule = (rule or 'simple').strip().lower()
    if rule not in VALID_RULES:
        return {'status': 'NO_DECISION', 'message': f'قاعده تصمیم ناشناخته: {rule}'}

    def inside(v, lo, hi):
        low_ok = True if lo is None else (v >= lo if lower_inclusive else v > lo)
        high_ok = True if hi is None else (v <= hi if upper_inclusive else v < hi)
        return low_ok and high_ok

    base = {'U': U, 'u': u, 'k': k}

    if rule == 'simple':
        ok = inside(value, lower, upper)
        return {
            **base,
            'status': 'PASS' if ok else 'FAIL',
            'guard_band': 0.0,
            'pc': None,
            'effective_lower': lower,
            'effective_upper': upper,
            'message': 'قابل قبول' if ok else 'خارج از حدود مشخصه',
        }

    if rule == 'guard_band':
        # Guard Band باید صریحاً از Policy/CalibrationLimit بیاید؛ در نبود مقدار صریح
        # برای سازگاری با رفتار قبلی، U به عنوان margin استفاده می‌شود.
        if gb is None:
            if U is None:
                return {'status': 'NO_DECISION', 'message': 'برای Guard Band باید مقدار GB یا U مشخص باشد.', **base}
            gb = U
        effective_lower = lower + gb if lower is not None else None
        effective_upper = upper - gb if upper is not None else None
        if effective_lower is not None and effective_upper is not None and effective_lower > effective_upper:
            return {
                **base, 'status': 'NO_DECISION', 'guard_band': gb,
                'effective_lower': effective_lower, 'effective_upper': effective_upper,
                'message': 'Guard Band از پهنای ناحیه پذیرش بزرگ‌تر است.'
            }
        ok = inside(value, effective_lower, effective_upper)
        return {
            **base,
            'status': 'PASS' if ok else 'FAIL',
            'guard_band': gb,
            'effective_lower': effective_lower,
            'effective_upper': effective_upper,
            'pc': None,
            'message': 'قابل قبول با Guard Band' if ok else 'عدم انطباق با Guard Band',
        }

    # Probability of Conformity با فرض توزیع نرمال
    if u is None or u <= 0:
        return {'status': 'NO_DECISION', 'message': 'برای احتمال انطباق، u معتبر و بزرگ‌تر از صفر لازم است.', **base}
    lo = -math.inf if lower is None else (lower - value)
    hi = math.inf if upper is None else (upper - value)
    pc = _cdf(hi / u) - _cdf(lo / u)
    pc = max(0.0, min(1.0, pc))
    threshold = confidence / 100.0
    ok = pc >= threshold
    return {
        **base,
        'status': 'PASS' if ok else 'FAIL',
        'guard_band': 0.0,
        'pc': pc * 100.0,
        'confidence_threshold': confidence,
        'distribution_assumption': 'normal',
        'effective_lower': lower,
        'effective_upper': upper,
        'message': f'Pc={pc*100:.3f}% | آستانه={confidence:.3f}%',
    }
