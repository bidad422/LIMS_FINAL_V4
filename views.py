import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .engine import CALC_TYPES, SPECTRO_TABLES, ELEMENTS_FA
from .models import UncertaintyRecord

SPECTRO_ELEMENTS = ['C', 'SI', 'MN', 'P', 'S', 'CR', 'NI', 'MO', 'CU', 'V', 'AL', 'NB', 'TI', 'W', 'CO', 'SN']


def _parse_readings(request, grid):
    name = grid['name']
    fields = grid['fields']
    rows = []
    for i in range(grid['count']):
        r = {}
        has = False
        for fname, _label in fields:
            val = (request.POST.get(f'{name}_{i}_{fname}') or '').strip()
            r[fname] = val
            if val:
                has = True
        if has:
            rows.append(r)
    return rows


def _family_of(calc_type):
    return {
        'tensile_round': 'مکانیک (کشش)', 'tensile_flat': 'مکانیک (کشش)',
        'rockwell': 'سختی', 'vickers': 'سختی', 'mhv': 'سختی', 'brinell': 'سختی',
        'impact': 'ضربه', 'grain': 'متالوگرافی', 'spectro': 'آنالیز شیمیایی', 'spectro_crm': 'آنالیز شیمیایی',
    }.get(calc_type, 'سایر')


def _fmt_dec(d):
    s = format(d, 'f')
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s or '0'






def _fmt_unc(val):
    """فرمت‌دهی عدم قطعیت: حذف صفرهای اضافی، حداکثر ۶ رقم اعشار."""
    if val is None or val == '':
        return ''
    try:
        f = float(val)
        s = f"{f:.6f}"
        s = s.rstrip('0').rstrip('.')
        return s if s else '0'
    except (ValueError, TypeError):
        return str(val)

def _crm_u_from_record(rec):
    """مقادیر u را از رفرنس CRM رکورد می‌خواند.
    برمی‌گرداند: (dict, error_msg) — dict خالی + پیغام اگر رفرنس نبود/داده نداشت.
    """
    try:
        from uncertainty.crm_models import CRMCertificateVersion
        crm_code = (rec.crm_code or '').strip() or ((rec.inputs or {}).get('crm_codes') or '').strip()
        if not crm_code:
            return {}, 'کد CRM برای این رکورد تعریف نشده است.'

        # اول reference.name، بعد certificate_no
        crm = CRMCertificateVersion.objects.filter(reference__name=crm_code).first()
        if not crm:
            crm = CRMCertificateVersion.objects.filter(certificate_no=crm_code).first()
        if not crm:
            crm = CRMCertificateVersion.objects.filter(certificate_no__icontains=crm_code).first()
        if not crm:
            return {}, f'رفرنس CRM با کد «{crm_code}» در دیتابیس یافت نشد. لطفاً ابتدا رفرنس را ثبت کنید.'

        result = {}
        for ev in crm.element_values.all():
            if ev.uncertainty_value is not None:
                result[str(ev.element).upper()] = _fmt_unc(ev.uncertainty_value)
        if not result:
            return {}, f'رفرنس «{crm_code}» در دیتابیس هیچ مقدار عدم قطعیتی ندارد.'
        return result, None
    except Exception as e:
        return {}, f'خطا در خواندن رفرنس CRM: {e}'


def _crm_u_defaults(family=None):
    try:
        from .crm_models import CRMCertificateVersionStandardU
        values, label = CRMCertificateVersionStandardU.defaults_for_family(family)
        if values:
            return {k: _fmt_dec(v) for k, v in values.items()}, label, True
    except Exception:
        pass
    crm_ref = SPECTRO_TABLES.get('crm_reference') or {}
    raw = crm_ref.get('crm_u') or {}
    return {str(k).upper(): v for k, v in raw.items()}, (crm_ref.get('code') or ''), False


