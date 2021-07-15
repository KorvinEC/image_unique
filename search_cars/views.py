from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
import requests
from .models import Advertisement
from django.utils import timezone
import logging
import numpy as np

from multiprocessing.dummy import Pool as ThreadPool
from datetime import datetime
from django.core.paginator import Paginator,  EmptyPage, PageNotAnInteger
from .functions import create_new_advertisement_threading, get_updates
from django.shortcuts import redirect
from .forms import SearchForm
from django.http import QueryDict

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


def index(request):
    # Обработчик главной страницы
    # :param request:
    #     request - запрос к странице
    # :return:
    #     Возвращается главная страница

    link = 'http://crwl.ru/api/rest/latest/get_ads/'
    payload = {
        'api_key' : '__api_key__',
        'region'  : '3504',
        'last'    : '1'
    }
    try:
        result = requests.get(link, params=payload, timeout=10)
    except requests.exceptions.ReadTimeout as ex:
        logger.warning('Read timeout error: {}'.format(ex))
        return render(request, 'index.html')
    except requests.exceptions.ConnectTimeout as ex:
        logger.warning('Connection timeout error: {}'.format(ex))
        return render(request, 'index.html')
    except requests.exceptions.ConnectionError as ex:
        logger.warning('Connection error: {}'.format(ex))
        return render(request, 'index.html')
    if result.status_code != 200:
        logger.warning('Response: {}'.format(result.status_code))
        return render(request, 'index.html')

    result_json = result.json()[::-1]
    for i in range(len(result_json)):
        splitted = result_json[i]['photo'].split(',')
        result_json[i]['photo'] = splitted if len(splitted[0]) != 0 else None
        result_json[i]['New_car'] = True if i % 8 else False

    return render(request, 'index.html', {'cars': result_json})


def database(request):
    # Обработчик базы данных
    # :param request:
    #     request - запрос к странице
    # :return:
    #     Возвращается страница базы данных

    brand = request.GET.get('brand')
    model = request.GET.get('model')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    duplicates = request.GET.get('duplicates')

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

    advertisements = advertisements.order_by('-added_at')

    if advertisements.order_by('-added_at'):
        paginator = Paginator(advertisements, 12)

        page = request.GET.get('page')

        try:
            cars = paginator.page(page)
        except PageNotAnInteger:
            cars = paginator.page(1)
        except EmptyPage:
            cars = paginator.page(paginator.num_pages)

        return render(request, 'database.html', {'cars': cars})
    else:
        return render(request, 'database.html', )


from tqdm import tqdm


def test(request):
    link = 'http://crwl.ru/api/rest/latest/get_ads/'
    payload = {
        'api_key' : '__api_key__',
        'region'  : '3504',
        'last'    : str(8)
        # 'last'    : 1
    }
    result = requests.get(link, params=payload)

    json_result = result.json()

    pool = ThreadPool()

    for item in tqdm(json_result):
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
        }
        create_new_advertisement_threading(post_adv_data, pool, logger)

    pool.close()
    pool.join()

    return JsonResponse({'result': True})



def test_2(request):
    res = get_updates()
    pool = ThreadPool()

    result = []

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
            'color': item['color'],
        }
        res = create_new_advertisement_threading(post_adv_data, pool, logger)
        result.append({'unique': res})

    pool.close()
    pool.join()

    return JsonResponse({'result': result})


def test_request():
    form_data = {
        'id'       : (None, 104171436 + 24341),
        'brand'    : (None, 'Toyota'),
        'model'    : (None, 'Camry'),
        'year'     : (None, '2019'),
        'text'     : (None, 'Тойота  Камри ,2019г сентябрь,на гарантии до 2022 г август месяц,пробег 28т.км,состояние новой машины,без ДТП вся в родной краске 100%,обслуживание у ОФ,куплена за наличный расчёт, физ лицо, комплектация предмаксимальная,машина маркирована,сигнализация с автозапуском, противоугоная система, GPS маяк,резина новая ,все комплекты брелков,зимняя резина,.'),
        'adv_link' : (None, 'http://www.avito.ru/chelyabinsk/avtomobili/toyota_camry_2019_2164110309'),
        'photos'   : (None, 'http://59.img.avito.st/640x480/11163333959.jpg,http://76.img.avito.st/640x480/11257975576.jpg,https://i.imgur.com/ibhsQMo.jpeg'),
        'site'     : (None, 'avitoru'),
        'color'     : (None, 'черный'),
        # 'added_at' : (None, timezone.now().timestamp()),
    }

    result = requests.post('http://127.0.0.1:8000/CheckUnique', files=form_data)
    return result.json()


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
        logger.debug('POST запрос содержит: {}'.format(post_data))

        post_adv_data = {
            'id': post_data.get('id'),
            'url': post_data.get('adv_link'),
            'brand': post_data.get('brand'),
            'model': post_data.get('model'),
            'year': post_data.get('year'),
            'text': post_data.get('text'),
            'site': post_data.get('site'),
            'added_at': post_data.get('added_at'),
            'links': post_data.get('photos').split(','),
            'color': post_data.get('color'),
        }

        # Проверяем на наличие данного объявления

        if Advertisement.objects.filter(advertisement_id=post_adv_data['id']).exists():
            adv = Advertisement.objects.get(advertisement_id=post_adv_data['id'])
            logger.debug('Объявление {} уже существует'.format(post_adv_data['id']))
            return JsonResponse({'unique': adv.original})
        else:
            result = create_new_advertisement_threading(post_adv_data)
            return JsonResponse({'unique': result})








