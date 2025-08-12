#апи для мобильных сканеров
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Material
from .serializers import MaterialSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_incoming(request):
    barcode = request.data.get('barcode')
    quantity = request.data.get('quantity')
    
    try:
        material = Material.objects.get(barcode=barcode)
        material.add_quantity(
            quantity=quantity,
            user=request.user,
            comment=request.data.get('comment', '')
        )
        return Response({
            'status': 'success',
            'material': MaterialSerializer(material).data
        })
    except Material.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'Material not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_outgoing(request):
    barcode = request.data.get('barcode')
    quantity = request.data.get('quantity')
    
    try:
        material = Material.objects.get(barcode=barcode)
        material.subtract_quantity(
            quantity=quantity,
            user=request.user,
            comment=request.data.get('comment', '')
        )
        return Response({
            'status': 'success',
            'material': MaterialSerializer(material).data
        })
    except Material.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'Material not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )