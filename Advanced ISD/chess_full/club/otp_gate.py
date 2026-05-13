"""Optional member TOTP gate (django-otp) without blocking setup or OTP verification routes."""

from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp import user_has_device


def otp_verified_safe(user) -> bool:
    """
    True when TOTP challenge is unnecessary (no device) or django-otp considers the session verified.

    Django's plain User gains ``is_verified`` only once OTP middleware / login flow has patched it.
    Calling ``user.is_verified()`` directly from LoginView.get_success_url can raise AttributeError.
    """
    if not getattr(user, 'is_authenticated', False):
        return False
    if not user_has_device(user):
        return True
    checker = getattr(user, 'is_verified', None)
    if not callable(checker):
        return False
    try:
        return bool(checker())
    except Exception:
        return False


def _fallback_next(request) -> str:
    target = getattr(settings, 'LOGIN_REDIRECT_URL', '') or ''
    try:
        if target.startswith('/'):
            return target
        return reverse(target)
    except Exception:
        return reverse('club:dashboard')


def otp_session_redirect_if_needed(request):
    path = request.path or ''
    if path.startswith('/login/otp'):
        return None

    user = request.user
    if not getattr(user, 'is_authenticated', False):
        return None
    if not user_has_device(user):
        return None
    if otp_verified_safe(user):
        return None

    raw = request.get_full_path()[:2048]
    safe = resolve_safe_next(request, raw)

    return redirect(f"{reverse('club:otp_verify')}?next={quote(safe, safe='/')}")


def resolve_safe_next(request, raw_next: str | None) -> str:
    raw_next = raw_next or ''
    if raw_next.startswith('/') and not raw_next.startswith('//'):
        return raw_next
    if raw_next and url_has_allowed_host_and_scheme(
        raw_next,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return raw_next
    return _fallback_next(request)
