from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from warehouse2.models import Product, ProductOperation
from django.db import transaction

# ==============================================================================
# Модель 1: "Шапка" Заказа
# ==============================================================================
class ProductionOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        PLANNED = 'planned', 'В плане'
        PARTIAL = 'partial', 'Частично выполнен'
        COMPLETED = 'completed', 'Выполнен'
        SHIPPED = 'shipped', 'Передано в отгрузку'

    customer = models.CharField(max_length=255, blank=True, verbose_name="Заказчик (Поставщик)")
    due_date = models.DateField(verbose_name="Дата потребности (срок)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Статус")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий к заказу")
    linked_shipment = models.ForeignKey('warehouse2.Shipment', on_delete=models.SET_NULL, null=True, blank=True, related_name='source_orders', verbose_name="Связанная накладная")

    @property
    def total_requested(self):
        """Сумма всех запрошенных товаров в заказе"""
        # Используем sum() по связанным объектам
        return sum(item.quantity_requested for item in self.items.all())

    @property
    def total_produced(self):
        """Сумма всех произведенных товаров в заказе"""
        return sum(item.quantity_produced for item in self.items.all())
    
    @property
    def total_shipped(self):
        """Сумма всех фактически отгруженных товаров"""
        # ОПТИМИЗАЦИЯ: Если мы уже посчитали это в annotate (во view), берем готовое
        if hasattr(self, 'annotated_shipped_total'):
            return self.annotated_shipped_total
            
        # Fallback (запасной вариант): если вызвали не из вьюхи, считаем по-старому
        if not self.linked_shipment:
            return 0
        from django.db.models import Sum
        return self.linked_shipment.items.aggregate(total=Sum('quantity'))['total'] or 0

    @property
    def shipment_gap(self):
        # Python sum() работает быстро, так как items уже в памяти (prefetch_related)
        # А total_shipped теперь берется из аннотации
        return self.total_requested - self.total_shipped

    @property
    def is_under_shipped(self):
        """Флаг недогруза: если отгружено меньше, чем просили в заказе"""
        return self.total_shipped < self.total_requested

    # --- ДОБАВЛЯЕМ ЛОГИКУ ОБНОВЛЕНИЯ СТАТУСА ---
    def update_status(self):
            """Пересчитывает статус всего заказа"""
            # Если к заказу уже привязана накладная — это приоритетный статус
            if self.linked_shipment:
                self.status = self.Status.SHIPPED
                self.save()
                return

            items = self.items.all()
            if not items.exists():
                self.status = self.Status.PENDING
            elif all(item.is_completed for item in items):
                self.status = self.Status.COMPLETED
            elif any(item.quantity_produced > 0 for item in items):
                self.status = self.Status.PARTIAL
            elif any(item.quantity_planned > 0 for item in items):
                self.status = self.Status.PLANNED
            else:
                self.status = self.Status.PENDING
                
            self.save()

    def get_absolute_url(self):
        return reverse('portfolio_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return f"Заказ №{self.id} (Заказчик: {self.customer}) к {self.due_date}"

    class Meta:
        verbose_name = "Планирование заказов"
        verbose_name_plural = "Планирование заказов"
        ordering = ['due_date']

# ==============================================================================
# Модель 2: "Строка" Заказа
# ==============================================================================
class ProductionOrderItem(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        PLANNED = 'planned', 'В плане'
        PARTIAL = 'partial', 'Частично выполнен'
        COMPLETED = 'completed', 'Выполнен'
        SHIPPED = 'shipped', 'Передано в отгрузку'

    production_order = models.ForeignKey(
        ProductionOrder,
        on_delete=models.CASCADE,
        related_name='items', 
        verbose_name="Заказ"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Продукция")
    quantity_requested = models.PositiveIntegerField(verbose_name="Запрошено (кол-во)")
    quantity_planned = models.PositiveIntegerField(default=0, verbose_name="Запланировано")
    quantity_produced = models.PositiveIntegerField(default=0, verbose_name="Произведено (факт)")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Статус")

    @property
    def remaining_to_plan(self):
        return self.quantity_requested - self.quantity_planned

    @property
    def is_fully_planned(self):
        return self.remaining_to_plan <= 0
        
    @property
    def is_completed(self):
        return self.quantity_produced >= self.quantity_requested

    def update_status(self):
            # Если у родителя есть накладная, то и строка считается отгруженной
            if self.production_order.linked_shipment:
                self.status = self.Status.SHIPPED
            elif self.is_completed:
                self.status = self.Status.COMPLETED
            elif self.quantity_produced > 0:
                self.status = self.Status.PARTIAL
            elif self.quantity_planned > 0:
                self.status = self.Status.PLANNED
            else:
                self.status = self.Status.PENDING
            self.save()
            
            # Обновляем статус родителя (там сработает проверка на linked_shipment)
            self.production_order.update_status()

    def __str__(self):
        return f"Строка: {self.product.name} ({self.quantity_requested} шт.)"

    class Meta:
        verbose_name = "Строка заказа"
        verbose_name_plural = "Строки заказов"
        unique_together = ('production_order', 'product')

# ==============================================================================
# Модель 3: Задание на смену
# ==============================================================================
class WorkOrder(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        IN_PROGRESS = 'in_progress', 'В работе'
        COMPLETED = 'completed', 'Выполнен'

    order_item = models.ForeignKey(
        ProductionOrderItem,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Из строки заказа"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Продукция")
    quantity_planned = models.PositiveIntegerField(verbose_name="План (на смену)")
    quantity_produced = models.PositiveIntegerField(default=0, verbose_name="Факт (произведено)")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата выполнения")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий")

    @property
    def remaining_to_produce(self):
        return self.quantity_planned - self.quantity_produced
    
    @property
    def status_display_short(self):
        """Возвращает человекочитаемый статус"""
        return self.get_status_display()

    @property
    def status_badge_class(self):
        """Возвращает цвет для Bootstrap badge"""
        choices = {
            'new': 'info',
            'in_progress': 'primary',
            'completed': 'success',
            'canceled': 'danger',
        }
        return choices.get(self.status, 'secondary')

    @property
    def is_completed(self):
        return self.remaining_to_produce <= 0

    def report_production(self, quantity_done: int, user: User):
            if self.status == self.Status.COMPLETED:
                return False, "Задание уже завершено"
                
            # 1. Сначала обновляем фактическое количество в WorkOrder и в Товаре на складе
            with transaction.atomic():
                # Обновление WorkOrder: добавляем факт
                WorkOrder.objects.filter(pk=self.pk).update(
                    quantity_produced=F('quantity_produced') + quantity_done
                )
                
                # Обновление Склада: добавляем факт
                self.product.total_quantity = F('total_quantity') + quantity_done
                self.product.save()

                # Создание записи об операции
                ProductOperation.objects.create(
                    product=self.product,
                    operation_type=ProductOperation.OperationType.PRODUCTION,
                    quantity=quantity_done,
                    source=self,
                    user=user
                )

                # 2. Получаем актуальные данные из базы для проверки статуса
                self.refresh_from_db()

                # 3. Проверяем статус и сохраняем изменения
                if self.quantity_produced >= self.quantity_planned:
                    self.status = self.Status.COMPLETED
                    self.completed_at = timezone.now()
                elif self.quantity_produced > 0:
                    self.status = self.Status.IN_PROGRESS
                # else: status остается 'new'

                self.save() # Сохраняем статус и completed_at

                # 4. Обновление родительской строки заказа (ProductionOrderItem)
                if self.order_item:
                    # Обновляем произведенное количество в строке заказа
                    ProductionOrderItem.objects.filter(pk=self.order_item.pk).update(
                        quantity_produced=F('quantity_produced') + quantity_done
                    )
                    
                    # Получаем обновленную строку заказа и обновляем ее статус
                    self.order_item.refresh_from_db()
                    self.order_item.update_status() # Метод update_status внутри ProductionOrderItem

            return True, f"Выпуск {quantity_done} шт. зарегистрирован. Задание №{self.pk}"

    def get_absolute_url(self):
        return reverse('workorder_list')

    def __str__(self):
        return f"[Задание] {self.product.name} ({self.quantity_produced}/{self.quantity_planned} шт.)"
    
    class Meta:
        verbose_name = "Задание на смену"
        verbose_name_plural = "Задания на смену (Доска)"
        ordering = ['-created_at']