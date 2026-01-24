import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from warehouse2.models import (ProductCategory, Product, Package, ProductOperation,
    Sender, Shipment, ShipmentItem, generate_product_barcode, generate_package_barcode, generate_unique_barcode)
from django.test import override_settings


@pytest.mark.django_db
class TestProductCategoryModel:
    """Тесты для модели ProductCategory"""
    
    def test_create_product_category(self):
        """Тест создания категории продукции"""
        category = ProductCategory.objects.create(name="Подушки")
        
        assert category.pk is not None
        assert category.name == "Подушки"
        assert str(category) == "Подушки"
    
    def test_product_category_unique_name(self):
        """Тест уникальности названия категории"""
        ProductCategory.objects.create(name="Подушки")
        
        with pytest.raises(IntegrityError):
            ProductCategory.objects.create(name="Подушки")
    
    def test_product_category_verbose_names(self):
        """Тест verbose names"""
        assert ProductCategory._meta.verbose_name == "Категория продукции"
        assert ProductCategory._meta.verbose_name_plural == "Категории продукции"


@pytest.mark.django_db
class TestProductModel:
    """Тесты для модели Product"""
    
    def test_create_product(self, product_category):
        """Тест создания продукта"""
        product = Product.objects.create(
            name="Ортопедическая подушка",
            sku="PILLOW-001",
            barcode="123456789012",
            category=product_category,
            price=1500.50,
            color="Белый",
            total_quantity=200,
            reserved_quantity=30
        )
        
        assert product.pk is not None
        assert product.name == "Ортопедическая подушка"
        assert product.sku == "PILLOW-001"
        assert product.barcode == "123456789012"
        assert product.category == product_category
        assert product.price == Decimal('1500.50')
        assert product.color == "Белый"
        assert product.total_quantity == 200
        assert product.reserved_quantity == 30
    
    def test_create_product_without_category(self):
        """Тест создания продукта без категории (опциональное поле)"""
        product = Product.objects.create(
            name="Продукт без категории",
            sku="NO-CAT-001",
            barcode="987654321098",
            price=500.00,
            total_quantity=50
        )
        
        assert product.pk is not None
        assert product.category is None
    
    def test_product_unique_sku(self, product_category):
        """Тест уникальности артикула"""
        Product.objects.create(
            name="Продукт 1",
            sku="UNIQUE-001",
            barcode="111111111111",
            category=product_category,
            price=100,
            total_quantity=10
        )
        
        with pytest.raises(IntegrityError):
            Product.objects.create(
                name="Продукт 2",
                sku="UNIQUE-001",  # Дублирующий SKU
                barcode="222222222222",
                category=product_category,
                price=200,
                total_quantity=20
            )
    
    def test_product_unique_barcode(self, product_category):
        """Тест уникальности штрихкода"""
        Product.objects.create(
            name="Продукт 1",
            sku="PROD-001",
            barcode="123456789012",
            category=product_category,
            price=100,
            total_quantity=10
        )
        
        with pytest.raises(IntegrityError):
            Product.objects.create(
                name="Продукт 2",
                sku="PROD-002",
                barcode="123456789012",  # Дублирующий штрихкод
                category=product_category,
                price=200,
                total_quantity=20
            )
    
    def test_product_available_quantity_property(self, product):
        """Тест свойства available_quantity"""
        # total_quantity = 100, reserved_quantity = 20
        assert product.available_quantity == 80
        
        # Изменяем зарезервированное количество
        product.reserved_quantity = 40
        product.save()
        assert product.available_quantity == 60
        
        # Все зарезервировано
        product.reserved_quantity = 100
        product.save()
        assert product.available_quantity == 0
        
        # Больше зарезервировано, чем есть
        product.reserved_quantity = 120
        product.save()
        assert product.available_quantity == -20  # Отрицательное значение возможно
    
    def test_product_string_representation(self, product):
        """Тест строкового представления продукта"""
        assert str(product) == "[НЕТ TC] Тестовая Подушка (TEST-SKU-001)"
    
    def test_product_default_values(self, product_category):
        """Тест значений по умолчанию"""
        product = Product.objects.create(
            name="Продукт с дефолтами",
            sku="DEFAULT-001",
            barcode="999999999999",
            category=product_category
        )
        
        assert product.price == Decimal('0.00')
        assert product.total_quantity == 0
        assert product.reserved_quantity == 0
        assert product.color is None
        assert not product.image.name  # Пустое имя файла
    
    def test_product_verbose_names_and_permissions(self):
        """Тест verbose names и permissions"""
        assert Product._meta.verbose_name == "Штучный товар"
        assert Product._meta.verbose_name_plural == "Штучные товары"
        
        permissions = [perm[0] for perm in Product._meta.permissions]
        assert "can_view_product_quantity" in permissions
        assert "can_edit_product_price" in permissions
    
    def test_product_barcode_generation(self, product_category):
        """Тест автоматической генерации штрихкода"""
        product = Product.objects.create(
            name="Продукт с автоштрихкодом",
            sku="AUTO-BC-001",
            category=product_category,
            price=100
            # barcode не указан - должен сгенерироваться автоматически
        )
        
        assert product.barcode is not None
        assert len(product.barcode) == 15


