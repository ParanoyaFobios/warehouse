from django.db import models
from django.contrib.auth.models import User
from warehouse2.models import Product  # Импорт твоей модели

class Operation(models.Model):
    """Справочник типов работ (шаблоны)"""
    PAYMENT_TYPES = [
        ('piece', 'Сдельная (за шт.)'),
        ('hourly', 'Почасовая (за час)'),
    ]
    
    name = models.CharField(max_length=255, verbose_name="Название операции")
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES, default='piece')
    default_rate = models.DecimalField(
        max_digits=10, decimal_places=2, 
        verbose_name="Ставка по умолчанию", 
        default=0
    )

    def __str__(self):
        return f"{self.name} ({self.get_payment_type_display()})"

    class Meta:
        verbose_name = "Справочник операций"
        verbose_name_plural = "Справочник операций"


class TechCardGroup(models.Model):
    """Группа техкарты (Шаблон)"""
    name = models.CharField(max_length=255, verbose_name="Название техкарты (шаблона)")
    description = models.TextField(blank=True, verbose_name="Описание")

    def __str__(self):
        return self.name


class TechCardOperation(models.Model):
    """Операции внутри конкретной техкарты"""
    group = models.ForeignKey(TechCardGroup, on_delete=models.CASCADE, related_name='operations')
    operation = models.ForeignKey('Operation', on_delete=models.CASCADE, verbose_name="Операция")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена в этой карте")

    class Meta:
        unique_together = ('group', 'operation')


class WorkEntry(models.Model):
    """Запись о выполненной работе на проверку менеджеру"""
    worker = models.ForeignKey(User, on_delete=models.PROTECT, related_name='work_entries', verbose_name="Работник")
    operation = models.ForeignKey(Operation, on_delete=models.PROTECT, verbose_name="Операция")
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Изделие"
    )
    
    quantity = models.PositiveIntegerField(default=0, verbose_name="Кол-во (шт/час)")
    date_performed = models.DateField(verbose_name="Дата выполнения")
    
    is_verified = models.BooleanField(default=False, verbose_name="Подтверждено менеджером")
    verified_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_entries'
    )
    
    # Фиксация цены на момент выполнения
    final_rate = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 1. Сначала определяем базовую ставку из справочника операций (на всякий случай)
        rate = self.operation.default_rate or 0

        # 2. Если это сделка и привязан продукт
        if self.operation.payment_type == 'piece' and self.product:
            # Ищем техкарту, привязанную к этому продукту
            if self.product.tech_card:
                from .models import TechCardOperation # Локальный импорт во избежание циклов
                tc_op = TechCardOperation.objects.filter(
                    group=self.product.tech_card, 
                    operation=self.operation
                ).first()
                
                if tc_op:
                    rate = tc_op.price
        
        # 3. Фиксируем итоговую ставку
        self.final_rate = rate
        
        super().save(*args, **kwargs)

    @property
    def total_sum(self):
        return self.quantity * self.final_rate


class PenaltyBonus(models.Model):
    """Система премий и штрафов"""
    TYPES = [('bonus', 'Премия'), ('penalty', 'Штраф')]
    
    worker = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Работник")
    type = models.CharField(max_length=10, choices=TYPES, verbose_name="Тип")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    reason = models.TextField(verbose_name="Причина/Комментарий")
    date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Премия/Штраф"
        verbose_name_plural = "Премии и штрафы"


class Payout(models.Model):
    """Модель выдачи денег работнику"""
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts', verbose_name="Работник")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Выплаченная сумма")
    date_paid = models.DateField(auto_now_add=True, verbose_name="Дата выплаты")
    comment = models.CharField(max_length=255, blank=True, verbose_name="Комментарий (напр. Аванс)")

    def __str__(self):
        return f"{self.worker.username} - {self.amount} ({self.date_paid})"