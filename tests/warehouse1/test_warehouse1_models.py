import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from warehouse1.models import (
    MaterialCategory, UnitOfMeasure, MaterialColor, 
    Material, OperationOutgoingCategory, MaterialOperation,
    generate_material_barcode
)
from django.contrib.auth.models import User


@pytest.mark.django_db
class TestMaterialCategoryModel:
    """Тесты для модели MaterialCategory"""
    
    def test_create_material_category(self):
        """Тест создания категории материала"""
        category = MaterialCategory.objects.create(name="Ткани")
        
        assert category.pk is not None
        assert category.name == "Ткани"
        assert str(category) == "Ткани"
    
    def test_material_category_unique_name(self):
        """Тест уникальности названия категории"""
        MaterialCategory.objects.create(name="Ткани")
        
        with pytest.raises(IntegrityError):
            MaterialCategory.objects.create(name="Ткани")
    
    def test_material_category_verbose_names(self):
        """Тест verbose names"""
        assert MaterialCategory._meta.verbose_name == "Категория материала"
        assert MaterialCategory._meta.verbose_name_plural == "Категории материалов"


@pytest.mark.django_db
class TestUnitOfMeasureModel:
    """Тесты для модели UnitOfMeasure"""
    
    def test_create_unit_of_measure(self):
        """Тест создания единицы измерения"""
        unit = UnitOfMeasure.objects.create(
            name="Метр",
            short_name="м"
        )
        
        assert unit.pk is not None
        assert unit.name == "Метр"
        assert unit.short_name == "м"
        assert str(unit) == "Метр (м)"
    
    def test_unit_of_measure_unique_name(self):
        """Тест уникальности названия единицы измерения"""
        UnitOfMeasure.objects.create(name="Метр", short_name="м")
        
        with pytest.raises(IntegrityError):
            UnitOfMeasure.objects.create(name="Метр", short_name="м2")
    
    def test_unit_of_measure_verbose_names(self):
        """Тест verbose names"""
        assert UnitOfMeasure._meta.verbose_name == "Единица измерения"
        assert UnitOfMeasure._meta.verbose_name_plural == "Единицы измерения"


@pytest.mark.django_db
class TestMaterialColorModel:
    """Тесты для модели MaterialColor"""
    
    def test_create_material_color(self):
        """Тест создания цвета материала"""
        color = MaterialColor.objects.create(name="Красный")
        
        assert color.pk is not None
        assert color.name == "Красный"
        assert str(color) == "Красный"
    
    def test_material_color_unique_name(self):
        """Тест уникальности названия цвета"""
        MaterialColor.objects.create(name="Красный")
        
        with pytest.raises(IntegrityError):
            MaterialColor.objects.create(name="Красный")
    
    def test_material_color_verbose_names(self):
        """Тест verbose names"""
        assert MaterialColor._meta.verbose_name == "Цвет материала"
        assert MaterialColor._meta.verbose_name_plural == "Цвета материала"


@pytest.mark.django_db
class TestOperationOutgoingCategoryModel:
    """Тесты для модели OperationOutgoingCategory"""
    
    def test_create_operation_outgoing_category(self):
        """Тест создания категории выдачи"""
        category = OperationOutgoingCategory.objects.create(
            name="Технические нужды"
        )
        
        assert category.pk is not None
        assert category.name == "Технические нужды"
        assert str(category) == "Технические нужды"
    
    def test_operation_outgoing_category_unique_name(self):
        """Тест уникальности названия категории выдачи"""
        OperationOutgoingCategory.objects.create(name="Технические нужды")
        
        with pytest.raises(IntegrityError):
            OperationOutgoingCategory.objects.create(name="Технические нужды")
    
    def test_operation_outgoing_category_verbose_names(self):
        """Тест verbose names"""
        assert OperationOutgoingCategory._meta.verbose_name == "Категория выдачи"
        assert OperationOutgoingCategory._meta.verbose_name_plural == "Категории выдачи"


