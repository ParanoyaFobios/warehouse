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

    def __str__(self):
        return f"Профиль для {self.user.username}"