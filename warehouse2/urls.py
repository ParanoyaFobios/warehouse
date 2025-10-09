from django.urls import path
from . import views


urlpatterns = [
    # Продукция
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/incoming/', views.ProductIncomingView.as_view(), name='product_incoming'),
    path('products/search-json/', views.product_search_json, name='product_search_json'),
    path('products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'), # <<< Добавьте эту строку

    path('package/<int:pk>/edit/', views.PackageUpdateView.as_view(), name='package_edit'),
    path('package/<int:pk>/delete/', views.PackageDeleteView.as_view(), name='package_delete'),
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
    path('shipments/<int:pk>/delete/', views.ShipmentDeleteView.as_view(), name='shipment_delete'),
    path('shipments/<int:pk>/ship/', views.ship_shipment, name='shipment_ship'),
    path('shipments/<int:pk>/items/', views.ShipmentItemsView.as_view(), name='shipment_items'),
    path('available-product-search/', views.stock_search, name='stock_search'),
    path('shipments/items/<int:pk>/delete/', views.delete_shipment_item, name='delete_shipment_item'),
    path('shipment/<int:pk>/return/', views.ReturnShipmentView.as_view(), name='shipment_return'),
    path('shipment/<int:pk>/mark_packaged/', views.mark_shipment_as_packaged, name='shipment_mark_packaged'),
]