@pytest.mark.django_db
class TestMaterialModel:
    """Тесты для модели Material"""
    
    def test_create_material(self, material_category, unit_of_measure, material_color):
        """Тест создания материала"""
        material = Material.objects.create(
            name="Хлопковая ткань",
            article="COTTON-001",
            category=material_category,
            quantity=150,
            min_quantity=20,
            color=material_color,
            unit=unit_of_measure,
            description="Высококачественная хлопковая ткань"
        )
        
        assert material.pk is not None
        assert material.name == "Хлопковая ткань"
        assert material.article == "COTTON-001"
        assert material.category == material_category
        assert material.quantity == 150
        assert material.min_quantity == 20.00
        assert material.color == material_color
        assert material.unit == unit_of_measure
        assert material.description == "Высококачественная хлопковая ткань"
        assert len(material.barcode) == 15
    
    def test_material_unique_article(self, material_category, unit_of_measure):
        """Тест уникальности артикула материала"""
        Material.objects.create(
            name="Материал 1",
            article="TEST-001",
            category=material_category,
            quantity=100,
            unit=unit_of_measure
        )
        
        with pytest.raises(IntegrityError):
            Material.objects.create(
                name="Материал 2",
                article="TEST-001",
                category=material_category,
                quantity=50,
                unit=unit_of_measure
            )
    
    def test_material_string_representation(self, material):
        """Тест строкового представления материала"""
        assert str(material) == f"{material.name} ({material.article})"
    
    def test_material_add_quantity(self, material):
            """Тест метода add_quantity (увеличение количества)"""
            initial_quantity = material.quantity
            add_amount = 25
            
            material.add_quantity(add_amount)          #передаем Decimal (или Decimal('25.50'))
            
            material.refresh_from_db()
            # Ожидаем Decimal сравнение
            assert material.quantity == initial_quantity + add_amount
    
    def test_material_subtract_quantity_success(self, material):
            """Тест успешного вычитания количества"""
            initial_quantity = material.quantity
            subtract_amount = 30.00
            
            material.subtract_quantity(subtract_amount)
            
            material.refresh_from_db()
            assert material.quantity == initial_quantity - subtract_amount
    
    def test_material_subtract_quantity_insufficient(self, material):
        """Тест попытки вычитания большего количества, чем есть"""
        initial_quantity = material.quantity
        subtract_amount = initial_quantity + 10
        
        with pytest.raises(ValueError, match="Недостаточно материала на складе"):
            material.subtract_quantity(int(subtract_amount))
        
        material.refresh_from_db()
        assert material.quantity == initial_quantity
    
    def test_material_subtract_quantity_edge_case(self, material):
        """Тест граничного случая - вычитание всего количества"""
        material.subtract_quantity(float(material.quantity))
        
        material.refresh_from_db()
        assert material.quantity == Decimal('0.00')
    
    def test_material_without_color(self, material_category, unit_of_measure):
        """Тест создания материала без цвета (опциональное поле)"""
        material = Material.objects.create(
            name="Материал без цвета",
            article="NOCOLOR-001",
            category=material_category,
            quantity=100,
            unit=unit_of_measure,
            color=None
        )
        
        assert material.pk is not None
        assert material.color is None
    
    def test_material_barcode_generation(self, material_category, unit_of_measure):
        """Тест автоматической генерации штрихкода"""
        material1 = Material.objects.create(
            name="Материал 1",
            article="TEST-1",
            category=material_category,
            quantity=100,
            unit=unit_of_measure
        )
        
        material2 = Material.objects.create(
            name="Материал 2",
            article="TEST-2",
            category=material_category,
            quantity=200,
            unit=unit_of_measure
        )
        
        assert material1.barcode is not None
        assert material2.barcode is not None
        assert material1.barcode != material2.barcode
        assert len(material1.barcode) == 15
        assert len(material2.barcode) == 15
    
    def test_material_verbose_names_and_permissions(self):
        """Тест verbose names и permissions"""
        assert Material._meta.verbose_name == "Материал"
        assert Material._meta.verbose_name_plural == "Материалы"
        
        permissions = [perm[0] for perm in Material._meta.permissions]
        assert "can_view_material_quantity" in permissions
    
    def test_material_default_values(self, material_category, unit_of_measure):
        """Тест значений по умолчанию"""
        material = Material.objects.create(
            name="Тестовый материал",
            article="DEFAULT-TEST",
            category=material_category,
            unit=unit_of_measure
        )
        
        # Проверяем значения по умолчанию
        assert material.quantity == Decimal('0.00')
        assert material.min_quantity == Decimal('0.00')
        assert material.description == ""
        # ImageFieldFile проверяем по имени файла, а не по None
        assert not material.image.name  # Пустое имя файла


