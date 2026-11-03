from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile, LabSection, Department


class UserCreateForm(forms.Form):
    """فرم ایجاد کاربر جدید."""

    username = forms.CharField(
        max_length=150, label="نام کاربری (کد پرسنلی)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: 10025'})
    )
    password = forms.CharField(
        label="کلمه عبور",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text="حداقل ۸ کاراکتر شامل حرف و عدد"
    )
    password2 = forms.CharField(
        label="تکرار کلمه عبور",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        max_length=150, label="نام",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150, label="نام خانوادگی",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=False, label="ایمیل",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    personnel_code = forms.CharField(
        required=False, max_length=50, label="کد پرسنلی",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    phone = forms.CharField(
        required=False, max_length=30, label="شماره تماس",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES, label="نقش",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_role'})
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(), required=False, label="واحد سازمانی",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    lab_section = forms.ModelChoiceField(
        queryset=LabSection.objects.filter(is_active=True),
        required=False, label="آزمایشگاه تخصصی (برای کارشناس)",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_lab_section'})
    )
    supervised_labs = forms.ModelMultipleChoiceField(
        queryset=LabSection.objects.filter(is_active=True),
        required=False, label="آزمایشگاه‌های تحت سرپرستی",
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'id_supervised_labs', 'size': '5'})
    )

    def clean_username(self):
        u = self.cleaned_data['username']
        if User.objects.filter(username=u).exists():
            raise forms.ValidationError('این نام کاربری قبلاً استفاده شده است.')
        return u

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('کلمه عبور و تکرار آن یکسان نیستند.')
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                raise forms.ValidationError(e.messages)
        role = cleaned.get('role')
        if role == 'lab_operator' and not cleaned.get('lab_section'):
            self.add_error('lab_section', 'برای نقش «کارشناس آزمایشگاه»، انتخاب آزمایشگاه الزامی است.')
        if role == 'lab_supervisor' and not cleaned.get('supervised_labs'):
            self.add_error('supervised_labs', 'برای نقش «سرپرست»، انتخاب حداقل یک آزمایشگاه الزامی است.')
        return cleaned


class UserEditForm(forms.Form):
    """فرم ویرایش کاربر (بدون پسورد)."""

    first_name = forms.CharField(max_length=150, label="نام", widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, label="نام خانوادگی", widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, label="ایمیل", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    personnel_code = forms.CharField(required=False, max_length=50, label="کد پرسنلی", widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(required=False, max_length=30, label="شماره تماس", widget=forms.TextInput(attrs={'class': 'form-control'}))

    role = forms.ChoiceField(choices=UserProfile.ROLE_CHOICES, label="نقش", widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_role'}))
    department = forms.ModelChoiceField(queryset=Department.objects.all(), required=False, label="واحد سازمانی", widget=forms.Select(attrs={'class': 'form-select'}))
    lab_section = forms.ModelChoiceField(
        queryset=LabSection.objects.filter(is_active=True),
        required=False, label="آزمایشگاه تخصصی (برای کارشناس)",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_lab_section'})
    )
    supervised_labs = forms.ModelMultipleChoiceField(
        queryset=LabSection.objects.filter(is_active=True),
        required=False, label="آزمایشگاه‌های تحت سرپرستی",
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'id': 'id_supervised_labs', 'size': '5'})
    )

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get('role')
        if role == 'lab_operator' and not cleaned.get('lab_section'):
            self.add_error('lab_section', 'برای نقش «کارشناس آزمایشگاه»، انتخاب آزمایشگاه الزامی است.')
        if role == 'lab_supervisor' and not cleaned.get('supervised_labs'):
            self.add_error('supervised_labs', 'برای نقش «سرپرست»، انتخاب حداقل یک آزمایشگاه الزامی است.')
        return cleaned


class UserChangePasswordForm(forms.Form):
    new_password = forms.CharField(
        label="کلمه عبور جدید",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    new_password2 = forms.CharField(
        label="تکرار کلمه عبور جدید",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('کلمه عبور و تکرار آن یکسان نیستند.')
        if p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                raise forms.ValidationError(e.messages)
        return cleaned
from .models import Equipment, Standard


class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['name', 'code', 'asset_no', 'manufacturer', 'model_name',
                  'serial_no', 'measurement_range', 'resolution',
                  'calibration_interval_months', 'calibration_status', 'last_calibration_date',
                  'next_calibration_date', 'calibration_certificate_no', 'metrological_traceability',
                  'is_active', 'is_default', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'asset_no': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'model_name': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_no': forms.TextInput(attrs={'class': 'form-control'}),
            'measurement_range': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: 0-150 mm'}),
            'resolution': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: 0.01 mm'}),
            'calibration_interval_months': forms.NumberInput(attrs={'class': 'form-control'}),
            'calibration_status': forms.Select(attrs={'class': 'form-select'}),
            'last_calibration_date': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1405/06/01'}),
            'next_calibration_date': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1406/06/01'}),
            'calibration_certificate_no': forms.TextInput(attrs={'class': 'form-control'}),
            'metrological_traceability': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Traceability chain / certificate'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class StandardForm(forms.ModelForm):
    class Meta:
        model = Standard
        fields = ['code', 'title', 'revision', 'year', 'is_active', 'is_default', 'notes']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: ASTM E8'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'revision': forms.TextInput(attrs={'class': 'form-control'}),
            'year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: 2022'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }