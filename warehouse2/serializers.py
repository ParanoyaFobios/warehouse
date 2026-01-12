from rest_framework import serializers
from .models import Product, ProductCategory

class KeyCRMProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='keycrm_id', required=False)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    is_archived = serializers.BooleanField(required=False)
    thumbnail_url = serializers.URLField(required=False, allow_null=True) # Прямая ссылка на превью

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'barcode', 'price', 
            'category_id', 'total_quantity', 'keycrm_id',
            'is_archived', 'thumbnail_url'
        ]

    def save(self, **kwargs):
        data = self.validated_data
        category_id = data.pop('category_id', None)
        external_url = data.pop('thumbnail_url', None)
        is_archived = data.get('is_archived', False)
        sku = data.get('sku')
        keycrm_id = data.get('keycrm_id')
        product = Product.objects.filter(sku=sku).first() or \
                  Product.objects.filter(keycrm_id=keycrm_id).first()

        if product:
            # Обновляем поля
            for attr, value in data.items():
                setattr(product, attr, value)
            
            # Если пришла внешняя ссылка и нет своей картинки — сохраняем ссылку
            if external_url and not product.image:
                product.external_image_url = external_url
            
            product.save()
            return product
        else:
            # При создании нового
            new_product = Product.objects.create(
                **data, 
                external_image_url=external_url
            )
            return new_product