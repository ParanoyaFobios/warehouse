from django.urls import path
from .views import (MaterialListView, MaterialCreateView, MaterialUpdateView)
from .views_operations import IncomingSearchView, IncomingConfirmView, OutgoingSearchView, OutgoingConfirmView
from django.views.generic import TemplateView

urlpatterns = [
    path('materials/', MaterialListView.as_view(), name='material_list'),
    path('materials/create/', MaterialCreateView.as_view(), name='material_create'),
    path('materials/update/<int:pk>/', MaterialUpdateView.as_view(), name='material_update'),
    
    path('operations/incoming/', IncomingSearchView.as_view(), name='incoming_operation'),
    path('operations/incoming/confirm/', IncomingConfirmView.as_view(), name='operation_confirm'),
    path('operations/outgoing/', OutgoingSearchView.as_view(), name='outgoing_operation'),
    path('operations/outgoing/confirm/', OutgoingConfirmView.as_view(), name='operation_confirm'),
]