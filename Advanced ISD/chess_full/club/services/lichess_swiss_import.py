"""Import a Lichess Swiss tournament from API exports into club Swiss models."""

from __future__ import annotations

import json
from collections import defaultdict
from io import StringIO
from pathlib import Path
from typing import Any, Iterator

import chess.pgn
import requests
from django.conf import settings
from django.db import transaction

from club.models import Match, Member, SwissPairing, SwissParticipant, SwissRound, SwissTournament

ABORT_LIKE = frozenset({'aborted', 'noStart'})


def lichess_slug(swiss_id: str) -> str:
    base = f'lichess-{swiss_id}'
    return base[:220]


def load_info(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def iter_ndjson(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def game_round_number(game: dict[str, Any]) -> int:
    pgn_text = game.get('pgn') or ''
    if not pgn_text:
        return 1
    parsed = chess.pgn.read_game(StringIO(pgn_text))
    if parsed is None:
        return 1
    raw = (parsed.headers.get('Round') or '1').strip().strip('"').strip("'")
    try:
        return max(1, int(float(raw)))
    except ValueError:
        return 1


def game_result_string(game: dict[str, Any]) -> str | None:
    status = game.get('status')
    if status in ABORT_LIKE:
        return None
    winner = game.get('winner')
    if winner == 'white':
        return Match.RESULT_WHITE
    if winner == 'black':
        return Match.RESULT_BLACK
    return Match.RESULT_DRAW


def white_black_names(game: dict[str, Any]) -> tuple[str, str]:
    w = game['players']['white']['user']['name']
    b = game['players']['black']['user']['name']
    return w, b


def fetch_swiss_files(swiss_id: str, out_dir: Path, session: requests.Session | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    api_root = settings.LICHESS_API_BASE_URL.rstrip('/')
    sess = session or requests.Session()
    tok = (getattr(settings, 'LICHESS_API_TOKEN', None) or '').strip()
    if tok:
        sess.headers.setdefault('Authorization', f'Bearer {tok}')
    info_url = f'{api_root}/swiss/{swiss_id}'
    r = sess.get(info_url, headers={'Accept': 'application/json'}, timeout=90)
    r.raise_for_status()
    (out_dir / 'info.json').write_text(r.text, encoding='utf-8')
    games_url = f'{api_root}/swiss/{swiss_id}/games'
    params = {'pgnInJson': 'true', 'tags': 'true', 'moves': 'false', 'clocks': 'false', 'evals': 'false'}
    r2 = sess.get(games_url, headers={'Accept': 'application/x-ndjson'}, params=params, timeout=240)
    r2.raise_for_status()
    (out_dir / 'games.ndjson').write_text(r2.text, encoding='utf-8')


def resolve_member(username: str, *, create: bool) -> Member:
    un = username.strip()
    if not un:
        raise ValueError('empty username')
    q = Member.objects.filter(lichess_username__iexact=un).order_by('pk')
    existing = q.first()
    if existing:
        return existing
    q2 = Member.objects.filter(display_name__iexact=un).order_by('pk')
    fallback = q2.first()
    if fallback:
        if not fallback.lichess_username:
            fallback.lichess_username = un.lower()
            fallback.save(update_fields=['lichess_username'])
        return fallback
    if create:
        return Member.objects.create(display_name=un[:150], lichess_username=un.lower()[:100])
    raise LookupError(f'No club member matched Lichess user "{username}"')


def _lichess_meta_status(info: dict[str, Any]) -> str:
    raw = info.get('status')
    return str(raw) if raw is not None else 'finished'


@transaction.atomic
def import_swiss_from_dir(
    directory: Path,
    *,
    create_members: bool = False,
    counts_for_club_elo: bool = False,
    replace: bool = False,
) -> SwissTournament:
    directory = directory.resolve()
    info_path = directory / 'info.json'
    games_path = directory / 'games.ndjson'
    if not info_path.is_file():
        raise FileNotFoundError(f'Missing {info_path}')
    if not games_path.is_file():
        raise FileNotFoundError(f'Missing {games_path}')
    info = load_info(info_path)
    swiss_id = info.get('id')
    if not swiss_id:
        raise ValueError('info.json missing id')
    slug = lichess_slug(str(swiss_id))
    if replace:
        SwissTournament.objects.filter(slug=slug).delete()
    if SwissTournament.objects.filter(slug=slug).exists():
        raise ValueError(f'Tournament slug {slug!r} already exists (pass --replace to overwrite).')

    lichess_status = _lichess_meta_status(info)
    if lichess_status == 'created':
        t_status = SwissTournament.STATUS_DRAFT
    elif lichess_status == 'started':
        t_status = SwissTournament.STATUS_ACTIVE
    else:
        t_status = SwissTournament.STATUS_DONE

    nb_rounds = int(info.get('nbRounds') or 5)
    name = str(info.get('name') or f'Lichess Swiss {swiss_id}')[:200]

    tournament = SwissTournament.objects.create(
        name=name,
        slug=slug,
        status=t_status,
        rounds_target=min(max(nb_rounds, 1), 32767),
        rounds_played=0,
        venue='Lichess (online)',
        counts_for_club_elo=counts_for_club_elo,
    )

    norm_casing: dict[str, str] = {}
    by_round: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for g in iter_ndjson(games_path):
        res = game_result_string(g)
        if res is None:
            continue
        try:
            wn, bn = white_black_names(g)
        except (KeyError, TypeError):
            continue
        norm_casing[wn.lower()] = wn
        norm_casing[bn.lower()] = bn
        rd = game_round_number(g)
        by_round[rd].append({'_g': g, '_result': res, '_white': wn, '_black': bn})

    for display in sorted(norm_casing.values(), key=lambda s: s.lower()):
        m = resolve_member(display, create=create_members)
        SwissParticipant.objects.get_or_create(tournament=tournament, member=m)

    round_keys = sorted(by_round.keys())
    for rnum in round_keys:
        chunk = by_round[rnum]
        chunk.sort(key=lambda row: row['_g'].get('lastMoveAt') or row['_g'].get('createdAt') or 0)
        rnd = SwissRound.objects.create(tournament=tournament, number=rnum)
        for board_idx, row in enumerate(chunk, start=1):
            white_m = resolve_member(row['_white'], create=create_members)
            black_m = resolve_member(row['_black'], create=create_members)
            SwissPairing.objects.create(
                round=rnd,
                board=board_idx,
                white=white_m,
                black=black_m,
                result=row['_result'],
            )

    if round_keys:
        tournament.rounds_played = max(round_keys)

    tournament.save(update_fields=['rounds_played', 'updated_at'])
    return tournament
