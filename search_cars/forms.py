from django import forms
import datetime


class SearchForm(forms.Form):
    brand = forms.CharField(label='Бренд', max_length=15, required=False)
    model = forms.CharField(label='Модель', max_length=15, required=False)
    start_date = day = forms.DateField(initial=datetime.date.today)


class ImageUploadForm(forms.Form):
    background = forms.ImageField(
        label='Загрузить задний фон',
        widget=forms.ClearableFileInput(
            attrs={
                'class' : 'form-control-file'
            }
        )
    )
    images = forms.ImageField(
        label='Загрузить изображения',
        widget=forms.ClearableFileInput(
            attrs={
                'multiple': True,
                'class' : 'form-control-file'
            }
        )
    )