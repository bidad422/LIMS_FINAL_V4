"""Draft CRM certificate versions and per-element certificate values."""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import models




# آستانه تفکیک کم/پرآلیاژ (مجموع عناصر آلیاژی به‌جز C, Fe, N)
ALLOY_THRESHOLD_PERCENT = 5.0
ALLOY_EXCLUDE = {'C', 'FE', 'N'}


def classify_matrix_from_elements(assigned_values: dict) -> str:
    """تفکیک matrix بر اساس مجموع عناصر آلیاژی (به‌جز C, Fe, N).
    کم‌آلیاژ: مجموع < ۵٪، پرآلیاژ: مجموع ≥ ۵٪."""
    alloy_sum = 0.0
    for k, v in (assigned_values or {}).items():
        if str(k).upper() in ALLOY_EXCLUDE:
            continue
        try:
            if v is not None:
                alloy_sum += float(v)
        except (TypeError, ValueError):
            pass
    return 'low_alloy' if alloy_sum < ALLOY_THRESHOLD_PERCENT else 'high_alloy'


class CRMCertificateVersion(models.Model):
    MATRIX_CHOICES = [
        ("low_alloy", "Low-alloy / carbon steel"),
        ("austenitic_stainless", "Austenitic stainless steel"),
        ("other_high_alloy", "Other high-alloy steel"),
        ("other", "Other matrix"),
    ]

    reference = models.ForeignKey(
        "core.ReferenceStandard",
        on_delete=models.PROTECT,
        related_name="chemical_crm_certificates",
        limit_choices_to={"standard_type": "crm"},
    )
    version = models.PositiveIntegerField()
    certificate_no = models.CharField(max_length=200)
    producer_name = models.CharField(max_length=200)
    lot_no = models.CharField(max_length=100, blank=True)
    matrix = models.CharField(max_length=40, choices=MATRIX_CHOICES)
    matrix_description = models.CharField(max_length=250, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    certificate_file = models.FileField(
        upload_to="chemical_crm/certificates/%Y/%m/",
        blank=True,
    )
    traceability_statement = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["reference_id", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["reference", "version"],
                name="uq_chem_crm_ref_version",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="ck_chem_crm_version_positive",
            ),
        ]

    def __str__(self):
        return f"{self.certificate_no} / v{self.version}"

    def clean(self):
        super().clean()
        errors = {}

        if self.reference_id and self.reference.standard_type != "crm":
            errors["reference"] = "Select a certified reference material."

        if (
            self.issue_date
            and self.valid_until
            and self.valid_until < self.issue_date
        ):
            errors["valid_until"] = "Validity cannot precede issue date."

        if errors:
            raise ValidationError(errors)


