import pytest
from django.contrib.auth.models import User
from decimal import Decimal
from warehouse2.models import Product, Sender
from todo.models import ProductionOrder, ProductionOrderItem, WorkOrder
from warehouse1.models import MaterialCategory, UnitOfMeasure, MaterialColor, Material, OperationOutgoingCategory, MaterialOperation
from warehouse2.models import (Product, Sender, ProductCategory, Package, ProductOperation,
    generate_product_barcode, generate_package_barcode, Shipment, ShipmentItem)

# Фикстура для создания юзера
@pytest.fixture
def user():
    return User.objects.create_user(username='testuser', password='password')

# Фикстура для создания товара
@pytest.fixture
def product():
    return Product.objects.create(
        name="Тестовая Подушка",
        sku="TEST-SKU-001",
        barcode="123456789",
        total_quantity=100
    )

# Фикстура для создания клиента (браузера)
@pytest.fixture
def client():
    from django.test.client import Client
    return Client()

@pytest.fixture
def base_sender():
    """Создает базового отправителя, необходимого для создания Shipment."""
    # Создаем Sender с pk=1, так как он используется во вьюхе CreateShipmentFromOrderView
    return Sender.objects.create(pk=1, name="Основной ФОП", full_name="ООО Ромашка")

@pytest.fixture
def production_order(product):
    """
    Создает готовый ProductionOrder с одной строкой (item).
    По умолчанию: запрошено 50 шт., ничего не запланировано.
    """
    order = ProductionOrder.objects.create(
        customer="Тестовый Заказчик А",
        due_date="2026-03-01",
        comment="Срочный заказ"
    )
    ProductionOrderItem.objects.create(
        production_order=order,
        product=product,
        quantity_requested=50
    )
    return order

@pytest.fixture
def planned_work_order(production_order, product):
    """
    Создает готовый WorkOrder (Задание на смену).
    Заказ Портфеля -> Строка Заказа -> Задание на смену.
    По умолчанию: запланировано 10 шт.
    """
    # Получаем строку заказа, созданную в фикстуре production_order
    order_item = production_order.items.first()
    
    # Имитируем, что это количество было "запланировано" (quantity_planned)
    order_item.quantity_planned = 10
    order_item.save()
    
    work_order = WorkOrder.objects.create(
        order_item=order_item,
        product=product,
        quantity_planned=10, # Запланировано 10 к производству
        status=WorkOrder.Status.NEW
    )
    return work_order

@pytest.fixture
def material_category():
    """Фикстура для категории материалов"""
    return MaterialCategory.objects.create(
        name="Тестовая категория"
    )

@pytest.fixture
def unit_of_measure():
    """Фикстура для единицы измерения"""
    return UnitOfMeasure.objects.create(
        name="Килограмм",
        short_name="кг"
    )

@pytest.fixture
def material_color():
    """Фикстура для цвета материала"""
    return MaterialColor.objects.create(
        name="Белый"
    )

@pytest.fixture
def operation_outgoing_category():
    """Фикстура для категории выдачи"""
    return OperationOutgoingCategory.objects.create(
        name="Производство"
    )

@pytest.fixture
def material(material_category, unit_of_measure, material_color):
    """Фикстура для материала"""
    return Material.objects.create(
        name="Тестовый материал",
        article="TEST-MAT-001",
        category=material_category,
        quantity=Decimal('100.00'),
        min_quantity=Decimal('10.00'),
        color=material_color,
        unit=unit_of_measure,
        description="Тестовое описание материала"
    )

@pytest.fixture
def material_operation_incoming(user, material):
    """Фикстура для операции прихода материала"""
    return MaterialOperation.objects.create(
        material=material,
        operation_type='incoming',
        quantity=50.00,
        user=user,
        comment="Тестовый приход"
    )

@pytest.fixture
def material_operation_outgoing(user, material, operation_outgoing_category):
    """Фикстура для операции расхода материала"""
    return MaterialOperation.objects.create(
        material=material,
        operation_type='outgoing',
        outgoing_category=operation_outgoing_category,
        quantity=20.00,
        user=user,
        comment="Тестовый расход"
    )

# фикстуры для приложения warehouse2

@pytest.fixture
def product_category():
    """Фикстура для категории продукции"""
    return ProductCategory.objects.create(
        name="Тестовая категория продукции"
    )

@pytest.fixture
def product(product_category):
    """Фикстура для продукта"""
    return Product.objects.create(
        name="Тестовая Подушка",
        sku="TEST-SKU-001",
        barcode="123456789012",
        category=product_category,
        price=1000.00,
        color="Красный",
        total_quantity=100,
        reserved_quantity=20
    )

@pytest.fixture
def product_without_category():
    """Фикстура для продукта без категории"""
    return Product.objects.create(
        name="Продукт без категории",
        sku="NO-CAT-001",
        barcode="987654321098",
        price=500.00,
        total_quantity=50,
        reserved_quantity=5
    )

@pytest.fixture
def package(product):
    """Фикстура для упаковки"""
    return Package.objects.create(
        name="Тестовая упаковка",
        product=product,
        quantity=10
    )

@pytest.fixture
def product_operation_incoming(user, product):
    """Фикстура для операции прихода продукции"""
    from django.contrib.contenttypes.models import ContentType
    
    # Создаем "источник" операции - например, инвентаризацию
    class MockSource:
        id = 1
    
    content_type = ContentType.objects.get(app_label='warehouse2', model='product')
    
    operation = ProductOperation.objects.create(
        product=product,
        operation_type=ProductOperation.OperationType.INCOMING,
        quantity=50,
        content_type=content_type,
        object_id=1,
        user=user,
        comment="Тестовый приход продукции"
    )
    return operation

@pytest.fixture
def product_operation_shipment(user, product):
    """Фикстура для операции отгрузки продукции"""
    from django.contrib.contenttypes.models import ContentType
    
    content_type = ContentType.objects.get(app_label='warehouse2', model='product')
    
    operation = ProductOperation.objects.create(
        product=product,
        operation_type=ProductOperation.OperationType.SHIPMENT,
        quantity=20,
        content_type=content_type,
        object_id=2,
        user=user,
        comment="Тестовая отгрузка"
    )
    return operation

@pytest.fixture
def sender():
    """Фикстура для отправителя"""
    return Sender.objects.create(
        name="Тестовый ФОП"
    )

@pytest.fixture
def shipment(user, sender):
    """Фикстура для отгрузки"""
    return Shipment.objects.create(
        created_by=user,
        sender=sender,
        destination="Тестовый адрес",
        recipient="Тестовый получатель",
        status='pending'
    )

@pytest.fixture
def shipment_item_product(shipment, product):
    """Фикстура для позиции отгрузки с продуктом"""
    return ShipmentItem.objects.create(
        shipment=shipment,
        product=product,
        quantity=5,
        price=product.price
    )

@pytest.fixture
def shipment_item_package(shipment, package):
    """Фикстура для позиции отгрузки с упаковкой"""
    return ShipmentItem.objects.create(
        shipment=shipment,
        package=package,
        quantity=2,
        price=package.price
    )