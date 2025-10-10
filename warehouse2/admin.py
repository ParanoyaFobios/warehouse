from django.contrib import admin
from .models import (
    ProductCategory, Product,
    WorkOrder, Shipment, ShipmentItem, ProductOperation, Sender)
from django.urls import reverse
from django.utils.html import format_html

# ==============================================================================
# Справочники
# ==============================================================================

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Sender)
class SenderAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
# ==============================================================================
# Основные модели
# ==============================================================================

class ShipmentItemInline(admin.TabularInline):
    model = ShipmentItem
    extra = 1
    fields = ('product', 'quantity')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'color', 'total_quantity', 'available_quantity')
    list_filter = ('category', 'color')
    search_fields = ('name', 'sku', 'barcode')
    readonly_fields = ('barcode', 'available_quantity')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'sku', 'barcode', 'category')
        }),
        ('Характеристики', {
            'fields': ('color', 'image')
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
    inlines = [ShipmentItemInline]
    actions = ['mark_as_shipped']
    
    def mark_as_shipped(self, request, queryset):
        for shipment in queryset:
            try:
                shipment.ship()
            except Exception as e:
                self.message_user(request, f"Ошибка при отгрузке {shipment.id}: {str(e)}", level='error')
        self.message_user(request, "Выбранные отгрузки помечены как отгруженные")
    mark_as_shipped.short_description = "Пометить как отгруженные"

class ShipmentInline(admin.TabularInline):
    """Отображает связанные отгрузки внутри накладной."""
    model = Shipment
    extra = 0 # Не показывать пустые формы для добавления
    fields = ('id', 'barcode', 'status', 'view_shipment_link')
    readonly_fields = ('id', 'barcode', 'status', 'view_shipment_link')
    can_delete = False

    def view_shipment_link(self, obj):
        if obj.pk:
            url = reverse('admin:warehouse2_shipment_change', args=[obj.pk])
            return format_html('<a href="{}">Смотреть</a>', url)
        return "-"
    view_shipment_link.short_description = 'Ссылка'


@admin.register(ProductOperation)
class ProductOperationAdmin(admin.ModelAdmin):
    list_display = ('product', 'timestamp', 'operation_type', 'quantity', 'user', 'source')
    list_filter = ('operation_type', 'timestamp', 'product__category')
    search_fields = ('product__name', 'product__sku', 'user__username')
    list_per_page = 25
    
    # Запрещаем создание, изменение и удаление записей вручную
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False