class CRMElementValue(models.Model):
    VALUE_STATUS_CHOICES = [
        ("certified", "Certified"),
        ("reference", "Reference / non-certified"),
        ("indicative", "Indicative / information only"),
    ]
    UNIT_CHOICES = [
        ("mass_percent", "Mass percent"),
        ("mg_kg", "mg/kg"),
    ]
    UNCERTAINTY_KIND_CHOICES = [
        ("unknown", "Not specified / requires review"),
        ("standard", "Standard uncertainty"),
        ("expanded", "Expanded uncertainty"),
        ("ci_half_width", "Confidence interval half-width"),
    ]
    UNCERTAINTY_BASIS_CHOICES = [
        ("absolute", "Absolute, in the assigned-value unit"),
        ("relative_percent", "Relative percent of assigned value"),
    ]

    certificate = models.ForeignKey(
        CRMCertificateVersion,
        on_delete=models.PROTECT,
        related_name="element_values",
    )
    element = models.CharField(max_length=3)
    assigned_value = models.DecimalField(
        max_digits=24, decimal_places=12
    )
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    value_status = models.CharField(
        max_length=20, choices=VALUE_STATUS_CHOICES
    )
    uncertainty_value = models.DecimalField(
        max_digits=24, decimal_places=12,
        null=True, blank=True,
    )
    uncertainty_kind = models.CharField(
        max_length=20,
        choices=UNCERTAINTY_KIND_CHOICES,
        default="unknown",
    )
    uncertainty_basis = models.CharField(
        max_length=20,
        choices=UNCERTAINTY_BASIS_CHOICES,
    )
    coverage_factor = models.DecimalField(
        max_digits=12, decimal_places=6,
        null=True, blank=True,
    )
    coverage_probability_percent = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
    )
    ci_method = models.CharField(
        max_length=20,
        choices=[("unknown", "Requires review"), ("student_t", "Two-sided Student t")],
        default="unknown",
    )
    ci_accepted_mean_count = models.PositiveIntegerField(null=True, blank=True)
    ci_reviewed = models.BooleanField(default=False)
    ci_source = models.TextField(blank=True)

    certificate_text = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["element"]
        constraints = [
            models.UniqueConstraint(
                fields=["certificate", "element"],
                name="uq_chem_crm_cert_element",
            ),
            models.CheckConstraint(
                condition=models.Q(assigned_value__gte=0),
                name="ck_chem_crm_value_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(uncertainty_value__isnull=True)
                    | models.Q(uncertainty_value__gte=0)
                ),
                name="ck_chem_crm_unc_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(coverage_factor__isnull=True)
                    | models.Q(coverage_factor__gt=0)
                ),
                name="ck_chem_crm_k_positive",
            ),
        ]

    def __str__(self):
        return f"{self.element}: {self.assigned_value} {self.unit}"

    @staticmethod
    def _finite(value):
        try:
            return Decimal(str(value)).is_finite()
        except (InvalidOperation, TypeError, ValueError):
            return False

    def clean(self):
        super().clean()
        errors = {}

        symbols = set(
            "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca "
            "Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr "
            "Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba "
            "La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta "
            "W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa "
            "U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs "
            "Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
        )

        self.element = (self.element or "").strip().capitalize()

        if self.element not in symbols:
            errors["element"] = "Use a valid chemical element symbol."

        for name in (
            "assigned_value", "uncertainty_value", "coverage_factor",
            "coverage_probability_percent",
        ):
            value = getattr(self, name)
            if value is not None and not self._finite(value):
                errors[name] = "A finite numeric value is required."

        if self.assigned_value is None:
            errors["assigned_value"] = "Assigned value is required."
        elif "assigned_value" not in errors:
            value = Decimal(str(self.assigned_value))
            limit = Decimal("100") if self.unit == "mass_percent" else Decimal("1000000")
            if value < 0 or value > limit:
                errors["assigned_value"] = "Assigned value is outside the unit limits."

        if (
            self.uncertainty_value is not None
            and "uncertainty_value" not in errors
            and Decimal(str(self.uncertainty_value)) < 0
        ):
            errors["uncertainty_value"] = "Uncertainty cannot be negative."

        if (
            self.coverage_factor is not None
            and "coverage_factor" not in errors
            and Decimal(str(self.coverage_factor)) <= 0
        ):
            errors["coverage_factor"] = "Coverage factor must be positive."

        if (
            self.coverage_probability_percent is not None
            and "coverage_probability_percent" not in errors
            and not Decimal("0") < Decimal(str(self.coverage_probability_percent)) < Decimal("100")
        ):
            errors["coverage_probability_percent"] = "Use a probability between 0 and 100."

        count = self.ci_accepted_mean_count
        if count is not None and (
            isinstance(count, bool) or not isinstance(count, int)
            or not 2 <= count <= 2147483647
        ):
            errors["ci_accepted_mean_count"] = "Use an integer of at least two."
        if self.ci_reviewed:
            if self.uncertainty_kind != "ci_half_width":
                errors["ci_reviewed"] = "CI review applies only to confidence intervals."
            if self.ci_method != "student_t":
                errors["ci_method"] = "Select the documented Student t method."
            if count is None:
                errors["ci_accepted_mean_count"] = "Verified accepted mean count is required."
            if self.coverage_probability_percent is None:
                errors["coverage_probability_percent"] = "Confidence probability is required."
            if not (self.ci_source or "").strip():
                errors["ci_source"] = "Document the source and accepted result identifiers."
            if self.coverage_factor is not None:
                errors["coverage_factor"] = "Leave k empty: Student t is calculated separately."

        if errors:
            raise ValidationError(errors)

    def standard_uncertainty_mass_percent(self):
        """Convert explicit certificate data; never infer k from probability."""
        self.clean()

        if self.value_status != "certified":
            raise ValidationError("This value is not certified.")

        if self.uncertainty_value is None:
            raise ValidationError("Certificate uncertainty is missing.")

        if self.uncertainty_kind == "unknown":
            raise ValidationError("Uncertainty type requires review.")

        u = Decimal(str(self.uncertainty_value))

        if self.uncertainty_basis == "relative_percent":
            u = abs(Decimal(str(self.assigned_value))) * u / Decimal("100")
        elif self.uncertainty_basis != "absolute":
            raise ValidationError("Uncertainty basis requires review.")

        if self.uncertainty_kind == "ci_half_width":
            u /= self.ci_student_t_factor()
        elif self.uncertainty_kind == "expanded":
            if self.coverage_factor is None:
                raise ValidationError("Explicit coverage factor is required.")
            u /= Decimal(str(self.coverage_factor))
        elif self.uncertainty_kind != "standard":
            raise ValidationError("Unsupported uncertainty type.")

        if self.unit == "mg_kg":
            u /= Decimal("10000")
        elif self.unit != "mass_percent":
            raise ValidationError("Unsupported unit.")

        return u

    @property
    def ci_degrees_of_freedom(self):
        count = self.ci_accepted_mean_count
        if isinstance(count, int) and not isinstance(count, bool) and count >= 2:
            return count - 1
        return None

    def ci_student_t_factor(self):
        self.clean()
        if self.uncertainty_kind != "ci_half_width" or not self.ci_reviewed:
            raise ValidationError(
                "Confidence interval conversion requires verified "
                "distribution and conversion metadata."
            )
        from .ci_conversion_v4 import student_t_factor
        try:
            return student_t_factor(
                self.ci_accepted_mean_count, self.coverage_probability_percent
            )
        except (ValueError, ArithmeticError) as error:
            raise ValidationError(str(error)) from error


