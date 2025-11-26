from django import forms
from django.forms import inlineformset_factory
from .models import ProductionOrder, ProductionOrderItem, WorkOrder

class ProductionOrderForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = ['customer', 'due_date', 'comment']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class ProductionOrderItemForm(forms.ModelForm):
    class Meta:
        # ИСПРАВЛЕНО: имя модели
        model = ProductionOrderItem 
        fields = ['product', 'quantity_requested']
        widgets = {
            # Пока используем обычный Select, чтобы не ломать голову с JS сейчас
            'product': forms.Select(attrs={'class': 'form-control product-select-field'}),
        }

# ИСПРАВЛЕНО: Имена моделей
ProductionOrderItemFormSet = inlineformset_factory(
    ProductionOrder,      
    ProductionOrderItem,  
    form=ProductionOrderItemForm,
    fields=['product', 'quantity_requested'],
    extra=1,              
    can_delete=True,
    can_delete_extra=True
)

class WorkOrderAdHocForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = ['product', 'quantity_planned', 'comment']
        widgets = {
            'product': forms.HiddenInput(attrs={'id': 'product-select'})
        }

class ReportProductionForm(forms.Form):
    quantity_done = forms.IntegerField(label="Сколько произведено (факт)", min_value=1)
    
    def __init__(self, *args, **kwargs):
        self.work_order = kwargs.pop('work_order', None)
        super().__init__(*args, **kwargs)
        if self.work_order:
            remaining = self.work_order.remaining_to_produce
            self.fields['quantity_done'].initial = remaining
            self.fields['quantity_done'].max_value = remaining
            self.fields['quantity_done'].help_text = f"Осталось по этому заданию: {remaining} шт."