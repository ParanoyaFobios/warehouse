from django.contrib import admin
from .models import InventoryCount, InventoryCountItem

@admin.register(InventoryCountItem)
class InventoryCountItemAdmin(admin.ModelAdmin):
    """
    Отдельное отображение позиций (в основном для отладки).
    Основное управление будет через инлайн в InventoryCountAdmin.
    """
    list_display = ('inventory_count', 'content_object', 'system_quantity', 'actual_quantity', 'variance')
    list_filter = ('inventory_count__status',)
    search_fields = ('content_object__name',) # Это может работать не для всех моделей, но для Product/Material подойдет

    @admin.display(description="Расхождение")
    def variance(self, obj):
        return obj.variance


class InventoryCountItemInline(admin.TabularInline):
    """
    Позволяет отображать и редактировать позиции переучета
    прямо на странице самого переучета.
    """
    model = InventoryCountItem
    fields = ('content_object', 'system_quantity', 'actual_quantity', 'variance_display')
    readonly_fields = ('content_object', 'system_quantity', 'variance_display')
    extra = 0 # Не показывать пустые строки для добавления
    
    # Отключаем возможность добавлять/удалять позиции напрямую через админку
    def has_add_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Расхождение")
    def variance_display(self, obj):
        variance = obj.variance
        color = "green" if variance > 0 else "red" if variance < 0 else "black"
        sign = "+" if variance > 0 else ""
        return f'<strong style="color: {color};">{sign}{variance}</strong>'
    variance_display.allow_tags = True


@admin.register(InventoryCount)
class InventoryCountAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user', 'status', 'created_at', 'completed_at', 'item_count')
    list_filter = ('status', 'user')
    readonly_fields = ('created_at', 'completed_at')
    inlines = [InventoryCountItemInline]

    @admin.display(description="Кол-во позиций")
    def item_count(self, obj):
        return obj.items.count()