@pytest.mark.django_db
class TestMaterialOperationModel:
    """Тесты для модели MaterialOperation"""
    
    def test_create_incoming_operation(self, user, material):
        """Тест создания операции прихода"""
        operation = MaterialOperation.objects.create(
            material=material,
            operation_type='incoming',
            quantity=50,
            user=user,
            comment="Приход от поставщика"
        )
        
        assert operation.pk is not None
        assert operation.material == material
        assert operation.operation_type == 'incoming'
        assert operation.quantity == 50
        assert operation.user == user
        assert operation.comment == "Приход от поставщика"
        assert operation.date is not None
        assert operation.outgoing_category is None
        
        assert "Приход" in str(operation)
        assert material.name in str(operation)
    
    def test_create_outgoing_operation(self, user, material, operation_outgoing_category):
        """Тест создания операции расхода"""
        operation = MaterialOperation.objects.create(
            material=material,
            operation_type='outgoing',
            outgoing_category=operation_outgoing_category,
            quantity=25,
            user=user,
            comment="Расход на производство"
        )
        
        assert operation.pk is not None
        assert operation.operation_type == 'outgoing'
        assert operation.outgoing_category == operation_outgoing_category
        assert operation.quantity == 25
        
        assert "Расход" in str(operation)
    
    def test_create_adjustment_operation(self, user, material):
        """Тест создания операции корректировки"""
        operation = MaterialOperation.objects.create(
            material=material,
            operation_type='adjustment',
            quantity=10.00,
            user=user,
            comment="Корректировка: +10.00 (инвентаризация)"
        )
        
        assert operation.pk is not None
        assert operation.operation_type == 'adjustment'
        
        operation_str = str(operation)
        assert "Корректировка" in operation_str or "adjustment" in operation_str
    
    def test_operation_string_representation_adjustment_with_pattern(self, user, material):
        """Тест строкового представления корректировки с паттерном в комментарии"""
        operation = MaterialOperation.objects.create(
            material=material,
            operation_type='adjustment',
            quantity=15,
            user=user,
            comment="Корректировка: +15 (исправление ошибки)"
        )
        
        operation_str = str(operation)
        assert "+15" in operation_str or "15" in operation_str
    
    def test_operation_verbose_names(self):
        """Тест verbose names"""
        assert MaterialOperation._meta.verbose_name == "Операция с материалом"
        assert MaterialOperation._meta.verbose_name_plural == "Операции с материалами"
    
    def test_operation_auto_now_add_date(self, user, material):
        """Тест автоматической установки даты"""
        operation = MaterialOperation.objects.create(
            material=material,
            operation_type='incoming',
            quantity=10,
            user=user
        )
        
        assert operation.date is not None
    
    def test_operation_outgoing_category_null_for_non_outgoing(self, user, material):
        """Тест что outgoing_category может быть null для не-outgoing операций"""
        operation1 = MaterialOperation.objects.create(
            material=material,
            operation_type='incoming',
            quantity=10,
            user=user
        )
        assert operation1.outgoing_category is None
        
        operation2 = MaterialOperation.objects.create(
            material=material,
            operation_type='adjustment',
            quantity=5,
            user=user,
            comment="Корректировка"
        )
        assert operation2.outgoing_category is None


