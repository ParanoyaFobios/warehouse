import sys
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product, ProductOperation
from .tasks import update_stock_in_keycrm, sync_product_to_keycrm

@receiver(post_save, sender=Product)
def trigger_product_sync(sender, instance, created, **kwargs):
    """
    Синхронизация продукта с KeyCRM при создании или изменении важных полей.
    """
    update_fields = kwargs.get('update_fields')

    # Игнорируем обновление ID
    if update_fields:
        # Поля, которые относятся только к складу
        stock_fields = {'total_quantity', 'reserved_quantity', 'keycrm_id'}
        
        # Если обновляемые поля — это подмножество складских полей, ничего не делаем
        if set(update_fields).issubset(stock_fields):
            return

    # Если мы здесь (created=True или изменили цену/имя), шлем полную карточку
    sync_product_to_keycrm.apply_async(args=[instance.id], countdown=2)


@receiver(post_save, sender=ProductOperation)
def trigger_stock_update_on_operation(sender, instance, created, **kwargs):
    """
    Синхронизация остатков при создании операции (приход/расход).
    """
    if created and instance.product:
        # Запускаем специальную задачу для остатков (PUT /offers/stocks)
        update_stock_in_keycrm.apply_async(args=[instance.product.id], countdown=2)