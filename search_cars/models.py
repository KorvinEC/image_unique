from django.db import models
from django.utils import timezone
# from .models import *

# Create your models here.


class AdvertisementPhotos(models.Model):
    adv_id    = models.ForeignKey('Advertisement', on_delete=models.CASCADE, verbose_name="Объявление", db_index=True)
    photo_url = models.CharField(verbose_name="ссылка на изображение", max_length=200)


class Advertisement(models.Model):
    advertisement_id = models.IntegerField(verbose_name="Id объявления", unique=True)
    advertisement_url = models.CharField(verbose_name="Ссылка на объявление", max_length=300)

    brand = models.CharField(verbose_name="Марка", max_length=50)
    model = models.CharField(verbose_name="Модель", max_length=200)
    year = models.CharField(verbose_name="Год авто", max_length=4)
    color = models.CharField(verbose_name='Цвет автомобиля', max_length=15)
    info = models.TextField(verbose_name="Текст объявление")
    site = models.CharField(verbose_name="Сайт объявления", max_length=30)
    original = models.BooleanField(verbose_name='Оригинальное объявление')

    created_at = models.DateTimeField(verbose_name="Дата появления объявления", db_index=True)
    added_at = models.DateTimeField(verbose_name="Дата добавления в базу", blank=True)

    photos = models.ManyToManyField(to='AdvertisementPhotos',
                                    verbose_name='Ссылки на фотографии')
    similar_advertisement = models.ManyToManyField(to='self')

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.localtime(timezone.now())
        return super(Advertisement, self).save(*args, **kwargs)

    def __str__(self):
        return '{} {} {}'.format(self.advertisement_id, self.brand, self.model)

