"""Context Processor برای تزریق داده‌های سراسری به همه Templateها.

- user_profile: پروفایل کاربر جاری (یا None)
- user_perms: dict دسترسی‌های سفارشی + پیش‌فرض‌های نقش (ادغام‌شده)
- unread_count / unread_notifications: اعلان‌های خوانده‌نشده
- unread_messages_count: پیام‌های خوانده‌نشده
- unseen_audits_count, unseen_reviews_count, ...: شمارنده‌های badge

⚠️ از cache استفاده می‌کند (timeout = 30s) تا کوئری‌های اضافی کاهش یابد.
"""
from django.core.cache import cache
from django.utils import timezone


CACHE_TIMEOUT = 30  # ثانیه


def _empty_context():
    return {
        'user_profile': None,
        'user_perms': {},
        'unread_count': 0,
        'unread_notifications': [],
        'unread_messages_count': 0,
        'unseen_audits_count': 0,
        'unseen_reviews_count': 0,
        'unseen_risks_count': 0,
        'unseen_documents_count': 0,
        'unseen_validations_count': 0,
        'unseen_references_count': 0,
    }


def _build_context(request, profile, perms):
    """ساخت کامل context (بدون cache)."""
    from .models import (
        Message, InternalAudit, ManagementReview, RiskRegister,
        ControlledDocument, MethodValidation, ReferenceStandard,
    )
    from datetime import timedelta

    user = request.user
    today = timezone.now().date()

    # اعلان‌های خوانده‌نشده
    qs = user.notifications.filter(is_read=False)
    unread_count = qs.count()
    unread_notifications = list(qs.order_by('-created_at')[:6])

    # پیام‌های خوانده‌نشده
    try:
        unread_msgs = Message.objects.filter(recipient=user, is_read=False).count()
    except Exception:
        unread_msgs = 0

    # نقش کاربر
    role = (profile.role if profile else '') or ''
    is_super = user.is_superuser

    # ─── ممیزی‌ها ───
    unseen_audits = 0
    try:
        if role == 'lab_supervisor':
            lab_ids = list(profile.supervised_labs.values_list('id', flat=True))
            if profile.lab_section_id:
                lab_ids.append(profile.lab_section_id)
            lab_ids = list(set(lab_ids))
            if lab_ids:
                unseen_audits = InternalAudit.objects.filter(
                    status__in=['planned', 'in_progress', 'completed'],
                    lab_sections__id__in=lab_ids
                ).distinct().count()
        elif role in ('quality_manager', 'head_of_lab'):
            unseen_audits = InternalAudit.objects.filter(status='supervisor_responded').count()
        elif role == 'admin' or is_super:
            unseen_audits = InternalAudit.objects.exclude(status__in=['closed', 'cancelled']).count()
    except Exception:
        pass

    # ─── بازنگری‌های مدیریت ───
    unseen_reviews = 0
    try:
        if role in ('quality_manager', 'head_of_lab', 'admin') or is_super:
            unseen_reviews = ManagementReview.objects.exclude(status__in=['closed', 'cancelled']).count()
        elif role == 'lab_supervisor':
            unseen_reviews = ManagementReview.objects.filter(status='completed').count()
    except Exception:
        pass

    # ─── ریسک‌ها ───
    unseen_risks = 0
    try:
        if role in ('quality_manager', 'head_of_lab', 'admin') or is_super:
            unseen_risks = RiskRegister.objects.filter(
                risk_level__in=['critical', 'high']
            ).exclude(status__in=['closed', 'accepted']).count()
        elif role == 'lab_supervisor':
            unseen_risks = RiskRegister.objects.filter(
                risk_level__in=['critical', 'high'],
                owner=user
            ).exclude(status__in=['closed', 'accepted']).count()
    except Exception:
        pass

    # ─── اسناد سررسید بازنگری ───
    unseen_documents = 0
    try:
        if role in ('quality_manager', 'head_of_lab', 'admin') or is_super:
            unseen_documents = ControlledDocument.objects.filter(
                next_review_date__lte=today,
                next_review_date__isnull=False,
            ).exclude(status__in=['obsolete', 'superseded']).count()
        elif role == 'lab_supervisor':
            unseen_documents = ControlledDocument.objects.filter(
                distribution_list=user,
                next_review_date__lte=today,
                next_review_date__isnull=False,
            ).exclude(status__in=['obsolete', 'superseded']).count()
    except Exception:
        pass

    # ─── اعتبارسنجی‌ها ───
    unseen_validations = 0
    try:
        if role in ('quality_manager', 'head_of_lab', 'admin', 'lab_supervisor') or is_super:
            unseen_validations = MethodValidation.objects.filter(
                next_review_at__lte=today,
                next_review_at__isnull=False,
            ).exclude(status__in=['obsolete', 'rejected']).count()
    except Exception:
        pass

    # ─── استانداردهای مرجع ───
    unseen_references = 0
    try:
        soon = today + timedelta(days=60)
        if role in ('quality_manager', 'head_of_lab', 'admin', 'lab_supervisor', 'lab_operator') or is_super:
            unseen_references = ReferenceStandard.objects.filter(
                expiry_date__lte=soon,
                expiry_date__isnull=False,
                is_active=True,
            ).exclude(status__in=['depleted', 'out_of_service', 'obsolete']).count()
    except Exception:
        pass

    return {
        'user_profile': profile,
        'user_perms': perms,
        'unread_count': unread_count,
        'unread_notifications': unread_notifications,
        'unread_messages_count': unread_msgs,
        'unseen_audits_count': unseen_audits,
        'unseen_reviews_count': unseen_reviews,
        'unseen_risks_count': unseen_risks,
        'unseen_documents_count': unseen_documents,
        'unseen_validations_count': unseen_validations,
        'unseen_references_count': unseen_references,
    }


