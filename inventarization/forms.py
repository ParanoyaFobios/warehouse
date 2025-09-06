from django import forms

class InventoryItemForm(forms.Form):
    """
    Форма для добавления новой позиции в переучет через AJAX-поиск или сканер.
    """
    item_identifier = forms.CharField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(
        min_value=0,
        label="Фактическое количество",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Введите фактическое кол-во'})
    )

class InventoryItemUpdateForm(forms.Form):
    """
    Мини-форма для быстрого обновления количества уже добавленной позиции.
    """
    quantity = forms.IntegerField(
        min_value=0,
        label="",
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm'})
    )