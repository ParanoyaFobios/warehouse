import pytest
import json
from django.urls import reverse
from todo.models import WorkOrder, ProductionOrder, ProductionOrderItem
from django.utils import timezone
from datetime import timedelta
from django.contrib.messages import get_messages
from warehouse2.models import Shipment, Sender, Product


@pytest.mark.django_db
def test_report_production_success(client, user, product):
    """Тест успешного отчета о производстве."""
    client.force_login(user)
    
    # 1. Создаем задание на смену
    work_order = WorkOrder.objects.create(
        product=product,
        quantity_planned=10,
        status=WorkOrder.Status.NEW
    )
    
    url = reverse('workorder_report', kwargs={'pk': work_order.pk})
    
    # 2. Отправляем отчет: сделали 5 штук
    response = client.post(url, {'quantity_done': 5})
    
    # 3. Проверки
    assert response.status_code == 302 # Редирект
    
    work_order.refresh_from_db()
    assert work_order.quantity_produced == 5
    assert work_order.status == WorkOrder.Status.IN_PROGRESS
    
    # Проверка склада
    product.refresh_from_db()
    # Было 100 (из фикстуры) + 5 произведено = 105
    assert product.total_quantity == 105

@pytest.mark.django_db
def test_report_production_complete(client, user, product):
    """Тест полного выполнения задания."""
    client.force_login(user)
    work_order = WorkOrder.objects.create(product=product, quantity_planned=10)
    
    url = reverse('workorder_report', kwargs={'pk': work_order.pk})
    client.post(url, {'quantity_done': 10})
    
    work_order.refresh_from_db()
    assert work_order.status == WorkOrder.Status.COMPLETED
    assert work_order.completed_at is not None


@pytest.mark.django_db
def test_create_order_via_json(client, user, product):
    """
    Тест проверяет, что отправка JSON в скрытом поле реально создает заказ и строки.
    """
    # 1. Логинимся (так как view требует LoginRequiredMixin)
    client.force_login(user)

    # 2. Готовим данные
    url = reverse('portfolio_create') # Убедись, что name в urls.py такой же
    
    # Это тот JSON, который собирает JavaScript на фронте
    items_data = [
        {"id": product.id, "qty": 50}
    ]
    
    form_data = {
        'customer': 'Тестовый Клиент',
        'due_date': '2025-10-10',
        'comment': 'Срочно!',
        'items_data': json.dumps(items_data) # Эмулируем скрытый инпут
    }

    # 3. Делаем POST запрос
    response = client.post(url, form_data)

    # 4. Проверки
    # Должен быть редирект (код 302) на список
    assert response.status_code == 302 
    
    # Проверяем, что в БД реально создался заказ
    assert ProductionOrder.objects.count() == 1
    order = ProductionOrder.objects.first()
    assert order.customer == 'Тестовый Клиент'
    
    # Проверяем, что создались строки (Items)
    assert order.items.count() == 1
    item = order.items.first()
    assert item.product == product
    assert item.quantity_requested == 50

@pytest.mark.django_db
def test_workorder_list_filter_by_date(client, user, product):
    """Тест фильтрации заданий по дате заказа."""
    client.force_login(user)
    
    # Дата 1: Сегодня
    date1 = timezone.now().date()
    order1 = ProductionOrder.objects.create(due_date=date1)
    item1 = ProductionOrderItem.objects.create(production_order=order1, product=product, quantity_requested=10)
    wo1 = WorkOrder.objects.create(order_item=item1, product=product, quantity_planned=10)
    
    # Дата 2: Завтра
    date2 = date1 + timedelta(days=1)
    order2 = ProductionOrder.objects.create(due_date=date2)
    item2 = ProductionOrderItem.objects.create(production_order=order2, product=product, quantity_requested=10)
    wo2 = WorkOrder.objects.create(order_item=item2, product=product, quantity_planned=10)
    
    url = reverse('workorder_list')
    
    # 1. Запрос без фильтров (должен вернуть оба, если они активны)
    response = client.get(url)
    assert len(response.context['workorders']) == 2
    
    # 2. Фильтр по дате 1
    response = client.get(url, {'due_date': str(date1)})
    workorders = response.context['workorders']
    assert len(workorders) == 1
    assert workorders[0] == wo1
    
    # 3. Фильтр по дате 2
    response = client.get(url, {'due_date': str(date2)})
    workorders = response.context['workorders']
    assert len(workorders) == 1
    assert workorders[0] == wo2

