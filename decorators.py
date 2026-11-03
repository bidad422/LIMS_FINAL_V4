from functools import wraps
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """
    محدود کردن دسترسی یک view به نقش‌های مشخص.
    استفاده:
        @role_required('reception', 'lab_manager', 'admin')
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            profile = getattr(request.user, 'profile', None)
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if profile and profile.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapper
    return decorator