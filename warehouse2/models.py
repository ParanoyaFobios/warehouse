# warehouse2/models.py

from django.db import models
from django.db.models import F, Sum
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
from decimal import Decimal

# ==============================================================================
# Генераторы штрихкодов
# ==============================================================================

def generate_unique_barcode(model_class):
    """Универсальная функция для генерации уникального штрихкода."""
    while True:
        barcode = uuid.uuid4().hex[:12].upper()
        if not model_class.objects.filter(barcode=barcode).exists():
            return barcode

def generate_product_barcode():
    return generate_unique_barcode(Product)

def generate_package_barcode():
    # Используем ту же универсальную функцию, но для модели Package
    return generate_unique_barcode(Package)


# ==============================================================================
# Справочники (Catalogs)
# ==============================================================================

class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Категория продукции"
        verbose_name_plural = "Категории продукции"

class ProductSize(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Размер")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Размер продукции"
        verbose_name_plural = "Размеры продукции"

class ProductColor(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Цвет")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Цвет продукции"
        verbose_name_plural = "Цвета продукции"

# ==============================================================================
# Продукция и Упаковки
# ==============================================================================

class Product(models.Model):
    """Модель ПОШТУЧНОЙ готовой продукции."""
    name = models.CharField(max_length=200, verbose_name="Название продукции")
    sku = models.CharField(max_length=50, unique=True, verbose_name="Артикул")
    barcode = models.CharField(max_length=12, unique=True, verbose_name="Штрихкод (штучный)", default=generate_product_barcode, editable=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, verbose_name="Категория")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за единицу", default=0)
    size = models.ForeignKey(ProductSize, on_delete=models.PROTECT, verbose_name="Размер", blank=True, null=True)
    color = models.ForeignKey(ProductColor, on_delete=models.PROTECT, verbose_name="Цвет", blank=True, null=True)
    weight = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Вес (кг)", blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Изображение")
    # === Складской учет ===
    total_quantity = models.IntegerField(default=0, verbose_name="На балансе")  # Изменено на PositiveIntegerField
    reserved_quantity = models.IntegerField(default=0, verbose_name="Зарезервировано")

    @property
    def available_quantity(self):
        return self.total_quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.name} ({self.sku})"

    class Meta:
        verbose_name = "Штучный товар"
        verbose_name_plural = "Штучные товары"

class Package(models.Model):
    """
    Упаковка НЕ имеет своего остатка на складе, она ссылается на `Product`.
    """
    name = models.CharField(max_length=255, verbose_name="Название упаковки")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='packages', verbose_name="Базовый продукт")
    quantity = models.PositiveIntegerField(verbose_name="Количество товара в упаковке")
    barcode = models.CharField(max_length=12, unique=True, verbose_name="Штрихкод упаковки", default=generate_package_barcode, editable=False)

    @property
    def price(self):
        """Цена упаковки рассчитывается динамически."""
        return self.product.price * self.quantity

    @property
    def available_packages(self):
        """Сколько таких упаковок можно собрать из доступных товаров."""
        if self.quantity > 0:
            return self.product.available_quantity // self.quantity
        return 0

    def __str__(self):
        if self.name:
            return f"{self.name} - {self.product.name}"
        return f"Упаковка: {self.product.name} ({self.quantity} шт.)"

    class Meta:
        verbose_name = "Упаковка"
        verbose_name_plural = "Упаковки"
        # Ограничение, чтобы не было двух одинаковых упаковок для одного товара
        unique_together = ('product', 'quantity')


# ==============================================================================
# Производство: WorkOrder
# ==============================================================================

class WorkOrder(models.Model):
    STATUS_CHOICES = [('new', 'Новый'), ('in_progress', 'В работе'), ('completed', 'Выполнен')]
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Продукция")
    quantity_to_produce = models.PositiveIntegerField(verbose_name="Количество к производству")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Статус")

    def complete_order(self):
        if self.status != 'completed':
            self.product.total_quantity += self.quantity_to_produce
            self.product.save()
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            return True
        return False
    def __str__(self):
        return f"Заказ №{self.id} на {self.product.name} ({self.quantity_to_produce} шт.)"
    class Meta:
        verbose_name = "Производственный заказ"
        verbose_name_plural = "Производственные заказы"

# ==============================================================================
# Отгрузки: Shipment
# ==============================================================================

