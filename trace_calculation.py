import os, sys, inspect
BASE = r"D:\LIMS_FINAL_V3"
sys.path.insert(0, BASE)

try:
    import django
    mng = open(os.path.join(BASE, "manage.py"), encoding="utf-8").read()
    import re
    m = re.search(r"DJANGO_SETTINGS_MODULE[\"'],\s*[\"']([^\"']+)", mng)
    if m: os.environ.setdefault("DJANGO_SETTINGS_MODULE", m.group(1))
    django.setup()
except Exception as e:
    print(f"Django setup: {e}")

print("="*70)
print("🎯 تشخیص مسیر دقیق calc_spectro")
print("="*70)

from uncertainty import engine
from uncertainty.engine import calc_spectro, calc_spectro_crm, _u_regression

print(f"\n📂 مسیر engine.py:")
print(f"   {engine.__file__}")

print(f"\n📂 مسیر calc_spectro:")
print(f"   {inspect.getfile(calc_spectro)}")

print(f"\n📂 مسیر spectro_data.json:")
spectro_file = getattr(engine, '_SPECTRO_FILE', 'NOT FOUND')
print(f"   {spectro_file}")

print(f"\n📊 اطلاعات SPECTRO_TABLES:")
tables = getattr(engine, 'SPECTRO_TABLES', {})
print(f"   کلیدها: {list(tables.keys())}")
if 'low_alloy' in tables:
    print(f"   low_alloy عناصر: {list(tables['low_alloy'].keys())[:10]}...")
if 'steel' in tables:
    print(f"   steel عناصر: {list(tables['steel'].keys())[:10]}...")

print(f"\n🔬 تست یک محاسبه ساده:")
result = calc_spectro({
    'family': 'low_alloy',
    'resolution': 0.00001,
    'elements': {'C': [0.05, 0.051, 0.049, 0.050, 0.052]},
    'ucrm': {'C': 0.001}
})
param = result['parameters'][0]
u_rep_row = next((r for r in param['rows'] if r['symbol'] == 'u_rep'), None)
if u_rep_row:
    print(f"   u_rep = {u_rep_row['u']:.6f}")
    print(f"   note = {u_rep_row['note']}")
    if '√n' in u_rep_row['note']:
        print("   ❌ هنوز از s/√n استفاده می‌شود (کد قدیمی)")
    else:
        print("   ✅ از s استفاده می‌شود (کد جدید)")

print("\n" + "="*70)