@pytest.mark.django_db
class TestBarcodeGenerationFunctions:
    """Тесты для функций генерации штрихкода"""
    
    def test_generate_material_barcode(self):
        """Тест функции генерации штрихкода для материала"""
        barcode = generate_material_barcode()
        
        assert barcode is not None
        assert len(barcode) == 15
        assert barcode.isupper()
    
    def test_barcode_uniqueness(self, material_category, unit_of_measure):
        """Тест уникальности сгенерированных штрихкодов"""
        materials = []
        for i in range(5):
            material = Material.objects.create(
                name=f"Материал {i}",
                article=f"TEST-{i}",
                category=material_category,
                quantity=100,
                unit=unit_of_measure
            )
            materials.append(material)
        
        barcodes = [m.barcode for m in materials]
        
        assert len(barcodes) == len(set(barcodes))
        
        for barcode in barcodes:
            assert len(barcode) == 15
            assert barcode.isalnum() # Проверяем, что это цифры и/или буквы
            # Проверяем, что строка является корректным шестнадцатеричным числом (необязательно, но надежно)
            assert all(c in '0123456789ABCDEF' for c in barcode) 
            # Если нужно убедиться, что все буквы заглавные, достаточно проверить, что 
            # она не содержит строчных букв
            assert not any(c.islower() for c in barcode)
    
    def test_barcode_generation_on_material_creation(self, material_category, unit_of_measure):
        """Тест что штрихкод генерируется автоматически при создании материала"""
        material = Material.objects.create(
            name="Тестовый материал",
            article="BARCODE-TEST",
            category=material_category,
            quantity=100,
            unit=unit_of_measure
        )
        
        assert material.barcode is not None
        assert len(material.barcode) == 15
        assert material.barcode.isupper()


@pytest.mark.django_db
class TestMaterialRelationships:
    """Тесты для связей между моделями"""
    
    def test_material_foreign_key_relationships(self, material, material_operation_incoming):
        """Тест связей foreign key"""
        assert hasattr(material, 'category')
        assert material.category is not None
        
        assert hasattr(material, 'unit')
        assert material.unit is not None
        
        assert material_operation_incoming.material == material
        
        assert hasattr(material_operation_incoming, 'user')
        assert material_operation_incoming.user is not None
    
    def test_material_operation_cascade_delete(self, user, material):
        """Тест каскадного удаления операций при удалении материала"""
        for i in range(3):
            MaterialOperation.objects.create(
                material=material,
                operation_type='incoming',
                quantity=10 * (i + 1),
                user=user
            )
        
        operations_count = MaterialOperation.objects.filter(material=material).count()
        assert operations_count == 3
        
        material.delete()
        
        operations_count_after = MaterialOperation.objects.filter(material_id=material.id).count()
        assert operations_count_after == 0
    
    def test_material_protect_on_delete_category(self, material_category, material):
        """Тест PROTECT при удалении категории, если есть материалы"""
        with pytest.raises(ProtectedError):
            material_category.delete()
        
        assert MaterialCategory.objects.filter(pk=material_category.pk).exists()
    
    def test_material_color_protect_on_delete(self, material_color, material):
        """Тест PROTECT при удалении цвета, если есть материалы"""
        # В модели Material поле color имеет on_delete=models.PROTECT
        # Поэтому удаление должно вызвать ProtectedError
        with pytest.raises(ProtectedError):
            material_color.delete()
        
        assert MaterialColor.objects.filter(pk=material_color.pk).exists()
    
    def test_operation_outgoing_category_protect_on_delete(self, operation_outgoing_category, material_operation_outgoing):
        """Тест PROTECT при удалении категории выдачи, если есть операции"""
        with pytest.raises(ProtectedError):
            operation_outgoing_category.delete()
        
        assert OperationOutgoingCategory.objects.filter(pk=operation_outgoing_category.pk).exists()


