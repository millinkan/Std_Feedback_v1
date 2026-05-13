import json

import requests
from django.conf import settings


class LichessAPIError(Exception):
    pass


class LichessClient:
    def __init__(self, api_token=''):
        self.base_url = settings.LICHESS_API_BASE_URL
        self.session = requests.Session()
        token = api_token or settings.LICHESS_API_TOKEN
        if token:
            self.session.headers.update({'Authorization': f'Bearer {token}'})

    def _get(self, path, params=None, accept='application/json'):
        self.session.headers['Accept'] = accept
        url = f'{self.base_url}{path}'
        response = self.session.get(url, params=params, timeout=30)
        if not response.ok:
            raise LichessAPIError(f'GET {url} returned {response.status_code}: {response.text[:200]}')
        return response

    def _post(self, path, data=None):
        url = f'{self.base_url}{path}'
        response = self.session.post(url, data=data, timeout=30)
        if not response.ok:
            raise LichessAPIError(f'POST {url} returned {response.status_code}: {response.text[:200]}')
        return response.json()

    def fetch_recent_games(self, lichess_username, max_games=20):
        params = {
            'max': max_games,
            'pgnInJson': 'true',
            'moves': 'true',
            'clocks': 'false',
            'evals': 'false',
            'opening': 'false',
        }
        response = self._get(f'/games/user/{lichess_username}', params=params, accept='application/x-ndjson')
        games = []
        for line in response.text.strip().splitlines():
            if line.strip():
                games.append(json.loads(line))
        return games

    def fetch_game_pgn(self, game_id):
        response = self._get(
            f'/game/export/{game_id}',
            params={'moves': 'true', 'clocks': 'false', 'evals': 'false'},
            accept='application/x-chess-pgn',
        )
        pgn = response.text.strip()
        if not pgn:
            raise LichessAPIError(f'Empty PGN returned for game ID "{game_id}"')
        return pgn

    def create_challenge(self, lichess_username, time_limit=600, increment=5):
        data = {
            'clock.limit': time_limit,
            'clock.increment': increment,
            'color': 'random',
            'variant': 'standard',
        }
        result = self._post(f'/challenge/{lichess_username}', data=data)
        challenge_url = result.get('challenge', {}).get('url')
        if not challenge_url:
            raise LichessAPIError(f'Could not extract challenge URL from response: {result}')
        return challenge_url
