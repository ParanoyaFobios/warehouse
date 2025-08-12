# warehouse1/views.py
from rest_framework import viewsets
from .models import MaterialCategory, UnitOfMeasure, Supplier, Material, MaterialOperation
from .serializers import (
    MaterialCategorySerializer,
    UnitOfMeasureSerializer,
    SupplierSerializer,
    MaterialSerializer,
    MaterialOperationSerializer
)

class MaterialCategoryViewSet(viewsets.ModelViewSet):
    queryset = MaterialCategory.objects.all()
    serializer_class = MaterialCategorySerializer

class UnitOfMeasureViewSet(viewsets.ModelViewSet):
    queryset = UnitOfMeasure.objects.all()
    serializer_class = UnitOfMeasureSerializer

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    filterset_fields = ['category', 'unit', 'supplier']
    search_fields = ['name', 'article', 'barcode']

class MaterialOperationViewSet(viewsets.ModelViewSet):
    queryset = MaterialOperation.objects.all()
    serializer_class = MaterialOperationSerializer
    filterset_fields = ['operation_type', 'material', 'user']