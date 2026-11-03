"""
موتور محاسبه عدم‌قطعیت اندازه‌گیری — پورت پایتونی از فایل اکسل
«calculate uncertainty final1405.01.xlsm»

هر تابع یک دیکشنری برمی‌گرداند:
{
  'parameters': [ {name, symbol, unit, mean, u_c, U, k, U_percent, rows: [...]} ],
  'summary': {...},
}
هر ردیف بودجه (row):
{symbol, source, distribution, value, unit, u, sens, contrib, note}
"""

import math
from .precision_spectro_v2 import analyze_precision

# ---------------------------------------------------------------
# توابع کمکی آماری
# ---------------------------------------------------------------

_PERSIAN = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def _f(v, default=None):
    """تبدیل امن به float؛ ارقام فارسی/عربی و ممیز فارسی هم پشتیبانی می‌شود."""
    if v is None:
        return default
    s = str(v).strip().translate(_PERSIAN)
    if s == '':
        return default
    s = s.replace('٫', '.').replace(',', '').replace(' ', '')
    try:
        x = float(s)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


def mean(vals):
    return sum(vals) / len(vals)


def stdev(vals):
    """انحراف معیار نمونه‌ای (معادل STDEV اکسل، n-1)."""
    n = len(vals)
    if n < 2:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1))


def _vals(lst, key='v'):
    """استخراج مقادیر عددی از لیست قرائت‌ها — هم لیست ساده و هم سطرهای دیکشنری فرم."""
    out = []
    for item in lst or []:
        v = item.get(key) if isinstance(item, dict) else item
        x = _f(v)
        if x is not None:
            out.append(x)
    return out


def t_factor(nu):
    """فاکتور t دوطرفه 95% (همان جدول شیت Impact اکسل؛ برای ν بزرگ → 1.96)."""
    table = [
        (1, 12.71), (2, 4.30), (3, 3.18), (4, 2.78), (5, 2.57),
        (6, 2.45), (7, 2.36), (8, 2.31), (9, 2.26), (10, 2.23),
        (11, 2.20), (12, 2.18), (13, 2.16), (14, 2.14), (15, 2.13),
        (16, 2.12), (17, 2.11), (18, 2.10), (19, 2.09), (20, 2.09),
        (25, 2.06), (30, 2.05), (40, 2.02), (60, 2.00), (120, 1.98),
    ]
    if nu <= 0:
        nu = 1
    prev_b, prev_t = 1, table[0][1]
    for bound, tval in table:
        if nu <= bound:
            if nu > prev_b and bound > prev_b:
                frac = (nu - prev_b) / (bound - prev_b)
                return prev_t + frac * (tval - prev_t)
            return tval
        prev_b, prev_t = bound, tval
    return 1.96


def row(symbol, source, distribution, value, unit, u, sens=1.0, note=''):
    """ساخت یک ردیف بودجه؛ سهم بعداً محاسبه می‌شود."""
    return {
        'symbol': symbol, 'source': source, 'distribution': distribution,
        'value': value, 'unit': unit, 'u': u,
        'sens': sens, 'contribution_in_output': u * sens,
        'note': note,
    }


def finalize_parameter(name, symbol, unit, mean_val, rows, k=2.0, denom=None):
    """u ترکیبی، U گسترش‌یافته و درصد سهم هر مؤلفه را نهایی می‌کند."""
    u_c = math.sqrt(sum(r['contribution_in_output'] ** 2 for r in rows))
    U = k * u_c
    denom = denom if denom else mean_val
    U_percent = (U / denom * 100) if denom else None
    for r in rows:
        c = r['contribution_in_output']
        r['contrib_percent'] = (c * c / (u_c * u_c) * 100) if u_c > 0 else 0.0
        r['k'] = k
    return {
        'name': name, 'symbol': symbol, 'unit': unit,
        'mean': mean_val, 'u_c': u_c, 'U': U, 'k': k,
        'U_percent': U_percent, 'rows': rows,
    }


def _num(v):
    return v if v is not None else 0.0


def _env_u(p, measurand):
    """عدم‌قطعیت شرایط محیطی (دما) — محاسبهٔ خودکار از روی دما.
    u_env = |Y| × sens_per_°C × |T_test − T_ref| / √3   (توزیع مستطیلی).
    sens_per_°C وابسته به متریال است. اگر u_env دستی هم وارد شده باشد، RSS می‌شود."""
    manual = _f(p.get('u_env'))
    temp = _f(p.get('test_temp'))
    parts = []
    if manual is not None:
        parts.append(manual)
    if temp is not None and measurand:
        ref = _f(p.get('ref_temp'), 23.0)
        mat = (p.get('material') or 'steel').strip().lower()
        sens = {'steel': 0.0005, 'stainless': 0.0005, 'aluminum': 0.0012,
                'copper': 0.0010, 'cast_iron': 0.0003, 'titanium': 0.0004,
                'nickel': 0.0004}.get(mat, 0.0005)
        delta = abs(temp - ref)
        parts.append(abs(measurand) * sens * delta / math.sqrt(3))
    if not parts:
        return None
    return math.sqrt(sum(x * x for x in parts))


# ---------------------------------------------------------------
# ۱) کشش — تخت / گرد  (Rm ، Rp0.2 ، Reh ، %EL)
# ---------------------------------------------------------------

def calc_tensile(p):
    """p: machine_u, machine_res, cal_u, cal_res, shape, readings[]"""
    shape = p.get('shape', 'round')
    m_u = _f(p.get('machine_u'), 0.0)
    m_res = _f(p.get('machine_res'), 0.0)
    c_u = _f(p.get('cal_u'), 0.0)
    c_res = _f(p.get('cal_res'), 0.0)

    readings = [r for r in p.get('readings', []) if any(_f(v) is not None for v in r.values())]
    if not readings:
        raise ValueError('هیچ قرائتی وارد نشده است.')

    n = len(readings)
    uF = math.sqrt((_num(m_u) / 2) ** 2 + (m_res / math.sqrt(12)) ** 2)  # عدم‌قطعیت نیرو (N)

    # مساحت هر قرائت
    areas, d_vals, t_vals, w_vals = [], [], [], []
    for r in readings:
        if shape == 'round':
            d = _f(r.get('d0'))
            if d:
                d_vals.append(d)
                areas.append(math.pi * d * d / 4)
        else:
            t, w = _f(r.get('thk')), _f(r.get('wide'))
            if t and w:
                t_vals.append(t)
                w_vals.append(w)
                areas.append(t * w)
    if not areas:
        raise ValueError('ابعاد نمونه (قطر یا ضخامت/عرض) وارد نشده است.')
    A = mean(areas)

    params = []

    # --- پارامترهای استحکام: Rm ، Rp0.2 ، Reh ---
    # منطق مطابق اکسل: ورودی نیرو (N) است؛ σ = F/A ؛ ∂σ/∂F = 1/A ؛ ∂σ/∂d = 2σ/d̄
    strength_defs = [('rm', 'Rm', 'مقاومت کششی'), ('rp02', 'Rp0.2', 'تنش تسلیم اسمی'),
                     ('reh', 'Reh', 'حد تسلیم بالایی')]
    for key, sym, title in strength_defs:
        vals = [_f(r.get(key)) for r in readings]
        vals = [v for v in vals if v is not None]
        if len(vals) < 2:
            continue
        P = mean(vals)              # نیروی متوسط (N)
        sigma = P / A               # تنس متوسط (MPa = N/mm²)
        sP = stdev(vals)
        inv_A = 1.0 / A
        rows = []
        rows.append(row('u(F)_cal', 'کالیبراسیون دستگاه کشش', 'نرمال',
                        m_u, 'N', m_u / 2, sens=inv_A, note='U/2 با k=2'))
        rows.append(row('u(F)_res', 'رزولوشن دستگاه کشش', 'مستطیلی',
                        m_res, 'N', m_res / math.sqrt(12), sens=inv_A))
        # Type A — تکرارپذیری بین‌نمونه‌ها (الزام رویه سری آزمون؛ GUM/ISO 5725):
        # حساسیت صحیح ∂σ/∂F = 1/A (اکسل مرجع به‌اشتباه 1/A² می‌گرفت)
        include_rep = str(p.get('include_rep', '')).strip().lower()
        if shape == 'round' and include_rep == '':
            include_rep = '1'
        if include_rep in ('1', 'true', 'yes', 'on', 'بله'):
            rows.append(row('u(F)_rep', 'تکرارپذیری نیرو (Type A — سری آزمون)', 'نرمال',
                            sP, 'N', sP / math.sqrt(n), sens=inv_A,
                            note=f's (تک اندازه‌گیری)، n={n}'))
        if shape == 'round':
            d_mean = mean(d_vals)
            s_d = stdev(d_vals)
            sens_d = 2.0 * sigma / d_mean     # ∂σ/∂d
            rows.append(row('u(d)_cal', 'کالیبراسیون کولیس (قطر)', 'نرمال',
                            c_u, 'mm', c_u / 2, sens=sens_d))
            rows.append(row('u(d)_res', 'رزولوشن کولیس', 'مستطیلی',
                            c_res, 'mm', c_res / math.sqrt(12), sens=sens_d))
            if s_d > 0:
                rows.append(row('u(d)_rep', 'تکرارپذیری قطرسنجی (COP07 Eqn.12)', 'نرمال',
                                s_d, 'mm', s_d / math.sqrt(n), sens=sens_d))
        else:
            t_m, w_m = mean(t_vals), mean(w_vals)
            s_t, s_w = stdev(t_vals), stdev(w_vals)
            ut = math.sqrt((c_u / 2) ** 2 + (c_res / math.sqrt(12)) ** 2)
            uw = ut
            rows.append(row('u(t)', 'عدم‌قطعیت ضخامت (کالیبراسیون+رزولوشن کولیس)', 'ترکیبی',
                            t_m, 'mm', ut, sens=sigma / t_m))
            if s_t > 0:
                rows.append(row('u(t)_rep', 'تکرارپذیری ضخامت', 'نرمال',
                                s_t, 'mm', s_t / math.sqrt(n), sens=sigma / t_m))
            rows.append(row('u(w)', 'عدم‌قطعیت عرض (کالیبراسیون+رزولوشن کولیس)', 'ترکیبی',
                            w_m, 'mm', uw, sens=sigma / w_m))
            if s_w > 0:
                rows.append(row('u(w)_rep', 'تکرارپذیری عرض', 'نرمال',
                                s_w, 'mm', s_w / math.sqrt(n), sens=sigma / w_m))
        u_env = _env_u(p, sigma)
        if u_env:
            rows.append(row('u_env', 'شرایط محیطی/دما (خودکار از دما + دستی)', 'نرمال',
                            u_env, 'MPa', u_env, 1.0, note='COP07'))
        params.append(finalize_parameter(f'{title} ({sym})', sym, 'MPa', sigma, rows, denom=sigma))

    # --- ازدیاد طول نسبی %EL ---
    l0_vals = [_f(r.get('l0')) for r in readings]
    l1_vals = [_f(r.get('l1')) for r in readings]
    pairs = [(a, b) for a, b in zip(l0_vals, l1_vals) if a and b]
    if len(pairs) >= 2:
        el = [100.0 * (b - a) / a for a, b in pairs]
        EL = mean(el)
        s_el = stdev(el)
        uL = math.sqrt((c_u / 2) ** 2 + (c_res / math.sqrt(12)) ** 2)
        l0_m = mean([a for a, _ in pairs])
        l1_m = mean([b for _, b in pairs])
        # ∂e/∂L1 = 100/L0 ؛ ∂e/∂L0 = −100·L1/L0² → حساسیت مؤثر هر قرائت طول
        sens_L = 100.0 * math.sqrt(1.0 / l0_m ** 2 + l1_m ** 2 / l0_m ** 4)
        rows = [
            row('u(rep)', 'تکرارپذیری ازدیاد طول', 'نرمال', s_el, '%',
                s_el / math.sqrt(len(pairs)), 1.0, note=f's (تک اندازه‌گیری) ، n={len(pairs)}'),
            row('u(L)_cal', 'کالیبراسیون کولیس (طول‌سنجی)', 'نرمال', c_u, 'mm',
                c_u / 2, sens=sens_L),
            row('u(L)_res', 'رزولوشن کولیس', 'مستطیلی', c_res, 'mm',
                c_res / math.sqrt(12), sens=sens_L),
        ]
        params.append(finalize_parameter('ازدیاد طول نسبی (%EL)', 'EL', '%', EL, rows, denom=EL))

    # خلاصه
    # --- کاهش سطح مقطع %RA (فقط نمونه گرد) ---
    if shape == 'round':
        ra_pairs = []
        for r in readings:
            d0, d1 = _f(r.get('d0')), _f(r.get('d1'))
            if d0 and d1 and d0 > 0:
                ra_pairs.append((d0, d1))
        if len(ra_pairs) >= 2:
            ras = [100.0 * (1.0 - (d1 / d0) ** 2) for d0, d1 in ra_pairs]
            RA = mean(ras)
            s_ra = stdev(ras)
            d0_m = mean([a for a, _ in ra_pairs])
            d1_m = mean([b for _, b in ra_pairs])
            u_d = math.sqrt((c_u / 2) ** 2 + (c_res / math.sqrt(12)) ** 2)
            # ∂RA/∂d0 = 200·d1²/d0³ ؛ ∂RA/∂d1 = −200·d1/d0²
            sens_d0 = 200.0 * d1_m ** 2 / d0_m ** 3
            sens_d1 = 200.0 * d1_m / d0_m ** 2
            rows = [
                row('u(rep)', 'تکرارپذیری کاهش سطح مقطع', 'نرمال', s_ra, '%',
                    s_ra / math.sqrt(len(ras)), 1.0, note=f's (تک اندازه‌گیری) ، n={len(ras)}'),
                row('u(d0)', 'عدم‌قطعیت D0 (کولیس+رزولوشن)', 'ترکیبی', d0_m, 'mm',
                    u_d, sens_d0),
                row('u(d1)', 'عدم‌قطعیت D1 (کولیس+رزولوشن)', 'ترکیبی', d1_m, 'mm',
                    u_d, sens_d1),
            ]
            params.append(finalize_parameter('کاهش سطح مقطع (%RA)', 'RA', '%', RA, rows, denom=RA))

    # --- بازه دستگاه (مطابق منطق شیت INPUT اکسل) ---
    machine_code = str(p.get('machine_code') or p.get('machine') or '').strip().upper()
    force_cal = _f(p.get('force_cal'))
    range_label = str(p.get('range_label') or '').strip().lower()
    range_auto = ''
    if machine_code in ('TT-73-01', 'TT-73-02') and force_cal:
        if machine_code == 'TT-73-01':
            range_auto = 'Low Range' if force_cal < 150000 else ('Middle Range' if force_cal < 250000 else 'High Range')
        else:
            range_auto = 'Low Range' if force_cal < 300000 else ('Middle Range' if force_cal < 600000 else 'High Range')
    if range_label in ('low', 'middle', 'high'):
        range_fa = {'low': 'Low Range', 'middle': 'Middle Range', 'high': 'High Range'}[range_label]
    else:
        range_fa = range_auto

    summary = {
        'نوع نمونه': 'گرد' if shape == 'round' else 'تخت',
        'تعداد قرائت': n,
        'مساحت متوسط (mm²)': round(A, 4),
        'عدم‌قطعیت نیرو (N)': round(uF, 4),
        'بازه دستگاه': range_fa or '—',
        'پارامترهای محاسبه‌شده': ', '.join(x['symbol'] for x in params),
    }
    if range_fa:
        for prm in params:
            prm['range'] = range_fa
    return {'parameters': params, 'summary': summary}


