"""Mirror Swiss tournament boards into OTB Match rows when organisers opt in."""

from django.utils import timezone

from club.constants import CLUB_PRIMARY_VENUE
from club.models import Match, SwissPairing


def upsert_match_for_pairing(pairing: SwissPairing) -> None:
    tournament = pairing.round.tournament
    if not tournament.counts_for_club_elo or not pairing.result or not pairing.black_id:
        return

    venue = (tournament.venue or '').strip() or CLUB_PRIMARY_VENUE
    anchor = pairing.round.created_at or timezone.now()

    if pairing.club_match_id:
        m = Match.objects.get(pk=pairing.club_match_id)
        m.white_player_id = pairing.white_id
        m.black_player_id = pairing.black_id
        m.status = Match.STATUS_COMPLETED
        m.result = pairing.result
        m.venue = venue
        if not m.completed_at:
            m.completed_at = timezone.now()
        m.save()
        return

    m = Match.objects.create(
        white_player_id=pairing.white_id,
        black_player_id=pairing.black_id,
        status=Match.STATUS_COMPLETED,
        result=pairing.result,
        venue=venue,
        scheduled_at=anchor,
        completed_at=timezone.now(),
    )
    SwissPairing.objects.filter(pk=pairing.pk).update(club_match_id=m.pk)
