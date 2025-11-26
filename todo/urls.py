# todo/urls.py
from django.urls import path
from todo import views


urlpatterns = [
    # --- "ДОСКА ОБЪЯВЛЕНИЙ" (Задания на смену) ---
    path('workorders/', views.WorkOrderListView.as_view(), name='workorder_list'),
    path('workorders/create_adhoc/', views.WorkOrderAdHocCreateView.as_view(), name='workorder_create_adhoc'),
    path('workorders/<int:pk>/report/', views.ReportProductionView.as_view(), name='workorder_report'),
    path('workorders/<int:pk>/edit/', views.WorkOrderUpdateView.as_view(), name='workorder_edit'),
    path('workorders/<int:pk>/delete/', views.WorkOrderDeleteView.as_view(), name='workorder_delete'),

    # --- "ПОРТФЕЛЬ ЗАКАЗОВ" (Backlog) ---
    path('portfolio/', views.ProductionOrderListView.as_view(), name='portfolio_list'),
    path('portfolio/create/', views.ProductionOrderCreateView.as_view(), name='portfolio_create'),
    path('portfolio/<int:pk>/', views.ProductionOrderDetailView.as_view(), name='portfolio_detail'),
    path('portfolio/<int:pk>/edit/', views.ProductionOrderUpdateView.as_view(), name='portfolio_edit'),
    path('portfolio/<int:pk>/delete/', views.ProductionOrderDeleteView.as_view(), name='portfolio_delete'),

    path('portfolio/<int:pk>/plan/', views.PlanWorkOrdersView.as_view(), name='portfolio_plan_workorders'),
]