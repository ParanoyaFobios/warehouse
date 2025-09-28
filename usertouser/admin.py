from django.contrib import admin
from django.utils.html import format_html
from usertouser.models import Message, MessageRecipient

class MessageRecipientInline(admin.TabularInline):
    """
    Inline для отображения получателей прямо в форме сообщения.
    """
    model = MessageRecipient
    extra = 1  # Количество пустых форм для добавления новых получателей
    readonly_fields = ['is_read', 'is_deleted']
    fields = ['user', 'is_read', 'is_deleted']
    can_delete = True
    
    def has_add_permission(self, request, obj=None):
        # Запрещаем добавлять получателей через админку для существующих сообщений
        # Это лучше делать через логику приложения
        return False

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Админ-панель для сообщений.
    """
    list_display = [
        'id', 
        'truncated_content', 
        'sender_info', 
        'recipients_count', 
        'timestamp', 
        'sender_deleted',
        'is_read_status'
    ]
    list_filter = [
        'timestamp',
        'sender_deleted',
        'sender',
    ]
    search_fields = [
        'content',
        'sender__username',
        'sender__first_name', 
        'sender__last_name',
        'recipients__username'
    ]
    readonly_fields = [
        'timestamp',
        'recipients_list',
        'read_status_summary'
    ]
    fieldsets = (
        ('Основная информация', {
            'fields': ('sender', 'content', 'timestamp')
        }),
        ('Получатели', {
            'fields': ('recipients_list',),
            'classes': ('collapse',)
        }),
        ('Статусы', {
            'fields': ('sender_deleted', 'read_status_summary'),
            'classes': ('collapse',)
        }),
    )
    inlines = [MessageRecipientInline]
    
    def truncated_content(self, obj):
        """
        Обрезает содержание сообщения для отображения в списке.
        """
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    truncated_content.short_description = 'Содержание'
    
    def sender_info(self, obj):
        """
        Отображает информацию об отправителе.
        """
        if obj.sender:
            return f"{obj.sender.username} ({obj.sender.get_full_name() or 'нет имени'})"
        return "Удаленный пользователь"
    sender_info.short_description = 'Отправитель'
    
    def recipients_count(self, obj):
        """
        Показывает количество получателей.
        """
        count = obj.recipients.count()
        read_count = obj.messagerecipient_set.filter(is_read=True).count()
        return f"{count} ({read_count} прочитано)"
    recipients_count.short_description = 'Получатели'
    
    def is_read_status(self, obj):
        """
        Показывает статус прочтения в виде иконок.
        """
        total = obj.recipients.count()
        if total == 0:
            return "📝"  # Нет получателей
        
        read_count = obj.messagerecipient_set.filter(is_read=True).count()
        if read_count == total:
            return "✅"  # Все прочитали
        elif read_count > 0:
            return "🟡"  # Частично прочитано
        else:
            return "🔴"  # Никто не прочитал
    is_read_status.short_description = 'Статус'
    
    def recipients_list(self, obj):
        """
        Показывает список получателей с их статусами.
        """
        recipients_info = []
        for recipient_rel in obj.messagerecipient_set.select_related('user').all():
            status = "✅" if recipient_rel.is_read else "⏳"
            deleted = "🗑️" if recipient_rel.is_deleted else ""
            recipients_info.append(
                f"{status} {deleted} {recipient_rel.user.username}"
            )
        
        if recipients_info:
            return format_html("<br>".join(recipients_info))
        return "Нет получателей"
    recipients_list.short_description = 'Список получателей'
    
    def read_status_summary(self, obj):
        """
        Сводка по статусам прочтения.
        """
        total = obj.recipients.count()
        if total == 0:
            return "Нет получателей"
        
        read_count = obj.messagerecipient_set.filter(is_read=True).count()
        deleted_count = obj.messagerecipient_set.filter(is_deleted=True).count()
        
        return format_html(
            "Всего получателей: {}<br>"
            "Прочитали: {}<br>"
            "Удалили: {}",
            total, read_count, deleted_count
        )
    read_status_summary.short_description = 'Статистика'
    
    def get_queryset(self, request):
        """
        Оптимизируем запросы к базе данных.
        """
        return super().get_queryset(request).prefetch_related(
            'recipients',
            'messagerecipient_set',
            'messagerecipient_set__user'
        )

@admin.register(MessageRecipient)
class MessageRecipientAdmin(admin.ModelAdmin):
    """
    Админ-панель для связи сообщений с получателями.
    """
    list_display = [
        'id',
        'message_preview',
        'user_info',
        'is_read',
        'is_deleted',
        'message_timestamp'
    ]
    list_filter = [
        'is_read',
        'is_deleted',
        'message__timestamp',
        'user'
    ]
    search_fields = [
        'message__content',
        'user__username',
        'user__first_name',
        'user__last_name'
    ]
    readonly_fields = ['message_timestamp']
    list_select_related = ['message', 'user']
    
    def message_preview(self, obj):
        """
        Показывает превью сообщения.
        """
        if len(obj.message.content) > 30:
            return f"{obj.message.content[:30]}..."
        return obj.message.content
    message_preview.short_description = 'Сообщение'
    
    def user_info(self, obj):
        """
        Информация о пользователе-получателе.
        """
        return f"{obj.user.username} ({obj.user.get_full_name() or 'нет имени'})"
    user_info.short_description = 'Получатель'
    
    def message_timestamp(self, obj):
        """
        Время отправки сообщения.
        """
        return obj.message.timestamp
    message_timestamp.short_description = 'Время отправки'
    
    def get_queryset(self, request):
        """
        Оптимизируем запросы.
        """
        return super().get_queryset(request).select_related('message', 'user')

# Дополнительные настройки для админ-панели
admin.site.site_header = "Панель управления системой сообщений"
admin.site.site_title = "Система сообщений"
admin.site.index_title = "Управление сообщениями"