import os
import sys
import django
import numpy as np
from tabulate import tabulate # برای نمایش جدول زیبا (نیاز به نصب دارد: pip install tabulate)

# راه‌اندازی محیط Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

# وارد کردن مدل‌های شما
from uncertainty.crm_models import CRMCertificateVersion, CRMElementValue

def get_category(matrix):
    """تشخیص دسته بر اساس ماتریس تعریف‌شده در مدل‌های شما"""
    if matrix in ['austenitic_stainless', 'other_high_alloy']:
        return 'High_Alloy'
    return 'Low_Alloy'

def build_regression_models(elements_to_analyze=['C', 'SI', 'MN', 'CR', 'NI']):
    print("="*70)
    print("🚀 شروع استخراج معادلات رگرسیون عدم قطعیت از دیتابیس CRMها")
    print("="*70)
    
    # 1. خواندن تمام مقادیر گواهی‌شده از دیتابیس
    qs = CRMElementValue.objects.filter(
        element__in=elements_to_analyze,
        value_status='certified'
    ).select_related('certificate_version')
    
    # ساختار داده برای دسته‌بندی
    data = {
        'Low_Alloy': {e: {'C': [], 'U': []} for e in elements_to_analyze},
        'High_Alloy': {e: {'C': [], 'U': []} for e in elements_to_analyze}
    }
    
    print(f"✅ تعداد {qs.count()} رکورد معتبر از دیتابیس خوانده شد.")
    
    for val in qs:
        cat = get_category(val.certificate_version.matrix)
        try:
            c = float(val.assigned_value)
            # تبدیل عدم قطعیت استاندارد به گسترده (k=2)
            u_std = float(val.standard_uncertainty_mass_percent())
            U_exp = u_std * 2.0 
            
            data[cat][val.element]['C'].append(c)
            data[cat][val.element]['U'].append(U_exp)
        except Exception:
            continue
            
    # 2. برازش منحنی (رگرسیون خطی: U = a*C + b)
    results = []
    for cat in ['Low_Alloy', 'High_Alloy']:
        for elem in elements_to_analyze:
            C = np.array(data[cat][elem]['C'])
            U = np.array(data[cat][elem]['U'])
            
            if len(C) < 3:
                continue # داده کافی برای رگرسیون نیست
                
            # برازش خطی درجه 1
            try:
                coeffs = np.polyfit(C, U, 1)
                slope, intercept = coeffs[0], coeffs[1]
                
                # محاسبه R-squared برای ارزیابی کیفیت رگرسیون
                U_pred = slope * C + intercept
                ss_res = np.sum((U - U_pred)**2)
                ss_tot = np.sum((U - np.mean(U))**2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                results.append({
                    'Category': 'پرآلیاژ' if cat == 'High_Alloy' else 'کم‌آلیاژ',
                    'Element': elem,
                    'Slope (a)': f"{slope:.6f}",
                    'Intercept (b)': f"{intercept:.6f}",
                    'R²': f"{r_squared:.3f}",
                    'Points': len(C),
                    'Formula': f"U = {slope:.5f}·C + {intercept:.6f}"
                })
            except Exception as e:
                print(f"⚠️ خطا در رگرسیون {elem} برای {cat}: {e}")

    # 3. نمایش نتایج
    print("\n📊 معادلات نهایی برای استفاده در گزارش‌های آزمایشگاه:")
    print(tabulate(results, headers='keys', tablefmt='fancy_grid'))
    
    print("\n" + "="*70)
    print("💡 پیشنهاد:")
    print("این معادلات را می‌توانید در جدول `regression_models` دیتابیس ذخیره کنید")
    print("تا هنگام صدور گواهی برای نمونه مجهول، برنامه به صورت خودکار U را محاسبه کند.")
    print("="*70)

if __name__ == '__main__':
    # نصب tabulate اگر نیست
    try:
        import tabulate
    except ImportError:
        os.system('pip install tabulate')
        import tabulate
        
    build_regression_models()