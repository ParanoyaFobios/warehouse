from django import forms
from .models import Operation, TechCardGroup, TechCardOperation, WorkEntry
from django.forms import inlineformset_factory
from .models import TechCardGroup, TechCardOperation
from django import forms
from warehouse2.models import Product


class OperationForm(forms.ModelForm):
    class Meta:
        model = Operation
        fields = ['name', 'payment_type', 'default_rate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Пошив подушки'}),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'default_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
        labels = {
            'name': 'Название операции',
            'payment_type': 'Тип оплаты',
            'default_rate': 'Ставка (дефолтная)',
        }


class TechCardGroupForm(forms.ModelForm):
    class Meta:
        model = TechCardGroup
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TechCardOperationForm(forms.ModelForm):
    class Meta:
        model = TechCardOperation
        fields = ['operation', 'price']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ограничиваем список только сдельными операциями
        self.fields['operation'].queryset = Operation.objects.filter(payment_type='piece')
        self.fields['operation'].widget.attrs.update({'class': 'form-select'})
        self.fields['price'].widget.attrs.update({'class': 'form-control'})


TechCardOperationFormSet = inlineformset_factory(
    TechCardGroup, 
    TechCardOperation,
    form=TechCardOperationForm, # Используем нашу настроенную форму
    extra=0,                    # Теперь ставим 0, так как будем добавлять кнопкой
    can_delete=True
)

#===============================================
# Форма для работника, чтобы подать заявку на выполненные операции
#===============================================

class HourlyWorkForm(forms.ModelForm):
    class Meta:
        model = WorkEntry
        fields = ['operation', 'quantity', 'date_performed']
        labels = {
            'operation': 'Что делали (почасовое)',
            'quantity': 'Сколько часов',
            'date_performed': 'Дата работы'
        }
        widgets = {
            'operation': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
            'date_performed': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только почасовые операции
        self.fields['operation'].queryset = Operation.objects.filter(payment_type='hourly')

class PieceWorkForm(forms.ModelForm):
    class Meta:
        model = WorkEntry
        fields = ['product', 'operation', 'quantity', 'date_performed']
        labels = {
            'product': 'Поиск изделия',
            'operation': 'Операция (из техкарты)',
            'quantity': 'Количество (шт.)',
            'date_performed': 'Дата работы'
        }
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select select2'}), # Будем использовать поиск
            'operation': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'date_performed': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['operation'].queryset = Operation.objects.none()
        self.fields['product'].queryset = Product.objects.filter(tech_card__isnull=False)

        # Исправленная логика фильтрации операций
        if 'product' in self.data:
            try:
                product_id = int(self.data.get('product'))
                product = Product.objects.get(id=product_id)
                if product.tech_card:
                    # Теперь мы берем операции через TechCardOperation, 
                    # связанные с группой (tech_card), привязанной к продукту
                    op_ids = TechCardOperation.objects.filter(
                        group=product.tech_card
                    ).values_list('operation_id', flat=True)
                    
                    self.fields['operation'].queryset = Operation.objects.filter(id__in=op_ids)
            except (ValueError, TypeError, Product.DoesNotExist):
                pass