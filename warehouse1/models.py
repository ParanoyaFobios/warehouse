from django.db import models
from django.contrib.auth.models import User
import uuid

def generate_unique_barcode():
    """
    Генерирует уникальный 12-значный код и проверяет его на уникальность в БД.
    """
    while True:
        barcode = uuid.uuid4().hex[:12].upper()
        if not Material.objects.filter(barcode=barcode).exists():
            return barcode

class MaterialCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Категория материала"
        verbose_name_plural = "Категории материалов"


class UnitOfMeasure(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Единица измерения")
    short_name = models.CharField(max_length=10, verbose_name="Короткое обозначение")
    
    def __str__(self):
        return f"{self.name} ({self.short_name})"
    
    class Meta:
        verbose_name = "Единица измерения"
        verbose_name_plural = "Единицы измерения"



class Material(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название материала")
    article = models.CharField(max_length=50, unique=True, verbose_name="Артикул")
    category = models.ForeignKey(MaterialCategory, on_delete=models.PROTECT, verbose_name="Категория")
    barcode = models.CharField(max_length=12, unique=True, verbose_name="Штрихкод", default=generate_unique_barcode, editable=False)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Количество")
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, verbose_name="Единица измерения")
    image = models.ImageField(upload_to='photos/', blank=True, null=True, verbose_name="Изображение")
    description = models.TextField(blank=True, verbose_name="Описание")

    def add_quantity(self, quantity, user, comment=''):
        """Увеличение количества материала (прием)"""
        self.quantity += quantity
        self.save()
        MaterialOperation.objects.create(
            material=self,
            operation_type='incoming',
            quantity=quantity,
            user=user,
            comment=comment
        )
    
    def subtract_quantity(self, quantity, user, comment=''):
        """Уменьшение количества материала (выдача/списание)"""
        if self.quantity < quantity:
            raise ValueError("Недостаточно материала на складе")
        self.quantity -= quantity
        self.save()
        MaterialOperation.objects.create(
            material=self,
            operation_type='outgoing',
            quantity=quantity,
            user=user,
            comment=comment
        )
    
    
    def __str__(self):
        return f"{self.name} ({self.article})"
    
    class Meta:
        verbose_name = "Материал"
        verbose_name_plural = "Материалы"


class MaterialOperation(models.Model):
    OPERATION_TYPES = (
        ('incoming', 'Приход'),
        ('outgoing', 'Расход'),
    )
    
    material = models.ForeignKey(Material, on_delete=models.CASCADE, verbose_name="Материал")
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name="Тип операции")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Количество")
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Пользователь")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    
    def __str__(self):
        return f"{self.get_operation_type_display()} {self.material.name} - {self.quantity}"
    
    class Meta:
        verbose_name = "Операция с материалом"
        verbose_name_plural = "Операции с материалами"