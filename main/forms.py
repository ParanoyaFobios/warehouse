from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User, Group

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


class UserCreationWithGroupForm(forms.Form):
    username = forms.CharField(label="Логин (имя пользователя)", max_length=100)
    first_name = forms.CharField(label="Имя пользователя", max_length=100, required=False)
    phone = forms.IntegerField(label="Телефон", required=False)
    password = forms.CharField(label="Пароль", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Повторите пароль", widget=forms.PasswordInput)
    
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Роль (группа)",
        empty_label="Выберите роль для пользователя"
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Пользователь с таким логином уже существует.")
        return username

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError("Пароли не совпадают.")
        return password2
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