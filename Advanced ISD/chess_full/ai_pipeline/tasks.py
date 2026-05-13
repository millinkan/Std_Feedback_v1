import logging
from datetime import datetime, timezone as dt_tz

from celery import shared_task
from django.utils import timezone as django_tz

from club.models import Member

from .models import Game, GameAnalysis, MoveEvaluation
from .services.insight_aggregator import aggregate_insights
from .services.lichess_api import LichessAPIError, LichessClient
from .services.stockfish_analysis import analyse_game

logger = logging.getLogger(__name__)


def _resolve_member_for_player(player_name, tracked_username, tracked_member):
    normalized = (player_name or '').strip()
    if normalized and normalized.lower() == tracked_username.lower():
        return tracked_member
    if normalized:
        opponent, _ = Member.objects.get_or_create(
            lichess_username=normalized,
            defaults={'display_name': normalized},
        )
        if opponent.display_name != normalized:
            opponent.display_name = normalized
            opponent.save(update_fields=['display_name'])
        return opponent
    return tracked_member


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def analyse_game_task(self, game_id):
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        logger.error('analyse_game_task: Game %s not found.', game_id)
        return

    analysis, _ = GameAnalysis.objects.get_or_create(game=game)
    analysis.status = 'processing'
    analysis.error_message = ''
    analysis.save(update_fields=['status', 'error_message'])

    try:
        result = analyse_game(game.pgn)
        move_objects = [
            MoveEvaluation(
                analysis=analysis,
                move_number=m['move_number'],
                is_white=m['is_white'],
                move_san=m['move_san'],
                best_move_san=m['best_move_san'],
                eval_before=m['eval_before'],
                eval_after=m['eval_after'],
                centipawn_loss=m['centipawn_loss'],
                classification=m['classification'],
            )
            for m in result['moves']
        ]
        analysis.move_evaluations.all().delete()
        MoveEvaluation.objects.bulk_create(move_objects)

        analysis.white_avg_centipawn_loss = result['white_avg_cpl']
        analysis.black_avg_centipawn_loss = result['black_avg_cpl']
        analysis.white_blunders = result['white_blunders']
        analysis.black_blunders = result['black_blunders']
        analysis.white_mistakes = result['white_mistakes']
        analysis.black_mistakes = result['black_mistakes']
        analysis.white_inaccuracies = result['white_inaccuracies']
        analysis.black_inaccuracies = result['black_inaccuracies']
        analysis.status = 'completed'
        analysis.analysed_at = django_tz.now()
        analysis.save()

        # Keep user insights current automatically after each completed analysis.
        generate_insights_task.delay(game.player_white_id)
        if game.player_black_id != game.player_white_id:
            generate_insights_task.delay(game.player_black_id)
    except Exception as exc:
        logger.exception('analyse_game_task failed for game %s', game_id)
        analysis.status = 'failed'
        analysis.error_message = str(exc)
        analysis.save(update_fields=['status', 'error_message'])
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def fetch_lichess_games_task(self, lichess_username, member_id, api_token=''):
    try:
        member = Member.objects.get(pk=member_id)
    except Member.DoesNotExist:
        logger.error('fetch_lichess_games_task: Member %s not found.', member_id)
        return

    client = LichessClient(api_token=api_token)
    try:
        raw_games = client.fetch_recent_games(lichess_username)
    except LichessAPIError as exc:
        raise self.retry(exc=exc)

    for raw in raw_games:
        lichess_id = raw.get('id')
        if not lichess_id or Game.objects.filter(lichess_game_id=lichess_id).exists():
            continue

        players = raw.get('players', {})
        white_name = players.get('white', {}).get('user', {}).get('name', '')
        black_name = players.get('black', {}).get('user', {}).get('name', '')
        white_member = _resolve_member_for_player(white_name, lichess_username, member)
        black_member = _resolve_member_for_player(black_name, lichess_username, member)

        winner = raw.get('winner', '')
        if winner == 'white':
            result = '1-0'
        elif winner == 'black':
            result = '0-1'
        else:
            result = '1/2-1/2'

        created_ms = raw.get('createdAt', 0)
        played_at = datetime.fromtimestamp(created_ms / 1000, tz=dt_tz.utc)

        pgn = raw.get('pgn', '')
        if not pgn:
            try:
                pgn = client.fetch_game_pgn(lichess_id)
            except LichessAPIError:
                pgn = ''

        game = Game.objects.create(
            lichess_game_id=lichess_id,
            player_white=white_member or member,
            player_black=black_member or member,
            pgn=pgn,
            time_control=raw.get('speed', ''),
            result=result,
            played_at=played_at,
        )
        if pgn:
            analyse_game_task.delay(game.pk)


@shared_task
def periodic_fetch_linked_lichess_games():
    """
    Enqueue imports for members who linked a username (intended for Celery Beat hourly schedule).
    """
    from django.db.models import Q

    from club.member_utils import sync_member_with_user
    from club.models import UserProfile

    qs = UserProfile.objects.filter(
        Q(lichess_username__isnull=False) & ~Q(lichess_username=''),
    ).select_related('user')

    count = 0
    for profile in qs.iterator():
        if not profile.user_id:
            continue
        member = sync_member_with_user(profile.user, profile.lichess_username)
        fetch_lichess_games_task.delay(profile.lichess_username, member.pk, profile.lichess_api_key or '')
        count += 1
    return count


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_insights_task(self, member_id):
    try:
        member = Member.objects.get(pk=member_id)
    except Member.DoesNotExist:
        logger.error('generate_insights_task: Member %s not found.', member_id)
        return

    try:
        aggregate_insights(member)
    except Exception as exc:
        raise self.retry(exc=exc)
