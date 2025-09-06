from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class InventoryCount(models.Model):
    """
    Основная модель, представляющая одну сессию переучета (инвентаризации).
    """
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'В процессе'
        COMPLETED = 'completed', 'Завершен (ожидает сверки)'
        RECONCILED = 'reconciled', 'Скорректирован (закрыт)'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Ответственный кладовщик"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        verbose_name="Статус"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата начала")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")
    notes = models.TextField(blank=True, verbose_name="Примечания к переучету")

    def __str__(self):
        return f"Переучет №{self.id} от {self.created_at.strftime('%d.%m.%Y')}"

    class Meta:
        verbose_name = "Переучет"
        verbose_name_plural = "Переучеты"
        ordering = ['-created_at']


class InventoryCountItem(models.Model):
    """
    Одна позиция (строка) в документе переучета.
    Может ссылаться на любую модель складского учета (Material, Product).
    """
    inventory_count = models.ForeignKey(
        InventoryCount,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Переучет"
    )

    # GenericForeignKey для связи с любой моделью (Material, Product и т.д.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="Тип объекта")
    object_id = models.PositiveIntegerField(verbose_name="ID объекта")
    content_object = GenericForeignKey('content_type', 'object_id')

    system_quantity = models.IntegerField(
        verbose_name="Кол-во по системе",
        help_text="Количество в базе данных на момент добавления позиции"
    )
    actual_quantity = models.IntegerField(
        default=0,
        verbose_name="Фактическое кол-во",
        help_text="Количество, введенное кладовщиком по факту"
    )

    @property
    def variance(self):
        """Расхождение между фактом и системой."""
        return self.actual_quantity - self.system_quantity

    def __str__(self):
        if self.content_object:
            return f"{self.content_object.name} - Факт: {self.actual_quantity}"
        return f"Позиция {self.id}"

    class Meta:
        verbose_name = "Позиция переучета"
        verbose_name_plural = "Позиции переучета"
        # Гарантирует, что один и тот же товар не будет добавлен в один переучет дважды
        unique_together = ('inventory_count', 'content_type', 'object_id')