def _render_form(request, ct, calc_type, inputs=None, status=200):
    field_values = {}
    if inputs:
        for f in ct['fields']:
            field_values[f['name']] = inputs.get(f['name'], '')
        # fallback: اگر فیلد ساده از inputs نیامد ولی در inputs هست، استفاده کن
        for col in ('title', 'test_date', 'operator', 'machine', 'crm_code'):
            if not field_values.get(col) and inputs.get(col):
                field_values[col] = inputs[col]
        # تضمین ucrm دیکشنری
        if ct.get('special') == 'spectro':
            if not isinstance(inputs.get('ucrm'), dict):
                inputs['ucrm'] = {}
            for k in list(inputs.keys()):
                if k.startswith('u_crm_'):
                    elem = k[len('u_crm_'):]
                    if inputs[k] and not inputs['ucrm'].get(elem):
                        inputs['ucrm'][elem] = inputs[k]
    # پشتیبانی از هر دو حالت ucrm دیکشنری و تخت
    if inputs:
        if not isinstance(inputs.get('ucrm'), dict):
            inputs['ucrm'] = {}
        for k in list(inputs.keys()):
            if k.startswith('u_crm_'):
                elem = k[len('u_crm_'):]
                if inputs[k] and not inputs['ucrm'].get(elem):
                    inputs['ucrm'][elem] = inputs[k]

    ctx = {
        'ct': ct, 'calc_type': calc_type, 'inputs': inputs,
        'field_values': field_values,
    }
    if ct.get('special') == 'spectro':
        ctx['spectro_elements'] = SPECTRO_ELEMENTS
        ctx['spectro_rows_range'] = list(range(1, 11))
        family = (inputs or {}).get('family') or 'low_alloy'
        defaults, source_label, from_bank = _crm_u_defaults(family)
        ctx['crm_u_defaults'] = defaults
        ctx['crm_ref_code'] = source_label
        ctx['crm_from_bank'] = from_bank
        # ساخت لیست ucrm برای رندر در HTML: اولویت با مقدار رکورد، سپس پیش‌فرض بانک
        # ترتیب نمایش: اول عناصر رفرنس (به ترتیب SPECTRO_ELEMENTS)، بعد بقیه
        ucrm_from_inputs = (inputs or {}).get('ucrm') or {}
        defaults = ctx.get('crm_u_defaults') or {}
        crm_code = (inputs or {}).get('crm_codes') or (inputs or {}).get('crm_code') or ''

        # ۱. عناصر واقعی رفرنس از دیتابیس
        ref_elems = {}
        if crm_code:
            try:
                from uncertainty.crm_models import CRMCertificateVersion
                crm_obj = CRMCertificateVersion.objects.filter(reference__name=crm_code).first()
                if not crm_obj:
                    crm_obj = CRMCertificateVersion.objects.filter(certificate_no=crm_code).first()
                if crm_obj:
                    for ev in crm_obj.element_values.all():
                        if ev.uncertainty_value is not None:
                            ref_elems[str(ev.element).upper()] = _fmt_unc(ev.uncertainty_value)
            except Exception:
                pass

        # ۲. ادغام: اولویت با ucrm_from_inputs (کاربر دستی)، بعد ref_elems
        merged = dict(ref_elems)
        for k, v in ucrm_from_inputs.items():
            if v:
                merged[str(k).upper()] = v
        if not merged:
            for k, v in (defaults or {}).items():
                if v:
                    merged[str(k).upper()] = v

        # ۳. مرتب‌سازی: SPECTRO_ELEMENTS اول، بعد بقیه
        ordered = [e for e in SPECTRO_ELEMENTS if e in merged]
        for e in sorted(merged.keys()):
            if e not in ordered:
                ordered.append(e)

        ucrm_items = [{'elem': e, 'value': merged[e]} for e in ordered]
        ctx['ucrm_items'] = ucrm_items
        ctx['crm_has_ref'] = bool(ref_elems)
    return render(request, 'uncertainty/form.html', ctx, status=status)


@login_required
def record_list(request):
    qs = UncertaintyRecord.objects.all()
    t = request.GET.get('type', '').strip()
    if t:
        qs = qs.filter(calc_type=t)
    q = (request.GET.get('q') or '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(machine__icontains=q) |
                       Q(operator__icontains=q) | Q(crm_code__icontains=q))
    archived = request.GET.get('archived') == '1'
    if archived:
        qs = qs.filter(is_archived=True)
    else:
        qs = qs.filter(is_archived=False)
    recent = qs[:200]
    return render(request, 'uncertainty/list.html', {
        'records': recent,
        'calc_types': CALC_TYPES,
        'current_type': t,
        'current_q': q,
        'showing_archived': archived,
    })


def parse_spectro_post(request):
    elements = {}
    element_series = {}
    for e in SPECTRO_ELEMENTS:
        series_list = []
        for series_num in range(1, 4):
            vals = []
            for i in range(10):
                v = (request.POST.get(f'series_{series_num}_el{e}_{i}') or '').strip()
                if v:
                    vals.append(v)
            if len(vals) >= 2:
                series_list.append(vals)
        if series_list:
            element_series[e] = series_list
            elements[e] = series_list[0]
    return elements, element_series


