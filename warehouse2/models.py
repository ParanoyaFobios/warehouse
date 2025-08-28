from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType # Импортируем ContentType
import uuid

def generate_unique_barcode_for_model(model_class):
    """Универсальная функция для генерации уникального штрихкода для любой модели."""
    while True:
        barcode = uuid.uuid4().hex[:12].upper()
        if not model_class.objects.filter(barcode=barcode).exists():
            return barcode

# 👇 НОВАЯ ИМЕНОВАННАЯ ФУНКЦИЯ ДЛЯ Product 👇
def generate_product_barcode():
    return generate_unique_barcode_for_model(Product)

# 👇 НОВАЯ ИМЕНОВАННАЯ ФУНКЦИЯ ДЛЯ Package 👇
def generate_package_barcode():
    return generate_unique_barcode_for_model(Package)
# ==============================================================================
# Справочники (Catalogs)
# ==============================================================================

class ProductCategory(models.Model):
    """Категории готовой продукции (например, Подушки, Одеяла)."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория продукции"
        verbose_name_plural = "Категории продукции"

class ProductSize(models.Model):
    """Размеры продукции (например, 40x55, 150x200)."""
    name = models.CharField(max_length=50, unique=True, verbose_name="Размер")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Размер продукции"
        verbose_name_plural = "Размеры продукции"

class ProductColor(models.Model):
    """Цвета продукции (например, Белый, Синий)."""
    name = models.CharField(max_length=50, unique=True, verbose_name="Цвет")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Цвет продукции"
        verbose_name_plural = "Цвета продукции"

# ==============================================================================
# Основная модель: Product (Готовая продукция)
# ==============================================================================

class Product(models.Model):
    """Модель готовой продукции."""
    name = models.CharField(max_length=200, verbose_name="Название продукции")
    sku = models.CharField(max_length=50, unique=True, verbose_name="Артикул")
    barcode = models.CharField(max_length=12, unique=True, verbose_name="Штрихкод продукции", default=generate_product_barcode, editable=False)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, verbose_name="Категория")
    size = models.ForeignKey(ProductSize, on_delete=models.PROTECT, verbose_name="Размер", blank=True, null=True)
    color = models.ForeignKey(ProductColor, on_delete=models.PROTECT, verbose_name="Цвет", blank=True, null=True)
    weight = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Вес (кг)", blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Изображение")
    total_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Общее количество")
    reserved_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Зарезервировано")

    @property
    def available_quantity(self):
        return self.total_quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.name} ({self.sku})"

    class Meta:
        verbose_name = "Готовая продукция"
        verbose_name_plural = "Готовая продукция"
# ==============================================================================
# Производство: WorkOrder (Производственный заказ)
# ==============================================================================

class WorkOrder(models.Model):
    """Производственное задание."""
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнен'),
    ]
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Продукция")
    quantity_to_produce = models.PositiveIntegerField(verbose_name="Количество к производству")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")

    def complete_order(self):
        """Завершает заказ и ставит продукцию на баланс."""
        if self.status != 'completed':
            self.product.total_quantity += self.quantity_to_produce
            self.product.save()
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            # Здесь можно добавить логику для списания материалов со склада 1
            # и создания записи в журнале операций
            return True
        return False

    def __str__(self):
        return f"Заказ №{self.id} на {self.product.name} ({self.quantity_to_produce} шт.)"

    class Meta:
        verbose_name = "Производственный заказ"
        verbose_name_plural = "Производственные заказы"

# ==============================================================================
# Отгрузки: Shipment и Package (Накладная и Упаковка)
# ==============================================================================
class ShipmentDocument(models.Model):
    """Накладная, объединяющая несколько отгрузок (упаковок)."""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('finalized', 'Сформирована'),
        ('shipped', 'Отправлена'),
    ]
    destination = models.CharField(max_length=255, verbose_name="Адрес/Получатель")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Статус")

    def __str__(self):
        return f"Накладная №{self.id} для '{self.destination}'"
    
    class Meta:
        verbose_name = "Накладная"
        verbose_name_plural = "Накладные"

class Shipment(models.Model):
    """Отгрузка (накладная)."""
    STATUS_CHOICES = [
        ('pending', 'В процессе сборки'),
        ('packaged', 'Собрано и упаковано'),
        ('assigned', 'Включено в накладную'),
        ('shipped', 'Отгружено'), # Этот статус будет наследоваться от накладной
    ]
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    document = models.ForeignKey(ShipmentDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name='shipments', verbose_name="Накладная")

    def get_total_items(self):
        """Возвращает общее количество товаров в отгрузке"""
        return self.shipmentitem_set.aggregate(total=models.Sum('quantity'))['total'] or 0
    
    def get_total_products(self):
        """Возвращает количество уникальных продуктов"""
        return self.shipmentitem_set.count()
    
    def can_be_edited(self):
        """Можно ли редактировать отгрузку"""
        return self.status != 'shipped'
    
    def can_be_shipped(self):
        """Можно ли отгрузить"""
        return self.status != 'shipped' and self.shipmentitem_set.exists()

    def ship(self):
        """Отгружает товар и списывает его с баланса."""
        if self.status == 'shipped':
            raise ValidationError("Этот заказ уже отгружен.")
        
        for item in self.shipmentitem_set.all():
            product = item.product
            product.total_quantity -= item.quantity
            product.reserved_quantity -= item.quantity
            product.save()
        
        self.status = 'shipped'
        self.save()

    def __str__(self):
        return f"Отгрузка №{self.id} от {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Отгрузка (накладная)"
        verbose_name_plural = "Отгрузки (баулы/коробки)"

class ShipmentItem(models.Model):
    """Строка в накладной."""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, verbose_name="Отгрузка")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Продукция")
    quantity = models.PositiveIntegerField(verbose_name="Количество")

    def delete(self, *args, **kwargs):
        """При удалении строки снимаем резерв"""
        if self.product:
            self.product.reserved_quantity -= self.quantity
            self.product.save()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        """При добавлении товара в накладную, резервируем его."""
        if self.pk is None: # Выполняется только при создании новой строки
            if self.product.available_quantity < self.quantity:
                raise ValidationError(f"Недостаточно товара '{self.product.name}' на складе. Доступно: {self.product.available_quantity}")
            self.product.reserved_quantity += self.quantity
            self.product.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.quantity} шт."

class Package(models.Model):
    """Упаковка (баул/ящик) с уникальным штрихкодом."""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, verbose_name="Привязан к отгрузке")
    barcode = models.CharField(max_length=12, unique=True, verbose_name="Штрихкод упаковки", default=generate_package_barcode, editable=False)

    def __str__(self):
        return f"Упаковка {self.barcode} для отгрузки №{self.shipment.id}"
    
    class Meta:
        verbose_name = "Упаковка (баул)"
        verbose_name_plural = "Упаковки (баулы)"