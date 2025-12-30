from django import forms
from django.contrib.auth.models import User
from .models import Message

class NewMessageForm(forms.ModelForm):
    recipients = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(), 
        widget=forms.CheckboxSelectMultiple,
        label="Получатели",
        required=True
    )

    class Meta:
        model = Message
        fields = ['recipients', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        # Извлекаем пользователя, которого мы передадим из view
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Кастомная метка для отображения
        self.fields['recipients'].label_from_instance = self.get_user_display
        
        # Если пользователь передан, настраиваем queryset
        if user:
            self.fields['recipients'].queryset = User.objects.filter(
                is_active=True
            ).exclude(pk=user.pk).prefetch_related('groups')

    @staticmethod
    def get_user_display(user):
        """Кастомное отображение пользователя в выборе"""
        parts = [user.username]
        
        # Добавляем полное имя, если есть
        full_name = user.get_full_name()
        if full_name:
            parts.append(f"({full_name})")
        
        # Добавляем группы
        groups = user.groups.all()
        if groups.exists():
            group_names = ", ".join([group.name for group in groups])
            parts.append(f"- {group_names}")
        
        return " ".join(parts)
    

# --- Сценарий 2: Ответ в открытом чате (новая простая форма) ---
class ChatForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Напишите сообщение...',
                'autocomplete': 'off'
            }),
        }