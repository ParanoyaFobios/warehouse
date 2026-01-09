from django.db import models
from django.db.models import F, Sum
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
from decimal import Decimal
from django.db.models import Sum
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from main.models import ContentTypeAware
from django.db import transaction
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


# ==============================================================================
# Продукция и Упаковки
# ==============================================================================

class Product(ContentTypeAware, models.Model):
    """Модель ПОШТУЧНОЙ готовой продукции."""
    name = models.CharField(max_length=200, db_index=True, verbose_name="Название продукции")
    sku = models.CharField(max_length=50, unique=True, verbose_name="Артикул")
    barcode = models.CharField(max_length=12, unique=True, verbose_name="Штрихкод (штучный)", default=generate_product_barcode, editable=True)
    is_archived = models.BooleanField(default=False, verbose_name="В архиве")
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT, verbose_name="Категория", blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена за единицу", default=0)
    color = models.CharField(max_length=50, unique=True, verbose_name="Цвет", blank=True, null=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Изображение")
    # === Складской учет ===
    total_quantity = models.IntegerField(default=0, verbose_name="На балансе")
    reserved_quantity = models.IntegerField(default=0, verbose_name="Зарезервировано")

    @property
    def available_quantity(self):
        return self.total_quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.name}"

    class Meta:
        verbose_name = "Штучный товар"
        verbose_name_plural = "Штучные товары"
        permissions = [
            ("can_view_product_quantity", "Может просматривать количество продукции на складе"),
            ("can_edit_product_price", "Может менять цену продукции на складе"),
        ]

class Package(ContentTypeAware, models.Model):
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

    @property
    def total_units_available(self):
        """Общее количество штук товара, доступное в упаковках."""
        if self.product.available_quantity >= self.quantity:
            return self.product.available_quantity // self.quantity
        return 0
    
    @property
    def total_units(self):
        """Общее количество штук товара в упаковках."""
        return self.product.total_quantity // self.quantity

    def __str__(self):
        if self.name:
            return f"{self.name} - {self.product.name}"
        return f"Упаковка: {self.product.name} ({self.quantity} шт.)"

    class Meta:
        verbose_name = "Упаковка"
        verbose_name_plural = "Упаковки"
        # Ограничение, чтобы не было двух одинаковых упаковок для одного товара
        unique_together = ('product', 'quantity')

class ProductOperation(models.Model):
    """
    Журнал операций с готовой продукцией.
    Фиксирует каждое изменение количества товара на складе.
    """
    class OperationType(models.TextChoices):
        INCOMING = 'incoming', 'Поступление (+)'
        PRODUCTION = 'production', 'Производство (+)'
        SHIPMENT = 'shipment', 'Отгрузка (-)'
        ADJUSTMENT = 'adjustment', 'Корректировка (+/-)'
        RETURN = 'return', 'Возврат (+)'

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='operations', verbose_name="Продукция")
    operation_type = models.CharField(max_length=20, choices=OperationType.choices, verbose_name="Тип операции")
    quantity = models.IntegerField(verbose_name="Количество")
    
    # Связь с документом-основанием (Shipment, InventoryCount и т.д.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    source = GenericForeignKey('content_type', 'object_id')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время операции")
    comment = models.TextField(blank=True, verbose_name="Комментарий")

    def __str__(self):
        # Определяем список всех операций, увеличивающих количество
        POSITIVE_OPERATIONS = [
            self.OperationType.PRODUCTION, 
            self.OperationType.RETURN, 
            self.OperationType.INCOMING
        ]
        
        if self.operation_type == self.OperationType.ADJUSTMENT:     
            # Если quantity положительно, знак "+", иначе "-"
            adj_sign = '+' if self.quantity >= 0 else '' # знак '-' будет в quantity
            return f"[{self.get_operation_type_display()}] {self.product.name}: {adj_sign}{self.quantity}"

        else:
            # Для остальных операций, где quantity всегда должно быть положительным числом, 
            # но знак отображается в зависимости от типа
            sign = '+' if self.operation_type in POSITIVE_OPERATIONS else '-'
            
            # Используем abs(self.quantity) на случай, если кто-то сохранил отрицательное число
            return f"[{self.get_operation_type_display()}] {self.product.name}: {sign}{abs(self.quantity)}"

    class Meta:
        verbose_name = "Операция с продукцией"
        verbose_name_plural = "Журнал операций с продукцией"
        ordering = ['-timestamp']
        permissions = [
            ("can_return_product", "Может делать возврат накладных"),
        ]


# ==============================================================================
# Отгрузки: Shipment
# ============================================================================== 
class Sender(models.Model):
    """Физ/Юр лицо - отправитель отгрузки."""
    name = models.CharField(max_length=100, unique=True, verbose_name="ФОП отправитель")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "ФОП отправитель"
        verbose_name_plural = "ФОП отправителя"

