from django.db import models
from django.contrib.auth.models import User
import uuid
import re

def generate_unique_barcode_for_model(model_class):
    """Универсальная функция для генерации уникального штрихкода для любой модели."""
    while True:
        barcode = uuid.uuid4().hex[:12].upper()
        if not model_class.objects.filter(barcode=barcode).exists():
            return barcode

def generate_material_barcode():
    return generate_unique_barcode_for_model(Material)

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

class MaterialColor(models.Model):
    """Цвета продукции (например, Белый, Синий)."""
    name = models.CharField(max_length=50, unique=True, verbose_name="Цвет")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Цвет материала"
        verbose_name_plural = "Цвета материала"

class Material(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название материала")
    article = models.CharField(max_length=50, unique=True, verbose_name="Артикул")
    category = models.ForeignKey(MaterialCategory, on_delete=models.PROTECT, verbose_name="Категория")
    barcode = models.CharField(max_length=12, unique=True, verbose_name="Штрихкод", default=generate_material_barcode, editable=False)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Количество")
    min_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Минимальное количество")
    color = models.ForeignKey(MaterialColor, on_delete=models.PROTECT, verbose_name="Цвет", blank=True, null=True)
    unit = models.ForeignKey(UnitOfMeasure, on_delete=models.PROTECT, verbose_name="Единица измерения")
    image = models.ImageField(upload_to='material/', blank=True, null=True, verbose_name="Изображение")
    description = models.TextField(blank=True, verbose_name="Описание")

    def add_quantity(self, quantity):
        """Увеличение количества материала (прием)"""
        self.quantity += quantity
        self.save()

    
    def subtract_quantity(self, quantity):
        """Уменьшение количества материала (выдача/списание)"""
        if self.quantity < quantity:
            raise ValueError("Недостаточно материала на складе")
        self.quantity -= quantity
        self.save()

    
    
    def __str__(self):
        return f"{self.name} ({self.article})"
    
    class Meta:
        verbose_name = "Материал"
        verbose_name_plural = "Материалы"
        permissions = [
            ("can_view_material_quantity", "Может просматривать количество материалов на складе"),
        ]

class OperationOutgoingCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название категории выдачи")
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Категория выдачи"
        verbose_name_plural = "Категории выдачи"

class MaterialOperation(models.Model):
    OPERATION_TYPES = (
        ('incoming', 'Приход'),
        ('outgoing', 'Расход'),
        ('adjustment', 'Корректировка:')
    )
    
    material = models.ForeignKey(Material, on_delete=models.CASCADE, verbose_name="Материал")
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name="Тип операции")
    outgoing_category = models.ForeignKey(OperationOutgoingCategory, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Назначение выдачи")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Количество")#Поменять на quantity = models.IntegerField(verbose_name="Количество")
    
    date = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Пользователь")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    
    def __str__(self):
        if self.operation_type == 'adjustment':
            # Для корректировки пытаемся извлечь информацию о знаке из комментария
            match = re.search(r'Корректировка:\s*([+-]?\d*\.?\d+)', self.comment)
            if match:
                adjustment_value = match.group(1)
                return f"Корректировка {self.material.name}: {adjustment_value}"
            return f"{self.get_operation_type_display()} {self.material.name} - {self.quantity}"
        else:
            return f"{self.get_operation_type_display()} {self.material.name} - {self.quantity}"
    
    class Meta:
        verbose_name = "Операция с материалом"
        verbose_name_plural = "Операции с материалами"
