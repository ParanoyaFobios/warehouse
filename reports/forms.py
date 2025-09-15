from django import forms

# Собираем все возможные типы операций из обеих моделей
OPERATION_TYPE_CHOICES = [
    ('', 'Все типы'),
    ('production', 'Производство (+)'),
    ('shipment', 'Отгрузка (-)'),
    ('adjustment', 'Корректировка (+/-)'),
    ('return', 'Возврат (+)'),
    ('incoming', 'Прием (+)'),# такое же поле есть в warehouse2\models.py class ProductOperation(models.Model) проверить не будет ли конфликтов
    ('outgoing', 'Выдача (-)'),
]

class MovementReportFilterForm(forms.Form):
    start_date = forms.DateField(
        label="Дата с", 
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label="Дата по", 
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    operation_type = forms.ChoiceField(
        label="Тип операции",
        required=False,
        choices=OPERATION_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Поле для поиска конкретного товара/материала
    item_search = forms.CharField(
        label="Название/Артикул",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Поиск по товару'})
    )

class DateRangeFilterForm(forms.Form):
    start_date = forms.DateField(
        label="Дата с", 
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        label="Дата по", 
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )