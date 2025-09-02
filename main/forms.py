from django import forms
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Логин',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Логин'
        })
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Пароль'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Запомнить меня'
    )
    
    error_messages = {
        'invalid_login': "Введите правильное имя пользователя и пароль.",
        'inactive': "Этот аккаунт не активен.",
    }

#==============================================
# Форма для глобального поиска
#==============================================

class GlobalSearchForm(forms.Form):
    q = forms.CharField(
        label='',
        widget=forms.TextInput(attrs={
            'class': 'form-control me-2',
            'placeholder': 'Поиск по названию, артикулу, штрихкоду...',
            'aria-label': 'Search'
        })
    )