from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Vista básica de login"""
    username = request.data.get('username')
    return Response({
        'mensaje': 'Login en desarrollo',
        'username': username,
        'estado': 'En construcción'
    })