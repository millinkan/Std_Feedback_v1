"""FIDE-style Elo expectation and rating update (Club OTB ratings)."""


def expected_score(rating_a: float, rating_b: float) -> float:
    """Expected score for player A versus player B (0–1)."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def k_factor(games_played: int, current_rating: float) -> int:
    """Adaptive K-factor: new players K=40, elite (>=2400) K=10, else K=20."""
    if games_played < 30:
        return 40
    if current_rating >= 2400:
        return 10
    return 20


def new_ratings(
    white_rating: float,
    black_rating: float,
    result: str,
    white_games_played: int,
    black_games_played: int,
) -> tuple[float, float]:
    """
    Compute post-match ratings for white and black.
    result: '1-0', '0-1', or '1/2-1/2'
    games_played counts completed club matches *before* this game (for K).
    """
    if result == '1-0':
        sw, sb = 1.0, 0.0
    elif result == '0-1':
        sw, sb = 0.0, 1.0
    else:
        sw, sb = 0.5, 0.5

    ew = expected_score(white_rating, black_rating)
    eb = 1.0 - ew

    kw = k_factor(white_games_played, white_rating)
    kb = k_factor(black_games_played, black_rating)

    new_white = white_rating + kw * (sw - ew)
    new_black = black_rating + kb * (sb - eb)
    return new_white, new_black
