# -*- coding: utf-8 -*-
"""اطلاعات شرکت — خوانده شده از دیتابیس (قابل ویرایش از ادمین)."""

def get_company_info():
    from core.models import CompanyInfo
    obj = CompanyInfo.get_solo()
    return {
        'company_name_fa': obj.company_name_fa,
        'company_name_en': obj.company_name_en,
        'lab_name_fa': obj.lab_name_fa,
        'lab_subtitle_fa': obj.lab_subtitle_fa,
        'lab_name_en': obj.lab_name_en,
        'address_fa': obj.address_fa,
        'phone': obj.phone,
        'fax': obj.fax,
        'website': obj.website,
        'email': obj.email,
        'form_code': obj.form_code,
        'form_revision': obj.form_revision,
        'form_issue_date': obj.form_issue_date,
        'iso_standard': obj.iso_standard,
        'logo_company': obj.logo_company,
        'logo_lab': obj.logo_lab,
    }


# سازگاری با کد قدیمی
COMPANY_INFO = None  # دیگر استفاده نمی‌شود

def get_company():
    return get_company_info()