@pytest.mark.django_db
class TestPackageModel:
    """Тесты для модели Package"""
    
    def test_create_package(self, product):
        """Тест создания упаковки"""
        package = Package.objects.create(
            name="Упаковка 10 штук",
            product=product,
            quantity=10
        )
        
        assert package.pk is not None
        assert package.name == "Упаковка 10 штук"
        assert package.product == product
        assert package.quantity == 10
        assert package.barcode is not None
        assert len(package.barcode) == 15
    
    def test_package_price_property(self, product):
        """Тест свойства price упаковки"""
        # Продукт стоит 1000, упаковка 10 штук
        package = Package.objects.create(
            name="Упаковка",
            product=product,
            quantity=10
        )
        
        assert package.price == Decimal('10000.00')  # 1000 * 10
        
        # Изменяем цену продукта
        product.price = Decimal('1500.00')
        product.save()
        
        # Свойство должно пересчитываться динамически
        assert package.price == Decimal('15000.00')  # 1500 * 10
    
    def test_package_available_packages_property(self, product):
        """Тест свойства available_packages"""
        # Продукт: total_quantity=100, reserved_quantity=20, available=80
        # Упаковка: quantity=10
        package = Package.objects.create(
            name="Упаковка",
            product=product,
            quantity=10
        )
        
        # Доступно 80 штук, в упаковке 10 штук -> 8 упаковок
        assert package.available_packages == 8
        
        # Изменяем зарезервированное количество
        product.reserved_quantity = 40
        product.save()
        
        # Теперь доступно 60 штук -> 6 упаковок
        assert package.available_packages == 6
    
    def test_package_total_units_available_property(self, product):
        """Тест свойства total_units_available"""
        package = Package.objects.create(
            name="Упаковка",
            product=product,
            quantity=10
        )
        
        # Доступно 80 штук, упаковка 10 штук -> 8 упаковок
        assert package.total_units_available == 8
        
        # Меньше чем в одной упаковке
        product.reserved_quantity = 95  # Доступно 5 штук
        product.save()
        
        assert package.total_units_available == 0  # Нельзя собрать ни одной упаковки
    
    def test_package_total_units_property(self, product):
        """Тест свойства total_units"""
        package = Package.objects.create(
            name="Упаковка",
            product=product,
            quantity=10
        )
        
        # Всего 100 штук, упаковка 10 штук -> 10 упаковок всего
        assert package.total_units == 10
        
        # Не делится нацело
        product.total_quantity = 105
        product.save()
        
        # 105 // 10 = 10 упаковок (5 штук останутся не упакованными)
        assert package.total_units == 10
    
    def test_package_string_representation(self, package):
        """Тест строкового представления упаковки"""
        assert str(package) == "Тестовая упаковка - Тестовая Подушка"
    

    def test_package_unique_together_constraint(self, product):
        """Тест ограничения unique_together для product и quantity"""
        
        # 1. Создаем первую упаковку, используя количество, КОТОРОЕ ЕЩЕ НЕ ИСПОЛЬЗОВАНО фикстурой
        # Предполагаем, что фикстура package использует quantity=10, используем 20
        Package.objects.create(
            name="Упаковка 20",
            product=product,
            quantity=20
        )

        # 2. Успешно ловим ошибку при попытке создать вторую с тем же (product, 20)
        with pytest.raises(IntegrityError):
            Package.objects.create(
                name="Другая упаковка 20",
                product=product,
                quantity=20
            )
    
    def test_package_without_name(self, product):
        """Тест создания упаковки без имени (используется дефолтное представление)"""
        package = Package.objects.create(
            name="",  # Пустое имя
            product=product,
            quantity=5
        )
        
        # Должно использоваться дефолтное строковое представление
        assert str(package) == f"Упаковка: {product.name} (5 шт.)"
    
    def test_package_verbose_names(self):
        """Тест verbose names"""
        assert Package._meta.verbose_name == "Упаковка"
        assert Package._meta.verbose_name_plural == "Упаковки"
    
    def test_package_barcode_generation(self, product):
        """Тест автоматической генерации штрихкода для упаковки"""
        package = Package.objects.create(
            name="Автоупаковка",
            product=product,
            quantity=15
        )
        
        assert package.barcode is not None
        assert len(package.barcode) == 15
        assert package.barcode != product.barcode  # Штрихкоды должны быть разные


