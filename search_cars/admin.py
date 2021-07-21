from django.contrib import admin
from .models import *

# Register your models here.


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('id', 'advertisement_id', 'advertisement_url', 'model', 'brand', 'created_at', 'added_at')
    search_fields = ('id', 'advertisement_id', 'advertisement_url', 'model', 'brand')
    exclude = ('photos', 'similar_advertisement')


@admin.register(AdvertisementPhotos)
class AdvertisementPhotosAdmin(admin.ModelAdmin):
    list_display = ('id', 'adv_id_id', 'adv_id', 'photo_url')
    search_fields = ('id',)

# admin.site.register(Advertisement)
# admin.site.register(AdvertisementPhotos)