from itertools import product, islice
from .models import Advertisement, AdvertisementPhotos
import mysql.connector
import PIL
import io
import cv2
import requests
import numpy as np


def get_updates():
    link = 'http://crwl.ru/api/rest/latest/get_new_ads/'
    payload = {
        'api_key' : '__api_key__',
        'region'  : '3504',
    }
    result = requests.get(link, params=payload)

    if result.content:
        return result.json()
    else:
        return {}



def create_new_advertisement_threading(post_adv_data : dict, pool, logger=None):

    # Создаем объект объявления

    if Advertisement.objects.filter(advertisement_id=post_adv_data['id']).exists():
        adv = Advertisement.objects.get(advertisement_id=post_adv_data['id'])
        logger.debug(
            'Объявление {} {} {} уже существует'.format(
                post_adv_data['id'],
                post_adv_data['brand'],
                post_adv_data['model'],
            )
        )
        return adv.original

    new_adv = Advertisement()

    new_adv.advertisement_id   = post_adv_data['id']
    new_adv.advertisement_url  = post_adv_data['url']
    new_adv.brand              = post_adv_data['brand']
    new_adv.model              = post_adv_data['model']
    new_adv.year               = post_adv_data['year']
    new_adv.info               = post_adv_data['text']
    new_adv.site               = post_adv_data['site']
    new_adv.added_at           = post_adv_data['added_at']

    # Находим дупликаты полученного объявления

    dup_advs = Advertisement.objects.filter(
        year=post_adv_data['year']  ,
        brand=post_adv_data['brand']   ,
        model=post_adv_data['model'] ,
        added_at__lt=post_adv_data['added_at'],
        original=True
    )

    print(dup_advs)

    # Загрузка изображений из POST запроса с созданием класса AdvertisementPhotos

    post_images = create_adv_photos(post_adv_data['links'])

    # Проверяем объявления

    if not dup_advs:
        # Если не найдено подходящих объявлений, то возвращается значение unique : True

        if logger:
            logger.debug(
                'Нет подходящих объявлений для {} {}'.format(
                    post_adv_data['brand'],
                    post_adv_data['model'],
                )
            )

        new_adv.original = True
        new_adv.save()
        for post_image in post_images:
            post_image.adv_id = new_adv
            post_image.save()
        new_adv.photos.add(*post_images)
        return True
    else:
        # Проверка найденных дупликатов

        if logger:
            logger.debug(
                'Найдено {1} {2} объявлений: {0}'.format(
                    len(dup_advs),
                    post_adv_data['brand'],
                    post_adv_data['model'],
                )
            )

        # pool = ThreadPool()

        # Загрузка изображения для дальнейшего сравнения

        downloaded_images = []

        for post_image in post_images:
            response = requests.get(post_image.photo_url, timeout=10)
            img2 = np.frombuffer(response.content, np.uint8)
            img2 = cv2.imdecode(img2, cv2.IMREAD_GRAYSCALE)
            downloaded_images.append(img2)

        # Проверка

        for dup_adv in dup_advs:
            if dup_adv.original:
                if logger:
                    logger.debug(
                        'Проверка объявления {1} {2} фотографий: {0} '.format(
                            len(dup_adv.photos.all()),
                            dup_adv.brand,
                            dup_adv.model,
                        )
                    )

                adv_downloaded_images = []
                for dup_image in dup_adv.photos.all():
                    response = requests.get(dup_image.photo_url, timeout=10)
                    img1 = np.frombuffer(response.content, np.uint8)
                    img1 = cv2.imdecode(img1, cv2.IMREAD_GRAYSCALE)

                    adv_downloaded_images.append(img1)

                all_args = product(adv_downloaded_images, downloaded_images)

                for args in chunks(all_args, 4):
                    results = pool.starmap(orb_match_template, args)

                    if True in results:
                        if logger:
                            logger.debug(
                                'Найдено совпадение для {} {} {}'.format(
                                    dup_adv.brand,
                                    dup_adv.model,
                                    dup_adv.color
                                )
                            )

                        new_adv.original = False
                        new_adv.save()
                        for post_image in post_images:
                            post_image.adv_id = new_adv
                            post_image.save()
                        new_adv.photos.add(*post_images)
                        dup_adv.similar_advertisement.add(new_adv)
                        dup_adv.save()

                        return False

        new_adv.original = True
        new_adv.save()
        for post_image in post_images:
            post_image.adv_id = new_adv
            post_image.save()
        new_adv.photos.add(*post_images)

        return True


