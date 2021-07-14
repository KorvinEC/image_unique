import os

from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'work_site.settings')

app = Celery('work_site')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings')

# Load task modules from all registered Django apps.
app.autodiscover_tasks(settings.INSTALLED_APPS)


app.conf.beat_schedule = {
    'listen_crwl' : {
        'task' : 'search_cars.tasks.listen_crwl',
        'schedule' : 10,
    }
}