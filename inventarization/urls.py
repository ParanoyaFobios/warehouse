from django.urls import path
from . import views


urlpatterns = [
    # Список всех переучетов
    path('', views.InventoryCountListView.as_view(), name='count_list'),
    
    # URL для создания нового переучета
    path('start/', views.StartInventoryCountView.as_view(), name='count_start'),
    
    # Главная рабочая страница для проведения переучета
    path('<int:pk>/', views.InventoryCountWorkView.as_view(), name='count_work'),
    
    # URL для обновления и удаления конкретной позиции
    path('item/<int:pk>/update/', views.update_inventory_item, name='item_update'),
    path('item/<int:pk>/delete/', views.delete_inventory_item, name='item_delete'),
]