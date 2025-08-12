# warehouse1/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MaterialCategoryViewSet,
    UnitOfMeasureViewSet,
    SupplierViewSet,
    MaterialViewSet,
    MaterialOperationViewSet
)
from .views_api import api_incoming, api_outgoing

router = DefaultRouter()
router.register(r'categories', MaterialCategoryViewSet)
router.register(r'units', UnitOfMeasureViewSet)
router.register(r'suppliers', SupplierViewSet)
router.register(r'materials', MaterialViewSet)
router.register(r'operations', MaterialOperationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api/operations/incoming/', api_incoming, name='api_incoming'),
    path('api/operations/outgoing/', api_outgoing, name='api_outgoing'),
]