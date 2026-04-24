import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chess_club.settings')

app = Celery('chess_club')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
