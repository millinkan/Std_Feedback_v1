import csv
import json

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from club.models import Member

from .models import Game


def _resolve_game(game_id, prefetch_analysis_moves=False):
    game_id = str(game_id).strip()
    query = Q(lichess_game_id=game_id)
    if game_id.isdigit():
        query = query | Q(pk=int(game_id))
    qs = Game.objects.select_related('player_white', 'player_black')
    if prefetch_analysis_moves:
        qs = qs.prefetch_related('analysis__move_evaluations')
    return get_object_or_404(qs, query)


@login_required
def game_embed(request, game_id):
    game = _resolve_game(game_id)
    return render(request, 'ai_pipeline/game_embed.html', {'game': game})


@login_required
def game_analysis_view(request, game_id):
    game = _resolve_game(game_id, prefetch_analysis_moves=True)
    analysis = getattr(game, 'analysis', None)
    moves = analysis.move_evaluations.all() if analysis else []
    report = None
    if analysis and analysis.status == 'completed':
        white_username = (game.player_white.lichess_username or '').lower()
        black_username = (game.player_black.lichess_username or '').lower()
        profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
        current_username = (profile.lichess_username or '').lower() if profile else ''

        user_side = None
        if current_username and current_username == white_username:
            user_side = 'white'
        elif current_username and current_username == black_username:
            user_side = 'black'

        white_total = analysis.white_blunders + analysis.white_mistakes + analysis.white_inaccuracies
        black_total = analysis.black_blunders + analysis.black_mistakes + analysis.black_inaccuracies

        white_cpl = analysis.white_avg_centipawn_loss or 0
        black_cpl = analysis.black_avg_centipawn_loss or 0
        if user_side == 'white':
            user_cpl = white_cpl
            opp_cpl = black_cpl
            user_errors = white_total
            opp_errors = black_total
            user_label = 'White'
            opp_label = 'Black'
        elif user_side == 'black':
            user_cpl = black_cpl
            opp_cpl = white_cpl
            user_errors = black_total
            opp_errors = white_total
            user_label = 'Black'
            opp_label = 'White'
        else:
            # Fallback for viewers who are not one of the players.
            user_cpl = white_cpl
            opp_cpl = black_cpl
            user_errors = white_total
            opp_errors = black_total
            user_label = 'White'
            opp_label = 'Black'

        focus_areas = []
        if user_errors > 0 and (analysis.white_blunders or analysis.black_blunders):
            focus_areas.append('Reduce blunders by adding a final tactical scan before each move.')
        if user_errors > 0 and (analysis.white_mistakes or analysis.black_mistakes):
            focus_areas.append('Improve middlegame planning with candidate-move comparison.')
        if user_errors > 0 and (analysis.white_inaccuracies or analysis.black_inaccuracies):
            focus_areas.append('Sharpen opening move quality through pattern review and model lines.')
        if not focus_areas:
            focus_areas.append('Maintain consistency and deepen calculation in critical transitions.')

        user_outperformed = user_cpl <= opp_cpl
        summary = (
            f"Stockfish evaluated this game at depth {analysis.depth}. "
            f"Your side ({user_label}) {'showed better practical accuracy' if user_outperformed else 'had lower practical accuracy'} "
            f"than {opp_label} based on average centipawn loss."
        )

        report = {
            'user_side': user_label,
            'opponent_side': opp_label,
            'user_avg_cpl': round(user_cpl, 2),
            'opponent_avg_cpl': round(opp_cpl, 2),
            'user_total_errors': user_errors,
            'opponent_total_errors': opp_errors,
            'user_outperformed': user_outperformed,
            'focus_areas': focus_areas,
            'summary': summary,
        }
    return render(
        request,
        'ai_pipeline/game_analysis.html',
        {'game': game, 'analysis': analysis, 'moves': moves, 'report': report},
    )


@login_required
def player_insights_view(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    insights = member.insights.all()
    return render(
        request,
        'ai_pipeline/player_insights.html',
        {'member': member, 'insights': insights},
    )


@login_required
def export_game_analysis(request, game_id, fmt='json'):
    game = _resolve_game(game_id)
    profile = getattr(request.user, 'profile', None)
    if not profile or not profile.lichess_username:
        return HttpResponse('No linked member profile found.', status=403)
    username = profile.lichess_username.lower()
    allowed = (
        (game.player_white.lichess_username or '').lower() == username
        or (game.player_black.lichess_username or '').lower() == username
    )
    if not allowed:
        return HttpResponse('You are not allowed to export this analysis.', status=403)

    analysis = getattr(game, 'analysis', None)
    if not analysis:
        return HttpResponse('No analysis available for this game.', status=404)

    moves = analysis.move_evaluations.all().values(
        'move_number',
        'is_white',
        'move_san',
        'best_move_san',
        'eval_before',
        'eval_after',
        'centipawn_loss',
        'classification',
    )
    payload = {
        'game_id': game.id,
        'result': game.result,
        'time_control': game.time_control,
        'analysis_status': analysis.status,
        'white_avg_centipawn_loss': analysis.white_avg_centipawn_loss,
        'black_avg_centipawn_loss': analysis.black_avg_centipawn_loss,
        'moves': list(moves),
    }

    if fmt == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="game_{game.id}_analysis.csv"'
        writer = csv.writer(response)
        writer.writerow(['game_id', game.id])
        writer.writerow(['result', game.result])
        writer.writerow(['time_control', game.time_control])
        writer.writerow([])
        writer.writerow(['move_number', 'is_white', 'move_san', 'best_move_san', 'eval_before', 'eval_after', 'centipawn_loss', 'classification'])
        for move in payload['moves']:
            writer.writerow(
                [
                    move['move_number'],
                    move['is_white'],
                    move['move_san'],
                    move['best_move_san'],
                    move['eval_before'],
                    move['eval_after'],
                    move['centipawn_loss'],
                    move['classification'],
                ]
            )
        return response

    response = HttpResponse(json.dumps(payload, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="game_{game.id}_analysis.json"'
    return response
