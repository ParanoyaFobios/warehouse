from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

# 1. Создаем инлайн для профиля
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Дополнительная информация (Профиль)'

# 2. Переопределяем стандартный UserAdmin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'get_phone', 'first_name', 'last_name', 'is_staff', 'get_groups')
    list_select_related = ('profile',) # Оптимизация запросов

    # Метод для вывода телефона в списке всех пользователей
    def get_phone(self, instance):
        return instance.profile.phone if hasattr(instance, 'profile') else '-'
    get_phone.short_description = 'Телефон'

    # Метод для вывода групп в списке
    def get_groups(self, instance):
        return ", ".join([group.name for group in instance.groups.all()])
    get_groups.short_description = 'Роли'

# 3. Перерегистрируем модель User
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# На всякий случай регистрируем и сам профиль отдельно, 
# если вдруг захочется редактировать телефоны без захода в User
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone')
    search_fields = ('user__username', 'phone')