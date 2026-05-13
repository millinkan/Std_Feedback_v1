import os
from datetime import timedelta

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_club.settings')

app = Celery('chess_club')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

try:
    _beat_seconds = int(os.environ.get('LICHESS_BEAT_SCHEDULE_SECONDS', '3600'))
except ValueError:
    _beat_seconds = 3600
if _beat_seconds > 0 and os.environ.get('DISABLE_LICHESS_BEAT', '').lower() not in ('1', 'true', 'yes'):
    _beat = getattr(app.conf, 'beat_schedule', None) or {}
    _beat['lichess-fetch-linked-profiles'] = {
        'task': 'ai_pipeline.tasks.periodic_fetch_linked_lichess_games',
        'schedule': timedelta(seconds=_beat_seconds),
    }
    app.conf.beat_schedule = _beat
