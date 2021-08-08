from django.db import models
from django.utils import timezone
from django.db.models.signals import pre_delete
from django.dispatch.dispatcher import receiver


# Create your models here.


class AdvertisementPhotos(models.Model):
    adv_id    = models.ForeignKey('Advertisement', on_delete=models.CASCADE, verbose_name="Объявление", db_index=True)
    photo_url = models.CharField(verbose_name="Ссылка на изображение", max_length=200)
    photo     = models.ImageField(verbose_name='Изображение', null=True)
    avg_hash  = models.CharField(verbose_name='Изображение', max_length=16, null=True)

    def __str__(self):
        return '{} {} {} {}'.format(self.adv_id, self.photo_url, self.photo, self.avg_hash)


@receiver(pre_delete, sender=AdvertisementPhotos)
def mymodel_delete(sender, instance, **kwargs):
    instance.photo.delete(False)


class Advertisement(models.Model):
    advertisement_id = models.IntegerField(verbose_name="Id объявления", unique=True, db_index=True)
    advertisement_url = models.CharField(verbose_name="Ссылка на объявление", max_length=300)

    brand = models.CharField(verbose_name="Марка", max_length=50)
    model = models.CharField(verbose_name="Модель", max_length=200)
    year = models.CharField(verbose_name="Год авто", max_length=4)
    color = models.CharField(verbose_name='Цвет автомобиля', max_length=15, blank=True)
    info = models.TextField(verbose_name="Текст объявление")
    site = models.CharField(verbose_name="Сайт объявления", max_length=30)

    latitude = models.CharField(verbose_name='Широта', max_length=20, blank=True)
    longitude = models.CharField(verbose_name="Долгота", max_length=20, blank=True)

    run = models.IntegerField(verbose_name='Пробег', blank=True, null=True)
    price = models.IntegerField(verbose_name="Цена", blank=True, null=True)

    original = models.BooleanField(verbose_name='Оригинальное объявление', null=True)

    created_at = models.DateTimeField(verbose_name="Дата добавления в базу", db_index=True)
    added_at = models.DateTimeField(verbose_name="Дата появления объявления", blank=True)

    photos = models.ManyToManyField(to='AdvertisementPhotos',
                                    verbose_name='Ссылки на фотографии')
    similar_advertisement = models.ManyToManyField(to='self', blank=True)

    def save(self, *args, **kwargs):
        if not self.created_at:
            self.created_at = timezone.localtime(timezone.now())
        return super(Advertisement, self).save(*args, **kwargs)

    def __str__(self):
        return '{} {} {} {}'.format(self.advertisement_id, self.brand, self.model, self.year)

