from django import forms
from .models import Material

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = [
            'name', 'article', 'category', 'supplier', 
            'barcode', 'quantity', 'unit', 'image', 'description'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class IncomingForm(forms.Form):
    barcode = forms.CharField(label='Штрихкод', max_length=50)
    quantity = forms.DecimalField(label='Количество', max_digits=10, decimal_places=2)
    comment = forms.CharField(label='Комментарий', required=False, widget=forms.Textarea(attrs={'rows': 2}))

class OutgoingForm(forms.Form):
    barcode = forms.CharField(label='Штрихкод', max_length=50)
    quantity = forms.DecimalField(label='Количество', max_digits=10, decimal_places=2)
    comment = forms.CharField(label='Комментарий', required=False, widget=forms.Textarea(attrs={'rows': 2}))

class InventoryForm(forms.Form):
    barcode = forms.CharField(label='Штрихкод', max_length=50)
    new_quantity = forms.DecimalField(label='Фактическое количество', max_digits=10, decimal_places=2)
    comment = forms.CharField(label='Комментарий', required=False, widget=forms.Textarea(attrs={'rows': 2}))