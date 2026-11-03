import math, json, os
import numpy as np
import pandas as pd
from tabulate import tabulate

BASE = r"D:\LIMS_FINAL_V3"
EXCEL_PATH = os.path.join(BASE, "Book2.xlsx")
SRC_JSON  = os.path.join(BASE, "uncertainty", "spectro_data.json")
OUT_JSON  = os.path.join(BASE, "spectro_data_generated.json")

ELEMENTS = ['C','SI','S','P','MN','NI','CR','MO','V','CU','W','TI','SN','CO','AL','NB','PB','B','ZR','N']

def fam_of(cr, ni):
    cr = cr or 0.0; ni = ni or 0.0
    return 'steel' if (cr > 5 or ni > 2) else 'low_alloy'

raw = pd.read_excel(EXCEL_PATH, header=None)
nrows, ncols = raw.shape

hrow = None
for i in range(min(20, nrows)):
    if any(str(v).strip() == 'CRM Code' for v in raw.iloc[i] if isinstance(v, str)):
        hrow = i; break
if hrow is None: raise SystemExit('سطر هدر یافت نشد!')
hdr = [str(v).strip() if isinstance(v, str) else None for v in raw.iloc[hrow]]
icrm = hdr.index('CRM Code')
istart = icrm + 3

runs, prev, start = [], None, None
for j in range(istart, ncols + 1):
    sym = (hdr[j] or '').upper() if j < ncols else None
    if sym != prev:
        if prev is not None:
            runs.append((prev, start, j))
        prev, start = sym, j
groups = [(s, a, min(b, ncols)) for (s, a, b) in runs if s in ELEMENTS and a + 2 < ncols]
if not groups: raise SystemExit('هیچ گروه عنصری در هدر پیدا نشد!')
widths = [g1 - g0 for _, g0, g1 in groups]
print(f"✅ گروه‌های عنصری: {len(groups)} | عرض min={min(widths)} max={max(widths)}")
if min(widths) < 5:
    raise SystemExit('⚠ عرض گروه‌ها خیلی کوچک است؛ ساختار هدر متفاوت است. خروجی را بفرستید.')

crms = {}
for r in range(hrow + 1, nrows):
    code = raw.iloc[r, icrm]
    if not isinstance(code, str): continue
    code = code.strip()
    if not code.upper().startswith('CRM-'): continue
    rec = crms.setdefault(code, {'desc': raw.iloc[r, icrm + 1], 'res': 0.00001, 'elems': {}})
    res = pd.to_numeric(raw.iloc[r, icrm + 2], errors='coerce')
    res = float(res) if not pd.isna(res) else None
    if res and res > 0: rec['res'] = res
    for sym, g0, g1 in groups:
        a0 = pd.to_numeric(raw.iloc[r, g0], errors='coerce')
        u0 = pd.to_numeric(raw.iloc[r, g0 + 1], errors='coerce')
        reads = pd.to_numeric(raw.iloc[r, g0 + 2:g1], errors='coerce').dropna().tolist()
        e = rec['elems'].setdefault(sym, {'assigned': None, 'unc': None, 'reads': []})
        if e['assigned'] is None and not pd.isna(a0): e['assigned'] = float(a0)
        if e['unc'] is None and not pd.isna(u0): e['unc'] = float(u0)
        e['reads'].extend(float(x) for x in reads)

print(f"✅ تعداد CRM یافت‌شده: {len(crms)}")

fam_points = {'low_alloy': {}, 'steel': {}}
crm_table = []
for code, rec in sorted(crms.items()):
    cr = (rec['elems'].get('CR') or {}).get('assigned')
    ni = (rec['elems'].get('NI') or {}).get('assigned')
    fam = fam_of(cr, ni)
    crm_table.append([code, rec['desc'] if isinstance(rec['desc'], str) else '—',
                      'پرآلیاژ/استنلس' if fam == 'steel' else 'کم‌آلیاژ',
                      cr if cr is not None else '—', ni if ni is not None else '—'])
    u_res = rec['res'] / math.sqrt(12)
    for sym, e in rec['elems'].items():
        if e['assigned'] is None or len(e['reads']) < 5: continue
        s = float(np.std(e['reads'], ddof=1))
        u_crm = (e['unc'] / 2.0) if e['unc'] else 0.0
        u_c = math.sqrt(s ** 2 + u_res ** 2 + u_crm ** 2)
        fam_points[fam].setdefault(sym, []).append((e['assigned'], 2.0 * u_c))

print("\n📋 دسته‌بندی CRMها:")
print(tabulate(crm_table, headers=['کد CRM', 'شرح', 'دسته', 'Cr%', 'Ni%'], tablefmt='fancy_grid'))

def fit(pts):
    xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
    if len(pts) < 3 or np.ptp(xs) == 0: return None
    a, b = np.polyfit(xs, ys, 1)
    pred = a * xs + b
    ss_res = np.sum((ys - pred) ** 2); ss_tot = np.sum((ys - ys.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return a, b, r2

tables, points_out, report = {}, {}, []
for fam in ('low_alloy', 'steel'):
    tables[fam], points_out[fam] = {}, {}
    for sym, pts in sorted(fam_points[fam].items()):
        pts.sort()
        points_out[fam][sym] = [[round(x, 6), round(y, 8)] for x, y in pts]
        f = fit(pts); segs = []
        if f and f[2] < 0.80 and len(pts) >= 6:
            mid = float(np.median([p[0] for p in pts]))
            for sub in ([p for p in pts if p[0] <= mid], [p for p in pts if p[0] > mid]):
                fs = fit(sub)
                if fs: segs.append([min(p[0] for p in sub), max(p[0] for p in sub), fs[0], fs[1]])
        elif f:
            segs.append([pts[0][0], pts[-1][0], f[0], f[1]])
        if segs:
            tables[fam][sym] = [[round(lo, 6), round(hi, 6), round(m, 8), round(c, 8)] for lo, hi, m, c in segs]
            r2 = f[2] if f else None
            report.append(['پرآلیاژ' if fam == 'steel' else 'کم‌آلیاژ', sym, len(pts),
                           f"{segs[0][2]:.6f}", f"{segs[0][3]:.6f}",
                           f"{r2:.3f}" if r2 is not None else '—', len(segs)])

print("\n📊 معادلات رگرسیون U = a·x + b :")
print(tabulate(report, headers=['دسته','عنصر','نقاط','شیب a','عرض b','R²','بازه‌ها'], tablefmt='fancy_grid'))

merged = {}
if os.path.exists(SRC_JSON):
    with open(SRC_JSON, encoding='utf-8') as fh: merged = json.load(fh)
merged.update(tables)
merged['points'] = points_out
with open(OUT_JSON, 'w', encoding='utf-8') as fh:
    json.dump(merged, fh, ensure_ascii=False, indent=1)
print(f"\n💾 خروجی ذخیره شد: {OUT_JSON}")