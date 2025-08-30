from django import forms
from .models import Product, WorkOrder, Shipment, Package

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'size', 'color', 'weight', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'size': forms.Select(attrs={'class': 'form-control'}),
            'color': forms.Select(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class PackageForm(forms.ModelForm):
    class Meta:
        model = Package
        fields = ['name', 'quantity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например, Коробка (опционально)'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Кол-во штук в упаковке'}),
        }
        labels = {
            'name': 'Название упаковки',
            'quantity': 'Количество',
        }

class WorkOrderForm(forms.ModelForm):
    product_search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по названию, артикулу или штрихкоду...',
            'id': 'product-search'
        }),
        label='Поиск продукта'
    )
    
    class Meta:
        model = WorkOrder
        fields = ['product', 'quantity_to_produce']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control',
                'id': 'product-select'
            }),
            'quantity_to_produce': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].widget.attrs['style'] = 'display: none;'
        self.fields['product'].label = ''

#================= Shipment and ShipmentItem Forms =================#
        
class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ['destination'] # Оставляем только те поля, что заполняет пользователь
        widgets = {
            'destination': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Город, адрес склада и т.д.'}),
        }
        labels = {
            'destination': 'Пункт назначения',
        }

# 👇 Новая форма для добавления позиций в отгрузку 👇
class ShipmentItemForm(forms.Form):
    # Это поле будет скрытым, его заполнит JavaScript после выбора в поиске
    # Оно будет хранить строку вида "product-1" или "package-5"
    item_identifier = forms.CharField(widget=forms.HiddenInput())
    
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'value': 1}),
        label="Количество"
    )
