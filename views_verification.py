
# ===== Calibration Verification Views =====
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json
import uuid

from .models_verification_settings import CalibrationVerificationSettings
from .models_verification import (
    CalibrationAcceptanceRule,
    CalibrationVerification,
    CalibrationVerificationPoint,
    CalibrationVerificationEvent,
)
from .services.calibration_verification import evaluate_point





def _next_report_number(settings_obj=None):
    """شماره گزارش بعدی را بر اساس آخرین شماره تولید می‌کند"""
    import re as _re
    prefix = (settings_obj.report_number_prefix if settings_obj else 'CV') or 'CV'
    last = CalibrationVerification.objects.order_by('-id').first()
    if not last or not last.report_number:
        return f"{prefix}-0001"
    # الگوی CV-20261014-E28D یا CV-001 یا CV-XXXX
    m = _re.search(r'(\d+)$', last.report_number)
    if m:
        n = int(m.group(1)) + 1
        width = len(m.group(1))
        return _re.sub(r'\d+$', str(n).zfill(width), last.report_number)
    # اگر الگو نبود، سری جدید بساز
    return f"{prefix}-0001"


def _jalali_to_gregorian(s):
    """تبدیل '1405/07/22' به date میلادی. اگر میلادی بود، همان را برمی‌گرداند."""
    if not s: return None
    s = s.strip().replace('-', '/')
    parts = s.split('/')
    if len(parts) != 3: return None
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if y < 1700:
        try:
            import jdatetime
            return jdatetime.date(y, m, d).togregorian()
        except Exception:
            return None
    try:
        from datetime import date
        return date(y, m, d)
    except Exception:
        return None




def _parse_checklist(request, settings_obj):
    """پاسخ بندهای بازرسی را از POST جمع می‌کند."""
    items = settings_obj.checklist_list()
    out = []
    for idx, item in enumerate(items):
        yes = request.POST.get(f'chk_{idx}') == 'yes'
        no = request.POST.get(f'chk_{idx}') == 'no'
        note = request.POST.get(f'chk_note_{idx}', '').strip()
        out.append({'item': item, 'yes': yes, 'no': no, 'note': note})
    return out


def _gen_report_number(serial=None):
    if serial:
        return f"CV-{serial}"
    today = timezone.now().strftime('%Y%m%d')
    return f"CV-{today}-{uuid.uuid4().hex[:4].upper()}"


def _parse_points_from_post(post):
    """نقاط را از POST می‌خواند و ردیف‌های خالی را نادیده می‌گیرد"""
    indices = set()
    for key in post.keys():
        m = re.match(r'point_(\d+)_error$', key)
        if m:
            indices.add(int(m.group(1)))

    points = []
    for idx in sorted(indices):
        error_raw = (post.get(f'point_{idx}_error') or '').strip()
        nominal_raw = (post.get(f'point_{idx}_nominal') or '').strip()
        u_raw = (post.get(f'point_{idx}_u') or '').strip()
        mpe_raw = (post.get(f'point_{idx}_mpe') or '').strip()

        if not (error_raw or nominal_raw or u_raw or mpe_raw):
            continue
        if not error_raw:
            continue

        def _num(v):
            if v in (None, ''): return None
            try: return float(v)
            except (ValueError, TypeError): return None

        try:
            e = float(error_raw)
        except ValueError:
            continue

        points.append({
            'order': len(points) + 1,
            'nominal': _num(nominal_raw),
            'error_e': e,
            'uncertainty_u': _num(u_raw),
            'mpe': _num(mpe_raw),
        })
    return points


def _aggregate_decision(decisions):
    if 'rejected' in decisions:
        return 'rejected'
    if 'conditional' in decisions:
        return 'conditional'
    if decisions:
        return 'accepted'
    return ''