@pytest.mark.django_db
def test_create_shipment_from_order(client, user, product):
    """Тест создания отгрузки из выполненного заказа."""
    client.force_login(user)
    
    # Создаем отправителя по умолчанию (чтобы вьюха не упала)
    Sender.objects.create(name="Test Sender")
    
    # 1. Подготовка: Заказ, который частично выполнен
    # На складе должно быть достаточно товара!
    # Фикстура product дает 100 шт.
    
    order = ProductionOrder.objects.create(customer="Customer X", due_date="2025-01-01")
    item = ProductionOrderItem.objects.create(
        production_order=order, product=product, quantity_requested=20
    )
    
    # Имитируем производство (чтобы total_produced > 0)
    # Напрямую меняем поле, т.к. нас интересует только логика создания отгрузки
    item.quantity_produced = 10
    item.save()
    
    url = reverse('portfolio_create_shipment', kwargs={'pk': order.pk})
    
    # 2. Вызов (POST запрос)
    response = client.post(url)
    
    # 3. Проверки
    assert response.status_code == 302 # Редирект на shipment_detail
    
    # Должна создаться 1 отгрузка
    assert Shipment.objects.count() == 1
    shipment = Shipment.objects.first()
    assert shipment.destination == "Customer X"
    assert shipment.status == 'pending'
    
    # В отгрузке должна быть 1 позиция
    assert shipment.items.count() == 1
    shipment_item = shipment.items.first()
    assert shipment_item.product == product
    # Внимание: логика вьюхи берет min(запрошено, доступно)
    # Запрошено 20, доступно 100 -> берет 20.
    # НО мы в item.quantity_produced написали 10.
    # Вьюха смотрит на item.quantity_requested (20). 
    # Если на складе есть 20, она создаст на 20.
    assert shipment_item.quantity == 20



# ============================================================================
# Тесты для ProductionOrderUpdateView
# ============================================================================

class TestProductionOrderUpdateView:
    """Тесты для обновления ProductionOrder"""

    @pytest.mark.django_db
    def test_get_update_view_authenticated(self, client, user, production_order):
        """Тест GET-запроса на страницу обновления заказа"""
        client.force_login(user)
        # ИСПРАВЛЕНО ИМЯ URL: 'portfolio_edit'
        url = reverse('portfolio_edit', kwargs={'pk': production_order.pk})
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'existing_items_json' in response.context
        # Проверяем вхождение имени шаблона, так как response.templates возвращает список объектов
        assert 'todo/portfolio_order_form.html' in [t.name for t in response.templates]
        
        # Проверяем, что JSON корректно сформирован
        json_data = json.loads(response.context['existing_items_json'])
        assert len(json_data) == 1
        assert json_data[0]['name'] == production_order.items.first().product.name

    @pytest.mark.django_db
    def test_get_update_view_unauthenticated(self, client, production_order):
        """Тест GET-запроса без авторизации (должен перенаправить на логин)"""
        # ИСПРАВЛЕНО ИМЯ URL
        url = reverse('portfolio_edit', kwargs={'pk': production_order.pk})
        
        response = client.get(url)
        
        assert response.status_code == 302 
        assert response.url.startswith('login/')

    @pytest.mark.django_db
    def test_update_order_valid_data(self, client, user, production_order, product):
        """Тест успешного обновления заказа с новыми данными"""
        client.force_login(user)
        url = reverse('portfolio_edit', kwargs={'pk': production_order.pk})
        
        # Создаем второй продукт для теста
        product2 = Product.objects.create(
            name="Тестовый Продукт 2",
            sku="TEST-SKU-002",
            barcode="987654321",
            total_quantity=200
        )
        
        # Подготавливаем данные для обновления
        items_data = [
            {
                'pk': production_order.items.first().pk,  # Обновляем существующую строку
                'id': product.pk,
                'name': product.name,
                'sku': product.sku,
                'qty': 30,  # Меняем количество
                'available_quantity': 100
            },
            {
                'pk': None,  # Новая строка
                'id': product2.pk,
                'name': product2.name,
                'sku': product2.sku,
                'qty': 20,
                'available_quantity': 200
            }
        ]
        
        post_data = {
            'customer': 'Обновленный Заказчик',
            'due_date': '2026-04-01',
            'comment': 'Обновленный комментарий',
            'items_data': json.dumps(items_data)
        }
        
        response = client.post(url, post_data, follow=True)
        
        # Проверяем редирект
        assert response.status_code == 200
        assert response.redirect_chain[-1][0] == reverse('portfolio_list')
        
        # Проверяем сообщение об успехе
        messages = list(get_messages(response.wsgi_request))
        assert any('успешно обновлен' in str(message) for message in messages)
        
        # Проверяем обновленные данные
        production_order.refresh_from_db()
        assert production_order.customer == 'Обновленный Заказчик'
        assert str(production_order.due_date) == '2026-04-01'
        
        # Проверяем строки заказа
        items = production_order.items.all()
        assert items.count() == 2
        
        # Проверяем обновленную строку
        updated_item = items.get(product=product)
        assert updated_item.quantity_requested == 30
        
        # Проверяем новую строку
        new_item = items.get(product=product2)
        assert new_item.quantity_requested == 20

    @pytest.mark.django_db
    def test_update_order_remove_item_no_production(self, client, user, production_order, product):
        """Тест удаления строки, по которой нет производства"""
        client.force_login(user)
        url = reverse('portfolio_edit', kwargs={'pk': production_order.pk})
        
        post_data = {
            'customer': 'Заказчик',
            'due_date': '2026-03-01',
            'comment': 'Комментарий',
            'items_data': json.dumps([])  # Пустой список
        }
        
        response = client.post(url, post_data, follow=True)
        
        production_order.refresh_from_db()
        assert production_order.items.count() == 0

    @pytest.mark.django_db
    def test_update_order_cannot_remove_item_with_planned_production(self, client, user, production_order, product):
        """Тест попытки удаления строки, по которой уже есть запланированное производство"""
        client.force_login(user)
        url = reverse('portfolio_edit', kwargs={'pk': production_order.pk})
        
        # Создаем WorkOrder для этой строки
        order_item = production_order.items.first()
        order_item.quantity_planned = 10 
        order_item.save()
        
        WorkOrder.objects.create(
            order_item=order_item,
            product=product,
            quantity_planned=10,
            status=WorkOrder.Status.NEW
        )
        
        post_data = {
            'customer': 'Заказчик',
            'due_date': '2026-03-01',
            'comment': 'Комментарий',
            'items_data': json.dumps([]) 
        }
        
        response = client.post(url, post_data, follow=True)
        
        production_order.refresh_from_db()
        # Строка НЕ должна удалиться
        assert production_order.items.count() == 1
        
        messages = list(get_messages(response.wsgi_request))
        # Проверяем наличие предупреждения (case insensitive)
        assert any('не удалось удалить' in str(message).lower() for message in messages)