@pytest.mark.django_db
class TestProductOperationModel:
    """Тесты для модели ProductOperation"""
    
    def test_create_incoming_operation(self, user, product):
        """Тест создания операции прихода"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        operation = ProductOperation.objects.create(
            product=product,
            operation_type=ProductOperation.OperationType.INCOMING,
            quantity=50,
            content_type=content_type,
            object_id=1,
            user=user,
            comment="Приход от поставщика"
        )
        
        assert operation.pk is not None
        assert operation.product == product
        assert operation.operation_type == ProductOperation.OperationType.INCOMING
        assert operation.quantity == 50
        assert operation.content_type == content_type
        assert operation.object_id == 1
        assert operation.user == user
        assert operation.comment == "Приход от поставщика"
        assert operation.timestamp is not None
    
    def test_create_shipment_operation(self, user, product):
        """Тест создания операции отгрузки"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        operation = ProductOperation.objects.create(
            product=product,
            operation_type=ProductOperation.OperationType.SHIPMENT,
            quantity=20,
            content_type=content_type,
            object_id=2,
            user=user,
            comment="Отгрузка клиенту"
        )
        
        assert operation.pk is not None
        assert operation.operation_type == ProductOperation.OperationType.SHIPMENT
        assert operation.quantity == 20
    
    def test_create_all_operation_types(self, user, product):
        """Тест создания операций всех типов"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        operation_types = [
            (ProductOperation.OperationType.INCOMING, "Поступление (+)"),
            (ProductOperation.OperationType.PRODUCTION, "Производство (+)"),
            (ProductOperation.OperationType.SHIPMENT, "Отгрузка (-)"),
            (ProductOperation.OperationType.ADJUSTMENT, "Корректировка (+/-)"),
            (ProductOperation.OperationType.RETURN, "Возврат (+)"),
        ]
        
        for op_type, display_name in operation_types:
            operation = ProductOperation.objects.create(
                product=product,
                operation_type=op_type,
                quantity=10,
                content_type=content_type,
                object_id=1,
                user=user,
                comment=f"Операция {display_name}"
            )
            
            assert operation.pk is not None
            assert operation.operation_type == op_type
            assert operation.get_operation_type_display() == display_name
    
    def test_operation_string_representation_incoming(self, user, product):
        """Тест строкового представления для операции прихода"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        operation = ProductOperation.objects.create(
            product=product,
            operation_type=ProductOperation.OperationType.INCOMING,
            quantity=50,
            content_type=content_type,
            object_id=1,
            user=user
        )
        
        operation_str = str(operation)
        assert "[Поступление (+)]" in operation_str
        assert product.name in operation_str
        assert "+50" in operation_str
    
    def test_operation_string_representation_shipment(self, user, product):
        """Тест строкового представления для операции отгрузки"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        operation = ProductOperation.objects.create(
            product=product,
            operation_type=ProductOperation.OperationType.SHIPMENT,
            quantity=30,
            content_type=content_type,
            object_id=1,
            user=user
        )
        
        operation_str = str(operation)
        assert "[Отгрузка (-)]" in operation_str
        assert product.name in operation_str
        assert "-30" in operation_str
    
    def test_operation_string_representation_adjustment(self, user, product):
        """Тест строкового представления для операции корректировки"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        operation = ProductOperation.objects.create(
            product=product,
            operation_type=ProductOperation.OperationType.ADJUSTMENT,
            quantity=15,
            content_type=content_type,
            object_id=1,
            user=user
        )
        
        operation_str = str(operation)
        assert "[Корректировка (+/-)]" in operation_str
        assert product.name in operation_str
    
    def test_operation_verbose_names(self):
        """Тест verbose names"""
        assert ProductOperation._meta.verbose_name == "Операция с продукцией"
        assert ProductOperation._meta.verbose_name_plural == "Журнал операций с продукцией"
    
    def test_operation_ordering(self, user, product):
        """Тест порядка сортировки операций (по убыванию timestamp)"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        # Создаем несколько операций с разными timestamp
        operations = []
        for i in range(5):
            operation = ProductOperation.objects.create(
                product=product,
                operation_type=ProductOperation.OperationType.INCOMING,
                quantity=(i + 1) * 10,
                content_type=content_type,
                object_id=i,
                user=user
            )
            operations.append(operation)
        
        # Проверяем порядок по умолчанию
        all_operations = ProductOperation.objects.all()
        timestamps = [op.timestamp for op in all_operations]
        
        # Должны быть отсортированы по убыванию (самые новые первыми)
        assert timestamps == sorted(timestamps, reverse=True)
    
    def test_operation_permissions(self):
        """Тест permissions"""
        permissions = [perm[0] for perm in ProductOperation._meta.permissions]
        assert "can_return_product" in permissions
    
    def test_operation_with_null_user(self, product):
        """Тест создания операции без пользователя (null allowed)"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        operation = ProductOperation.objects.create(
            product=product,
            operation_type=ProductOperation.OperationType.INCOMING,
            quantity=25,
            content_type=content_type,
            object_id=1,
            user=None,  # Допустимо
            comment="Операция без пользователя"
        )
        
        assert operation.pk is not None
        assert operation.user is None
    
    def test_operation_with_empty_comment(self, user, product):
        """Тест создания операции без комментария"""
        content_type = ContentType.objects.get(app_label='warehouse2', model='product')
        
        operation = ProductOperation.objects.create(
            product=product,
            operation_type=ProductOperation.OperationType.INCOMING,
            quantity=10,
            content_type=content_type,
            object_id=1,
            user=user,
            comment=""  # Пустой комментарий
        )
        
        assert operation.pk is not None
        assert operation.comment == ""


