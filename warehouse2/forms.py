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
    class Meta:
        model = WorkOrder
        fields = ['product', 'quantity_to_produce']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity_to_produce': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = []  # Пока только статус, можно добавить клиента и т.д.