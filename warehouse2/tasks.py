import requests
from celery import shared_task
from django.conf import settings
from .models import Product

@shared_task(bind=True, default_retry_delay=300, max_retries=3)
def update_stock_in_keycrm(self, product_id):
    try:
        product = Product.objects.get(pk=product_id)
        product.refresh_from_db() # Подтягиваем свежие цифры из БД
        current_stock = product.available_quantity
        if not product.keycrm_id:
            return f"Пропущено: нет KeyCRM ID."

        API_KEY = settings.KEYCRM_API_KEY
        url = "https://openapi.keycrm.app/v1/offers/stocks"
        headers = { 
            "Authorization": f"Bearer {API_KEY}", 
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "warehouse_id": 2, # ваш проверенный ID
            "stocks": [
                {
                    "sku": product.sku,  # Используем SKU как главный идентификатор
                    "quantity": int(current_stock)
                }
            ]
        }
        
        response = requests.put(url, json=payload, headers=headers)
        
        if response.status_code == 422:
            print(f"!!! Ошибка валидации остатков: {response.json()}")
            return f"Ошибка валидации: {response.json()}"

        response.raise_for_status() 
        
        return f"Остатки для '{product.name}' успешно обовлены до {product.available_quantity} шт."

    except Exception as e:
        print(f"!!! Ошибка обновления склада: {e}")
        return f"Ошибка API KeyCRM: {e}"


@shared_task(bind=True, default_retry_delay=10, max_retries=3)
def sync_product_to_keycrm(self, product_id):
    try:
        product = Product.objects.get(pk=product_id)
        print(f">>> Начало синхронизации: {product.name} (ID: {product.keycrm_id})")
        
        API_KEY = settings.KEYCRM_API_KEY
        API_URL = "https://openapi.keycrm.app/v1/products"
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        # Секция кода для прокси URL для изображений, раскоментить если нужно использовать
        # base_url = "https://5cda685854be.ngrok-free.app" # Замените на ваш реальный базовый URL после деплоя
        # pictures = []
        # if product.image:
        #     # Короткая и чистая ссылка для KeyCRM
        #     proxy_url = f"{base_url}/img-proxy/{product.id}/"
        #     pictures.append(proxy_url)
        payload = {
            "name": str(product.name),
            "sku": str(product.sku),
            "price": float(product.price),
            "quantity": int(product.total_quantity or 0),
            "unit_type": "шт",
            "currency_code": "UAH",}
            # "pictures": pictures,}

        # if not pictures:
        #     payload.pop("pictures")

        if product.category and product.category.keycrm_id:
            payload["category_id"] = int(product.category.keycrm_id)

        if product.keycrm_id:
            url = f"{API_URL}/{product.keycrm_id}"
            print(f"--- Отправка PUT запроса на {url}")
            response = requests.put(url, json=payload, headers=headers, timeout=10)
        else:
            print(f"--- Отправка POST запроса (создание)")
            response = requests.post(API_URL, json=payload, headers=headers, timeout=10)

        print(f"--- Статус ответа: {response.status_code}")

        if response.status_code in [422, 400]:
            err_msg = response.json()
            print(f"!!! Ошибка валидации CRM: {err_msg}")
            return f"Ошибка данных: {err_msg}"

        response.raise_for_status()
        data = response.json()

        if not product.keycrm_id and 'id' in data:
            new_id = data['id']
            print(f"--- Получен новый ID: {new_id}. Сохраняем...")
            # Чтобы избежать рекурсии сигналов, обновляем через QuerySet
            Product.objects.filter(pk=product.pk).update(keycrm_id=new_id)

        print(f">>> УСПЕШНО для {product.name}")
        return f"Успех: {product.name}"

    except requests.exceptions.Timeout:
        print("!!! Ошибка: Сервер KeyCRM не ответил вовремя (Timeout)")
        raise self.retry(exc=Exception("KeyCRM Timeout"))
    except Exception as exc:
        print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: {exc}")
        raise self.retry(exc=exc)