"""Aggregates chart and standings payloads for the member dashboard JSON + template."""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from ai_pipeline.models import Game, GameAnalysis, MoveEvaluation

from club.member_utils import member_for_dashboard


def member_games_for_player(member):
    """Single-query games where member played either color."""
    return (
        Game.objects.filter(Q(player_white=member) | Q(player_black=member))
        .select_related('player_white', 'player_black')
        .distinct()
        .order_by('-played_at')
    )


def build_elo_history_for_member(member):
    """
    Display-only trace from this member's imports in time order.

    The signed-in member starts at their club OTB `elo_rating`; opponents start at their stored
    OTB the first time they appear, so the path is not artificially dragged by assuming everyone
    is 1500. (Chart Y-axis is fixed with padding in the dashboard so it does not jitter each refresh.)
    """
    if not member:
        return []

    games = (
        Game.objects.filter(Q(player_white=member) | Q(player_black=member))
        .select_related('player_white', 'player_black')
        .order_by('played_at', 'id')
    )

    baseline = float(member.elo_rating)
    ratings: dict[int, float] = {member.id: baseline}
    history: list[dict] = []
    k_factor = 20

    def rating_or_seed(mid: int, row_member) -> float:
        if mid not in ratings:
            ratings[mid] = float(getattr(row_member, 'elo_rating', 1500.0))
        return ratings[mid]

    for game in games:
        white_id = game.player_white_id
        black_id = game.player_black_id
        if white_id == black_id:
            continue

        white_rating = rating_or_seed(white_id, game.player_white)
        black_rating = rating_or_seed(black_id, game.player_black)

        expected_white = 1.0 / (1.0 + (10 ** ((black_rating - white_rating) / 400.0)))
        expected_black = 1.0 - expected_white

        res = (game.result or '').strip()
        if not res:
            continue

        if res == '1-0':
            score_white, score_black = 1.0, 0.0
        elif res == '0-1':
            score_white, score_black = 0.0, 1.0
        else:
            score_white, score_black = 0.5, 0.5

        white_new = white_rating + k_factor * (score_white - expected_white)
        black_new = black_rating + k_factor * (score_black - expected_black)
        ratings[white_id] = white_new
        ratings[black_id] = black_new

        dt = timezone.localtime(game.played_at)
        # Short axis label: "May 13" style (no leading zero on day); keep id for tooltip/disambiguation.
        label = f'{dt.strftime("%b")} {dt.day}'
        history.append(
            {
                'x': f'{label} · #{game.pk}',
                'y': round(ratings[member.id], 2),
            }
        )
    return history


def build_skill_radar(member):
    labels = ['Opening Accuracy', 'Middlegame Accuracy', 'Endgame Accuracy', 'Tactical Safety']
    if not member:
        return {
            'labels': labels,
            'values': [0.0, 0.0, 0.0, 0.0],
            'games_analysed': 0,
            'plies_sampled': 0,
        }

    analysis_for_member = (
        GameAnalysis.objects.filter(status='completed')
        .filter(Q(game__player_white=member) | Q(game__player_black=member))
        .select_related('game')
        .prefetch_related('move_evaluations')
    )

    opening, middlegame, endgame = [], [], []
    tactical_penalty = 0
    games_analysed = 0
    plies_sampled = 0

    for analysis in analysis_for_member:
        is_white = analysis.game.player_white_id == member.id
        member_moves = [ev for ev in analysis.move_evaluations.all() if ev.is_white == is_white]
        if not member_moves:
            continue
        games_analysed += 1
        for ev in member_moves:
            plies_sampled += 1
            if ev.move_number <= 15:
                opening.append(ev.centipawn_loss)
            elif ev.move_number <= 35:
                middlegame.append(ev.centipawn_loss)
            else:
                endgame.append(ev.centipawn_loss)
            if ev.classification in ('mistake', 'blunder'):
                tactical_penalty += 1

    def accuracy(cpls):
        if not cpls:
            return 0.0
        avg_cpl = sum(cpls) / len(cpls)
        return float(max(0, min(100, round(100 - (avg_cpl * 0.9), 2))))

    tactical_safety = float(max(0, min(100, round(100 - tactical_penalty * 2.5, 2))))
    return {
        'labels': labels,
        'values': [
            accuracy(opening),
            accuracy(middlegame),
            accuracy(endgame),
            tactical_safety,
        ],
        'games_analysed': games_analysed,
        'plies_sampled': plies_sampled,
    }


def build_standings():
    games = Game.objects.select_related('player_white', 'player_black').order_by('played_at')
    standings: dict[int, dict] = {}

    def ensure(m):
        if m.id not in standings:
            standings[m.id] = {
                'member_id': m.id,
                'name': m.display_name,
                'points': 0.0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'played': 0,
                'opponents': set(),
            }
        return standings[m.id]

    for game in games:
        white = ensure(game.player_white)
        black = ensure(game.player_black)
        white['played'] += 1
        black['played'] += 1
        white['opponents'].add(game.player_black_id)
        black['opponents'].add(game.player_white_id)

        if game.result == '1-0':
            white['points'] += 1.0
            white['wins'] += 1
            black['losses'] += 1
        elif game.result == '0-1':
            black['points'] += 1.0
            black['wins'] += 1
            white['losses'] += 1
        else:
            white['points'] += 0.5
            black['points'] += 0.5
            white['draws'] += 1
            black['draws'] += 1

    for item in standings.values():
        item['buchholz'] = round(sum(standings[opp]['points'] for opp in item['opponents'] if opp in standings), 2)
        item.pop('opponents', None)

    sorted_rows = sorted(standings.values(), key=lambda r: (r['points'], r['buchholz'], r['wins']), reverse=True)
    for idx, row in enumerate(sorted_rows, start=1):
        row['rank'] = idx
    return sorted_rows


def build_dashboard_metrics(user, profile):
    member = member_for_dashboard(user, profile.lichess_username)
    return {
        'elo_progress': build_elo_history_for_member(member),
        'skill_radar': build_skill_radar(member),
        'standings': build_standings(),
    }