def notifications(request):
    """تزریق داده‌های سراسری با cache ۳۰ ثانیه‌ای."""
    if not request.user.is_authenticated:
        return _empty_context()

    user = request.user

    # پروفایل و permissions (این‌ها را cache نمی‌کنیم چون سبک هستند)
    profile = getattr(user, 'profile', None)
    perms = {}
    try:
        from .models import ALL_PERMISSIONS, ROLE_DEFAULT_PERMISSIONS
        merged = {code: False for code in ALL_PERMISSIONS}
        if profile and profile.role:
            for code in ROLE_DEFAULT_PERMISSIONS.get(profile.role, []):
                if code in merged:
                    merged[code] = True
        if profile is not None and isinstance(getattr(profile, 'permissions', None), dict):
            for code, val in profile.permissions.items():
                if code in merged:
                    merged[code] = bool(val)
        perms = merged
    except Exception:
        if profile is not None and isinstance(getattr(profile, 'permissions', None), dict):
            perms = profile.permissions

    # ─── Cache برای شمارنده‌ها ───
    cache_key = f'notif_ctx_{user.id}'
    cached_data = cache.get(cache_key)

    if cached_data is None:
        # ساخت کامل (بدون profile/perms که سبک هستند)
        full_ctx = _build_context(request, profile, perms)
        # فقط شمارنده‌ها و لیست اعلان‌ها را cache کن
        cached_data = {
            'unread_count': full_ctx['unread_count'],
            'unread_notifications': full_ctx['unread_notifications'],
            'unread_messages_count': full_ctx['unread_messages_count'],
            'unseen_audits_count': full_ctx['unseen_audits_count'],
            'unseen_reviews_count': full_ctx['unseen_reviews_count'],
            'unseen_risks_count': full_ctx['unseen_risks_count'],
            'unseen_documents_count': full_ctx['unseen_documents_count'],
            'unseen_validations_count': full_ctx['unseen_validations_count'],
            'unseen_references_count': full_ctx['unseen_references_count'],
        }
        cache.set(cache_key, cached_data, CACHE_TIMEOUT)

    return {
        'user_profile': profile,
        'user_perms': perms,
        **cached_data,
    }