# ============================================================================
# Тесты для PlanWorkOrdersView
# ============================================================================

class TestPlanWorkOrdersView:
    """Тесты для создания WorkOrders из ProductionOrder"""

    @pytest.mark.django_db
    def test_get_plan_view_authenticated(self, client, user, production_order):
        client.force_login(user)
        url = reverse('portfolio_plan_workorders', kwargs={'pk': production_order.pk})
        
        response = client.get(url)
        
        assert response.status_code == 200
        assert 'order' in response.context
        assert 'lines_to_plan' in response.context
        assert 'todo/plan_workorders_form.html' in [t.name for t in response.templates]
        
        assert response.context['lines_to_plan'].count() == 1
        line = response.context['lines_to_plan'].first()
        assert line.remaining_to_plan == 50

    @pytest.mark.django_db
    def test_plan_workorders_success(self, client, user, production_order, product):
        client.force_login(user)
        url = reverse('portfolio_plan_workorders', kwargs={'pk': production_order.pk})
        
        response = client.post(url, follow=True)
        
        assert response.status_code == 200
        assert response.redirect_chain[-1][0] == reverse('portfolio_detail', kwargs={'pk': production_order.pk})
        
        messages = list(get_messages(response.wsgi_request))
        assert any('успешно создано' in str(message).lower() for message in messages)
        
        work_orders = WorkOrder.objects.filter(order_item__production_order=production_order)
        assert work_orders.count() == 1
        
        work_order = work_orders.first()
        assert work_order.quantity_planned == 50
        assert work_order.status == WorkOrder.Status.NEW
        
        order_item = production_order.items.first()
        order_item.refresh_from_db()
        assert order_item.quantity_planned == 50
        assert order_item.status == ProductionOrderItem.Status.PLANNED
        
        production_order.refresh_from_db()
        assert production_order.status == ProductionOrder.Status.PLANNED

    @pytest.mark.django_db
    def test_plan_workorders_atomic_transaction(self, client, user, production_order, mocker):
        """Тест атомарности (требует pip install pytest-mock)"""
        client.force_login(user)
        url = reverse('portfolio_plan_workorders', kwargs={'pk': production_order.pk})
        
        # Mocking managers напрямую сложен, лучше мокать метод save модели или create менеджера
        original_create = WorkOrder.objects.create
        call_count = 0
        
        def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  
                raise Exception("DB Error")
            return original_create(**kwargs)
        

        mocker.patch.object(WorkOrder.objects, 'create', side_effect=mock_create)
        
        product2 = Product.objects.create(name="P2", sku="S2", total_quantity=100)
        ProductionOrderItem.objects.create(production_order=production_order, product=product2, quantity_requested=75)
        
        try:
            client.post(url, follow=True)
        except Exception:
            pass # Ожидаем, что вьюха упадет с ошибкой (или обработает её)
        
        # Если транзакция сработала, то ни один WorkOrder не должен остаться
        # Так как второй упал, первый должен был откатиться
        assert WorkOrder.objects.filter(order_item__production_order=production_order).count() == 0
        
        # Статусы должны остаться прежними
        for item in production_order.items.all():
            item.refresh_from_db()
            assert item.quantity_planned == 0