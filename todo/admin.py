from django.contrib import admin
from todo.models import WorkOrder

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('created_at', 'completed_at')
    actions = ['complete_orders']
    
    def complete_orders(self, request, queryset):
        for order in queryset:
            if order.status != 'completed':
                order.complete_order()
        self.message_user(request, "Выбранные заказы завершены")
    complete_orders.short_description = "Завершить выбранные заказы"