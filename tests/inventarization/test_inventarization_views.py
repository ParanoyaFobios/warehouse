import pytest
import json
from django.urls import reverse
from django.contrib.messages import get_messages
from inventarization.models import InventoryCount, InventoryCountItem
from warehouse2.models import Product, ProductOperation
from warehouse1.models import Material, MaterialOperation

# ============================================================================
# 1. Тесты создания и управления процессом (StartInventoryCountView)
# ============================================================================

@pytest.mark.django_db
class TestStartInventoryCountView:
    
    def test_start_new_count(self, client, user):
        """Тест создания нового переучета."""
        client.force_login(user)
        url = reverse('count_start')
        
        response = client.post(url, follow=True)
        
        assert response.status_code == 200
        assert InventoryCount.objects.filter(user=user, status='in_progress').count() == 1
        
        # Проверяем редирект на страницу работы с переучетом
        count = InventoryCount.objects.first()
        expected_url = reverse('count_work', kwargs={'pk': count.pk})
        assert response.redirect_chain[-1][0] == expected_url

    def test_redirect_to_existing_count(self, client, user):
        """Тест редиректа на существующий активный переучет."""
        client.force_login(user)
        # Создаем активный переучет вручную
        existing_count = InventoryCount.objects.create(user=user, status='in_progress')
        
        url = reverse('count_start')
        response = client.post(url, follow=True)
        
        # Должен редиректнуть на СУЩЕСТВУЮЩИЙ, а не создать новый
        assert InventoryCount.objects.filter(user=user).count() == 1
        assert response.redirect_chain[-1][0] == reverse('count_work', kwargs={'pk': existing_count.pk})
        
        messages = list(get_messages(response.wsgi_request))
        assert any('уже есть незавершенный переучет' in str(m) for m in messages)


# ============================================================================
# 2. Тесты работы с позициями (InventoryCountWorkView)
# ============================================================================

@pytest.mark.django_db
class TestInventoryCountWorkView:
    
    @pytest.fixture
    def inventory_count(self, user):
        return InventoryCount.objects.create(user=user, status='in_progress')

    def test_add_product_item(self, client, user, inventory_count, product):
        """Тест добавления Продукта в переучет."""
        client.force_login(user)
        url = reverse('count_work', kwargs={'pk': inventory_count.pk})
        
        # Симулируем выбор продукта из автокомплита (product-ID)
        form_data = {
            'item_identifier': f'product-{product.id}',
            'quantity': 55
        }
        
        response = client.post(url, form_data, follow=True)
        assert response.status_code == 200
        
        # Проверяем создание позиции
        item = InventoryCountItem.objects.filter(inventory_count=inventory_count).first()
        assert item is not None
        assert item.content_object == product
        assert item.actual_quantity == 55
        # System quantity должно подтянуться из продукта
        assert item.system_quantity == product.available_quantity

    def test_update_existing_item(self, client, user, inventory_count, product):
        """Тест обновления количества, если товар уже добавлен."""
        client.force_login(user)
        url = reverse('count_work', kwargs={'pk': inventory_count.pk})
        
        # Сначала добавляем товар
        client.post(url, {'item_identifier': f'product-{product.id}', 'quantity': 10})
        
        # Потом добавляем тот же товар с новым количеством
        client.post(url, {'item_identifier': f'product-{product.id}', 'quantity': 20})
        
        assert InventoryCountItem.objects.count() == 1
        item = InventoryCountItem.objects.first()
        assert item.actual_quantity == 20 # Должно обновиться (update_or_create)

    def test_cannot_edit_completed_count(self, client, user, inventory_count, product):
        """Тест запрета редактирования завершенного переучета."""
        client.force_login(user)
        inventory_count.status = InventoryCount.Status.COMPLETED
        inventory_count.save()
        
        url = reverse('count_work', kwargs={'pk': inventory_count.pk})
        form_data = {'item_identifier': f'product-{product.id}', 'quantity': 10}
        
        response = client.post(url, form_data, follow=True)
        
        # Проверяем сообщение об ошибке
        messages = list(get_messages(response.wsgi_request))
        assert any('переучет завершен' in str(m) for m in messages)
        assert InventoryCountItem.objects.count() == 0


# ============================================================================
# 3. Тесты завершения и сверки (Complete & Reconcile)
# ============================================================================