# نگاشت خانواده فرم عدم‌قطعیت کوانتومتری به ماتریس‌های بانک CRM
FAMILY_TO_MATRICES = {
    "low_alloy": ["low_alloy", "other"],
    "steel": ["austenitic_stainless", "other_high_alloy", "other"],
}


class CRMCertificateVersionStandardU:
    """Bridge helpers — u استاندارد بر حسب mass percent از بانک CRM."""

    @staticmethod
    def defaults_for_family(family=None):
        """جدیدترین نسخه گواهی سازگار با ماتریس → ({ELEMENT: u}, source_label).

        فقط مقادیر certified با عدم‌قطعیت قابل محاسبه (u استاندارد بر حسب
        mass percent از standard_uncertainty_mass_percent) برمی‌گردد.
        در نبود داده بانک، خروجی (dict خالی، '') است تا فرم به جدول JSON
        fallback کند. خطای هر عنصر کل پل را نمی‌شکند (fail-safe).
        """
        matrices = FAMILY_TO_MATRICES.get(family)
        qs = CRMCertificateVersion.objects.select_related("reference").order_by(
            "-version", "-pk")
        if matrices:
            matched = qs.filter(matrix__in=matrices)
            candidates = list(matched) + [c for c in qs if c.matrix not in matrices]
        else:
            candidates = list(qs)

        for cert in candidates:
            values = {}
            for ev in cert.element_values.filter(value_status="certified"):
                try:
                    u = ev.standard_uncertainty_mass_percent()
                except (ValidationError, ArithmeticError, TypeError, ValueError):
                    continue
                values[str(ev.element).strip().upper()] = u
            if values:
                label = (
                    f"{cert.reference.ref_no} — گواهی {cert.certificate_no} "
                    f"نسخه {cert.version}"
                )
                return values, label
        return {}, ""
