# Create your tasks here

from celery import shared_task
from .functions import get_updates, create_new_advertisement_threading
from multiprocessing.dummy import Pool as ThreadPool
from django.utils import timezone
from datetime import datetime


@shared_task
def listen_crwl():
    res = get_updates()
    pool = ThreadPool()

    results = []

    for item in res:
        post_adv_data = {
            'id': item['Id'],
            'url': item['url'],
            'brand': item['marka'],
            'model': item['model'],
            'year': item['year'],
            'text': item['info'],
            'site': item['source'],
            'added_at': timezone.make_aware(datetime.fromisoformat(item['dt'])),
            'links': item['photo'].split(','),
        }
        res = create_new_advertisement_threading(post_adv_data, pool)
        results.append({'unique': res})

    pool.close()
    pool.join()

    if not results:
        return []
    else:
        return results
