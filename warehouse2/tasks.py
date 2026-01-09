import requests
from celery import shared_task
from django.conf import settings
from .models import Product

@shared_task(bind=True, default_retry_delay=300, max_retries=10)
def update_stock_in_keycrm(self, product_id):
    """
    Фоновая задача для обновления остатка товара в KeyCRM.
    """
    try:
        product = Product.objects.get(pk=product_id)
        # Если у товара нет ID из KeyCRM или остаток 0, ничего не делаем
        if not product.keycrm_id:
            return f"Пропущен товар '{product.name}': отсутствует KeyCRM ID."

        API_KEY = getattr(settings, 'KEYCRM_API_KEY')
        API_URL = "https://openapi.keycrm.app/v1"
        headers = { "Authorization": f"Bearer {API_KEY}" }
        
        # Данные для обновления. KeyCRM ожидает 'quantity'.
        payload = {
            "quantity": product.available_quantity
        }
        
        # Отправляем PATCH-запрос для обновления только одного поля
        response = requests.patch(f"{API_URL}/products/{product.keycrm_id}", json=payload, headers=headers)
        response.raise_for_status() # Вызовет ошибку, если запрос неуспешный
        
        return f"Остаток для '{product.name}' (KeyCRM ID: {product.keycrm_id}) успешно обновлен на {payload['quantity']}."

    except Product.DoesNotExist:
        return f"Ошибка: Товар с ID {product_id} не найден."
    except requests.exceptions.RequestException as e:
        # В реальном проекте здесь можно настроить повторные попытки
        return f"Ошибка API KeyCRM для товара ID {product_id}: {e}"
    


@shared_task(bind=True, default_retry_delay=300, max_retries=5)
def sync_product_to_keycrm(self, product_id):
    try:
        product = Product.objects.get(pk=product_id)
        if not product.keycrm_id:
            return "Синхронизация невозможна: нет KeyCRM ID"

        url = f"https://openapi.keycrm.app/v1/products/{product.keycrm_id}"
        headers = {"Authorization": f"Bearer {settings.KEYCRM_API_KEY}"}
        
        # Формируем данные для CRM
        payload = {
            "name": product.name,
            "sku": product.sku,
            "price": float(product.price),
            "is_archived": product.is_archived,
            "quantity": product.total_quantity
        }
        
        if product.category and product.category.keycrm_id:
            payload["category_id"] = product.category.keycrm_id

        response = requests.put(url, json=payload, headers=headers)
        response.raise_for_status()
        
        return f"Товар {product.sku} синхронизирован. Статус архива: {product.is_archived}"
    except Exception as exc:
        raise self.retry(exc=exc)