from django import forms
from django.forms import inlineformset_factory
from core.models import ReferenceStandard
from .crm_models import CRMCertificateVersion, CRMElementValue

CHOICES_FA = {
    "": "انتخاب کنید",
    "low_alloy": "فولاد کربنی و کم‌آلیاژ",
    "austenitic_stainless": "فولاد زنگ‌نزن آستنیتی",
    "other_high_alloy": "سایر فولادهای پرآلیاژ",
    "other": "سایر",
    "mass_percent": "درصد وزنی",
    "mg_kg": "میلی‌گرم بر کیلوگرم (mg/kg)",
    "certified": "گواهی‌شده",
    "reference": "مرجع / غیرگواهی‌شده",
    "indicative": "اطلاعاتی / تقریبی",
    "unknown": "نامشخص؛ نیازمند بررسی",
    "standard": "عدم قطعیت استاندارد (u)",
    "expanded": "عدم قطعیت گسترش‌یافته (U)",
    "ci_half_width": "نیم‌عرض فاصلهٔ اطمینان (C95)",
    "student_t": "Student t دوطرفه",
    "absolute": "مطلق؛ در واحد مقدار گواهی",
    "relative_percent": "درصد نسبی از مقدار گواهی",
}

DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫",
    "01234567890123456789."
)


class PersianDecimalField(forms.DecimalField):
    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().translate(DIGITS)
        return super().to_python(value)


def prepare_fields(form):
    for name, field in form.fields.items():
        field.widget.attrs.setdefault("class", "crm-input")
        field.error_messages["required"] = "تکمیل این فیلد الزامی است."
        field.error_messages["invalid"] = "مقدار واردشده معتبر نیست."

        if isinstance(field, forms.ChoiceField):
            field.choices = [
                (value, CHOICES_FA.get(str(value), label))
                for value, label in field.choices
            ]

        if isinstance(field, (forms.DecimalField, forms.IntegerField)):
            field.widget.attrs["dir"] = "ltr"


class CRMCertificateForm(forms.ModelForm):
    class Meta:
        model = CRMCertificateVersion
        fields = (
            "reference", "version", "certificate_no", "producer_name",
            "lot_no", "matrix", "matrix_description", "issue_date",
            "valid_until", "certificate_file", "traceability_statement",
            "instructions", "notes",
        )
        labels = {
            "reference": "نمونهٔ مرجع CRM",
            "version": "نسخهٔ گواهی در بانک",
            "certificate_no": "شمارهٔ گواهی",
            "producer_name": "تولیدکننده",
            "lot_no": "شمارهٔ لات",
            "matrix": "خانوادهٔ ماتریس",
            "matrix_description": "توضیح خانواده و گرید",
            "issue_date": "تاریخ صدور گواهی ـ میلادی",
            "valid_until": "پایان اعتبار در صورت اعلام ـ میلادی",
            "certificate_file": "فایل گواهی PDF",
            "traceability_statement": "بیان ردیابی اندازه‌شناختی",
            "instructions": "شرایط نگهداری و دستورالعمل استفاده",
            "notes": "یادداشت",
        }
        widgets = {
            "issue_date": forms.TextInput(
                attrs={"placeholder": "YYYY-MM-DD", "dir": "ltr"}
            ),
            "valid_until": forms.TextInput(
                attrs={"placeholder": "YYYY-MM-DD", "dir": "ltr"}
            ),
            "traceability_statement": forms.Textarea(attrs={"rows": 3}),
            "instructions": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reference"].queryset = (
            ReferenceStandard.objects.filter(standard_type="crm")
            .order_by("ref_no")
        )
        self.fields["reference"].empty_label = "نمونهٔ مرجع را انتخاب کنید"
        self.fields["version"].min_value = 1
        if not self.instance.pk and not self.is_bound:
            self.initial.setdefault("version", 1)
        prepare_fields(self)

    def clean_certificate_file(self):
        value = self.cleaned_data.get("certificate_file")
        uploaded = self.files.get("certificate_file")
        if uploaded:
            if uploaded.size > 10 * 1024 * 1024:
                raise forms.ValidationError(
                    "حجم فایل باید حداکثر ۱۰ مگابایت باشد."
                )
            header = uploaded.read(5)
            uploaded.seek(0)
            if not uploaded.name.lower().endswith(".pdf") or header != b"%PDF-":
                raise forms.ValidationError("فایل جدید باید PDF معتبر باشد.")
        return value


class CRMElementForm(forms.ModelForm):
    class Meta:
        model = CRMElementValue
        fields = (
            "element", "assigned_value", "unit", "value_status",
            "uncertainty_value", "uncertainty_kind", "uncertainty_basis",
            "coverage_factor", "coverage_probability_percent",
            "certificate_text", "notes",
        )
        labels = {
            "element": "نماد عنصر",
            "assigned_value": "مقدار گواهی",
            "unit": "واحد",
            "value_status": "وضعیت مقدار",
            "uncertainty_value": "عدم قطعیت گواهی",
            "uncertainty_kind": "نوع عدم قطعیت",
            "uncertainty_basis": "مبنای عدم قطعیت",
            "coverage_factor": "ضریب پوشش k",
            "coverage_probability_percent": "احتمال پوشش (%)",
            "ci_method": "روش تبدیل فاصلهٔ اطمینان",
            "ci_accepted_mean_count": "تعداد میانگین‌های پذیرفته‌شدهٔ این عنصر",
            "ci_reviewed": "اطلاعات تبدیل را با منبع بررسی کرده‌ام",
            "ci_source": "منبع تأیید تعداد و شناسهٔ نتایج پذیرفته‌شده",
            "certificate_text": "توضیح یا پاورقی گواهی",
            "notes": "یادداشت",
        }
        field_classes = {
            "assigned_value": PersianDecimalField,
            "uncertainty_value": PersianDecimalField,
            "coverage_factor": PersianDecimalField,
            "coverage_probability_percent": PersianDecimalField,
        }
        widgets = {
            "element": forms.TextInput(attrs={"dir": "ltr"}),
            "assigned_value": forms.TextInput(attrs={"inputmode": "decimal"}),
            "uncertainty_value": forms.TextInput(attrs={"inputmode": "decimal"}),
            "coverage_factor": forms.TextInput(attrs={"inputmode": "decimal"}),
            "coverage_probability_percent": forms.TextInput(
                attrs={"inputmode": "decimal"}
            ),
            "ci_source": forms.Textarea(attrs={"rows": 3}),
            "certificate_text": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        prepare_fields(self)


CRMElementFormSet = inlineformset_factory(
    CRMCertificateVersion,
    CRMElementValue,
    form=CRMElementForm,
    extra=1,
    can_delete=False,
    max_num=118,
    validate_max=True,
    absolute_max=118,
)