# ---------------------------------------------------------------
# ۲) سختی راکول (HRA / HRB / HRC) — مطابق شیت Rockwell
# ---------------------------------------------------------------

def _rockwell_bE(scale, x):
    """حداکثر بایاس مجاز bE (جدول شیت اکسل R19 — مطابق ISO 6508)."""
    if scale == 'HRA':
        return 2.0 if 20 < x <= 75 else 1.5
    if scale == 'HRB':
        if x <= 45:
            return 4.0
        return 3.0 if x <= 80 else 2.0
    if scale == 'HRC':
        return 1.5
    return 0.0


def calc_rockwell(p):
    crm = _f(p.get('crm_value'))
    res = _f(p.get('resolution'), 0.0)
    u_cert = _f(p.get('u_htm'), 0.0)      # U گزارش راستی‌آزمایی غیرمستقیم (HTM)
    scale = (p.get('scale') or 'HRC').strip().upper()
    r1 = _vals(p.get('readings1'))
    r2 = _vals(p.get('readings2'))
    if not crm or len(r1) < 2:
        raise ValueError('مقدار CRM و حداقل ۲ قرائت لازم است.')

    n1 = len(r1)
    m1 = mean(r1)
    s1 = stdev(r1)
    rows = []
    rows.append(row('u_rep', 'تکرارپذیری (۵ قرائت روی نمونه/CRM)', 'نرمال',
                    s1, scale, s1 / math.sqrt(n1), 1.0, note=f's (تک اندازه‌گیری) ، n={n1}'))
    u_reprod = 0.0
    if len(r2) >= 2:
        pairs = [(a + b) / 2 for a, b in zip(r1, r2[:n1])]
        u_reprod = stdev(pairs) / math.sqrt(len(pairs))
        rows.append(row('u_reprod', 'بازتولیدپذیری (دو دستگاه/اپراتور)', 'نرمال',
                        stdev(pairs), scale, u_reprod, 1.0))
    rows.append(row('u_reso', 'رزولوشن دستگاه', 'مستطیلی',
                    res, scale, res / (2 * math.sqrt(3)), 1.0, note='a/2√3'))
    if u_cert:
        rows.append(row('u_htm', 'U راستی‌آزمایی غیرمستقیم (HTM)', 'نرمال',
                        u_cert, scale, u_cert / 2, 1.0, note='U/2'))
    u_env = _env_u(p, m1)
    if u_env:
        rows.append(row('u_env', 'شرایط محیطی/دما (خودکار از دما + دستی)', 'نرمال',
                        u_env, scale, u_env, 1.0, note='COP06 A4'))
    u_c = math.sqrt(sum(r['contribution_in_output'] ** 2 for r in rows))
    b = m1 - crm
    bE = _rockwell_bE(scale, m1)
    k = 2.0
    U_M1 = k * u_c
    U_M2 = U_M1 + abs(b)
    U_ASTM = U_M1 + bE
    method = (p.get('std_method') or 'M2').strip().upper()
    if method == 'M1':
        U_report = U_M1
    elif method == 'ASTM':
        U_report = U_ASTM
    else:
        U_report = U_M2
    for r in rows:
        c = r['contribution_in_output']
        r['contrib_percent'] = (c * c / (u_c * u_c) * 100) if u_c > 0 else 0.0
    param = {
        'name': f'سختی راکول ({scale})', 'symbol': scale, 'unit': scale,
        'mean': m1, 'u_c': u_c, 'U': U_report, 'k': k,
        'U_percent': (U_report / m1 * 100) if m1 else None,
        'rows': rows,
        'extras': {
            'CRM': crm,
            'b (بایاس اندازه‌گیری‌شده)': round(b, 4),
            'bE (حداکثر بایاس مجاز)': bE,
            'U (M1) = k·u': round(U_M1, 4),
            'U (M2) = k·u + |b|': round(U_M2, 4),
            'U (ASTM) = k·u + bE': round(U_ASTM, 4),
            'روش گزارش': method,
            'نتیجه تصحیح‌شده': f'{round(m1 - b, 2)} ± {round(U_M1, 2)} {scale}',
            'وضعیت بایاس': 'قابل قبول' if abs(b) <= bE else '⚠ بیش از حد مجاز',
        },
    }
    summary = {
        'مقیاس': scale, 'مقدار CRM': crm, 'میانگین قرائت‌ها': round(m1, 3),
        'تعداد قرائت': n1, 'بایاس': round(b, 4), 'حد مجاز بایاس': bE,
    }
    return {'parameters': [param], 'summary': summary}


# ---------------------------------------------------------------
# ۳) سختی ویکرز / میکروویکرز — مطابق شیت Vickers / MHV
# ---------------------------------------------------------------

