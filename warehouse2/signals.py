from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ProductOperation
from .tasks import update_stock_in_keycrm

@receiver(post_save, sender=ProductOperation)
def trigger_stock_update_on_operation(sender, instance, created, **kwargs):
    """
    Этот сигнал срабатывает каждый раз, когда сохраняется объект ProductOperation.
    """
    # Мы запускаем задачу только при СОЗДАНИИ новой операции
    if created:
        # Отправляем ID товара в фоновую задачу Celery
        # .delay() - это команда для Celery "выполни это в фоне"
        update_stock_in_keycrm.delay(instance.product.id)