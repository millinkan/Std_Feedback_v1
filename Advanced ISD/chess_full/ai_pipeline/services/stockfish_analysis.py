import io
from pathlib import Path

import chess
import chess.pgn
from django.conf import settings
from stockfish import Stockfish

THRESHOLDS = {
    'best': 0,
    'excellent': 10,
    'good': 25,
    'inaccuracy': 50,
    'mistake': 100,
    'blunder': 200,
}
EVAL_CAP = 1000


def classify_move(centipawn_loss):
    if centipawn_loss <= THRESHOLDS['best']:
        return 'best'
    if centipawn_loss <= THRESHOLDS['excellent']:
        return 'excellent'
    if centipawn_loss <= THRESHOLDS['good']:
        return 'good'
    if centipawn_loss <= THRESHOLDS['inaccuracy']:
        return 'inaccuracy'
    if centipawn_loss <= THRESHOLDS['mistake']:
        return 'mistake'
    return 'blunder'


def get_stockfish_engine():
    engine_path = Path(settings.STOCKFISH_PATH)
    if not engine_path.exists():
        raise FileNotFoundError(f'Stockfish binary not found: {engine_path}')
    return Stockfish(
        path=str(engine_path),
        depth=settings.STOCKFISH_DEPTH,
        parameters={'Threads': settings.STOCKFISH_THREADS, 'Hash': settings.STOCKFISH_HASH_MB},
    )


def _get_eval(engine, board):
    engine.set_fen_position(board.fen())
    evaluation = engine.get_evaluation()
    if evaluation['type'] == 'mate':
        return EVAL_CAP if evaluation['value'] > 0 else -EVAL_CAP
    raw = evaluation['value']
    return max(-EVAL_CAP, min(EVAL_CAP, raw))


def analyse_game(pgn_string):
    game = chess.pgn.read_game(io.StringIO(pgn_string))
    if game is None:
        raise ValueError('Could not parse PGN string - no game found.')

    engine = get_stockfish_engine()
    board = game.board()
    move_results, white_cpls, black_cpls = [], [], []
    counters = {
        'white_blunders': 0,
        'black_blunders': 0,
        'white_mistakes': 0,
        'black_mistakes': 0,
        'white_inaccuracies': 0,
        'black_inaccuracies': 0,
    }

    for move_number, node in enumerate(game.mainline(), start=1):
        move = node.move
        is_white = board.turn == chess.WHITE
        eval_before = _get_eval(engine, board)
        engine.set_fen_position(board.fen())
        best_move_uci = engine.get_best_move()
        best_move_san = ''
        if best_move_uci:
            try:
                best_move_san = board.san(chess.Move.from_uci(best_move_uci))
            except Exception:
                best_move_san = best_move_uci

        move_san = board.san(move)
        board.push(move)
        eval_after = _get_eval(engine, board)
        cpl = max(0.0, eval_before - eval_after) if is_white else max(0.0, eval_after - eval_before)
        classification = classify_move(cpl)
        side = 'white' if is_white else 'black'
        if classification == 'blunder':
            counters[f'{side}_blunders'] += 1
        elif classification == 'mistake':
            counters[f'{side}_mistakes'] += 1
        elif classification == 'inaccuracy':
            counters[f'{side}_inaccuracies'] += 1
        (white_cpls if is_white else black_cpls).append(cpl)
        move_results.append(
            {
                'move_number': (move_number + 1) // 2,
                'is_white': is_white,
                'move_san': move_san,
                'best_move_san': best_move_san,
                'eval_before': eval_before,
                'eval_after': eval_after,
                'centipawn_loss': round(cpl, 2),
                'classification': classification,
            }
        )

    white_avg_cpl = round(sum(white_cpls) / len(white_cpls), 2) if white_cpls else 0.0
    black_avg_cpl = round(sum(black_cpls) / len(black_cpls), 2) if black_cpls else 0.0
    return {
        'moves': move_results,
        'white_avg_cpl': white_avg_cpl,
        'black_avg_cpl': black_avg_cpl,
        **counters,
    }
