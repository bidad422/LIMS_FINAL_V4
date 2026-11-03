"""محاسبات مستقل کالیبراسیون LIMS.

Reference/Reading ابتدا باید در یک واحد محاسباتی مشترک باشند. این ماژول فقط
محاسبات مترولوژیک و تصمیم نقطه‌ای را انجام می‌دهد و به Django وابسته نیست.
"""
import math

from .conformity import decide


def _num(v):
    try:
        if v is None or str(v).strip() == '':
            return None
        v = float(v)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _mpe_for_point(mpe, mpe_type, reading, range_min=None, range_max=None):
    mpe = _num(mpe)
    reading = _num(reading)
    if mpe is None or reading is None or mpe < 0:
        return None
    mpe_type = (mpe_type or 'absolute').strip().lower()
    if mpe_type == 'percent_reading':
        return abs(reading) * mpe / 100.0
    if mpe_type == 'percent_range':
        rmin = _num(range_min)
        rmax = _num(range_max)
        if rmin is None or rmax is None or rmax < rmin:
            return None
        return abs(rmax - rmin) * mpe / 100.0
    if mpe_type == 'absolute':
        return mpe
    return None


def calculate_calibration_points(points, mpe=None, mpe_type='absolute', range_min=None,
                                  range_max=None, expanded_uncertainty=None,
                                  standard_uncertainty=None, coverage_factor=2.0,
                                  decision_rule='simple', guard_band=None,
                                  guard_band_factor=1.0, confidence=95.0):
    out = []
    coverage_factor = _num(coverage_factor)
    if coverage_factor is None or coverage_factor <= 0:
        return {
            'points': [], 'u': None, 'U': None, 'max_error_percent': None,
            'guard_band': None, 'status': 'NO_DECISION',
            'errors': ['ضریب پوشش k باید بزرگ‌تر از صفر باشد.']
        }
    confidence = _num(confidence)
    if confidence is None or not (0.0 < confidence <= 100.0):
        return {
            'points': [], 'u': None, 'U': None, 'max_error_percent': None,
            'guard_band': None, 'status': 'NO_DECISION',
            'errors': ['سطح اطمینان نامعتبر است.']
        }

    range_min = _num(range_min)
    range_max = _num(range_max)
    if range_min is not None and range_max is not None and range_min > range_max:
        return {
            'points': [], 'u': None, 'U': None, 'max_error_percent': None,
            'guard_band': None, 'status': 'NO_DECISION',
            'errors': ['Range Min از Range Max بزرگ‌تر است.']
        }

    global_u = _num(standard_uncertainty)
    global_U = _num(expanded_uncertainty)
    if global_u is not None and global_u < 0:
        return {'points': [], 'u': None, 'U': None, 'max_error_percent': None,
                'guard_band': None, 'status': 'NO_DECISION',
                'errors': ['u نمی‌تواند منفی باشد.']}
    if global_U is not None and global_U < 0:
        return {'points': [], 'u': None, 'U': None, 'max_error_percent': None,
                'guard_band': None, 'status': 'NO_DECISION',
                'errors': ['U نمی‌تواند منفی باشد.']}
    if global_U is None and global_u is not None:
        global_U = global_u * coverage_factor
    elif global_U is not None:
        # U مرجع اصلی گزارش است و u از U/k بازسازی می‌شود تا تصمیم دوگانه ایجاد نشود.
        global_u = global_U / coverage_factor

    decision_rule = (decision_rule or 'simple').strip().lower()
    global_gb = _num(guard_band)
    factor = _num(guard_band_factor)
    if factor is None or factor < 0:
        return {'points': [], 'u': global_u, 'U': global_U, 'max_error_percent': None,
                'guard_band': None, 'status': 'NO_DECISION',
                'errors': ['ضریب Guard Band نامعتبر است.']}

    errors = []
    for p in points or []:
        raw_ref = p.get('reference') if isinstance(p, dict) else None
        raw_reading = p.get('reading') if isinstance(p, dict) else None
        # ردیف کاملاً خالی مجاز است؛ ردیف نیمه‌کاره باید صراحتاً NO_DECISION شود.
        if (raw_ref is None or str(raw_ref).strip() == '') and (raw_reading is None or str(raw_reading).strip() == ''):
            continue
        ref = _num(raw_ref)
        reading = _num(raw_reading)
        p2 = dict(p) if isinstance(p, dict) else {}
        if ref is None or reading is None:
            p2.update({'decision': 'NO_DECISION', 'message': 'Reference و Reading باید عدد معتبر باشند.'})
            out.append(p2)
            errors.append('حداقل یک نقطه Reference/Reading نامعتبر دارد.')
            continue

        error = reading - ref
        correction = ref - reading
        p2['reference'] = ref
        p2['reading'] = reading
        p2['error'] = error
        p2['correction'] = correction
        p2['C'] = correction
        p2['error_percent'] = (error / ref * 100.0) if ref != 0 else None

        # اگر MPE سراسری وجود دارد، آن را بر MPE قدیمیِ Browser مقدم می‌کنیم.
        point_mpe = _mpe_for_point(mpe, mpe_type, reading, range_min, range_max) if _num(mpe) is not None else _num(p.get('mpe'))
        p2['mpe'] = point_mpe

        # عدم‌قطعیت سراسری بر داده‌ی Point غالب است؛ فقط در حالت نبود داده‌ی سراسری از Point استفاده می‌شود.
        u_point = global_u if global_u is not None else _num(p.get('u'))
        U_point = global_U if global_U is not None else _num(p.get('U'))
        if U_point is None and u_point is not None:
            U_point = u_point * coverage_factor
        elif U_point is not None:
            u_point = U_point / coverage_factor
        if u_point is not None and u_point < 0:
            u_point = None
            U_point = None
            p2['uncertainty_error'] = 'u منفی است.'
        if U_point is not None and U_point < 0:
            u_point = None
            U_point = None
            p2['uncertainty_error'] = 'U منفی است.'
        p2['u'] = u_point
        p2['U'] = U_point

        if u_point is not None and point_mpe is not None:
            p2['tur_standard_u'] = point_mpe / u_point if u_point > 0 else None
            p2['tur'] = point_mpe / U_point if U_point and U_point > 0 else None
            p2['tur_basis'] = 'MPE/U' if U_point and U_point > 0 else None
        else:
            p2['tur'] = None
            p2['tur_basis'] = None

        gb = global_gb
        if gb is None and decision_rule == 'guard_band':
            if U_point is not None:
                gb = U_point * factor
            else:
                gb = _num(p.get('guard_band'))
        if gb is not None and gb < 0:
            p2['guard_band'] = None
            p2['decision'] = 'NO_DECISION'
            p2['message'] = 'Guard Band نمی‌تواند منفی باشد.'
            out.append(p2)
            continue
        p2['guard_band'] = gb

        if point_mpe is None:
            p2['decision'] = 'NO_DECISION'
            p2['pc'] = None
            p2['message'] = 'MPE معتبر برای این نقطه مشخص نشده است.'
        else:
            result = decide(
                error,
                lower=-point_mpe,
                upper=point_mpe,
                u=u_point,
                U=U_point,
                k=coverage_factor,
                rule=decision_rule,
                guard_band=gb,
                confidence=confidence,
                lower_inclusive=True,
                upper_inclusive=True,
            )
            p2['decision'] = result.get('status', 'NO_DECISION')
            p2['pc'] = result.get('pc')
            p2['message'] = result.get('message', '')
            for key in ('effective_lower', 'effective_upper', 'confidence_threshold', 'distribution_assumption'):
                if key in result:
                    p2[key] = result[key]
        out.append(p2)

    pct_errors = [abs(x['error_percent']) for x in out if x.get('error_percent') is not None and math.isfinite(x['error_percent'])]
    max_err_pct = round(max(pct_errors), 6) if pct_errors else None
    gb_final = global_gb
    if gb_final is None and decision_rule == 'guard_band' and global_U is not None:
        gb_final = global_U * factor

    status = 'PASS'
    if not out:
        status = 'NO_DATA'
    elif any(p.get('decision') == 'NO_DECISION' for p in out):
        status = 'NO_DECISION'
    elif any(p.get('decision') == 'FAIL' for p in out):
        status = 'FAIL'

    return {
        'points': out, 'u': global_u, 'U': global_U,
        'max_error_percent': max_err_pct, 'guard_band': gb_final,
        'status': status, 'errors': errors,
    }


