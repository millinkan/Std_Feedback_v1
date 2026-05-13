"""django-allauth hooks: stable usernames from email + club profile rows."""

from __future__ import annotations

import re

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model


def _slug_from_email(email: str) -> str:
    local = (email.split('@')[0] if '@' in email else email).strip()
    local = re.sub(r'[^a-zA-Z0-9_]+', '_', local).strip('_') or 'player'
    return local[:30]


class ClubSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Prefer readable usernames; ensure Member + UserProfile exist after OAuth signup."""

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        email = (user.email or data.get('email') or '').strip()
        if email:
            user.email = email
        if email and not user.username:
            User = get_user_model()
            base = _slug_from_email(email)
            candidate = base
            n = 1
            while User.objects.filter(username=candidate).exists():
                suffix = f'_{n}'
                candidate = f'{base[: max(1, 30 - len(suffix))]}{suffix}'
                n += 1
            user.username = candidate
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        from club.member_utils import sync_member_with_user
        from club.models import UserProfile

        UserProfile.objects.get_or_create(user=user)
        sync_member_with_user(user, '')
        return user
