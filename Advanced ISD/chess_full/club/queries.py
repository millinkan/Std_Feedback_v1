"""Reusable queryset helpers."""

from django.db.models import Case, ExpressionWrapper, F, FloatField, Value, When

from .models import Member


def members_for_leaderboard(sort: str):
    """
    Return members ordered by club ELO or by OTB win rate (percentage of decisive games ignored for draws-only).
    """
    qs = Member.objects.all()
    if sort != 'winpct':
        return qs.order_by('-elo_rating', '-wins')

    return (
        qs.annotate(lb_played=F('wins') + F('losses') + F('draws'))
        .annotate(
            win_pct=Case(
                When(lb_played=0, then=Value(0.0)),
                default=ExpressionWrapper(F('wins') * 100.0 / F('lb_played'), output_field=FloatField()),
            ),
        )
        .order_by('-win_pct', '-elo_rating', '-wins')
    )
