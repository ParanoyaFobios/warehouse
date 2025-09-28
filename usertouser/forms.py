from django import forms
from usertouser.models import Message

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['recipient', 'content']
        widgets = {
            'recipient': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
        labels = {
            'recipient': 'Получатель',
            'content': 'Сообщение',
        }