def calc_vickers(p, micro=False):
    X = _f(p.get('crm_value'))
    U_crm = _f(p.get('u_crm'), 0.0)
    res = _f(p.get('resolution'), 0.0)   # میلی‌متر
    r1 = _vals(p.get('readings1'))   # قرائت HV روی نمونه
    r_crm = _vals(p.get('readings_crm'))  # قرائت روی CRM
    d_vals = _vals(p.get('d_readings'))   # قطرها mm
    unit = 'HV'
    if not X or len(r1) < 2:
        raise ValueError('مقدار CRM و حداقل ۲ قرائت لازم است.')

    n1 = len(r1)
    m1 = mean(r1)
    s1 = stdev(r1)
    d_bar = mean(d_vals) if d_vals else 0.0
    rows = []
    # U_H = t·s_H با t=1.14 برای n=5 (مطابق اکسل)
    U_H = 1.14 * s1
    # u_ms: رزولوشن قطری → حساسیت (2X/d̄)
    a_opt = math.sqrt(res ** 2 + (0.00058 / 1.5) ** 2)
    u_ms = (2 * m1 / d_bar) * (a_opt / math.sqrt(12)) if d_bar else 0.0
    s_crm = stdev(r_crm) if len(r_crm) >= 2 else 0.0
    # Drift دستگاه: در اکسل عدد هاردکد 2 (HV²) بود؛ اینجا پارامتر مستند از ورودی —
    # اگر گواهی/راستی‌آزمایی مقدار drift نداده باشد صفر است (مؤلفه بدون مبنا جمع نمی‌شود).
    drift = _f(p.get('drift'), 0.0) or 0.0
    u_htm = 0.5 * math.sqrt(s_crm ** 2 + drift ** 2 + (U_crm / 2) ** 2 + u_ms ** 2)
    rows.append(row('U_H', 'پراکندگی ۵ قرائت (t=1.14)', 'نرمال',
                    s1, unit, U_H, 1.0, note='U_H = 1.14·s'))
    if u_ms:
        rows.append(row('u_ms', 'رزولوشن اندازه‌گیری قطر فرورفتگی', 'مستطیلی',
                        res, 'mm', u_ms, 1.0))
    rows.append(row('u_htm', 'راستی‌آزمایی غیرمستقیم با CRM', 'نرمال',
                    U_crm, unit, u_htm, 1.0, note='½·√(s²_CRM+drift²+(U/2)²+u_ms²)'))
    u_env = _env_u(p, m1)
    if u_env:
        rows.append(row('u_env', 'شرایط محیطی/دما (خودکار از دما + دستی)', 'نرمال',
                        u_env, unit, u_env, 1.0, note='COP06 A4'))
    u_c_M1 = math.sqrt(U_H ** 2 + (2 * u_ms ** 2) + u_htm ** 2 + (u_env or 0.0) ** 2)
    k = 2.0
    U_M1 = k * u_c_M1
    # بایاس و u_e
    b = 0.0
    if len(r_crm) >= 2:
        b = mean(r_crm) - X
    u_e = abs(b) / math.sqrt(3) if b else 0.0
    U_M2 = k * math.sqrt(U_H ** 2 + 2 * u_ms ** 2 + u_e ** 2) if b else None
    for r in rows:
        c = r['contribution_in_output']
        r['contrib_percent'] = (c * c / (u_c_M1 * u_c_M1) * 100) if u_c_M1 > 0 else 0.0
    title = 'میکروسختی ویکرز' if micro else 'سختی ویکرز'
    param = {
        'name': title, 'symbol': unit, 'unit': unit,
        'mean': m1, 'u_c': u_c_M1, 'U': U_M1, 'k': k,
        'U_percent': (U_M1 / m1 * 100) if m1 else None,
        'rows': rows,
        'extras': {
            'X (مقدار CRM)': X,
            'b (بایاس)': round(b, 4) if b else '—',
            'U (M1)': round(U_M1, 3),
            'U (M2) با تصحیح بایاس': round(U_M2, 3) if U_M2 else '—',
            'X_corr = X − b': round(m1 - b, 2) if b else round(m1, 2),
            'U%': round(U_M1 / m1 * 100, 2) if m1 else '—',
        },
    }
    summary = {
        'روش': 'M1 (با u_htm)', 'مقدار CRM': X, 'میانگین قرائت': round(m1, 2),
        'تعداد قرائت': n1, 'میانگین قطر (mm)': round(d_bar, 5) if d_bar else '—',
    }
    return {'parameters': [param], 'summary': summary}


# ---------------------------------------------------------------
# ۴) سختی برینل — مطابق شیت Brinell
# ---------------------------------------------------------------

def calc_brinell(p):
    X = _f(p.get('crm_value'))
    U_crm = _f(p.get('u_crm'), 0.0)
    res = _f(p.get('resolution'), 0.0)     # mm
    ball = _f(p.get('ball_dia'), 2.5)      # mm
    r1 = _vals(p.get('readings1'))   # HBW
    d_vals = _vals(p.get('d_readings'))  # mm
    if not X or len(r1) < 2:
        raise ValueError('مقدار CRM و حداقل ۲ قرائت لازم است.')
    n1 = len(r1)
    m1 = mean(r1)
    s1 = stdev(r1)
    d_bar = mean(d_vals) if d_vals else 0.0
    # Erel طبق ISO 6506-2
    if X < 250:
        Erel = 0.03
    elif X <= 450:
        Erel = 0.025
    else:
        Erel = 0.02
    U_mpe = Erel * X
    u_mpe = U_mpe / math.sqrt(3)
    U_H = 1.14 * s1
    b = m1 - X
    # u_ms از رزولوشن قطری (مطابق فرمول D16 اکسل)
    if d_bar and d_bar < ball:
        root = math.sqrt(ball ** 2 - d_bar ** 2)
        u_ms = (res / math.sqrt(12)) * (X / d_bar) * ((ball + root) / root)
    else:
        u_ms = 0.0
    rows = [
        row('u_CRM', 'عدم‌قطعیت گواهی CRM', 'نرمال', U_crm, 'HBW',
            U_crm / 2, 1.0, note='U/2'),
        row('U_H', 'پراکندگی قرائت‌ها (t=1.14)', 'نرمال', s1, 'HBW', U_H, 1.0),
        row('u_ms', 'رزولوشن اندازه‌گیری قطر فرورفتگی', 'مستطیلی', res, 'mm', u_ms, 1.0),
        row('u_mpe', 'خطای مجاز روش (ISO 6506-2)', 'مستطیلی', U_mpe, 'HBW',
            u_mpe, 1.0, note=f'Erel={Erel * 100:.1f}%'),
    ]
    u_env = _env_u(p, m1)
    if u_env:
        rows.append(row('u_env', 'شرایط محیطی/دما (خودکار از دما + دستی)', 'نرمال',
                        u_env, 'HBW', u_env, 1.0, note='COP06 A4'))
    u_c = math.sqrt(sum(r['contribution_in_output'] ** 2 for r in rows))
    k = 2.0
    U_M1 = k * u_c
    U_M2 = k * math.sqrt((U_crm / 2) ** 2 + U_H ** 2 + u_ms ** 2) + abs(b)
    for r in rows:
        c = r['contribution_in_output']
        r['contrib_percent'] = (c * c / (u_c * u_c) * 100) if u_c > 0 else 0.0
    param = {
        'name': 'سختی برینل', 'symbol': 'HBW', 'unit': 'HBW',
        'mean': m1, 'u_c': u_c, 'U': U_M1, 'k': k,
        'U_percent': (U_M1 / m1 * 100) if m1 else None,
        'rows': rows,
        'extras': {
            'X (CRM)': X,
            'b (بایاس)': round(b, 4),
            'Erel (ISO 6506-2)': f'{Erel * 100:.1f}%',
            'U (M1)': round(U_M1, 3),
            'U (M2) = k·u + |b|': round(U_M2, 3),
            'U%': round(U_M1 / m1 * 100, 2) if m1 else '—',
        },
    }
    summary = {
        'قطر گوی (mm)': ball, 'مقدار CRM': X, 'میانگین قرائت': round(m1, 2),
        'میانگین قطر فرورفتگی (mm)': round(d_bar, 4) if d_bar else '—',
    }
    return {'parameters': [param], 'summary': summary}


# ---------------------------------------------------------------
# ۵) ضربه (شارپی) — مطابق شیت Impact با Welch–Satterthwaite
# ---------------------------------------------------------------

def calc_impact(p):
    crm = _f(p.get('crm_value'))
    U_cert = _f(p.get('u_cert'), 0.0)
    res = _f(p.get('resolution'), 0.0)
    material_ref = _f(p.get('material_ref'))   # نمونه مرجع داخلی (WRM) — اختیاری
    r_crm = _vals(p.get('readings_crm'))
    r_mat = _vals(p.get('readings_material'))
    if not crm or len(r_mat) < 2:
        raise ValueError('مقدار CRM و حداقل ۲ قرائت نمونه لازم است. مقادیر را با ارقام انگلیسی و نقطه اعشار وارد کنید.')
    n_crm = len(r_crm) if len(r_crm) >= 2 else 1
    n_mat = len(r_mat)
    m_mat = mean(r_mat)
    u_cert = U_cert / 2
    u_rep = s  # اصلاح if n_crm >= 2 else 0.0
    u_mat = stdev(r_mat) / math.sqrt(n_mat)
    if res > 0.1:
        u_reso = res / math.sqrt(3)
    else:
        u_reso = res / math.sqrt(12)
    u_dim = (0.01 * m_mat) / math.sqrt(3)
    rows = [
        row('u_cert', 'عدم‌قطعیت گواهی CRM', 'نرمال', U_cert, 'J', u_cert, 1.0),
        row('u_rep', 'تکرارپذیری روی CRM', 'نرمال', stdev(r_crm) if n_crm >= 2 else 0, 'J',
            u_rep, 1.0, note=f's (تک اندازه‌گیری) ، n={n_crm}'),
        row('u_mat', 'تکرارپذیری روی نمونه', 'نرمال', stdev(r_mat), 'J', u_mat, 1.0,
            note=f's (تک اندازه‌گیری) ، n={n_mat}'),
        row('u_reso', 'رزولوشن دستگاه', 'مستطیلی', res, 'J', u_reso, 1.0),
        row('u_dim', 'ابعاد نمونه (۱٪)', 'مستطیلی', 0.01 * m_mat, 'J', u_dim, 1.0),
    ]
    u_env = _env_u(p, m_mat)
    if u_env:
        rows.append(row('u_env', 'شرایط محیطی/دما (cT·uT)', 'نرمال',
                        u_env, 'J', u_env, 1.0, note='COP06 A4'))
    u_c = math.sqrt(sum(r['contribution_in_output'] ** 2 for r in rows))
    # درجه آزادی مؤثر Welch–Satterthwaite (فقط دو مؤلفه دارای تکرار)
    num = u_c ** 4
    den = 0.0
    if u_rep > 0:
        den += u_rep ** 4 / max(n_crm - 1, 1)
    if u_mat > 0:
        den += u_mat ** 4 / max(n_mat - 1, 1)
    nu_eff = (num / den) if den > 0 else 10 ** 9
    t = t_factor(nu_eff)
    U = t * u_c
    # بایاس مطابق شیت Impact اکسل: N2 = |x̄₂ − مقدار WRM| (نمونه مرجع خود آزمایشگاه
    # در همان سطح انرژی — کوچک و معنادار). اگر WRM داده نشده باشد، مطابق COP 06
    # خطای نسبی دستگاه eA1%×x̄₂ اعمال می‌شود؛ و با انتخاب «بدون بایاس» حذف می‌شود.
    bias_mode = (p.get('bias_mode') or 'auto').strip().lower()
    wrm = material_ref
    if wrm is not None:
        bias_lin = abs(m_mat - wrm)
        bias_note = f'|x̄₂ − WRM| = |{round(m_mat, 2)} − {wrm}| (مطابق N2 شیت اکسل)'
    elif _f(p.get('machine_err_pct')) is not None:
        bias_lin = abs(_f(p.get('machine_err_pct'))) / 100.0 * m_mat
        bias_note = 'eA1% × x̄₂ از گواهی کالیبراسیون (COP 06)'
    elif bias_mode != 'none' and len(r_crm) >= 2 and crm:
        err_pct = abs(mean(r_crm) - crm) / crm
        bias_lin = err_pct * m_mat
        bias_note = 'eA1% × x̄₂ از قرائت‌های CRM (COP 06)'
    else:
        bias_lin = 0.0
        bias_note = 'بدون بایاس'
    if bias_mode == 'none':
        bias_lin = 0.0
        bias_note = 'بدون بایاس (انتخاب کاربر)'
    U_total = U + bias_lin
    for r in rows:
        c = r['contribution_in_output']
        r['contrib_percent'] = (c * c / (u_c * u_c) * 100) if u_c > 0 else 0.0
        r['k'] = t
    param = {
        'name': 'انرژی ضربه', 'symbol': 'KV', 'unit': 'J',
        'mean': m_mat, 'u_c': u_c, 'U': U_total, 'k': t,
        'U_percent': (U_total / m_mat * 100) if m_mat else None,
        'rows': rows,
        'extras': {
            'مقدار CRM (E_BCR)': crm,
            'نمونه مرجع WRM': wrm if wrm is not None else '—',
            'بایاس خطی اعمال‌شده': round(bias_lin, 3),
            'مبنا': bias_note,
            'روش': 'UNCERT COP 06:2000 + N2 شیت اکسل',
            'درجه آزادی مؤثر ν_eff': nu_eff if nu_eff < 10 ** 9 else '∞',
            'فاکتور t (95%)': t,
            'U (بدون بایاس)': round(U, 3),
            'U کل = t·u + |b|': round(U_total, 3),
            'U%': round(U_total / m_mat * 100, 2) if m_mat else '—',
        },
    }
    summary = {
        'روش': 'UNCERT COP 06', 'مقدار CRM': crm,
        'میانگین نمونه': round(m_mat, 2),
        'بایاس': round(bias_lin, 2),
        'ν مؤثر': nu_eff if nu_eff < 10 ** 9 else '∞', 'k_p': t,
    }
    return {'parameters': [param], 'summary': summary}