@pytest.mark.django_db
class TestSenderModel:
    """Тесты для модели Sender"""
    
    def test_create_sender(self):
        """Тест создания отправителя"""
        sender = Sender.objects.create(
            name="ИП Иванов"
        )
        
        assert sender.pk is not None
        assert sender.name == "ИП Иванов"
        assert str(sender) == "ИП Иванов"
    
    def test_sender_unique_name(self):
        """Тест уникальности названия отправителя"""
        Sender.objects.create(name="ИП Иванов")
        
        with pytest.raises(IntegrityError):
            Sender.objects.create(name="ИП Иванов")
    
    def test_sender_verbose_names(self):
        """Тест verbose names"""
        assert Sender._meta.verbose_name == "ФОП отправитель"
        assert Sender._meta.verbose_name_plural == "ФОП отправителя"


@pytest.mark.django_db
class TestShipmentModel:
    """Тесты для модели Shipment"""
    
    def test_create_shipment(self, user, sender):
        """Тест создания отгрузки"""
        shipment = Shipment.objects.create(
            created_by=user,
            sender=sender,
            destination="ул. Тестовая, 123",
            recipient="ООО Получатель",
            status='pending'
        )
        
        assert shipment.pk is not None
        assert shipment.created_by == user
        assert shipment.sender == sender
        assert shipment.destination == "ул. Тестовая, 123"
        assert shipment.recipient == "ООО Получатель"
        assert shipment.status == 'pending'
        assert shipment.created_at is not None
        assert shipment.shipped_at is None
        assert shipment.processed_by is None
    
    def test_shipment_string_representation(self, shipment):
        """Тест строкового представления отгрузки"""
        assert f"Отгрузка №{shipment.id}" in str(shipment)
    
    def test_shipment_grand_total_price_empty(self, shipment):
        """Тест общей суммы пустой отгрузки"""
        assert shipment.grand_total_price == Decimal('0.00')
    
    def test_shipment_grand_total_price_with_items(self, shipment, shipment_item_product, shipment_item_package):
        """Тест общей суммы отгрузки с позициями"""
        # shipment_item_product: quantity=5, price=1000 -> 5000
        # shipment_item_package: quantity=2, price=10000 -> 20000
        # Итого: 25000
        assert shipment.grand_total_price == Decimal('25000.00')
    
    def test_shipment_total_items_count(self, shipment, shipment_item_product, shipment_item_package):
        """Тест общего количества товаров в штуках"""
        # shipment_item_product: 5 штук
        # shipment_item_package: 2 упаковки × 10 штук = 20 штук
        # Итого: 25 штук
        assert shipment.total_items_count == 25
    
    def test_shipment_status_badge_class(self, shipment):
        """Тест класса бейджа статуса"""
        shipment.status = 'pending'
        assert shipment.status_badge_class == 'secondary'
        
        shipment.status = 'packaged'
        assert shipment.status_badge_class == 'warning'
        
        shipment.status = 'shipped'
        assert shipment.status_badge_class == 'success'
        
        shipment.status = 'returned'
        # Не определен в словаре, должен вернуть 'secondary'
        assert shipment.status_badge_class == 'secondary'
    
    def test_shipment_status_display_short(self, shipment):
        """Тест короткого отображения статуса"""
        shipment.status = 'pending'
        assert shipment.status_display_short == 'Сборка'
        
        shipment.status = 'packaged'
        assert shipment.status_display_short == 'Собрано'
        
        shipment.status = 'shipped'
        assert shipment.status_display_short == 'Отгружено'
        
        shipment.status = 'returned'
        assert shipment.status_display_short == 'Возвращено'
    
    def test_shipment_can_be_edited(self, shipment):
        """Тест возможности редактирования отгрузки"""
        shipment.status = 'pending'
        assert shipment.can_be_edited() == True
        
        shipment.status = 'packaged'
        assert shipment.can_be_edited() == True
        
        shipment.status = 'shipped'
        assert shipment.can_be_edited() == False
        
        shipment.status = 'returned'
        assert shipment.can_be_edited() == False
    
    def test_shipment_can_be_packed(self, shipment, product):
        """Тест возможности пометить как собранную"""
        shipment.status = 'pending'
        assert shipment.can_be_packed() == False  # Нет товаров
        
        # Добавляем товар
        ShipmentItem.objects.create(
            shipment=shipment,
            product=Product.objects.first(),  # Используем любой продукт
            quantity=1,
            price=100
        )
        
        assert shipment.can_be_packed() == True
        
        shipment.status = 'packaged'
        assert shipment.can_be_packed() == False  # Уже собрано
    
    def test_shipment_can_be_shipped(self, shipment, product):
        """Тест возможности отгрузки"""
        shipment.status = 'pending'
        assert shipment.can_be_shipped() == False  # Нет товаров
        
        # Добавляем товар
        ShipmentItem.objects.create(
            shipment=shipment,
            product=Product.objects.first(),
            quantity=1,
            price=100
        )
        
        shipment.status = 'pending'
        assert shipment.can_be_shipped() == True
        
        shipment.status = 'packaged'
        assert shipment.can_be_shipped() == True
        
        shipment.status = 'shipped'
        assert shipment.can_be_shipped() == False
    
    def test_shipment_can_be_deleted(self, shipment):
        """Тест возможности удаления отгрузки"""
        shipment.status = 'pending'
        assert shipment.can_be_deleted() == True
        
        shipment.status = 'packaged'
        assert shipment.can_be_deleted() == True
        
        shipment.status = 'shipped'
        assert shipment.can_be_deleted() == False
        
        shipment.status = 'returned'
        assert shipment.can_be_deleted() == False
    
    def test_shipment_ship_success(self, shipment, product, user):
        """Тест успешной отгрузки товара"""
        # Добавляем товар в отгрузку
        item = ShipmentItem.objects.create(
            shipment=shipment,
            product=product,
            quantity=10,
            price=product.price
        )
        
        # Сохраняем начальные значения
        initial_total = product.total_quantity
        initial_reserved = product.reserved_quantity
        
        # Отгружаем
        shipment.ship(user)
        
        # Проверяем обновление продукта
        product.refresh_from_db()
        assert product.total_quantity == initial_total - 10
        assert product.reserved_quantity == initial_reserved - 10
        
        # Проверяем обновление отгрузки
        shipment.refresh_from_db()
        assert shipment.status == 'shipped'
        assert shipment.processed_by == user
        assert shipment.shipped_at is not None
        
        # Проверяем создание операции
        operation = ProductOperation.objects.filter(product=product).last()
        assert operation is not None
        assert operation.operation_type == ProductOperation.OperationType.SHIPMENT
        assert operation.quantity == 10
    
    def test_shipment_ship_already_shipped(self, shipment, user):
        """Тест отгрузки уже отгруженной отгрузки"""
        shipment.status = 'shipped'
        shipment.save()
        
        with pytest.raises(ValidationError, match="уже отгружена"):
            shipment.ship(user)
    
    def test_shipment_ship_insufficient_stock(self, shipment, product, user):
        """Тест отгрузки при недостаточном количестве товара"""
        # Устанавливаем недостаточное количество товара
        product.total_quantity = 5
        product.reserved_quantity = 5
        product.save()
        
        # Добавляем больше товара, чем есть
        with pytest.raises(ValidationError, match="Недостаточно товара"):
                ShipmentItem.objects.create(
                    shipment=shipment,
                    product=product,
                    quantity=10,
                    price=product.price
                )
        shipment.ship(user)
    
    def test_shipment_verbose_names(self):
        """Тест verbose names"""
        assert Shipment._meta.verbose_name == "Отгрузка"
        assert Shipment._meta.verbose_name_plural == "Отгрузки"
    
    def test_shipment_ordering(self, user, sender):
        """Тест порядка сортировки отгрузок"""
        # Создаем несколько отгрузок
        shipments = []
        for i in range(3):
            shipment = Shipment.objects.create(
                created_by=user,
                sender=sender,
                status='pending'
            )
            shipments.append(shipment)
        
        # Проверяем что сортировка по убыванию даты создания
        all_shipments = Shipment.objects.all()
        created_dates = [s.created_at for s in all_shipments]
        
        assert created_dates == sorted(created_dates, reverse=True)


