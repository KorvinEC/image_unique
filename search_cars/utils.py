from itertools import product, islice
from .models import Advertisement, AdvertisementPhotos

import cv2
import os
import requests
import aiohttp
import asyncio
from asgiref.sync import sync_to_async
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import imagehash
from PIL import Image, ImageFile
from django.conf import settings


ImageFile.LOAD_TRUNCATED_IMAGES = True


if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def get_updates():
    link = 'http://crwl.ru/api/rest/latest/get_new_ads/'
    payload = {
        'api_key' : settings.API_KEY,
        'region'  : '3504',
    }
    result = requests.get(link, params=payload)

    if result.content:
        return result.json()
    else:
        return {}


async def async_download_and_save(session, url, adv):
    # prox = '222.186.153.71:28080'
    # proxy = {'http': f'https://{prox}'}
    # session.proxies  = proxy
    async with session.get(url) as response:
        photo = AdvertisementPhotos()

        photo.adv_id = adv
        photo.photo_url = url

        content = await response.read()
        headers = response.headers['Content-Type'].split('/')[1]

        file = ContentFile(content)
        photo.avg_hash = str(imagehash.average_hash(Image.open(file)))

        fs = FileSystemStorage()
        name = '_'.join(
            map(str, [photo.adv_id.id,
                      photo.avg_hash])) + '.' + headers
        file = fs.save(name=name, content=file)

        photo.photo = file

        return photo


async def async_download(links, adv):
    async with aiohttp.ClientSession() as session:

        tasks = []
        for link in links:
            tasks.append(asyncio.ensure_future(async_download_and_save(session, link, adv)))

        results = await asyncio.gather(*tasks)

        return results


def async_create_adv_photos(links, adv):
    photos = []

    links_len = len(links)

    if links_len == 1:
        if not links[0]:
            return photos

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    future = asyncio.ensure_future(async_download(links, adv))
    photos = loop.run_until_complete(future)

    for photo in photos:
        photo.save()

    return photos


def _get_adv_id(photo):
    return photo.adv_id.id


async def async_photos_download_and_save(session, photo):
    async with session.get(photo.photo_url) as response:
        content = await response.read()
        headers = response.headers['Content-Type'].split('/')[1]

        file = ContentFile(content)
        photo.avg_hash = str(imagehash.average_hash(Image.open(file)))

        fs = FileSystemStorage()
        adv_id = sync_to_async(_get_adv_id, thread_sensitive=True)(photo)
        name = '_'.join(
            map(str, [await adv_id,
                      photo.avg_hash])) + '.' + headers
        file = fs.save(name=name, content=file)

        photo.photo = file

        return photo


async def async_photos_download(photos):
    async with aiohttp.ClientSession() as session:

        tasks = []
        for photo in photos:
            tasks.append(asyncio.ensure_future(async_photos_download_and_save(session, photo)))

        results = await asyncio.gather(*tasks)

        return results


def async_save_photos(photos):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    future = asyncio.ensure_future(async_photos_download(photos))
    results = loop.run_until_complete(future)

    for photo in results:
        photo.save()


def orb_match_template(photo_1, photo_2):
    image_1 = cv2.imread(photo_1.photo.path)
    image_2 = cv2.imread(photo_2.photo.path)

    orb = cv2.ORB_create()

    keypoints1, descriptors1 = orb.detectAndCompute(image_1, None)
    keypoints2, descriptors2 = orb.detectAndCompute(image_2, None)

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(descriptors1, descriptors2, k=2)
    good_matches = []

    for m1, m2 in matches:
        if m1.distance < 0.89 * m2.distance:
            good_matches.append([m1])

    if len(keypoints1) >= len(keypoints2):
        number_keypoints = len(keypoints1)
    else:
        number_keypoints = len(keypoints2)

    percentage_similarity = float(len(good_matches)) / number_keypoints * 100

    if percentage_similarity > 50.:
        return True
    return False


def hash_orb_match_template(photo_1, photo_2):
    hash_1 = imagehash.hex_to_hash(photo_1.avg_hash)
    hash_2 = imagehash.hex_to_hash(photo_2.avg_hash)

    res_hash = hash_1 - hash_2

    if res_hash <= 5:
        return True
    elif 5 < res_hash <= 20:
        return orb_match_template(photo_1, photo_2)
    else:
        return False


def save_adv_and_photos(adv, photos, orig):
    adv.original = orig
    for post_image in photos:
        post_image.adv_id = adv
        post_image.save()
    adv.photos.add(*photos)
    adv.save()
    return orig


