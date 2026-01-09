from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, ProductOperation
from .tasks import update_stock_in_keycrm, sync_product_to_keycrm

@receiver(post_save, sender=Product)
def trigger_product_sync(sender, instance, created, update_fields, **kwargs):
    """
    Синхронизация ПРИ ИЗМЕНЕНИИ КАРТОЧКИ ТОВАРА.
    """
    if update_fields and 'keycrm_id' in update_fields:
        return

    # Если мы изменили ТОЛЬКО остатки (через складскую операцию), 
    # полная синхронизация не нужна, ее сделает другой сигнал ниже.
    if update_fields and list(update_fields) == ['total_quantity']:
        return

    sync_product_to_keycrm.delay(instance.id)


@receiver(post_save, sender=ProductOperation)
def trigger_stock_update_on_operation(sender, instance, created, **kwargs):
    """
    Синхронизация ОСТАТКОВ при движении товара (быстрый PATCH).
    """
    if created:
        # Используем именно быстрый метод обновления остатка
        update_stock_in_keycrm.delay(instance.product.id)


@receiver(post_save, sender=Product)
def trigger_product_sync(sender, instance, created, **kwargs):
    # Если это не техническое сохранение самого ID, отправляем на синхронизацию
    # Мы передаем задачу в Celery, которая сделает PUT запрос в KeyCRM
    from .tasks import sync_product_to_keycrm
    sync_product_to_keycrm.delay(instance.id)