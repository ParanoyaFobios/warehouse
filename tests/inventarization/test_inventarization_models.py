import pytest
from django.db import IntegrityError
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from inventarization.models import InventoryCount, InventoryCountItem
from warehouse2.models import Product  # Используем для тестов связи

# ----------------------------------------------------------------------------
# Фикстуры для инвентаризации
# ----------------------------------------------------------------------------

@pytest.fixture
def inventory_count(user):
    """Фикстура: создает активную сессию переучета"""
    return InventoryCount.objects.create(
        user=user,
        notes="Тестовая инвентаризация"
    )

# ----------------------------------------------------------------------------
# Тесты модели InventoryCount (Шапка)
# ----------------------------------------------------------------------------

@pytest.mark.django_db
class TestInventoryCountModel:
    
    def test_create_inventory_count_defaults(self, user):
        """Тест создания переучета с дефолтными значениями"""
        count = InventoryCount.objects.create(user=user)
        
        assert count.pk is not None
        assert count.status == InventoryCount.Status.IN_PROGRESS
        assert count.created_at is not None
        assert count.completed_at is None
        assert count.notes == ""

    def test_inventory_count_str_representation(self, inventory_count):
        """Тест строкового представления (__str__)"""
        date_str = inventory_count.created_at.strftime('%d.%m.%Y')
        expected_str = f"Переучет №{inventory_count.id} от {date_str}"
        assert str(inventory_count) == expected_str

    def test_status_choices(self):
        """Проверка, что статусы соответствуют ожидаемым"""
        assert InventoryCount.Status.IN_PROGRESS == 'in_progress'
        assert InventoryCount.Status.COMPLETED == 'completed'
        assert InventoryCount.Status.RECONCILED == 'reconciled'


# ----------------------------------------------------------------------------
# Тесты модели InventoryCountItem (Позиции и Расчеты)
# ----------------------------------------------------------------------------

@pytest.mark.django_db
class TestInventoryCountItemModel:

    def test_create_item_with_generic_relation(self, inventory_count, product):
        """
        Тест создания позиции и работы GenericForeignKey.
        Проверяем, что item правильно ссылается на product.
        """
        # Получаем ContentType для модели Product
        product_ct = ContentType.objects.get_for_model(product)
        
        item = InventoryCountItem.objects.create(
            inventory_count=inventory_count,
            content_type=product_ct,
            object_id=product.pk,
            system_quantity=10,
            actual_quantity=10
        )
        
        assert item.pk is not None
        # Проверяем, что через generic поле мы получаем наш продукт
        assert item.content_object == product
        assert item.content_object.name == product.name

    def test_variance_calculation_exact(self, inventory_count, product):
        """Тест расчета расхождения: Факт равен Системе (0)"""
        item = InventoryCountItem.objects.create(
            inventory_count=inventory_count,
            content_object=product, # Django позволяет передавать объект напрямую, если настроено, но лучше через CT
            system_quantity=10,
            actual_quantity=10
        )
        # 10 - 10 = 0
        assert item.variance == 0

    def test_variance_calculation_surplus(self, inventory_count, product):
        """Тест расчета расхождения: Излишек (Факт > Система)"""
        item = InventoryCountItem.objects.create(
            inventory_count=inventory_count,
            content_object=product,
            system_quantity=10,
            actual_quantity=15
        )
        # 15 - 10 = +5
        assert item.variance == 5

    def test_variance_calculation_deficit(self, inventory_count, product):
        """Тест расчета расхождения: Недостача (Факт < Система)"""
        item = InventoryCountItem.objects.create(
            inventory_count=inventory_count,
            content_object=product,
            system_quantity=10,
            actual_quantity=8
        )
        # 8 - 10 = -2
        assert item.variance == -2

    def test_unique_together_constraint(self, inventory_count, product):
        """
        Тест уникальности: нельзя добавить один и тот же товар 
        дважды в один переучет.
        """
        # Создаем первую запись
        InventoryCountItem.objects.create(
            inventory_count=inventory_count,
            content_object=product,
            system_quantity=5,
            actual_quantity=5
        )

        # Пытаемся создать вторую запись с тем же товаром и тем же переучетом
        with pytest.raises(IntegrityError):
            InventoryCountItem.objects.create(
                inventory_count=inventory_count,
                content_object=product,
                system_quantity=10,
                actual_quantity=10
            )

    def test_item_str_representation(self, inventory_count, product):
        """Тест строкового представления позиции"""
        item = InventoryCountItem.objects.create(
            inventory_count=inventory_count,
            content_object=product,
            system_quantity=10,
            actual_quantity=12
        )
        # Ожидаем: "ИмяПродукта - Факт: 12"
        assert str(item) == f"{product.name} - Факт: 12"

    def test_work_with_different_models(self, inventory_count, product):
        """
        Тест (концептуальный): GenericForeignKey должен работать и с Material 
        (если он есть в фикстурах, но проверим хотя бы принцип).
        """
        # Допустим, у нас есть Material из warehouse1
        # from warehouse1.models import Material
        # material = Material.objects.create(...)
        
        # Для теста просто используем тот факт, что мы можем создать item
        # привязав его к Product, и это работает.
        # Главное, что мы используем content_type.
        
        assert inventory_count.items.count() == 0
        
        InventoryCountItem.objects.create(
            inventory_count=inventory_count,
            content_object=product,
            system_quantity=5
        )
        
        assert inventory_count.items.count() == 1
        assert inventory_count.items.first().content_object == product