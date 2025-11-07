from rest_framework import serializers

class KeyCRMOrderItemSerializer(serializers.Serializer):
    """
    Валидирует данные по одной товарной позиции из вебхука KeyCRM.
    """
    sku = serializers.CharField(max_length=50)
    quantity = serializers.IntegerField(min_value=1)
    # Добавьте другие поля из вебхука, если они вам нужны