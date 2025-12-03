import pytest
from todo.models import ProductionOrder, ProductionOrderItem

# Декоратор дает доступ к базе данных (без него тесты упадут)
@pytest.mark.django_db
def test_production_order_status_logic(product):
    """
    Проверяем, что статус заказа меняется от 'Ожидает' до 'Выполнен'
    в зависимости от строк.
    """
    # 1. Создаем заказ
    order = ProductionOrder.objects.create(
        customer="Рога и Копыта",
        due_date="2025-12-31"
    )
    
    # Изначально статус должен быть PENDING
    assert order.status == ProductionOrder.Status.PENDING

    # 2. Создаем строку заказа
    item = ProductionOrderItem.objects.create(
        production_order=order,
        product=product,
        quantity_requested=10
    )

    # 3. Имитируем, что задание запланировали (quantity_planned > 0)
    item.quantity_planned = 10
    item.save()
    item.update_status() # Это должно дернуть order.update_status()

    # Проверяем, что статус заказа стал PLANNED
    order.refresh_from_db()
    assert order.status == ProductionOrder.Status.PLANNED

    # 4. Имитируем частичное производство (сделали 5 из 10)
    item.quantity_produced = 5
    item.save()
    item.update_status()

    # Проверяем статус PARTIAL
    order.refresh_from_db()
    assert order.status == ProductionOrder.Status.PARTIAL

    # 5. Имитируем полное выполнение (10 из 10)
    item.quantity_produced = 10
    item.save()
    item.update_status()

    # Проверяем статус COMPLETED
    order.refresh_from_db()
    assert order.status == ProductionOrder.Status.COMPLETED