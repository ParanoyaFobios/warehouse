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
    path('workorders/<int:pk>/', views.WorkOrderDetailView.as_view(), name='workorder_detail'),
    path('workorders/<int:pk>/edit/', views.WorkOrderUpdateView.as_view(), name='workorder_edit'),
    path('workorders/<int:pk>/delete/', views.WorkOrderDeleteView.as_view(), name='workorder_delete'),
    path('workorders/<int:pk>/complete/', views.complete_workorder, name='workorder_complete'),
    path('product-search/', views.product_search, name='product_search'),
    
    # Отгрузки
    path('shipments/', views.ShipmentListView.as_view(), name='shipment_list'),
    path('shipments/<int:pk>/ship/', views.ship_shipment, name='shipment_ship'),
]