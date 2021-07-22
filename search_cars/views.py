from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView

import requests
from .models import Advertisement, AdvertisementPhotos
from django.utils import timezone
import logging
import numpy as np

from multiprocessing.dummy import Pool as ThreadPool
from datetime import datetime
from django.core.paginator import Paginator,  EmptyPage, PageNotAnInteger
from .utils import create_new_advertisement_threading, get_updates
from django.shortcuts import redirect
from .forms import SearchForm
from django.http import QueryDict
from tqdm import tqdm


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(message)s',
    '%d/%b/%Y %H:%M:%S'
)

ch.setFormatter(formatter)
logger.addHandler(ch)


from django.db.models import Avg, Count


def index(request):
    # Обработчик главной страницы
    # :param request:
    #     request - запрос к странице
    # :return:
    #     Возвращается главная страница

    link = 'http://crwl.ru/api/rest/latest/get_ads/'
    payload = {
        'api_key' : '710090c4b15d091696d5369ee18cd3f5',
        'region'  : '3504',
        'last'    : '1'
    }

    result = requests.get(link, params=payload, timeout=10)

    result_json = result.json()[::-1]
    ret = []

    for item in result_json:
        if item['company'] == '0' and item['run'] != '0':
            item['photo'] = item['photo'].split(',')
            ret.append(item)
    return render(request, 'index.html', {'cars': ret})


class DatabaseList(ListView):
    model = Advertisement
    template_name = 'database.html'
    context_object_name = 'cars'
    paginate_by = 12

    def get_queryset(self):
        brand = self.request.GET.get('brand')
        model = self.request.GET.get('model')
        year = self.request.GET.get('year')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        duplicates = self.request.GET.get('duplicates')
        url = self.request.GET.get('url')
        sort_by = self.request.GET.get('sort_by')

        advertisements = Advertisement.objects.filter(original=True)

        if brand and len(brand) != 0:
            advertisements = advertisements.filter(
                brand__contains=brand,
            )
        if model and len(model) != 0:
            advertisements = advertisements.filter(
                model__contains=model,
            )
        if start_date:
            start_date = timezone.make_aware(datetime.strptime(start_date, '%d/%m/%Y'))
            advertisements = advertisements.filter(
                created_at__gte=start_date
            )
        if end_date:
            end_date = timezone.make_aware(datetime.strptime(end_date, '%d/%m/%Y'))
            advertisements = advertisements.filter(
                created_at__lte=end_date
            )
        if duplicates:
            advertisements = advertisements.filter(
                similar_advertisement__isnull=False
            )
        if url:
            advertisements = advertisements.filter(
                advertisement_url=url
            )
        if year:
            advertisements = advertisements.filter(
                year=year
            )
        if sort_by == 'created':
            advertisements = advertisements.order_by('-created_at')
        else:
            advertisements = advertisements.order_by('-added_at')

        return advertisements

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(DatabaseList, self).get_context_data()

        models = [i[0] for i in
                  Advertisement.objects.order_by('model').values_list('model').distinct().exclude(model='')]
        brands = [i[0] for i in
                  Advertisement.objects.order_by('brand').values_list('brand').distinct().exclude(brand='')]

        models = zip(*[iter(models)] * 4)
        brands = zip(*[iter(brands)] * 4)

        context['models'] = models
        context['brands'] = brands

        context['title'] = 'Объявления'

        return context


class AdvertisementPost(DetailView):
    model = Advertisement
    template_name = 'advertisement.html'

    def get_context_data(self, **kwargs):
        context = super(AdvertisementPost, self).get_context_data()

        context['title'] = ' '.join([
            context['object'].brand,
            context['object'].model,
            context['object'].year
        ])

        return context