@pytest.mark.django_db
class TestInventoryReconciliation:
    
    @pytest.fixture
    def completed_count(self, user, product, material):
        """Фикстура завершенного переучета с расхождениями."""
        # Создаем переучет
        count = InventoryCount.objects.create(user=user, status='completed')
        
        # 1. Продукт: Система 10, Факт 8 (Недостача -2)
        product.total_quantity = 10
        product.save()
        
        from django.contrib.contenttypes.models import ContentType
        ct_prod = ContentType.objects.get_for_model(product)
        InventoryCountItem.objects.create(
            inventory_count=count, content_type=ct_prod, object_id=product.pk,
            system_quantity=10, actual_quantity=8
        )
        
        # 2. Материал: Система 20, Факт 25 (Излишек +5)
        material.quantity = 20
        material.save()
        
        ct_mat = ContentType.objects.get_for_model(material)
        InventoryCountItem.objects.create(
            inventory_count=count, content_type=ct_mat, object_id=material.pk,
            system_quantity=20, actual_quantity=25
        )
        return count

    def test_complete_inventory_count_view_owner(self, client, user):
        """Тест смены статуса на COMPLETED владельцем."""
        client.force_login(user)
        count = InventoryCount.objects.create(user=user, status='in_progress')
        
        url = reverse('count_complete', kwargs={'pk': count.pk})
        response = client.post(url, follow=True)
        
        count.refresh_from_db()
        assert count.status == 'completed'
        assert count.completed_at is not None

    def test_complete_inventory_count_permissions(self, client, user, staff_user):
        """Тест прав доступа при завершении переучета."""
        # 1. Создаем переучет от имени user
        count = InventoryCount.objects.create(user=user, status='in_progress')
        
        # 2. Пытаемся завершить от имени staff_user (должен иметь право 'can_reconcile_inventory')
        client.force_login(staff_user)
        url = reverse('count_complete', kwargs={'pk': count.pk})
        response = client.post(url, follow=True)
        
        count.refresh_from_db()
        assert count.status == 'completed' # Staff с правом может завершать чужие переучеты
        
        # 3. Создаем еще один переучет
        count2 = InventoryCount.objects.create(user=user, status='in_progress')
        
        # 4. Создаем пользователя БЕЗ прав и не владельца
        from django.contrib.auth.models import User
        other_user = User.objects.create_user(username='other', password='pw')
        client.force_login(other_user)
        
        url2 = reverse('count_complete', kwargs={'pk': count2.pk})
        response = client.post(url2, follow=True)
        
        count2.refresh_from_db()
        assert count2.status == 'in_progress' # Не владелец и без прав - не может завершить
        messages = list(get_messages(response.wsgi_request))
        assert any('У вас нет прав' in str(m) for m in messages)

    def test_reconcile_view_permission_denied(self, client, user, completed_count):
        """Тест: обычный пользователь не имеет доступа к сверке (403)."""
        client.force_login(user) # Обычный юзер
        url = reverse('count_reconcile_action', kwargs={'pk': completed_count.pk})
        
        # Пытаемся сделать POST запрос
        response = client.post(url, {'item_id': 1})
        
        # PermissionRequiredMixin должен вернуть 403 Forbidden (или редирект на логин, зависит от настроек)
        # По умолчанию raise_exception = False -> редирект на login_url
        # Если вы хотите 403, добавьте raise_exception = True во View.
        # Проверим, что доступ закрыт (код не 200 и не 302 на успех)
        
        # В стандартной конфигурации LoginRequiredMixin + PermissionRequiredMixin без raise_exception=True
        # перенаправляет на страницу логина.
        assert response.status_code == 403 or response.status_code == 302

    def test_reconcile_product_deficit(self, client, staff_user, completed_count, product):
        """
        Тест сверки продукта (Недостача) пользователем с правами.
        """
        client.force_login(staff_user) # staff_user имеет право 'can_reconcile_inventory'
        
        item = completed_count.items.get(object_id=product.pk)
        url = reverse('count_reconcile_action', kwargs={'pk': completed_count.pk})
        
        response = client.post(url, {'item_id': item.pk}, follow=True)
        assert response.status_code == 200
        
        # 1. Проверка остатка
        product.refresh_from_db()
        assert product.total_quantity == 8 # Стало как по факту
        
        # 2. Проверка статуса позиции
        item.refresh_from_db()
        assert item.reconciliation_status == 'reconciled'
        
        # 3. Проверка операции
        op = ProductOperation.objects.filter(
            product=product, 
            operation_type=ProductOperation.OperationType.ADJUSTMENT
        ).last()
        assert op is not None
        assert op.quantity == -2 # Недостача

    def test_reconcile_material_surplus(self, client, staff_user, completed_count, material):
        """Тест сверки материала (Излишек)."""
        client.force_login(staff_user)
        
        item = completed_count.items.get(object_id=material.pk)
        url = reverse('count_reconcile_action', kwargs={'pk': completed_count.pk})
        
        client.post(url, {'item_id': item.pk}, follow=True)
        
        # 1. Проверка остатка
        material.refresh_from_db()
        assert material.quantity == 25 # Стало как по факту
        
        # 2. Проверка операции
        op = MaterialOperation.objects.filter(
            material=material, 
            operation_type='adjustment'
        ).last()
        assert op is not None
        assert op.quantity == 5 # Излишек

    def test_finalize_inventory_check_pending_items(self, client, staff_user, completed_count):
        """Тест: нельзя закрыть переучет, пока есть необработанные расхождения."""
        client.force_login(staff_user)
        url = reverse('count_finalize', kwargs={'pk': completed_count.pk})
        
        # Пытаемся закрыть сразу (items еще в pending)
        response = client.post(url, follow=True)
        
        # Должна быть ошибка
        messages = list(get_messages(response.wsgi_request))
        assert any('Не все позиции' in str(m) for m in messages)
        
        completed_count.refresh_from_db()
        assert completed_count.status == 'completed' # Не изменился

# ============================================================================
# 4. Тест поиска для инвентаризации (AJAX)
# ============================================================================

@pytest.mark.django_db
def test_inventory_stock_search(client, user, product):
    """Тест поиска товаров с отображением уже посчитанного количества."""
    client.force_login(user)
    
    # 1. Подготовка: переучет с 1 позицией (5 шт)
    count = InventoryCount.objects.create(user=user)
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(product)
    InventoryCountItem.objects.create(
        inventory_count=count, content_type=ct, object_id=product.pk,
        system_quantity=10, actual_quantity=5
    )
    
    url = reverse('inventory_stock_search')
    
    # 2. Поиск этого продукта в контексте этого переучета
    response = client.get(url, {
        'q': product.sku, 
        'inventory_count_id': count.pk
    })
    
    assert response.status_code == 200
    data = json.loads(response.content)
    
    assert len(data['results']) >= 1
    res = data['results'][0]
    
    # Главная проверка: в результатах поиска должно быть видно, что мы уже насчитали 5 шт.
    assert res['counted_quantity'] == 5
    assert "Посчитано: <strong>5 шт.</strong>" in res['info']