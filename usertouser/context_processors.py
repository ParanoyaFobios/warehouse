from .models import MessageRecipient

def unread_messages_count(request):
    """
    Считает количество непрочитанных сообщений для текущего пользователя.
    """
    if request.user.is_authenticated:
        # 2. Теперь мы запрашиваем промежуточную модель MessageRecipient
        count = MessageRecipient.objects.filter(
            user=request.user,       # Фильтруем по текущему пользователю
            is_read=False,           # Сообщение не прочитано
            is_deleted=False         # И не удалено получателем
        ).count()
        return {'unread_messages_count': count}
    return {}