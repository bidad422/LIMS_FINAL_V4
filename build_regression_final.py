import math, json, os
import numpy as np
import pandas as pd
from tabulate import tabulate

BASE = r"D:\LIMS_FINAL_V3"
EXCEL_PATH = os.path.join(BASE, "Book2.xlsx")
OUT_JSON = os.path.join(BASE, "spectro_data_generated.json")

# عناصر مورد نظر و موقعیت شروع آن‌ها در هدر
ELEMENT_STARTS = {
    'C': 9, 'SI': 41, 'S': 73, 'P': 105, 'MN': 137,
    'NI': 169, 'CR': 201, 'MO': 233, 'V': 265, 'CU': 297,
    'W': 329, 'TI': 361, 'SN': 393, 'CO': 425, 'AL': 457,
    'PB': 489, 'B': 521, 'NB': 553, 'ZR': 585, 'N': 617
}
ELEMENTS = list(ELEMENT_STARTS.keys())
READINGS_COUNT = 30  # تعداد تکرارها

def fam_of(cr, ni):
    """دسته‌بندی بر اساس Cr و Ni"""
    cr = cr or 0.0; ni = ni or 0.0
    return 'steel' if (cr > 5 or ni > 2) else 'low_alloy'

print("="*80)
print("🚀 استخراج معادلات رگرسیون از Book2.xlsx")
print("="*80)

# خواندن فایل اکسل
df = pd.read_excel(EXCEL_PATH, header=None)
nrows, ncols = df.shape
print(f"📐 ابعاد فایل: {nrows} سطر × {ncols} ستون")

# استخراج داده‌های CRM (از سطر 2 به بعد)
crms = {}
for r in range(2, nrows):
    code = df.iloc[r, 3]  # ستون CRM Code
    if not isinstance(code, str) or not code.strip().upper().startswith('CRM'):
        continue
    
    code = code.strip()
    desc = df.iloc[r, 4]  # CRM Description
    res = df.iloc[r, 5]   # رزولوشن دستگاه
    res = float(res) if pd.notna(res) else 0.00001
    
    rec = {'desc': desc, 'res': res, 'elems': {}}
    
    # خواندن هر عنصر
    for elem, start_col in ELEMENT_STARTS.items():
        if start_col + 1 >= ncols:
            continue
        
        assigned = df.iloc[r, start_col]
        unc = df.iloc[r, start_col + 1]
        
        if pd.isna(assigned) or pd.isna(unc):
            continue
        
        # خواندن 30 تکرار
        end_col = min(start_col + 2 + READINGS_COUNT, ncols)
        reads = []
        for i in range(start_col + 2, end_col):
            val = df.iloc[r, i]
            if pd.notna(val):
                try:
                    reads.append(float(val))
                except:
                    pass
        
        if len(reads) >= 5:  # حداقل 5 تکرار معتبر
            rec['elems'][elem] = {
                'assigned': float(assigned),
                'unc': float(unc),
                'reads': reads
            }
    
    if rec['elems']:
        crms[code] = rec

print(f"✅ تعداد CRM یافت‌شده: {len(crms)}")

# دسته‌بندی و محاسبه U برای هر CRM
fam_points = {'low_alloy': {}, 'steel': {}}
crm_table = []

for code, rec in sorted(crms.items()):
    cr = (rec['elems'].get('CR') or {}).get('assigned')
    ni = (rec['elems'].get('NI') or {}).get('assigned')
    fam = fam_of(cr, ni)
    
    crm_table.append([
        code,
        str(rec['desc'])[:30] if isinstance(rec['desc'], str) else '—',
        'پرآلیاژ/استنلس' if fam == 'steel' else 'کم‌آلیاژ',
        f"{cr:.3f}" if cr is not None else '—',
        f"{ni:.3f}" if ni is not None else '—'
    ])
    
    u_res = rec['res'] / math.sqrt(12)
    
    for elem, e in rec['elems'].items():
        s = float(np.std(e['reads'], ddof=1))
        u_crm = e['unc'] / 2.0
        u_c = math.sqrt(s**2 + u_res**2 + u_crm**2)
        U = 2.0 * u_c
        
        fam_points[fam].setdefault(elem, []).append((e['assigned'], U))

print("\n📋 دسته‌بندی CRMها:")
print(tabulate(crm_table, headers=['کد CRM', 'شرح', 'دسته', 'Cr%', 'Ni%'], tablefmt='fancy_grid'))

# رگرسیون خطی
def fit(pts):
    if len(pts) < 3:
        return None
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    if np.ptp(xs) == 0:
        return None
    a, b = np.polyfit(xs, ys, 1)
    pred = a * xs + b
    ss_res = np.sum((ys - pred)**2)
    ss_tot = np.sum((ys - ys.mean())**2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return a, b, r2

tables, points_out, report = {}, {}, []

for fam in ('low_alloy', 'steel'):
    tables[fam], points_out[fam] = {}, {}
    
    for elem in sorted(fam_points[fam].keys()):
        pts = sorted(fam_points[fam][elem])
        points_out[fam][elem] = [[round(x, 6), round(y, 8)] for x, y in pts]
        
        f = fit(pts)
        segs = []
        
        if f and f[2] < 0.80 and len(pts) >= 6:
            # تقسیم به دو بازه
            mid = float(np.median([p[0] for p in pts]))
            for sub in ([p for p in pts if p[0] <= mid], [p for p in pts if p[0] > mid]):
                if len(sub) >= 3:
                    fs = fit(sub)
                    if fs:
                        segs.append([
                            min(p[0] for p in sub),
                            max(p[0] for p in sub),
                            fs[0], fs[1]
                        ])
        elif f:
            segs.append([pts[0][0], pts[-1][0], f[0], f[1]])
        
        if segs:
            tables[fam][elem] = [
                [round(lo, 6), round(hi, 6), round(m, 8), round(c, 8)]
                for lo, hi, m, c in segs
            ]
            r2 = f[2] if f else None
            report.append([
                'پرآلیاژ' if fam == 'steel' else 'کم‌آلیاژ',
                elem,
                len(pts),
                f"{segs[0][2]:.6f}",
                f"{segs[0][3]:.6f}",
                f"{r2:.3f}" if r2 is not None else '—',
                len(segs)
            ])

print("\n📊 معادلات رگرسیون U = a·x + b :")
print(tabulate(report, headers=['دسته','عنصر','نقاط','شیب a','عرض b','R²','بازه‌ها'], tablefmt='fancy_grid'))

# ذخیره خروجی
output = {
    'low_alloy': tables['low_alloy'],
    'steel': tables['steel'],
    'points': points_out
}

with open(OUT_JSON, 'w', encoding='utf-8') as fh:
    json.dump(output, fh, ensure_ascii=False, indent=2)

print(f"\n💾 خروجی ذخیره شد: {OUT_JSON}")
print("="*80)