def create_new_advertisement_threading(post_adv_data: dict, pool, logger=None):

    # Создаем объект объявления

    if Advertisement.objects.filter(advertisement_id=post_adv_data['id']).exists():
        adv = Advertisement.objects.get(advertisement_id=post_adv_data['id'])
        logger.debug(
            f"{post_adv_data['id']}"
            f" {post_adv_data['brand']}"
            f" {post_adv_data['model']}"
            f" {post_adv_data['year']}"
            f" Объявление уже существует"
        )
        return adv.original

    new_adv = Advertisement()

    new_adv.advertisement_id  = post_adv_data['id']
    new_adv.advertisement_url = post_adv_data['url']
    new_adv.brand             = post_adv_data['brand']
    new_adv.model             = post_adv_data['model']
    new_adv.year              = post_adv_data['year']
    new_adv.info              = post_adv_data['text']
    new_adv.site              = post_adv_data['site']
    new_adv.added_at          = post_adv_data['added_at']

    if ('latitude' and 'longitude') in post_adv_data.keys():
        new_adv.latitude      = post_adv_data['latitude']
        new_adv.longitude     = post_adv_data['longitude']

    if ('run' and 'price') in post_adv_data.keys():
        new_adv.run      = post_adv_data['run']
        new_adv.price     = post_adv_data['price']

    new_adv.save()

    # Находим дупликаты полученного объявления

    dup_advs = Advertisement.objects.filter(
        year=post_adv_data['year'],
        brand__icontains=post_adv_data['brand'],
        model__icontains=post_adv_data['model'],
        original=True,
        added_at__lte=post_adv_data['added_at'],
    )

    print(dup_advs)

    # Загрузка изображений из POST запроса с созданием класса AdvertisementPhotos

    logger.debug(
        f"{new_adv} Загрузка фотографий {len(post_adv_data['links'])}"
    )

    post_images = async_create_adv_photos(post_adv_data['links'], new_adv)

    # Проверка дубликатов по пробегу и цене

    if ('run' and 'price') in post_adv_data.keys():
        dup_adv = dup_advs.exclude(
            run__isnull=True,
            price__isnull=True,
        )
        dup_adv = dup_advs.filter(
            run__gt=post_adv_data['run'] - 1000,
            run__lt=post_adv_data['run'] + 1000,
            price__gt=post_adv_data['price'] - 10000,
            price__lt=post_adv_data['price'] + 10000,
        )

        if dup_adv:
            dup_adv = dup_adv.first()

            logger.debug(
                f"{new_adv} Найден дубликат {dup_adv}"
            )

            res = save_adv_and_photos(new_adv, post_images, False)

            dup_adv.similar_advertisement.add(new_adv)
            dup_adv.save()

            return res

    # Проверяем объявления

    if not dup_advs:
        # Если не найдено подходящих объявлений, то возвращается значение unique : True

        if logger:
            logger.debug(
                f'{new_adv} Нет подходящих объявлений'
            )

        return save_adv_and_photos(new_adv, post_images, True)
    else:
        # Проверка найденных дупликатов

        if logger:
            logger.debug(
                f'{new_adv} Найдено объявлений: {len(dup_advs)}'
            )

        # Подготавливаем изображения

        for dup_adv in dup_advs:
            if dup_adv.original:
                if logger:
                    logger.debug(
                        f'{new_adv} Проверка объявления {dup_adv}'
                        f' с {len(dup_adv.photos.all())} фотографиями'
                    )

                dup_images = []

                links = []

                import os

                for photo in dup_adv.photos.all():
                    if not photo.photo:
                        links.append(photo)
                    else:
                        if not os.path.exists(photo.photo.path):
                            links.append(photo)

                    dup_images.append(
                        photo
                    )

                if links:
                    async_save_photos(links)

                all_args = product(post_images, dup_images)

                for args in chunks(all_args, 4):

                    results = pool.starmap(hash_orb_match_template, args)

                    if True in results:
                        if logger:
                            logger.debug(
                                f'{new_adv} Найдено совпадение {dup_adv}'
                            )

                        res = save_adv_and_photos(new_adv, post_images, False)

                        dup_adv.similar_advertisement.add(new_adv)
                        dup_adv.save()

                        return res

        if logger:
            logger.debug(
                f'{new_adv} Нет подходящих объявлений'
            )

        return save_adv_and_photos(new_adv, post_images, True)


def chunks(iterable, size):
    """Generate adjacent chunks of data"""
    it = iter(iterable)
    return iter(lambda: tuple(islice(it, size)), ())