def summarize_calibration(points, u=None, decision_rule='simple'):
    if not points:
        return {'decision': 'NO_DATA', 'pc': None, 'tur': None, 'tur_basis': 'MPE/U'}
    decisions = [p.get('decision') for p in points]
    if 'NO_DECISION' in decisions:
        decision = 'نیازمند تکمیل اطلاعات'
    elif all(x == 'PASS' for x in decisions):
        decision = 'قابل قبول'
    else:
        decision = 'مردود'
    pcs = [p['pc'] for p in points if _num(p.get('pc')) is not None]
    turs = [p['tur'] for p in points if _num(p.get('tur')) is not None]
    return {
        'decision': decision,
        'pc': min(pcs) if pcs else None,
        'tur': min(turs) if turs else None,
        'tur_basis': 'MPE/U'
    }


def calculate_uncertainty_budget(components, coverage_factor=2.0):
    """محاسبه uc و U از مؤلفه‌های Type A/B و Welch-Satterthwaite."""
    k = _num(coverage_factor)
    errors = []
    if k is None or k <= 0:
        return {'components': [], 'uc': None, 'U': None, 'k': None,
                'effective_degrees_of_freedom': None,
                'status': 'NO_DECISION', 'errors': ['k باید بزرگ‌تر از صفر باشد.']}

    prepared = []
    for comp in components or []:
        comp = dict(comp or {})
        name = str(comp.get('name') or '').strip()
        if not name:
            errors.append('نام یک مؤلفه عدم‌قطعیت خالی است.')
            continue
        ctype = str(comp.get('component_type') or 'B').strip().upper()
        if ctype not in {'A', 'B'}:
            errors.append(f'نوع مؤلفه «{name}» باید A یا B باشد.')
            continue
        sensitivity = _num(comp.get('sensitivity'))
        if sensitivity is None:
            sensitivity = 1.0
        value = _num(comp.get('value'))
        divisor = _num(comp.get('divisor'))
        if ctype == 'A' and divisor is None:
            divisor = 1.0
        if divisor is None or divisor <= 0:
            errors.append(f'Divisor مؤلفه «{name}» نامعتبر است.')
            continue
        observations_raw = comp.get('observations') or []
        observations = []
        for x in observations_raw:
            xv = _num(x)
            if xv is None:
                errors.append(f'مشاهده نامعتبر در مؤلفه «{name}».')
            else:
                observations.append(xv)

        df = _num(comp.get('degrees_of_freedom'))
        if ctype == 'A':
            if len(observations) < 2:
                errors.append(f'برای Type A مؤلفه «{name}» حداقل دو مشاهده لازم است.')
                continue
            mean = sum(observations) / len(observations)
            sd = math.sqrt(sum((x - mean) ** 2 for x in observations) / (len(observations) - 1))
            value = sd
            divisor = math.sqrt(len(observations))
            df = len(observations) - 1
        else:
            if value is None:
                errors.append(f'Value مؤلفه Type B «{name}» مشخص نشده است.')
                continue

        ui = abs(value / divisor)
        signed = sensitivity * ui
        prepared.append({
            **comp,
            'name': name,
            'component_type': ctype,
            'standard_uncertainty': ui,
            'contribution': abs(signed),
            'signed_contribution': signed,
            'degrees_of_freedom': df,
            'observations': observations,
        })

    if errors:
        return {'components': prepared, 'uc': None, 'U': None, 'k': k,
                'effective_degrees_of_freedom': None,
                'status': 'NO_DECISION', 'errors': errors}

    variance = sum(row['signed_contribution'] ** 2 for row in prepared)
    df_terms = []
    for row in prepared:
        df = _num(row.get('degrees_of_freedom'))
        if df is not None:
            if df <= 0:
                return {'components': prepared, 'uc': None, 'U': None, 'k': k,
                        'effective_degrees_of_freedom': None,
                        'status': 'NO_DECISION', 'errors': [f'DF مؤلفه «{row["name"]}» باید بزرگ‌تر از صفر باشد.']}
            df_terms.append((row['signed_contribution'] ** 4) / df)

    # کوواریانس فقط بین مؤلفه‌های یک گروه مشترک و با rho معتبر.
    for i in range(len(prepared)):
        gi = (prepared[i].get('correlation_group') or '').strip()
        if not gi:
            continue
        for j in range(i + 1, len(prepared)):
            gj = (prepared[j].get('correlation_group') or '').strip()
            if gi != gj:
                continue
            rho_i = _num(prepared[i].get('correlation_coefficient'))
            rho_j = _num(prepared[j].get('correlation_coefficient'))
            if rho_i is not None and rho_j is not None and abs(rho_i - rho_j) > 1e-12:
                return {'components': prepared, 'uc': None, 'U': None, 'k': k,
                        'effective_degrees_of_freedom': None, 'status': 'NO_DECISION',
                        'errors': [f'ضرایب همبستگی گروه «{gi}» یکسان نیستند.']}
            rho = rho_i if rho_i is not None else rho_j
            if rho is None or not -1.0 <= rho <= 1.0:
                return {'components': prepared, 'uc': None, 'U': None, 'k': k,
                        'effective_degrees_of_freedom': None, 'status': 'NO_DECISION',
                        'errors': [f'ضریب همبستگی گروه «{gi}» نامعتبر است.']}
            variance += 2.0 * rho * prepared[i]['signed_contribution'] * prepared[j]['signed_contribution']

    uc = math.sqrt(max(0.0, variance))
    denominator = sum(df_terms)
    effective_df = (uc ** 4 / denominator) if uc > 0 and denominator > 0 else None
    U = k * uc
    return {
        'components': prepared, 'uc': uc, 'U': U, 'k': k,
        'effective_degrees_of_freedom': effective_df,
        'status': 'PASS', 'errors': [],
    }