class Shipment(models.Model):
    """Отгрузка (накладная)."""
    STATUS_CHOICES = [
        ('pending', 'В процессе сборки'), 
        ('packaged', 'Собрано'), 
        ('shipped', 'Отгружено')
    ]
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_shipments', verbose_name="Кем создана")
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_shipments', verbose_name="Кем собрана/отгружена")
    destination = models.CharField(max_length=255, verbose_name="Адрес отгрузки", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отгрузки")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    
    @property
    def grand_total_price(self):
        """Возвращает общую сумму по всей накладной."""
        total = self.items.aggregate(
            total_price=Sum(F('price') * F('quantity'))
        )['total_price']
        return total or Decimal('0.00')

    @property
    def total_items_count(self):
        """Возвращает общее количество товаров в штуках."""
        total = 0
        for item in self.items.all():
            if item.product:
                total += item.quantity
            elif item.package:
                total += item.quantity * item.package.quantity
        return total
    
    def can_be_edited(self):
        """Можно ли редактировать отгрузку."""
        return self.status != 'shipped'
    
    def can_be_shipped(self):
        """Можно ли отгрузить."""
        return self.status != 'shipped' and self.items.exists()
    
    def ship(self, user):
        """Отгружает товар и списывает его с баланса."""
        if self.status == 'shipped':
            raise ValidationError("Эта отгрузка уже отгружена.")
        
        for item in self.items.all():
            product_to_ship = item.stock_product
            units_to_ship = item.base_product_units
            
            # Проверяем доступность
            if product_to_ship.available_quantity < units_to_ship:
                raise ValidationError(
                    f"Недостаточно товара '{product_to_ship.name}'. "
                    f"Доступно: {product_to_ship.available_quantity}, требуется: {units_to_ship}"
                )
            
            # Списание с баланса
            product_to_ship.total_quantity -= units_to_ship
            product_to_ship.reserved_quantity -= units_to_ship
            product_to_ship.save()
        
        self.status = 'shipped'
        self.processed_by = user
        self.shipped_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Отгрузка №{self.id} от {self.created_at.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = "Отгрузка"
        verbose_name_plural = "Отгрузки"
        ordering = ['-created_at']

class ShipmentItem(models.Model):
    """Строка в накладной. Теперь может содержать или штучный товар, или упаковку."""
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='items', verbose_name="Отгрузка")
    # <<< Одно из двух полей должно быть заполнено >>>
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Штучный товар")
    package = models.ForeignKey(Package, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Упаковка")
    quantity = models.PositiveIntegerField(verbose_name="Количество (товаров или упаковок)")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Фиксированная цена за ед.")

    def clean(self):
        """Проверка, что заполнено только одно поле: или товар, или упаковка."""
        if self.product and self.package:
            raise ValidationError("Позиция не может содержать одновременно и товар, и упаковку.")
        if not self.product and not self.package:
            raise ValidationError("Необходимо указать товар или упаковку для этой позиции.")
    
    @property
    def base_product_units(self):
        """Возвращает, сколько ШТУК базового товара представляет эта строка."""
        if self.product:
            return self.quantity
        if self.package:
            return self.quantity * self.package.quantity
        return 0
    
    @property
    def total_price(self):
        """Общая стоимость позиции (цена × количество)."""
        return self.price * self.quantity
    
    @property
    def stock_product(self):
        """Возвращает товар, у которого нужно проверять остатки на складе."""
        return self.product or self.package.product

    def save(self, *args, **kwargs):
        self.clean()
        is_new = self.pk is None
        
        # Фиксируем цену при первом сохранении
        if is_new:
            self.price = self.product.price if self.product else self.package.price
            old_units = 0
        else:
            old_item = ShipmentItem.objects.get(pk=self.pk)
            old_units = old_item.base_product_units
        
        new_units = self.base_product_units
        difference = new_units - old_units
        
        # Обновляем резерв
        product_to_reserve = self.stock_product
        if difference > 0:
            if product_to_reserve.available_quantity < difference:
                raise ValidationError(f"Недостаточно товара '{product_to_reserve.name}'. Доступно: {product_to_reserve.available_quantity}")
            product_to_reserve.reserved_quantity += difference
        elif difference < 0:
            product_to_reserve.reserved_quantity -= abs(difference)
            
        product_to_reserve.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Снимаем с резерва
        units_to_release = self.base_product_units
        product_to_release = self.stock_product
        product_to_release.reserved_quantity -= units_to_release
        product_to_release.save()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Позиция отгрузки"
        verbose_name_plural = "Позиции отгрузки"