# ---------------------------------------------------------------
# ۶) اندازه دانه — دو روش (مقایسه‌ای / شمارش تقاطعی) مطابق شیت Grain
# ---------------------------------------------------------------

def calc_grain(p):
    """ورودی‌های عمومی: u_cert_machine (Ucert.), nاختیاری"""
    method = p.get('method', 'comparison')
    u_cert = _f(p.get('u_cert_machine'), 0.0)
    # --- روش ۱: مقایسه‌ای (Comparison) ---
    r_comp = _vals(p.get('readings_comparison'))
    # --- روش ۲: تقاطعی (Intercept) ---
    r_int = _vals(p.get('readings_intercept'))
    params = []
    if method in ('comparison', 'both') and len(r_comp) >= 2:
        n = len(r_comp)
        m = mean(r_comp)
        s = stdev(r_comp)
        u_rep = s / math.sqrt(n) if n >= 2 else 0.0  # s/√n (تکرارپذیری میانگین)
        u_res = _f(p.get('res_comparison'), 0.5)
        u_res_u = u_res / math.sqrt(12)
        rows = [
            row('u_rep', 'تکرارپذیری تعیین اندازه دانه (مقایسه‌ای)', 'نرمال', s, 'G',
                u_rep, 1.0, note=f's (تک اندازه‌گیری)، n={n}'),
            row('u_htm', 'U گواهی میکروسکوپ/دستگاه', 'نرمال', u_cert, 'G', u_cert / 2, 1.0, note='U/2'),
            row('u_res', 'رزولوشن مقایسه (گام نمودار مقایسه)', 'مستطیلی', u_res, 'G', u_res_u, 1.0, note='a/√12'),
        ]
        u_c = math.sqrt(sum(r['contribution_in_output'] ** 2 for r in rows))
        k = 2.0
        prm = finalize_parameter('اندازه دانه — روش مقایسه‌ای', 'G', 'G', m, rows, k=k, denom=m)
        prm['extras'] = {'میانگین G': round(m, 3), 's': round(s, 4), 'n': n,
                         'U': round(k * u_c, 4)}
        params.append(prm)
    if method in ('intercept', 'both') and len(r_int) >= 2:
        n = len(r_int)
        m = mean(r_int)
        s = stdev(r_int)
        u_rep = s  # اصلاح: عدم قطعیت تک اندازه‌گیری
        u_res = _f(p.get('res_intercept'), 0.001)
        u_res_u = u_res / math.sqrt(12)
        rows = [
            row('u_rep', 'تکرارپذیری شمارش تقاطعی', 'نرمال', s, 'mm⁻¹' if m < 10 else 'G',
                u_rep, 1.0, note=f's (تک اندازه‌گیری)، n={n}'),
            row('u_htm', 'U گواهی میکروسکوپ/دستگاه', 'نرمال', u_cert, 'G', u_cert / 2, 1.0, note='U/2'),
            row('u_res', 'رزولوشن اندازه‌گیری (تقاطعی)', 'مستطیلی', u_res, 'mm', u_res_u, 1.0, note='a/√12'),
        ]
        prm = finalize_parameter('اندازه دانه — روش تقاطعی (Intercept)', 'G', 'G', m, rows, k=2.0, denom=m)
        u_c = prm['u_c']
        prm['extras'] = {'میانگین': round(m, 5), 's': round(s, 5), 'n': n,
                         'U': round(prm['U'], 5)}
        params.append(prm)
    if not params:
        raise ValueError('برای روش انتخاب‌شده حداقل ۲ قرائت لازم است.')
    return {'parameters': params,
            'summary': {'روش': {'comparison': 'مقایسه‌ای', 'intercept': 'تقاطعی', 'both': 'هر دو روش'}[method],
                        'Ucert. دستگاه': u_cert}}


# ---------------------------------------------------------------
# ۷) آنالیز شیمیایی (کوانتومتری OES) — مطابق شیت spectro + رگرسیون U(x)
# ---------------------------------------------------------------

import json as _json
import os as _os

_SPECTRO_FILE = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'spectro_data.json')
try:
    with open(_SPECTRO_FILE, encoding='utf-8') as _fh:
        SPECTRO_TABLES = _json.load(_fh)
except Exception:
    SPECTRO_TABLES = {'low_alloy': {}, 'steel': {}}

ELEMENTS_FA = {'C': 'کربن', 'SI': 'سیلیسیم', 'MN': 'منگنز', 'P': 'فسفر', 'S': 'گوگرد',
               'CR': 'کروم', 'NI': 'نیکل', 'MO': 'مولیبدن', 'CU': 'مس', 'V': 'وانادیم',
               'AL': 'آلومینیم', 'NB': 'نیوبیم', 'TI': 'تیتانیم', 'W': 'تنگستن',
               'CO': 'کبالت', 'SN': 'قلع', 'PB': 'سرب', 'B': 'بور', 'N': 'نیتروژن',
               'ZR': 'زیرکونیم', 'FE': 'آهن'}


def _u_regression(family, elem, x):
    """U براساس جدول رگرسیون قطعه‌ای U(x) — مطابق شیت‌های Spectro-Regration."""
    tbl = SPECTRO_TABLES.get(family, {}).get(elem.upper())
    if not tbl:
        return None, None
    for lo, hi, slope, const in tbl:
        if lo <= x <= hi:
            return abs(slope * x + const), (lo, hi)
    # خارج از بازه: نزدیک‌ترین سگمنت
    seg = min(tbl, key=lambda t: min(abs(x - t[0]), abs(x - t[1])))
    lo, hi, slope, const = seg
    return abs(slope * x + const), (lo, hi)




def _get_crm_assigned(crm_codes, elem):
    """مقدار assigned_value از CRMElementValue برای عنصر در اولین CRM موجود."""
    if not crm_codes:
        return None
    try:
        from uncertainty.crm_models import CRMCertificateVersion
        codes = [c.strip() for c in str(crm_codes).split(',') if c.strip()]
        for code in codes:
            crm = CRMCertificateVersion.objects.filter(reference__name=code).first()
            if not crm:
                crm = CRMCertificateVersion.objects.filter(certificate_no=code).first()
            if not crm:
                continue
            ev = crm.element_values.filter(element__iexact=elem).first()
            if ev and ev.assigned_value is not None:
                return float(ev.assigned_value)
    except Exception:
        pass
    return None


def _nu_from_row(sym, row_dict, n=None):
    """درجه آزادی برای هر مؤلفه — برای Welch–Satterthwaite."""
    if sym in ('u_rep', 'u_reprod') and n and n >= 2:
        return n - 1
    if sym == 'u_CRM':
        return 50  # پیش‌فرض محافظه‌کارانه برای گواهی
    if sym == 'u_res':
        return 1_000_000  # توزیع مستطیلی ≈ ∞
    if sym == 'u_bias':
        return 1_000_000  # توزیع مستطیلی ≈ ∞
    if sym == 'u_env':
        return 50
    return 1_000_000


def _t_factor_975(nu):
    """t دوطرفه 95% — از تابع t_factor موجود."""
    try:
        return t_factor(nu)
    except Exception:
        return 2.0




def _fit_u_regression(matrix='low_alloy', min_points=4):
    """برازش خطی u = a + b·x برای هر عنصر از CRMهای یک دسته.
    برمی‌گرداند: {element: {'a': float, 'b': float, 'r2': float, 'n': int}}
    """
    from uncertainty.crm_models import CRMCertificateVersion
    data = {}
    try:
        for crm in CRMCertificateVersion.objects.filter(matrix=matrix):
            for ev in crm.element_values.all():
                x = ev.assigned_value
                u = ev.uncertainty_value
                if x is None or u is None:
                    continue
                try:
                    xf, uf = float(x), float(u)
                except (TypeError, ValueError):
                    continue
                if xf <= 0 or uf < 0:
                    continue
                elem = str(ev.element).upper()
                data.setdefault(elem, []).append((xf, uf))
    except Exception:
        return {}

    result = {}
    for elem, pairs in data.items():
        if len(pairs) < min_points:
            continue
        n = len(pairs)
        sx = sum(p[0] for p in pairs)
        sy = sum(p[1] for p in pairs)
        sxx = sum(p[0]**2 for p in pairs)
        sxy = sum(p[0]*p[1] for p in pairs)
        denom = n*sxx - sx*sx
        if abs(denom) < 1e-15:
            continue
        b = (n*sxy - sx*sy) / denom
        a = (sy - b*sx) / n
        y_mean = sy / n
        ss_tot = sum((p[1]-y_mean)**2 for p in pairs)
        ss_res = sum((p[1] - (a + b*p[0]))**2 for p in pairs)
        r2 = 1 - ss_res/ss_tot if ss_tot > 1e-15 else 0.0
        result[elem] = {'a': a, 'b': b, 'r2': r2, 'n': n}
    return result


def _nearest_crm_u(crm_codes, elem, x_value):
    """Fallback: نزدیک‌ترین CRM بر اساس assigned_value به x_value."""
    from uncertainty.crm_models import CRMCertificateVersion
    try:
        codes = [c.strip() for c in str(crm_codes or '').split(',') if c.strip()]
        candidates = []
        for code in codes:
            crm = CRMCertificateVersion.objects.filter(reference__name=code).first()
            if not crm:
                continue
            for ev in crm.element_values.filter(element__iexact=elem):
                if ev.assigned_value is not None and ev.uncertainty_value is not None:
                    candidates.append((abs(float(ev.assigned_value) - x_value), float(ev.uncertainty_value)))
        if candidates:
            candidates.sort(key=lambda t: t[0])
            return candidates[0][1]
    except Exception:
        pass
    return None