@login_required
def new_record(request, calc_type):
    ct = CALC_TYPES.get(calc_type)
    if not ct:
        messages.error(request, 'نوع محاسبه نامعتبر است.')
        return redirect('uncertainty:list')

    inputs = None
    if request.method == 'POST':
        params = {}
        for f in ct['fields']:
            params[f['name']] = (request.POST.get(f['name']) or '').strip()
        inputs = dict(params)
        for g in ct['grid']:
            inputs[g['name']] = _parse_readings(request, g)
        if calc_type == 'spectro':
            elements, element_series = parse_spectro_post(request)
            inputs['elements'] = elements
            inputs['element_series'] = element_series

            ucrm = {}
            for e in SPECTRO_ELEMENTS:
                v = (request.POST.get(f'ucrm_{e}') or '').strip()
                if v:
                    ucrm[e] = v
                    inputs['u_crm_' + e] = v

            bank_defaults, bank_label, from_bank = _crm_u_defaults(params.get('family'))
            if bank_defaults:
                for e in SPECTRO_ELEMENTS:
                    if not ucrm.get(e) and bank_defaults.get(e):
                        ucrm[e] = bank_defaults[e]
                        inputs['u_crm_' + e] = bank_defaults[e]
            inputs['ucrm'] = ucrm
            inputs['crm_u_source'] = bank_label or (SPECTRO_TABLES.get('crm_reference') or {}).get('code', '')
            inputs['crm_u_from_bank'] = from_bank
        try:
            result = ct['func'](inputs)
        except (ValueError, ZeroDivisionError) as exc:
            messages.error(request, f'خطا در محاسبه: {exc}')
            return _render_form(request, ct, calc_type, inputs, status=400)
        except Exception as exc:
            messages.error(request, f'خطای غیرمنتظره در محاسبه: {exc}')
            return _render_form(request, ct, calc_type, inputs, status=400)

        first = (result.get('parameters') or [{}])[0]
        rec = UncertaintyRecord.objects.create(
            calc_type=calc_type,
            title=(request.POST.get('title') or '').strip(),
            machine=(request.POST.get('machine') or params.get('machine_code') or '').strip(),
            test_date=(request.POST.get('test_date') or '').strip(),
            operator=(request.POST.get('operator') or '').strip(),
            crm_code=(request.POST.get('crm_code') or params.get('crm_codes') or '').strip(),
            range_label=(params.get('range_label') or '').strip(),
            lab_family=_family_of(calc_type),
            inputs=inputs,
            results=result,
            summary=result.get('summary', {}),
            parameter_name=first.get('name', '')[:150],
            mean_value=first.get('mean'),
            u_c=first.get('u_c'),
            expanded_U=first.get('U'),
            U_percent=first.get('U_percent'),
            created_by=request.user if request.user.is_authenticated else None,
        )
        messages.success(request, 'محاسبه با موفقیت انجام و ذخیره شد.')
        return redirect('uncertainty:detail', rec_id=rec.id)

    return _render_form(request, ct, calc_type, inputs)


@login_required
def record_detail(request, rec_id):
    rec = get_object_or_404(UncertaintyRecord, id=rec_id)
    ct = CALC_TYPES.get(rec.calc_type, {})
    charts = []
    for prm in (rec.results or {}).get('parameters', []):
        rows = [r for r in prm.get('rows', []) if (r.get('contrib_percent') or 0) > 0.05]
        charts.append({
            'symbol': prm.get('symbol'),
            'labels': [r['source'] for r in rows],
            'values': [round(r.get('contrib_percent') or 0, 1) for r in rows],
        })
    ctx = {
        'rec': rec, 'ct': ct, 'charts': charts,
        'charts_json': json.dumps(charts, ensure_ascii=False),
    }
    if rec.calc_type == 'spectro':
        fam = (rec.inputs or {}).get('family', 'low_alloy')
        segs_all = SPECTRO_TABLES.get(fam, {})
        pts_all = (SPECTRO_TABLES.get('points') or {}).get(fam, {})
        reg_charts = []
        for prm in (rec.results or {}).get('parameters', []):
            E = (prm.get('symbol') or '').upper()
            segs = segs_all.get(E) or []
            if not segs:
                continue
            line = []
            for lo, hi, m, c in segs:
                line.append([round(lo, 6), round(abs(m * lo + c), 8)])
                line.append([round(hi, 6), round(abs(m * hi + c), 8)])
            u_reg_row = next((r for r in prm.get('rows', []) if r.get('symbol') == 'u_reg'), None)
            reg_charts.append({
                'elem': E,
                'name': prm.get('name'),
                'points': pts_all.get(E) or [],
                'line': line,
                'x': round(prm.get('mean') or 0, 6),
                'u': round((u_reg_row or {}).get('u') or 0, 8),
                'range': prm.get('range', ''),
                'U': round(prm.get('U') or 0, 8),
            })
        ctx['reg_charts'] = reg_charts
        ctx['reg_charts_json'] = json.dumps(reg_charts, ensure_ascii=False)
    return render(request, 'uncertainty/detail.html', ctx)


