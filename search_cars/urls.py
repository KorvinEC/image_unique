from django.urls import path
from . import views
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    path('index', views.index, name='index'),
    path('', views.DatabaseList.as_view(), name='database'),
    path('<int:pk>', views.AdvertisementPost.as_view(), name='advertisement'),
    path('check_unique', views.CheckUnique.as_view(), name='check unique'),
    path('test', views.test, name='test'),
    path('test_2', views.test_2, name='test_2'),
    path('test_request', views.test_request, name='test_request'),

    # path('admin', views.database, name='admin'),
    # path('test', , name='test'),
]
