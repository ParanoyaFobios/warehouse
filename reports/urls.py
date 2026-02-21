from django.urls import path
from . import views


urlpatterns = [
    path('', views.ReportsHomeView.as_view(), name='reports_home'),
    path('sales-over-time/', views.SalesOverTimeView.as_view(), name='sales_over_time'),
    path('movement-report/', views.MovementReportView.as_view(), name='movement_report'),
    path('sales-by-product/', views.SalesByProductReportView.as_view(), name='sales_by_product_report'),
    path('low-stock-report/', views.LowStockReportView.as_view(), name='low_stock_report'),
    path('stock-ageing/', views.StockAgeingReportView.as_view(), name='stock_ageing_report'),
    path('audit/', views.ShipmentAuditListView.as_view(), name='shipment_audit_list'),
    # URL для API, к которому будет обращаться JavaScript для получения данных
    path('api/sales-chart-data/', views.sales_chart_data_api, name='sales_chart_data_api'),
    path('api/sales-by-product-data/', views.sales_by_product_api, name='sales_by_product_api'),
    path('api/sales-by-category-data/', views.sales_by_category_api, name='sales_by_category_api'),
]