def calc_spectro(p):
    """آنالیز شیمیایی (کوانتومتری OES) — بودجه مؤلفه‌ای (component-by-component).
    برای هر عنصر: u_rep + u_reprod + u_res + u_CRM + u_env (RSS) = U_elem.
    رگرسیون U(x) به‌عنوان گزارش/نمودار جداگانه ارائه می‌شود (نه مؤلفهٔ بودجه)."""
    family = p.get('family', 'low_alloy')
    res = _f(p.get('resolution'), 0.0)
    crm_codes = (p.get('crm_codes') or '').strip()
    rows_in = p.get('elements', {})
    multi = p.get('element_series', {})
    if not rows_in:
        raise ValueError('هیچ قرائتی برای عناصر وارد نشده است.')
    params = []
    u_res = res / math.sqrt(12)
    for elem, readings in rows_in.items():
        E = elem.upper()
        vals = [_f(v) for v in readings if _f(v) is not None]
        if len(vals) < 2:
            continue
        n = len(vals)
        m = mean(vals)
        s = stdev(vals)
        u_rep = s  # اصلاح: عدم قطعیت تک اندازه‌گیری
        u_reprod = 0.0
        series = multi.get(elem)
        if series and len(series) >= 2:
            # analyze_precision انتظار dict می‌گیرد: {group_id: [readings]}
            groups = {}
            for i, sr in enumerate(series):
                sv = [_f(v) for v in sr if _f(v) is not None]
                if len(sv) >= 2:
                    groups[f"Series_{i+1}"] = sv
            if len(groups) >= 2:
                try:
                    precision_result = analyze_precision(groups)
                    u_reprod = precision_result.get('intermediate_sd_single', 0.0) or 0.0
                except Exception:
                    u_reprod = 0.0
        # === u_CRM: اولویت با رگرسیون، بعد نزدیک‌ترین CRM، بعد فرم ===
        ucrm_map = p.get('ucrm') if isinstance(p.get('ucrm'), dict) else {}
        u_crm = _f(ucrm_map.get(E))
        crm_src = 'U گواهی/2 (ورودی کاربر)' if u_crm is not None else ''
        if u_crm is None:
            u_crm = _f(p.get('u_crm_' + E))
            if u_crm is not None:
                crm_src = 'U گواهی/2 (ورودی کاربر)'

        if u_crm is None:
            # ۱. رگرسیون U(x) از CRMهای همان دسته
            reg = _fit_u_regression(matrix=family)
            reg_item = reg.get(E)
            if (reg_item and reg_item.get('r2', 0) >= 0.5 and reg_item.get('n', 0) >= 4):
                a, b = reg_item['a'], reg_item['b']
                u_crm_calc = a + b * m
                if u_crm_calc > 0:
                    u_crm = u_crm_calc
                    crm_src = f"رگرسیون U(x) — {reg_item['n']} CRM، R²={reg_item['r2']:.3f}"
            # ۲. اگر رگرسیون نبود یا R² ضعیف → نزدیک‌ترین CRM
            if u_crm is None:
                u_near = _nearest_crm_u(p.get('crm_codes') or p.get('crm_code'), E, m)
                if u_near is not None:
                    u_crm = u_near
                    crm_src = 'نزدیک‌ترین CRM (رگرسیون ضعیف/کم‌داده)'

        if u_crm is None:
            u_crm = 0.0
            crm_src = '⚠ ثبت نشده — مقدار U گواهی CRM این عنصر را از فرم وارد کنید'
        # u_reg حذف شد — بودجه ۴ مؤلفه: u_rep, u_reprod, u_res, u_CRM
        rows = [
            row('u_rep', f'تکرارپذیری {ELEMENTS_FA.get(E, E)}', 'نرمال', s, '%',
                u_rep, 1.0, note=f's (تک اندازه‌گیری)، n={n}'),
        ]
        if u_reprod > 0:
            rows.append(row('u_reprod', f'بازتولیدپذیری {ELEMENTS_FA.get(E, E)} (سری‌ها)', 'نرمال',
                            u_reprod, '%', u_reprod, 1.0))
        rows.append(row('u_res', 'رزولوشن دستگاه', 'مستطیلی', res, '%', u_res, 1.0, note='a/√12'))
        rows.append(row('u_CRM', f'عدم‌قطعیت گواهی CRM ({E})', 'نرمال', u_crm * 2, '%',
                        u_crm, 1.0, note=crm_src or '⚠ ثبت نشده'))


        # --- ν_eff و U = t(0.975,ν_eff)·u_c ---
        uc_sq_sum = sum((r['u'] ** 2) for r in rows)
        if uc_sq_sum > 0:
            nu_denom = 0.0
            for r in rows:
                u_i = r['u']
                if u_i and u_i > 0:
                    nu_i = _nu_from_row(r['symbol'], r, n=n)
                    nu_denom += (u_i ** 4) / nu_i
            nu_eff = (uc_sq_sum ** 2) / nu_denom if nu_denom > 0 else 1_000_000
            t_val = _t_factor_975(nu_eff)
        else:
            nu_eff = 1_000_000
            t_val = 2.0
        prm = finalize_parameter(f'{ELEMENTS_FA.get(E, E)} ({E})', E, '%', m, rows, k=t_val, denom=m)
        prm['nu_eff'] = nu_eff
        # range حذف شد
        # u_reg و regression_range حذف شدند
        prm['method'] = 'component-by-component'
        params.append(prm)
    if not params:
        raise ValueError('برای هیچ عنصری حداقل ۲ قرائت معتبر وارد نشده است.')
    u_combined = math.sqrt(sum((prm['u_c'] ** 2) for prm in params)) if params else 0.0
    return {'parameters': params,
            'summary': {'خانواده': 'فولاد کم‌آلیاژ' if family == 'low_alloy' else 'فولاد',
                        'کدهای CRM': crm_codes or '—',
                        'رزولوشن دستگاه': res,
                        'عناصر محاسبه‌شده': ', '.join(x['symbol'] for x in params),
                        'U ترکیبی کل (RSS)': round(u_combined * 2, 6)}}


def _readings_field(prefix, fields, count, label):
    return {'kind': 'grid', 'name': prefix, 'label': label, 'count': count,
            'count_range': list(range(count)),
            'fields': fields}


# ---------------------------------------------------------------
# رجیستری انواع محاسبه + شمای فرم ورودی
# ---------------------------------------------------------------

def _readings_field(prefix, fields, count, label):
    return {'kind': 'grid', 'name': prefix, 'label': label, 'count': count,
            'count_range': list(range(count)),
            'fields': fields}


def calc_spectro_crm(p):
    """مسیر A — راستی‌آزمایی روی CRM (عین شیت‌های Spectro_Input / spectro):
    u_rep + u_reprod (اگر سری‌های متعدد) + u_res + u_CRM (الزامی) → U، U%."""
    res = _f(p.get('resolution'), 0.0)
    rows_in = p.get('elements', {})
    multi = p.get('element_series', {})
    if not rows_in:
        raise ValueError('هیچ قرائتی برای عناصر وارد نشده است.')
    params = []
    u_res = res / math.sqrt(12)
    for elem, readings in rows_in.items():
        E = elem.upper()
        vals = [_f(v) for v in readings if _f(v) is not None]
        if len(vals) < 2:
            continue
        n = len(vals)
        m = mean(vals)
        s = stdev(vals)
        u_rep = s  # اصلاح: عدم قطعیت تک اندازه‌گیری
        u_reprod = 0.0
        series = multi.get(elem)
        if series and len(series) >= 2:
            groups = []
            for i, sr in enumerate(series):
                sv = [_f(v) for v in sr if _f(v) is not None]
                if len(sv) >= 2:
                    groups.append((f"Series_{i+1}", sv))
            if len(groups) >= 2:
                try:
                    precision_result = analyze_precision(groups)
                    u_reprod = precision_result.get('intermediate_sd_single', 0.0) or 0.0
                except Exception:
                    u_reprod = 0.0
        ucrm_map = p.get('ucrm') if isinstance(p.get('ucrm'), dict) else {}
        u_crm = _f(ucrm_map.get(E))
        if u_crm is None:
            u_crm = _f(p.get('u_crm_' + E))
        if u_crm is None:
            crm_ref = SPECTRO_TABLES.get('crm_reference') or {}
            u_crm = _f((crm_ref.get('crm_u') or {}).get(E))
        if u_crm is None:
            u_crm = 0.0
        rows = [
            row('u_rep', f'تکرارپذیری {ELEMENTS_FA.get(E, E)}', 'نرمال', s, '%',
                u_rep, 1.0, note=f's (تک اندازه‌گیری)، n={n}'),
        ]
        if u_reprod > 0:
            rows.append(row('u_reprod', f'بازتولیدپذیری {ELEMENTS_FA.get(E, E)} (سری‌ها)', 'نرمال',
                            u_reprod, '%', u_reprod, 1.0))
        rows.append(row('u_res', 'رزولوشن دستگاه', 'مستطیلی', res, '%', u_res, 1.0, note='a/√12'))
        rows.append(row('u_CRM', f'عدم‌قطعیت گواهی CRM ({E})', 'نرمال', u_crm * 2, '%',
                        u_crm, 1.0, note='U/2 — الزامی ISO 17025 §7.6'))
        u_env = _env_u(p, m)
        if u_env:
            rows.append(row('u_env', 'شرایط محیطی/دما (خودکار از دما + دستی)', 'نرمال',
                            u_env, '%', u_env, 1.0, note='COP06 A4'))
        prm = finalize_parameter(f'{ELEMENTS_FA.get(E, E)} ({E}) — CRM', E, '%', m, rows, k=2.0, denom=m)
        prm['method'] = 'CRM-verification'
        params.append(prm)
    if not params:
        raise ValueError('برای هیچ عنصری حداقل ۲ قرائت معتبر وارد نشده است.')
    return {'parameters': params,
            'summary': {'روش': 'CRM-verification (مسیر A)',
                        'خانواده': 'فولاد کم‌آلیاژ' if p.get('family') == 'low_alloy' else 'فولاد',
                        'کدهای CRM': (p.get('crm_codes') or '—'),
                        'رزولوشن دستگاه': res,
                        'عناصر محاسبه‌شده': ', '.join(x['symbol'] for x in params)}}




def _linear_regression(points):
    """Fit U = a*x + b to list of (x, U) points. Returns (a, b, r_squared)."""
    if len(points) < 2:
        return None, None, None
    n = len(points)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    ss_xx = sum((x - x_mean) ** 2 for x in xs)
    ss_yy = sum((y - y_mean) ** 2 for y in ys)
    ss_xy = sum((x - x_mean) * (y - y_mean) for x, y in points)
    if ss_xx == 0:
        return None, None, None
    a = ss_xy / ss_xx
    b = y_mean - a * x_mean
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy > 0 else 0.0
    return a, b, r_squared