def chunks(iterable, size):
    """Generate adjacent chunks of data"""
    it = iter(iterable)
    return iter(lambda: tuple(islice(it, size)), ())


def insert_into_photo_adv(request):

    config = {
        'host': 'localhost',
        'user': 'root',
        'passwd': '1234',
        'database': 'dump_base'
    }

    try:
        db = mysql.connector.connect(**config)

        with db.cursor() as cursor:

            all_advs = Advertisement.objects.all().order_by('-created_at')[3:]
            for adv in all_advs:
                cursor.execute(
                    'SELECT link, avg_hash, dhash, phash, whash FROM imageuniqe_photo \
                     WHERE adv_id_id in ( SELECT id FROM imageuniqe_advertisement \
                                          WHERE inner_adv_id = {} )'.format(adv.advertisement_id)
                )

                for row in cursor.fetchall():
                    print(row)
                    new_photo = AdvertisementPhotos()

                    new_photo.adv_id    = adv
                    new_photo.photo_url = row[0]
                    new_photo.avg_hash  = row[1]
                    new_photo.d_hash    = row[2]
                    new_photo.p_hash    = row[3]
                    new_photo.w_hash    = row[4]

                    new_photo.save()
                    adv.photos.add(new_photo)
                adv.save()

    except mysql.connector.Error as err:
        print('Error: ', err)
    else:
        cursor.close()
        db.close()


    # all_entries = Advertisement.objects.all().order_by('-created_at')[:3]
    # for item in all_entries:
    #     print(item.advertisement_id)

    # 'select * from imageuniqe_photo where adv_id_id in (select id from imageuniqe_advertisement where inner_adv_id = {})'.format(item.advertisement_id)


def insert_into_database(request):

    config = {
        'host': 'localhost',
        'user': 'root',
        'passwd': '1234',
        'database': 'dump_base'
    }

    try:
        db = mysql.connector.connect(**config)

        with db.cursor() as cursor:
            cursor.execute(
                'SELECT link, inner_adv_id, brand, model, year, text, created_at, added_at \
                 FROM imageuniqe_advertisement'
            )

            for row in cursor.fetchall():
                print(row)
                new_adv = Advertisement()

                new_adv.advertisement_url = row[0]
                new_adv.advertisement_id  = row[1]
                new_adv.brand             = row[2]
                new_adv.model             = row[3]
                new_adv.year              = row[4]
                new_adv.info              = row[5]
                new_adv.added_at          = timezone.make_aware(row[6])
                new_adv.created_at        = timezone.make_aware(row[7])

                new_adv.save()

    except mysql.connector.Error as err:
        print('Error: ', err)
    else:
        cursor.close()
        db.close()


def insert_sites_into_advs(request):
    'select name from imageuniqe_sites where id in (select site_id from imageuniqe_advertisement where inner_adv_id = 103952542)'

    config = {
        'host': 'localhost',
        'user': 'root',
        'passwd': '1234',
        'database': 'dump_base'
    }

    try:
        db = mysql.connector.connect(**config)

        with db.cursor() as cursor:

            all_advs = Advertisement.objects.all()
            for adv in all_advs:
                cursor.execute(
                    'select name from imageuniqe_sites \
                     where id in (select site_id from imageuniqe_advertisement \
                                  where inner_adv_id = {})'.format( adv.advertisement_id )
                )
                site = cursor.fetchone()[0]

                adv.site = site
                adv.save()

    except mysql.connector.Error as err:
        print('Error: ', err)
    else:
        cursor.close()
        db.close()