class Shipment(models.Model):
    """Отгрузка (накладная)."""
    STATUS_CHOICES = [
        ('pending', 'В процессе сборки'), 
        ('packaged', 'Собрано'), 
        ('shipped', 'Отгружено'),
        ('returned', 'Возвращено')
    ]
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_shipments', verbose_name="Кем создана")
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_shipments', verbose_name="Кем собрана/отгружена")
    sender = models.ForeignKey(Sender, on_delete=models.PROTECT, verbose_name="ФОП отпраитель", blank=True, null=True)
    destination = models.CharField(max_length=255, verbose_name="Адрес отгрузки", blank=True)
    recipient = models.CharField(max_length=255, verbose_name="Адрес отгрузки", blank=True, null=True)
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
    
    @property
    def status_badge_class(self):
        """Возвращает класс для бейджа статуса."""
        return {
            'pending': 'secondary',
            'packaged': 'warning', 
            'shipped': 'success'
        }.get(self.status, 'secondary')
    
    @property
    def status_display_short(self):
        """Короткое отображение статуса."""
        return {
            'pending': 'Сборка',
            'packaged': 'Собрано',
            'shipped': 'Отгружено',
            'returned': 'Возвращено'
        }.get(self.status, self.status)

    def can_be_edited(self):
        """Можно ли редактировать отгрузку (добавлять/удалять товары)."""
        # 👇 Редактировать можно только те, что в процессе сборки или уже собраны
        return self.status in ['pending', 'packaged']
    
    def can_be_packed(self):
        """Можно ли отметить как собранную (только для отгрузок в статусе 'pending')."""
        return self.status == 'pending' and self.items.exists()
    
    def can_be_shipped(self):
        """Можно ли отгрузить."""
        # 👇 Отгрузить можно собранные или находящиеся в процессе сборки, если в них есть товары
        return self.status in ['pending', 'packaged'] and self.items.exists()
    
    def can_be_deleted(self):
        """Отгрузку можно удалить, только если она еще не обработана."""
        return self.status in ['pending', 'packaged']

    def ship(self, user):
        """Отгружает товар и списывает его с баланса."""
        if self.status == 'shipped':
            raise ValidationError("Эта отгрузка уже отгружена.")
        
        # Для гарантии целостности данных оборачиваем всё в транзакцию
        with transaction.atomic():
            for item in self.items.all():
                base_product = item.stock_product
                units_to_ship = item.base_product_units
                
                # --- 👇 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ 👇 ---
                # Проверяем не "доступное", а общее количество на балансе,
                # так как зарезервированное количество мы и собираемся отгрузить.
                if base_product.total_quantity < units_to_ship:
                    raise ValidationError(
                        f"Недостаточно товара '{base_product.name}' на балансе. "
                        f"На складе: {base_product.total_quantity}, требуется: {units_to_ship}"
                    )
                
                # Списание с баланса и ОДНОВРЕМЕННОЕ снятие с резерва
                base_product.total_quantity -= units_to_ship
                base_product.reserved_quantity -= units_to_ship
                base_product.save()

                # Создание записи в журнале (остается без изменений)
                ProductOperation.objects.create(
                    product=base_product,
                    operation_type=ProductOperation.OperationType.SHIPMENT,
                    quantity=units_to_ship,
                    source=self,
                    user=user,
                    comment=f"Позиция: {item}"
                )
            
            # Обновление статуса отгрузки (остается без изменений)
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
    def price_per_unit(self):
        """Цена за одну штуку товара (универсальное свойство)."""
        
        if self.product:
            # Для штучного товара: общая цена / количество
            return self.price
        
        elif self.package:
            # Для упаковки: общая цена / (количество упаковок × товаров в упаковке)
            total_units = self.quantity * self.package.quantity
            return self.price / total_units
        
        return Decimal('0.00')
    
    @property
    def stock_product(self):
        """Возвращает товар, у которого нужно проверять остатки на складе."""
        return self.product or self.package.product

    def save(self, *args, **kwargs):
        self.clean()
        is_new = self.pk is None
        
        if is_new:
            # Фиксируем цену при первом сохранении
            if self.price is None:
                self.price = self.product.price if self.product else self.package.price
            
            old_units = 0
        else:
            # Получаем старую версию для расчета разницы
            old_item = ShipmentItem.objects.get(pk=self.pk)
            old_units = old_item.base_product_units
        
        new_units = self.base_product_units
        difference = new_units - old_units
        
        # Обновляем резерв у БАЗОВОГО продукта (не у упаковки!)
        base_product = self.stock_product
        if difference > 0:
            if base_product.available_quantity < difference:
                raise ValidationError(f"Недостаточно товара '{base_product.name}'. Доступно: {base_product.available_quantity}")
            base_product.reserved_quantity += difference
        elif difference < 0:
            base_product.reserved_quantity -= abs(difference)
            
        base_product.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Снимаем с резерва, только если отгрузка находится в статусе,
        # где резервирование имеет смысл ('pending' или 'packaged').
        if self.shipment.status in ['pending', 'packaged']:
            units_to_release = self.base_product_units
            base_product = self.stock_product
            
            # Уменьшаем резерв, но не даем ему уйти в минус
            base_product.reserved_quantity = max(0, base_product.reserved_quantity - units_to_release)
            base_product.save()
            
        # Вызываем стандартный метод удаления для самой строки
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = "Позиция отгрузки"
        verbose_name_plural = "Позиции отгрузки"