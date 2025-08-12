from django.contrib import admin
from .models import MaterialCategory, UnitOfMeasure, Supplier, Material, MaterialOperation

@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name')
    search_fields = ('name', 'short_name')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_info')
    search_fields = ('name',)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('name', 'article', 'category', 'quantity', 'unit', 'barcode')
    list_filter = ('category', 'unit')
    search_fields = ('name', 'article', 'barcode')

@admin.register(MaterialOperation)
class MaterialOperationAdmin(admin.ModelAdmin):
    list_display = ('material', 'operation_type', 'quantity', 'date', 'user')
    list_filter = ('operation_type', 'date')
    search_fields = ('material__name', 'material__article')