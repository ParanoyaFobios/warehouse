from django.contrib import admin
from .models import (
    ProductCategory, ProductSize, ProductColor, Product,
    WorkOrder, Shipment, ShipmentItem, Package
)

# ==============================================================================
# Справочники
# ==============================================================================

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(ProductColor)
class ProductColorAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

# ==============================================================================
# Основные модели
# ==============================================================================

class ShipmentItemInline(admin.TabularInline):
    model = ShipmentItem
    extra = 1
    fields = ('product', 'quantity')

class PackageInline(admin.TabularInline):
    model = Package
    extra = 0
    readonly_fields = ('barcode',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'size', 'color', 'total_quantity', 'available_quantity')
    list_filter = ('category', 'size', 'color')
    search_fields = ('name', 'sku', 'barcode')
    readonly_fields = ('barcode', 'available_quantity')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'sku', 'barcode', 'category')
        }),
        ('Характеристики', {
            'fields': ('size', 'color', 'weight', 'image')
        }),
        ('Остатки', {
            'fields': ('total_quantity', 'reserved_quantity', 'available_quantity')
        }),
    )

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'quantity_to_produce', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'completed_at')
    actions = ['complete_orders']
    
    def complete_orders(self, request, queryset):
        for order in queryset:
            if order.status != 'completed':
                order.complete_order()
        self.message_user(request, "Выбранные заказы завершены")
    complete_orders.short_description = "Завершить выбранные заказы"

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'status')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at',)
    inlines = [ShipmentItemInline, PackageInline]
    actions = ['mark_as_shipped']
    
    def mark_as_shipped(self, request, queryset):
        for shipment in queryset:
            try:
                shipment.ship()
            except Exception as e:
                self.message_user(request, f"Ошибка при отгрузке {shipment.id}: {str(e)}", level='error')
        self.message_user(request, "Выбранные отгрузки помечены как отгруженные")
    mark_as_shipped.short_description = "Пометить как отгруженные"

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('barcode', 'shipment')
    readonly_fields = ('barcode',)
    search_fields = ('barcode',)