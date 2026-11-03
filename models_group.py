# -*- coding: utf-8 -*-
"""
مدل‌های گروه تولیدی، واحد، و قیمت‌گذاری
"""
from django.db import models


class ProductionGroup(models.Model):
    """گروه تولیدی"""
    code = models.CharField(max_length=20, unique=True, verbose_name="کد گروه")
    name = models.CharField(max_length=150, verbose_name="نام گروه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    order = models.IntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        ordering = ['order', 'code']
        verbose_name = "گروه تولیدی"
        verbose_name_plural = "۱۰. گروه‌های تولیدی"

    def __str__(self):
        return f"{self.code} — {self.name}"


class CalibrationPricing(models.Model):
    """تعرفه قیمت کالیبراسیون"""
    SCOPE_CHOICES = [
        ('dimensional', 'ابعادی'),
        ('welding', 'جوش و کنترل دما'),
        ('other', 'سایر'),
    ]

    scope = models.CharField(max_length=30, choices=SCOPE_CHOICES,
                             default='dimensional', verbose_name="دامنه")
    equipment_type = models.CharField(max_length=100, verbose_name="نوع تجهیز")
    range_group = models.CharField(max_length=50, blank=True,
                                    verbose_name="گروه رنج")
    range_min = models.FloatField(null=True, blank=True, verbose_name="حد پایین رنج")
    range_max = models.FloatField(null=True, blank=True, verbose_name="حد بالا رنج")
    unit = models.CharField(max_length=30, blank=True, verbose_name="واحد")
    base_price = models.IntegerField(default=0, verbose_name="تعرفه پایه (ریال)")
    extra_per_point = models.IntegerField(default=0,
                                            verbose_name="هزینه هر نقطه اضافه (ریال)")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scope', 'equipment_type', 'range_min']
        verbose_name = "تعرفه کالیبراسیون"
        verbose_name_plural = "۱۱. تعرفه‌های کالیبراسیون"

    def __str__(self):
        r = f"{self.range_min or ''}-{self.range_max or ''}"
        return f"{self.get_scope_display()} / {self.equipment_type} / {r}"