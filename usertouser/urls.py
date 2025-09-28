from django.urls import path
from usertouser import views

urlpatterns = [
    path('inbox/', views.InboxView.as_view(), name='inbox'),
    path('outbox/', views.OutboxView.as_view(), name='outbox'),
    path('compose/', views.ComposeMessageView.as_view(), name='compose'),
    path('message/<int:pk>/', views.MessageDetailView.as_view(), name='message_detail'),
    path('message/<int:pk>/reply/', views.ComposeMessageView.as_view(), name='message_reply'),
]