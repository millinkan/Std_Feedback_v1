"""Traditional Swiss pairing: score order, upper vs lower half, repair repeats, single full-point bye."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from club.models import Match, Member, SwissParticipant, SwissPairing, SwissRound, SwissTournament


def _played_pairs(tournament: SwissTournament) -> set[frozenset[int]]:
    out: set[frozenset[int]] = set()
    for p in SwissPairing.objects.filter(round__tournament=tournament).select_related('white', 'black'):
        if p.black_id:
            out.add(frozenset({p.white_id, p.black_id}))
    return out


def scores_before_round(tournament: SwissTournament, before_round_number: int) -> dict[int, float]:
    """Tournament points from pairings with a recorded result in rounds strictly before ``before_round_number``."""
    participants = list(
        SwissParticipant.objects.filter(tournament=tournament).values_list('member_id', flat=True),
    )
    totals: dict[int, float] = {mid: 0.0 for mid in participants}
    qs = (
        SwissPairing.objects.filter(round__tournament=tournament, round__number__lt=before_round_number)
        .exclude(Q(result='') | Q(result__isnull=True))
        .select_related('white', 'black')
    )
    for pr in qs:
        w, b = pr.white_id, pr.black_id
        if not b:
            totals[w] = totals.get(w, 0.0) + 1.0
            continue
        if pr.result == Match.RESULT_WHITE:
            totals[w] = totals.get(w, 0.0) + 1.0
        elif pr.result == Match.RESULT_BLACK:
            totals[b] = totals.get(b, 0.0) + 1.0
        elif pr.result == Match.RESULT_DRAW:
            totals[w] = totals.get(w, 0.0) + 0.5
            totals[b] = totals.get(b, 0.0) + 0.5
    return totals


def _sort_key(mid: int, score_map: dict[int, float], members: dict[int, Member]):
    m = members[mid]
    return (-score_map[mid], -m.elo_rating, m.display_name.lower())


def _repair_upper_lower(
    upper: list[int],
    lower: list[int],
    played: set[frozenset[int]],
) -> list[tuple[int, int | None]]:
    """Pair upper[i] vs lower[i], swapping lower assignments to minimise repeat pairings."""
    n = len(upper)
    if n != len(lower):
        raise ValueError('upper and lower must match odd-free bracket size')
    assignments = lower[:]

    def repeat_count(assigns: list[int]) -> int:
        c = 0
        for i in range(n):
            pr = frozenset({upper[i], assigns[i]})
            if pr in played:
                c += 1
        return c

    best = repeat_count(assignments)
    if best == 0:
        return [(upper[i], assignments[i]) for i in range(n)]

    for _ in range(n * n * 2):
        improved = False
        for i in range(n):
            for j in range(i + 1, n):
                assignments[i], assignments[j] = assignments[j], assignments[i]
                rc = repeat_count(assignments)
                if rc < best:
                    best = rc
                    improved = True
                    if best == 0:
                        return [(upper[k], assignments[k]) for k in range(n)]
                else:
                    assignments[i], assignments[j] = assignments[j], assignments[i]
        if not improved:
            break
    return [(upper[i], assignments[i]) for i in range(n)]


def compute_pairings_for_round(
    tournament: SwissTournament,
    round_number: int,
) -> list[tuple[Member, Member | None]]:
    """
    Return list of (white, black or None for bye) boards for ``round_number``.
    ``round_number`` must be the next round to generate (no existing SwissRound with this number).
    """
    parts = list(
        SwissParticipant.objects.filter(tournament=tournament).select_related('member'),
    )
    if len(parts) < 2:
        return []

    member_by_id: dict[int, Member] = {p.member_id: p.member for p in parts}
    mids = [p.member_id for p in parts]
    score_map = scores_before_round(tournament, round_number)
    played = _played_pairs(tournament)

    ordered = sorted(mids, key=lambda mid: _sort_key(mid, score_map, member_by_id))
    bye_id: int | None = None
    work = ordered[:]
    if len(work) % 2 == 1:
        bye_id = work.pop()
    half = len(work) // 2
    upper = work[:half]
    lower = work[half:]
    boards = _repair_upper_lower(upper, lower, played)
    out: list[tuple[Member, Member | None]] = [
        (member_by_id[w], member_by_id[b]) for w, b in boards
    ]
    if bye_id is not None:
        out.append((member_by_id[bye_id], None))
    return out


@transaction.atomic
def generate_next_swiss_round(tournament: SwissTournament) -> SwissRound | None:
    """
    Create the next round and pairings. Returns None if fewer than two players or max rounds reached.
    """
    if tournament.status not in (SwissTournament.STATUS_DRAFT, SwissTournament.STATUS_ACTIVE):
        return None
    next_num = tournament.rounds_played + 1
    if next_num > tournament.rounds_target:
        return None
    if SwissRound.objects.filter(tournament=tournament, number=next_num).exists():
        return None

    boards = compute_pairings_for_round(tournament, next_num)
    if not boards:
        return None

    if tournament.status == SwissTournament.STATUS_DRAFT:
        tournament.status = SwissTournament.STATUS_ACTIVE
        tournament.save(update_fields=['status', 'updated_at'])

    swiss_round = SwissRound.objects.create(tournament=tournament, number=next_num)
    for i, (white, black) in enumerate(boards, start=1):
        kwargs = {'round': swiss_round, 'board': i, 'white': white, 'black': black}
        if black is None:
            kwargs['result'] = Match.RESULT_WHITE
        SwissPairing.objects.create(**kwargs)

    tournament.rounds_played = next_num
    tournament.save(update_fields=['rounds_played', 'updated_at'])
    return swiss_round


def tournament_standings_rows(tournament: SwissTournament) -> list[dict]:
    """Points, Buchholz (sum of opponents' points), W/D/L for display."""
    participants = list(
        SwissParticipant.objects.filter(tournament=tournament).select_related('member'),
    )
    mids = [p.member_id for p in participants]
    score_map = scores_before_round(tournament, tournament.rounds_played + 1)
    opponents: dict[int, set[int]] = {m: set() for m in mids}
    wins = {m: 0 for m in mids}
    draws = {m: 0 for m in mids}
    losses = {m: 0 for m in mids}
    played = {m: 0 for m in mids}

    for pr in SwissPairing.objects.filter(round__tournament=tournament).select_related('white', 'black'):
        w, b = pr.white_id, pr.black_id
        if not pr.result:
            continue
        if b:
            played[w] += 1
            played[b] += 1
            opponents[w].add(b)
            opponents[b].add(w)
            if pr.result == Match.RESULT_WHITE:
                wins[w] += 1
                losses[b] += 1
            elif pr.result == Match.RESULT_BLACK:
                losses[w] += 1
                wins[b] += 1
            else:
                draws[w] += 1
                draws[b] += 1
        else:
            played[w] += 1
            wins[w] += 1

    names = {p.member_id: p.member.display_name for p in participants}
    rows = []
    for m in mids:
        buch = sum(score_map.get(oid, 0.0) for oid in opponents[m])
        rows.append(
            {
                'member_id': m,
                'name': names.get(m, ''),
                'points': round(score_map.get(m, 0.0), 2),
                'buchholz': round(buch, 2),
                'wins': wins[m],
                'draws': draws[m],
                'losses': losses[m],
                'played': played[m],
            }
        )
    rows.sort(key=lambda r: (r['points'], r['buchholz'], r['wins']), reverse=True)
    for i, r in enumerate(rows, start=1):
        r['rank'] = i
    return rows