@pytest.mark.django_db
class TestShipmentItemModel:
    """Тесты для модели ShipmentItem"""
    
    def test_create_shipment_item_with_product(self, shipment, product):
        """Тест создания позиции отгрузки с продуктом"""
        item = ShipmentItem.objects.create(
            shipment=shipment,
            product=product,
            quantity=5,
            price=product.price
        )
        
        assert item.pk is not None
        assert item.shipment == shipment
        assert item.product == product
        assert item.package is None
        assert item.quantity == 5
        assert item.price == product.price
    
    def test_create_shipment_item_with_package(self, shipment, package):
        """Тест создания позиции отгрузки с упаковкой"""
        item = ShipmentItem.objects.create(
            shipment=shipment,
            package=package,
            quantity=2,
            price=package.price
        )
        
        assert item.pk is not None
        assert item.shipment == shipment
        assert item.package == package
        assert item.product is None
        assert item.quantity == 2
        assert item.price == package.price
    
    def test_shipment_item_clean_both_product_and_package(self, shipment, product, package):
        """Тест валидации при указании и продукта, и упаковки"""
        item = ShipmentItem(
            shipment=shipment,
            product=product,
            package=package,
            quantity=1,
            price=100
        )
        
        with pytest.raises(ValidationError, match="одновременно и товар, и упаковку"):
            item.clean()
    
    def test_shipment_item_clean_neither_product_nor_package(self, shipment):
        """Тест валидации при отсутствии и продукта, и упаковки"""
        item = ShipmentItem(
            shipment=shipment,
            product=None,
            package=None,
            quantity=1,
            price=100
        )
        
        with pytest.raises(ValidationError, match="Необходимо указать товар или упаковку"):
            item.clean()
    
    def test_shipment_item_base_product_units_product(self, shipment_item_product):
        """Тест base_product_units для продукта"""
        # quantity=5, product - штучный товар
        assert shipment_item_product.base_product_units == 5
    
    def test_shipment_item_base_product_units_package(self, shipment_item_package):
        """Тест base_product_units для упаковки"""
        # quantity=2, package.quantity=10, всего 20 штук
        assert shipment_item_package.base_product_units == 20
    
    def test_shipment_item_total_price(self, shipment_item_product):
        """Тест total_price"""
        # quantity=5, price=1000
        assert shipment_item_product.total_price == Decimal('5000.00')
    
    def test_shipment_item_price_per_unit_product(self, shipment_item_product):
        """Тест price_per_unit для продукта"""
        # Для штучного товара: price = 1000
        assert shipment_item_product.price_per_unit == Decimal('1000.00')
    
    def test_shipment_item_price_per_unit_package(self, shipment_item_package):
        """Тест price_per_unit для упаковки"""
        # Для упаковки: price = 10000, quantity=2, package.quantity=10
        # Общее количество штук: 20
        # Цена за штуку: 10000 / 20 = 500
        assert shipment_item_package.price_per_unit == Decimal('500.00')
    
    def test_shipment_item_stock_product_with_product(self, shipment_item_product, product):
        """Тест stock_product для продукта"""
        assert shipment_item_product.stock_product == product
    
    def test_shipment_item_stock_product_with_package(self, shipment_item_package, product):
        """Тест stock_product для упаковки"""
        assert shipment_item_package.stock_product == product
    
    def test_shipment_item_save_new_product_item(self, shipment, product):
        """Тест сохранения новой позиции с продуктом"""
        initial_reserved = product.reserved_quantity
        
        item = ShipmentItem.objects.create(
            shipment=shipment,
            product=product,
            quantity=10,
            price=product.price
        )
        
        product.refresh_from_db()
        assert product.reserved_quantity == initial_reserved + 10
    
    def test_shipment_item_save_update_product_item(self, shipment_item_product, product):
        """Тест обновления позиции с продуктом"""
        initial_reserved = product.reserved_quantity
        initial_quantity = shipment_item_product.quantity
        
        # Увеличиваем количество
        shipment_item_product.quantity = 15
        shipment_item_product.save()
        
        product.refresh_from_db()
        # Разница: 15 - 5 = 10
        assert product.reserved_quantity == initial_reserved + 10
    
    def test_shipment_item_save_insufficient_available(self, shipment, product):
        """Тест сохранения позиции с недостаточным доступным количеством"""
        product.reserved_quantity = 95  # Доступно всего 5
        product.save()
        
        item = ShipmentItem(
            shipment=shipment,
            product=product,
            quantity=10,
            price=product.price
        )
        
        with pytest.raises(ValidationError, match="Недостаточно товара"):
            item.save()
    
    def test_shipment_item_delete(self, shipment_item_product, product):
        """Тест удаления позиции"""
        initial_reserved = product.reserved_quantity
        
        shipment_item_product.delete()
        
        product.refresh_from_db()
        assert product.reserved_quantity == initial_reserved - 5  # Снимаем резерв
    
    def test_shipment_item_delete_shipped_shipment(self, shipment_item_product, product):
        """Тест удаления позиции из отгруженной отгрузки"""
        shipment_item_product.shipment.status = 'shipped'
        shipment_item_product.shipment.save()
        
        initial_reserved = product.reserved_quantity
        
        shipment_item_product.delete()
        
        # Резерв не должен измениться для отгруженных отгрузок
        product.refresh_from_db()
        assert product.reserved_quantity == initial_reserved
    
    def test_shipment_item_verbose_names(self):
        """Тест verbose names"""
        assert ShipmentItem._meta.verbose_name == "Позиция отгрузки"
        assert ShipmentItem._meta.verbose_name_plural == "Позиции отгрузки"


