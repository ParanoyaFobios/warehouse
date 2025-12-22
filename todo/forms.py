from django import forms
from .models import ProductionOrder, WorkOrder


class ProductionOrderForm(forms.ModelForm):
    class Meta:
        model = ProductionOrder
        fields = ['customer', 'due_date', 'comment']
        widgets = {
            'due_date': forms.DateInput(
                format='%Y-%m-%d', # Важно: именно такой формат понимает HTML5
                attrs={
                    'type': 'date', # Превращает обычное поле в календарь
                    'class': 'form-control'}),
            'customer': forms.TextInput(attrs={'class': 'form-control'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Это гарантирует, что при редактировании дата будет в нужном формате
        if self.instance and self.instance.due_date:
            self.initial['due_date'] = self.instance.due_date.strftime('%Y-%m-%d')

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