import os, sys, re
BASE = r"D:\LIMS_FINAL_V3"
sys.path.insert(0, BASE)
try:
    mng = open(os.path.join(BASE, "manage.py"), encoding="utf-8").read()
    m = re.search(r"DJANGO_SETTINGS_MODULE[\"'],\s*[\"']([^\"']+)", mng)
    if m: os.environ.setdefault("DJANGO_SETTINGS_MODULE", m.group(1))
    import django; django.setup()
except Exception as e:
    print("Django setup skipped:", e)

from uncertainty.engine import _u_regression, SPECTRO_TABLES
print("="*70)
print("🧪 تست تابع _u_regression با جداول جدید:")
tests = [
    ("low_alloy", "C", 0.05), ("low_alloy", "SI", 0.30), ("low_alloy", "MN", 1.0),
    ("low_alloy", "P", 0.03), ("steel", "C", 0.03), ("steel", "CR", 18.0),
    ("steel", "NI", 8.0), ("steel", "SI", 0.5),
]
for fam, E, x in tests:
    u, seg = _u_regression(fam, E, x)
    
    # پیدا کردن شیب از جدول اصلی برای تشخیص نوع (میانگین یا رگرسیون)
    slope = 1.0
    if seg:
        tbl = SPECTRO_TABLES.get(fam, {}).get(E.upper(), [])
        for lo, hi, m, c in tbl:
            if lo == seg[0] and hi == seg[1]:
                slope = m
                break
                
    kind = "ثابت(میانگین)" if abs(slope) < 1e-12 else "رگرسیون"
    print(f"{fam:9s} {E:3s} x={x:<6} → U={u}  بازه={seg if seg else '—'}  [{kind}]")
    
print("="*70)
print("✅ اگر همه مقادیر U عدد مثبت و معقول بودند، جداول به‌درستی به موتور متصل‌اند.")