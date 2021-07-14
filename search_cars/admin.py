from django.contrib import admin
from .models import *

# Register your models here.


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('id', 'advertisement_id', 'advertisement_url', 'model', 'brand', 'created_at', 'added_at')
    list_filter = ('model', 'brand', 'created_at', 'added_at')
    # pass


@admin.register(AdvertisementPhotos)
class AdvertisementPhotosAdmin(admin.ModelAdmin):
    list_display = ('adv_id', 'photo_url')

# admin.site.register(Advertisement)
# admin.site.register(AdvertisementPhotos)