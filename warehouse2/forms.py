from django import forms
from .models import Product, WorkOrder, Shipment

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

class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = []  # Пока только статус, можно добавить клиента и т.д.