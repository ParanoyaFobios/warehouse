# usertouser/models.py
from django.db import models
from django.conf import settings # Лучше использовать settings.AUTH_USER_MODEL

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages',verbose_name="Отправитель")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages',verbose_name="Получатель")
    content = models.TextField(verbose_name="Содержание")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время отправки")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    
    # Поля для "мягкого" удаления
    sender_deleted = models.BooleanField(default=False, verbose_name="Удалено отправителем")
    recipient_deleted = models.BooleanField(default=False, verbose_name="Удалено получателем")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"
        
    def __str__(self):
        return f'От {self.sender.username} для {self.recipient.username}'