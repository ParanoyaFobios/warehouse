import requests
from django.conf import settings
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Product

STATUS_SHIPPED = 8
STATUS_COMPLETED = 12
CANCEL_STATUSES = [19, 27, 13]

class KeyCRMWebhookView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        event = data.get('event', '')
        context = data.get('context', {})
        
        # Обрабатываем только смену статуса, чтобы не делать лишних запросов на order.created
        if event == "order.change_status" or "order" in event:
            order_id = context.get('id')
            new_status_id = context.get('status_id')
            
            if not order_id:
                return Response({"error": "No order ID"}, status=400)

            # Получаем состав заказа через API
            products_in_order = self.get_order_products(order_id)
            
            if not products_in_order:
                print(f"!!! Заказ {order_id} пуст или не удалось получить товары")
                return Response({"status": "no products found"}, status=200)

            # Вызываем логику (теперь передаем только нужные 2 аргумента)
            self.process_stock_logic(products_in_order, new_status_id)
            
            return Response({"status": "processed"}, status=200)

        return Response({"status": "ignored event"}, status=200)

    def get_order_products(self, order_id):
        url = f"https://openapi.keycrm.app/v1/order/{order_id}?include=products"
        headers = {
            "Authorization": f"Bearer {settings.KEYCRM_API_KEY}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                # В KeyCRM товары лежат в ключе 'products' корня объекта заказа
                return response.json().get('products', [])
        except Exception as e:
            print(f"Ошибка при запросе заказа {order_id}: {e}")
        return []

    def process_stock_logic(self, products, current_status):
        """Управляет остатками, используя глобальные константы"""
        with transaction.atomic():
            for item in products:
                # Проверка SKU в самом продукте или в оффере
                sku = item.get('sku') or (item.get('offer') and item.get('offer').get('sku'))
                qty = int(item.get('quantity', 0))
                
                if not sku: 
                    continue
                
                # Используем select_for_update(), чтобы заблокировать строку в базе на время транзакции
                # Это предотвратит "состояние гонки", если придет два хука одновременно
                product = Product.objects.filter(sku=sku).select_for_update().first()
                if not product: 
                    continue
                
                changed_fields = []

                if current_status == STATUS_SHIPPED:
                    product.reserved_quantity += qty
                    changed_fields = ['reserved_quantity']
                    print(f"Резерв для {sku}: +{qty}")

                elif current_status == STATUS_COMPLETED:
                    # Списание общего остатка
                    if product.total_quantity >= qty:
                        product.total_quantity -= qty
                    else:
                        product.total_quantity = 0 # Защита от минуса
                    
                    # Обязательное снятие резерва
                    if product.reserved_quantity >= qty:
                        product.reserved_quantity -= qty
                    else:
                        product.reserved_quantity = 0
                        
                    changed_fields = ['total_quantity', 'reserved_quantity']
                    print(f"Продано: {sku} -{qty}, резерв снят")

                elif current_status in CANCEL_STATUSES:
                    # Просто возвращаем из резерва в доступные (уменьшаем резерв)
                    if product.reserved_quantity >= qty:
                        product.reserved_quantity -= qty
                    else:
                        product.reserved_quantity = 0
                    
                    changed_fields = ['reserved_quantity']
                    print(f"Резерв снят (отмена) для {sku}")

                if changed_fields:
                    # update_fields позволит сигналу проигнорировать это сохранение
                    product.save(update_fields=changed_fields)