@pytest.mark.django_db
class TestBarcodeGenerationFunctions:
    """Тесты для функций генерации штрихкода"""
    
    def test_generate_unique_barcode(self):
        """Тест универсальной функции генерации штрихкода"""
        # Тестируем на модели Product
        barcode = generate_unique_barcode(Product)
        
        assert barcode is not None
        assert len(barcode) == 15
        assert barcode.isupper()
    
    def test_generate_product_barcode(self):
        """Тест функции генерации штрихкода для продукта"""
        barcode = generate_product_barcode()
        
        assert barcode is not None
        assert len(barcode) == 15
    
    def test_generate_package_barcode(self):
        """Тест функции генерации штрихкода для упаковки"""
        barcode = generate_package_barcode()
        
        assert barcode is not None
        assert len(barcode) == 15
    
    def test_barcode_uniqueness(self, product_category):
        """Тест уникальности сгенерированных штрихкодов"""
        # Создаем несколько продуктов
        products = []
        for i in range(5):
            product = Product.objects.create(
                name=f"Продукт {i}",
                sku=f"PROD-{i}",
                category=product_category,
                price=100
                # barcode сгенерируется автоматически
            )
            products.append(product)
        
        # Собираем все штрихкоды
        barcodes = [p.barcode for p in products]
        
        # Проверяем что все штрихкоды уникальны
        assert len(barcodes) == len(set(barcodes))
        
        # Проверяем что все штрихкоды имеют правильную длину
        for barcode in barcodes:
            assert len(barcode) == 15


