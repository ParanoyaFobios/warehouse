from django.urls import path
from todo import views


urlpatterns = [
    # --- "ДОСКА ОБЪЯВЛЕНИЙ" (Задания на смену) ---
    path('workorders/', views.WorkOrderListView.as_view(), name='workorder_list'),
    path('workorder/<int:pk>/detail/', views.WorkorderOrderDetailView.as_view(), name='workorder_detail'),
    path('orders/aggregate/', views.AggregateOrdersView.as_view(), name='aggregate_orders'),
    # AJAX эндпоинт (скрытый путь для JS)
    path('api/workorder/report/', views.workorder_report_ajax, name='api_workorder_report'),

    # --- "ПЛАНИРОВАНИЕ ЗАКАЗОВ" (Backlog) ---
    path('portfolio/', views.ProductionOrderListView.as_view(), name='portfolio_list'),
    path('portfolio/create/', views.ProductionOrderCreateView.as_view(), name='portfolio_create'),
    path('portfolio/<int:pk>/', views.ProductionOrderDetailView.as_view(), name='portfolio_detail'),
    path('portfolio/<int:pk>/edit/', views.ProductionOrderUpdateView.as_view(), name='portfolio_edit'),
    path('portfolio/<int:pk>/delete/', views.ProductionOrderDeleteView.as_view(), name='portfolio_delete'),

    path('portfolio/<int:pk>/plan/', views.PlanWorkOrdersView.as_view(), name='portfolio_plan_workorders'),
    path('portfolio/<int:pk>/create_shipment/', views.CreateShipmentFromOrderView.as_view(), name='portfolio_create_shipment'),
]