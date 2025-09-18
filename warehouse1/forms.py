from django import forms
from .models import Material, OperationOutgoingCategory

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = [
            'name', 'article', 'category', 'unit', 'color', 'image', 'min_quantity', 'description'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def clean_article(self):
        article = self.cleaned_data['article']
        if Material.objects.filter(article=article).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Материал с таким артикулом уже существует")
        return article

class MaterialSearchForm(forms.Form):
    barcode = forms.CharField(
        label='Штрихкод',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Введите штрихкод'})
    )
    name = forms.CharField(
        label='Название',
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Введите название'})
    )
    article = forms.CharField(
        label='Артикул',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Введите артикул'})
    )



class MaterialOperationForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Динамически заполняем choices для outgoing_category
        self.fields['outgoing_category'] = forms.ModelChoiceField(
            label='Категория выдачи',
            queryset=OperationOutgoingCategory.objects.all(),
            empty_label="Выберите категорию",
            required=False
        )

    quantity = forms.DecimalField(
        label='Количество',
        max_digits=10,
        decimal_places=2,
        min_value=0.01
    )
    comment = forms.CharField(
        label='Комментарий',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2})
    )