@login_required
def verification_list(request):
    qs = CalibrationVerification.objects.all()

    decision = request.GET.get('decision')
    unit = request.GET.get('unit')
    code = request.GET.get('code')
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')

    if decision:
        qs = qs.filter(decision=decision)
    if code:
        qs = qs.filter(equipment_code__icontains=code)
    if unit:
        qs = qs.filter(department__icontains=unit)
    if date_from:
        d = _jalali_to_gregorian(date_from)
        if d: qs = qs.filter(evaluation_date__gte=d)
    if date_to:
        d = _jalali_to_gregorian(date_to)
        if d: qs = qs.filter(evaluation_date__lte=d)

    # آماده‌سازی برای نمایش
    rows = []
    for v in qs:
        rows.append({
            'pk': v.pk,
            'report_number': v.report_number,
            'equipment_code': v.equipment_code,
            'equipment_name': v.equipment_name,
            'method_display': v.get_method_display(),
            'method': v.method,
            'decision': v.decision,
            'decision_fa': v.get_decision_display(),
            'date_fa': _to_jalali_str(v.evaluation_date),
            'min_tur': v.min_tur,
            'deactivated': v.equipment_deactivated,
        })

    # آمار خلاصه بر اساس فیلتر فعلی
    stats = {
        'total': qs.count(),
        'accepted': qs.filter(decision='accepted').count(),
        'conditional': qs.filter(decision='conditional').count(),
        'rejected': qs.filter(decision='rejected').count(),
    }

    return render(request, 'calibration/verification_list.html', {
        'verifications': rows,
        'stats': stats,
        'filters': {'decision': decision or '', 'unit': unit or '',
                    'code': code or '', 'from': date_from or '', 'to': date_to or ''},
        'decision_choices': CalibrationVerification.DECISION_CHOICES,
    })