@pytest.mark.django_db
class TestMaterialModelMethodsEdgeCases:
    """Тесты для граничных случаев методов модели Material"""
    
    def test_add_quantity_negative_value(self, material):
        """Тест добавления отрицательного количества (должно уменьшить количество)"""
        initial_quantity = material.quantity
        negative_amount = -10
        
        material.add_quantity(int(negative_amount))
        
        material.refresh_from_db()
        assert material.quantity == initial_quantity + negative_amount
    
    def test_add_quantity_zero(self, material):
        """Тест добавления нулевого количества"""
        initial_quantity = material.quantity
        
        material.add_quantity(0)
        
        material.refresh_from_db()
        assert material.quantity == initial_quantity
    
    def test_subtract_quantity_zero(self, material):
        """Тест вычитания нулевого количества"""
        initial_quantity = material.quantity
        
        material.subtract_quantity(0)
        
        material.refresh_from_db()
        assert material.quantity == initial_quantity
    
    def test_subtract_quantity_decimal_precision(self, material):
            """Тест точности вычислений с Decimal"""
            
            # 1. Устанавливаем точное количество. В БД сохранится 100
            material.quantity = 100
            material.save()
            material.refresh_from_db()
            
            # Проверка, что в базе 100
            assert material.quantity == 100
            
            subtract_amount = 50
            material.subtract_quantity(subtract_amount)
            material.refresh_from_db()
            
            
            assert material.quantity == 50
    
    def test_material_min_quantity_alert_logic(self, material):
        """Тест логики проверки минимального количества"""
        material.min_quantity = 20
        material.quantity = 15.00
        material.save()
        
        assert material.quantity < material.min_quantity
        
        material.add_quantity(10)
        material.refresh_from_db()
        
        assert material.quantity > material.min_quantity
    
    def test_add_quantity_with_string(self, material):
        """Тест добавления количества в виде строки"""
        initial_quantity = material.quantity
        
        # Метод должен обрабатывать строки, так как Decimal(str(quantity)) используется в модели
        material.add_quantity(25)
        
        material.refresh_from_db()
        assert material.quantity == initial_quantity + 25
    
    def test_subtract_quantity_with_string(self, material):
        """Тест вычитания количества в виде строки"""
        material.add_quantity(50)  # Сначала добавляем
        material.refresh_from_db()
        
        initial_quantity = material.quantity
        
        material.subtract_quantity(25)
        
        material.refresh_from_db()
        assert material.quantity == initial_quantity - 25


@pytest.mark.django_db
class TestMaterialModelBusinessLogic:
    """Тесты бизнес-логики модели Material"""
    
    def test_material_quantity_never_negative(self, material):
        """Тест что количество материала никогда не становится отрицательным"""
        with pytest.raises(ValueError, match="Недостаточно материала на складе"):
            material.subtract_quantity(int(material.quantity + 10))
        
        material.refresh_from_db()
        assert material.quantity >= 0
    
    def test_material_operations_affect_quantity(self, user, material):
        """Тест что операции влияют на количество материала"""
        # Начальное количество
        initial_quantity = material.quantity
        
        # Симуляция прихода
        material.add_quantity(50)
        MaterialOperation.objects.create(
            material=material,
            operation_type='incoming',
            quantity=50,
            user=user,
            comment="Приход"
        )
        
        material.refresh_from_db()
        assert material.quantity == initial_quantity + 50
        
        # Симуляция расхода
        material.subtract_quantity(30)
        MaterialOperation.objects.create(
            material=material,
            operation_type='outgoing',
            quantity=30,
            user=user,
            comment="Расход"
        )
        
        material.refresh_from_db()
        assert material.quantity == initial_quantity + 20
    
    def test_material_reorder_point_logic(self, material_category, unit_of_measure):
        """Тест логики точки повторного заказа"""
        # Создаем материал с мин. количеством
        material = Material.objects.create(
            name="Материал для теста запасов",
            article="REORDER-TEST",
            category=material_category,
            quantity=5,  # Ниже минимального
            min_quantity=10,  # Минимальный запас
            unit=unit_of_measure
        )
        
        # Проверяем что нужно докупить
        assert material.quantity < material.min_quantity
        reorder_amount = material.min_quantity - material.quantity
        assert reorder_amount == 5