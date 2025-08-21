from django.urls import path
from . import views


urlpatterns = [
    # Продукция
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    
    # Производственные заказы
    path('workorders/', views.WorkOrderListView.as_view(), name='workorder_list'),
    path('workorders/create/', views.WorkOrderCreateView.as_view(), name='workorder_create'),
    path('workorders/<int:pk>/complete/', views.complete_workorder, name='workorder_complete'),
    
    # Отгрузки
    path('shipments/', views.ShipmentListView.as_view(), name='shipment_list'),
    path('shipments/<int:pk>/ship/', views.ship_shipment, name='shipment_ship'),
]