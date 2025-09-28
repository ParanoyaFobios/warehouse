from django import forms
from django.contrib.auth.models import User
from .models import Message

class MessageForm(forms.ModelForm):
    # Используем ModelMultipleChoiceField для выбора нескольких получателей
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().prefetch_related('groups').order_by('username'),
        widget=forms.CheckboxSelectMultiple, # Отображаем в виде чекбоксов
        label="Получатели"
    )

    class Meta:
        model = Message
        fields = ['recipients', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }