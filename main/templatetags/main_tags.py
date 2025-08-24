from django import template
from django.contrib.contenttypes.models import ContentType

register = template.Library()

@register.filter
def get_content_type_id(obj):
    """
    Возвращает ID ContentType для переданного объекта.
    """
    if not obj:
        return None
    return ContentType.objects.get_for_model(obj).pk