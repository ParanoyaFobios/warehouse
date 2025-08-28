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
    
    # Shipment URLs
    path('shipments/', views.ShipmentListView.as_view(), name='shipment_list'),
    path('shipments/create/', views.ShipmentCreateView.as_view(), name='shipment_create'),
    path('shipments/<int:pk>/', views.ShipmentDetailView.as_view(), name='shipment_detail'),
    path('shipments/<int:pk>/edit/', views.ShipmentUpdateView.as_view(), name='shipment_edit'),
    path('shipments/<int:pk>/delete/', views.ShipmentDeleteView.as_view(), name='shipment_delete'),
    path('shipments/<int:pk>/ship/', views.ship_shipment, name='shipment_ship'),
    path('shipments/<int:pk>/items/', views.ShipmentItemsView.as_view(), name='shipment_items'),
    path('available-product-search/', views.available_product_search, name='available_product_search'),
    path('shipments/items/<int:pk>/delete/', views.delete_shipment_item, name='delete_shipment_item'),
    # Shipment Document URLs
    path('documents/', views.ShipmentDocumentListView.as_view(), name='shipment_document_list'),
    path('documents/create/', views.ShipmentDocumentCreateView.as_view(), name='shipment_document_create'),
    path('documents/<int:pk>/', views.ShipmentDocumentDetailView.as_view(), name='shipment_document_detail'),
    path('documents/<int:pk>/manage/', views.manage_shipment_document, name='shipment_document_manage'),
]