@login_required
def verification_dashboard(request):
    from collections import Counter
    qs = CalibrationVerification.objects.all()
    total = qs.count()
    by_decision = {d[0]: qs.filter(decision=d[0]).count()
                   for d in CalibrationVerification.DECISION_CHOICES}
    by_method_raw = list(qs.values('method').annotate(c=Count('id')).order_by('-c'))
    method_labels = dict(CalibrationVerification.METHOD_CHOICES)
    by_method = [{'key': m['method'], 'label': method_labels.get(m['method'], m['method']), 'count': m['c']}
                 for m in by_method_raw]

    recent_qs = qs.order_by('-created_at')[:10]
    recent = []
    for v in recent_qs:
        recent.append({
            'pk': v.pk,
            'report_number': v.report_number,
            'equipment_code': v.equipment_code,
            'equipment_name': v.equipment_name,
            'decision': v.decision,
            'decision_fa': v.get_decision_display(),
            'date_fa': _to_jalali_str(v.evaluation_date),
            'created_fa': _to_jalali_str(v.created_at),
        })

    # آمار ۶ ماه اخیر
    from datetime import timedelta
    from django.utils import timezone as _tz
    today = _tz.now().date()
    monthly = []
    for i in range(5, -1, -1):
        # اول ماه i ماه پیش
        first = (today.replace(day=1) - timedelta(days=30*i)).replace(day=1)
        if i == 0:
            last = today
        else:
            last = (first.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
        cnt = qs.filter(evaluation_date__gte=first, evaluation_date__lte=last).count()
        monthly.append({'label': _to_jalali_str(first)[:7], 'count': cnt})

    deactivated = qs.filter(equipment_deactivated=True).count()

    return render(request, 'calibration/verification_dashboard.html', {
        'total': total,
        'by_decision': by_decision,
        'by_method': by_method,
        'recent': recent,
        'deactivated': deactivated,
        'monthly': monthly,
    })

@login_required
def verification_detail(request, pk):
    obj = get_object_or_404(CalibrationVerification, pk=pk)
    return render(request, 'calibration/verification_detail.html', {
        'v': obj,
        'points': obj.points.all(),
        'events': obj.events.all(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def verification_create(request, equipment_code=None):
    rules = CalibrationAcceptanceRule.objects.filter(is_active=True)
    if equipment_code:
        rules = rules.filter(equipment_code__iexact=equipment_code)

    if request.method == 'POST':
        # اگر دکمه پیش‌نمایش زده شد، فقط نمایش بده (بدون ذخیره)
        if request.POST.get('action') == 'preview':
            v, pts = _build_unsaved_from_post(request, equipment_code)
            report = _build_report(v, points=pts)
            return render(request, 'calibration/verification_print.html', {
                'v': v, 'report': report, 'is_preview': True,
                'original_post': request.POST,
                'checklist_items': CalibrationVerificationSettings.get_solo().checklist_list(),
            'point_count': len(pts),
            'v_eval_fa': _to_jalali_str(v.evaluation_date),
            'v_cal_fa': _to_jalali_str(v.calibration_date),
        })
        code = request.POST.get('equipment_code') or equipment_code or ''
        method = request.POST.get('method') or 'simple'
        try:
            k = float(request.POST.get('coverage_factor_k') or 2)
        except ValueError:
            k = 2.0
        try:
            f = float(request.POST.get('guard_band_factor') or 1)
        except ValueError:
            f = 1.0
        try:
            thr_acc = float(request.POST.get('threshold_accepted') or 95)
        except ValueError:
            thr_acc = 95.0
        try:
            thr_cond = float(request.POST.get('threshold_conditional') or 75)
        except ValueError:
            thr_cond = 75.0

        points_in = _parse_points_from_post(request.POST)
        if not points_in:
            messages.error(request, 'حداقل یک نقطه اندازه‌گیری لازم است.')
            return redirect(request.path)

        default_mpe = request.POST.get('mpe') or None
        try:
            default_mpe = float(default_mpe) if default_mpe not in (None, '') else None
        except ValueError:
            default_mpe = None

        serial = request.POST.get('asset_serial', '').strip()
        report_number = request.POST.get('report_number') or _gen_report_number(serial)
        v = CalibrationVerification.objects.create(
            report_number=report_number,
            evaluation_date=_jalali_to_gregorian(request.POST.get('evaluation_date')) or timezone.now().date(),
            operator=request.POST.get('operator', ''),
            asset_serial=request.POST.get('asset_serial', ''),
            department=request.POST.get('department', ''),
            customer=request.POST.get('customer', ''),
            equipment_code=code,
            equipment_name=request.POST.get('equipment_name', ''),
            reference_standard=request.POST.get('reference_standard', ''),
            category=request.POST.get('category', ''),
            measurement_range=request.POST.get('measurement_range', ''),
            mpe=default_mpe,
            mpe_calc_type=request.POST.get('mpe_calc_type', 'abs'),
            mpe_b=float(request.POST.get('mpe_b') or 0),
            full_scale=float(request.POST.get('full_scale')) if request.POST.get('full_scale') else None,
            method=method,
            guard_band_factor=f,
            coverage_factor_k=k,
            threshold_accepted=thr_acc,
            threshold_conditional=thr_cond,
            notes=request.POST.get('notes', ''),
            limitations=request.POST.get('limitations', ''),
            corrective_actions=request.POST.get('corrective_actions', ''),
            outsourced_ref=request.POST.get('outsourced_ref', ''),
            certificate_number=request.POST.get('certificate_number', ''),
            calibration_date=_jalali_to_gregorian(request.POST.get('calibration_date')),
            doc_code=request.POST.get('doc_code', 'F192049'),
            doc_version=request.POST.get('doc_version', '1'),
            calibration_lab=request.POST.get('calibration_lab', ''),
            created_by=request.user if request.user.is_authenticated else None,
        )

        decisions = []
        min_tur = None
        for p in points_in:
            mpe = p['mpe'] if p['mpe'] is not None else default_mpe
            r = evaluate_point(
                e=p['error_e'], u=p['uncertainty_u'], mpe=mpe,
                method=method, k=k, f=f,
                threshold_acc=thr_acc, threshold_cond=thr_cond,
            )
            CalibrationVerificationPoint.objects.create(
                verification=v,
                order=p['order'],
                nominal=p['nominal'],
                error_e=p['error_e'],
                abs_e=abs(p['error_e']),
                uncertainty_u=p['uncertainty_u'],
                coverage_factor_k=k,
                mpe=mpe,
                tur=r['tur'],
                conformance_probability=r['conformance_probability'],
                decision=r['decision'],
                explanation=r['explanation'],
            )
            decisions.append(r['decision'])
            if r['tur'] is not None:
                min_tur = r['tur'] if min_tur is None else min(min_tur, r['tur'])

        v.decision = _aggregate_decision(decisions)
        v.min_tur = min_tur
        try:
            v.checklist_answers = _parse_checklist(request, CalibrationVerificationSettings.get_solo())
        except Exception:
            v.checklist_answers = []

        if v.decision == 'rejected':
            v.equipment_deactivated = True
            v.deactivated_at = timezone.now()
            CalibrationVerificationEvent.objects.create(
                verification=v, event_type='equipment_deactivated',
                description='غیرفعال‌سازی خودکار به‌دلیل تصمیم «مردود»',
                user=request.user if request.user.is_authenticated else None,
            )

        v.save()
        CalibrationVerificationEvent.objects.create(
            verification=v, event_type='created',
            description=f'ایجاد با تصمیم {v.get_decision_display()}',
            user=request.user if request.user.is_authenticated else None,
        )
        messages.success(request, f'تصدیق {v.report_number} ثبت شد.')
        return redirect('calibration_verification_detail', pk=v.pk)

    settings_obj = CalibrationVerificationSettings.get_solo()
    # تبدیل تاریخ میلادی به شمسی برای نمایش در فرم
    
    return render(request, 'calibration/verification_form.html', {
        'rules': rules,
        'equipment_code': equipment_code or '',
        'method_choices': CalibrationVerification.METHOD_CHOICES,
        'settings': settings_obj,
        'checklist_items': settings_obj.checklist_list(),
        'suggested_report_number': _next_report_number(settings_obj),
        'existing_eval_fa': '',
        'existing_cal_fa': '',
    })


@login_required
def api_rules_for_equipment(request, code):
    rules = list(CalibrationAcceptanceRule.objects.filter(
        equipment_code__iexact=code, is_active=True
    ).values('id', 'parameter', 'unit', 'measurement_range', 'mpe',
             'mpe_type', 'target_uncertainty', 'standard'))
    return JsonResponse({'rules': rules})


@login_required
def api_equipment_lookup(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'items': []})
    qs = CalibrationAcceptanceRule.objects.filter(
        is_active=True
    ).filter(
        Q(equipment_code__icontains=q) | Q(equipment_name__icontains=q)
    ).values('equipment_code', 'equipment_name').distinct()[:20]
    return JsonResponse({'items': list(qs)})


@login_required
@require_http_methods(["POST"])
def verification_reactivate(request, pk):
    v = get_object_or_404(CalibrationVerification, pk=pk)
    v.equipment_deactivated = False
    v.reactivated_at = timezone.now()
    v.save()
    CalibrationVerificationEvent.objects.create(
        verification=v, event_type='equipment_reactivated',
        description='فعال‌سازی مجدد تجهیز',
        user=request.user if request.user.is_authenticated else None,
    )
    messages.success(request, 'تجهیز فعال شد.')
    return redirect('calibration_verification_detail', pk=pk)

# ===== Report view (updated) =====
from .services.calibration_report import build_report


@login_required
def verification_print(request, pk):
    obj = get_object_or_404(CalibrationVerification, pk=pk)
    report = build_report(obj)
    settings_obj = CalibrationVerificationSettings.get_solo()
    return render(request, 'calibration/verification_print.html', {
        'v': obj,
        'report': report,
        'checklist_items': settings_obj.checklist_list(),
        'point_count': obj.points.count(),
        'v_eval_fa': _to_jalali_str(obj.evaluation_date),
        'v_cal_fa': _to_jalali_str(obj.calibration_date),
        'v_created_fa': _dt_to_jalali_str(obj.created_at),
    })

# ===== Preview view (unsaved) =====
from .services.calibration_report import build_report as _build_report
from .models_verification import CalibrationVerificationPoint as _CVP


class _FakePoints:
    def __init__(self, items): self._items = items
    def all(self): return self._items


def _build_unsaved_from_post(request, equipment_code=None):
    """یک نمونه ذخیره‌نشده برای پیش‌نمایش می‌سازد."""
    code = request.POST.get('equipment_code') or equipment_code or ''
    method = request.POST.get('method') or 'simple'
    def _f(key, default):
        try: return float(request.POST.get(key) or default)
        except (TypeError, ValueError): return default
    k = _f('coverage_factor_k', 2.0)
    f = _f('guard_band_factor', 1.0)
    ta = _f('threshold_accepted', 95.0)
    tc = _f('threshold_conditional', 75.0)
    default_mpe = request.POST.get('mpe') or None
    try: default_mpe = float(default_mpe) if default_mpe not in (None, '') else None
    except ValueError: default_mpe = None

    v = CalibrationVerification()
    v.report_number = request.POST.get('report_number') or _gen_report_number(
        request.POST.get('asset_serial', '').strip() or None)
    v.evaluation_date = _jalali_to_gregorian(request.POST.get('evaluation_date')) or timezone.now().date()
    v.operator = request.POST.get('operator', '')
    v.asset_serial = request.POST.get('asset_serial', '')
    v.department = request.POST.get('department', '')
    v.customer = request.POST.get('customer', '')
    v.equipment_code = code
    v.equipment_name = request.POST.get('equipment_name', '')
    v.reference_standard = request.POST.get('reference_standard', '')
    v.category = request.POST.get('category', '')
    v.measurement_range = request.POST.get('measurement_range', '')
    v.mpe = default_mpe
    v.method = method
    v.guard_band_factor = f
    v.coverage_factor_k = k
    v.threshold_accepted = ta
    v.threshold_conditional = tc
    v.mpe_calc_type = request.POST.get('mpe_calc_type', 'abs')
    v.mpe_b = _f('mpe_b', 0.0)
    fs = request.POST.get('full_scale')
    v.full_scale = float(fs) if fs else None
    v.notes = request.POST.get('notes', '')
    v.limitations = request.POST.get('limitations', '')
    v.corrective_actions = request.POST.get('corrective_actions', '')
    v.certificate_number = request.POST.get('certificate_number', '')
    v.calibration_date = _jalali_to_gregorian(request.POST.get('calibration_date'))
    v.doc_code = request.POST.get('doc_code', 'F192049')
    v.doc_version = request.POST.get('doc_version', '1')
    v.calibration_lab = request.POST.get('calibration_lab', '')

    points_in = _parse_points_from_post(request.POST)
    pts = []
    decisions = []
    min_tur = None
    for p in points_in:
        mpe = p['mpe'] if p['mpe'] is not None else default_mpe
        r = evaluate_point(e=p['error_e'], u=p['uncertainty_u'], mpe=mpe,
                           method=method, k=k, f=f, threshold_acc=ta, threshold_cond=tc)
        pt = _CVP()
        pt.order = p['order']
        pt.nominal = p['nominal']
        pt.error_e = p['error_e']
        pt.abs_e = abs(p['error_e'])
        pt.uncertainty_u = p['uncertainty_u']
        pt.coverage_factor_k = k
        pt.mpe = mpe
        pt.tur = r['tur']
        pt.conformance_probability = r['conformance_probability']
        pt.decision = r['decision']
        pt.explanation = r['explanation']
        pts.append(pt)
        decisions.append(r['decision'])
        if r['tur'] is not None:
            min_tur = r['tur'] if min_tur is None else min(min_tur, r['tur'])
    v.min_tur = min_tur
    v.decision = _aggregate_decision(decisions)
    try:
        v.checklist_answers = _parse_checklist(request, CalibrationVerificationSettings.get_solo())
    except Exception:
        v.checklist_answers = []
    return v, pts


@login_required
@require_http_methods(["POST"])
def verification_preview(request):
    v, pts = _build_unsaved_from_post(request)
    report = _build_report(v, points=pts)
    return render(request, 'calibration/verification_print.html', {
        'v': v, 'report': report, 'is_preview': True,
            'point_count': len(pts),
            'v_eval_fa': _to_jalali_str(v.evaluation_date),
            'v_cal_fa': _to_jalali_str(v.calibration_date),
        })


# ===== Equipment lookup (from bank) =====
def _eq_serialize(eq):
    """فیلدهای احتمالی را به‌صورت انعطاف‌پذیر استخراج می‌کند."""
    def g(*names):
        for n in names:
            v = getattr(eq, n, None)
            if v not in (None, ''):
                return v
        return ''
    return {
        'code': g('code', 'equipment_code', 'asset_code', 'identifier'),
        'name': g('name', 'equipment_name', 'title', 'device_name'),
        'serial': g('serial', 'serial_number', 'asset_serial', 's_n'),
        'manufacturer': g('manufacturer', 'maker', 'brand'),
        'model': g('model', 'model_number'),
        'range': g('measurement_range', 'range', 'measurement_span', 'span'),
        'accuracy': g('accuracy', 'specification'),
        'standard': g('reference_standard', 'standard', 'standard_ref'),
        'category': g('category', 'group', 'type'),
        'lab': g('calibration_lab', 'reference_lab', 'outsourced_lab', 'lab_name'),
        'certificate': g('certificate_number', 'cert_no', 'certificate_no'),
        'location': g('location', 'place'),
    }




def _dt_to_jalali_str(dt):
    """datetime/date -> jalali string with HH:MM"""
    if not dt: return ''
    try:
        import jdatetime
        if hasattr(dt, 'hour'):
            j = jdatetime.datetime.fromgregorian(datetime=dt)
            return f"{j.year:04d}/{j.month:02d}/{j.day:02d} {j.hour:02d}:{j.minute:02d}"
        else:
            j = jdatetime.date.fromgregorian(date=dt)
            return f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
    except Exception:
        try:
            if hasattr(dt, 'strftime'):
                return dt.strftime('%Y/%m/%d %H:%M')
        except Exception:
            pass
        return ''


def _to_jalali_str(gdate):
    """Gregorian -> Jalali string with Latin digits: YYYY/MM/DD"""
    if not gdate: return ''
    try:
        import jdatetime
        j = jdatetime.date.fromgregorian(date=gdate)
        # فرمت دقیق با صفر پیشوند
        return f"{j.year:04d}/{j.month:02d}/{j.day:02d}"
    except Exception:
        try:
            return gdate.strftime('%Y/%m/%d')
        except Exception:
            return ''


@login_required
def api_equipment_info(request, code):
    """اطلاعات کامل تجهیز از CalibrationEquipment + OutsourcedCalibration + CalibrationRegistry"""
    from .models_calib import CalibrationEquipment, CalibrationRegistry, OutsourcedCalibration

    out = {'found': False, 'equipment': {}}
    code = (code or '').strip()
    if not code:
        return JsonResponse(out)

    eq_data = {
        'code': code, 'name': '', 'spec': '', 'range': '', 'accuracy': '',
        'serial': '', 'manufacturer': '', 'model': '', 'location': '',
        'standard': '', 'category': '', 'lab': '', 'certificate': '',
        'calibration_date': '', 'next_calibration': '',
    }

    # 1) CalibrationEquipment
    eq = CalibrationEquipment.objects.filter(code__iexact=code).first()
    if eq:
        eq_data['name'] = eq.name or ''
        eq_data['spec'] = eq.spec or ''
        eq_data['model'] = eq.spec or ''
        eq_data['range'] = eq.range_text or ''
        eq_data['accuracy'] = eq.accuracy or ''
        eq_data['location'] = eq.location or ''
        try:
            eq_data['category'] = str(eq.equipment_group) if eq.equipment_group else ''
        except Exception:
            eq_data['category'] = ''
        out['found'] = True

        # 1a) آخرین OutsourcedCalibration
        oc = OutsourcedCalibration.objects.filter(equipment=eq).order_by('-calibration_date', '-id').first()
        if not oc:
            oc = OutsourcedCalibration.objects.filter(equipment_code__iexact=code).order_by('-calibration_date', '-id').first()
        if oc:
            eq_data['certificate'] = oc.certificate_no or ''
            eq_data['lab'] = oc.calibration_lab or ''
            eq_data['calibration_date'] = _to_jalali_str(oc.calibration_date)
            eq_data['next_calibration'] = _to_jalali_str(oc.next_date)

    # 2) CalibrationRegistry (پشتیبان)
    reg = CalibrationRegistry.objects.filter(equipment_code__iexact=code).order_by('-date_report', '-created_at').first()
    if not reg:
        reg = CalibrationRegistry.objects.filter(equipment_code_base__iexact=code).order_by('-date_report', '-created_at').first()
    if reg:
        out['found'] = True
        if not eq_data['name']: eq_data['name'] = reg.equipment_name or ''
        if not eq_data['range']: eq_data['range'] = reg.range_text or ''
        if not eq_data['accuracy']: eq_data['accuracy'] = reg.accuracy or ''
        if not eq_data['standard']: eq_data['standard'] = reg.standard or ''
        if not eq_data['certificate']: eq_data['certificate'] = reg.certificate_no or ''
        if not eq_data['lab']: eq_data['lab'] = reg.lab or ''
        if not eq_data['calibration_date']:
            eq_data['calibration_date'] = _to_jalali_str(reg.date_report or reg.date_test_current)
        if not eq_data['next_calibration']:
            eq_data['next_calibration'] = _to_jalali_str(reg.date_test_next)

    # 3) پشتیبان آخر از تصدیق‌های قبلی
    if not out['found']:
        prev = CalibrationVerification.objects.filter(equipment_code__iexact=code).order_by('-evaluation_date').first()
        if prev:
            out['found'] = True
            eq_data['name'] = prev.equipment_name or ''
            eq_data['range'] = prev.measurement_range or ''
            eq_data['standard'] = prev.reference_standard or ''
            eq_data['certificate'] = prev.certificate_number or ''
            eq_data['lab'] = prev.calibration_lab or ''
            eq_data['calibration_date'] = _to_jalali_str(prev.calibration_date)

    out['equipment'] = eq_data
    return JsonResponse(out)

# ===== Suggestions API =====
@login_required
def api_equipment_suggestions(request, code):
    """پیشنهادها بر اساس آخرین تصدیق‌های همان تجهیز + رکورد برون‌سپاری"""
    result = {'last': {}, 'certificates': [], 'labs': [], 'standards': [], 'ranges': [],
              'last_points': []}

    # آخرین ۵ تصدیق همین تجهیز
    prev = CalibrationVerification.objects.filter(
        equipment_code__iexact=code
    ).order_by('-evaluation_date')[:5]

    for v in prev:
        for key, val in [('equipment_name', v.equipment_name),
                         ('reference_standard', v.reference_standard),
                         ('measurement_range', v.measurement_range),
                         ('calibration_lab', v.calibration_lab),
                         ('certificate_number', v.certificate_number),
                         ('operator', v.operator),
                         ('doc_code', v.doc_code),
                         ('doc_version', v.doc_version)]:
            if val and not result['last'].get(key):
                result['last'][key] = val
        if v.certificate_number:
            result['certificates'].append(v.certificate_number)
        if v.calibration_lab:
            result['labs'].append(v.calibration_lab)
        if v.reference_standard:
            result['standards'].append(v.reference_standard)
        if v.measurement_range:
            result['ranges'].append(v.measurement_range)

    # نقاط آخرین تصدیق (برای پیشنهاد اسمی‌ها)
    if prev.exists():
        last_v = prev[0]
        for pt in last_v.points.all().order_by('order')[:20]:
            result['last_points'].append({
                'nominal': pt.nominal,
                'u': pt.uncertainty_u,
                'mpe': pt.mpe,
                'error_e': pt.error_e,
            })

    # dedupe
    for key in ('certificates', 'labs', 'standards', 'ranges'):
        result[key] = list(dict.fromkeys([x for x in result[key] if x]))

    return JsonResponse(result)

# ===== Edit view =====
@login_required
@require_http_methods(["GET", "POST"])
def verification_edit(request, pk):
    v = get_object_or_404(CalibrationVerification, pk=pk)

    if request.method == 'POST':
        if request.POST.get('action') == 'preview':
            v2, pts = _build_unsaved_from_post(request, v.equipment_code)
            report = _build_report(v2, points=pts)
            return render(request, 'calibration/verification_print.html', {
                'v': v2, 'report': report, 'is_preview': True,
                'checklist_items': CalibrationVerificationSettings.get_solo().checklist_list(),
            'point_count': len(pts),
            'v_eval_fa': _to_jalali_str(v2.evaluation_date),
            'v_cal_fa': _to_jalali_str(v2.calibration_date),
        })

        # ذخیره
        code = request.POST.get('equipment_code') or v.equipment_code
        method = request.POST.get('method') or v.method
        try: k = float(request.POST.get('coverage_factor_k') or v.coverage_factor_k)
        except ValueError: k = v.coverage_factor_k
        try: f = float(request.POST.get('guard_band_factor') or v.guard_band_factor)
        except ValueError: f = v.guard_band_factor
        try: ta = float(request.POST.get('threshold_accepted') or v.threshold_accepted)
        except ValueError: ta = v.threshold_accepted
        try: tc = float(request.POST.get('threshold_conditional') or v.threshold_conditional)
        except ValueError: tc = v.threshold_conditional

        try:
            default_mpe = float(request.POST.get('mpe') or 0) if request.POST.get('mpe') else None
        except ValueError:
            default_mpe = v.mpe

        v.evaluation_date = _jalali_to_gregorian(request.POST.get('evaluation_date')) or v.evaluation_date
        v.operator = request.POST.get('operator', v.operator)
        v.asset_serial = request.POST.get('asset_serial', v.asset_serial)
        v.department = request.POST.get('department', v.department)
        v.customer = request.POST.get('customer', v.customer)
        v.equipment_code = code
        v.equipment_name = request.POST.get('equipment_name', v.equipment_name)
        v.reference_standard = request.POST.get('reference_standard', v.reference_standard)
        v.category = request.POST.get('category', v.category)
        v.measurement_range = request.POST.get('measurement_range', v.measurement_range)
        v.mpe = default_mpe
        v.method = method
        v.guard_band_factor = f
        v.coverage_factor_k = k
        v.threshold_accepted = ta
        v.threshold_conditional = tc
        v.mpe_calc_type = request.POST.get('mpe_calc_type', v.mpe_calc_type)
        v.mpe_b = float(request.POST.get('mpe_b') or 0)
        fs = request.POST.get('full_scale')
        v.full_scale = float(fs) if fs else None
        v.notes = request.POST.get('notes', v.notes)
        v.limitations = request.POST.get('limitations', v.limitations)
        v.corrective_actions = request.POST.get('corrective_actions', v.corrective_actions)
        v.certificate_number = request.POST.get('certificate_number', v.certificate_number)
        v.calibration_date = _jalali_to_gregorian(request.POST.get('calibration_date')) or v.calibration_date
        v.doc_code = request.POST.get('doc_code', v.doc_code)
        v.doc_version = request.POST.get('doc_version', v.doc_version)
        v.calibration_lab = request.POST.get('calibration_lab', v.calibration_lab)

        # حذف نقاط قدیمی و ساخت جدید
        v.points.all().delete()
        points_in = _parse_points_from_post(request.POST)
        decisions = []
        min_tur = None
        for p in points_in:
            mpe = p['mpe'] if p['mpe'] is not None else default_mpe
            r = evaluate_point(e=p['error_e'], u=p['uncertainty_u'], mpe=mpe,
                               method=method, k=k, f=f, threshold_acc=ta, threshold_cond=tc)
            CalibrationVerificationPoint.objects.create(
                verification=v, order=p['order'], nominal=p['nominal'],
                error_e=p['error_e'], abs_e=abs(p['error_e']),
                uncertainty_u=p['uncertainty_u'], coverage_factor_k=k,
                mpe=mpe, tur=r['tur'],
                conformance_probability=r['conformance_probability'],
                decision=r['decision'], explanation=r['explanation'],
            )
            decisions.append(r['decision'])
            if r['tur'] is not None:
                min_tur = r['tur'] if min_tur is None else min(min_tur, r['tur'])

        old_decision = v.decision
        v.decision = _aggregate_decision(decisions)
        v.min_tur = min_tur

        if v.decision == 'rejected' and not v.equipment_deactivated:
            v.equipment_deactivated = True
            v.deactivated_at = timezone.now()
            CalibrationVerificationEvent.objects.create(
                verification=v, event_type='equipment_deactivated',
                description='غیرفعال‌سازی خودکار به‌دلیل تصمیم مردود',
                user=request.user,
            )
        if old_decision != v.decision:
            CalibrationVerificationEvent.objects.create(
                verification=v, event_type='decision_changed',
                from_value=old_decision, to_value=v.decision,
                description='تغییر تصمیم پس از ویرایش',
                user=request.user,
            )

        v.checklist_answers = _parse_checklist(request, CalibrationVerificationSettings.get_solo())
        v.save()
        messages.success(request, 'تصدیق ویرایش شد.')
        return redirect('calibration_verification_detail', pk=v.pk)

    # GET — پیش‌پر کردن فرم
    settings_obj = CalibrationVerificationSettings.get_solo()
    existing_points = list(v.points.all().order_by('order'))
    # تبدیل تاریخ به شمسی برای جلوگیری از تداخل
    eval_date_fa = _to_jalali_str(v.evaluation_date) if v.evaluation_date else ''
    calib_date_fa = _to_jalali_str(v.calibration_date) if v.calibration_date else ''
    
    return render(request, 'calibration/verification_form.html', {
        'rules': CalibrationAcceptanceRule.objects.filter(is_active=True),
        'equipment_code': v.equipment_code,
        'method_choices': CalibrationVerification.METHOD_CHOICES,
        'settings': settings_obj,
        'checklist_items': settings_obj.checklist_list(),
        'suggested_report_number': v.report_number,
        'existing': v,
        'existing_points': existing_points,
        'existing_eval_fa': eval_date_fa,
        'existing_cal_fa': calib_date_fa,
    })