def calc_spectro_regression(p):
    """آنالیز شیمیایی — رگرسیون چند-CRM.
    برای هر CRM: u_rep + u_reprod + u_res + u_CRM + u_env → U_elem (per element).
    برای هر عنصر: برازش رگرسیون خطی U = a*x + b روی نقاط (غلظت_CRM, U_elem).
    خروجی: per-CRM per-element U, per-element regression, combined U per CRM."""
    family = p.get('family', 'low_alloy')
    res = _f(p.get('resolution'), 0.0)
    material = (p.get('material') or 'steel').strip().lower()
    test_temp = _f(p.get('test_temp'), 23.0)
    crms = p.get('crms', [])
    if not crms:
        raise ValueError('حداقل یک CRM باید وارد شود.')
    if len(crms) < 2:
        raise ValueError('برای رگرسیون حداقل ۲ CRM لازم است.')

    u_res = res / math.sqrt(12)
    crm_results = []
    element_points = {}
    element_names = set()

    for crm_idx, crm in enumerate(crms):
        crm_code = (crm.get('code') or f'CRM-{crm_idx+1}').strip()
        concentrations = crm.get('concentrations', {})
        readings_map = crm.get('readings', {})
        series_map = crm.get('series', {})
        ucrm_map = crm.get('ucrm', {})
        if not isinstance(ucrm_map, dict):
            ucrm_map = {}

        crm_elem_results = []
        crm_u_combined_sq = 0.0

        for elem, conc in concentrations.items():
            E = elem.upper()
            element_names.add(E)
            conc_val = _f(conc)
            if conc_val is None:
                continue

            readings = readings_map.get(elem, [])
            vals = [_f(v) for v in readings if _f(v) is not None]
            if len(vals) < 2:
                continue
            n = len(vals)
            m = mean(vals)
            s = stdev(vals)
            u_rep = s  # اصلاح: عدم قطعیت تک اندازه‌گیری

            u_reprod = 0.0
            series = series_map.get(elem)
            if series and len(series) >= 2:
                groups = []
            for i, sr in enumerate(series):
                sv = [_f(v) for v in sr if _f(v) is not None]
                if len(sv) >= 2:
                    groups.append((f"Series_{i+1}", sv))
            if len(groups) >= 2:
                try:
                    precision_result = analyze_precision(groups)
                    u_reprod = precision_result.get('intermediate_sd_single', 0.0) or 0.0
                except Exception:
                    u_reprod = 0.0

            u_crm = _f(ucrm_map.get(E))
            if u_crm is None:
                crm_ref = SPECTRO_TABLES.get('crm_reference') or {}
                u_crm = _f((crm_ref.get('crm_u') or {}).get(E))
            if u_crm is None:
                u_crm = 0.0

            u_env = _env_u({'test_temp': test_temp, 'material': material, 'u_env': crm.get('u_env')}, conc_val)
            if u_env is None:
                u_env = 0.0

            rows = [
                row('u_rep', f'تکرارپذیری {ELEMENTS_FA.get(E, E)}', 'نرمال', s, '%',
                    u_rep, 1.0, note=f's (تک اندازه‌گیری)، n={n}'),
            ]
            if u_reprod > 0:
                rows.append(row('u_reprod', f'بازتولیدپذیری {ELEMENTS_FA.get(E, E)}', 'نرمال',
                                u_reprod, '%', u_reprod, 1.0))
            rows.append(row('u_res', 'رزولوشن دستگاه', 'مستطیلی', res, '%', u_res, 1.0, note='a/√12'))
            rows.append(row('u_CRM', f'عدم‌قطعیت گواهی CRM ({E})', 'نرمال', u_crm * 2, '%',
                            u_crm, 1.0, note='U/2'))
            if u_env > 0:
                rows.append(row('u_env', 'شرایط محیطی/دما', 'نرمال', u_env, '%', u_env, 1.0, note='خودکار از دما'))

            u_combined = math.sqrt(sum(r['contribution_in_output'] ** 2 for r in rows))
            U_expanded = 2.0 * u_combined
            U_percent = (U_expanded / conc_val * 100) if conc_val else None

            prm = finalize_parameter(f'{ELEMENTS_FA.get(E, E)} ({E})', E, '%', m, rows, k=2.0, denom=conc_val)
            prm['crm_code'] = crm_code
            prm['concentration'] = conc_val
            prm['u_combined'] = u_combined
            prm['U_expanded'] = U_expanded
            prm['U_percent'] = U_percent
            prm['method'] = 'component-by-component'
            crm_elem_results.append(prm)
            crm_u_combined_sq += u_combined ** 2

            element_points.setdefault(E, []).append((conc_val, U_expanded))

        crm_combined_u = math.sqrt(crm_u_combined_sq)
        crm_results.append({
            'code': crm_code,
            'elements': crm_elem_results,
            'combined_u': crm_combined_u,
            'combined_U': 2.0 * crm_combined_u,
        })

    regression_results = {}
    regression_chart_data = {}
    for E in sorted(element_names):
        pts = element_points.get(E, [])
        if len(pts) < 2:
            continue
        a, b, r2 = _linear_regression(pts)
        regression_results[E] = {
            'element': ELEMENTS_FA.get(E, E),
            'symbol': E,
            'slope': round(a, 8) if a is not None else None,
            'intercept': round(b, 8) if b is not None else None,
            'r_squared': round(r2, 6) if r2 is not None else None,
            'equation': f'U = {a:.6f}·x + {b:.6f}' if a is not None else '—',
            'n_points': len(pts),
            'points': [{'x': round(p[0], 6), 'y': round(p[1], 8)} for p in pts],
        }
        if a is not None:
            xs = [p[0] for p in pts]
            x_min, x_max = min(xs), max(xs)
            line_pts = [
                {'x': round(x_min, 6), 'y': round(a * x_min + b, 8)},
                {'x': round(x_max, 6), 'y': round(a * x_max + b, 8)},
            ]
            regression_chart_data[E] = {
                'scatter': [{'x': round(p[0], 6), 'y': round(p[1], 8)} for p in pts],
                'line': line_pts,
                'equation': f'U = {a:.6f}·x + {b:.6f}',
                'r2': round(r2, 6) if r2 is not None else None,
            }

    combined_points = []
    for cr in crm_results:
        concs = [e['concentration'] for e in cr['elements']]
        mean_conc = sum(concs) / len(concs) if concs else 0
        combined_points.append((mean_conc, cr['combined_U']))
    a_c, b_c, r2_c = _linear_regression(combined_points)

    summary = {
        'روش': 'رگرسیون چند-CRM (component-by-component + linear fit)',
        'تعداد CRM': len(crms),
        'عناصر': ', '.join(sorted(element_names)),
        'رزولوشن دستگاه': res,
        'متریال': material,
        'دما (°C)': test_temp,
    }

    return {
        'parameters': [elem for cr in crm_results for elem in cr['elements']],
        'crm_results': crm_results,
        'regression': regression_results,
        'regression_chart_data': regression_chart_data,
        'combined_regression': {
            'slope': round(a_c, 8) if a_c is not None else None,
            'intercept': round(b_c, 8) if b_c is not None else None,
            'r_squared': round(r2_c, 6) if r2_c is not None else None,
            'equation': f'U_total = {a_c:.6f}·x̄ + {b_c:.6f}' if a_c is not None else '—',
            'points': [{'x': round(p[0], 6), 'y': round(p[1], 8)} for p in combined_points],
        },
        'summary': summary,
    }

