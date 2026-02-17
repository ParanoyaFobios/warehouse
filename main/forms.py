from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User, Group
from .models import UserProfile

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
    username = forms.CharField(
        label="Логин", 
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    first_name = forms.CharField(
        label="Имя", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input'})
    )
    phone = forms.CharField( # Используем CharField для гибкости формата
        label="Телефон", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'type': 'tel'})
    )
    password = forms.CharField(
        label="Пароль", 
        widget=forms.PasswordInput(attrs={'class': 'form-input'})
    )
    password2 = forms.CharField(
        label="Повторите пароль", 
        widget=forms.PasswordInput(attrs={'class': 'form-input'})
    )
    
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        label="Роль",
        empty_label="Выберите роль"
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
    

class UserUpdateForm(forms.ModelForm):
    phone = forms.CharField(
        label="Телефон", 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'type': 'tel'})
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(), 
        label="Роль",
        empty_label="Выберите роль"
    )

    new_password = forms.CharField(
        label="Новый пароль", 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Оставьте пустым, чтобы не менять'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        if self.instance.pk:

            if hasattr(self.instance, 'profile'):

                self.fields['phone'].initial = self.instance.profile.phone

            self.fields['group'].initial = self.instance.groups.first()

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pwd = self.cleaned_data.get('new_password')
        if new_pwd:
            user.set_password(new_pwd) # Django сам всё захеширует
        if commit:
            user.save()
        return user
#==============================================
# Форма для глобального поиска
#==============================================

class GlobalSearchForm(forms.Form):
    q = forms.CharField(
        label='Поиск',
        widget=forms.TextInput(attrs={
            'class': 'search-bar__elem search-bar__field-control', # Ваши CSS классы
            'placeholder': 'Поиск',
            'aria-label': 'Search',
            'required': 'required',
            'id': 'id_q', # Django и так ставит id_q по умолчанию, но можно прописать явно
        })
    )