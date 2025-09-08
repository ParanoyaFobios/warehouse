from django.urls import path
from . import views


urlpatterns = [
    # Список всех переучетов
    path('', views.InventoryCountListView.as_view(), name='count_list'),
    path('stock-search/', views.inventory_stock_search, name='inventory_stock_search'),
    # URL для создания нового переучета
    path('start/', views.StartInventoryCountView.as_view(), name='count_start'),
    path('<int:pk>/complete/', views.complete_inventory_count, name='count_complete'),
    # Главная рабочая страница для проведения переучета
    path('<int:pk>/', views.InventoryCountWorkView.as_view(), name='count_work'),
    
    # URL для обновления и удаления конкретной позиции
    path('item/<int:pk>/update/', views.update_inventory_item, name='item_update'),
    path('item/<int:pk>/delete/', views.delete_inventory_item, name='item_delete'),
    # Маршруты для сверки
    path('<int:pk>/reconcile/', views.InventoryReconciliationView.as_view(), name='count_reconcile'),
    path('<int:pk>/reconcile/action/', views.ReconcileInventoryView.as_view(), name='count_reconcile_action'),
    path('<int:pk>/finalize/', views.FinalizeInventoryView.as_view(), name='count_finalize'),
]