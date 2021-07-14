from django.urls import path
from . import views
from django.contrib.admin.views.decorators import staff_member_required

urlpatterns = [
    path('index', views.index, name='index'),
    path('', views.database, name='database'),
    # path('admin', views.database, name='admin'),
    path('CheckUnique', views.CheckUnique.as_view(), name='check unique'),
    path('test', views.test, name='test'),
    # path('test_2', views.test_2, name='test_2'),
]
