from django.contrib import admin
from .models import MaterialCategory, UnitOfMeasure, Material, MaterialOperation, OperationOutgoingCategory, MaterialColor

@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name')
    search_fields = ('name', 'short_name')

@admin.register(MaterialColor)
class MaterialColorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(OperationOutgoingCategory)
class OperationOutgoingCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'article', 'category', 'quantity', 'unit', 'barcode')
    list_filter = ('category', 'unit')
    search_fields = ('name', 'article', 'barcode')

@admin.register(MaterialOperation)
class MaterialOperationAdmin(admin.ModelAdmin):
    list_display = ('material', 'operation_type', 'outgoing_category', 'quantity', 'date', 'user')
    list_filter = ('operation_type', 'outgoing_category', 'date')
    search_fields = ('material__name', 'material__article')