from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from rest_framework.views import APIView
from django.conf import settings
from django.http import HttpResponse
from django.db.models import Count
from django.utils import timezone

from .utils import create_new_advertisement_threading, get_updates
from .models import Advertisement
from .forms import ImageUploadForm

from multiprocessing.dummy import Pool as ThreadPool
from datetime import datetime
from PIL import Image
from rembg.bg import remove
import base64
import io
import requests
import logging
import re


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
    link = 'http://crwl.ru/api/rest/latest/get_ads/'
    payload = {
        'api_key' : settings.API_KEY,
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


class ImageBackgroundRemoveView(FormView):
    # Обработчик вставки машины на задний фон

    template_name = 'image_background_remove.html'
    form_class = ImageUploadForm
    success_url = 'image-background-remove'

    def form_valid(self, form):
        img_list = []

        raw_bg = self.request.FILES.get('background').read()

        backgroud_image = Image.open(io.BytesIO(raw_bg)).convert("RGBA")

        for i in self.request.FILES.getlist('images'):
            content_type = i.content_type
            result = remove(i.read())

            trimmed_car = Image.open(io.BytesIO(result))

            trimmed_car = trimmed_car.crop(trimmed_car.getbbox())

            width = (backgroud_image.width // 2) - (trimmed_car.width // 2)
            height = (backgroud_image.height * 3//4) - (trimmed_car.height // 2)

            backgroud_image.paste(
                trimmed_car,
                (width, height),
                trimmed_car
            )

            output_buffer = io.BytesIO()
            backgroud_image.save(output_buffer, format='PNG')

            encoded_img  = base64.b64encode(
                output_buffer.getvalue()
            )

            decoded_img = encoded_img.decode('utf-8')

            img_data = f"data:{content_type};base64,{decoded_img}"
            img_list.append(img_data)

        context = self.get_context_data()
        context['images'] = img_list
        context['form'] = form
        return self.render_to_response(context)


class GraphsView(TemplateView):
    # Обработчик страницы с графиками

    template_name = 'graphs.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(GraphsView, self).get_context_data()

        context['title'] = 'Графики'

        sites_count = Advertisement.objects.filter(original=True).values('site').annotate(Count('site')).order_by('-site__count')
        # sites_count = Advertisement.objects.filter(~Q).values('site').annotate(Count('site')).order_by('-site__count')

        dup_sites_count = Advertisement.objects.filter(original=False).values('site').annotate(Count('site')).order_by('-site__count')

        context['sites_count']  = sites_count
        context['total_sites']  = sum([i['site__count'] for i in sites_count])

        context['dup_sites_count']  = dup_sites_count
        context['total_dup_sites']  = sum([i['site__count'] for i in dup_sites_count])
        context['total_sum']  = context['total_sites'] + context['total_dup_sites']

        return context


class DatabaseList(ListView):
    # Обработчик главной страницы вывода объявлений из базы данных

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
        sort_by = self.request.GET.get('sort_by')
        site = self.request.GET.get('site')
        adv_id = self.request.GET.get('adv_id')

        raw_url = self.request.GET.get('url')
        url_reg = re.compile(r"https?://(www\.)?")
        url = url_reg.sub('', raw_url).strip().strip('/') if raw_url else None


        # Надо переделать в будущем, так как это костыль. Если не добавляется оригинальность к значению, то появляются баги.
        advertisements = Advertisement.objects.all()

        if brand and len(brand) != 0:
            advertisements = advertisements.filter(
                brand__contains=brand.strip(),
            )
        if model and len(model) != 0:
            advertisements = advertisements.filter(
                model__contains=model.strip(),
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
                original=False
            )
        if url:
            advertisements = advertisements.filter(
                advertisement_url__contains=url
            )
        if year:
            advertisements = advertisements.filter(
                year=year.strip()
            )
        if site:
            advertisements = advertisements.filter(
                site=site.strip()
            )
        if adv_id:
            advertisements = advertisements.filter(
                advertisement_id=adv_id.strip()
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
        sites  = [i[0] for i in
                  Advertisement.objects.order_by('site').values_list('site').distinct()]

        models = chunks(models, 4)
        brands = chunks(brands, 4)
        sites  = chunks(sites, 4)

        context['models'] = models
        context['brands'] = brands
        context['sites']  = sites

        context['title'] = 'Объявления'

        return context


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


class AdvertisementPost(DetailView):
    # Обработчик страницы вывода информации об объявлении

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
    # advs = Advertisement.objects.all().delete()
    link = 'http://crwl.ru/api/rest/latest/get_ads/'
    payload = {
        'api_key' : settings.API_KEY,
        'region'  : '3504',
        'last'    : str(24),
        # 'last'    : 1
    }
    result = requests.get(link, params=payload)
    json_result = result.json()

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


def test_4(request):
    link = 'https://proxylist.geonode.com/api/proxy-list'
    payload = {
        'limit': '50',
        'page': '1',
        'sort_by': 'lastChecked',
        'sort_type': 'desc',
        'protocols': 'https,https',
        # 'country': 'RU'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
    }
    result = requests.get(link, params=payload, headers=headers)
    proxies = result.json()

    link = 'https://www.showmemyip.com/'

    for proxy_obj in proxies['data']:

        proxy = dict()

        for protocol in proxy_obj['protocols']:
            proxy[protocol] = f'{protocol}://{proxy_obj["ip"]}:{proxy_obj["port"]}'

        print(proxy)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
        }

        try:
            result = requests.get(link, headers=headers, proxies=proxy, timeout=3)
            print(result)
        except requests.exceptions.ProxyError as ex:
            print(ex)
        except requests.exceptions.ConnectTimeout as ex:
            print(ex)
        except ValueError as ex:
            print(ex)
    return HttpResponse('???')


def test_5(request):
    link = 'https://www.showmemyip.com/'

    proxy = {'https': 'https://5.188.114.54:8081'}

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
    }

    result = requests.get(link, headers=headers, proxies=proxy)
    return result.text


def test_3(request, adv_id):
    link = 'http://crwl.ru/api/rest/latest/get_ads/'
    payload = {
        'api_key': settings.API_KEY,
        'region': '3504',
        'last': str(1),
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

        if len(post_data.get('adv_run')) != 0:
            post_adv_data['run'] = int(post_data.get('adv_run'))
        if len(post_data.get('adv_price')) != 0:
            post_adv_data['price'] = int(post_data.get('adv_price'))

        # Проверяем на наличие данного объявления

        pool = ThreadPool()

        result = create_new_advertisement_threading(post_adv_data, pool, logger)

        pool.close()
        pool.join()

        return JsonResponse({'unique': result})


# def test_6(request):
#     advs_to_del = Advertisement.objects.filter(
#         original=False,
#         created_at__gte=timezone.make_aware(datetime.fromisoformat('2021-07-25 00:00:00'))
#     )
#     for i in advs_to_del:
#         logger.debug(f'Deleting {i} {i.created_at}')
#         i.delete()
#
#     return HttpResponse()






