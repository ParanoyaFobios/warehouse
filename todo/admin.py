from django.contrib import admin
from todo.models import ProductionOrder, ProductionOrderItem, WorkOrder

# --- Inlines (Встроенные формы для связанных моделей) ---

@admin.register(ProductionOrderItem)
class ProductionOrderItemAdmin(admin.ModelAdmin):
    """Отдельное представление для ProductionOrderItem, если нужно"""
    list_display = ('id', 'production_order', 'product', 'quantity_requested', 
                    'quantity_planned', 'quantity_produced', 'status')
    list_filter = ('status', 'product__name')
    search_fields = ('product__name', 'production_order__customer')
    readonly_fields = ('quantity_produced',)
    # Поля для редактирования
    fields = ('production_order', 'product', 'quantity_requested', 'quantity_planned', 'status')


class ProductionOrderItemInline(admin.TabularInline):
    """
    Строки заказа (items) внутри ProductionOrder.
    Используем TabularInline для компактности.
    """
    model = ProductionOrderItem
    # Дополнительные поля для отображения и редактирования
    fields = ('product', 'quantity_requested', 'quantity_planned', 'status')
    readonly_fields = ('quantity_planned', 'status')
    extra = 1 # Сколько пустых строк добавлять
    
    # Добавляем функциональность, чтобы запретить удаление, если есть запланированное производство
    def has_delete_permission(self, request, obj=None):
        if obj:
            for item in obj.items.all():
                if item.quantity_planned > 0:
                    return False
        return True


class WorkOrderInline(admin.StackedInline):
    """
    Задания на производство (WorkOrders) внутри ProductionOrderItem.
    Используем StackedInline для лучшего отображения информации.
    """
    model = WorkOrder
    fields = ('product', 'quantity_planned', 'quantity_produced', 'status', 'start_time', 'end_time')
    readonly_fields = ('product', 'quantity_planned', 'quantity_produced', 'status')
    can_delete = False
    max_num = 0 # Нельзя создавать/удалять WorkOrder через ProductionOrder, только через PlanWorkOrdersView

# --- Основные модели (Admin Views) ---

@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    """Настройки для ProductionOrder (Заказ Портфеля)"""
    list_display = ('id', 'customer', 'due_date', 'status', 'created_at')
    list_filter = ('status', 'due_date')
    search_fields = ('customer', 'comment')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    # Встраиваем строки заказа
    inlines = [ProductionOrderItemInline]

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    """Настройки для WorkOrder (Задание на смену)"""
    list_display = ('id', 'product', 'quantity_planned', 'quantity_produced', 'status', 'created_at')
    list_filter = ('status', 'product__name', 'created_at')
    search_fields = ('product__name', 'order_item__production_order__customer')
    date_hierarchy = 'created_at'
    ordering = ('status', '-created_at')
    
    # Поля, которые нельзя редактировать, после того как задание создано
    readonly_fields = ('order_item', 'product', 'quantity_planned', 'quantity_produced')
    
    fieldsets = (
        ('Связанный заказ', {
            'fields': ('order_item', 'product',),
            'description': 'Информация о том, для какого товара и строки заказа создано задание.'
        }),
        ('Планирование и выполнение', {
            'fields': ('quantity_planned', 'quantity_produced', 'status', 'start_time', 'end_time', 'comment'),
        }),
    )