from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([AllowAny])
def estadisticas_generales_view(request):
    """Vista básica para estadísticas"""
    return Response({
        'mensaje': 'Estadísticas generales',
        'total_aulas': 0,
        'total_usuarios': 0,
        'estado': 'En desarrollo'
    })