def create_new_advertisement(post_adv_data : dict, logger):

    # Создаем объект объявления

    if Advertisement.objects.filter(advertisement_id=post_adv_data['id']).exists():
        adv = Advertisement.objects.get(advertisement_id=post_adv_data['id'])
        logger.debug(
            'Объявление {} {} {} уже существует'.format(
                post_adv_data['id'],
                post_adv_data['brand'],
                post_adv_data['model']
            )
        )
        return adv.original

    new_adv = Advertisement()

    new_adv.advertisement_id   = post_adv_data['id']
    new_adv.advertisement_url  = post_adv_data['url']
    new_adv.brand              = post_adv_data['brand']
    new_adv.model              = post_adv_data['model']
    new_adv.year               = post_adv_data['year']
    new_adv.info               = post_adv_data['text']
    new_adv.site               = post_adv_data['site']
    new_adv.added_at           = post_adv_data['added_at']

    # Находим дупликаты полученного объявления

    dup_advs = Advertisement.objects.filter(
        year=post_adv_data['year']  ,
        brand=post_adv_data['brand']   ,
        model=post_adv_data['model'] ,
        created_at__lt=post_adv_data['added_at'],
        original=True
    )

    # Загрузка изображений из POST запроса с созданием класса AdvertisementPhotos

    post_images = create_adv_photos(post_adv_data['links'])

    # Проверяем объявления

    if not dup_advs:
        # Если не найдено подходящих объявлений, то возвращается значение unique : True

        logger.debug('Нет подходящих объявлений')

        new_adv.original = True
        new_adv.save()
        for post_image in post_images:
            post_image.adv_id = new_adv
            post_image.save()
        new_adv.photos.add(*post_images)
        return True
    else:
        # Проверка найденных дупликатов

        logger.debug(
            'Найдено подходящих объявлений: {} {} {}'.format(
                len(dup_advs),
                post_adv_data['brand'],
                post_adv_data['model'])
        )

        # pool = ThreadPool(4)

        # Загрузка изображения для дальнейшего сравнения

        downloaded_images = []

        for post_image in post_images:
            response = requests.get(post_image.photo_url, timeout=10)
            img2 = np.frombuffer(response.content, np.uint8)
            img2 = cv2.imdecode(img2, cv2.IMREAD_GRAYSCALE)
            downloaded_images.append(img2)

        # Проверка

        for dup_adv in dup_advs:
            if dup_adv.original:
                logger.debug('Проверка фотографий: {}'.format(len(dup_adv.photos.all())))

                for dup_image in dup_adv.photos.all():
                    response = requests.get(dup_image.photo_url, timeout=10)
                    img1 = np.frombuffer(response.content, np.uint8)
                    img1 = cv2.imdecode(img1, cv2.IMREAD_GRAYSCALE)

                    for downloaded_image in downloaded_images:

                        res, pers, matches = orb_match_template(img1, downloaded_image)

                        if res:

                            new_adv.original = False
                            new_adv.save()
                            for post_image in post_images:
                                post_image.adv_id = new_adv
                                post_image.save()
                            new_adv.photos.add(*post_images)
                            dup_adv.similar_advertisement.add(new_adv)
                            dup_adv.save()

                            return False

        new_adv.original = True
        new_adv.save()
        for post_image in post_images:
            post_image.adv_id = new_adv
            post_image.save()
        new_adv.photos.add(*post_images)

        return True


def orb_match_template(image_1, image_2):
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

    # logger.debug("Рeзультат сравнения: {:0.1f} {}".format(percentage_similarity, len(good_matches)))

    if percentage_similarity > 50.:
        return True
    return False

        # return True, percentage_similarity, len(good_matches)
    # return False, percentage_similarity, len(good_matches)


def create_adv_photos(links):
    photos = []

    for link in links:
        if link:
            new_photo = AdvertisementPhotos()

            new_photo.photo_url = link

            photos.append(new_photo)

    return photos


def get_image_in_IO(link):
    response = requests.get(link, timeout=10)
    return PIL.Image.open(io.BytesIO(response.content))
