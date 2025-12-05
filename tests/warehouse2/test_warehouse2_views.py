import pytest
import json
from decimal import Decimal
from django.urls import reverse
from django.contrib.messages import get_messages
from warehouse2.models import Product, ProductOperation, Shipment, ShipmentItem, Package, Sender

# ==============================================================================
# Тесты для Product Views (Бизнес-логика)
# ==============================================================================

@pytest.mark.django_db
class TestProductViewsLogic:
    
    def test_product_create_view_success(self, client, user, product_category):
        """Тест успешного создания продукта через форму."""
        client.force_login(user)
        url = reverse('product_create')
        
        form_data = {
            'name': 'Новый Продукт',
            'sku': 'NEW-SKU-001',
            'category': product_category.pk,
            'price': '150.00',
            # Остальные поля опциональны
        }
        
        response = client.post(url, form_data, follow=True)
        
        assert response.status_code == 200
        assert Product.objects.filter(sku='NEW-SKU-001').exists()
        
        messages = list(get_messages(response.wsgi_request))
        assert any('успешно создан' in str(m) for m in messages)

    def test_product_incoming_view_logic(self, client, user, product):
        """
        Тест логики поступления товара (ProductIncomingView):
        1. Увеличение total_quantity.
        2. Создание ProductOperation (INCOMING).
        """
        client.force_login(user)
        url = reverse('product_incoming')
        
        initial_qty = product.total_quantity
        incoming_qty = 50
        
        form_data = {
            'product': product.pk, # ID продукта (скрытое поле)
            'quantity': incoming_qty,
            'comment': 'Поступление от поставщика А'
        }
        
        response = client.post(url, form_data, follow=True)
        
        assert response.status_code == 200
        
        # Проверка обновления продукта
        product.refresh_from_db()
        assert product.total_quantity == initial_qty + incoming_qty
        
        # Проверка создания операции
        operation = ProductOperation.objects.last()
        assert operation.product == product
        assert operation.operation_type == ProductOperation.OperationType.INCOMING
        assert operation.quantity == incoming_qty
        assert operation.comment == 'Поступление от поставщика А'

    def test_product_search_json_logic(self, client, user, product):
        """Тест JSON поиска (product_search_json) для автокомплита."""
        client.force_login(user)
        url = reverse('product_search_json')
        
        # 1. Поиск по части названия
        response = client.get(url, {'q': 'Тестовая'})
        assert response.status_code == 200
        data = json.loads(response.content)
        assert len(data['results']) >= 1
        assert data['results'][0]['id'] == product.id
        
        # 2. Поиск по артикулу
        response = client.get(url, {'q': product.sku})
        data = json.loads(response.content)
        assert len(data['results']) >= 1
        assert data['results'][0]['sku'] == product.sku

    def test_product_detail_create_package_logic(self, client, user, product):
        """
        Тест создания упаковки (Package) через детальную страницу продукта (ProductDetailView).
        """
        client.force_login(user)
        url = reverse('product_detail', kwargs={'pk': product.pk})
        
        form_data = {
            'name': 'Коробка (10 шт)',
            'quantity': 10
        }
        
        response = client.post(url, form_data, follow=True)
        
        assert response.status_code == 200
        assert Package.objects.filter(product=product, quantity=10).exists()
        
        messages = list(get_messages(response.wsgi_request))
        assert any('Упаковка на 10 шт. успешно создана' in str(m) for m in messages)


# ==============================================================================
# Тесты для Shipment Views (Бизнес-логика)
# ==============================================================================

