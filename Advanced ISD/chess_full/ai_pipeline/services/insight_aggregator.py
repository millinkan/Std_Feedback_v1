from collections import defaultdict

from ..models import GameAnalysis, MoveEvaluation, PlayerInsight

OPENING_END = 15
MIDDLEGAME_END = 35
BLUNDER_THRESHOLD = 1.5
CPL_HIGH_THRESHOLD = 60.0


def _phase(move_number):
    if move_number <= OPENING_END:
        return 'opening'
    if move_number <= MIDDLEGAME_END:
        return 'middlegame'
    return 'endgame'


def _build_insight(member, category, title, description, recommendation, games_analysed, avg_cpl):
    PlayerInsight.objects.update_or_create(
        member=member,
        category=category,
        title=title,
        defaults={
            'description': description,
            'recommendation': recommendation,
            'games_analysed': games_analysed,
            'avg_centipawn_loss': avg_cpl,
        },
    )


def aggregate_insights(member):
    completed_analyses = (
        GameAnalysis.objects.filter(status='completed', game__player_white=member)
        | GameAnalysis.objects.filter(status='completed', game__player_black=member)
    ).distinct().select_related('game')
    if not completed_analyses.exists():
        return

    game_count = completed_analyses.count()
    phase_cpls, phase_blunders, phase_mistakes = defaultdict(list), defaultdict(int), defaultdict(int)

    for analysis in completed_analyses:
        is_white = analysis.game.player_white == member
        evals = MoveEvaluation.objects.filter(analysis=analysis, is_white=is_white)
        for ev in evals:
            phase = _phase(ev.move_number)
            phase_cpls[phase].append(ev.centipawn_loss)
            if ev.classification == 'blunder':
                phase_blunders[phase] += 1
            elif ev.classification == 'mistake':
                phase_mistakes[phase] += 1

    labels = {'opening': 'Opening', 'middlegame': 'Middlegame', 'endgame': 'Endgame'}
    recommendations = {
        'opening': 'Review opening principles and study a smaller, consistent repertoire.',
        'middlegame': 'Train tactics daily and evaluate threats before committing each move.',
        'endgame': 'Practice fundamental king-pawn and rook endings to improve conversion.',
    }
    for phase in ['opening', 'middlegame', 'endgame']:
        cpls = phase_cpls[phase]
        if not cpls:
            continue
        avg_cpl = round(sum(cpls) / len(cpls), 2)
        blunders_rate = phase_blunders[phase] / game_count
        mistakes_rate = phase_mistakes[phase] / game_count
        if avg_cpl < CPL_HIGH_THRESHOLD and blunders_rate < BLUNDER_THRESHOLD:
            continue

        label = labels[phase]
        description = (
            f'Across {game_count} analysed game(s), average centipawn loss in the {label.lower()} '
            f'was {avg_cpl:.1f}, with {blunders_rate:.1f} blunder(s) and {mistakes_rate:.1f} mistake(s) per game.'
        )
        _build_insight(
            member,
            phase,
            f'{label} Accuracy - Needs Improvement',
            description,
            recommendations[phase],
            game_count,
            avg_cpl,
        )
