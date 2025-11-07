import requests
from celery import shared_task
from django.conf import settings
from .models import Product

@shared_task
def update_stock_in_keycrm(product_id):
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