METHOD_DOCS = {
    'spectro': {
        'title': 'آنالیز شیمیایی (کوانتومتری OES)',
        'ref': 'ASTM E415/E1086 + Eurachem/CITAC CG4',
        'rows': [
            ('u_rep = s', 'تکرارپذیری (تک اندازه‌گیری)'),
            ('u_reprod = ANOVA', 'بازتولیدپذیری (سری‌های متعدد)'),
            ('u_res = a/√12', 'رزولوشن دستگاه'),
            ('u_CRM = U_CRM(گواهی)/2', 'عدم‌قطعیت گواهی CRM'),
            ('U_reg(x) = m·x + c', 'رگرسیون U(x) از جداول CRM'),
            ('U = 2·√(Σu²)', 'ترکیبی'),
        ],
        'note': 'رگرسیون قطعه‌ای از 21 CRM با fallback به میانگین برای R²<0.8.',
    },
}


@login_required
def methodology(request):
    fam_tables = {}
    for fam, tbl in SPECTRO_TABLES.items():
        fam_tables[fam] = {e: segs for e, segs in tbl.items()}
    return render(request, 'uncertainty/methodology.html', {
        'method_docs': METHOD_DOCS,
        'calc_types': CALC_TYPES,
        'spectro_tables': fam_tables,
        'elements_fa': ELEMENTS_FA,
    })


@login_required
def record_delete(request, rec_id):
    rec = get_object_or_404(UncertaintyRecord, id=rec_id)
    if request.method == 'POST':
        rec.is_archived = True
        rec.save(update_fields=['is_archived'])
        messages.success(request, 'رکورد به بایگانی منتقل شد.')
    return redirect('uncertainty:list')


@login_required
def record_restore(request, rec_id):
    rec = get_object_or_404(UncertaintyRecord, id=rec_id)
    if request.method == 'POST':
        rec.is_archived = False
        rec.save(update_fields=['is_archived'])
        messages.success(request, 'رکورد از بایگانی بازیابی شد.')
    return redirect('uncertainty:list')


@login_required
def record_recall(request, rec_id):
    """Recall with 3-series support for spectro — واکشی ucrm از رفرنس CRM."""
    rec = get_object_or_404(UncertaintyRecord, id=rec_id)
    ct = CALC_TYPES.get(rec.calc_type)
    if not ct:
        messages.error(request, 'نوع محاسبه این رکورد در نسخه فعلی موجود نیست.')
        return redirect('uncertainty:detail', rec_id=rec.id)

    field_values = {}
    for f in ct['fields']:
        field_values[f['name']] = (rec.inputs or {}).get(f['name'], '')

    inputs = dict(rec.inputs) if rec.inputs else {}
    if ct.get('special') == 'spectro':
        if 'element_series' not in inputs and 'elements' in inputs:
            inputs['element_series'] = {
                elem: [vals] for elem, vals in inputs['elements'].items()
            }

    # پر کردن field_values از ستون‌های مدل (title/test_date/operator/machine/crm_code)
    for col in ('title', 'test_date', 'operator', 'machine', 'crm_code'):
        field_values[col] = getattr(rec, col, '') or ''
        inputs[col] = field_values[col]

    # ============ ucrm: اولویت با رفرنس CRM رکورد ============
    ucrm_dict = {}
    # ۱. اگر در inputs به صورت تخت هست
    for k, v in inputs.items():
        if k.startswith('u_crm_') and v:
            elem = k[len('u_crm_'):]
            ucrm_dict[elem.upper()] = str(v)
    # ۲. اگر دیکشنری ucrm در inputs هست
    if isinstance(inputs.get('ucrm'), dict):
        for k, v in inputs['ucrm'].items():
            if v:
                ucrm_dict[str(k).upper()] = str(v)
    # ۳. اگر هیچ‌کدام نبود → از رفرنس CRM رکورد بخوان
    crm_error = None
    if not ucrm_dict:
        ucrm_from_ref, crm_error = _crm_u_from_record(rec)
        if ucrm_from_ref:
            ucrm_dict = ucrm_from_ref
    if crm_error:
        messages.warning(request, crm_error)
    inputs['ucrm'] = ucrm_dict
    print(f"[record_recall] ucrm keys: {list(ucrm_dict.keys())[:6]}...")
    # ======================================================

    response = _render_form(request, ct, rec.calc_type, inputs)
    if hasattr(response, 'context_data') and response.context_data is not None:
        response.context_data['recall_from'] = rec
    return response

@login_required
def dashboard(request):
    fam = (request.GET.get('family') or '').strip()
    qs = UncertaintyRecord.objects.filter(is_archived=False)
    if fam:
        qs = qs.filter(lab_family=fam)
    latest = qs.order_by('-created_at')[:500]
    families = ['مکانیک (کشش)', 'سختی', 'ضربه', 'متالوگرافی', 'آنالیز شیمیایی']
    return render(request, 'uncertainty/dashboard.html', {
        'records': latest, 'families': families, 'current_family': fam,
    })