RANGE_CHOICES = [('', '— تشخیص خودکار از روی کد دستگاه و Force Cal —'),
                 ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')]

CALC_TYPES = {
    'tensile_round': {
        'label': 'کشش — نمونه گرد',
        'icon': '🔄',
        'func': lambda p: calc_tensile({**p, 'shape': 'round'}),
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'TT-73-01'},
            {'name': 'force_cal', 'label': 'Force Cal بازه کالیبراسیون (N)', 'default': 300000},
            {'name': 'range_label', 'label': 'بازه (Low/Middle/High)', 'type': 'select',
             'choices': RANGE_CHOICES, 'default': ''},
            {'name': 'machine_u', 'label': 'U کالیبراسیون دستگاه کشش (N)', 'default': 510},
            {'name': 'machine_res', 'label': 'رزولوشن دستگاه (N)', 'default': 1},
            {'name': 'cal_u', 'label': 'U کالیبراسیون کولیس (mm)', 'default': 0.01},
            {'name': 'cal_res', 'label': 'رزولوشن کولیس (mm)', 'default': 0.01},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری، MPa)'},
            {'name': 'include_rep', 'label': 'تکرارپذیری نیرو (Type A — سری آزمون)', 'type': 'select',
             'choices': [('1', 'بله (پیش‌فرض — الزام سری آزمون)'), ('0', 'خیر (فقط بودجه Type B تک‌نمونه COP 07)')]},
        ],
        'grid': [_readings_field('readings',
                                 [('d0', 'قطر اولیه D0 (mm)'), ('d1', 'قطر نهایی D1 (mm)'),
                                  ('rm', 'نیروی Rm (N)'), ('rp02', 'نیروی Rp0.2 (N)'), ('reh', 'نیروی Reh (N)'),
                                  ('l0', 'L0 (mm)'), ('l1', 'L1 (mm)')], 10, 'قرائت‌های نمونه گرد')],
    },
    'tensile_flat': {
        'label': 'کشش — نمونه تخت',
        'icon': '➖',
        'func': lambda p: calc_tensile({**p, 'shape': 'flat'}),
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'TT-73-01'},
            {'name': 'force_cal', 'label': 'Force Cal بازه کالیبراسیون (N)', 'default': 300000},
            {'name': 'range_label', 'label': 'بازه (Low/Middle/High)', 'type': 'select',
             'choices': RANGE_CHOICES, 'default': ''},
            {'name': 'machine_u', 'label': 'U کالیبراسیون دستگاه کشش (N)', 'default': 510},
            {'name': 'machine_res', 'label': 'رزولوشن دستگاه (N)', 'default': 1},
            {'name': 'cal_u', 'label': 'U کالیبراسیون کولیس (mm)', 'default': 0.01},
            {'name': 'cal_res', 'label': 'رزولوشن کولیس (mm)', 'default': 0.01},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری، MPa)'},
            {'name': 'include_rep', 'label': 'افزودن تکرارپذیری بین‌نمونه‌ها (خارج از COP 07 — اطلاعاتی)', 'type': 'select',
             'choices': [('', 'خیر (پیش‌فرض COP 07)'), ('1', 'بله، اضافه کن')]},
        ],
        'grid': [_readings_field('readings',
                                 [('thk', 'ضخامت (mm)'), ('wide', 'عرض (mm)'),
                                  ('rm', 'نیروی Rm (N)'), ('rp02', 'نیروی Rp0.2 (N)'), ('reh', 'نیروی Reh (N)'),
                                  ('l0', 'L0 (mm)'), ('l1', 'L1 (mm)')], 10, 'قرائت‌های نمونه تخت')],
    },
    'rockwell': {
        'label': 'سختی راکول',
        'icon': '💎',
        'func': calc_rockwell,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه سختی', 'default': 'HT-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM (بلاک مرجع)'},
            {'name': 'scale', 'label': 'مقیاس', 'type': 'select',
             'choices': [('HRC', 'HRC'), ('HRB', 'HRB'), ('HRA', 'HRA')], 'default': 'HRC'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM'},
            {'name': 'u_htm', 'label': 'U راستی‌آزمایی غیرمستقیم HTM', 'default': 1.5},
            {'name': 'resolution', 'label': 'رزولوشن دستگاه', 'default': 0.1},
            {'name': 'std_method', 'label': 'روش گزارش', 'type': 'select',
             'choices': [('M1', 'ISO — روش M1 (بدون بایاس)'), ('M2', 'ISO — روش M2 (k·u+|b|)'), ('ASTM', 'ASTM (k·u + حد مجاز)')],
             'default': 'M2'},
            {'name': 'drift', 'label': 'Drift دستگاه از گواهی (اختیاری، HV)'},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری)'},
        ],
        'grid': [_readings_field('readings1', [('v', 'قرائت سری ۱')], 5, 'قرائت‌های سری ۱'),
                 _readings_field('readings2', [('v', 'قرائت سری ۲ / اپراتور دوم (اختیاری)')], 5, 'قرائت‌های سری ۲ / اپراتور دوم')],
    },
    'vickers': {
        'label': 'سختی ویکرز',
        'icon': '🔺',
        'func': calc_vickers,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه سختی', 'default': 'HT-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM (HV)'},
            {'name': 'u_crm', 'label': 'U گواهی CRM (HV)', 'default': 10},
            {'name': 'resolution', 'label': 'رزولوشن اندازه‌گیری قطری (mm)', 'default': 0.0005},
            {'name': 'drift', 'label': 'Drift دستگاه از گواهی (اختیاری، HV)'},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری)'},
        ],
        'grid': [_readings_field('readings1', [('v', 'قرائت HV نمونه')], 5, 'قرائت‌های نمونه'),
                 _readings_field('readings2', [('v', 'قرائت سری ۲ (اختیاری)')], 5, 'قرائت‌های سری ۲'),
                 _readings_field('readings_crm', [('v', 'قرائت HV روی CRM')], 5, 'قرائت‌های روی CRM'),
                 _readings_field('d_readings', [('v', 'قطر فرورفتگی d (mm)')], 5, 'قطرهای فرورفتگی')],
    },
    'mhv': {
        'label': 'میکروسختی ویکرز',
        'icon': '🔬',
        'func': lambda p: calc_vickers({**p}, micro=True),
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'MH-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM (HV)'},
            {'name': 'u_crm', 'label': 'U گواهی CRM (HV)', 'default': 5},
            {'name': 'resolution', 'label': 'رزولوشن اندازه‌گیری قطری (mm)', 'default': 0.0005},
            {'name': 'drift', 'label': 'Drift دستگاه از گواهی (اختیاری، HV)'},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری)'},
        ],
        'grid': [_readings_field('readings1', [('v', 'قرائت HV نمونه')], 5, 'قرائت‌های نمونه'),
                 _readings_field('readings2', [('v', 'قرائت سری ۲ (اختیاری)')], 5, 'قرائت‌های سری ۲'),
                 _readings_field('readings_crm', [('v', 'قرائت HV روی CRM')], 5, 'قرائت‌های روی CRM'),
                 _readings_field('d_readings', [('v', 'قطر فرورفتگی d (mm)')], 5, 'قطرهای فرورفتگی')],
    },
    'brinell': {
        'label': 'سختی برینل',
        'icon': '⚪',
        'func': calc_brinell,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه سختی', 'default': 'HT-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM (HBW)'},
            {'name': 'u_crm', 'label': 'U گواهی CRM (HBW)', 'default': 10},
            {'name': 'resolution', 'label': 'رزولوشن اندازه‌گیری قطری (mm)', 'default': 0.01},
            {'name': 'ball_dia', 'label': 'قطر گوی (mm)', 'default': 2.5},
        ],
        'grid': [_readings_field('readings1', [('v', 'قرائت HBW')], 5, 'قرائت‌های سختی'),
                 _readings_field('readings2', [('v', 'قرائت سری ۲ (اختیاری)')], 5, 'قرائت‌های سری ۲'),
                 _readings_field('d_readings', [('v', 'قطر فرورفتگی d (mm)')], 5, 'قطرهای فرورفتگی')],
    },
    'impact': {
        'label': 'ضربه (شارپی)',
        'icon': '💥',
        'func': calc_impact,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'IT-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM (J)'},
            {'name': 'material_ref', 'label': 'مقدار مرجع نمونه داخلی WRM (اختیاری، J)'},
            {'name': 'u_cert', 'label': 'U گواهی CRM (J)', 'default': 2},
            {'name': 'resolution', 'label': 'رزولوشن دستگاه (J)', 'default': 0.1},
            {'name': 'machine_err_pct', 'label': 'خطای دستگاه eA1 از گواهی (٪، اختیاری)'},
            {'name': 'bias_mode', 'label': 'روش بایاس', 'type': 'select',
             'choices': [('auto', 'خودکار: WRM اگر وارد شده، وگرنه eA1% طبق COP'),
                         ('none', 'بدون بایاس (فقط Type A)')],
             'default': 'auto'},
            {'name': 'u_env', 'label': 'عدم‌قطعیت دما/شرایط محیطی cT·uT (اختیاری، J)'},
        ],
        'grid': [_readings_field('readings_crm', [('v', 'قرائت روی CRM (J)')], 5, 'قرائت‌های CRM'),
                 _readings_field('readings_material', [('v', 'قرائت نمونه (J)')], 10, 'قرائت‌های نمونه')],
    },
    'grain': {
        'label': 'اندازه دانه',
        'icon': '🧿',
        'func': calc_grain,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه/میکروسکوپ', 'default': 'OPM-73-02'},
            {'name': 'method', 'label': 'روش', 'type': 'select',
             'choices': [('comparison', 'مقایسه‌ای (Comparison)'), ('intercept', 'تقاطعی (Intercept)'), ('both', 'هر دو روش')],
             'default': 'comparison'},
            {'name': 'u_cert_machine', 'label': 'Ucert. دستگاه (از گواهی)', 'default': 0.0015},
            {'name': 'res_comparison', 'label': 'رزولوشن مقایسه (گام)', 'default': 0.5},
            {'name': 'res_intercept', 'label': 'رزولوشن تقاطعی (mm)', 'default': 0.001},
        ],
        'grid': [_readings_field('readings_comparison', [('v', 'قرائت مقایسه‌ای (G)')], 10, 'قرائت‌های روش مقایسه‌ای'),
                 _readings_field('readings_intercept', [('v', 'قرائت تقاطعی')], 10, 'قرائت‌های روش تقاطعی')],
    },
    'spectro': {
        'label': 'آنالیز شیمیایی (کوانتومتری)',
        'icon': '⚗️',
        'func': calc_spectro,
        'special': 'spectro',
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'ARL-73-01'},
            {'name': 'family', 'label': 'خانواده ماده', 'type': 'select',
             'choices': [('low_alloy', 'فولاد کم‌آلیاژ (Low Alloy)'), ('steel', 'فولاد (Steel)')], 'default': 'low_alloy'},
            {'name': 'crm_codes', 'label': 'کد(های) CRM/RM استفاده‌شده'},
            {'name': 'resolution', 'label': 'رزولوشن دستگاه', 'default': 0.00001},
        ],
        'grid': [],
    },
    'spectro_regression': {
        'label': 'آنالیز شیمیایی — رگرسیون چند-CRM',
        'icon': '📈',
        'func': calc_spectro_regression,
        'special': 'spectro_regression',
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'ARL-73-01'},
            {'name': 'family', 'label': 'خانواده ماده', 'type': 'select',
             'choices': [('low_alloy', 'فولاد کم‌آلیاژ (Low Alloy)'), ('steel', 'فولاد (Steel)')], 'default': 'low_alloy'},
            {'name': 'resolution', 'label': 'رزولوشن دستگاه', 'default': 0.00001},
            {'name': 'test_temp', 'label': 'دما (°C)', 'default': 23},
            {'name': 'material', 'label': 'متریال', 'type': 'select',
             'choices': [('steel', 'فولاد'), ('stainless', 'فولاد زنگ‌نزن'), ('aluminum', 'آلومینیم'),
                         ('copper', 'مس'), ('cast_iron', 'چدن'), ('titanium', 'تیتانیم'),
                         ('nickel', 'نیکل')], 'default': 'steel'},
            {'name': 'crm_count', 'label': 'تعداد CRM', 'default': 2},
        ],
        'grid': [],
    },
}


import math

