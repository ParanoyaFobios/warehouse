from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from .models import Product
from .serializers import KeyCRMOrderItemSerializer

class KeyCRMOrderWebhookView(APIView):
    """
    Принимает и обрабатывает вебхуки от KeyCRM о создании/обновлении заказа.
    """
    # Отключаем стандартную аутентификацию DRF, будем проверять токен вручную
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        # Опционально, но рекомендуется: проверка секретного токена
        # secret_token = request.headers.get('X-Secret-Token')
        # if secret_token != settings.KEYCRM_WEBHOOK_SECRET:
        #     return Response({'error': 'Invalid secret token'}, status=status.HTTP_403_FORBIDDEN)
        
        order_data = request.data
        order_items = order_data.get('products', []) # В API KeyCRM товары в заказе могут быть в поле 'products'

        try:
            with transaction.atomic():
                # Проходим по всем товарам в заказе
                for item_data in order_items:
                    serializer = KeyCRMOrderItemSerializer(data=item_data)
                    if serializer.is_valid(raise_exception=True):
                        sku = serializer.validated_data['sku']
                        quantity = serializer.validated_data['quantity']

                        try:
                            # Находим товар в нашей БД по артикулу
                            product = Product.objects.get(sku=sku)
                            
                            # ЛУЧШАЯ ПРАКТИКА: Резервируем товар, а не списываем
                            # Это позволит вам видеть, сколько товара доступно для новых заказов
                            if product.available_quantity < quantity:
                                # В реальном проекте здесь нужно логировать ошибку
                                # и, возможно, отправлять уведомление менеджеру
                                print(f"ВНИМАНИЕ: Недостаточно товара {sku} для резервирования!")
                                continue # Пропускаем эту позицию

                            product.reserved_quantity += quantity
                            product.save()

                        except Product.DoesNotExist:
                            # Логируем, что товар из заказа не найден в нашей системе
                            print(f"Товар с артикулом {sku} из заказа не найден в WMS.")
                            continue
            
            # Если все прошло успешно, отвечаем KeyCRM статусом 200 OK
            return Response({'status': 'success'}, status=status.HTTP_200_OK)

        except Exception as e:
            # Если произошла любая ошибка, логируем ее и отвечаем ошибкой
            print(f"Ошибка обработки вебхука KeyCRM: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)