from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User

class ContentTypeAware(models.Model):
    """
    Миксин, который добавляет моделям метод для получения ID их ContentType.
    """
    class Meta:
        abstract = True # Это говорит Django, что не нужно создавать для миксина отдельную таблицу в БД

    def get_content_type_id(self):
        return ContentType.objects.get_for_model(self).pk
    


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)

    @property
    def avatar_path(self):
        """Возвращает путь к иконке аватара на основе группы пользователя."""
        # Обращаемся к связанному пользователю через self
        u = self.user
        
        # Если юзер не активен или не авторизован (на всякий случай)
        if not u.is_active:
            return 'icons/avatar-default.svg'

        # Получаем список имен в нижнем регистре для страховки
        group_names = [g.name.lower() for g in u.groups.all()]
        
        # Словарь "Ключевое слово" -> "Файл в статике"
        mapping = {
            'manager': 'avatar-manager.svg',
            'менеджер': 'avatar-manager.svg',
            'store': 'avatar-storekeeper.svg',
            'склад': 'avatar-storekeeper.svg',
            'клад': 'avatar-storekeeper.svg',
            'prod': 'avatar-production.svg',
            'производст': 'avatar-production.svg',
            'бухг': 'avatar-accountant.svg',
            'управл': 'avatar-administrator.svg',
        }

        for key, icon in mapping.items():
            # Проверяем, есть ли ключевое слово в любом из имен групп
            if any(key in name for name in group_names):
                return f'icons/{icon}'

        return 'icons/avatar.svg'

    def __str__(self):
        return f"Профиль для {self.user.username}"