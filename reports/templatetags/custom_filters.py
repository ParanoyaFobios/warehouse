from django import template
from urllib.parse import urlencode, parse_qs, urlparse, urlunparse

register = template.Library()

@register.filter
def remove_param(url_string, param_to_remove):
    """
    Удаляет параметр из URL строки
    Использование: {{ request.GET.urlencode|remove_param:'page' }}
    """
    if not url_string:
        return ''
    
    # Парсим URL
    parsed = urlparse(url_string)
    query_dict = parse_qs(parsed.query)
    
    # Удаляем параметр
    if param_to_remove in query_dict:
        del query_dict[param_to_remove]
    
    # Собираем URL обратно
    new_query = urlencode(query_dict, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    
    return urlunparse(new_parsed)