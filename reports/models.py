from django.db import models
from django.conf import settings
from warehouse2.models import Shipment

class ShipmentAuditLog(models.Model):
    ACTION_CHOICES = [
        ('item_added', 'Добавлен товар после печати'),
        ('item_removed', 'Удален товар после печати'),
        ('item_updated', 'Изменено количество/цена после печати'),
    ]

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(verbose_name="Что именно изменилось")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Лог аудита накладной"
        verbose_name_plural = "Логи аудита накладных"
        ordering = ['-created_at']

    def __str__(self):
        return f"Инцидент по накладной №{self.shipment_id} - {self.get_action_display()}"