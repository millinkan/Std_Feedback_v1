"""Keep Django User ↔ Member in sync without changing Lichess / Celery semantics."""

from club.models import Member


def sync_member_with_user(user, lichess_username: str | None = None) -> Member:
    """
    Ensure there is exactly one logical Member row for this user for pipeline tasks.
    Prefers FK user; falls back to display_name=user.username linking.
    """
    lichess_username = (lichess_username or '').strip()

    member = Member.objects.filter(user=user).first()
    if member:
        if lichess_username and member.lichess_username != lichess_username:
            member.lichess_username = lichess_username
            member.save(update_fields=['lichess_username'])
        return member

    loose = Member.objects.filter(display_name=user.username, user__isnull=True).first()
    if loose:
        loose.user = user
        if lichess_username:
            loose.lichess_username = lichess_username
        loose.save()
        return loose

    return Member.objects.create(
        user=user,
        display_name=user.username,
        lichess_username=lichess_username,
    )


def member_for_dashboard(user, lichess_username: str | None) -> Member | None:
    """Resolve Member for AI dashboard metrics (User link first, then Lichess handle)."""
    if user.is_authenticated:
        m = Member.objects.filter(user=user).first()
        if m:
            return m
    lichess_username = (lichess_username or '').strip()
    if lichess_username:
        return Member.objects.filter(lichess_username__iexact=lichess_username).first()
    return None
