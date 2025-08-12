from rest_framework import serializers
from .models import MaterialCategory, UnitOfMeasure, Supplier, Material, MaterialOperation

class MaterialCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialCategory
        fields = '__all__'

class UnitOfMeasureSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitOfMeasure
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'

class MaterialSerializer(serializers.ModelSerializer):
    category = MaterialCategorySerializer()
    unit = UnitOfMeasureSerializer()
    supplier = SupplierSerializer()
    
    class Meta:
        model = Material
        fields = '__all__'

class MaterialOperationSerializer(serializers.ModelSerializer):
    material = MaterialSerializer()
    user = serializers.StringRelatedField()
    
    class Meta:
        model = MaterialOperation
        fields = '__all__'