# Generated by Django 3.2.5 on 2021-07-18 16:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('search_cars', '0013_auto_20210718_1744'),
    ]

    operations = [
        migrations.AddField(
            model_name='advertisement',
            name='latitude',
            field=models.CharField(blank=True, max_length=20, verbose_name='Широта'),
        ),
        migrations.AddField(
            model_name='advertisement',
            name='longitude',
            field=models.CharField(blank=True, max_length=20, verbose_name='Долгота'),
        ),
    ]
