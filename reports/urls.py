from django.urls import path
from . import views


urlpatterns = [
    path('', views.ReportsHomeView.as_view(), name='reports_home'),
    path('sales-over-time/', views.SalesOverTimeView.as_view(), name='sales_over_time'),
    path('movement-report/', views.MovementReportView.as_view(), name='movement_report'),
    # URL для API, к которому будет обращаться JavaScript для получения данных
    path('api/sales-chart-data/', views.sales_chart_data_api, name='sales_chart_data_api'),
]