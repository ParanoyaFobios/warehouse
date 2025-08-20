from django.urls import path
from .views import (MaterialListView, MaterialCreateView, material_barcode_view, MaterialUpdateView, MaterialDetailView)
from .views_operations import MaterialOperationView, IncomingOperationView, OutgoingOperationView

urlpatterns = [
    path('materials/', MaterialListView.as_view(), name='material_list'),
    path('materials/detail/<int:pk>/', MaterialDetailView.as_view(), name='material_detail'),
    path('materials/create/', MaterialCreateView.as_view(), name='material_create'),
    path('material/<int:pk>/barcode/', material_barcode_view, name='material_barcode'),
    path('materials/update/<int:pk>/', MaterialUpdateView.as_view(), name='material_update'),
    
    path('operations/incoming/', MaterialOperationView.as_view(operation_type='incoming'), name='incoming_operation'),
    path('operations/outgoing/', MaterialOperationView.as_view(operation_type='outgoing'), name='outgoing_operation'),
    path('operations/incoming/<int:material_id>/', IncomingOperationView.as_view(), name='incoming_with_material'),
    path('operations/outgoing/<int:material_id>/', OutgoingOperationView.as_view(), name='outgoing_with_material'),
]