@pytest.mark.django_db
class TestShipmentViewsLogic:

    def test_shipment_create_view(self, client, user, sender):
        """Тест создания пустой отгрузки (ShipmentCreateView)."""
        client.force_login(user)
        url = reverse('shipment_create')
        
        form_data = {
            'sender': sender.pk,
            'destination': 'Склад Клиента',
            'recipient': 'Иванов И.И.'
        }
        
        response = client.post(url, form_data, follow=True) # Должен редиректнуть на добавление товаров
        
        assert response.status_code == 200
        shipment = Shipment.objects.last()
        assert shipment.destination == 'Склад Клиента'
        assert shipment.created_by == user
        assert shipment.status == 'pending'
        
        # Проверяем, что редирект был на добавление товаров
        expected_url = reverse('shipment_items', kwargs={'pk': shipment.pk})
        assert response.redirect_chain[-1][0] == expected_url

    def test_shipment_items_view_add_product(self, client, user, shipment, product):
        """
        Тест добавления товара в отгрузку (ShipmentItemsView).
        Проверяем: создание ShipmentItem и резервирование товара.
        """
        client.force_login(user)
        url = reverse('shipment_items', kwargs={'pk': shipment.pk})
        
        # Убедимся, что на складе достаточно товара
        product.total_quantity = 100
        product.reserved_quantity = 0
        product.save()
        initial_qty = 5
        ShipmentItem.objects.create(
        shipment=shipment,
        product=product,
        quantity=initial_qty,
        # При создании item, его метод save() должен зарезервировать 5.
        # Если метод save() не вызывается автоматически, или логика резерва в нем,
        # нам нужно вызвать его явно, или убедиться, что логика резерва работает
    )
        product.refresh_from_db()
        # Форма принимает скрытый идентификатор 'product-ID'
        # Если мы полагаем, что логика резерва сработала:
        assert product.reserved_quantity == 5, "Резерв не сработал при создании ShipmentItem в тесте!"
        
        # --- Тестирование: Добавляем еще 10 ---
        added_qty = 10
        form_data = {
            'item_identifier': f'product-{product.id}',
            'quantity': added_qty # Добавляем 10
        }

        response = client.post(url, form_data, follow=True)
        assert response.status_code == 200

        # 1. Проверяем ОБНОВЛЕННЫЙ ShipmentItem
        item = ShipmentItem.objects.get(shipment=shipment, product=product)
        assert item.quantity == 15 # Должно стать 5 + 10

        # 2. Проверяем ОБНОВЛЕННЫЙ резерв
        product.refresh_from_db()
        # Теперь резерв должен быть 15
        assert product.reserved_quantity == 15

    def test_ship_shipment_view_logic(self, client, user, shipment, product):
        """
        Тест финальной отгрузки (ship_shipment).
        Проверяем: списание со склада, списание с резерва, смена статуса.
        """
        client.force_login(user)
        reserved_qty = 5
        product.total_quantity = 100
        product.reserved_quantity = 0 
        product.save()

        ShipmentItem.objects.create(
        shipment=shipment,
        product=product,
        quantity=reserved_qty,
        price=product.price
        ).save()
        
    # Проверяем, что резерв установлен (для отладки)
        product.refresh_from_db()
        assert product.reserved_quantity == reserved_qty
        
        # --- Выполнение отгрузки ---
        
        initial_total_qty = product.total_quantity
        
        url = reverse('shipment_ship', kwargs={'pk': shipment.pk})
        response = client.get(url, follow=True)

        # Убеждаемся, что отгрузка прошла
        assert response.status_code == 200
        
        # Проверяем сообщение об успехе (для дополнительной уверенности, что не попали в 'else')
        messages = list(get_messages(response.wsgi_request))
        assert any('успешно выполнена' in str(m) for m in messages)
        
        # 1. Проверка статуса отгрузки
        shipment.refresh_from_db()
        assert shipment.status == 'shipped' # 🟢 Должно пройти
        
        # 2. Проверка списания со склада и резерва
        product.refresh_from_db()
        assert product.total_quantity == initial_total_qty - reserved_qty
        assert product.reserved_quantity == 0
        
        # 3. Проверка журнала операций
        op = ProductOperation.objects.filter(
            operation_type=ProductOperation.OperationType.SHIPMENT, 
            product=product
        ).last()
        assert op is not None
        assert op.quantity == 5

    def test_return_shipment_view_logic(self, client, user, basic_shipment, product):
        """
        Тест возврата отгрузки (ReturnShipmentView).
        Проверяем: статус 'returned', возврат товара на баланс.
        """
        client.force_login(user)
        
        # Сначала нужно отгрузить (чтобы можно было вернуть)
        basic_shipment.ship(user) 
        # Теперь: total=95, status='shipped'
        
        url = reverse('shipment_return', kwargs={'pk': basic_shipment.pk})
        
        # Это POST запрос
        response = client.post(url, follow=True)
        
        assert response.status_code == 200
        
        # 1. Проверка статуса
        basic_shipment.refresh_from_db()
        assert basic_shipment.status == 'returned'
        
        # 2. Проверка возврата товара
        product.refresh_from_db()
        # Было 95. Вернули 5. Стало 100.
        assert product.total_quantity == 100
        
        # 3. Проверка операции RETURN
        op = ProductOperation.objects.filter(
            operation_type=ProductOperation.OperationType.RETURN,
            product=product
        ).last()
        assert op is not None
        assert op.quantity == 5

    def test_mark_shipment_as_packaged_logic(self, client, user, shipment):
        """Тест смены статуса на 'Собрано'."""
        client.force_login(user)
        assert shipment.status == 'pending'
        
        url = reverse('shipment_mark_packaged', kwargs={'pk': shipment.pk})
        response = client.post(url, follow=True)
        
        assert response.status_code == 200
        shipment.refresh_from_db()
        assert shipment.status == 'packaged'
        assert shipment.processed_by == user

    def test_delete_shipment_item_view_logic(self, client, user, basic_shipment, product):
        """
        Тест удаления позиции из отгрузки (delete_shipment_item).
        Проверяем: удаление ShipmentItem и снятие резерва.
        """
        client.force_login(user)
        
        # В basic_shipment есть 1 позиция (5 шт). Резерв = 5.
        item = basic_shipment.items.first()
        url = reverse('delete_shipment_item', kwargs={'pk': item.pk})
        
        response = client.post(url, follow=True) # View принимает и GET, и POST (обычно delete лучше через POST)
        # В вашем коде views.py: delete_shipment_item - это функция, она не проверяет метод, 
        # но лучше использовать POST форму в шаблоне. По коду это просто вызов delete().
        
        assert response.status_code == 200
        
        # 1. Проверяем удаление
        assert not ShipmentItem.objects.filter(pk=item.pk).exists()
        
        # 2. Проверяем снятие резерва
        product.refresh_from_db()
        assert product.reserved_quantity == 0

    def test_stock_search_logic(self, client, user, product):
        """
        Тест поиска доступных товаров для отгрузки (stock_search).
        """
        client.force_login(user)
        url = reverse('stock_search')
        
        # У продукта: total=100, reserved=5 (из фикстуры basic_shipment, если она использовалась, иначе 0)
        # В этом тесте мы не используем basic_shipment, значит reserved=0.
        product.total_quantity = 50
        product.reserved_quantity = 0
        product.save()
        
        # 1. Поиск штучного товара
        response = client.get(url, {'q': product.sku})
        assert response.status_code == 200
        data = json.loads(response.content)
        
        assert len(data['results']) >= 1
        res = data['results'][0]
        assert res['id'] == f"product-{product.id}"
        assert str(int(product.total_quantity)) in res['info'] # "Доступно: 50 шт."