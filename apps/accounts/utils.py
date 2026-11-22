import datetime as dt
from functools import wraps
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core import signing
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone

TRUSTED_COOKIE = "family_device"
_SALT = "trusted-device"


def local_now(family=None):
    tz = ZoneInfo(family.timezone if family else settings.TIME_ZONE)
    return timezone.now().astimezone(tz)


def local_today(family=None) -> dt.date:
    return local_now(family).date()


def set_trusted_device(response, family):
    """FR-AUTH-3: подписанная cookie на 180 дней — устройство становится «семейным»."""
    value = signing.dumps({"family": family.pk}, salt=_SALT)
    response.set_cookie(
        TRUSTED_COOKIE,
        value,
        max_age=settings.TRUSTED_DEVICE_DAYS * 24 * 3600,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
    )
    return response


def trusted_family_id(request):
    raw = request.COOKIES.get(TRUSTED_COOKIE)
    if not raw:
        return None
    try:
        data = signing.loads(raw, salt=_SALT, max_age=settings.TRUSTED_DEVICE_DAYS * 24 * 3600)
    except signing.BadSignature:
        return None
    return data.get("family")


def get_child(request):
    user = request.user
    if user.is_authenticated and user.role == "child" and hasattr(user, "child_profile"):
        return user.child_profile
    return None


def get_parent(request):
    user = request.user
    if user.is_authenticated and hasattr(user, "parent_profile"):
        return user.parent_profile
    return None


def child_required(view):
    """FR-ROLE-1: проверка роли на сервере в каждом представлении."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        child = get_child(request)
        if child is None:
            return redirect("child_start")
        request.child = child
        return view(request, *args, **kwargs)

    return wrapper


def parent_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        parent = get_parent(request)
        if parent is None:
            if request.user.is_authenticated and request.user.role == "child":
                raise Http404
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        request.parent = parent
        return view(request, *args, **kwargs)

    return wrapper
