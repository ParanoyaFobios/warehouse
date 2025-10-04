from django.db import models
from django.contrib.contenttypes.models import ContentType

class ContentTypeAware(models.Model):
    """
    Миксин, который добавляет моделям метод для получения ID их ContentType.
    """
    class Meta:
        abstract = True # Это говорит Django, что не нужно создавать для миксина отдельную таблицу в БД

    def get_content_type_id(self):
        return ContentType.objects.get_for_model(self).pk