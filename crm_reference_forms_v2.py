from django import forms
from core.models import ReferenceStandard

class CRMReferenceForm(forms.ModelForm):
    class Meta:
        model = ReferenceStandard
        fields = ("ref_no", "name", "manufacturer", "catalog_no", "lot_no", "serial_no")
        labels = {
            "ref_no": "کد شناسایی CRM",
            "name": "نام یا شرح نمونه",
            "manufacturer": "تولیدکننده",
            "catalog_no": "کد کاتالوگ سازنده",
            "lot_no": "شمارهٔ لات",
            "serial_no": "شمارهٔ سریال",
        }
        widgets = {
            "ref_no": forms.TextInput(attrs={"dir": "ltr", "placeholder": "CRM-73-01"}),
        }
        error_messages = {
            "ref_no": {"unique": "این کد شناسایی قبلاً ثبت شده است."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.standard_type = "crm"
        self.fields["ref_no"].required = True
        self.fields["ref_no"].help_text = "کد خود نمونه؛ نه شمارهٔ گواهی."
        for field in self.fields.values():
            field.widget.attrs["style"] = "width:100%;padding:9px;box-sizing:border-box"
            field.error_messages["required"] = "تکمیل این فیلد الزامی است."