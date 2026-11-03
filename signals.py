"""Signalهای سراسری سامانه LIMS."""
import logging

from django.contrib.auth.models import User
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import UserProfile, Notification, TestRequest, ExcelRawRow

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, **kwargs):
    """هر User جدید یا موجود بدون profile، یکی خودکار بسازد."""
    UserProfile.objects.get_or_create(user=instance)


def notify_users(users, title, message, link=None, level='info'):
    """ساخت اعلان برای لیستی از کاربران."""
    for u in users:
        if u is None:
            continue
        Notification.objects.create(
            user=u, title=title, message=message, link=link, level=level
        )


def notify_role(role_names, title, message, link=None, level='info'):
    """ساخت اعلان برای همه کاربران یک یا چند نقش."""
    if isinstance(role_names, str):
        role_names = [role_names]
    users = User.objects.filter(profile__role__in=role_names)
    notify_users(users, title, message, link=link, level=level)


@receiver(post_save, sender=TestRequest)
def auto_link_excel_to_request(sender, instance, created, **kwargs):
    """وقتی TestRequest ذخیره می‌شود، اگر Excel data با همان tracking_code باشد، لینک شود."""
    if not instance.tracking_code:
        return

    unlinked = ExcelRawRow.objects.filter(
        tracking_code=instance.tracking_code,
        request__isnull=True,
    )

    count = unlinked.update(request=instance, processed=True)
    if count > 0:
        logger.info(
            'AUTO-LINK: %s Excel rows linked to request %s',
            count, instance.tracking_code,
        )


# ==========================================================
# Cache Invalidation
# ==========================================================
from django.core.cache import cache
from django.db.models.signals import post_save, post_delete


def _invalidate_user_cache(user_id):
    """پاک کردن cache context برای کاربر."""
    try:
        cache.delete(f'notif_ctx_{user_id}')
    except Exception:
        pass


@receiver(post_save, sender=Notification)
def invalidate_notif_cache_on_save(sender, instance, **kwargs):
    """بعد از ساخت/تغییر اعلان، cache کاربر را پاک کن."""
    if instance.user_id:
        _invalidate_user_cache(instance.user_id)


@receiver(post_delete, sender=Notification)
def invalidate_notif_cache_on_delete(sender, instance, **kwargs):
    """بعد از حذف اعلان."""
    if instance.user_id:
        _invalidate_user_cache(instance.user_id)