RANGE_CHOICES = [('', '— تشخیص خودکار از روی کد دستگاه و Force Cal —'),
                 ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')]

CALC_TYPES = {
    'tensile_round': {
        'label': 'کشش — نمونه گرد',
        'icon': '🔄',
        'func': lambda p: calc_tensile({**p, 'shape': 'round'}),
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'TT-73-01'},
            {'name': 'force_cal', 'label': 'Force Cal بازه کالیبراسیون (N)', 'default': 300000},
            {'name': 'range_label', 'label': 'بازه (Low/Middle/High)', 'type': 'select',
             'choices': RANGE_CHOICES, 'default': ''},
            {'name': 'machine_u', 'label': 'U کالیبراسیون دستگاه کشش (N)', 'default': 510},
            {'name': 'machine_res', 'label': 'رزولوشن دستگاه (N)', 'default': 1},
            {'name': 'cal_u', 'label': 'U کالیبراسیون کولیس (mm)', 'default': 0.01},
            {'name': 'cal_res', 'label': 'رزولوشن کولیس (mm)', 'default': 0.01},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری، MPa)'},
            {'name': 'include_rep', 'label': 'تکرارپذیری نیرو (Type A — سری آزمون)', 'type': 'select',
             'choices': [('1', 'بله (پیش‌فرض — الزام سری آزمون)'), ('0', 'خیر (فقط بودجه Type B تک‌نمونه COP 07)')]},
        ],
        'grid': [_readings_field('readings',
                                 [('d0', 'قطر اولیه D0 (mm)'), ('d1', 'قطر نهایی D1 (mm)'),
                                  ('rm', 'نیروی Rm (N)'), ('rp02', 'نیروی Rp0.2 (N)'), ('reh', 'نیروی Reh (N)'),
                                  ('l0', 'L0 (mm)'), ('l1', 'L1 (mm)')], 10, 'قرائت‌های نمونه گرد')],
    },
    'tensile_flat': {
        'label': 'کشش — نمونه تخت',
        'icon': '➖',
        'func': lambda p: calc_tensile({**p, 'shape': 'flat'}),
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'TT-73-01'},
            {'name': 'force_cal', 'label': 'Force Cal بازه کالیبراسیون (N)', 'default': 300000},
            {'name': 'range_label', 'label': 'بازه (Low/Middle/High)', 'type': 'select',
             'choices': RANGE_CHOICES, 'default': ''},
            {'name': 'machine_u', 'label': 'U کالیبراسیون دستگاه کشش (N)', 'default': 510},
            {'name': 'machine_res', 'label': 'رزولوشن دستگاه (N)', 'default': 1},
            {'name': 'cal_u', 'label': 'U کالیبراسیون کولیس (mm)', 'default': 0.01},
            {'name': 'cal_res', 'label': 'رزولوشن کولیس (mm)', 'default': 0.01},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری، MPa)'},
            {'name': 'include_rep', 'label': 'افزودن تکرارپذیری بین‌نمونه‌ها (خارج از COP 07 — اطلاعاتی)', 'type': 'select',
             'choices': [('', 'خیر (پیش‌فرض COP 07)'), ('1', 'بله، اضافه کن')]},
        ],
        'grid': [_readings_field('readings',
                                 [('thk', 'ضخامت (mm)'), ('wide', 'عرض (mm)'),
                                  ('rm', 'نیروی Rm (N)'), ('rp02', 'نیروی Rp0.2 (N)'), ('reh', 'نیروی Reh (N)'),
                                  ('l0', 'L0 (mm)'), ('l1', 'L1 (mm)')], 10, 'قرائت‌های نمونه تخت')],
    },
    'rockwell': {
        'label': 'سختی راکول',
        'icon': '💎',
        'func': calc_rockwell,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه سختی', 'default': 'HT-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM (بلاک مرجع)'},
            {'name': 'scale', 'label': 'مقیاس', 'type': 'select',
             'choices': [('HRC', 'HRC'), ('HRB', 'HRB'), ('HRA', 'HRA')], 'default': 'HRC'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM'},
            {'name': 'u_htm', 'label': 'U راستی‌آزمایی غیرمستقیم HTM', 'default': 1.5},
            {'name': 'resolution', 'label': 'رزولوشن دستگاه', 'default': 0.1},
            {'name': 'std_method', 'label': 'روش گزارش', 'type': 'select',
             'choices': [('M1', 'ISO — روش M1 (بدون بایاس)'), ('M2', 'ISO — روش M2 (k·u+|b|)'), ('ASTM', 'ASTM (k·u + حد مجاز)')],
             'default': 'M2'},
            {'name': 'drift', 'label': 'Drift دستگاه از گواهی (اختیاری، HV)'},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری)'},
        ],
        'grid': [_readings_field('readings1', [('v', 'قرائت سری ۱')], 5, 'قرائت‌های سری ۱'),
                 _readings_field('readings2', [('v', 'قرائت سری ۲ / اپراتور دوم (اختیاری)')], 5, 'قرائت‌های سری ۲ / اپراتور دوم')],
    },
    'vickers': {
        'label': 'سختی ویکرز',
        'icon': '🔺',
        'func': calc_vickers,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه سختی', 'default': 'HT-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM (HV)'},
            {'name': 'u_crm', 'label': 'U گواهی CRM (HV)', 'default': 10},
            {'name': 'resolution', 'label': 'رزولوشن اندازه‌گیری قطری (mm)', 'default': 0.0005},
            {'name': 'drift', 'label': 'Drift دستگاه از گواهی (اختیاری، HV)'},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری)'},
        ],
        'grid': [_readings_field('readings1', [('v', 'قرائت HV نمونه')], 5, 'قرائت‌های نمونه'),
                 _readings_field('readings2', [('v', 'قرائت سری ۲ (اختیاری)')], 5, 'قرائت‌های سری ۲'),
                 _readings_field('readings_crm', [('v', 'قرائت HV روی CRM')], 5, 'قرائت‌های روی CRM'),
                 _readings_field('d_readings', [('v', 'قطر فرورفتگی d (mm)')], 5, 'قطرهای فرورفتگی')],
    },
    'mhv': {
        'label': 'میکروسختی ویکرز',
        'icon': '🔬',
        'func': lambda p: calc_vickers({**p}, micro=True),
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'MH-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM (HV)'},
            {'name': 'u_crm', 'label': 'U گواهی CRM (HV)', 'default': 5},
            {'name': 'resolution', 'label': 'رزولوشن اندازه‌گیری قطری (mm)', 'default': 0.0005},
            {'name': 'drift', 'label': 'Drift دستگاه از گواهی (اختیاری، HV)'},
            {'name': 'u_env', 'label': 'عدم‌قطعیت شرایط محیطی/دما (اختیاری)'},
        ],
        'grid': [_readings_field('readings1', [('v', 'قرائت HV نمونه')], 5, 'قرائت‌های نمونه'),
                 _readings_field('readings2', [('v', 'قرائت سری ۲ (اختیاری)')], 5, 'قرائت‌های سری ۲'),
                 _readings_field('readings_crm', [('v', 'قرائت HV روی CRM')], 5, 'قرائت‌های روی CRM'),
                 _readings_field('d_readings', [('v', 'قطر فرورفتگی d (mm)')], 5, 'قطرهای فرورفتگی')],
    },
    'brinell': {
        'label': 'سختی برینل',
        'icon': '⚪',
        'func': calc_brinell,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه سختی', 'default': 'HT-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM (HBW)'},
            {'name': 'u_crm', 'label': 'U گواهی CRM (HBW)', 'default': 10},
            {'name': 'resolution', 'label': 'رزولوشن اندازه‌گیری قطری (mm)', 'default': 0.01},
            {'name': 'ball_dia', 'label': 'قطر گوی (mm)', 'default': 2.5},
        ],
        'grid': [_readings_field('readings1', [('v', 'قرائت HBW')], 5, 'قرائت‌های سختی'),
                 _readings_field('readings2', [('v', 'قرائت سری ۲ (اختیاری)')], 5, 'قرائت‌های سری ۲'),
                 _readings_field('d_readings', [('v', 'قطر فرورفتگی d (mm)')], 5, 'قطرهای فرورفتگی')],
    },
    'impact': {
        'label': 'ضربه (شارپی)',
        'icon': '💥',
        'func': calc_impact,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'IT-73-01'},
            {'name': 'crm_code', 'label': 'کد CRM'},
            {'name': 'range_label', 'label': 'بازه', 'type': 'select',
             'choices': [('', '—'), ('low', 'Low Range'), ('middle', 'Middle Range'), ('high', 'High Range')], 'default': ''},
            {'name': 'crm_value', 'label': 'مقدار CRM (J)'},
            {'name': 'material_ref', 'label': 'مقدار مرجع نمونه داخلی WRM (اختیاری، J)'},
            {'name': 'u_cert', 'label': 'U گواهی CRM (J)', 'default': 2},
            {'name': 'resolution', 'label': 'رزولوشن دستگاه (J)', 'default': 0.1},
            {'name': 'machine_err_pct', 'label': 'خطای دستگاه eA1 از گواهی (٪، اختیاری)'},
            {'name': 'bias_mode', 'label': 'روش بایاس', 'type': 'select',
             'choices': [('auto', 'خودکار: WRM اگر وارد شده، وگرنه eA1% طبق COP'),
                         ('none', 'بدون بایاس (فقط Type A)')],
             'default': 'auto'},
            {'name': 'u_env', 'label': 'عدم‌قطعیت دما/شرایط محیطی cT·uT (اختیاری، J)'},
        ],
        'grid': [_readings_field('readings_crm', [('v', 'قرائت روی CRM (J)')], 5, 'قرائت‌های CRM'),
                 _readings_field('readings_material', [('v', 'قرائت نمونه (J)')], 10, 'قرائت‌های نمونه')],
    },
    'grain': {
        'label': 'اندازه دانه',
        'icon': '🧿',
        'func': calc_grain,
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه/میکروسکوپ', 'default': 'OPM-73-02'},
            {'name': 'method', 'label': 'روش', 'type': 'select',
             'choices': [('comparison', 'مقایسه‌ای (Comparison)'), ('intercept', 'تقاطعی (Intercept)'), ('both', 'هر دو روش')],
             'default': 'comparison'},
            {'name': 'u_cert_machine', 'label': 'Ucert. دستگاه (از گواهی)', 'default': 0.0015},
            {'name': 'res_comparison', 'label': 'رزولوشن مقایسه (گام)', 'default': 0.5},
            {'name': 'res_intercept', 'label': 'رزولوشن تقاطعی (mm)', 'default': 0.001},
        ],
        'grid': [_readings_field('readings_comparison', [('v', 'قرائت مقایسه‌ای (G)')], 10, 'قرائت‌های روش مقایسه‌ای'),
                 _readings_field('readings_intercept', [('v', 'قرائت تقاطعی')], 10, 'قرائت‌های روش تقاطعی')],
    },
    'spectro': {
        'label': 'آنالیز شیمیایی (کوانتومتری)',
        'icon': '⚗️',
        'func': calc_spectro,
        'special': 'spectro',
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'ARL-73-01'},
            {'name': 'family', 'label': 'خانواده ماده', 'type': 'select',
             'choices': [('low_alloy', 'فولاد کم‌آلیاژ (Low Alloy)'), ('steel', 'فولاد (Steel)')], 'default': 'low_alloy'},
            {'name': 'crm_codes', 'label': 'کد(های) CRM/RM استفاده‌شده'},
            {'name': 'resolution', 'label': 'رزولوشن دستگاه', 'default': 0.00001},
        ],
        'grid': [],
    },
    'spectro_regression': {
        'label': 'آنالیز شیمیایی — رگرسیون چند-CRM',
        'icon': '📈',
        'func': calc_spectro_regression,
        'special': 'spectro_regression',
        'fields': [
            {'name': 'machine_code', 'label': 'کد دستگاه', 'default': 'ARL-73-01'},
            {'name': 'family', 'label': 'خانواده ماده', 'type': 'select',
             'choices': [('low_alloy', 'فولاد کم‌آلیاژ (Low Alloy)'), ('steel', 'فولاد (Steel)')], 'default': 'low_alloy'},
            {'name': 'resolution', 'label': 'رزولوشن دستگاه', 'default': 0.00001},
            {'name': 'test_temp', 'label': 'دما (°C)', 'default': 23},
            {'name': 'material', 'label': 'متریال', 'type': 'select',
             'choices': [('steel', 'فولاد'), ('stainless', 'فولاد زنگ‌نزن'), ('aluminum', 'آلومینیم'),
                         ('copper', 'مس'), ('cast_iron', 'چدن'), ('titanium', 'تیتانیم'),
                         ('nickel', 'نیکل')], 'default': 'steel'},
            {'name': 'crm_count', 'label': 'تعداد CRM', 'default': 2},
        ],
        'grid': [],
    },
}


import math

