from django.urls import path
from .views import ChatView, CreateDialogView, DeleteChatView

urlpatterns = [
    # Просто открыли /messages/ - видим список диалогов (пустой правый блок)
    path('messages/', ChatView.as_view(), name='dialogs'),
    
    # Создать новый диалог (кнопка "Новое сообщение")
    path('messages/new/', CreateDialogView.as_view(), name='new_message'),

    # Открыли конкретный чат
    path('messages/<int:user_id>/', ChatView.as_view(), name='chat_detail'),
    path('messages/delete/<int:user_id>/', DeleteChatView.as_view(), name='delete_chat'),
]