def test(request):
    link = 'http://crwl.ru/api/rest/latest/get_ads/'
    payload = {
        'api_key' : '710090c4b15d091696d5369ee18cd3f5',
        'region'  : '3504',
        'last'    : str(1),
        # 'last'    : 1
    }
    result = requests.get(link, params=payload)
    json_result = result.json()

    print(json_result)

    pool = ThreadPool()

    for item in json_result:
        post_adv_data = {
            'id':       item['Id'],
            'url':      item['url'],
            'brand':    item['marka'],
            'model':    item['model'],
            'year':     item['year'],
            'text':     item['info'],
            'site':     item['source'],
            'added_at': timezone.make_aware(datetime.fromisoformat(item['dt'])),
            'links':    item['photo'].split(','),
            'color':    item['color'],
            'latitude':    item['latitude'],
            'longitude':    item['longitude'],
        }

        create_new_advertisement_threading(post_adv_data, pool, logger)

    pool.close()
    pool.join()

    return JsonResponse({'result': True})


import asyncio


def test_2(request):
    # photos = AdvertisementPhotos.objects.filter(photo=1)
    # for photo in tqdm(photos):
    #     photo.photo = None
    #     photo.avg_hash = None
    #     photo.save()
    res = get_updates()
    pool = ThreadPool()

    result = []

    for item in res:
        if item:
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
                'color': item['color'],
                'latitude': item['latitude'],
                'longitude': item['longitude'],
            }
            res = create_new_advertisement_threading(
                post_adv_data=post_adv_data,
                pool=pool,
                logger=logger)
            result.append({'unique': res})

    pool.close()
    pool.join()

    return JsonResponse({'result': result})


def test_3(request, adv_id):
    link = 'http://crwl.ru/api/rest/latest/get_ads/'
    payload = {
        'api_key': '710090c4b15d091696d5369ee18cd3f5',
        'region': '3504',
        'last': str(1),
        # 'last'    : 1
    }
    result = requests.get(link, params=payload)
    json_result = result.json()

    pool = ThreadPool()

    item = json_result[adv_id]
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
        'color': item['color'],
        'latitude': item['latitude'],
        'longitude': item['longitude'],
    }

    create_new_advertisement_threading(post_adv_data, pool, logger)

    pool.close()
    pool.join()

    return JsonResponse({'result': True})


def test_request(request):
    form_data = {
        'id'       : (None, 104171436),
        'brand'    : (None, 'Toyota'),
        'model'    : (None, 'Camry'),
        'year'     : (None, '2019'),
        'adv_text' : (None, 'Тойота  Камри ,2019г сентябрь,на гарантии до 2022 г август месяц,пробег 28т.км,состояние новой машины,без ДТП вся в родной краске 100%,обслуживание у ОФ,куплена за наличный расчёт, физ лицо, комплектация предмаксимальная,машина маркирована,сигнализация с автозапуском, противоугоная система, GPS маяк,резина новая ,все комплекты брелков,зимняя резина,.'),
        'adv_link' : (None, 'http://www.avito.ru/chelyabinsk/avtomobili/toyota_camry_2019_2164110309'),
        'photos'   : (None, 'http://59.img.avito.st/640x480/11163333959.jpg,http://76.img.avito.st/640x480/11257975576.jpg,https://i.imgur.com/ibhsQMo.jpeg'),
        'site'     : (None, 'avitoru'),
        'date'     : (None, '2021-07-20 11:12:57'),
    }

    result = requests.post('http://127.0.0.1:8000/check_unique', files=form_data)
    # print(result.text)
    return JsonResponse(result.json())


class CheckUnique(APIView):
    def post(self, request):
        # Post запрос к API разработки, для выявления уникальности объявления.
        # Полученное объявление также сохраняется в базе данных
        # :param self, request:
        #     request - запрос к странице
        # :return:
        #     Возвращается JSON файл с содержанием:
        #         True - запись уникальна;
        #         False - запись уже существует в базе данных.

        post_data = request.POST

        post_adv_data = {
            'id': post_data.get('id'),
            'url': post_data.get('adv_link'),
            'brand': post_data.get('brand'),
            'model': post_data.get('model'),
            'year': post_data.get('year'),
            'text': post_data.get('adv_text'),
            'site': post_data.get('site'),
            'added_at': timezone.make_aware(datetime.fromisoformat(post_data.get('date'))),
            'links': post_data.get('photos').split(','),
        }

        # Проверяем на наличие данного объявления

        pool = ThreadPool()

        result = create_new_advertisement_threading(post_adv_data, pool, logger)

        pool.close()
        pool.join()

        return JsonResponse({'unique': result})







