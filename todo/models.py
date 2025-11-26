from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from warehouse2.models import Product, ProductOperation

# ==============================================================================
# Модель 1: "Шапка" Заказа
# ==============================================================================
class ProductionOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        PLANNED = 'planned', 'В плане'
        PARTIAL = 'partial', 'Частично выполнен'
        COMPLETED = 'completed', 'Выполнен'

    customer = models.CharField(max_length=255, blank=True, verbose_name="Заказчик (Поставщик)")
    due_date = models.DateField(verbose_name="Дата потребности (срок)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name="Статус")
    comment = models.TextField(blank=True, null=True, verbose_name="Комментарий к заказу")

    def get_absolute_url(self):
        return reverse('portfolio_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return f"Заказ №{self.id} (Заказчик: {self.customer}) к {self.due_date}"

    class Meta:
        verbose_name = "Заказ (Портфель)"
        verbose_name_plural = "Портфель заказов"
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
        if self.is_completed:
            self.status = self.Status.COMPLETED
        elif self.quantity_produced > 0:
            self.status = self.Status.PARTIAL
        elif self.quantity_planned > 0:
             self.status = self.Status.PLANNED
        else:
            self.status = self.Status.PENDING
        self.save()

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
    def is_completed(self):
        return self.remaining_to_produce <= 0

    def report_production(self, quantity_done: int, user: User):
        if self.status == self.Status.COMPLETED:
            return False, "Задание уже завершено"
            
        self.product.total_quantity = F('total_quantity') + quantity_done
        self.product.save()

        ProductOperation.objects.create(
            product=self.product,
            operation_type=ProductOperation.OperationType.PRODUCTION,
            quantity=quantity_done,
            source=self,
            user=user
        )

        self.quantity_produced = F('quantity_produced') + quantity_done
        if (self.quantity_produced + quantity_done) >= self.quantity_planned:
            self.status = self.Status.COMPLETED
            self.completed_at = timezone.now()
        else:
            self.status = self.Status.IN_PROGRESS
        self.save()
        
        if self.order_item:
            self.order_item.quantity_produced = F('quantity_produced') + quantity_done
            self.order_item.save()
            self.order_item.refresh_from_db()
            self.order_item.update_status()

        return True, f"Выпуск {quantity_done} шт. зарегистрирован"

    def get_absolute_url(self):
        return reverse('workorder_list')

    def __str__(self):
        return f"[Задание] {self.product.name} ({self.quantity_produced}/{self.quantity_planned} шт.)"
    
    class Meta:
        verbose_name = "Задание на смену"
        verbose_name_plural = "Задания на смену (Доска)"
        ordering = ['-created_at']