from django.db import transaction

from club.elo_engine import new_ratings
from club.models import EloHistory, Match, Member


def process_match_completion(match: Match) -> None:
    """
    Apply club ELO and W/L/D for a completed match (idempotent via match.elo_processed).
    Safe to call inside an outer transaction.atomic().
    """
    if match.status != Match.STATUS_COMPLETED or not match.result:
        return
    if match.elo_processed:
        return

    with transaction.atomic():
        locked = Match.objects.select_for_update().get(pk=match.pk)
        if locked.elo_processed:
            return

        white = Member.objects.select_for_update().get(pk=locked.white_player_id)
        black = Member.objects.select_for_update().get(pk=locked.black_player_id)

        white_games = white.wins + white.losses + white.draws
        black_games = black.wins + black.losses + black.draws

        rw, rb = white.elo_rating, black.elo_rating
        nw, nb = new_ratings(rw, rb, locked.result, white_games, black_games)

        EloHistory.objects.create(member=white, match=locked, rating_before=rw, rating_after=nw)
        EloHistory.objects.create(member=black, match=locked, rating_before=rb, rating_after=nb)

        if locked.result == '1-0':
            white.wins += 1
            black.losses += 1
        elif locked.result == '0-1':
            black.wins += 1
            white.losses += 1
        else:
            white.draws += 1
            black.draws += 1

        white.elo_rating = nw
        black.elo_rating = nb
        white.save(update_fields=['elo_rating', 'wins', 'losses', 'draws'])
        black.save(update_fields=['elo_rating', 'wins', 'losses', 'draws'])

        Match.objects.filter(pk=locked.pk).update(elo_processed=True)


def recalculate_all_club_elo() -> int:
    """
    Rebuild EloHistory and club ratings from completed matches in chronological order.
    Returns number of matches replayed.
    """
    with transaction.atomic():
        EloHistory.objects.all().delete()
        Member.objects.all().update(elo_rating=1500.0, wins=0, losses=0, draws=0)
        qs = Match.objects.filter(status=Match.STATUS_COMPLETED).exclude(result='')
        count = qs.count()
        qs.update(elo_processed=False)
        for m in qs.order_by('completed_at', 'pk'):
            process_match_completion(m)
        return count
