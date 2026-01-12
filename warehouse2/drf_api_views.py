from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import KeyCRMProductSerializer
from .models import Product

class KeyCRMWebhookView(APIView):
    """Приемщик вебхуков от KeyCRM."""
    
    def post(self, request, *args, **kwargs):
        data = request.data
        # KeyCRM присылает данные в разных форматах в зависимости от события
        # Но обычно объект товара лежит в корне или под ключом 'object'
        
        print(f"Получен вебхук от KeyCRM: {data}")

        # 1. Обработка создания/обновления товара
        # Если это вебхук по товару (product.created или product.updated)
        serializer = KeyCRMProductSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        
        # 2. Обработка движения остатков (если пришел вебхук по остаткам)
        # В KeyCRM остатки могут приходить в отдельном формате
        if 'stocks' in data:
            for stock in data['stocks']:
                sku = stock.get('sku')
                quantity = stock.get('quantity')
                Product.objects.filter(sku=sku).update(total_quantity=quantity)
            return Response({"status": "stocks updated"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)