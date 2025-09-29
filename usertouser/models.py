from django.db import models
from django.conf import settings

class Message(models.Model):
    """
    Основная модель сообщения. Хранит отправителя и текст.
    Получатели, статусы прочтения и удаления вынесены в модель MessageRecipient.
    """
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, # Если отправителя удалят, сообщение останется
        null=True,
        related_name='sent_messages',
        verbose_name="Отправитель"
    )
    recipients = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='MessageRecipient', # Указываем, что связь будет через промежуточную модель
        related_name='received_messages',
        verbose_name="Получатели"
    )
    content = models.TextField(verbose_name="Содержание")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время отправки")
    
    # Флаг удаления для отправителя
    sender_deleted = models.BooleanField(default=False, verbose_name="Удалено отправителем")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"

        
    def __str__(self):
        return f'"От {self.sender.username if self.sender else "N/A"}'
    
    def get_recipients_display(self):
        """Отображение получателей для шаблонов"""
        return ", ".join([user.username for user in self.recipients.all()])

    def get_recipients_count(self):
        """Количество получателей"""
        return self.recipients.count()


class MessageRecipient(models.Model):
    """
    Промежуточная модель. Связывает каждое сообщение с каждым его получателем
    и хранит персональный статус (прочитано/удалено) для этой связи.
    """
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Получатель")
    is_read = models.BooleanField(default=False, verbose_name="Прочитано")
    is_deleted = models.BooleanField(default=False, verbose_name="Удалено получателем")

    class Meta:
        unique_together = ('message', 'user') # У одного сообщения не может быть двух одинаковых получателей