@pytest.mark.django_db
class TestWarehouse2BusinessLogic:
    """Тесты бизнес-логики warehouse2"""
    
    def test_product_available_quantity_edge_cases(self):
        """Тест граничных случаев для available_quantity"""
        product_category = ProductCategory.objects.create(name="Категория")
        
        # 1. Нулевое количество
        product1 = Product.objects.create(
            name="Продукт 1",
            sku="PROD-1",
            barcode="111111111111",
            category=product_category,
            total_quantity=0,
            reserved_quantity=0
        )
        assert product1.available_quantity == 0
        
        # 2. Все зарезервировано
        product2 = Product.objects.create(
            name="Продукт 2",
            sku="PROD-2",
            barcode="222222222222",
            category=product_category,
            total_quantity=100,
            reserved_quantity=100
        )
        assert product2.available_quantity == 0
        
        # 3. Отрицательное доступное количество (резерв больше общего)
        product3 = Product.objects.create(
            name="Продукт 3",
            sku="PROD-3",
            barcode="333333333333",
            category=product_category,
            total_quantity=50,
            reserved_quantity=70
        )
        assert product3.available_quantity == -20
    
    def test_package_business_logic_comprehensive(self, product):
        """Комплексный тест бизнес-логики упаковки"""
        # Создаем несколько упаковок для одного продукта
        package_5 = Package.objects.create(
            name="Упаковка 5 шт",
            product=product,
            quantity=5
        )
        
        package_10 = Package.objects.create(
            name="Упаковка 10 шт",
            product=product,
            quantity=10
        )
        
        # Проверяем свойства
        assert package_5.price == Decimal('5000.00')  # 1000 * 5
        assert package_10.price == Decimal('10000.00')  # 1000 * 10
        
        # Проверяем доступность упаковок
        # total_quantity=100, reserved_quantity=20, available=80
        assert package_5.available_packages == 16  # 80 // 5
        assert package_10.available_packages == 8  # 80 // 10
        
        # Изменяем продукт
        product.price = Decimal('1500.00')
        product.total_quantity = 200
        product.reserved_quantity = 50
        product.save()
        
        # Проверяем обновление свойств
        assert package_5.price == Decimal('7500.00')  # 1500 * 5
        assert package_5.available_packages == 30  # (200-50) // 5
    
    def test_shipment_transaction_integrity(self, shipment, product, user):
        """Тест целостности транзакции при отгрузке"""
        # Создаем две позиции
        ShipmentItem.objects.create(
            shipment=shipment,
            product=product,
            quantity=30,
            price=product.price
        )
        
        ShipmentItem.objects.create(
            shipment=shipment,
            product=product,
            quantity=20,
            price=product.price
        )
        
        # Начальные значения
        initial_total = product.total_quantity
        initial_reserved = product.reserved_quantity
        
        # Отгружаем
        shipment.ship(user)
        
        # Проверяем
        product.refresh_from_db()
        assert product.total_quantity == initial_total - 50
        assert product.reserved_quantity == initial_reserved - 50
        
        # Проверяем создание операций
        operations = ProductOperation.objects.filter(product=product)
        assert operations.count() == 2  # По одной операции на каждую позицию
    
    def test_shipment_item_price_fixed_on_save(self, shipment, product):
        """Тест фиксации цены при сохранении ShipmentItem"""
        # Изменяем цену продукта после создания позиции
        item = ShipmentItem.objects.create(
            shipment=shipment,
            product=product,
            quantity=5,
            price=product.price  # 1000
        )
        
        # Сохраняем исходную цену
        original_price = item.price
        
        # Меняем цену продукта
        product.price = Decimal('2000.00')
        product.save()
        
        # Цена в ShipmentItem должна остаться прежней
        item.refresh_from_db()
        assert item.price == original_price
        
        # Создаем новую позицию - цена должна быть уже новой
        new_item = ShipmentItem.objects.create(
            shipment=shipment,
            product=product,
            quantity=3,
            price=product.price  # 2000
        )
        
        assert new_item.price == Decimal('2000.00')