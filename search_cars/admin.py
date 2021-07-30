from django.contrib import admin
from .models import *

# Register your models here.


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('id', 'advertisement_id', 'advertisement_url', 'model', 'brand', 'created_at', 'added_at', 'original')

    fields = (
        ('advertisement_id', 'advertisement_url'),
        ('model', 'brand', 'year', 'color', 'original'),
        ('created_at', 'added_at', 'site'),
        ('latitude', 'longitude', 'run', 'price'),
        ('photos', 'similar_advertisement'),
        'info'
    )

    readonly_fields = ('photos', 'similar_advertisement')

    search_fields = ('id', 'advertisement_id', 'advertisement_url', 'model', 'brand')

    # def formfield_for_manytomany(self, db_field, request, **kwargs):
    #     print(f'{request = }')
    #     if db_field.name == "similar_advertisement":
    #         kwargs["queryset"] = Advertisement.objects.filter(advertisement_id=0)
    #     return super().formfield_for_manytomany(db_field, request, **kwargs)

    # exclude = ('photos', 'similar_advertisement')
    # readonly_fields = ('photos__photo_url', 'similar_advertisement__advertisement_id')
    # filter_horizontal = ('photos','similar_advertisement')


@admin.register(AdvertisementPhotos)
class AdvertisementPhotosAdmin(admin.ModelAdmin):
    list_display = ('id', 'adv_id_id', 'adv_id', 'photo_url')
    search_fields = ('id',)

# admin.site.register(Advertisement)
# admin.site.register(AdvertisementPhotos)