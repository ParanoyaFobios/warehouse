from django.urls import path
from .views_ui import material_list, material_create, material_update
from .views_operations import incoming_operation, outgoing_operation, inventory_operation
from django.views.generic import TemplateView

urlpatterns = [
    path('materials/', material_list, name='material_list'),
    path('materials/create/', material_create, name='material_create'),
    path('materials/update/<int:pk>/', material_update, name='material_update'),
    path('operations/incoming/', incoming_operation, name='incoming_operation'),
    path('operations/outgoing/', outgoing_operation, name='outgoing_operation'),
    path('operations/inventory/', inventory_operation, name='inventory_operation'),
    path('operations/', TemplateView.as_view(template_name='warehouse1/operations_menu.html'), name='operations_menu'),
]